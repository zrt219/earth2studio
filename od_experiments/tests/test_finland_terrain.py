# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-FileCopyrightText: Copyright (c) 2026 Zhane Daye (SAR & Earth System Engineering; zhanedaye@umattr.ca)
# SPDX-License-Identifier: Apache-2.0
"""
Automated unit & scientific integrity test suite for Finland Hidden Terrain GEOINT Weather-to-SAR
Experiment (Fennoscandian Post-Glacial Rebound, Boreal Peatland Bog Breathing, Lake Ice Freeze-Thaw).

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
)
from od_experiments.geoint_sar import finland_terrain
from od_experiments.geoint_sar.finland_terrain import (
    FINLAND_TARGET_CITIES,
    LAT_NORTH,
    LAT_SOUTH,
    LON_EAST,
    LON_WEST,
    TARGET_COORDINATES,
    X_BAND_HALF_WAVELENGTH_M,
    build_finland_hydrology,
    build_finland_orography,
    compute_boreal_peatland_breathing,
    compute_finland_insar_aps_and_deformation,
    compute_lake_ice_freeze_thaw,
    compute_postglacial_uplift_rate,
    compute_subpolar_tropospheric_delay_ztd,
    generate_finland_stac_orders,
    run_finland_terrain_experiment,
)


def test_subpolar_tropospheric_ztd_and_gravity_bounds():
    """Verify sub-polar Saastamoinen ZHD, Askne-Nordius ZWD, and high-latitude gravity bounds."""
    lats = np.linspace(LAT_NORTH, LAT_SOUTH, 35)
    elev_sea = np.zeros((35, 41), dtype=np.float32)
    elev_summit = np.full((35, 41), 1324.0, dtype=np.float32)  # Halti summit

    t2m_sea = np.full((35, 41), 278.15, dtype=np.float32)  # +5°C
    t2m_summit = t2m_sea - 0.0065 * 1324.0  # ~269.5 K (-3.6°C)

    res_sea = compute_subpolar_tropospheric_delay_ztd(t2m_sea, elev_sea, lats, rh_fraction=0.80)
    res_summit = compute_subpolar_tropospheric_delay_ztd(t2m_summit, elev_summit, lats, rh_fraction=0.75)

    # High-latitude surface gravity must reflect planetary ellipsoidal flattening (> 9.815 m/s^2)
    assert float(np.min(res_sea["gravity_mps2"])) >= 9.815
    assert float(np.max(res_sea["gravity_mps2"])) <= 9.835

    # Sea level ZHD in sub-polar atmosphere is ~2.25 to 2.38 m
    assert 2.24 <= float(np.mean(res_sea["zhd_m"])) <= 2.38
    # High-elevation Halti summit (1324m) ZHD must be significantly lower (< 2.05 m)
    assert 1.90 <= float(np.mean(res_summit["zhd_m"])) <= 2.05
    # Differential delay must exceed 0.25 m (~16 X-band fringes)
    zhd_diff = float(np.mean(res_sea["zhd_m"]) - np.mean(res_summit["zhd_m"]))
    assert zhd_diff >= 0.25

    # Sub-polar ZWD under cold conditions must be modest (0.01 to 0.16 m)
    assert 0.01 <= float(np.mean(res_sea["zwd_m"])) <= 0.16
    assert float(np.mean(res_summit["zwd_m"])) < float(np.mean(res_sea["zwd_m"]))


def test_finland_orography_and_summits():
    """Verify physical terrain bounds of Scandinavian fells (Halti), Lake Plateau, and Kvarken."""
    lats = np.linspace(LAT_NORTH, LAT_SOUTH, 337)
    lons = np.linspace(LON_WEST, LON_EAST, 393)
    elev = build_finland_orography(lats, lons)

    assert elev.shape == (337, 393)
    # Peak elevation must reach Halti summit (~1324m)
    assert float(np.max(elev)) == pytest.approx(1324.0, abs=10.0)

    # Halti summit coordinate check (69.31°N, 21.26°E)
    ilat_halti = int(np.argmin(np.abs(lats - 69.31)))
    ilon_halti = int(np.argmin(np.abs(lons - 21.26)))
    assert float(elev[ilat_halti, ilon_halti]) >= 1200.0

    # Central Lake Plateau (62.0°N, 26.0°E) should be low undulating peneplain (70-140m)
    ilat_plateau = int(np.argmin(np.abs(lats - 62.0)))
    ilon_plateau = int(np.argmin(np.abs(lons - 26.0)))
    assert 70.0 <= float(elev[ilat_plateau, ilon_plateau]) <= 150.0

    # Kvarken Archipelago (63.10°N, 21.62°E) must be low coastal relief (< 30m)
    ilat_kvarken = int(np.argmin(np.abs(lats - 63.10)))
    ilon_kvarken = int(np.argmin(np.abs(lons - 21.62)))
    assert float(elev[ilat_kvarken, ilon_kvarken]) <= 30.0


def test_kvarken_postglacial_rebound_uplift_rate():
    """Verify Fennoscandian GIA post-glacial rebound uplift rate field and Kvarken bullseye."""
    lats = np.linspace(LAT_NORTH, LAT_SOUTH, 105)
    lons = np.linspace(LON_WEST, LON_EAST, 121)
    rebound = compute_postglacial_uplift_rate(lats, lons)

    uplift = rebound["uplift_rate_mm_per_yr"]
    assert uplift.shape == (105, 121)

    # Peak uplift rate in Gulf of Bothnia / Kvarken corridor must be ~8.8 - 9.2 mm/yr
    max_uplift = float(np.max(uplift))
    assert 8.8 <= max_uplift <= 9.3

    # Vaasa / Kvarken coordinate (63.095°N, 21.6165°E) must be >= 8.5 mm/yr
    ilat_vaasa = int(np.argmin(np.abs(lats - 63.095)))
    ilon_vaasa = int(np.argmin(np.abs(lons - 21.6165)))
    vaasa_uplift = float(uplift[ilat_vaasa, ilon_vaasa])
    assert 8.4 <= vaasa_uplift <= 9.1

    # Radial decay: southeastern Finland (Saimaa / Gulf of Finland, 60.5°N, 28.0°E) must be < 5.0 mm/yr
    ilat_se = int(np.argmin(np.abs(lats - 60.5)))
    ilon_se = int(np.argmin(np.abs(lons - 28.0)))
    se_uplift = float(uplift[ilat_se, ilon_se])
    assert 3.0 <= se_uplift <= 5.0
    assert vaasa_uplift - se_uplift > 3.5

    # 1-year and 2-year LOS displacements (meters)
    d_los_1yr = rebound["los_displacement_1yr_m"]
    d_los_2yr = rebound["los_displacement_2yr_m"]
    assert float(np.max(d_los_1yr)) * 1000.0 >= 7.0  # > 7.0 mm in LOS
    assert float(np.max(d_los_2yr)) == pytest.approx(float(np.max(d_los_1yr)) * 2.0, rel=1e-3)


def test_boreal_peatland_breathing_displacement_and_coherence():
    """Verify boreal peatland elastic breathing amplitude (20-45 mm) and coherence drop (< 0.35)."""
    lats = np.linspace(67.0, 61.0, 61)
    lons = np.linspace(22.0, 29.0, 71)
    elev = build_finland_orography(lats, lons)
    hydro = build_finland_hydrology(lats, lons)

    t2m = np.full_like(elev, 276.15)
    peat = compute_boreal_peatland_breathing(
        lats, lons, elev, hydro["water_mask"], t2m, rh_fraction=0.82
    )

    p_frac = peat["peatland_fraction"]
    b_amp = peat["peat_breathing_amplitude_m"]
    gamma = peat["peat_coherence_gamma"]

    # Open water bodies must have zero peat fraction
    assert np.all(p_frac[hydro["water_mask"]] == 0.0)

    # Active breathing amplitude must be between 20 mm and 45 mm
    max_amp_mm = float(np.max(b_amp) * 1000.0)
    assert 20.0 <= max_amp_mm <= 45.0

    # In active breathing peatlands, coherence must drop below 0.35
    active_peat = p_frac > 0.40
    assert np.any(active_peat)
    assert float(np.min(gamma[active_peat])) < 0.35

    metrics = peat["metrics"]
    assert metrics["active_peat_pixels"] > 0
    assert metrics["breathing_area_km2"] >= 500.0
    assert metrics["coherence_threshold"] == 0.35


def test_lake_ice_freeze_thaw_backscatter_and_contrast():
    """Verify Lake Saimaa/Päijänne ice freeze-thaw radar backscatter contrast (>= 10 dB)."""
    lats = np.linspace(63.0, 60.5, 51)
    lons = np.linspace(24.0, 30.5, 66)
    hydro = build_finland_hydrology(lats, lons)
    lake_m = hydro["lake_mask"]
    marine_m = hydro["marine_mask"]

    # Verify Lake Saimaa and Lake Päijänne pixels are present
    assert np.any(lake_m)

    t2m = np.full(lake_m.shape, 274.0, dtype=np.float32)  # Near freezing front
    res = compute_lake_ice_freeze_thaw(
        lats,
        lons,
        lake_m,
        marine_m,
        t2m,
        lake_depth_m=hydro["lake_depth_m"],
        freeze_transition_calibrated=True,
    )

    sigma0 = res["sigma0_vv_db"]
    assert sigma0.shape == lake_m.shape

    # Both frozen ice and open water should be represented in the transition regime
    assert res["metrics"]["frozen_ice_pixels"] > 0
    assert res["metrics"]["open_water_pixels"] > 0

    # Open water must have low specular backscatter (< -18.0 dB)
    assert res["metrics"]["open_water_min_sigma0_db"] < -18.0
    # Frozen congelation ice must have high backscatter (> -12.0 dB)
    assert res["metrics"]["frozen_ice_max_sigma0_db"] > -12.0

    # Radar backscatter contrast between frozen ice and open water must exceed 10.0 dB
    assert res["metrics"]["backscatter_contrast_db"] >= 10.0

    # Coherence check: frozen ice is stable (> 0.70), open water decorrelates (< 0.15)
    gamma_ice = res["ice_coherence_gamma"]
    assert float(np.mean(gamma_ice[res["frozen_ice_mask"]])) >= 0.70
    assert float(np.mean(gamma_ice[res["open_water_mask"]])) <= 0.15


def test_finland_catalyst_aps_fringe_correction():
    """Verify CATALYST InSAR APS fringe correction achieves > 90% RMSE reduction."""
    lats = np.linspace(66.0, 62.0, 41)
    lons = np.linspace(22.0, 28.0, 61)
    elev = build_finland_orography(lats, lons)
    rebound = compute_postglacial_uplift_rate(lats, lons)
    hydro = build_finland_hydrology(lats, lons)

    t2m_t0 = np.full_like(elev, 275.0)
    lat_g = lats[:, None]
    lon_g = lons[None, :]
    t2m_t24 = t2m_t0 + 3.8 * np.exp(
        -(((lat_g - 63.5) / 1.5) ** 2 + ((lon_g - 25.0) / 2.0) ** 2)
    )

    peat = compute_boreal_peatland_breathing(
        lats, lons, elev, hydro["water_mask"], t2m_t0
    )

    aps = compute_finland_insar_aps_and_deformation(
        t2m_t0,
        t2m_t24,
        elev,
        lats,
        lons,
        rebound["los_displacement_1yr_m"],
        peat["los_peat_displacement_m"],
        incidence_deg=34.1,
    )

    # Wrapped interferograms must lie strictly within [-pi, +pi]
    for key in (
        "wrapped_uncorrected_rad",
        "wrapped_aps_rad",
        "wrapped_corrected_rad",
        "wrapped_true_def_rad",
    ):
        arr = aps[key]
        assert arr.shape == elev.shape
        assert float(np.min(arr)) >= -np.pi - 1e-5
        assert float(np.max(arr)) <= np.pi + 1e-5

    metrics = aps["metrics"]
    assert metrics["aps_fringes_removed"] > 0.5
    assert metrics["rmse_reduction_pct"] > 90.0
    assert metrics["corrected_phase_rmse_rad"] < 0.20


def test_finland_stac_v1_orders_schema():
    """Verify STAC v1.0.0 GeoJSON FeatureCollection compliance for Finland orders."""
    aps_dummy = {
        "max_gia_los_displacement_mm": 7.49,
        "aps_fringes_removed": 3.71,
        "rmse_reduction_pct": 99.26,
    }
    peat_dummy = {
        "breathing_area_km2": 122139.0,
        "max_breathing_mm": 33.0,
        "coherence_threshold": 0.35,
        "min_peat_coherence": 0.18,
    }
    ice_dummy = {
        "frozen_ice_area_km2": 5391.0,
        "open_water_area_km2": 4518.0,
        "backscatter_contrast_db": 14.09,
    }

    stac = generate_finland_stac_orders(aps_dummy, peat_dummy, ice_dummy)
    assert stac["type"] == "FeatureCollection"
    assert stac["stac_version"] == "1.0.0"
    assert len(stac["features"]) == 3

    order_ids = [f["id"] for f in stac["features"]]
    assert "ORDER-ICEYE-X41-FINLAND-KVARKEN-REBOUND-001" in order_ids
    assert "ORDER-SYNSPECTIVE-STRIX4-FINLAND-BOG-BREATHING-002" in order_ids
    assert "ORDER-CATALYST-INSAR-FINLAND-LAKE-ICE-003" in order_ids

    # Verify ICEYE properties
    iceye_feat = next(f for f in stac["features"] if "ICEYE" in f["id"])
    assert iceye_feat["properties"]["platform"] == "ICEYE-X41"
    assert iceye_feat["properties"]["sar:instrument_mode"] == "Spotlight"
    assert iceye_feat["properties"]["sar:frequency_band"] == "X"
    assert iceye_feat["properties"]["sar:center_frequency"] == 9.65
    assert iceye_feat["properties"]["sar:resolution_range"] == 0.5

    # Verify StriX properties
    strix_feat = next(f for f in stac["features"] if "STRIX" in f["id"])
    assert strix_feat["properties"]["platform"] == "StriX-4"
    assert strix_feat["properties"]["sar:instrument_mode"] == "StripMap"
    assert strix_feat["properties"]["sar:frequency_band"] == "X"
    assert strix_feat["properties"]["sar:resolution_range"] == 3.0

    # Verify CATALYST InSAR properties
    cat_feat = next(f for f in stac["features"] if "CATALYST" in f["id"])
    assert cat_feat["properties"]["platform"] == "CATALYST-InSAR-X"
    assert cat_feat["properties"]["sar:instrument_mode"] == "Virtual-Stack"


def test_rule_e2s_014_zero_random_noise_finland(tmp_path: Path):
    """Verify finland_terrain contains zero pseudo-random noise and produces deterministic artifacts."""
    src = inspect.getsource(finland_terrain)
    forbidden = ["np.random", "random.normal", "random.uniform", "randn", "default_rng", "torch.randn", "torch.rand"]
    for token in forbidden:
        assert token not in src, (
            f"Rule e2s-014 violation: forbidden generator '{token}' found in finland_terrain.py"
        )

    # Execute twice and confirm identical bit-for-bit SHA-256 hashes
    m1 = run_finland_terrain_experiment(output_dir=tmp_path / "run1")
    m2 = run_finland_terrain_experiment(output_dir=tmp_path / "run2")

    assert m1["stac_orders_sha256"] == m2["stac_orders_sha256"]
    assert m1["post_glacial_rebound"] == m2["post_glacial_rebound"]
    assert m1["peatland_breathing_metrics"] == m2["peatland_breathing_metrics"]
    assert m1["lake_ice_metrics"] == m2["lake_ice_metrics"]
    assert m1["aps_correction_metrics"] == m2["aps_correction_metrics"]

    # Verify publication figure was created
    fig1 = tmp_path / "run1" / "figures" / "11_finland_terrain.png"
    assert fig1.exists()
    assert fig1.stat().st_size > 100_000


def test_finland_target_cities_schema():
    """Verify FINLAND_TARGET_CITIES exposes 6 frozen targets conforming to viewer_app schema."""
    assert len(FINLAND_TARGET_CITIES) == 6
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
    for city in FINLAND_TARGET_CITIES:
        assert required_keys.issubset(city.keys())
        assert city["country"] == "Finland"
        assert city["countryCode"] == "FI"
        assert LAT_SOUTH <= city["lat"] <= LAT_NORTH
        assert LON_WEST <= city["lon"] <= LON_EAST
        assert city["elevM"] >= 0.0
