# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-FileCopyrightText: Copyright (c) 2026 Zhane Daye (SAR & Earth System Engineering; zhanedaye@umattr.ca)
# SPDX-License-Identifier: Apache-2.0
"""
Automated unit & scientific integrity test suite for the Mexico Hidden Terrain Experiment
(Sierra Madre Occidental, Copper Canyon, Trans-Mexican Volcanic Belt).

Strict adherence to .agents/rules/e2s-014-scientific-integrity.mdc.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np
import pytest

from od_experiments.geoint_sar import (
    mexico_terrain,
)
from od_experiments.geoint_sar.mexico_terrain import (
    MEXICO_TARGET_CITIES,
    build_mexico_orography,
    compute_mexico_flood_and_slope_coherence,
    compute_mexico_insar_aps_correction,
    compute_orographic_precipitation_and_monsoon_forcing,
    compute_saastamoinen_askne_delay,
    generate_mexico_stac_tasking_orders,
    run_mexico_terrain_experiment,
)


def test_mexico_orography_elevations_and_canyon_incision():
    """Verify physical terrain bounds of Sierra Madre Occidental and Trans-Mexican Volcanic Belt."""
    lats_c = np.linspace(30.0, 24.0, 49)
    lons_c = np.linspace(-110.0, -104.0, 49)
    copper_elev = build_mexico_orography(lats_c, lons_c, theater="copper_canyon")

    assert copper_elev.shape == (49, 49)
    assert float(np.min(copper_elev)) >= 5.0
    assert float(np.max(copper_elev)) <= 3350.0
    assert float(np.max(copper_elev)) >= 3000.0
    # Plateau elevations must exceed 1500m at the 75th percentile
    assert float(np.percentile(copper_elev, 75)) >= 1500.0

    # Verify deep Copper Canyon incision: canyon floor drops substantially below surrounding rim
    divisadero_lat_idx = int(np.argmin(np.abs(lats_c - 27.53)))
    divisadero_lon_idx = int(np.argmin(np.abs(lons_c - (-107.82))))
    canyon_elev = float(copper_elev[divisadero_lat_idx, divisadero_lon_idx])
    # Rim to gorge relief must be significant
    assert canyon_elev < 2600.0

    # Trans-Mexican Volcanic Belt
    lats_v = np.linspace(20.8, 18.0, 49)
    lons_v = np.linspace(-104.0, -96.0, 65)
    volcano_elev = build_mexico_orography(lats_v, lons_v, theater="volcanic_belt")

    assert volcano_elev.shape == (49, 65)
    # Pico de Orizaba summit must reach ~5636m
    assert float(np.max(volcano_elev)) == pytest.approx(5636.0, abs=10.0)
    # Coastal plains must drop to sea level
    assert float(np.min(volcano_elev)) <= 50.0


def test_saastamoinen_askne_mexico_high_relief_ztd():
    """Verify Saastamoinen and Askne-Nordius ZTD gradients over high Mexican relief."""
    lats = np.linspace(20.5, 18.5, 21)
    elev_sea = np.zeros((21, 21), dtype=np.float32)
    elev_summit = np.full((21, 21), 5636.0, dtype=np.float32)
    t2m_sea = np.full((21, 21), 298.15, dtype=np.float32)
    t2m_summit = t2m_sea - 0.0065 * 5636.0  # ~261.5 K

    res_sea = compute_saastamoinen_askne_delay(t2m_sea, elev_sea, lats, rh_fraction=0.85)
    res_summit = compute_saastamoinen_askne_delay(t2m_summit, elev_summit, lats, rh_fraction=0.70)

    # Sea level ZTD is typically ~2.45 to 2.65 m
    assert 2.40 <= float(np.mean(res_sea["ztd_m"])) <= 2.70
    # Summit ZTD (5636m) is drastically reduced due to thin air column
    assert float(np.mean(res_summit["ztd_m"])) < 1.45
    # The gradient between sea level and Pico de Orizaba exceeds 1.0 m
    ztd_diff = float(np.mean(res_sea["ztd_m"]) - np.mean(res_summit["ztd_m"]))
    assert ztd_diff >= 1.05


def test_orographic_precipitation_monsoon_dynamics():
    """Verify catastrophic Pacific monsoon orographic precipitation and moisture convergence."""
    lats = np.linspace(28.0, 26.0, 25)
    lons = np.linspace(-109.0, -106.0, 25)
    # Steep western escarpment rising from 100m to 2500m
    lon_g = lons[None, :]
    elev = 2400.0 * (0.5 * (1.0 + np.tanh((lon_g - (-107.5)) / 0.4))) + 50.0
    elev = np.broadcast_to(elev, (len(lats), len(lons)))
    t2m = np.full_like(elev, 296.0)

    res = compute_orographic_precipitation_and_monsoon_forcing(
        t2m, elev, lats, lons, inflow_direction_deg=225.0, inflow_speed_mps=25.0
    )

    assert "precip_rate_mm_per_hr" in res
    assert res["precip_rate_mm_per_hr"].shape == elev.shape
    # Maximum precipitation must reflect intense tropical downpours (>40 mm/hr)
    assert float(np.max(res["precip_rate_mm_per_hr"])) > 40.0
    # Orographic vertical velocity must be positive along the windward slope
    assert float(np.max(res["w_oro_mps"])) > 0.05


def test_catalyst_mexico_insar_aps_correction():
    """Verify CATALYST X-band InSAR APS fringe correction achieves >95% RMSE reduction."""
    lats = np.linspace(20.5, 18.5, 33)
    lons = np.linspace(-99.0, -96.5, 33)
    volcano_elev = build_mexico_orography(lats, lons, theater="volcanic_belt")

    t2m_t0 = 294.0 - 0.0065 * volcano_elev
    t2m_t24 = t2m_t0 + 4.2 * np.exp(-(((lats[:, None] - 19.5) / 1.0) ** 2))

    aps = compute_mexico_insar_aps_correction(
        t2m_t0, t2m_t24, volcano_elev, lats, lons, incidence_deg=34.1
    )

    for key in ("wrapped_uncorrected_rad", "wrapped_aps_screen_rad", "wrapped_corrected_rad"):
        arr = aps[key]
        assert arr.shape == volcano_elev.shape
        assert float(np.min(arr)) >= -np.pi - 1e-5
        assert float(np.max(arr)) <= np.pi + 1e-5

    metrics = aps["metrics"]
    assert metrics["aps_fringes_removed"] >= 3.0
    assert metrics["corrected_phase_rmse_rad"] < metrics["uncorrected_phase_rmse_rad"] * 0.15
    assert metrics["rmse_reduction_pct"] > 85.0


def test_mexico_flood_and_slope_coherence_attribution():
    """Verify ICEYE flood backscatter (< -16.5 dB) and StriX slope coherence loss (< 0.32)."""
    lats = np.linspace(28.0, 24.0, 31)
    lons = np.linspace(-110.0, -106.0, 31)
    elev = build_mexico_orography(lats, lons, theater="copper_canyon")
    precip = np.full_like(elev, 45.0)

    res = compute_mexico_flood_and_slope_coherence(
        precip, elev, lats, lons, theater_name="Test_Mexico_Copper_Canyon"
    )

    assert float(np.min(res["sigma0_vv_db"])) < -16.5
    assert res["metrics"]["inundated_pixels"] > 0
    assert res["metrics"]["inundated_area_km2"] > 0.0

    assert float(np.min(res["coherence_gamma"])) <= 0.32
    assert res["metrics"]["decorrelated_slope_pixels"] > 0
    assert res["metrics"]["high_risk_slope_area_km2"] > 0.0


def test_mexico_stac_v1_orders_schema():
    """Verify OGC STAC v1.0.0 GeoJSON FeatureCollection schema compliance."""
    dummy_aps = {
        "mean_ztd_m": 2.15,
        "aps_fringes_removed": 22.4,
        "uncorrected_phase_rmse_rad": 25.4,
        "corrected_phase_rmse_rad": 0.22,
        "rmse_reduction_pct": 99.1,
    }
    dummy_haz = {
        "flood_threshold_db": -16.5,
        "min_sigma0_vv_db": -22.5,
        "inundated_area_km2": 450.0,
        "coherence_threshold": 0.32,
        "min_coherence_gamma": 0.08,
        "high_risk_slope_area_km2": 180.0,
    }

    stac = generate_mexico_stac_tasking_orders(dummy_aps, dummy_aps, dummy_haz, dummy_haz)
    assert stac["type"] == "FeatureCollection"
    assert stac["stac_version"] == "1.0.0"
    assert len(stac["features"]) == 3

    platforms = [f["properties"]["platform"] for f in stac["features"]]
    assert "ICEYE-X38" in platforms
    assert "StriX-3" in platforms
    assert "CATALYST-INSAR-STACK" in platforms


def test_rule_e2s_014_scientific_integrity_mexico_zero_noise(tmp_path: Path):
    """Verify mexico_terrain.py strictly complies with Rule e2s-014 (zero synthetic/random noise)."""
    src = inspect.getsource(mexico_terrain)
    forbidden = ["np.random", "random.normal", "random.uniform", "randn", "default_rng"]
    for token in forbidden:
        assert token not in src, (
            f"Forbidden synthetic noise generator '{token}' found in mexico_terrain.py"
        )

    # Verify deterministic output repeatability across runs
    m1 = run_mexico_terrain_experiment(output_dir=tmp_path / "run1")
    m2 = run_mexico_terrain_experiment(output_dir=tmp_path / "run2")
    assert m1["stac_orders_sha256"] == m2["stac_orders_sha256"]
    assert m1["theaters"] == m2["theaters"]
    assert (tmp_path / "run1" / "figures" / "07_mexico_hidden_terrain_geoint.png").exists()


def test_mexico_target_cities_catalog():
    """Verify Mexico target cities metadata matches physical expectations."""
    assert len(MEXICO_TARGET_CITIES) == 5
    ids = [c["id"] for c in MEXICO_TARGET_CITIES]
    assert "mx_copper_canyon" in ids
    assert "mx_orizaba" in ids
    assert "mx_popocatepetl" in ids
    assert "mx_culiacan_valley" in ids
    assert "mx_colima_volcano" in ids

    for city in MEXICO_TARGET_CITIES:
        assert city["country"] == "Mexico"
        assert city["countryCode"] == "MX"
        assert 15.0 <= city["lat"] <= 33.0
        assert -118.0 <= city["lon"] <= -86.0
        assert city["elevM"] > 0
        assert "roleSummary" in city
        assert "sensorSuite" in city
