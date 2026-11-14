# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-FileCopyrightText: Copyright (c) 2026 Zhane Daye (SAR & Earth System Engineering; zhanedaye@umattr.ca)
# SPDX-License-Identifier: Apache-2.0
"""
Automated Unit & Scientific Integrity Test Suite for Multi-Band InSAR Comparative Physics
(X-Band 9.65 GHz, C-Band 5.405 GHz, L-Band 1.27 GHz across South Africa, Mexico, and Northern Russia).

Strict adherence to .agents/rules/e2s-014-scientific-integrity.mdc:
  - Zero synthetic noise / AST token audit
  - Deterministic execution & cryptographic SHA-256 verification
  - Explicit origin='upper' geospatial mapping
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import numpy as np
import pytest

from od_experiments.geoint_sar import (
    BIOME_DECORRELATION_MODELS,
    C_BAND_FREQUENCY_HZ,
    C_BAND_HALF_WAVELENGTH_M,
    C_BAND_WAVELENGTH_M,
    L_BAND_FREQUENCY_HZ,
    L_BAND_HALF_WAVELENGTH_M,
    L_BAND_WAVELENGTH_M,
    MULTIBAND_SPECS,
    PENETRATION_MEDIA_MODELS,
    X_BAND_FREQUENCY_HZ,
    X_BAND_WAVELENGTH_M,
    multiband_sar_comparison,
)
from od_experiments.geoint_sar.multiband_sar_comparison import (
    compute_all_bands_insar_simulation,
    compute_all_bands_temporal_decorrelation,
    compute_electromagnetic_penetration_depth,
    compute_multiband_insar_phase,
    compute_temporal_decorrelation_decay,
    run_multiband_sar_comparison,
    simulate_mexico_multiband,
    simulate_russia_multiband,
    simulate_south_africa_multiband,
)


def test_multiband_frequencies_and_wavelengths():
    """Verify physical carrier frequencies, wavelengths, and half-wavelength fringe spacing."""
    # X-Band (9.65 GHz, 3.11 cm)
    assert X_BAND_FREQUENCY_HZ == pytest.approx(9.65e9, rel=1e-5)
    assert X_BAND_WAVELENGTH_M == pytest.approx(0.031066576, abs=1e-5)
    assert (X_BAND_WAVELENGTH_M * 100.0) == pytest.approx(3.1067, abs=1e-3)
    assert (X_BAND_WAVELENGTH_M / 2.0 * 100.0) == pytest.approx(1.5533, abs=1e-3)

    # C-Band (5.405 GHz, 5.55 cm)
    assert C_BAND_FREQUENCY_HZ == pytest.approx(5.405e9, rel=1e-5)
    assert C_BAND_WAVELENGTH_M == pytest.approx(0.055465765, abs=1e-5)
    assert (C_BAND_WAVELENGTH_M * 100.0) == pytest.approx(5.5466, abs=1e-3)
    assert C_BAND_HALF_WAVELENGTH_M * 100.0 == pytest.approx(2.7733, abs=1e-3)

    # L-Band (1.27 GHz, 23.6 cm)
    assert L_BAND_FREQUENCY_HZ == pytest.approx(1.27e9, rel=1e-5)
    assert L_BAND_WAVELENGTH_M == pytest.approx(0.236057054, abs=1e-5)
    assert (L_BAND_WAVELENGTH_M * 100.0) == pytest.approx(23.6057, abs=1e-3)
    assert L_BAND_HALF_WAVELENGTH_M * 100.0 == pytest.approx(11.8029, abs=1e-3)

    # Cross-band scaling ratios (fundamental physical invariant)
    assert (L_BAND_WAVELENGTH_M / X_BAND_WAVELENGTH_M) == pytest.approx(
        7.5986, abs=1e-3
    )
    assert (L_BAND_WAVELENGTH_M / C_BAND_WAVELENGTH_M) == pytest.approx(
        4.2559, abs=1e-3
    )
    assert (C_BAND_WAVELENGTH_M / X_BAND_WAVELENGTH_M) == pytest.approx(
        1.7854, abs=1e-3
    )

    # Registry validation
    for band in ["X", "C", "L"]:
        assert band in MULTIBAND_SPECS
        assert len(MULTIBAND_SPECS[band]["missions"]) >= 2
        assert MULTIBAND_SPECS[band]["typical_incidence_deg"] >= 25.0


def test_multiband_tropospheric_phase_and_fringe_scaling():
    """Verify Delta_phi = 4*pi/lambda * Delta_R and inverse fringe density scaling."""
    # 0.50m differential slant delay
    delta_ztd = np.array([[0.0, 0.25], [0.50, 0.50]], dtype=np.float32)
    incidence_deg = 34.1  # cos(34.1 deg) ~ 0.82806

    res_x = compute_multiband_insar_phase(
        delta_ztd, incidence_deg=incidence_deg, wavelength_m=X_BAND_WAVELENGTH_M
    )
    res_c = compute_multiband_insar_phase(
        delta_ztd, incidence_deg=incidence_deg, wavelength_m=C_BAND_WAVELENGTH_M
    )
    res_l = compute_multiband_insar_phase(
        delta_ztd, incidence_deg=incidence_deg, wavelength_m=L_BAND_WAVELENGTH_M
    )

    # Wrapped phase bounds check [-pi, +pi]
    assert np.all(res_x["phase_wrapped_rad"] >= -np.pi - 1e-5)
    assert np.all(res_x["phase_wrapped_rad"] <= np.pi + 1e-5)
    assert np.all(res_c["phase_wrapped_rad"] >= -np.pi - 1e-5)
    assert np.all(res_c["phase_wrapped_rad"] <= np.pi + 1e-5)
    assert np.all(res_l["phase_wrapped_rad"] >= -np.pi - 1e-5)
    assert np.all(res_l["phase_wrapped_rad"] <= np.pi + 1e-5)

    # Fringe count must scale strictly inverse to wavelength
    assert res_x["fringe_count"] > res_c["fringe_count"] > res_l["fringe_count"]

    ratio_x_to_l = res_x["fringe_count"] / res_l["fringe_count"]
    expected_ratio_x_l = L_BAND_WAVELENGTH_M / X_BAND_WAVELENGTH_M
    assert ratio_x_to_l == pytest.approx(expected_ratio_x_l, rel=0.01)

    ratio_c_to_l = res_c["fringe_count"] / res_l["fringe_count"]
    expected_ratio_c_l = L_BAND_WAVELENGTH_M / C_BAND_WAVELENGTH_M
    assert ratio_c_to_l == pytest.approx(expected_ratio_c_l, rel=0.01)


def test_spatial_nyquist_phase_gradient_hazard():
    """Verify X-band phase aliasing hazard (|grad| >= pi rad/px) vs L-band safety margin."""
    # Steep cliff with rapid delay step: 0.025m delay drop over 1 pixel
    delay_step = np.array([[0.0, 0.025]], dtype=np.float32)

    sim = compute_all_bands_insar_simulation(delay_step, incidence_deg=35.0)

    grad_x = sim["X"]["max_gradient_rad"]
    grad_c = sim["C"]["max_gradient_rad"]
    grad_l = sim["L"]["max_gradient_rad"]

    # Gradient hierarchy
    assert grad_x > grad_c > grad_l

    # X-band phase step exceeds Nyquist limit (pi rad = 3.14159)
    assert grad_x >= np.pi
    assert sim["X"]["nyquist_violation_fraction"] == 1.0

    # L-band phase step is far below the Nyquist limit (~0.4 - 0.9 rad)
    assert grad_l < np.pi
    assert sim["L"]["nyquist_violation_fraction"] == 0.0

    # Gradient ratio must follow inverse wavelength ratio
    assert grad_x / grad_l == pytest.approx(
        L_BAND_WAVELENGTH_M / X_BAND_WAVELENGTH_M, rel=0.01
    )


def test_vegetation_temporal_decorrelation_decay_across_biomes():
    """Verify temporal decorrelation decay curves, half-lives, and hierarchy (gamma_L > gamma_C > gamma_X)."""
    time_days = np.linspace(0.0, 60.0, 121)

    for biome in ["south_africa_savanna", "mexico_pine_oak", "russia_taiga_tundra"]:
        assert biome in BIOME_DECORRELATION_MODELS
        single_x = compute_temporal_decorrelation_decay(
            time_days, band="X", biome=biome
        )
        assert len(single_x["coherence"]) == len(time_days)

        decorr = compute_all_bands_temporal_decorrelation(time_days, biome=biome)

        coh_x = decorr["X"]["coherence"]
        coh_c = decorr["C"]["coherence"]
        coh_l = decorr["L"]["coherence"]

        # Initial coherence at t=0 must be 1.0
        assert coh_x[0] == pytest.approx(1.0, abs=1e-4)
        assert coh_c[0] == pytest.approx(1.0, abs=1e-4)
        assert coh_l[0] == pytest.approx(1.0, abs=1e-4)

        # Monotonic decay over time
        assert np.all(np.diff(coh_x) <= 1e-6)
        assert np.all(np.diff(coh_c) <= 1e-6)
        assert np.all(np.diff(coh_l) <= 1e-6)

        # Fundamental physical ordering: gamma_L > gamma_C >= gamma_X for all t > 0
        assert np.all(coh_l[1:] > coh_c[1:])
        assert np.all(coh_c[1:] >= coh_x[1:])
        # Before reaching asymptotic noise floor (t <= 20 days), coh_c strictly exceeds coh_x
        active_t = time_days[1:] <= 20.0
        assert np.all(coh_c[1:][active_t] > coh_x[1:][active_t])

        # Half-life ordering: tau_L >> tau_C > tau_X
        tau_half_x = decorr["X"]["half_life_days"]
        tau_half_c = decorr["C"]["half_life_days"]
        tau_half_l = decorr["L"]["half_life_days"]
        assert tau_half_l > (10.0 * tau_half_x)
        assert tau_half_c > tau_half_x

        # At 12-day NISAR repeat cycle: L-band must maintain usable coherence (> 0.65)
        assert decorr["L"]["coherence_at_12d"] >= 0.70

    # Cross-biome check: dense humid Mexican pine-oak forest decorrelates faster than semi-arid Savanna
    decorr_sa = compute_all_bands_temporal_decorrelation(
        time_days, biome="south_africa_savanna"
    )
    decorr_mx = compute_all_bands_temporal_decorrelation(
        time_days, biome="mexico_pine_oak"
    )
    assert decorr_mx["X"]["half_life_days"] < decorr_sa["X"]["half_life_days"]
    assert decorr_mx["C"]["half_life_days"] < decorr_sa["C"]["half_life_days"]


def test_electromagnetic_penetration_depth_physics():
    """Verify radar penetration depths across natural media (delta_p_L > delta_p_C > delta_p_X)."""
    for medium in ["forest_canopy", "dry_soil_sand", "wet_soil", "permafrost_ice_snow"]:
        assert medium in PENETRATION_MEDIA_MODELS
        depths = compute_electromagnetic_penetration_depth(medium)["depths_m"]

        d_x = depths["X"]
        d_c = depths["C"]
        d_l = depths["L"]

        # Hierarchy invariant
        assert d_l > d_c > d_x

        # Exact positive bounds
        assert d_x > 0.0
        assert d_c > 0.0
        assert d_l > 0.0

    # Canopy penetration: X-band outer crown, C-band mid-canopy, L-band sub-canopy ground
    canopy = compute_electromagnetic_penetration_depth("forest_canopy")["depths_m"]
    assert canopy["X"] < 1.0  # Crown scattering only
    assert 1.0 <= canopy["C"] <= 4.0  # Upper-to-mid canopy
    assert canopy["L"] >= 8.0  # Full canopy penetration to ground surface

    # Dry soil / sand: L-band achieves deep subsurface penetration (> 1m)
    sand = compute_electromagnetic_penetration_depth("dry_soil_sand")["depths_m"]
    assert sand["X"] <= 0.20  # Surface skin
    assert sand["L"] >= 1.0  # Deep subsurface

    # Cold snow & permafrost: L-band penetrates > 15m
    ice = compute_electromagnetic_penetration_depth("permafrost_ice_snow")["depths_m"]
    assert ice["X"] <= 4.0  # Grain Rayleigh scattering
    assert ice["L"] >= 20.0  # Bedrock / deep permafrost penetration


def test_regional_simulations_south_africa_mexico_russia():
    """Verify multi-band simulation execution across all three regional target theaters."""
    # Deterministic global test state
    lats = np.linspace(90.0, -90.0, 181)
    lons = np.linspace(0.0, 360.0, 360, endpoint=False)
    lat_r = np.deg2rad(lats)[:, None]
    lon_r = np.deg2rad(lons)[None, :]
    t0 = (
        288.0 + 20.0 * np.cos(lat_r) + 3.0 * np.sin(2.0 * lat_r) * np.cos(3.0 * lon_r)
    ).astype(np.float32)
    t24 = (
        288.0
        + 20.0 * np.cos(lat_r)
        + 3.0 * np.sin(2.0 * lat_r) * np.cos(3.0 * (lon_r - np.deg2rad(10.0)))
    ).astype(np.float32)

    # South Africa
    sa = simulate_south_africa_multiband(t0, t24, lats, lons)
    assert sa["theater"] == "south_africa_drakensberg"
    assert sa["metrics"]["max_elevation_m"] >= 3400.0
    assert (
        sa["metrics"]["fringes_X"]
        > sa["metrics"]["fringes_C"]
        > sa["metrics"]["fringes_L"]
    )
    assert sa["metrics"]["fringe_ratio_X_to_L"] == pytest.approx(7.60, abs=0.25)

    # Mexico
    mx = simulate_mexico_multiband(t0, t24, lats, lons)
    assert mx["theater"] == "mexico_volcanic_belt"
    assert mx["metrics"]["max_elevation_m"] >= 5400.0
    assert (
        mx["metrics"]["fringes_X"]
        > mx["metrics"]["fringes_C"]
        > mx["metrics"]["fringes_L"]
    )
    assert mx["metrics"]["fringe_ratio_X_to_L"] == pytest.approx(7.60, abs=0.25)

    # Northern Russia
    ru = simulate_russia_multiband(t0, t24, lats, lons)
    assert ru["theater"] == "russia_putorana"
    assert ru["metrics"]["max_elevation_m"] >= 1500.0
    assert (
        ru["metrics"]["fringes_X"]
        > ru["metrics"]["fringes_C"]
        > ru["metrics"]["fringes_L"]
    )
    assert ru["metrics"]["fringe_ratio_X_to_L"] == pytest.approx(7.60, abs=0.25)


def test_rule_e2s_014_zero_synthetic_noise_multiband():
    """Verify multiband_sar_comparison.py contains zero pseudo-random noise generators."""
    src = inspect.getsource(multiband_sar_comparison)
    forbidden = ["np.random", "random.normal", "random.uniform", "randn", "default_rng"]
    for token in forbidden:
        assert token not in src, (
            f"Forbidden synthetic noise generator '{token}' detected in multiband_sar_comparison.py"
        )


def test_origin_upper_in_geospatial_plots():
    """Verify all geospatial imshow calls strictly configure origin='upper' per Rule e2s-014."""
    src = inspect.getsource(multiband_sar_comparison)
    lines = [line.strip() for line in src.splitlines()]
    imshow_lines = [i for i, line in enumerate(lines) if "imshow(" in line]

    assert len(imshow_lines) >= 3, (
        "Expected at least 3 imshow calls for multi-band maps"
    )
    for idx in imshow_lines:
        # Check that origin="upper" is configured within the imshow call block (next 10 lines)
        block = " ".join(lines[idx : idx + 10])
        assert 'origin="upper"' in block or "origin='upper'" in block, (
            f"imshow at line {idx + 1} does not specify explicit origin='upper'"
        )


def test_multiband_determinism_and_artifact_integrity(tmp_path: Path):
    """Verify end-to-end execution, determinism, and SHA-256 cryptographic sealing."""
    # Execute run 1
    m1 = run_multiband_sar_comparison(output_dir=tmp_path / "run1")
    # Execute run 2
    m2 = run_multiband_sar_comparison(output_dir=tmp_path / "run2")

    # Figure and manifest existence
    fig1 = Path(m1["figure_file"])
    fig2 = Path(m2["figure_file"])
    assert fig1.exists() and fig1.stat().st_size > 100_000
    assert fig2.exists() and fig2.stat().st_size > 100_000

    # Cryptographic determinism
    assert m1["figure_sha256"] == m2["figure_sha256"]
    assert m1["regional_metrics"] == m2["regional_metrics"]
    assert (
        m1["vegetation_decorrelation_summary"] == m2["vegetation_decorrelation_summary"]
    )
    assert m1["penetration_depths_summary_m"] == m2["penetration_depths_summary_m"]

    # Manifest json validation
    manifest_file = tmp_path / "run1" / "multiband_sar_manifest.json"
    assert manifest_file.exists()
    loaded = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert loaded["study_id"] == "OD-EARTH2-MULTIBAND-SAR-COMPARISON"
    assert "Rule e2s-014 Certified" in loaded["compliance"]
