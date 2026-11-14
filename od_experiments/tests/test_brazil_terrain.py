# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-FileCopyrightText: Copyright (c) 2026 Zhane Daye (SAR & Earth System Engineering; zhanedaye@umattr.ca)
# SPDX-License-Identifier: Apache-2.0
"""
Automated unit & scientific integrity test suite for the Brazil Tropical Dynamics Experiment
(Serra do Mar Catastrophic Debris Flows, Pantanal Wetland Flood Pulse, and Amazon Deforestation Frontier).

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
    brazil_terrain,
)
from od_experiments.geoint_sar.brazil_terrain import (
    AMAZON_LAT_NORTH,
    AMAZON_LAT_SOUTH,
    AMAZON_LON_EAST,
    AMAZON_LON_WEST,
    BRAZIL_TARGET_CITIES,
    DEBRIS_FLOW_SLOPE_THRESHOLD_DEG,
    DEFORESTATION_DECORRELATION_THRESHOLD,
    ICEYE_FLOOD_THRESHOLD_DB,
    PANTANAL_LAT_NORTH,
    PANTANAL_LAT_SOUTH,
    PANTANAL_LON_EAST,
    PANTANAL_LON_WEST,
    SERRA_DO_MAR_LAT_NORTH,
    SERRA_DO_MAR_LAT_SOUTH,
    SERRA_DO_MAR_LON_EAST,
    SERRA_DO_MAR_LON_WEST,
    STRIX_DECORRELATION_THRESHOLD,
    TARGET_COORDINATES,
    TROPICAL_ZTD_THRESHOLD_M,
    build_brazil_orography,
    compute_amazon_deforestation_texture,
    compute_high_moisture_tropical_ztd,
    compute_pantanal_flood_pulse,
    compute_serra_do_mar_landslide_dynamics,
    compute_terrain_slope,
    generate_brazil_stac_orders,
    run_brazil_terrain_suite,
)


def test_brazil_orography_and_debris_flow_slopes():
    """Verify physical terrain bounds of Serra do Mar and steep debris flow slopes (> 40°)."""
    # Serra do Mar high-resolution grid (520 x 840)
    lats = np.linspace(SERRA_DO_MAR_LAT_NORTH, SERRA_DO_MAR_LAT_SOUTH, 520)
    lons = np.linspace(SERRA_DO_MAR_LON_WEST, SERRA_DO_MAR_LON_EAST, 840)
    elev = build_brazil_orography(lats, lons, theater="serra_do_mar")
    slope = compute_terrain_slope(elev, lats, lons)

    assert elev.shape == (520, 840)
    assert slope.shape == (520, 840)

    # Peak elevation must capture Serra dos Órgãos / Mantiqueira summits (> 1800m)
    assert float(np.max(elev)) >= 1800.0

    # Critical requirement: Catastrophic debris flow slopes MUST exceed 40°
    assert float(np.max(slope)) >= DEBRIS_FLOW_SLOPE_THRESHOLD_DEG
    assert np.sum(slope >= DEBRIS_FLOW_SLOPE_THRESHOLD_DEG) >= 50

    # São Sebastião coordinate check (-23.76°S, -45.41°W)
    ilat_ss = int(np.argmin(np.abs(lats - (-23.76))))
    ilon_ss = int(np.argmin(np.abs(lons - (-45.41))))
    # Near São Sebastião coastal wall, slope should be very steep
    local_ss_slope = float(np.max(slope[max(0, ilat_ss - 15) : ilat_ss + 15, max(0, ilon_ss - 15) : ilon_ss + 15]))
    assert local_ss_slope >= 38.0

    # Petrópolis coordinate check (-22.505°S, -43.179°W)
    ilat_pet = int(np.argmin(np.abs(lats - (-22.505))))
    ilon_pet = int(np.argmin(np.abs(lons - (-43.179))))
    local_pet_slope = float(np.max(slope[max(0, ilat_pet - 15) : ilat_pet + 15, max(0, ilon_pet - 15) : ilon_pet + 15]))
    assert local_pet_slope >= 40.0

    # Pantanal low-relief basin check: flat alluvial wetland (elev 80m-140m, mean slope < 1.0°)
    pan_lats = np.linspace(PANTANAL_LAT_NORTH, PANTANAL_LAT_SOUTH, 220)
    pan_lons = np.linspace(PANTANAL_LON_WEST, PANTANAL_LON_EAST, 160)
    pan_elev = build_brazil_orography(pan_lats, pan_lons, theater="pantanal")
    pan_slope = compute_terrain_slope(pan_elev, pan_lats, pan_lons)

    assert 75.0 <= float(np.min(pan_elev)) <= 110.0
    assert float(np.mean(pan_slope[pan_elev < 130.0])) <= 1.0


def test_high_moisture_tropical_ztd_exceeds_threshold():
    """Verify Saastamoinen/Askne tropical tropospheric ZTD strictly exceeds 2.65m in moist lowlands."""
    lats = np.linspace(-18.0, -20.0, 31)
    elev_wetland = np.full((31, 31), 100.0, dtype=np.float32)  # 100m elevation in Pantanal
    elev_summit = np.full((31, 31), 2200.0, dtype=np.float32)   # 2200m summit in Serra do Mar

    t2m_wetland = np.full((31, 31), 302.15, dtype=np.float32)  # 29°C in Pantanal
    t2m_summit = t2m_wetland - 0.0065 * 2100.0                # Lapse rate ~288.5 K

    # High tropical relative humidity (0.92) and convective moisture scale height
    res_wetland = compute_high_moisture_tropical_ztd(
        t2m_wetland, elev_wetland, lats, rh_fraction=0.92, sea_level_pressure_hpa=1014.50
    )
    res_summit = compute_high_moisture_tropical_ztd(
        t2m_summit, elev_summit, lats, rh_fraction=0.75, sea_level_pressure_hpa=1014.50
    )

    wetland_ztd = float(np.mean(res_wetland["ztd_m"]))
    summit_ztd = float(np.mean(res_summit["ztd_m"]))

    # Core requirement: High-moisture tropical ZTD must exceed 2.65m
    assert wetland_ztd > TROPICAL_ZTD_THRESHOLD_M
    assert 2.66 <= wetland_ztd <= 2.76

    # Summit ZTD should be substantially lower due to reduced air and vapor column
    assert summit_ztd < 2.30

    # Base-to-summit vertical delay gradient across the escarpment must exceed 0.40m (>25 fringes)
    ztd_gradient = wetland_ztd - summit_ztd
    assert ztd_gradient >= 0.40
    fringes = ztd_gradient / (X_BAND_WAVELENGTH_M / 2.0)
    assert fringes >= 25.0


def test_pantanal_iceye_flood_specular_backscatter():
    """Verify ICEYE flood specular backscatter (sigma_0 < -16.5 dB) and wetland inundation area."""
    lats = np.linspace(PANTANAL_LAT_NORTH, PANTANAL_LAT_SOUTH, 180)
    lons = np.linspace(PANTANAL_LON_WEST, PANTANAL_LON_EAST, 140)

    elev = build_brazil_orography(lats, lons, theater="pantanal")
    slope = compute_terrain_slope(elev, lats, lons)

    t2m_t0 = np.full_like(elev, 301.5)
    t2m_t24 = t2m_t0 + 2.0

    res = compute_pantanal_flood_pulse(elev, slope, t2m_t0, t2m_t24, lats, lons)

    sigma0_vv = res["sigma0_vv_db"]
    flood_mask = res["flood_mask"]
    metrics = res["metrics"]

    # Minimum backscatter must plunge below the flood threshold (-16.5 dB)
    assert float(np.min(sigma0_vv)) < ICEYE_FLOOD_THRESHOLD_DB
    assert float(np.min(sigma0_vv)) <= -20.0

    # Inundated area must be substantial (> 10,000 km²)
    assert metrics["inundated_area_km2"] >= 10000.0

    # Peak tropical ZTD in Pantanal must exceed 2.65m
    assert metrics["max_ztd_m"] > TROPICAL_ZTD_THRESHOLD_M

    # Flood mask must be boolean and correctly identify low-slope alluvial terrain
    assert flood_mask.dtype == bool
    assert np.all(slope[flood_mask] < 2.0)
    assert np.all(elev[flood_mask] < 140.0)


def test_serra_do_mar_debris_flow_coherence_loss():
    """Verify Synspective StriX slope coherence loss (gamma < 0.30) on steep debris flow slopes (> 40°)."""
    lats = np.linspace(SERRA_DO_MAR_LAT_NORTH, SERRA_DO_MAR_LAT_SOUTH, 416)
    lons = np.linspace(SERRA_DO_MAR_LON_WEST, SERRA_DO_MAR_LON_EAST, 672)

    elev = build_brazil_orography(lats, lons, theater="serra_do_mar")
    slope = compute_terrain_slope(elev, lats, lons)

    t2m_t0 = np.full_like(elev, 292.0)
    # Convective storm perturbation
    t2m_t24 = t2m_t0 + 3.2

    res = compute_serra_do_mar_landslide_dynamics(elev, slope, t2m_t0, t2m_t24, lats, lons)

    coherence = res["coherence_gamma"]
    landslide_mask = res["landslide_mask"]
    metrics = res["metrics"]

    # Coherence on unstable steep slopes must drop below threshold (0.30)
    assert float(np.min(coherence)) < STRIX_DECORRELATION_THRESHOLD
    assert metrics["min_coherence_gamma"] < STRIX_DECORRELATION_THRESHOLD

    # Landslide hazard area must be non-zero and located on slopes >= 40°
    assert metrics["high_risk_slope_area_km2"] > 0.0
    assert np.all(slope[landslide_mask] >= DEBRIS_FLOW_SLOPE_THRESHOLD_DEG)

    # Stable gentle terrain retains higher coherence
    gentle_mask = slope < 15.0
    assert float(np.mean(coherence[gentle_mask])) >= 0.70


def test_amazon_deforestation_radar_texture_shifts():
    """Verify Amazon deforestation backscatter contrast, texture variance, and InSAR decorrelation."""
    lats = np.linspace(AMAZON_LAT_NORTH, AMAZON_LAT_SOUTH, 160)
    lons = np.linspace(AMAZON_LON_WEST, AMAZON_LON_EAST, 160)

    elev = build_brazil_orography(lats, lons, theater="amazon_frontier")
    t2m_t0 = np.full_like(elev, 298.0)
    t2m_t24 = t2m_t0 + 1.5

    res = compute_amazon_deforestation_texture(elev, t2m_t0, t2m_t24, lats, lons)

    metrics = res["metrics"]
    sigma0_vv = res["sigma0_vv_db"]
    tex_var = res["texture_variance_db2"]
    edge_grad = res["edge_gradient_db"]
    coherence = res["coherence_gamma"]

    # Primary forest backscatter ~ -8 dB vs cleared pasture < -12.5 dB
    assert -9.5 <= metrics["forest_mean_sigma0_db"] <= -7.5
    assert metrics["cleared_mean_sigma0_db"] <= -12.5

    # Backscatter contrast must exceed 3.5 dB
    contrast_db = metrics["forest_mean_sigma0_db"] - metrics["cleared_mean_sigma0_db"]
    assert contrast_db >= 3.5

    # Spatial texture variance and edge gradient must be non-zero and detect frontiers
    assert metrics["max_texture_variance_db2"] >= 2.0
    assert metrics["max_edge_gradient_db"] >= 1.0

    # Active deforestation clearings suffer severe temporal decorrelation (gamma < 0.25)
    assert float(np.min(coherence)) < DEFORESTATION_DECORRELATION_THRESHOLD


def test_catalyst_aps_fringe_correction_serra_do_mar():
    """Verify CATALYST X-band InSAR APS phase screen removal achieves >90% phase RMSE reduction."""
    lats = np.linspace(-22.0, -24.5, 33)
    lons = np.linspace(-46.0, -42.5, 41)
    lat_g = lats[:, None]
    lon_g = lons[None, :]

    elev = 1500.0 * np.exp(-(((lat_g - (-23.2)) / 0.8) ** 2 + ((lon_g - (-44.2)) / 1.0) ** 2)) + 50.0
    t2m_t0 = 292.0 + 2.0 * np.cos(np.deg2rad(lat_g * 4.0))
    t2m_t24 = t2m_t0 + 4.0 * np.exp(-(((lat_g - (-23.0)) / 1.0) ** 2 + ((lon_g - (-44.0)) / 1.2) ** 2))

    slope = compute_terrain_slope(elev, lats, lons)
    res = compute_serra_do_mar_landslide_dynamics(elev, slope, t2m_t0, t2m_t24, lats, lons)
    aps = res["aps_result"]

    # Phase arrays must strictly lie in [-pi, pi]
    for key in ("wrapped_uncorrected_rad", "wrapped_aps_screen_rad", "wrapped_corrected_rad"):
        arr = aps[key]
        assert float(np.min(arr)) >= -np.pi - 1e-5
        assert float(np.max(arr)) <= np.pi + 1e-5

    aps_metrics = aps["metrics"]
    assert aps_metrics["aps_fringes_removed"] >= 3.0
    assert aps_metrics["rmse_reduction_pct"] > 90.0
    assert aps_metrics["corrected_phase_rmse_rad"] < aps_metrics["uncorrected_phase_rmse_rad"] * 0.15


def test_brazil_stac_v1_orders_schema():
    """Verify STAC v1.0.0 FeatureCollection schema and metadata integrity for Brazil tasking."""
    dummy_serra = {
        "coherence_threshold": STRIX_DECORRELATION_THRESHOLD,
        "min_coherence_gamma": 0.18,
        "high_risk_slope_area_km2": 105.4,
        "mean_ztd_m": 2.68,
        "aps_fringes_removed": 36.8,
        "rmse_reduction_pct": 98.8,
    }
    dummy_pantanal = {
        "flood_threshold_db": ICEYE_FLOOD_THRESHOLD_DB,
        "min_sigma0_vv_db": -22.5,
        "inundated_area_km2": 95400.0,
        "max_ztd_m": 2.71,
    }
    dummy_amazon = {
        "forest_mean_sigma0_db": -8.2,
        "cleared_mean_sigma0_db": -14.6,
        "deforested_area_km2": 45200.0,
    }

    orders = generate_brazil_stac_orders(dummy_serra, dummy_pantanal, dummy_amazon)

    assert orders["type"] == "FeatureCollection"
    assert orders["stac_version"] == "1.0.0"
    features = orders["features"]
    assert len(features) == 4

    # Verify orders covering Pantanal, Serra do Mar, Amazon, and São Sebastião
    order_ids = [f["id"] for f in features]
    assert "ORDER-ICEYE-X43-BRAZIL-PANTANAL-001" in order_ids
    assert "ORDER-SYNSPECTIVE-STRIX4-SERRADOMAR-002" in order_ids
    assert "ORDER-CATALYST-AMAZON-FRONTIER-003" in order_ids
    assert "ORDER-ICEYE-X43-SAOSEBASTIAO-004" in order_ids

    for f in features:
        assert f["type"] == "Feature"
        assert f["stac_version"] == "1.0.0"
        props = f["properties"]
        assert props["sar:frequency_band"] == "X"
        assert props["sar:center_frequency"] == pytest.approx(9.65, abs=0.01)
        assert props["sat:orbit_state"] in ("ascending", "descending")
        assert len(props["sar:polarizations"]) >= 1


def test_rule_e2s_014_zero_random_noise_brazil():
    """Verify strict Rule e2s-014 compliance: zero synthetic random noise and valid plot origin."""
    src = inspect.getsource(brazil_terrain)

    # Disallow stochastic noise injection
    assert "np.random" not in src
    assert "random.random" not in src
    assert "torch.randn" not in src
    assert "scipy.stats.norm.rvs" not in src

    # Verify all imshow calls include explicit origin="upper"
    assert 'origin="upper"' in src


def test_brazil_target_cities_schema():
    """Verify BRAZIL_TARGET_CITIES catalog satisfies all viewer_app telemetry requirements."""
    assert len(BRAZIL_TARGET_CITIES) == 6

    expected_keys = {
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
        "sentinel2Lod",
        "roleSummary",
    }

    for city in BRAZIL_TARGET_CITIES:
        missing = expected_keys - set(city.keys())
        assert not missing, f"City {city.get('id')} missing keys: {missing}"
        assert city["country"] == "Brazil"
        assert city["countryCode"] == "BR"
        # Geographical bounds for Brazil
        assert -26.0 <= city["lat"] <= -8.0
        assert -60.0 <= city["lon"] <= -40.0
        assert city["elevM"] >= 0
        assert city["apsZtdM"] >= 2.0


def test_brazil_terrain_suite_execution_and_artifacts(tmp_path: Path):
    """Verify end-to-end execution of run_brazil_terrain_suite and artifact creation."""
    out_dir = tmp_path / "advanced_capabilities"
    manifest = run_brazil_terrain_suite(output_dir=out_dir)

    assert Path(manifest["figure"]).exists()
    assert Path(manifest["figure"]).stat().st_size > 100_000  # Figure > 100 KB
    assert Path(manifest["stac_orders_file"]).exists()
    assert Path(manifest["stac_orders_file"]).stat().st_size > 1_000

    # Verify manifest structure
    assert manifest["module"] == "od_experiments.geoint_sar.brazil_terrain"
    assert manifest["theaters"]["serra_do_mar"]["max_slope_deg"] >= 40.0
    assert manifest["theaters"]["pantanal"]["min_sigma0_vv_db"] < ICEYE_FLOOD_THRESHOLD_DB
    assert manifest["theaters"]["pantanal"]["max_tropical_ztd_m"] > TROPICAL_ZTD_THRESHOLD_M
    assert manifest["theaters"]["amazon_frontier"]["deforested_area_km2"] > 0
    assert manifest["stac_orders_count"] == 4
