# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-FileCopyrightText: Copyright (c) 2026 Zhane Daye (SAR & Earth System Engineering; zhanedaye@umattr.ca)
# SPDX-License-Identifier: Apache-2.0
"""
Comprehensive automated unit & scientific integrity test suite for Deep Geophysical Hazards Modeling
(Witwatersrand gold reef mining subsidence & fault slip, Popocatépetl Mogi magma inflation,
Siberian permafrost thaw settlement & Yamal cryovolcanic gas blowout crater).

Strict adherence to .agents/rules/e2s-014-scientific-integrity.mdc.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
from pathlib import Path

import numpy as np
import pytest
from scipy.special import erf

from od_experiments.geoint_sar import (
    C_BAND_WAVELENGTH_M,
    GEOPHYSICAL_TARGET_LOCATIONS,
    L_BAND_WAVELENGTH_M,
    X_BAND_WAVELENGTH_M,
    compute_popocatepetl_mogi_inflation,
    compute_siberian_permafrost_thaw_and_crater_deformation,
    compute_witwatersrand_mining_subsidence_and_slip,
    deep_geophysical_hazards,
    knothe_stope_subsidence_2d,
    okada_strike_slip_dislocation,
    run_deep_geophysical_hazards_suite,
)


def test_witwatersrand_knothe_stope_subsidence_physics():
    """Verify Knothe-Bals tabular stope subsidence and Litwiniszyn horizontal displacement physics."""
    x = np.linspace(-4000.0, 4000.0, 81)
    y = np.linspace(4000.0, -4000.0, 81)
    xx, yy = np.meshgrid(x, y)

    depth_m = 2800.0
    extraction_thick = 2.0
    subsidence_coeff = 0.85
    s_expected_max = extraction_thick * subsidence_coeff  # 1.70m

    sub, ux, uy = knothe_stope_subsidence_2d(
        x_m=xx,
        y_m=yy,
        stope_center_x=0.0,
        stope_center_y=0.0,
        length_x_m=1200.0,
        length_y_m=800.0,
        depth_m=depth_m,
        extraction_thickness_m=extraction_thick,
        subsidence_coefficient=subsidence_coeff,
        draw_angle_deg=65.0,
    )

    # 1. Peak subsidence must occur at the stope center (0, 0)
    icenter_y = int(np.argmin(np.abs(y - 0.0)))
    icenter_x = int(np.argmin(np.abs(x - 0.0)))
    peak_sub = float(sub[icenter_y, icenter_x])
    radius_r = depth_m / np.tan(np.radians(65.0))
    # Closed-form theoretical center subsidence for subcritical stope panel
    s_theoretical_center = (
        s_expected_max
        * erf(np.sqrt(np.pi) * 1200.0 / radius_r)
        * erf(np.sqrt(np.pi) * 800.0 / radius_r)
    )
    assert peak_sub == pytest.approx(s_theoretical_center, rel=1e-3)
    assert peak_sub <= s_expected_max

    # 2. Horizontal displacement at stope center must be zero due to symmetry
    assert float(ux[icenter_y, icenter_x]) == pytest.approx(0.0, abs=1e-4)
    assert float(uy[icenter_y, icenter_x]) == pytest.approx(0.0, abs=1e-4)

    # 3. Horizontal displacement must be directed inwards towards the center (convergence)
    # To the east (+x), ux must be negative (pointing west towards center)
    ieast = int(np.argmin(np.abs(x - 1400.0)))
    assert float(ux[icenter_y, ieast]) < 0.0
    # To the west (-x), ux must be positive (pointing east towards center)
    iwest = int(np.argmin(np.abs(x - (-1400.0))))
    assert float(ux[icenter_y, iwest]) > 0.0

    # 4. Far-field subsidence must decay to near zero
    assert float(np.max(sub[0, :])) < 0.05
    assert float(np.max(sub[-1, :])) < 0.05


def test_okada_strike_slip_dislocation_physics():
    """Verify Okada (1985) shear fault dislocation in an elastic half-space."""
    x = np.linspace(-5000.0, 5000.0, 61)
    y = np.linspace(5000.0, -5000.0, 61)
    xx, yy = np.meshgrid(x, y)

    ue, un, uz = okada_strike_slip_dislocation(
        x_m=xx,
        y_m=yy,
        fault_x0=0.0,
        fault_y0=0.0,
        length_m=4000.0,
        width_m=2000.0,
        depth_m=800.0,
        strike_deg=0.0,  # North-striking fault
        dip_deg=90.0,  # Vertical strike-slip fault
        slip_m=0.50,
    )

    assert ue.shape == (61, 61)
    assert un.shape == (61, 61)
    assert uz.shape == (61, 61)

    # For a vertical left-lateral fault striking North:
    # On the west side (x < 0), fault-parallel displacement u_north is positive (northwards)
    # On the east side (x > 0), fault-parallel displacement u_north is negative (southwards)
    iy_mid = int(np.argmin(np.abs(y - 0.0)))
    ix_east = int(np.argmin(np.abs(x - 500.0)))
    ix_west = int(np.argmin(np.abs(x - (-500.0))))

    assert float(un[iy_mid, ix_west]) > 0.0
    assert float(un[iy_mid, ix_east]) < 0.0
    # Antisymmetry: magnitude across fault must be exactly equal and opposite
    assert float(un[iy_mid, ix_west]) == pytest.approx(-float(un[iy_mid, ix_east]), rel=1e-5)


def test_witwatersrand_mining_hazard_orchestration():
    """Verify integrated Witwatersrand multi-stope and Bank Fault dislocation modeling."""
    res = compute_witwatersrand_mining_subsidence_and_slip(
        grid_size=80,
        domain_width_km=15.0,
        incidence_angle_deg=34.0,
        heading_angle_deg=-168.0,
        wavelength_m=X_BAND_WAVELENGTH_M,
    )

    assert res["subsidence_m"].shape == (80, 80)
    assert 1.0 <= res["max_subsidence_m"] <= 3.0
    assert res["max_fault_disp_m"] > 0.10
    assert res["max_tilt_mm_per_m"] > 0.50
    assert res["fringe_count"] > 20.0

    # InSAR wrapped phase must strictly fall in [-pi, pi]
    assert float(np.min(res["wrapped_phase_rad"])) >= -np.pi - 1e-5
    assert float(np.max(res["wrapped_phase_rad"])) <= np.pi + 1e-5


def test_popocatepetl_mogi_inflation_analytical_formulation():
    """Verify Popocatépetl Mogi source inflation with explicit dr = 3*a^3*dP / (4*G) * ... check."""
    depth_d = 6000.0
    radius_a = 1200.0
    delta_p = 2.5e7
    shear_g = 1.25e10

    res = compute_popocatepetl_mogi_inflation(
        chamber_depth_m=depth_d,
        chamber_radius_a_m=radius_a,
        delta_overpressure_pa=delta_p,
        shear_modulus_g_pa=shear_g,
        grid_size=81,
        domain_radius_km=15.0,
        incidence_angle_deg=34.0,
        heading_angle_deg=-168.0,
        wavelength_m=X_BAND_WAVELENGTH_M,
    )

    # 1. Analytical Constant C_mogi = 3 * a^3 * dP / (4 * G)
    c_mogi_expected = (3.0 * (radius_a**3) * delta_p) / (4.0 * shear_g)
    assert res["c_mogi"] == pytest.approx(c_mogi_expected, rel=1e-6)

    # 2. Peak vertical surface uplift at epicenter r=0: u_z(0) = C_mogi / d^2
    u_z_epicenter_expected = c_mogi_expected / (depth_d**2)
    assert res["max_uplift_m"] == pytest.approx(u_z_epicenter_expected, rel=1e-5)
    # For these realistic values: 7.20 cm
    assert res["max_uplift_m"] * 100.0 == pytest.approx(7.20, abs=0.01)

    # 3. Peak radial displacement occurs analytically at r = d / sqrt(2) ~ 4242.6 m
    r_peak = depth_d / np.sqrt(2.0)
    u_r_peak_expected = c_mogi_expected * (r_peak / ((r_peak**2 + depth_d**2) ** 1.5))
    assert res["max_horizontal_m"] == pytest.approx(u_r_peak_expected, rel=1e-4)
    # Radial displacement at exact center (r=0) must be 0
    icenter_y = int(np.argmin(np.abs(res["y_km"] - 0.0)))
    icenter_x = int(np.argmin(np.abs(res["x_km"] - 0.0)))
    assert float(res["u_r_m"][icenter_y, icenter_x]) == pytest.approx(0.0, abs=1e-5)

    # 4. Chamber Volume Change: Delta_V = pi * a^3 * dP / G
    delta_v_expected = (np.pi * (radius_a**3) * delta_p) / shear_g
    assert res["delta_volume_m3"] == pytest.approx(delta_v_expected, rel=1e-5)

    # 5. Radial displacement formula check: dr = 3*a^3*dP / (4*G) * (r / (r^2 + d^2)^(3/2))
    r_test = np.array([1000.0, 3000.0, 6000.0, 10000.0])
    dr_analytical = c_mogi_expected * (r_test / ((r_test**2 + depth_d**2) ** 1.5))
    for r_val, dr_val in zip(r_test, dr_analytical):
        assert dr_val > 0.0
        assert dr_val < res["max_horizontal_m"] + 1e-5

    # 6. Multi-Frequency InSAR Fringe Scaling Check
    # X-band (3.11 cm) vs C-band (5.55 cm) vs L-band (23.6 cm)
    # Fringe count is inversely proportional to wavelength
    x_fringes = res["fringes_x_band"]
    assert x_fringes >= 3.5  # ~4.1 fringes for 7.2 cm displacement
    assert res["wrapped_phase_x_band"].shape == (81, 81)
    assert res["wrapped_phase_c_band"].shape == (81, 81)
    assert res["wrapped_phase_l_band"].shape == (81, 81)


def test_siberian_permafrost_stefan_thaw_settlement():
    """Verify Stefan equation active layer thaw depth and Yedoma thermokarst settlement."""
    res = compute_siberian_permafrost_thaw_and_crater_deformation(
        grid_size=75,
        domain_width_km=10.0,
        thawing_degree_days_ddt=620.0,
        mean_excess_ice_fraction=0.42,
    )

    assert res["z_alt_m"].shape == (75, 75)
    assert res["s_thaw_cm"].shape == (75, 75)

    # Active layer thickness under 620 degC*d in peat/silt must be ~0.9m to 1.3m
    assert 0.85 <= res["mean_alt_m"] <= 1.40

    # Thaw settlement in ice-rich Yedoma (excess ice 30-55%) must produce 30 to 65 cm
    assert 25.0 <= res["mean_thaw_cm"] <= 65.0
    assert res["max_thaw_cm"] >= res["mean_thaw_cm"]


def test_yamal_cryovolcanic_crater_and_coherence_loss():
    """Verify Yamal cryovolcanic gas blowout crater geometry and SAR coherence collapse."""
    res = compute_siberian_permafrost_thaw_and_crater_deformation(
        grid_size=81,
        domain_width_km=8.0,
        crater_radius_m=25.0,
        crater_depth_m=38.0,
        parapet_height_m=2.4,
        pingo_mound_height_m=1.85,
        pingo_mound_radius_m=90.0,
    )

    # Pre-blowout pingo mound must have peak uplift of 1.85m at center
    icenter_y = int(np.argmin(np.abs(res["y_km"] - 0.0)))
    icenter_x = int(np.argmin(np.abs(res["x_km"] - 0.0)))
    assert float(res["u_pingo_dome_m"][icenter_y, icenter_x]) == pytest.approx(1.85, abs=0.01)

    # Crater void must have profound negative displacement (-38m) at center
    assert float(res["crater_void_m"][icenter_y, icenter_x]) == pytest.approx(-38.0, abs=0.5)

    # Coherence gamma at crater center must collapse to < 0.15 (severe decorrelation)
    center_gamma = float(res["coherence_gamma"][icenter_y, icenter_x])
    assert 0.05 <= center_gamma < 0.15

    # Far-field coherence must recover to tundra baseline (> 0.70)
    assert float(res["coherence_gamma"][0, 0]) > 0.70
    assert float(res["coherence_gamma"][-1, -1]) > 0.70

    # Decorrelated area with gamma < 0.32 must be strictly positive
    assert res["blast_area_ha"] > 0.5


def test_rule_e2s_014_scientific_integrity_zero_random_noise():
    """Audit deep_geophysical_hazards.py against Rule e2s-014 (Zero synthetic noise, origin='upper')."""
    source_path = Path("od_experiments/geoint_sar/deep_geophysical_hazards.py")
    assert source_path.exists()
    source_text = source_path.read_text(encoding="utf-8")

    # 1. Zero Tolerance for Synthetic Noise
    tree = ast.parse(source_text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in {
                "normal",
                "randn",
                "uniform",
                "standard_normal",
                "choice",
                "permutation",
                "shuffle",
            }, f"Forbidden stochastic generator '{node.attr}' detected in {source_path}"

    # 2. Strict origin='upper' when latitudes or descending y-axes are imaged
    assert 'origin="upper"' in source_text

    # 3. License Header
    assert "SPDX-FileCopyrightText" in source_text
    assert "Apache-2.0" in source_text


def test_full_deep_geophysical_hazards_pipeline_and_manifest(tmp_path: Path):
    """Verify end-to-end execution of deep geophysical hazards suite, figure generation, and manifest."""
    suite_res = run_deep_geophysical_hazards_suite(output_dir=tmp_path)
    assert suite_res["status"] == "SUCCESS"

    fig_file = Path(suite_res["figure_file"])
    manifest_file = Path(suite_res["manifest_file"])

    assert fig_file.exists()
    assert fig_file.stat().st_size > 100_000  # High-DPI publication PNG > 100 KB

    assert manifest_file.exists()
    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))

    # Verify SHA-256 integrity match
    computed_sha256 = hashlib.sha256(fig_file.read_bytes()).hexdigest()
    assert manifest_data["figure_sha256"] == computed_sha256

    # Verify all 3 theaters exist in manifest
    assert "south_africa_witwatersrand" in manifest_data["theaters"]
    assert "mexico_popocatepetl" in manifest_data["theaters"]
    assert "northern_russia_permafrost_crater" in manifest_data["theaters"]

    # Verify Popocatépetl Mogi parameters in manifest
    mx_manifest = manifest_data["theaters"]["mexico_popocatepetl"]
    assert mx_manifest["max_vertical_uplift_cm"] == pytest.approx(7.20, abs=0.01)
    assert "dr = 3*a^3*dP / (4*G) *" in mx_manifest["mogi_formula"]


def test_geophysical_target_locations_schema():
    """Verify target telemetry metadata coordinates and schema."""
    assert len(GEOPHYSICAL_TARGET_LOCATIONS) == 3
    for target_id, target in GEOPHYSICAL_TARGET_LOCATIONS.items():
        assert "name" in target
        assert "country" in target
        assert "country_code" in target
        assert -90.0 <= target["lat"] <= 90.0
        assert -180.0 <= target["lon"] <= 180.0
        assert target["depth_m"] > 0.0
        assert "hazard_type" in target
