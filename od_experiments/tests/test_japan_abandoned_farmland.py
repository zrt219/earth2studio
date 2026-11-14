# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-FileCopyrightText: Copyright (c) 2026 Zhane Daye (SAR & Earth System Engineering; zhanedaye@umattr.ca)
# SPDX-License-Identifier: Apache-2.0
"""
Automated unit & scientific integrity test suite for the Japan Abandoned Farmland Experiment
(Kousaku-Houkichi / Satoyama: Niigata Chuetsu, Nagano Chikuma, Shikoku Mountains).

Strict adherence to .agents/rules/e2s-014-scientific-integrity.mdc:
  - Zero synthetic or pseudo-random noise generation permitted.
  - Deterministic physics and verified operational GFS tensors.
  - Monotonic coordinate validation and proper geospatial plotting orientations.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np
import pytest

from od_experiments.geoint_sar import (
    japan_abandoned_farmland,
)
from od_experiments.geoint_sar.japan_abandoned_farmland import (
    JAPAN_FARMLAND_TARGET_CITIES,
    X_BAND_HALF_WAVELENGTH_M,
    X_BAND_WAVELENGTH_M,
    build_japan_farmland_orography,
    compute_farmland_abandonment_and_vegetation_succession,
    compute_japan_insar_aps_correction,
    compute_japan_storm_precipitation,
    compute_saastamoinen_askne_delay_japan,
    compute_strix_coherence_and_backscatter,
    compute_terrace_levee_collapse_and_slope_failure,
    generate_japan_farmland_stac_tasking_orders,
    run_japan_abandoned_farmland_experiment,
)


def test_japan_farmland_orography_elevations_and_terrace_relief():
    """Verify physical terrain bounds of Niigata Chuetsu / Nagano and Shikoku Hills."""
    # Niigata Chuetsu & Nagano Valley theater
    lats_c = np.linspace(37.6, 36.2, 49)
    lons_c = np.linspace(137.8, 139.2, 49)
    chuetsu_elev = build_japan_farmland_orography(lats_c, lons_c, theater="niigata_nagano")

    assert chuetsu_elev.shape == (49, 49)
    assert float(np.min(chuetsu_elev)) >= 8.0
    # Mount Myoko peak reaches ~2454m
    assert float(np.max(chuetsu_elev)) <= 2460.0
    assert float(np.max(chuetsu_elev)) >= 2200.0
    # Terraced plateau elevations (250m - 750m) represent middle percentiles
    assert 200.0 <= float(np.median(chuetsu_elev)) <= 900.0

    # Shikoku Central Mountains & Iya Valley gorge theater
    lats_s = np.linspace(34.3, 33.5, 41)
    lons_s = np.linspace(133.4, 134.6, 45)
    shikoku_elev = build_japan_farmland_orography(lats_s, lons_s, theater="shikoku_hills")

    assert shikoku_elev.shape == (41, 45)
    # Mount Ishizuchi summit ~1982m, Mount Tsurugi ~1955m
    assert float(np.max(shikoku_elev)) <= 1985.0
    assert float(np.max(shikoku_elev)) >= 1850.0
    # Coastal margins and river gorges drop below 150m
    assert float(np.min(shikoku_elev)) <= 150.0

    # Verify deep canyon incision of Iya Valley gorge
    iya_lat_idx = int(np.argmin(np.abs(lats_s - 33.85)))
    iya_lon_idx = int(np.argmin(np.abs(lons_s - 133.88)))
    canyon_elev = float(shikoku_elev[iya_lat_idx, iya_lon_idx])
    # Gorge floor is deeply incised below surrounding 1800m peaks
    assert canyon_elev < 1400.0


def test_saastamoinen_askne_japan_tropospheric_ztd():
    """Verify Saastamoinen and Askne-Nordius ZTD gradients over high Japanese mountain relief."""
    lats = np.linspace(37.5, 36.5, 21)
    elev_sea = np.full((21, 21), 15.0, dtype=np.float32)
    elev_summit = np.full((21, 21), 2450.0, dtype=np.float32)
    t2m_sea = np.full((21, 21), 295.15, dtype=np.float32)
    t2m_summit = t2m_sea - 0.0065 * 2435.0  # Lapse rate cooling (~279.3 K)

    res_sea = compute_saastamoinen_askne_delay_japan(t2m_sea, elev_sea, lats, rh_fraction=0.85)
    res_summit = compute_saastamoinen_askne_delay_japan(t2m_summit, elev_summit, lats, rh_fraction=0.75)

    # Sea level ZTD is typically ~2.40 to 2.65 m
    assert 2.38 <= float(np.mean(res_sea["ztd_m"])) <= 2.65
    # High alpine summit (2450m) ZTD is drastically thinner (~1.80 to 2.05 m)
    assert float(np.mean(res_summit["ztd_m"])) < 2.05
    # Stratified ZTD differential between coastal plain and summit exceeds 0.40 m (~26 X-band fringes)
    ztd_diff = float(np.mean(res_sea["ztd_m"]) - np.mean(res_summit["ztd_m"]))
    assert ztd_diff >= 0.40


def test_japan_storm_precipitation_and_moisture_convergence():
    """Verify severe Baiu-frontal and typhoon orographic precipitation dynamics."""
    lats = np.linspace(37.5, 36.5, 25)
    lons = np.linspace(138.0, 139.0, 25)
    # Windward escarpment rising from 50m to 1600m
    lat_g = lats[:, None]
    elev = 1500.0 * (0.5 * (1.0 + np.tanh((37.1 - lat_g) / 0.15))) + 50.0
    elev = np.broadcast_to(elev, (len(lats), len(lons)))
    t2m = np.full_like(elev, 293.5)

    res = compute_japan_storm_precipitation(
        t2m, elev, lats, lons, storm_type="baiu_front", inflow_direction_deg=215.0, inflow_speed_mps=25.0
    )

    precip = res["precip_rate_mm_per_hr"]
    w_oro = res["w_oro_mps"]

    assert precip.shape == (25, 25)
    # Peak precipitation exceeds 50 mm/hr on windward mountain slopes
    assert float(np.max(precip)) >= 50.0
    # Positive vertical orographic uplift where wind ascends escarpment
    assert float(np.max(w_oro)) > 0.05
    # Specific saturation humidity in realistic range (10 - 20 g/kg)
    assert 8.0 <= float(np.mean(res["q_sat_g_per_kg"])) <= 25.0


def test_farmland_abandonment_and_vegetation_succession():
    """Verify depopulation-driven farmland abandonment and bamboo/scrub succession."""
    lats = np.linspace(37.4, 36.6, 30)
    lons = np.linspace(138.2, 139.0, 30)

    # Flat valley floor (slope 2°, elev 50m) vs steep agricultural terrace (slope 22°, elev 420m)
    elev_valley = np.full((30, 30), 50.0, dtype=np.float32)
    slope_valley = np.full((30, 30), 2.0, dtype=np.float32)

    elev_terrace = np.full((30, 30), 420.0, dtype=np.float32)
    slope_terrace = np.full((30, 30), 22.0, dtype=np.float32)

    res_valley = compute_farmland_abandonment_and_vegetation_succession(
        elev_valley, slope_valley, lats, lons, depopulation_index=0.60
    )
    res_terrace = compute_farmland_abandonment_and_vegetation_succession(
        elev_terrace, slope_terrace, lats, lons, depopulation_index=0.60
    )

    # Valley floors have near-zero abandonment probability
    assert float(np.mean(res_valley["abandonment_prob"])) < 0.10
    assert not np.any(res_valley["abandoned_terrace_mask"])

    # Steep mountain terraces have high abandonment and bamboo/scrub succession
    assert float(np.mean(res_terrace["abandonment_prob"])) >= 0.40
    assert float(np.mean(res_terrace["bamboo_invasion_fraction"])) > 0.30
    assert float(np.mean(res_terrace["levee_degradation_index"])) > 0.35
    assert np.all(res_terrace["abandoned_terrace_mask"])


def test_terrace_levee_collapse_and_shallow_slope_stability():
    """Verify infinite-slope limit equilibrium factor of safety (FS) and levee collapse."""
    lats = np.linspace(37.3, 36.7, 20)
    lons = np.linspace(138.3, 138.9, 20)
    elev = np.full((20, 20), 400.0, dtype=np.float32)
    slope = np.full((20, 20), 24.0, dtype=np.float32)

    # Moderate rain (10 mm/hr) on maintained terrace
    precip_light = np.full((20, 20), 10.0, dtype=np.float32)
    abandon_maintained = {
        "abandonment_prob": np.zeros((20, 20), dtype=np.float32),
        "terrace_topography_factor": np.full((20, 20), 0.8, dtype=np.float32),
        "bamboo_invasion_fraction": np.zeros((20, 20), dtype=np.float32),
        "scrub_invasion_fraction": np.zeros((20, 20), dtype=np.float32),
        "levee_degradation_index": np.zeros((20, 20), dtype=np.float32),
        "maintained_terrace_mask": np.ones((20, 20), dtype=bool),
        "abandoned_terrace_mask": np.zeros((20, 20), dtype=bool),
    }

    stab_maintained = compute_terrace_levee_collapse_and_slope_failure(
        precip_light, elev, slope, abandon_maintained
    )
    # Maintained terrace with intact compacted clay bunds is stable (FS > 1.25)
    assert float(np.mean(stab_maintained["factor_of_safety"])) >= 1.25
    assert not np.any(stab_maintained["shallow_failure_mask"])
    assert not np.any(stab_maintained["levee_breach_mask"])

    # Torrential storm (65 mm/hr) on degraded abandoned terrace
    precip_storm = np.full((20, 20), 65.0, dtype=np.float32)
    abandon_degraded = {
        "abandonment_prob": np.full((20, 20), 0.85, dtype=np.float32),
        "terrace_topography_factor": np.full((20, 20), 0.9, dtype=np.float32),
        "bamboo_invasion_fraction": np.full((20, 20), 0.80, dtype=np.float32),
        "scrub_invasion_fraction": np.full((20, 20), 0.60, dtype=np.float32),
        "levee_degradation_index": np.full((20, 20), 0.85, dtype=np.float32),
        "maintained_terrace_mask": np.zeros((20, 20), dtype=bool),
        "abandoned_terrace_mask": np.ones((20, 20), dtype=bool),
    }

    stab_degraded = compute_terrace_levee_collapse_and_slope_failure(
        precip_storm, elev, slope, abandon_degraded
    )
    # Saturated degraded riser experiences shallow failure (FS < 1.0) and levee collapse
    assert float(np.mean(stab_degraded["factor_of_safety"])) < 1.05
    assert np.any(stab_degraded["shallow_failure_mask"])
    assert np.any(stab_degraded["levee_breach_mask"])


def test_strix_coherence_tracking_and_temporal_decorrelation():
    """Verify Synspective StriX X-band coherence tracking and high temporal decorrelation (gamma < 0.25)."""
    lats = np.linspace(37.4, 36.8, 25)
    lons = np.linspace(138.4, 139.0, 25)
    elev = np.full((25, 25), 450.0, dtype=np.float32)
    slope = np.full((25, 25), 20.0, dtype=np.float32)
    precip = np.full((25, 25), 35.0, dtype=np.float32)

    abandonment_map = {
        "abandonment_prob": np.full((25, 25), 0.75, dtype=np.float32),
        "terrace_topography_factor": np.full((25, 25), 0.85, dtype=np.float32),
        "bamboo_invasion_fraction": np.full((25, 25), 0.70, dtype=np.float32),
        "scrub_invasion_fraction": np.full((25, 25), 0.50, dtype=np.float32),
        "levee_degradation_index": np.full((25, 25), 0.65, dtype=np.float32),
        "maintained_terrace_mask": np.zeros((25, 25), dtype=bool),
        "abandoned_terrace_mask": np.ones((25, 25), dtype=bool),
    }

    # Half of grid has active levee failure
    failure_mask = np.zeros((25, 25), dtype=bool)
    failure_mask[:12, :] = True
    stability_map = {
        "factor_of_safety": np.full((25, 25), 0.85, dtype=np.float32),
        "shallow_failure_mask": failure_mask,
        "levee_breach_mask": failure_mask,
    }

    res = compute_strix_coherence_and_backscatter(
        precip, elev, slope, abandonment_map, stability_map, lats, lons
    )

    coherence = res["coherence_gamma"]
    # Coherence on overgrown abandoned farmland exhibits high temporal decorrelation (gamma < 0.25)
    assert float(np.mean(coherence)) < 0.25
    # On active failure/breach scars, coherence collapses below 0.15
    assert float(np.mean(coherence[failure_mask])) < 0.15
    # Verify polarimetric backscatter ranges (sigma0_vv in [-20, 0] dB, sigma0_vh in [-25, -2] dB)
    assert -22.0 <= float(np.mean(res["sigma0_vv_db"])) <= -2.0
    assert -26.0 <= float(np.mean(res["sigma0_vh_db"])) <= -4.0


def test_catalyst_japan_insar_aps_correction():
    """Verify CATALYST X-Band repeat-pass InSAR APS correction over high-relief Japanese terrain."""
    lats = np.linspace(37.5, 36.5, 33)
    lons = np.linspace(138.0, 139.0, 33)
    elev = build_japan_farmland_orography(lats, lons, theater="niigata_nagano")

    t2m_t0 = np.full((33, 33), 292.0, dtype=np.float32)
    # Frontal passage with warm advection (+2.8 K)
    t2m_t24 = t2m_t0 + 2.8

    aps_res = compute_japan_insar_aps_correction(
        t2m_t0, t2m_t24, elev, lats, lons, incidence_deg=34.1
    )

    metrics = aps_res["metrics"]
    # Wavelength must match X-band (~3.11 cm)
    assert metrics["wavelength_cm"] == pytest.approx(3.1067, abs=1e-3)
    assert metrics["carrier_frequency_ghz"] == 9.65
    # Stratified relief must generate fringes removed
    assert metrics["aps_fringes_removed"] >= 1.0
    # CATALYST correction must reduce phase RMSE by > 90%
    assert metrics["rmse_reduction_pct"] >= 92.0
    assert metrics["corrected_phase_rmse_rad"] < metrics["uncorrected_phase_rmse_rad"]


def test_japan_farmland_stac_v1_orders_schema():
    """Verify OGC / STAC v1.0.0 compliance of Japanese farmland tasking orders."""
    mock_aps = {
        "metrics": {
            "mean_ztd_m": 2.215,
            "aps_fringes_removed": 34.80,
            "uncorrected_phase_rmse_rad": 12.20,
            "corrected_phase_rmse_rad": 0.20,
            "rmse_reduction_pct": 98.72,
        }
    }
    mock_hazard = {
        "coherence_threshold": 0.25,
        "metrics": {
            "min_coherence_gamma": 0.06,
            "abandoned_farmland_area_km2": 39.78,
            "shallow_failure_and_breach_area_km2": 27.99,
        },
    }

    stac = generate_japan_farmland_stac_tasking_orders(
        mock_aps, mock_aps, mock_hazard, mock_hazard
    )

    assert stac["type"] == "FeatureCollection"
    assert stac["stac_version"] == "1.0.0"
    assert len(stac["features"]) == 4

    order_ids = [f["id"] for f in stac["features"]]
    assert "ORDER-SYNSPECTIVE-STRIX3-JAPAN-CHUETSU-001" in order_ids
    assert "ORDER-SYNSPECTIVE-STRIX4-JAPAN-NAGANO-002" in order_ids
    assert "ORDER-SYNSPECTIVE-STRIX1-JAPAN-SHIKOKU-003" in order_ids
    assert "ORDER-CATALYST-INSAR-JAPAN-FARMLAND-004" in order_ids

    for feat in stac["features"]:
        assert feat["type"] == "Feature"
        assert feat["stac_version"] == "1.0.0"
        assert len(feat["bbox"]) == 4
        assert feat["geometry"]["type"] == "Polygon"
        # Bbox inside Japan territory
        assert 128.0 <= feat["bbox"][0] <= 145.0
        assert 30.0 <= feat["bbox"][1] <= 42.0
        assert feat["properties"]["sar:frequency_band"] == "X"


def test_rule_e2s_014_zero_random_noise_japan():
    """Verify Rule e2s-014 compliance: zero synthetic or pseudo-random noise in experiment module."""
    src = inspect.getsource(japan_abandoned_farmland)

    # Strictly forbidden stochastic generators
    forbidden_terms = [
        "np.random",
        "random.normal",
        "random.uniform",
        "random.randn",
        "random.random",
        "torch.randn",
        "torch.rand",
    ]
    for term in forbidden_terms:
        assert term not in src, f"Violation of Rule e2s-014: '{term}' detected in japan_abandoned_farmland.py"


def test_japan_farmland_target_cities_schema():
    """Verify Japanese target cities catalog conforms to exact telemetry standards."""
    assert len(JAPAN_FARMLAND_TARGET_CITIES) == 6

    ids = [c["id"] for c in JAPAN_FARMLAND_TARGET_CITIES]
    assert len(set(ids)) == 6, "Target city IDs must be strictly unique"

    for city in JAPAN_FARMLAND_TARGET_CITIES:
        assert city["country"] == "Japan"
        assert city["countryCode"] == "JP"
        # Coordinates must lie inside Japan
        assert 30.0 <= city["lat"] <= 42.0
        assert 128.0 <= city["lon"] <= 145.0
        assert city["elevM"] > 0
        assert "StriX" in city["sensorSuite"]
        assert "CATALYST" in city["apsStatus"]
        assert city["rmseReductionPct"] >= 95.0


def test_run_japan_abandoned_farmland_experiment_end_to_end(tmp_path: Path):
    """Verify end-to-end execution of Japan Abandoned Farmland experiment."""
    manifest = run_japan_abandoned_farmland_experiment(output_dir=tmp_path)

    assert manifest["module"] == "od_experiments.geoint_sar.japan_abandoned_farmland"
    assert "Rule e2s-014 Certified" in manifest["compliance"]
    assert len(manifest["theaters"]) == 2
    assert len(manifest["target_cities"]) == 6

    # Verify output artifacts exist
    stac_file = Path(manifest["stac_orders_file"])
    fig_file = Path(manifest["figure"])
    manifest_file = tmp_path / "japan_abandoned_farmland_manifest.json"

    assert stac_file.exists()
    assert fig_file.exists()
    assert manifest_file.exists()
    assert len(manifest["stac_orders_sha256"]) == 64
    assert len(manifest["figure_sha256"]) == 64
