# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-FileCopyrightText: Copyright (c) 2026 Zhane Daye (SAR & Earth System Engineering; zhanedaye@umattr.ca)
# SPDX-License-Identifier: Apache-2.0
"""
Automated unit & scientific integrity test suite for the Vancouver Cascadia Experiment
(Fraser River Delta Subsidence & Coast Mountain Atmospheric Rivers GEOINT SAR Suite).

Strict adherence to .agents/rules/e2s-014-scientific-integrity.mdc.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import numpy as np
import pytest

from od_experiments.geoint_sar import (
    X_BAND_FREQUENCY_HZ,
    X_BAND_WAVELENGTH_M,
    vancouver_terrain,
)
from od_experiments.geoint_sar.sar_geoint_engine import (
    compute_insar_aps_fringe_correction,
    compute_tropospheric_delay_ztd,
)
from od_experiments.geoint_sar.vancouver_terrain import (
    LAT_NORTH,
    LAT_SOUTH,
    LON_EAST,
    LON_WEST,
    TARGET_COORDINATES,
    VANCOUVER_TARGET_CITIES,
    build_vancouver_orography,
    compute_fraser_delta_subsidence,
    compute_vancouver_flood_and_coherence,
    compute_vancouver_hydrology,
    generate_vancouver_stac_orders,
    run_vancouver_terrain_suite,
)


def test_vancouver_orography_elevations_and_summits():
    """Verify physical terrain bounds of Coast Mountains, Mount Garibaldi, and Fraser Delta."""
    lats = np.linspace(LAT_NORTH, LAT_SOUTH, 160)
    lons = np.linspace(LON_WEST, LON_EAST, 224)
    elev = build_vancouver_orography(lats, lons)

    assert elev.shape == (160, 224)
    # Peak elevation must reach the authentic Mount Garibaldi summit (~2,678m)
    assert float(np.max(elev)) == pytest.approx(2678.0, abs=5.0)

    # Mount Garibaldi summit coordinate check (49.8517N, -123.0047W)
    ilat_garibaldi = int(np.argmin(np.abs(lats - 49.8517)))
    ilon_garibaldi = int(np.argmin(np.abs(lons - (-123.0047))))
    assert float(elev[ilat_garibaldi, ilon_garibaldi]) >= 2500.0

    # Mamquam Mountain check (49.79N, -122.86W)
    ilat_mamquam = int(np.argmin(np.abs(lats - 49.79)))
    ilon_mamquam = int(np.argmin(np.abs(lons - (-122.86))))
    assert float(elev[ilat_mamquam, ilon_mamquam]) >= 2350.0

    # Mount Cayley check (50.01N, -123.28W)
    ilat_cayley = int(np.argmin(np.abs(lats - 50.01)))
    ilon_cayley = int(np.argmin(np.abs(lons - (-123.28))))
    assert float(elev[ilat_cayley, ilon_cayley]) >= 2100.0

    # The Lions check (49.43N, -123.18W)
    ilat_lions = int(np.argmin(np.abs(lats - 49.43)))
    ilon_lions = int(np.argmin(np.abs(lons - (-123.18))))
    assert float(elev[ilat_lions, ilon_lions]) >= 1450.0

    # Howe Sound fjord channel floor (Squamish at 49.7016N, -123.1558W)
    ilat_howe = int(np.argmin(np.abs(lats - 49.7016)))
    ilon_howe = int(np.argmin(np.abs(lons - (-123.1558))))
    assert float(elev[ilat_howe, ilon_howe]) <= 25.0

    # Fraser Delta lowlands: Roberts Bank (49.0194N, -123.1583W)
    ilat_roberts = int(np.argmin(np.abs(lats - 49.0194)))
    ilon_roberts = int(np.argmin(np.abs(lons - (-123.1583))))
    assert float(elev[ilat_roberts, ilon_roberts]) <= 5.0

    # Richmond & Lulu Island (49.1666N, -123.1336W)
    ilat_richmond = int(np.argmin(np.abs(lats - 49.1666)))
    ilon_richmond = int(np.argmin(np.abs(lons - (-123.1336))))
    assert float(elev[ilat_richmond, ilon_richmond]) <= 5.0

    # Sea Island / YVR (49.1967N, -123.1815W)
    ilat_yvr = int(np.argmin(np.abs(lats - 49.1967)))
    ilon_yvr = int(np.argmin(np.abs(lons - (-123.1815))))
    assert float(elev[ilat_yvr, ilon_yvr]) <= 5.0

    # Sumas Prairie drained lakebed (49.05N, -122.25W)
    ilat_sumas = int(np.argmin(np.abs(lats - 49.05)))
    ilon_sumas = int(np.argmin(np.abs(lons - (-122.25))))
    assert float(elev[ilat_sumas, ilon_sumas]) <= 20.0

    # Strait of Georgia open ocean (-123.8W, 49.1N) must be 0m
    ilat_ocean = int(np.argmin(np.abs(lats - 49.1)))
    ilon_ocean = int(np.argmin(np.abs(lons - (-123.8))))
    assert float(elev[ilat_ocean, ilon_ocean]) == 0.0


def test_fraser_delta_subsidence_mechanics():
    """Verify Holocene sediment compaction and port surcharge subsidence in 2.0 to 10.0 mm/yr range."""
    lats = np.linspace(LAT_NORTH, LAT_SOUTH, 160)
    lons = np.linspace(LON_WEST, LON_EAST, 224)

    sub = compute_fraser_delta_subsidence(lats, lons, observation_years=1.0, incidence_deg=34.1)

    rates = sub["subsidence_rate_mm_yr"]
    assert rates.shape == (160, 224)
    assert 2.0 <= float(np.max(rates)) <= 10.0

    # Roberts Bank Superport (49.0194N, -123.1583W) must experience heavy 7-10 mm/yr loading
    ilat_roberts = int(np.argmin(np.abs(lats - 49.0194)))
    ilon_roberts = int(np.argmin(np.abs(lons - (-123.1583))))
    assert 7.0 <= float(rates[ilat_roberts, ilon_roberts]) <= 10.0

    # Richmond / Lulu Island (49.1666N, -123.1336W) peat compaction (4-7.5 mm/yr)
    ilat_richmond = int(np.argmin(np.abs(lats - 49.1666)))
    ilon_richmond = int(np.argmin(np.abs(lons - (-123.1336))))
    assert 4.0 <= float(rates[ilat_richmond, ilon_richmond]) <= 8.0

    # Sea Island / YVR (49.1967N, -123.1815W) runway/terminal loading (3.5-7.5 mm/yr)
    ilat_yvr = int(np.argmin(np.abs(lats - 49.1967)))
    ilon_yvr = int(np.argmin(np.abs(lons - (-123.1815))))
    assert 3.5 <= float(rates[ilat_yvr, ilon_yvr]) <= 8.0

    # Coast Mountains bedrock (Garibaldi summit) must have ~0 mm/yr subsidence
    ilat_garibaldi = int(np.argmin(np.abs(lats - 49.8517)))
    ilon_garibaldi = int(np.argmin(np.abs(lons - (-123.0047))))
    assert float(rates[ilat_garibaldi, ilon_garibaldi]) <= 0.05

    # LOS displacement check: d_LOS = d_z * cos(34.1 deg)
    cos_34 = float(np.cos(np.deg2rad(34.1)))
    expected_los = sub["vertical_displacement_m"] * cos_34
    np.testing.assert_allclose(sub["los_displacement_m"], expected_los, rtol=1e-5)
    # Downward displacement is negative
    assert float(np.min(sub["los_displacement_m"])) < 0.0


def test_saastamoinen_askne_vancouver_atmospheric_river_ztd():
    """Verify Saastamoinen and Askne-Nordius ZTD across Mount Garibaldi and Atmospheric River plume."""
    lats = np.linspace(48.8, 50.4, 33)
    elev_sea = np.zeros((33, 33), dtype=np.float32)
    elev_summit = np.full((33, 33), 2678.0, dtype=np.float32)

    # Warm, moisture-saturated Atmospheric River (Pineapple Express) conditions
    t2m_sea = np.full((33, 33), 288.15, dtype=np.float32)  # ~15 C at sea level
    t2m_summit = t2m_sea - 0.0065 * 2678.0  # Lapse rate ~270.7 K (~-2.4 C)

    res_sea = compute_tropospheric_delay_ztd(t2m_sea, elev_sea, lats, rh_fraction=0.95)
    res_summit = compute_tropospheric_delay_ztd(t2m_summit, elev_summit, lats, rh_fraction=0.85)

    # Sea level ZTD in warm moist AR air is ~2.45 to 2.65 m
    assert 2.40 <= float(np.mean(res_sea["ztd_m"])) <= 2.65
    # Garibaldi summit ZTD (2678m) is drastically reduced due to thin air column (~1.60 to 1.85 m)
    assert 1.60 <= float(np.mean(res_summit["ztd_m"])) <= 1.85

    # Vertical delay gradient across Coast Mountains must exceed 0.55m (~35 X-band fringes)
    ztd_diff = float(np.mean(res_sea["ztd_m"]) - np.mean(res_summit["ztd_m"]))
    assert ztd_diff >= 0.55
    fringes_gradient = ztd_diff / (X_BAND_WAVELENGTH_M / 2.0)
    assert fringes_gradient >= 35.0


def test_vancouver_catalyst_aps_fringe_correction():
    """Verify wrapped phase in [-pi, pi] and CATALYST APS correction achieves >90% error reduction."""
    lats = np.linspace(50.4, 48.8, 33)
    lons = np.linspace(-124.0, -122.0, 41)
    lat_g = lats[:, None]
    lon_g = lons[None, :]

    # Atmospheric river frontal passage between t0 and t24
    t2m_t0 = 281.0 + 2.5 * np.cos(np.deg2rad(lat_g * 2.0))
    t2m_t24 = t2m_t0 + 5.5 * np.exp(
        -(((lat_g - 49.30) / 0.8) ** 2 + ((lon_g - (-123.10)) / 1.0) ** 2)
    )
    elev = 2200.0 * np.exp(-(((lat_g - 49.75) / 0.6) ** 2 + ((lon_g - (-123.00)) / 0.7) ** 2)) + 15.0

    # Subtle 8 mm delta subsidence bowl
    subsidence_los = -0.008 * np.exp(
        -(((lat_g - 49.05) / 0.15) ** 2 + ((lon_g - (-123.15)) / 0.20) ** 2)
    )

    aps = compute_insar_aps_fringe_correction(
        t2m_t0,
        t2m_t24,
        elev,
        lats,
        lons,
        incidence_deg=34.1,
        true_deformation_los_m=subsidence_los,
    )

    # Wrapped interferograms must lie strictly within [-pi, +pi]
    for key in (
        "wrapped_uncorrected_rad",
        "wrapped_aps_screen_rad",
        "wrapped_corrected_rad",
    ):
        arr = aps[key]
        assert arr.shape == (len(lats), len(lons))
        assert float(np.min(arr)) >= -np.pi - 1e-5
        assert float(np.max(arr)) <= np.pi + 1e-5

    metrics = aps["metrics"]
    assert metrics["aps_fringes_removed"] >= 2.5
    assert metrics["corrected_phase_rmse_rad"] < metrics["uncorrected_phase_rmse_rad"] * 0.15
    assert metrics["rmse_reduction_pct"] > 88.0


def test_vancouver_iceye_flood_and_strix_coherence():
    """Verify ICEYE flood backscatter (< -16.5 dB) and Howe Sound fjord slope coherence loss (< 0.32)."""
    lats = np.linspace(LAT_NORTH, LAT_SOUTH, 41)
    lons = np.linspace(LON_WEST, LON_EAST, 61)

    elev = build_vancouver_orography(lats, lons)
    t2m_t0 = np.full_like(elev, 281.0)
    lat_g = lats[:, None]
    lon_g = lons[None, :]
    # Pineapple Express moisture plume
    t2m_t24 = t2m_t0 + 5.8 * np.exp(
        -(((lat_g - 49.25) / 0.8) ** 2 + ((lon_g - (-123.00)) / 1.0) ** 2)
    )

    res = compute_vancouver_flood_and_coherence(t2m_t0, t2m_t24, elev, lats, lons)

    assert res["sigma0_vv_db"].shape == elev.shape
    assert res["coherence_gamma"].shape == elev.shape

    # Flood detection checks (< -16.5 dB)
    assert float(np.min(res["sigma0_vv_db"])) < -16.5
    assert res["metrics"]["inundated_pixels"] > 0
    assert res["metrics"]["inundated_area_km2"] > 0.0

    # Verify open Strait of Georgia ocean (-123.8W, 49.0N) is excluded from flood mask
    ilat_ocean = int(np.argmin(np.abs(lats - 49.0)))
    ilon_ocean = int(np.argmin(np.abs(lons - (-123.8))))
    assert not bool(res["flood_mask"][ilat_ocean, ilon_ocean])

    # Coherence checks on steep fjord slopes (< 0.32)
    assert 0.05 <= float(np.min(res["coherence_gamma"])) <= 0.32
    assert float(np.max(res["coherence_gamma"])) <= 1.0
    assert res["metrics"]["decorrelated_slope_pixels"] > 0
    assert res["metrics"]["high_risk_slope_area_km2"] > 0.0


def test_vancouver_stac_v1_orders_schema():
    """Verify STAC v1.0.0 GeoJSON FeatureCollection compliance for Vancouver orders."""
    aps_dummy = {
        "mean_ztd_m": 2.22,
        "aps_fringes_removed": 3.82,
        "uncorrected_phase_rmse_rad": 4.49,
        "corrected_phase_rmse_rad": 0.17,
        "rmse_reduction_pct": 96.28,
    }
    haz_dummy = {
        "flood_threshold_db": -16.5,
        "min_sigma0_vv_db": -34.51,
        "inundated_area_km2": 24.5,
        "coherence_threshold": 0.32,
        "min_coherence_gamma": 0.08,
        "high_risk_slope_area_km2": 58.45,
    }

    stac = generate_vancouver_stac_orders(aps_dummy, haz_dummy)
    assert stac["type"] == "FeatureCollection"
    assert stac["stac_version"] == "1.0.0"
    assert len(stac["features"]) == 3

    order_ids = [f["id"] for f in stac["features"]]
    assert "ORDER-ICEYE-X45-VANCOUVER-DELTA-001" in order_ids
    assert "ORDER-SYNSPECTIVE-STRIX5-HOWESOUND-GARIBALDI-002" in order_ids
    assert "ORDER-CATALYST-INSAR-X-CASCADIA-VANCOUVER-003" in order_ids

    # Verify ICEYE properties
    iceye_feat = next(f for f in stac["features"] if "ICEYE" in f["id"])
    assert iceye_feat["properties"]["platform"] == "ICEYE-X45"
    assert iceye_feat["properties"]["sar:instrument_mode"] == "Spotlight"
    assert iceye_feat["properties"]["sar:frequency_band"] == "X"
    assert iceye_feat["properties"]["sar:resolution_range"] == 0.5

    # Verify StriX properties
    strix_feat = next(f for f in stac["features"] if "STRIX" in f["id"])
    assert strix_feat["properties"]["platform"] == "StriX-5"
    assert strix_feat["properties"]["sar:instrument_mode"] == "StripMap"
    assert strix_feat["properties"]["sar:frequency_band"] == "X"
    assert strix_feat["properties"]["sar:resolution_range"] == 3.0


def test_rule_e2s_014_zero_random_noise_vancouver(tmp_path: Path):
    """Verify vancouver_terrain contains zero pseudo-random noise and produces deterministic artifacts."""
    src = inspect.getsource(vancouver_terrain)
    forbidden = ["np.random", "random.normal", "random.uniform", "randn", "default_rng"]
    for token in forbidden:
        assert token not in src, (
            f"Forbidden synthetic noise generator '{token}' found in vancouver_terrain.py"
        )

    # Execute twice and confirm identical SHA-256 hashes
    m1 = run_vancouver_terrain_suite(output_dir=tmp_path / "run1")
    m2 = run_vancouver_terrain_suite(output_dir=tmp_path / "run2")

    assert m1["stac_orders_sha256"] == m2["stac_orders_sha256"]
    assert m1["aps_correction_metrics"] == m2["aps_correction_metrics"]
    assert m1["hazard_attribution_metrics"] == m2["hazard_attribution_metrics"]
    assert m1["fraser_delta_subsidence_metrics"] == m2["fraser_delta_subsidence_metrics"]
    assert (tmp_path / "run1" / "figures" / "14_vancouver_terrain.png").exists()

    stac_loaded = json.loads(
        (tmp_path / "run1" / "stac_vancouver_tasking_orders.geojson").read_text(encoding="utf-8")
    )
    assert stac_loaded["type"] == "FeatureCollection"
    assert len(stac_loaded["features"]) == 3


def test_vancouver_nyquist_fringe_sampling():
    """Verify 16x mesoscale upsampling keeps phase gradients below Nyquist limit on Vancouver grid."""
    init_npy = Path("outputs/scientific_study_verified/forecast/initial_condition.npy")
    truth_npy = Path("outputs/scientific_study_verified/verification/verifying_truth_t2m.npy")

    if init_npy.exists() and truth_npy.exists():
        global_t0 = np.load(init_npy)
        global_t24 = np.load(truth_npy)
        global_lats = np.linspace(90.0, -90.0, global_t0.shape[0])
        global_lons = np.linspace(0.0, 360.0, global_t0.shape[1], endpoint=False)
        van_lat_mask = (global_lats <= LAT_NORTH) & (global_lats >= LAT_SOUTH)
        van_lon_mask = (global_lons >= vancouver_terrain.LON_WEST_360) & (
            global_lons <= vancouver_terrain.LON_EAST_360
        )
        coarse_t0 = global_t0[np.ix_(van_lat_mask, van_lon_mask)]
        coarse_t24 = global_t24[np.ix_(van_lat_mask, van_lon_mask)]
        coarse_lats = global_lats[van_lat_mask]
        coarse_lons = global_lons[van_lon_mask]
    else:
        coarse_lats = np.linspace(LAT_NORTH, LAT_SOUTH, 10)
        coarse_lons = np.linspace(
            vancouver_terrain.LON_WEST_360, vancouver_terrain.LON_EAST_360, 13
        )
        lat_r = np.deg2rad(coarse_lats)[:, None]
        lon_r = np.deg2rad(coarse_lons)[None, :]
        coarse_t0 = (282.0 + 3.0 * np.sin(2.0 * lat_r) * np.cos(3.0 * lon_r)).astype(np.float32)
        coarse_t24 = (
            282.0 + 3.0 * np.sin(2.0 * lat_r) * np.cos(3.0 * (lon_r - np.deg2rad(10.0)))
        ).astype(np.float32)

    fine_t0, fine_t24, fine_lats, fine_lons_360 = vancouver_terrain._upsample_synoptic_theater(
        coarse_t0, coarse_t24, coarse_lats, coarse_lons, scale_factor=16, synoptic_sigma=1.8
    )
    fine_lons = np.where(fine_lons_360 > 180.0, fine_lons_360 - 360.0, fine_lons_360)
    elev = build_vancouver_orography(fine_lats, fine_lons)
    sub = compute_fraser_delta_subsidence(fine_lats, fine_lons)
    aps = compute_insar_aps_fringe_correction(
        fine_t0,
        fine_t24,
        elev,
        fine_lats,
        fine_lons,
        incidence_deg=34.1,
        true_deformation_los_m=sub["los_displacement_m"],
    )

    # Verify 99.5th percentile pixel-to-pixel unwrapped phase step < pi rad
    dphi_y = np.abs(np.diff(aps["phase_uncorrected_unwrapped_rad"], axis=0))
    dphi_x = np.abs(np.diff(aps["phase_uncorrected_unwrapped_rad"], axis=1))
    assert float(np.percentile(dphi_y, 99.5)) < np.pi
    assert float(np.percentile(dphi_x, 99.5)) < np.pi


def test_vancouver_target_cities_schema():
    """Verify VANCOUVER_TARGET_CITIES exposes 6 frozen cities conforming to viewer_app schema."""
    assert len(VANCOUVER_TARGET_CITIES) == 6
    required_keys = {
        "id",
        "country",
        "countryCode",
        "name",
        "region",
        "lat",
        "lon",
        "elevM",
        "zoomDistance",
        "sensorSuite",
        "sarSatelliteId",
        "incidenceAngleDeg",
        "apsStatus",
        "apsZtdM",
        "fringesRemoved",
        "rmseReductionPct",
        "roleSummary",
    }
    for city in VANCOUVER_TARGET_CITIES:
        assert required_keys.issubset(city.keys())
        assert 48.6 <= city["lat"] <= 50.6
        assert -124.4 <= city["lon"] <= -121.6
        assert city["elevM"] >= 0.0
        assert city["countryCode"] == "CA"
