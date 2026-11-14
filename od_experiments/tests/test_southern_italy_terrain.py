# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-FileCopyrightText: Copyright (c) 2026 Zhane Daye (SAR & Earth System Engineering; zhanedaye@umattr.ca)
# SPDX-License-Identifier: Apache-2.0
"""
Automated unit & scientific integrity test suite for the Southern Italy Hidden Terrain & Volcanotectonics Experiment
(Mount Etna Flank Collapse & Magma Intrusion, Campi Flegrei Caldera Bradyseism,
Calabria Crystalline Massifs Landslides, and Apulia Karst).

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
from od_experiments.geoint_sar.sar_geoint_engine import (
    compute_insar_aps_fringe_correction,
    compute_tropospheric_delay_ztd,
)
from od_experiments.geoint_sar.southern_italy_terrain import (
    LAT_NORTH,
    LAT_SOUTH,
    LON_EAST,
    LON_WEST,
    SOUTHERN_ITALY_TARGET_CITIES,
    TARGET_COORDINATES,
    X_BAND_HALF_WAVELENGTH_M,
    build_southern_italy_orography,
    compute_southern_italy_flood_and_coherence,
    compute_southern_italy_hydrology,
    compute_southern_italy_volcanotectonic_deformation,
    generate_southern_italy_stac_orders,
    run_southern_italy_terrain_suite,
)


def test_southern_italy_orography_elevations_and_summits():
    """Verify physical terrain bounds of Mount Etna, Calabria crystalline massifs, Vesuvius, and Apulia karst."""
    lats = np.linspace(LAT_NORTH, LAT_SOUTH, 184)
    lons = np.linspace(LON_WEST, LON_EAST, 232)
    elev = build_southern_italy_orography(lats, lons)

    assert elev.shape == (184, 232)
    # Peak elevation must reach the authentic Mount Etna summit (~3357m)
    assert float(np.max(elev)) == pytest.approx(3357.0, abs=5.0)

    # Mount Etna summit check (37.7510N, 14.9934E)
    ilat_etna = int(np.argmin(np.abs(lats - 37.7510)))
    ilon_etna = int(np.argmin(np.abs(lons - 14.9934)))
    assert float(elev[ilat_etna, ilon_etna]) >= 3200.0

    # Aspromonte Montalto summit check (38.165N, 15.905E)
    ilat_aspr = int(np.argmin(np.abs(lats - 38.165)))
    ilon_aspr = int(np.argmin(np.abs(lons - 15.905)))
    assert float(elev[ilat_aspr, ilon_aspr]) >= 1700.0

    # Sila Botte Donato check (39.220N, 16.600E)
    ilat_sila = int(np.argmin(np.abs(lats - 39.220)))
    ilon_sila = int(np.argmin(np.abs(lons - 16.600)))
    assert float(elev[ilat_sila, ilon_sila]) >= 1650.0

    # Somma-Vesuvius check (40.821N, 14.426E)
    ilat_ves = int(np.argmin(np.abs(lats - 40.821)))
    ilon_ves = int(np.argmin(np.abs(lons - 14.426)))
    assert float(elev[ilat_ves, ilon_ves]) >= 1100.0

    # Campi Flegrei caldera floor check (40.825N, 14.135E) must be low coastal elevation
    ilat_cf = int(np.argmin(np.abs(lats - 40.825)))
    ilon_cf = int(np.argmin(np.abs(lons - 14.135)))
    assert float(elev[ilat_cf, ilon_cf]) <= 120.0

    # Catania coastal plain check (37.40N, 15.05E)
    ilat_cat = int(np.argmin(np.abs(lats - 37.40)))
    ilon_cat = int(np.argmin(np.abs(lons - 15.05)))
    assert float(elev[ilat_cat, ilon_cat]) <= 65.0

    # Alta Murgia karst plateau check (40.95N, 16.45E)
    ilat_murg = int(np.argmin(np.abs(lats - 40.95)))
    ilon_murg = int(np.argmin(np.abs(lons - 16.45)))
    assert 400.0 <= float(elev[ilat_murg, ilon_murg]) <= 750.0


def test_saastamoinen_askne_southern_italy_ztd_gradient():
    """Verify Saastamoinen and Askne-Nordius ZTD gradients across the 3357m Mount Etna stratovolcano."""
    lats = np.linspace(38.0, 37.0, 25)
    elev_sea = np.full((25, 25), 15.0, dtype=np.float32)  # Catania coastal plain
    elev_summit = np.full((25, 25), 3357.0, dtype=np.float32)  # Mount Etna summit

    t2m_sea = np.full((25, 25), 294.15, dtype=np.float32)  # ~21 C in Catania
    t2m_summit = t2m_sea - 0.0065 * (3357.0 - 15.0)  # Lapse rate ~272.4 K (~-0.7 C)

    res_sea = compute_tropospheric_delay_ztd(t2m_sea, elev_sea, lats, rh_fraction=0.78)
    res_summit = compute_tropospheric_delay_ztd(t2m_summit, elev_summit, lats, rh_fraction=0.55)

    # Sea level ZTD in warm Mediterranean air is ~2.40 to 2.65 m
    assert 2.40 <= float(np.mean(res_sea["ztd_m"])) <= 2.65
    # Summit ZTD (3357m) is drastically reduced due to thin air column (~1.50 to 1.70 m)
    assert 1.50 <= float(np.mean(res_summit["ztd_m"])) <= 1.70

    # Vertical delay gradient across Mount Etna must exceed 0.75m (~48 X-band fringes)
    ztd_diff = float(np.mean(res_sea["ztd_m"]) - np.mean(res_summit["ztd_m"]))
    assert ztd_diff >= 0.75


def test_southern_italy_volcanotectonic_deformation_modeling():
    """Verify analytical Mogi, flank collapse slip, and landslide deformation components."""
    lats = np.linspace(LAT_NORTH, LAT_SOUTH, 184)
    lons = np.linspace(LON_WEST, LON_EAST, 232)
    elev = build_southern_italy_orography(lats, lons)

    def_dict = compute_southern_italy_volcanotectonic_deformation(lats, lons, elev, incidence_deg=34.1)

    # 1. Campi Flegrei caldera bradyseism: peak uplift in Pozzuoli harbor must be positive (> 5 cm in LOS)
    ilat_cf = int(np.argmin(np.abs(lats - 40.825)))
    ilon_cf = int(np.argmin(np.abs(lons - 14.135)))
    cf_los = float(def_dict["campi_flegrei_los_m"][ilat_cf, ilon_cf])
    assert cf_los >= 0.05
    assert float(np.max(def_dict["campi_flegrei_los_m"])) <= 0.12

    # 2. Mount Etna east flank collapse: seaward displacement/subsidence in Valle del Bove sector (< -2.5 cm in LOS)
    ilat_et_flank = int(np.argmin(np.abs(lats - 37.74)))
    ilon_et_flank = int(np.argmin(np.abs(lons - 15.08)))
    etna_los = float(def_dict["etna_los_m"][ilat_et_flank, ilon_et_flank])
    assert etna_los <= -0.025

    # 3. Calabria crystalline landslides: negative downslope creep on Aspromonte slopes (< -1.5 cm)
    ilat_aspr = int(np.argmin(np.abs(lats - 38.165)))
    ilon_aspr = int(np.argmin(np.abs(lons - 15.905)))
    cal_los = float(def_dict["calabria_los_m"][ilat_aspr, ilon_aspr])
    assert cal_los <= -0.015

    # 4. Apulia karst sinkhole subsidence: localized subsidence (< -1.0 cm)
    ilat_murg = int(np.argmin(np.abs(lats - 40.950)))
    ilon_murg = int(np.argmin(np.abs(lons - 16.450)))
    karst_los = float(def_dict["karst_los_m"][ilat_murg, ilon_murg])
    assert karst_los <= -0.010


def test_southern_italy_catalyst_aps_fringe_correction():
    """Verify CATALYST X-Band InSAR APS fringe correction and deformation recovery."""
    lats = np.linspace(LAT_NORTH, LAT_SOUTH, 184)
    lons = np.linspace(LON_WEST, LON_EAST, 232)
    elev = build_southern_italy_orography(lats, lons)

    # Realistic temperature change and orography across Southern Italy
    lat_g = lats[:, None]
    lon_g = lons[None, :]
    t2m_t0 = (288.0 + 3.0 * np.cos(np.deg2rad(lat_g * 3.0)) - 0.0065 * elev).astype(np.float32)
    t2m_t24 = (t2m_t0 + 4.5 * np.exp(-(((lat_g - 38.0) / 1.5) ** 2 + ((lon_g - 15.5) / 1.8) ** 2))).astype(np.float32)

    def_dict = compute_southern_italy_volcanotectonic_deformation(lats, lons, elev, incidence_deg=34.1)

    aps_res = compute_insar_aps_fringe_correction(
        t2m_t0=t2m_t0,
        t2m_t24=t2m_t24,
        elevation_m=elev,
        lats=lats,
        lons=lons,
        incidence_deg=34.1,
        wavelength_m=X_BAND_WAVELENGTH_M,
        true_deformation_los_m=def_dict["true_deformation_los_m"],
    )

    metrics = aps_res["metrics"]
    # Uncorrected interferogram is severely contaminated by troposphere
    assert metrics["uncorrected_phase_rmse_rad"] > 8.0
    # Corrected interferogram achieves clean recovery of ground deformation (< 1.0 rad residual RMSE)
    assert metrics["corrected_phase_rmse_rad"] < 1.0
    # CATALYST weather model screen removal achieves >95% error reduction
    assert metrics["rmse_reduction_pct"] >= 95.0
    # Multiple full fringes removed across high-relief topography
    assert metrics["aps_fringes_removed"] >= 1.5


def test_southern_italy_iceye_flood_and_strix_coherence():
    """Verify ICEYE flood specular backscatter and Synspective StriX coherence loss."""
    lats = np.linspace(LAT_NORTH, LAT_SOUTH, 184)
    lons = np.linspace(LON_WEST, LON_EAST, 232)
    elev = build_southern_italy_orography(lats, lons)

    t2m_t0 = (288.15 - 0.0065 * elev).astype(np.float32)
    t2m_t24 = (t2m_t0 + 2.2).astype(np.float32)

    hazard_res = compute_southern_italy_flood_and_coherence(t2m_t0, t2m_t24, elev, lats, lons)

    metrics = hazard_res["metrics"]
    # Specular flood threshold is -16.5 dB
    assert metrics["flood_threshold_db"] == -16.5
    assert metrics["min_sigma0_vv_db"] < -16.5
    assert metrics["inundated_area_km2"] > 0.0

    # Coherence loss on steep crystalline slopes
    assert metrics["coherence_threshold"] == 0.32
    assert metrics["min_coherence_gamma"] < 0.32
    assert metrics["high_risk_slope_area_km2"] > 0.0

    # Sea exclusion: open sea is excluded from terrestrial flood classification
    sea_weight = hazard_res["sea_weight"]
    flood_mask = hazard_res["flood_mask"]
    assert np.all(flood_mask[sea_weight >= 0.35] == False)


def test_southern_italy_stac_v1_orders_schema():
    """Verify OGC / STAC v1.0.0 compliance of Southern Italy tasking orders."""
    aps_metrics = {
        "mean_ztd_m": 2.4046,
        "aps_fringes_removed": 11.53,
        "uncorrected_phase_rmse_rad": 16.67,
        "corrected_phase_rmse_rad": 0.19,
        "rmse_reduction_pct": 98.83,
    }
    hazard_metrics = {
        "flood_threshold_db": -16.5,
        "min_sigma0_vv_db": -25.88,
        "inundated_area_km2": 16.2,
        "coherence_threshold": 0.32,
        "min_coherence_gamma": 0.08,
        "high_risk_slope_area_km2": 255.4,
    }

    stac_data = generate_southern_italy_stac_orders(aps_metrics, hazard_metrics)

    assert stac_data["type"] == "FeatureCollection"
    assert stac_data["stac_version"] == "1.0.0"
    assert len(stac_data["features"]) == 4

    expected_ids = {
        "ORDER-CATALYST-INSAR-X-CAMPIFLEGREI-001",
        "ORDER-SYNSPECTIVE-STRIX4-ETNA-002",
        "ORDER-SYNSPECTIVE-STRIX4-CALABRIA-003",
        "ORDER-ICEYE-X42-CATANIA-SIMETO-004",
    }
    found_ids = {f["id"] for f in stac_data["features"]}
    assert found_ids == expected_ids

    for feat in stac_data["features"]:
        assert feat["type"] == "Feature"
        assert feat["stac_version"] == "1.0.0"
        assert "geometry" in feat and feat["geometry"]["type"] == "Polygon"
        props = feat["properties"]
        assert props["sar:frequency_band"] == "X"
        assert props["sar:center_frequency"] == 9.65
        assert "view:incidence_angle" in props
        assert "tasking:priority" in props
        assert "e2s:tip_trigger" in props


def test_southern_italy_target_cities_schema():
    """Verify target cities schema, coordinates, and telemetry metadata."""
    assert len(SOUTHERN_ITALY_TARGET_CITIES) == 6

    for city in SOUTHERN_ITALY_TARGET_CITIES:
        assert city["country"] == "Italy"
        assert city["countryCode"] == "IT"
        assert LAT_SOUTH <= city["lat"] <= LAT_NORTH
        assert LON_WEST <= city["lon"] <= LON_EAST
        assert city["elevM"] >= 0
        assert "sarSatelliteId" in city
        assert "apsStatus" in city
        assert "fringesRemoved" in city
        assert "rmseReductionPct" in city

    for cid, data in TARGET_COORDINATES.items():
        assert cid in [c["id"] for c in SOUTHERN_ITALY_TARGET_CITIES]
        assert data["country"] == "Italy"
        assert data["elevation_m"] >= 0


def test_rule_e2s_014_zero_random_noise_southern_italy():
    """Rule e2s-014 compliance audit: ensure zero synthetic noise and explicit origin='upper'."""
    import od_experiments.geoint_sar.southern_italy_terrain as mod

    source = inspect.getsource(mod)

    # Disallow stochastic pseudorandom number generation
    forbidden = ["np.random.normal", "np.random.randn", "np.random.standard_normal", "np.random.uniform", "random.random", "default_rng"]
    for token in forbidden:
        assert token not in source, f"Forbidden noise generator {token} found"

    # Ensure all imshow calls in southern_italy_terrain.py specify origin="upper"
    imshow_count = source.count(".imshow(")
    origin_upper_count = source.count('origin="upper"')
    assert imshow_count > 0
    assert origin_upper_count >= imshow_count


def test_southern_italy_nyquist_fringe_sampling():
    """Verify Nyquist sampling restoration across steep Mount Etna and Calabrian slopes after APS correction."""
    lats = np.linspace(LAT_NORTH, LAT_SOUTH, 184)
    lons = np.linspace(LON_WEST, LON_EAST, 232)
    elev = build_southern_italy_orography(lats, lons)

    t2m_t0 = (288.15 - 0.0065 * elev).astype(np.float32)
    t2m_t24 = (t2m_t0 + 2.5 * np.cos(np.deg2rad(lats))[:, None]).astype(np.float32)

    def_dict = compute_southern_italy_volcanotectonic_deformation(lats, lons, elev, incidence_deg=34.1)

    aps_res = compute_insar_aps_fringe_correction(
        t2m_t0=t2m_t0,
        t2m_t24=t2m_t24,
        elevation_m=elev,
        lats=lats,
        lons=lons,
        incidence_deg=34.1,
        wavelength_m=X_BAND_WAVELENGTH_M,
        true_deformation_los_m=def_dict["true_deformation_los_m"],
    )

    phase_uncorrected = aps_res["phase_uncorrected_unwrapped_rad"]
    phase_corrected = aps_res["phase_corrected_unwrapped_rad"]

    # Compute phase gradient magnitudes (rad/pixel)
    grad_y_uncorr, grad_x_uncorr = np.gradient(phase_uncorrected)
    grad_mag_uncorr = np.hypot(grad_y_uncorr, grad_x_uncorr)

    grad_y_corr, grad_x_corr = np.gradient(phase_corrected)
    grad_mag_corr = np.hypot(grad_y_corr, grad_x_corr)

    # Uncorrected tropospheric screen produces high phase gradient across Etna's 3357m relief
    assert float(np.max(grad_mag_uncorr)) > np.pi

    # CATALYST APS correction dramatically suppresses atmospheric phase gradient
    assert float(np.mean(grad_mag_corr)) < float(np.mean(grad_mag_uncorr))
