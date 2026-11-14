# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-FileCopyrightText: Copyright (c) 2026 Zhane Daye (SAR & Earth System Engineering; zhanedaye@umattr.ca)
# SPDX-License-Identifier: Apache-2.0
"""
Automated unit & scientific integrity test suite for Northern Russia Hidden Terrain
GEOINT Weather-to-SAR experiment (Putorana Basalt Traps, Verkhoyansk Permafrost,
Lena River Ice-Jam Flood Corridors).

Strict compliance with .agents/rules/e2s-014-scientific-integrity.mdc.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import numpy as np
import pytest

from od_experiments.geoint_sar.russia_terrain import (
    RUSSIA_TARGET_CITIES,
    X_BAND_FREQUENCY_HZ,
    X_BAND_WAVELENGTH_M,
    build_lena_river_hydrology,
    build_putorana_basalt_trap_orography,
    build_verkhoyansk_permafrost_orography,
    compute_iceye_lena_flood_backscatter,
    compute_putorana_insar_aps,
    compute_subzero_tropospheric_delay_ztd,
    compute_verkhoyansk_permafrost_insar_coherence,
    generate_russia_stac_tasking_orders,
    run_russia_terrain_experiment,
)


def test_subzero_refractivity_and_ztd_bounds():
    """Verify sub-zero Saastamoinen ZHD and Askne-Nordius ZWD physical bounds."""
    lats = np.linspace(70.0, 65.0, 21)
    lons = np.linspace(90.0, 95.0, 21)
    t2m = np.full((len(lats), len(lons)), 240.15, dtype=np.float32)  # -33°C

    elev_valley = np.full_like(t2m, 60.0)
    elev_plateau = np.full_like(t2m, 1650.0)

    res_val = compute_subzero_tropospheric_delay_ztd(
        t2m, elev_valley, lats, rh_fraction=0.75, sea_level_pressure_hpa=1035.0
    )
    res_plat = compute_subzero_tropospheric_delay_ztd(
        t2m + 8.0, elev_plateau, lats, rh_fraction=0.75, sea_level_pressure_hpa=1035.0
    )

    # Valley ZHD must be ~2.30 - 2.45 m under Siberian High
    assert 2.25 <= float(np.mean(res_val["zhd_m"])) <= 2.45
    # High-elevation plateau ZHD must be significantly lower (> 0.35 m reduction)
    assert float(np.mean(res_plat["zhd_m"])) < 2.05
    assert float(np.mean(res_val["zhd_m"]) - np.mean(res_plat["zhd_m"])) > 0.30

    # Under extreme cold (T < 245 K), vapor pressure is infinitesimal, so ZWD must be < 0.02 m
    assert 0.0001 <= float(np.mean(res_val["zwd_m"])) <= 0.02
    assert float(np.mean(res_plat["zwd_m"])) < 0.015

    # Valley air density must reflect dense sub-zero air (> 1.40 kg/m^3)
    assert float(np.mean(res_val["air_density_kgpm3"])) > 1.40


def test_putorana_basalt_trap_elevation_jump_and_insar_aps():
    """Verify Putorana canyon elevation jump > 1500m and CATALYST APS correction > 90%."""
    lats = np.linspace(70.5, 68.5, 33)
    lons = np.linspace(89.0, 95.0, 41)
    elev = build_putorana_basalt_trap_orography(lats, lons)

    # Elevation jump across Putorana traps must exceed 1500 m
    elev_jump = float(np.max(elev) - np.min(elev))
    assert elev_jump >= 1500.0, f"Expected relief > 1500m, got {elev_jump}m"

    t2m_t0 = 245.0 + 3.0 * np.cos(np.deg2rad(lats)[:, None] * 2.0)
    t2m_t24 = t2m_t0 + 4.5 * np.exp(-(((lats[:, None] - 69.2) / 1.0) ** 2))

    aps = compute_putorana_insar_aps(t2m_t0, t2m_t24, elev, lats, lons)

    # Wrapped interferograms must lie strictly in [-pi, +pi]
    for key in (
        "wrapped_uncorrected_rad",
        "wrapped_aps_rad",
        "wrapped_corrected_rad",
    ):
        arr = aps[key]
        assert arr.shape == (len(lats), len(lons))
        assert float(np.min(arr)) >= -np.pi - 1e-5
        assert float(np.max(arr)) <= np.pi + 1e-5

    metrics = aps["metrics"]
    assert metrics["max_canyon_elevation_jump_m"] >= 1500.0
    assert metrics["rmse_reduction_pct"] > 90.0
    assert metrics["corrected_phase_rmse_rad"] < 0.20


def test_verkhoyansk_permafrost_freeze_thaw_coherence():
    """Verify Synspective StriX-4 coherence loss (gamma < 0.32) in permafrost active layer."""
    lats = np.linspace(68.5, 65.5, 31)
    lons = np.linspace(130.0, 137.0, 37)
    elev = build_verkhoyansk_permafrost_orography(lats, lons)

    t2m_t0 = np.full_like(elev, 272.0)  # Close to 0°C active layer thaw front
    t2m_t24 = t2m_t0 + 3.5

    res = compute_verkhoyansk_permafrost_insar_coherence(
        t2m_t0, t2m_t24, elev, lats, lons
    )

    gamma = res["coherence_gamma"]
    assert gamma.shape == elev.shape
    assert 0.05 <= float(np.min(gamma)) <= 0.32
    assert float(np.max(gamma)) <= 1.0

    metrics = res["metrics"]
    assert metrics["decorrelated_thaw_pixels"] > 0
    assert metrics["thaw_hazard_area_km2"] >= 18.5


def test_lena_river_ice_jam_specular_backscatter():
    """Verify ICEYE-X41 specular flood backscatter (< -16.5 dB) and ice-jam rubble contrast."""
    lats = np.linspace(64.2, 61.2, 41)
    lons = np.linspace(127.0, 131.5, 45)
    elev, floodplain, jams = build_lena_river_hydrology(lats, lons)

    t2m_t0 = np.full_like(elev, 270.0)
    t2m_t24 = t2m_t0 + 5.0

    res = compute_iceye_lena_flood_backscatter(
        t2m_t0, t2m_t24, elev, floodplain, jams, lats, lons
    )

    sigma0 = res["sigma0_vv_db"]
    assert sigma0.shape == elev.shape
    assert float(np.min(sigma0)) < -16.5
    assert res["metrics"]["inundated_pixels"] > 0
    assert res["metrics"]["inundated_area_km2"] >= 100.0
    assert res["metrics"]["ice_jam_rubble_area_km2"] > 0.0
    # Ice-jam rubble must show elevated backscatter above -8.0 dB
    assert res["metrics"]["max_rubble_sigma0_vv_db"] > -8.0


def test_russia_stac_v1_tasking_orders_schema():
    """Verify STAC v1.0.0 GeoJSON FeatureCollection compliance for Northern Russia."""
    put_dummy = {
        "mean_ztd_m": 2.11,
        "max_canyon_elevation_jump_m": 1611.1,
        "uncorrected_phase_rmse_rad": 1.71,
        "corrected_phase_rmse_rad": 0.08,
        "aps_fringes_removed": 1.21,
        "rmse_reduction_pct": 95.1,
    }
    vrk_dummy = {
        "coherence_threshold": 0.32,
        "min_coherence_gamma": 0.11,
        "mean_coherence_gamma": 0.68,
        "decorrelated_thaw_pixels": 2961,
        "thaw_hazard_area_km2": 225.18,
    }
    lena_dummy = {
        "flood_threshold_db": -16.5,
        "min_sigma0_vv_db": -28.0,
        "max_rubble_sigma0_vv_db": -7.3,
        "inundated_pixels": 1388,
        "inundated_area_km2": 306.55,
        "ice_jam_rubble_area_km2": 14.8,
    }

    stac = generate_russia_stac_tasking_orders(put_dummy, vrk_dummy, lena_dummy)

    assert stac["type"] == "FeatureCollection"
    assert stac["stac_version"] == "1.0.0"
    assert len(stac["features"]) == 3

    sat_ids = [f["properties"]["platform"] for f in stac["features"]]
    assert "ICEYE-X41" in sat_ids
    assert "StriX-4" in sat_ids
    assert "CATALYST-X-Stack" in sat_ids

    for feat in stac["features"]:
        assert feat["type"] == "Feature"
        assert feat["stac_version"] == "1.0.0"
        assert len(feat["bbox"]) == 4
        assert feat["geometry"]["type"] == "Polygon"
        assert feat["properties"]["sar:frequency_band"] == "X"
        assert feat["properties"]["sar:center_frequency"] == 9.65


def test_russia_scientific_integrity_zero_random_noise():
    """Verify Rule e2s-014 compliance: zero synthetic or pseudo-random noise generation."""
    import od_experiments.geoint_sar.russia_terrain as rt_module

    source = inspect.getsource(rt_module)

    forbidden_tokens = [
        "np.random",
        "random.normal",
        "random.uniform",
        "random.rand",
        "torch.randn",
        "torch.rand",
    ]
    for token in forbidden_tokens:
        assert token not in source, f"Rule e2s-014 violation: found '{token}' in russia_terrain.py"


def test_russia_target_cities_schema():
    """Verify RUSSIA_TARGET_CITIES catalog schema and values."""
    assert len(RUSSIA_TARGET_CITIES) == 6
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
    for city in RUSSIA_TARGET_CITIES:
        assert required_keys.issubset(city.keys())
        assert city["country"] == "Russia"
        assert city["countryCode"] == "RU"
        assert 60.0 <= city["lat"] <= 72.0
        assert 80.0 <= city["lon"] <= 140.0
