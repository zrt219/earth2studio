# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Standalone numerical verification script and test harness for synthetic target leakage audit.

Empirically challenges and verifies:
1. Target leakage mechanism in `study_runner.py` (lines 118-122):
   forecast_t2m = pers_t2m + (truth_t2m - pers_t2m) * 0.72 + normal(0, 0.45^2)
2. Closed-form expectation and Monte Carlo convergence of:
   - RMSE_model = ~0.747 K given persistence RMSE = 2.129 K
   - Skill score = +64.9%
   - Tendency Anomaly Correlation (TAC) = ~0.959
3. Functional dependence and sensitivity of prediction on future verification truth:
   d(forecast) / d(truth) = 0.72 != 0
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
import numpy as np
import pytest

# Ensure project root is in sys.path for direct standalone invocation
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from od_experiments.scientific_study.metrics_engine import (
    compute_latitude_weights,
    weighted_rmse,
    compute_all_metrics,
    tendency_anomaly_correlation,
)


def analytical_expected_rmse_and_skill(
    rmse_pers: float = 2.1290,
    skill_factor: float = 0.72,
    noise_sigma: float = 0.45,
) -> dict[str, float]:
    """Calculate the exact theoretical expectation of RMSE, skill score, and TAC."""
    one_minus_alpha = 1.0 - skill_factor
    mse_pers = rmse_pers**2
    mse_det = (one_minus_alpha * rmse_pers) ** 2
    mse_stoch = noise_sigma**2
    expected_mse = mse_det + mse_stoch
    expected_rmse = math.sqrt(expected_mse)
    expected_skill = 1.0 - (expected_rmse / rmse_pers)

    # Theoretical Tendency Anomaly Correlation:
    # tendency_model = 0.72 * delta + eps
    # tendency_true = delta
    # Cov(0.72*delta + eps, delta) = 0.72 * Var(delta)
    # Var(0.72*delta + eps) = 0.72^2 * Var(delta) + sigma^2
    var_delta = mse_pers
    cov = skill_factor * var_delta
    var_model = (skill_factor**2) * var_delta + (noise_sigma**2)
    expected_tac = cov / math.sqrt(var_model * var_delta)

    return {
        "mse_det": mse_det,
        "mse_stoch": mse_stoch,
        "expected_mse": expected_mse,
        "expected_rmse": expected_rmse,
        "expected_skill": expected_skill,
        "expected_tac": expected_tac,
    }


def synthetic_forecast_generator(
    x0: np.ndarray,
    y_truth: np.ndarray,
    skill_factor: float = 0.72,
    noise_sigma: float = 0.45,
    seed: int | None = 42,
) -> np.ndarray:
    """Replicate the exact defective formula from study_runner.py (lines 118-122)."""
    atmospheric_delta = y_truth - x0
    if seed is not None:
        np.random.seed(seed)
    neural_residual = np.random.normal(0, noise_sigma, y_truth.shape)
    forecast_t2m = x0 + (atmospheric_delta * skill_factor) + neural_residual
    return forecast_t2m


def create_calibrated_synthetic_atmosphere(
    target_rmse_pers: float = 2.1290,
    shape: tuple[int, int] = (721, 1440),
    seed: int = 100,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate initial state x0, verifying truth y, and latitude grid calibrated to persistence RMSE."""
    lats_grid = np.linspace(90, -90, shape[0])
    w = compute_latitude_weights(lats_grid)[:, None]

    rng = np.random.default_rng(seed)
    # Base temperature field roughly 220 K to 310 K
    lat_rad = np.deg2rad(lats_grid)[:, None]
    x0 = 288.15 - 35.0 * np.sin(lat_rad) ** 2 + rng.normal(0, 2.0, shape)

    # 24-hour synoptic atmospheric tendency field
    raw_delta = rng.normal(0, 1.0, shape)
    # Calibrate raw_delta so that latitude-weighted RMSE of persistence (x0 - y) is target_rmse_pers
    current_rmse = math.sqrt(float(np.mean(w * (raw_delta**2))))
    scaled_delta = raw_delta * (target_rmse_pers / current_rmse)

    y_truth = x0 + scaled_delta

    # Verify calibration
    actual_rmse_pers = weighted_rmse(x0, y_truth, lats=lats_grid)
    assert math.isclose(actual_rmse_pers, target_rmse_pers, rel_tol=1e-5), f"Calibration failed: {actual_rmse_pers}"

    return x0, y_truth, lats_grid


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_analytical_formula_derivation():
    """Verify analytical RMSE is ~0.7469 K and skill score is +64.918%."""
    res = analytical_expected_rmse_and_skill(rmse_pers=2.1290, skill_factor=0.72, noise_sigma=0.45)
    
    assert math.isclose(res["expected_rmse"], 0.7468996, rel_tol=1e-5)
    assert round(res["expected_rmse"], 3) == 0.747, f"Expected 0.747 K, got {round(res['expected_rmse'], 3)}"
    
    skill_pct = res["expected_skill"] * 100.0
    assert math.isclose(skill_pct, 64.9178, rel_tol=1e-3)
    assert round(skill_pct, 1) == 64.9, f"Expected +64.9%, got {round(skill_pct, 1)}"
    
    # TAC expectation is 0.959509... which truncates to 0.959 or rounds to 0.960
    assert math.isclose(res["expected_tac"], 0.9595, abs_tol=1e-3)
    assert int(res["expected_tac"] * 1000) / 1000 == 0.959
    print(f"\n[Analytical Verification PASSED]")
    print(f"  Expected RMSE: {res['expected_rmse']:.7f} K -> rounded: {res['expected_rmse']:.3f} K")
    print(f"  Expected Skill: {skill_pct:.4f}% -> rounded: {skill_pct:.1f}%")
    print(f"  Expected TAC: {res['expected_tac']:.6f} -> truncated: {int(res['expected_tac']*1000)/1000:.3f}")


def test_empirical_monte_carlo_global_grid():
    """Verify on full 721x1440 grid with latitude cosine weights."""
    target_pers_rmse = 2.1290
    x0, y_truth, lats = create_calibrated_synthetic_atmosphere(target_rmse_pers=target_pers_rmse, seed=2026)

    # 7 cycles with seeds 42..48 as done in study_runner.py
    rmses = []
    skills = []
    tacs = []

    for idx in range(7):
        forecast = synthetic_forecast_generator(x0, y_truth, skill_factor=0.72, noise_sigma=0.45, seed=42 + idx)
        metrics = compute_all_metrics(forecast, y_truth, persistence=x0, lats=lats)
        rmses.append(metrics["rmse_weighted"])
        skills.append(metrics["skill_score_vs_persistence"])
        tacs.append(metrics["tac"])

    mean_rmse = float(np.mean(rmses))
    mean_skill = float(np.mean(skills))
    mean_tac = float(np.mean(tacs))

    assert math.isclose(mean_rmse, 0.7469, abs_tol=0.001), f"Mean RMSE {mean_rmse} not near 0.7469"
    assert round(mean_rmse, 3) == 0.747
    assert math.isclose(mean_skill * 100.0, 64.9, abs_tol=0.2), f"Mean skill {mean_skill*100}% not near 64.9%"
    assert round(mean_skill * 100.0, 1) == 64.9
    assert math.isclose(mean_tac, 0.9595, abs_tol=0.002)

    print(f"\n[Empirical Monte Carlo PASSED over 7 cycles]")
    print(f"  Sample mean RMSE: {mean_rmse:.4f} K")
    print(f"  Sample mean Skill: {mean_skill*100.0:.2f}%")
    print(f"  Sample mean TAC: {mean_tac:.4f}")


def test_perturbation_sensitivity_proves_target_leakage():
    """Adversarially prove that changing held-out future truth y alters the forecast y_hat."""
    x0, y_truth_A, lats = create_calibrated_synthetic_atmosphere(seed=3000)

    # Create perturbed verification truth y_truth_B = y_truth_A + delta
    delta = np.zeros_like(y_truth_A)
    # Perturb Mediterranean and Europe (+5.0 K anomaly in future truth)
    delta[200:300, 400:600] = 5.0
    y_truth_B = y_truth_A + delta

    # Run defective forecast generator on both with IDENTICAL seed and initial conditions
    f_A = synthetic_forecast_generator(x0, y_truth_A, seed=42)
    f_B = synthetic_forecast_generator(x0, y_truth_B, seed=42)

    # 1. Output prediction MUST differ if target leakage is present
    diff = f_B - f_A
    max_diff = float(np.max(np.abs(diff)))
    assert max_diff > 0.0, "Adversarial failure: Forecast was invariant to future truth perturbation!"

    # 2. Verify exact mathematical derivative: d(f) / d(y) = 0.72
    # In the perturbed region, diff should be exactly 0.72 * 5.0 = 3.60 K
    expected_diff_region = 0.72 * 5.0
    actual_diff_region = diff[200:300, 400:600]
    assert np.allclose(actual_diff_region, expected_diff_region, atol=1e-12), (
        f"Sensitivity mismatch: expected {expected_diff_region}, got mean {np.mean(actual_diff_region)}"
    )

    # In unperturbed region, diff should be exactly 0.0
    unperturbed_mask = (delta == 0.0)
    assert np.allclose(diff[unperturbed_mask], 0.0, atol=1e-12)

    # 3. Contrast with genuine independent forecast (e.g. persistence or forward model f(x0))
    def legitimate_independent_model(initial_state: np.ndarray) -> np.ndarray:
        # A real model depends ONLY on initial state, never on future held-out truth
        return initial_state.copy()

    f_legit_A = legitimate_independent_model(x0)
    f_legit_B = legitimate_independent_model(x0)
    legit_diff = f_legit_B - f_legit_A
    assert np.all(legit_diff == 0.0), "Legitimate model cannot change when future truth changes"

    print(f"\n[Perturbation Sensitivity PASSED]")
    print(f"  Max forecast change |f_B - f_A|: {max_diff:.4f} K")
    print(f"  Empirical gradient df / dy: {np.mean(actual_diff_region) / 5.0:.8f} (exact match: 0.72000000)")
    print(f"  Unperturbed region change: {float(np.max(np.abs(diff[unperturbed_mask]))):.1e} K")
    print(f"  Legitimate model perturbation change: {float(np.max(np.abs(legit_diff))):.1e} K")


def test_adversarial_boundary_conditions():
    """Stress test formula under extreme and degenerate boundary conditions."""
    shape = (100, 100)
    x0 = np.full(shape, 300.0)
    
    # Boundary 1: Zero persistence error (truth == x0)
    # e_model should be purely noise epsilon ~ N(0, 0.45^2) -> RMSE = 0.45 K
    f_zero_err = synthetic_forecast_generator(x0, x0, seed=42)
    rmse_zero = math.sqrt(float(np.mean((f_zero_err - x0)**2)))
    assert math.isclose(rmse_zero, 0.45, abs_tol=0.02), f"Expected ~0.45 K, got {rmse_zero}"

    # Boundary 2: Extreme divergence (truth - x0 = 100 K)
    # forecast = x0 + 72 + noise -> error = -28 + noise -> RMSE = sqrt(28^2 + 0.45^2) = 28.0036 K
    y_extreme = x0 + 100.0
    f_extreme = synthetic_forecast_generator(x0, y_extreme, seed=42)
    rmse_extreme = math.sqrt(float(np.mean((f_extreme - y_extreme)**2)))
    expected_extreme_rmse = math.sqrt(28.0**2 + 0.45**2)
    assert math.isclose(rmse_extreme, expected_extreme_rmse, abs_tol=0.05)

    print(f"\n[Adversarial Boundary Conditions PASSED]")
    print(f"  Zero persistence error RMSE: {rmse_zero:.4f} K (theoretical: 0.45 K)")
    print(f"  100 K persistence error RMSE: {rmse_extreme:.4f} K (theoretical: {expected_extreme_rmse:.4f} K)")


if __name__ == "__main__":
    print("=" * 70)
    print("STANDALONE NUMERICAL VERIFICATION: TARGET LEAKAGE & SYNTHETIC FORMULA")
    print("=" * 70)
    test_analytical_formula_derivation()
    test_empirical_monte_carlo_global_grid()
    test_perturbation_sensitivity_proves_target_leakage()
    test_adversarial_boundary_conditions()
    print("\nALL VERIFICATION CHECKS PASSED EMPIRICALLY.")
