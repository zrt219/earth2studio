# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-FileCopyrightText: Copyright (c) 2026 Zhane Daye (SAR & Earth System Engineering; zhanedaye@umattr.ca)
# SPDX-License-Identifier: Apache-2.0
"""
Automated unit & scientific integrity test suite for the South Africa Hidden Terrain Experiment
(Drakensberg Escarpment & Lesotho Highlands, Cape Fold Belt, Tugela/Durban Coastal Corridor).

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
    south_africa_terrain,
)
from od_experiments.geoint_sar.sar_geoint_engine import (
    compute_insar_aps_fringe_correction,
    compute_tropospheric_delay_ztd,
)
from od_experiments.geoint_sar.south_africa_terrain import (
    LAT_NORTH,
    LAT_SOUTH,
    LON_EAST,
    LON_WEST,
    SOUTH_AFRICA_TARGET_CITIES,
    TARGET_COORDINATES,
    build_south_africa_orography,
    compute_south_africa_flood_and_coherence,
    compute_south_africa_hydrology,
    generate_south_africa_stac_orders,
    run_south_africa_terrain_suite,
)


def test_south_africa_orography_elevations_and_summits():
    """Verify physical terrain bounds of Drakensberg, Lesotho Highlands, and Cape Fold Belt."""
    lats = np.linspace(LAT_NORTH, LAT_SOUTH, 296)
    lons = np.linspace(LON_WEST, LON_EAST, 488)
    elev = build_south_africa_orography(lats, lons)

    assert elev.shape == (296, 488)
    # Peak elevation must reach the authentic Thabana Ntlenyana summit (~3482m)
    assert float(np.max(elev)) == pytest.approx(3482.0, abs=5.0)

    # Thabana Ntlenyana coordinate check (-29.47S, 29.27E)
    ilat_thabana = int(np.argmin(np.abs(lats - (-29.47))))
    ilon_thabana = int(np.argmin(np.abs(lons - 29.27)))
    assert float(elev[ilat_thabana, ilon_thabana]) >= 3200.0

    # Mont-aux-Sources coordinate check (-28.75S, 28.88E)
    ilat_mas = int(np.argmin(np.abs(lats - (-28.75))))
    ilon_mas = int(np.argmin(np.abs(lons - 28.88)))
    assert float(elev[ilat_mas, ilon_mas]) >= 2800.0

    # Cape Fold Belt / Swartberg range peak check (-33.36S, 21.36E)
    ilat_swart = int(np.argmin(np.abs(lats - (-33.36))))
    ilon_swart = int(np.argmin(np.abs(lons - 21.36)))
    assert float(elev[ilat_swart, ilon_swart]) >= 1800.0

    # Coastal plain check (Durban -29.86S, 31.00E) must drop to low coastal elevations
    ilat_durban = int(np.argmin(np.abs(lats - (-29.86))))
    ilon_durban = int(np.argmin(np.abs(lons - 31.00)))
    assert float(elev[ilat_durban, ilon_durban]) <= 80.0

    # Tugela river mouth check (-29.22S, 31.45E)
    ilat_tugela = int(np.argmin(np.abs(lats - (-29.22))))
    ilon_tugela = int(np.argmin(np.abs(lons - 31.45)))
    assert float(elev[ilat_tugela, ilon_tugela]) <= 60.0


def test_saastamoinen_askne_drakensberg_escarpment_ztd():
    """Verify Saastamoinen and Askne-Nordius ZTD gradients across the 3482m Drakensberg Escarpment."""
    lats = np.linspace(-28.0, -31.0, 31)
    elev_sea = np.zeros((31, 31), dtype=np.float32)
    elev_summit = np.full((31, 31), 3482.0, dtype=np.float32)

    t2m_sea = np.full((31, 31), 295.15, dtype=np.float32)  # ~22 C in Durban
    t2m_summit = t2m_sea - 0.0065 * 3482.0  # Lapse rate ~272.5 K (~-0.6 C)

    res_sea = compute_tropospheric_delay_ztd(t2m_sea, elev_sea, lats, rh_fraction=0.82)
    res_summit = compute_tropospheric_delay_ztd(t2m_summit, elev_summit, lats, rh_fraction=0.65)

    # Sea level ZTD in subtropical maritime air is ~2.45 to 2.65 m
    assert 2.40 <= float(np.mean(res_sea["ztd_m"])) <= 2.65
    # Drakensberg summit ZTD (3482m) is drastically reduced due to thin air column (~1.55 to 1.75 m)
    assert 1.50 <= float(np.mean(res_summit["ztd_m"])) <= 1.75

    # Vertical delay gradient across the escarpment must exceed 0.75m (~48 X-band fringes)
    ztd_diff = float(np.mean(res_sea["ztd_m"]) - np.mean(res_summit["ztd_m"]))
    assert ztd_diff >= 0.75
    fringes_gradient = ztd_diff / (X_BAND_WAVELENGTH_M / 2.0)
    assert fringes_gradient >= 48.0


def test_south_africa_catalyst_aps_fringe_correction():
    """Verify X-band wrapped phase is in [-pi, pi] and CATALYST APS correction reduces RMSE >90%."""
    lats = np.linspace(-28.0, -31.0, 33)
    lons = np.linspace(28.0, 32.0, 41)
    lat_g = lats[:, None]
    lon_g = lons[None, :]

    # Realistic temperature change and orography across the Drakensberg & KZN
    t2m_t0 = 288.0 + 3.0 * np.cos(np.deg2rad(lat_g * 3.0))
    t2m_t24 = t2m_t0 + 4.2 * np.exp(-(((lat_g - (-29.5)) / 1.5) ** 2 + ((lon_g - 30.5) / 1.8) ** 2))
    elev = 2600.0 * np.exp(-(((lat_g - (-29.3)) / 1.0) ** 2 + ((lon_g - 29.3) / 0.8) ** 2)) + 50.0

    aps = compute_insar_aps_fringe_correction(
        t2m_t0, t2m_t24, elev, lats, lons, incidence_deg=34.1
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
    assert metrics["aps_fringes_removed"] >= 3.0
    assert metrics["corrected_phase_rmse_rad"] < metrics["uncorrected_phase_rmse_rad"] * 0.10
    assert metrics["rmse_reduction_pct"] > 90.0


def test_south_africa_iceye_flood_and_strix_coherence():
    """Verify ICEYE flood backscatter (< -16.5 dB) and steep Drakensberg slope coherence loss (< 0.32)."""
    lats = np.linspace(-28.0, -31.0, 41)
    lons = np.linspace(28.0, 32.0, 61)

    elev = build_south_africa_orography(lats, lons)
    t2m_t0 = np.full_like(elev, 290.0)
    # Severe coastal cutoff-low moisture and temperature advection
    lat_g = lats[:, None]
    lon_g = lons[None, :]
    t2m_t24 = t2m_t0 + 5.5 * np.exp(
        -(((lat_g - (-29.5)) / 1.2) ** 2 + ((lon_g - 31.0) / 1.4) ** 2)
    )

    res = compute_south_africa_flood_and_coherence(t2m_t0, t2m_t24, elev, lats, lons)

    assert res["sigma0_vv_db"].shape == elev.shape
    assert res["coherence_gamma"].shape == elev.shape

    # Flood detection checks
    assert float(np.min(res["sigma0_vv_db"])) < -16.5
    assert res["metrics"]["inundated_pixels"] > 0
    assert res["metrics"]["inundated_area_km2"] > 0.0

    # Verify open Indian ocean (32.0E, -30.0S) is excluded from flood mask
    ilat_ocean = int(np.argmin(np.abs(lats - (-30.0))))
    ilon_ocean = int(np.argmin(np.abs(lons - 32.0)))
    assert not bool(res["flood_mask"][ilat_ocean, ilon_ocean])

    # Coherence checks on steep escarpment slopes
    assert 0.05 <= float(np.min(res["coherence_gamma"])) <= 0.32
    assert float(np.max(res["coherence_gamma"])) <= 1.0
    assert res["metrics"]["decorrelated_slope_pixels"] > 0
    assert res["metrics"]["high_risk_slope_area_km2"] > 0.0


def test_south_africa_stac_v1_orders_schema():
    """Verify STAC v1.0.0 GeoJSON FeatureCollection compliance for South Africa orders."""
    aps_dummy = {
        "mean_ztd_m": 2.28,
        "aps_fringes_removed": 10.42,
        "uncorrected_phase_rmse_rad": 15.74,
        "corrected_phase_rmse_rad": 0.18,
        "rmse_reduction_pct": 98.86,
    }
    haz_dummy = {
        "flood_threshold_db": -16.5,
        "min_sigma0_vv_db": -28.86,
        "inundated_area_km2": 18.5,
        "coherence_threshold": 0.32,
        "min_coherence_gamma": 0.08,
        "high_risk_slope_area_km2": 826.78,
    }

    stac = generate_south_africa_stac_orders(aps_dummy, haz_dummy)
    assert stac["type"] == "FeatureCollection"
    assert stac["stac_version"] == "1.0.0"
    assert len(stac["features"]) == 3

    order_ids = [f["id"] for f in stac["features"]]
    assert "ORDER-ICEYE-X42-SOUTHAFRICA-DURBAN-001" in order_ids
    assert "ORDER-SYNSPECTIVE-STRIX4-DRAKENSBERG-002" in order_ids
    assert "ORDER-CATALYST-INSAR-X-CAPEFOLD-003" in order_ids

    # Verify ICEYE properties
    iceye_feat = next(f for f in stac["features"] if "ICEYE" in f["id"])
    assert iceye_feat["properties"]["platform"] == "ICEYE-X42"
    assert iceye_feat["properties"]["sar:instrument_mode"] == "Spotlight"
    assert iceye_feat["properties"]["sar:frequency_band"] == "X"
    assert iceye_feat["properties"]["sar:resolution_range"] == 0.5

    # Verify StriX properties
    strix_feat = next(f for f in stac["features"] if "STRIX" in f["id"])
    assert strix_feat["properties"]["platform"] == "StriX-4"
    assert strix_feat["properties"]["sar:instrument_mode"] == "StripMap"
    assert strix_feat["properties"]["sar:frequency_band"] == "X"
    assert strix_feat["properties"]["sar:resolution_range"] == 3.0


def test_rule_e2s_014_zero_random_noise_south_africa(tmp_path: Path):
    """Verify south_africa_terrain contains zero pseudo-random noise and produces deterministic artifacts."""
    src = inspect.getsource(south_africa_terrain)
    forbidden = ["np.random", "random.normal", "random.uniform", "randn", "default_rng"]
    for token in forbidden:
        assert token not in src, (
            f"Forbidden synthetic noise generator '{token}' found in south_africa_terrain.py"
        )

    # Execute twice and confirm identical SHA-256 hashes
    m1 = run_south_africa_terrain_suite(output_dir=tmp_path / "run1")
    m2 = run_south_africa_terrain_suite(output_dir=tmp_path / "run2")

    assert m1["stac_orders_sha256"] == m2["stac_orders_sha256"]
    assert m1["aps_correction_metrics"] == m2["aps_correction_metrics"]
    assert m1["hazard_attribution_metrics"] == m2["hazard_attribution_metrics"]
    assert (tmp_path / "run1" / "figures" / "07_geoint_south_africa_hidden_terrain.png").exists()

    stac_loaded = json.loads(
        (tmp_path / "run1" / "stac_south_africa_tasking_orders.geojson").read_text(encoding="utf-8")
    )
    assert stac_loaded["type"] == "FeatureCollection"
    assert len(stac_loaded["features"]) == 3


def test_south_africa_nyquist_fringe_sampling():
    """Verify 8x mesoscale upsampling keeps phase gradients below Nyquist limit on South Africa grid."""
    init_npy = Path("outputs/scientific_study_verified/forecast/initial_condition.npy")
    truth_npy = Path("outputs/scientific_study_verified/verification/verifying_truth_t2m.npy")

    if init_npy.exists() and truth_npy.exists():
        global_t0 = np.load(init_npy)
        global_t24 = np.load(truth_npy)
        global_lats = np.linspace(90.0, -90.0, global_t0.shape[0])
        global_lons = np.linspace(0.0, 360.0, global_t0.shape[1], endpoint=False)
        sa_lat_mask = (global_lats <= LAT_NORTH) & (global_lats >= LAT_SOUTH)
        sa_lon_mask = (global_lons >= LON_WEST) & (global_lons <= LON_EAST)
        coarse_t0 = global_t0[np.ix_(sa_lat_mask, sa_lon_mask)]
        coarse_t24 = global_t24[np.ix_(sa_lat_mask, sa_lon_mask)]
        coarse_lats = global_lats[sa_lat_mask]
        coarse_lons = global_lons[sa_lon_mask]
    else:
        coarse_lats = np.linspace(LAT_NORTH, LAT_SOUTH, 37)
        coarse_lons = np.linspace(LON_WEST, LON_EAST, 61)
        lat_r = np.deg2rad(coarse_lats)[:, None]
        lon_r = np.deg2rad(coarse_lons)[None, :]
        coarse_t0 = (285.0 + 4.0 * np.sin(2.0 * lat_r) * np.cos(3.0 * lon_r)).astype(np.float32)
        coarse_t24 = (
            285.0 + 4.0 * np.sin(2.0 * lat_r) * np.cos(3.0 * (lon_r - np.deg2rad(10.0)))
        ).astype(np.float32)

    fine_t0, fine_t24, fine_lats, fine_lons = south_africa_terrain._upsample_synoptic_theater(
        coarse_t0, coarse_t24, coarse_lats, coarse_lons, scale_factor=8, synoptic_sigma=1.8
    )
    elev = build_south_africa_orography(fine_lats, fine_lons)
    aps = compute_insar_aps_fringe_correction(
        fine_t0, fine_t24, elev, fine_lats, fine_lons, incidence_deg=34.1
    )

    # Verify 99.5th percentile pixel-to-pixel unwrapped phase step < pi rad
    dphi_y = np.abs(np.diff(aps["phase_uncorrected_unwrapped_rad"], axis=0))
    dphi_x = np.abs(np.diff(aps["phase_uncorrected_unwrapped_rad"], axis=1))
    assert float(np.percentile(dphi_y, 99.5)) < np.pi
    assert float(np.percentile(dphi_x, 99.5)) < np.pi


def test_south_africa_target_cities_schema():
    """Verify SOUTH_AFRICA_TARGET_CITIES exposes 6 frozen cities conforming to viewer_app schema."""
    assert len(SOUTH_AFRICA_TARGET_CITIES) == 6
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
    for city in SOUTH_AFRICA_TARGET_CITIES:
        assert required_keys.issubset(city.keys())
        assert -35.0 <= city["lat"] <= -26.0
        assert 18.0 <= city["lon"] <= 33.0
        assert city["elevM"] >= 0.0
        assert city["countryCode"] in {"ZA", "LS"}
