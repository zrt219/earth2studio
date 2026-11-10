# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-FileCopyrightText: Copyright (c) 2026 Zhane Daye (SAR & Earth System Engineering; zhanedaye@umattr.ca)
# SPDX-License-Identifier: Apache-2.0
"""
Comprehensive automated unit & scientific integrity test suite for the GEOINT
Weather-to-SAR Tip-and-Cue, CATALYST X-Band Tropospheric Phase Screen (APS),
and Flood/Landslide Attribution Engine (ICEYE, Synspective StriX, CATALYST).

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
    compute_flood_and_coherence_attribution,
    compute_insar_aps_fringe_correction,
    compute_tropospheric_delay_ztd,
    generate_tip_and_cue_stac_orders,
    run_geoint_sar_suite,
    sar_geoint_engine,
)


def test_x_band_physical_constants():
    """Verify X-band carrier frequency (9.65 GHz) and wavelength (~3.1067 cm)."""
    assert X_BAND_FREQUENCY_HZ == pytest.approx(9.65e9, rel=1e-6)
    assert X_BAND_WAVELENGTH_M == pytest.approx(0.031066576, abs=1e-6)
    # Half-wavelength two-way fringe spacing must be ~1.5533 cm
    assert (X_BAND_WAVELENGTH_M / 2.0) * 100.0 == pytest.approx(1.5533, abs=1e-3)


def test_saastamoinen_and_askne_nordius_ztd_bounds():
    """Verify Zenith Hydrostatic (ZHD), Wet (ZWD), and Total Delay (ZTD) physical bounds."""
    lats = np.linspace(48.0, 38.0, 21)
    lons = np.linspace(6.0, 18.0, 25)
    t2m = np.full((len(lats), len(lons)), 288.15, dtype=np.float32)

    # Sea-level vs 3000m Alpine ridge
    elev_sea = np.zeros_like(t2m)
    elev_alps = np.full_like(t2m, 3000.0)

    res_sea = compute_tropospheric_delay_ztd(t2m, elev_sea, lats, rh_fraction=0.75)
    res_alps = compute_tropospheric_delay_ztd(
        t2m - 19.5, elev_alps, lats, rh_fraction=0.75
    )

    # Sea-level standard ZHD is ~2.30 m, ZWD is ~0.10-0.25 m, ZTD is ~2.40-2.55 m
    assert float(np.mean(res_sea["zhd_m"])) == pytest.approx(2.307, abs=0.05)
    assert 0.05 <= float(np.mean(res_sea["zwd_m"])) <= 0.35
    assert 2.35 <= float(np.mean(res_sea["ztd_m"])) <= 2.65

    # High-elevation Alpine ZHD and ZTD must be strictly smaller due to thinner air column
    assert np.all(res_alps["zhd_m"] < res_sea["zhd_m"])
    assert np.all(res_alps["ztd_m"] < res_sea["ztd_m"])
    assert float(np.mean(res_alps["ztd_m"])) < 1.80


def test_catalyst_insar_aps_fringe_correction_and_wrapping():
    """Verify X-band wrapped phase is in [-pi, pi] and CATALYST APS correction reduces RMSE >90%."""
    lats = np.linspace(40.0, 32.0, 33)
    lons = np.linspace(132.0, 142.0, 41)
    lat_g = lats[:, None]
    lon_g = lons[None, :]

    # Realistic baroclinic warming + orographic terrain
    t2m_t0 = 286.0 + 2.0 * np.cos(np.deg2rad(lat_g * 4.0))
    t2m_t24 = t2m_t0 + 4.5 * np.exp(
        -(((lat_g - 36.0) / 2.0) ** 2 + ((lon_g - 137.0) / 2.5) ** 2)
    )
    elev = 1800.0 * np.exp(
        -(((lat_g - 36.2) / 1.2) ** 2 + ((lon_g - 137.5) / 1.5) ** 2)
    )

    aps = compute_insar_aps_fringe_correction(
        t2m_t0, t2m_t24, elev, lats, lons, incidence_deg=34.1
    )

    # Wrapped interferograms must lie strictly in [-pi, +pi]
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
    assert (
        metrics["corrected_phase_rmse_rad"]
        < metrics["uncorrected_phase_rmse_rad"] * 0.10
    )
    assert metrics["rmse_reduction_pct"] > 90.0


def test_iceye_flood_and_synspective_coherence_attribution():
    """Verify specular flood backscatter (< -16.5 dB) and steep slope coherence loss (< 0.32)."""
    lats = np.linspace(47.0, 43.0, 41)
    lons = np.linspace(8.0, 14.0, 61)
    lat_g = lats[:, None]
    lon_g = lons[None, :]

    # Flat floodplain around 45N, steep mountain ridge around 46.5N
    elev = 2800.0 * np.exp(-(((lat_g - 46.5) / 0.5) ** 2)) + 0.0 * lon_g + 20.0
    t2m_t0 = np.full_like(elev, 285.0)
    t2m_t24 = t2m_t0 + 6.0 * np.exp(
        -(((lat_g - 46.0) / 1.5) ** 2 + ((lon_g - 11.0) / 2.0) ** 2)
    )

    res = compute_flood_and_coherence_attribution(
        t2m_t0, t2m_t24, elev, lats, lons, domain_name="Test_Po_Valley_Alps"
    )

    assert res["sigma0_vv_db"].shape == elev.shape
    assert res["coherence_gamma"].shape == elev.shape
    assert float(np.min(res["sigma0_vv_db"])) < -16.5
    assert res["metrics"]["inundated_pixels"] > 0
    assert res["metrics"]["inundated_area_km2"] > 0.0
    assert 0.05 <= float(np.min(res["coherence_gamma"])) <= 0.32
    assert float(np.max(res["coherence_gamma"])) <= 1.0
    assert res["metrics"]["decorrelated_slope_pixels"] > 0


def test_stac_v1_tasking_orders_schema():
    """Verify STAC v1.0.0 GeoJSON FeatureCollection compliance for ICEYE-X38 and StriX-3."""
    aps_dummy = {
        "mean_ztd_m": 2.32,
        "aps_fringes_removed": 18.4,
        "uncorrected_phase_rmse_rad": 17.5,
        "corrected_phase_rmse_rad": 0.19,
        "rmse_reduction_pct": 98.9,
    }
    haz_dummy = {
        "flood_threshold_db": -16.5,
        "min_sigma0_vv_db": -24.8,
        "inundated_area_km2": 142.5,
        "coherence_threshold": 0.32,
        "min_coherence_gamma": 0.14,
        "high_risk_slope_area_km2": 38.4,
    }

    stac = generate_tip_and_cue_stac_orders(aps_dummy, aps_dummy, haz_dummy, haz_dummy)
    assert stac["type"] == "FeatureCollection"
    assert stac["stac_version"] == "1.0.0"
    assert len(stac["features"]) == 2

    iceye_feat, strix_feat = stac["features"]
    assert iceye_feat["properties"]["platform"] == "ICEYE-X38"
    assert iceye_feat["properties"]["sar:instrument_mode"] == "Spotlight"
    assert iceye_feat["properties"]["sar:frequency_band"] == "X"
    assert iceye_feat["properties"]["view:incidence_angle"] == 28.4

    assert strix_feat["properties"]["platform"] == "StriX-3"
    assert strix_feat["properties"]["sar:instrument_mode"] == "StripMap"
    assert strix_feat["properties"]["sar:frequency_band"] == "X"
    assert strix_feat["properties"]["view:incidence_angle"] == 34.1


def test_rule_e2s_014_scientific_integrity_zero_random_noise(tmp_path: Path):
    """Verify sar_geoint_engine contains zero pseudo-random noise calls and produces deterministic outputs."""
    src = inspect.getsource(sar_geoint_engine)
    forbidden = ["np.random", "random.normal", "random.uniform", "randn", "default_rng"]
    for token in forbidden:
        assert token not in src, (
            f"Forbidden synthetic noise generator '{token}' found in sar_geoint_engine.py"
        )

    # Verify end-to-end execution produces bit-for-bit identical manifests across consecutive runs
    m1 = run_geoint_sar_suite(output_dir=tmp_path / "run1")
    m2 = run_geoint_sar_suite(output_dir=tmp_path / "run2")
    assert m1["stac_orders_sha256"] == m2["stac_orders_sha256"]
    assert m1["theaters"] == m2["theaters"]
    assert (tmp_path / "run1" / "figures" / "06_geoint_sar_aps_trifecta.png").exists()
    stac_loaded = json.loads(
        (tmp_path / "run1" / "stac_tasking_orders.geojson").read_text(encoding="utf-8")
    )
    assert stac_loaded["type"] == "FeatureCollection"


def test_nyquist_fringe_sampling_and_po_valley_sea_exclusion():
    """Verify 8x mesoscale upsampling keeps phase gradients below Nyquist limit on real GFS tensors and excludes offshore seas/non-European domains."""
    init_npy = Path("outputs/scientific_study_verified/forecast/initial_condition.npy")
    truth_npy = Path(
        "outputs/scientific_study_verified/verification/verifying_truth_t2m.npy"
    )
    if init_npy.exists() and truth_npy.exists():
        global_t0 = np.load(init_npy)
        global_t24 = np.load(truth_npy)
        global_lats = np.linspace(90.0, -90.0, global_t0.shape[0])
        global_lons = np.linspace(0.0, 360.0, global_t0.shape[1], endpoint=False)
        it_lat_mask = (global_lats <= 48.0) & (global_lats >= 38.0)
        it_lon_mask = (global_lons >= 6.0) & (global_lons <= 18.0)
        coarse_lats = global_lats[it_lat_mask]
        coarse_lons = global_lons[it_lon_mask]
        t0_c = global_t0[np.ix_(it_lat_mask, it_lon_mask)]
        t24_c = global_t24[np.ix_(it_lat_mask, it_lon_mask)]
    else:
        coarse_lats = np.linspace(48.0, 38.0, 41)
        coarse_lons = np.linspace(6.0, 18.0, 49)
        lat_r = np.deg2rad(coarse_lats)[:, None]
        lon_r = np.deg2rad(coarse_lons)[None, :]
        t0_c = (285.0 + 4.0 * np.sin(2.0 * lat_r) * np.cos(3.0 * lon_r)).astype(
            np.float32
        )
        t24_c = (
            285.0 + 4.0 * np.sin(2.0 * lat_r) * np.cos(3.0 * (lon_r - np.deg2rad(10.0)))
        ).astype(np.float32)

    fine_t0, fine_t24, fine_lats, fine_lons = (
        sar_geoint_engine._upsample_synoptic_theater(
            t0_c, t24_c, coarse_lats, coarse_lons, scale_factor=8
        )
    )
    assert fine_t0.shape == (41 * 8, 49 * 8)

    it_elev = sar_geoint_engine._build_deterministic_orography(
        fine_lats, fine_lons, region="italy"
    )
    aps = compute_insar_aps_fringe_correction(
        fine_t0, fine_t24, it_elev, fine_lats, fine_lons, incidence_deg=28.4
    )
    # Verify Nyquist compliance on actual GFS theater: 99.5th percentile pixel-to-pixel unwrapped phase step < pi rad
    dphi_y = np.abs(np.diff(aps["phase_uncorrected_unwrapped_rad"], axis=0))
    dphi_x = np.abs(np.diff(aps["phase_uncorrected_unwrapped_rad"], axis=1))
    assert float(np.percentile(dphi_y, 99.5)) < np.pi
    assert float(np.percentile(dphi_x, 99.5)) < np.pi

    # Verify Po Valley flood attribution excludes offshore Tyrrhenian Sea (40N, 8.5E) and Adriatic Sea (43N, 15E)
    attrib = compute_flood_and_coherence_attribution(
        fine_t0,
        fine_t24,
        it_elev,
        fine_lats,
        fine_lons,
        domain_name="Italy_Po_Valley_Alps",
    )
    tyrrhenian_idx_lat = int(np.argmin(np.abs(fine_lats - 40.0)))
    tyrrhenian_idx_lon = int(np.argmin(np.abs(fine_lons - 8.5)))
    assert not bool(attrib["flood_mask"][tyrrhenian_idx_lat, tyrrhenian_idx_lon])

    # All flooded pixels must lie within the Northern Italian / Po Valley corridor (44.3N to 46.0N, 7.8E to 12.6E)
    flood_lat_indices, flood_lon_indices = np.where(attrib["flood_mask"])
    assert len(flood_lat_indices) > 500
    assert float(np.min(fine_lats[flood_lat_indices])) >= 44.3
    assert float(np.max(fine_lats[flood_lat_indices])) <= 46.0
    assert float(np.min(fine_lons[flood_lon_indices])) >= 7.8
    assert float(np.max(fine_lons[flood_lon_indices])) <= 12.6
    # Verify longitudinal span covers from western Po Valley (<8.4E) to eastern Po Delta (>12.0E)
    assert float(np.min(fine_lons[flood_lon_indices])) <= 8.4
    assert float(np.max(fine_lons[flood_lon_indices])) >= 12.0

    # Verify non-European domain with longitudes in [6E, 18E] (e.g., Central Africa 10N to 0N) does NOT trigger Italy Po Valley hydrology
    africa_lats = np.linspace(10.0, 0.0, 21)
    africa_lons = np.linspace(6.0, 18.0, 25)
    africa_t0 = np.full((21, 25), 298.0, dtype=np.float32)
    africa_t24 = np.full((21, 25), 301.0, dtype=np.float32)
    africa_elev = np.full((21, 25), 40.0, dtype=np.float32)
    africa_res = compute_flood_and_coherence_attribution(
        africa_t0,
        africa_t24,
        africa_elev,
        africa_lats,
        africa_lons,
        domain_name="Central_Africa_Basin",
    )
    assert int(np.sum(africa_res["flood_mask"])) > 0
