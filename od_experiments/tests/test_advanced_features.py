# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Comprehensive automated test suite for Earth2Studio Advanced Capabilities:
Pillars 1-6 (Ensembles, Storm Tracking, Data Ingestion, Model Benchmark, Downscaling, DA).
"""

import numpy as np
import pytest

from od_experiments.ensemble.ensemble_engine import generate_ensemble_forecast
from od_experiments.storm_tracking.storm_tracker import detect_mslp_minima, track_cyclone_trajectory
from od_experiments.data_ingestion.ingestion_engine import MultiSourceIngestionEngine
from od_experiments.model_comparison.comparison_suite import benchmark_model_suite
from od_experiments.downscaling.mesoscale_engine import downscale_regional_grid
from od_experiments.data_assimilation.da_engine import run_point_observation_assimilation


def test_pillar1_ensemble_properties():
    """Verify ensemble spread is zero for control, strictly non-zero for perturbed members, and bounded."""
    lats = np.linspace(90, -90, 37)
    lons = np.linspace(0, 355, 72)
    init_state = np.ones((len(lats), len(lons))) * 285.0
    
    ens = generate_ensemble_forecast(init_state, lats, lons, n_members=10, n_steps=3, seed=123)
    
    assert ens["ensemble_cube"].shape == (10, 4, 37, 72)
    # Control member at t=0 has zero perturbation
    np.testing.assert_allclose(ens["ensemble_cube"][0, 0], init_state)
    # Ensemble spread across all members is non-zero
    assert np.all(ens["spread"][0] >= 0.0)
    assert np.mean(ens["spread"][0]) > 0.05
    # Percentiles ordering
    assert np.all(ens["p10"] <= ens["p90"])


def test_pillar2_storm_tracking_minima():
    """Verify detection and trajectory extraction for local MSLP minima."""
    lats = np.linspace(50, 20, 31)
    lons = np.linspace(120, 160, 41)
    
    # Create background pressure field (1015 hPa) with an embedded vortex (980 hPa) at lat=35, lon=140
    mslp = np.ones((len(lats), len(lons))) * 1015.0
    r_idx = np.argmin(np.abs(lats - 35.0))
    c_idx = np.argmin(np.abs(lons - 140.0))
    mslp[r_idx, c_idx] = 980.0
    # Add surrounding vortex gradient
    for dr in range(-2, 3):
        for dc in range(-2, 3):
            if dr == 0 and dc == 0:
                continue
            mslp[r_idx + dr, c_idx + dc] = 990.0 + (dr**2 + dc**2) * 2.0
            
    detected = detect_mslp_minima(mslp, lats, lons, neighborhood_size=5, threshold_hpa=1000.0)
    assert len(detected) == 1
    assert detected[0]["lat"] == pytest.approx(35.0, abs=1.5)
    assert detected[0]["lon"] == pytest.approx(140.0, abs=1.5)
    assert detected[0]["min_mslp_hpa"] == pytest.approx(980.0, abs=0.1)


def test_pillar3_data_ingestion_coordinate_standardization():
    """Verify coordinate reorientation and physical bounds checking."""
    # Ascending latitudes (-90 to +90) and negative longitudes (-180 to 180)
    lats_south_first = np.linspace(-90, 90, 19)
    lons_neg = np.linspace(-180, 170, 36)
    data = np.random.uniform(250, 310, (19, 36))
    
    std_data, out_lats, out_lons = MultiSourceIngestionEngine.standardize_coordinates(
        data, lats_south_first, lons_neg, "ERA5"
    )
    
    # Latitudes must now run North to South (+90 to -90)
    assert out_lats[0] > out_lats[-1]
    assert out_lats[0] == 90.0
    # Longitudes must now be strictly non-negative in [0, 360)
    assert np.all(out_lons >= 0.0)
    assert np.all(out_lons < 360.0)
    
    # Physical consistency validator
    assert MultiSourceIngestionEngine.validate_physical_consistency("t2m", np.array([288.15])) is True
    assert MultiSourceIngestionEngine.validate_physical_consistency("t2m", np.array([120.0])) is False


def test_pillar4_model_comparison_benchmark():
    """Verify multi-model comparison calculates unbiased RMSE and TAC."""
    lats = np.linspace(90, -90, 19)
    # Background truth
    truth = np.ones((19, 36)) * 290.0
    # Baseline persistence
    pers = np.ones((19, 36)) * 285.0 # error of 5K
    # Superior neural forecast
    neural = np.ones((19, 36)) * 289.0 # error of 1K
    
    results = benchmark_model_suite(
        init_state=pers,
        verifying_truth=truth,
        lats=lats,
        candidate_forecasts={
            "Persistence": pers,
            "Neural_Candidate": neural,
        }
    )
    
    assert "Persistence" in results
    assert "Neural_Candidate" in results
    assert results["Persistence"]["rmse"] == pytest.approx(5.0, abs=0.01)
    assert results["Neural_Candidate"]["rmse"] == pytest.approx(1.0, abs=0.01)
    # Neural skill relative to persistence should be ~80%
    assert results["Neural_Candidate"]["skill_vs_persistence_pct"] == pytest.approx(80.0, abs=0.1)


def test_pillar5_mesoscale_downscaling():
    """Verify high-resolution grid expansion and topographic lapse-rate cooling."""
    coarse = np.ones((10, 10)) * 290.0
    fine = downscale_regional_grid(coarse, scale_factor=2)
    assert fine.shape == (20, 20)
    np.testing.assert_allclose(fine, 290.0)
    
    # Elevation peak in center of 2000m (2 km) -> should cause ~13 K cooling
    elev = np.zeros((20, 20))
    elev[10, 10] = 2000.0
    fine_elev = downscale_regional_grid(coarse, scale_factor=2, elevation_highres=elev, lapse_rate_k_per_km=6.5)
    assert fine_elev[10, 10] < fine[10, 10] - 10.0


def test_pillar6_data_assimilation_increments():
    """Verify observation operator innovation and localized increment generation."""
    lats = np.linspace(45, 35, 11)
    lons = np.linspace(10, 20, 11)
    background = np.ones((11, 11)) * 290.0
    
    # Single observation at center (lat=40, lon=15) reporting 295.0 K (+5 K warm anomaly)
    obs = [{"lat": 40.0, "lon": 15.0, "value": 295.0}]
    
    da_result = run_point_observation_assimilation(
        background, lats, lons, obs, influence_radius_deg=2.0, observation_error_std=0.1
    )
    
    assert len(da_result["innovations"]) == 1
    assert da_result["innovations"][0]["innovation"] == pytest.approx(5.0, abs=0.01)
    # Increment at observation point should be positive
    center_r = np.argmin(np.abs(lats - 40.0))
    center_c = np.argmin(np.abs(lons - 15.0))
    assert da_result["analysis_increment"][center_r, center_c] > 3.0
    assert da_result["analysis_field"][center_r, center_c] > background[center_r, center_c]
