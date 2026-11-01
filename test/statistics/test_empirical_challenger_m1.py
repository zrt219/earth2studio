# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
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

"""Empirical Challenger Verification Suite for Milestone 1 / Pillar A.

Adversarial stress-testing, analytical benchmarks, invariance verification,
and edge-case exploration for CRPS and Spread-Skill Ratio (SSR).

Author: Challenger Agent (teamwork_challenger)
Target: earth2studio/statistics/crps.py, earth2studio/statistics/rmse.py,
        od_experiments/scientific_study/metrics_engine.py
"""

from __future__ import annotations

import math
import time
from collections import OrderedDict

import numpy as np
import pytest
import torch

from earth2studio.statistics import crps, spread_skill_ratio
from earth2studio.statistics.crps import compute_crps
from od_experiments.scientific_study.metrics_engine import (
    crps_ensemble,
)
from od_experiments.scientific_study.metrics_engine import (
    spread_skill_ratio as engine_ssr,
)

# ==============================================================================
# Helper Oracles
# ==============================================================================


def gaussian_crps_analytical(
    mu: float | np.ndarray,
    sigma: float | np.ndarray,
    y: float | np.ndarray,
) -> float | np.ndarray:
    """Exact closed-form CRPS for Gaussian distribution F ~ N(mu, sigma^2).

    Formula (Gneiting & Raftery 2007, eq. 5):
        CRPS(N(mu, sigma^2), y) = sigma * [ z * (2*Phi(z) - 1) + 2*phi(z) - 1/sqrt(pi) ]
    where z = (y - mu) / sigma, phi is standard normal PDF, Phi is standard normal CDF.
    """
    mu = np.asarray(mu, dtype=np.float64)
    sigma = np.asarray(sigma, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)

    z = (y - mu) / sigma
    phi_z = np.exp(-0.5 * z**2) / np.sqrt(2.0 * np.pi)
    Phi_z = 0.5 * (1.0 + np.vectorize(math.erf)(z / np.sqrt(2.0)))

    return sigma * (z * (2.0 * Phi_z - 1.0) + 2.0 * phi_z - 1.0 / np.sqrt(np.pi))


# ==============================================================================
# Focus 1: Analytical Gaussian Benchmark
# ==============================================================================


class TestAnalyticalGaussianBenchmark:
    """Compare numerical Monte Carlo CRPS of large ensemble against closed-form Gaussian solution."""

    def test_gaussian_benchmark_standard_normal_zero_observation(self):
        """CRPS(N(0, 1), 0) = (sqrt(2) - 1) / sqrt(pi) ~ 0.23369464."""
        torch.manual_seed(1001)
        M = 100_000
        samples = torch.randn(M, 1, dtype=torch.float64)
        truth = torch.zeros(1, dtype=torch.float64)

        expected = (math.sqrt(2.0) - 1.0) / math.sqrt(math.pi)

        # Fair CRPS (unbiased estimator)
        score_fair = compute_crps(samples, truth, dim=0, fair=True).item()
        # Standard CRPS (has 1 / (M * sqrt(pi)) finite-sample bias)
        score_std = compute_crps(samples, truth, dim=0, fair=False).item()

        # Statistical tolerance: SE ~ sigma / sqrt(M) ~ 1 / 316 ~ 0.003
        assert abs(score_fair - expected) < 0.005, (
            f"Fair CRPS {score_fair} deviates from analytical {expected}"
        )
        assert abs(score_std - expected) < 0.005, (
            f"Standard CRPS {score_std} deviates from analytical {expected}"
        )

        # Standard CRPS must exceed Fair CRPS by approximately 1 / (M * sqrt(pi))
        diff = score_std - score_fair
        expected_diff = 1.0 / (M * math.sqrt(math.pi))
        assert diff > 0, "Standard CRPS should be strictly greater than Fair CRPS"
        assert abs(diff - expected_diff) < 1e-6

    @pytest.mark.parametrize(
        "mu,sigma,y",
        [
            (280.0, 5.0, 280.0),  # z = 0, centered
            (280.0, 5.0, 285.0),  # z = +1.0
            (280.0, 5.0, 270.0),  # z = -2.0
            (15.0, 2.5, 20.0),  # z = +2.0
            (0.0, 10.0, -15.0),  # z = -1.5
        ],
    )
    def test_gaussian_benchmark_arbitrary_parameters(
        self, mu: float, sigma: float, y: float
    ):
        """Verify arbitrary (mu, sigma, y) against closed-form Gneiting & Raftery oracle."""
        analytical = gaussian_crps_analytical(mu, sigma, y)

        torch.manual_seed(2024)
        M = 80_000
        samples = mu + sigma * torch.randn(M, 1, dtype=torch.float64)
        truth = torch.tensor([y], dtype=torch.float64)

        score_fair = compute_crps(samples, truth, dim=0, fair=True).item()
        score_std = compute_crps(samples, truth, dim=0, fair=False).item()

        rel_err_fair = abs(score_fair - analytical) / analytical
        rel_err_std = abs(score_std - analytical) / analytical

        assert rel_err_fair < 0.015, (
            f"Fair CRPS {score_fair} vs analytical {analytical} (rel err: {rel_err_fair:.4%})"
        )
        assert rel_err_std < 0.015, (
            f"Std CRPS {score_std} vs analytical {analytical} (rel err: {rel_err_std:.4%})"
        )

    def test_metrics_engine_crps_gaussian_benchmark(self):
        """Verify od_experiments/scientific_study/metrics_engine.py crps_ensemble against oracle."""
        mu, sigma, y = 285.0, 4.0, 287.0
        analytical = gaussian_crps_analytical(mu, sigma, y)

        np.random.seed(42)
        M = 60_000
        forecast = mu + sigma * np.random.randn(M, 1, 1).astype(np.float32)
        truth = np.array([[y]], dtype=np.float32)

        res_fair = crps_ensemble(forecast, truth, fair=True, ensemble_axis=0)
        res_std = crps_ensemble(forecast, truth, fair=False, ensemble_axis=0)

        assert abs(res_fair - analytical) / analytical < 0.02
        assert abs(res_std - analytical) / analytical < 0.02


# ==============================================================================
# Focus 2: Singleton Property (M=1)
# ==============================================================================


class TestSingletonProperty:
    """Verify that when M=1, CRPS identically reduces to MAE |x - y|."""

    @pytest.mark.parametrize("shape", [(1, 10, 10), (1, 1), (1, 5, 20, 30)])
    def test_singleton_equals_mae_tensor(self, shape: tuple[int, ...]):
        torch.manual_seed(42)
        x = torch.randn(shape, dtype=torch.float64) * 20.0 + 273.15
        y = torch.randn(shape[1:], dtype=torch.float64) * 20.0 + 273.15

        crps_val = compute_crps(x, y, dim=0, fair=False)
        mae_val = torch.abs(x.squeeze(0) - y)

        assert torch.allclose(crps_val, mae_val, atol=1e-12, rtol=1e-12), (
            f"Max absolute discrepancy: {torch.max(torch.abs(crps_val - mae_val)).item()}"
        )

    def test_singleton_non_zero_dim(self):
        """Verify singleton property when ensemble dimension is not 0."""
        torch.manual_seed(42)
        # Shape: (batch=5, ensemble=1, lat=4, lon=6)
        x = torch.randn(5, 1, 4, 6)
        y = torch.randn(5, 4, 6)

        crps_val = compute_crps(x, y, dim=1, fair=False)
        mae_val = torch.abs(x.squeeze(1) - y)

        assert torch.allclose(crps_val, mae_val, atol=1e-7, rtol=1e-7)

    def test_singleton_fair_discrepancy_inspection(self):
        """Investigate fair CRPS behavior on M=1 across implementations.

        Finding:
        - In earth2studio/statistics/crps.py: line 71 returns term1 (MAE) before
          checking fair M >= 2, so it returns MAE without raising.
        - In od_experiments/scientific_study/metrics_engine.py: line 201 explicitly
          raises ValueError("Fair CRPS requires at least M >= 2 ensemble members.").
        This test documents the empirical divergence between the two modules.
        """
        x = torch.randn(1, 10)
        y = torch.randn(10)

        # 1. earth2studio.statistics.crps raises ValueError on fair M < 2
        with pytest.raises(ValueError, match="Fair CRPS requires at least M >= 2"):
            compute_crps(x, y, dim=0, fair=True)

        # 2. metrics_engine.crps_ensemble raises ValueError on fair M < 2
        with pytest.raises(ValueError, match="Fair CRPS requires at least M >= 2"):
            crps_ensemble(x.numpy(), y.numpy(), fair=True)


# ==============================================================================
# Focus 3: Invariances (Translation & Scale)
# ==============================================================================


class TestInvariances:
    """Verify Translation Invariance and Scale Equivariance."""

    @pytest.mark.parametrize("c", [-1000.0, -273.15, 0.0, 42.5, 10000.0])
    @pytest.mark.parametrize("fair", [False, True])
    def test_translation_invariance_scalar(self, c: float, fair: bool):
        """CRPS(x + c, y + c) == CRPS(x, y)."""
        torch.manual_seed(99)
        M = 15
        x = torch.randn(M, 8, 12, dtype=torch.float64) * 10.0 + 280.0
        y = torch.randn(8, 12, dtype=torch.float64) * 10.0 + 280.0

        base_crps = compute_crps(x, y, dim=0, fair=fair)
        shifted_crps = compute_crps(x + c, y + c, dim=0, fair=fair)

        assert torch.allclose(base_crps, shifted_crps, atol=1e-11, rtol=1e-11), (
            f"Translation failed for c={c}, fair={fair}. "
            f"Max error: {torch.max(torch.abs(base_crps - shifted_crps)).item()}"
        )

    def test_translation_invariance_spatial_field(self):
        """CRPS(x + c(lat, lon), y + c(lat, lon)) == CRPS(x, y)."""
        # Test Float64: exact to 1e-13
        torch.manual_seed(101)
        M = 12
        x64 = torch.randn(M, 15, 20, dtype=torch.float64)
        y64 = torch.randn(15, 20, dtype=torch.float64)
        c_field64 = torch.randn(15, 20, dtype=torch.float64) * 50.0

        base_crps64 = compute_crps(x64, y64, dim=0, fair=True)
        shifted_crps64 = compute_crps(
            x64 + c_field64.unsqueeze(0), y64 + c_field64, dim=0, fair=True
        )
        assert torch.allclose(base_crps64, shifted_crps64, atol=1e-12, rtol=1e-12)

        # Test Float32: accurate within IEEE 754 precision for numbers around 50 (atol=5e-5)
        x32 = x64.to(torch.float32)
        y32 = y64.to(torch.float32)
        c_field32 = c_field64.to(torch.float32)

        base_crps32 = compute_crps(x32, y32, dim=0, fair=True)
        shifted_crps32 = compute_crps(
            x32 + c_field32.unsqueeze(0), y32 + c_field32, dim=0, fair=True
        )
        assert torch.allclose(base_crps32, shifted_crps32, atol=5e-5, rtol=1e-4)

    @pytest.mark.parametrize("a", [0.001, 0.1, 0.5, 2.0, 10.0, 1000.0])
    @pytest.mark.parametrize("fair", [False, True])
    def test_scale_equivariance(self, a: float, fair: bool):
        """CRPS(a * x, a * y) == a * CRPS(x, y) for a > 0."""
        torch.manual_seed(102)
        M = 10
        x = torch.randn(M, 10, 10, dtype=torch.float64)
        y = torch.randn(10, 10, dtype=torch.float64)

        base_crps = compute_crps(x, y, dim=0, fair=fair)
        scaled_crps = compute_crps(a * x, a * y, dim=0, fair=fair)
        expected_scaled = a * base_crps

        assert torch.allclose(scaled_crps, expected_scaled, atol=1e-10, rtol=1e-6), (
            f"Scale equivariance failed for a={a}, fair={fair}. "
            f"Max rel error: {torch.max(torch.abs(scaled_crps - expected_scaled) / expected_scaled).item()}"
        )


# ==============================================================================
# Focus 4: Spread-Skill Ratio Calibration & Batch Equivalence
# ==============================================================================


class TestSSRCalibrationAndBatching:
    """Verify calibrated (SSR ~ 1.0), under-dispersive, and over-dispersive ensembles,
    and verify batched accumulation matches unbatched evaluation."""

    def test_calibrated_ensemble_convergence(self):
        """Calibrated ensemble: truth drawn from same distribution as members -> SSR ~ 1.0."""
        torch.manual_seed(42)
        M = 25
        sigma = 4.0
        n_samples = 400
        # Truth ~ N(mu, sigma^2), Forecast members ~ N(mu, sigma^2)
        mu = torch.randn(n_samples) * 10.0 + 280.0
        truth = mu + torch.randn(n_samples) * sigma
        ens = mu.unsqueeze(0) + torch.randn(M, n_samples) * sigma

        res = engine_ssr(ens.numpy(), truth.numpy(), correct_finite=True)
        assert abs(res["ssr_corrected"] - 1.0) < 0.06, (
            f"Calibrated SSR was {res['ssr_corrected']}, expected ~1.0"
        )
        assert res["calibration_status"] == "WELL-CALIBRATED"

        # Verify finite factor
        assert abs(res["finite_factor"] - np.sqrt((M + 1.0) / M)) < 1e-6
        # Uncorrected raw SSR must be smaller than 1.0 by ~ sqrt(M / (M+1))
        expected_raw = np.sqrt(M / (M + 1.0))
        assert abs(res["ssr_raw"] - expected_raw) < 0.06

    def test_under_and_over_dispersive_detection(self):
        """Verify strict classification of under-dispersive and over-dispersive ensembles."""
        torch.manual_seed(777)
        M = 20
        # Under-dispersive: spread = 1.0, error = 5.0 -> SSR ~ 0.2
        truth_under = torch.randn(100) * 5.0
        ens_under = torch.randn(M, 100) * 1.0
        res_under = engine_ssr(ens_under.numpy(), truth_under.numpy())
        assert res_under["ssr_corrected"] < 0.90
        assert res_under["calibration_status"] == "UNDER-DISPERSIVE"

        # Over-dispersive: spread = 10.0, error = 1.0 -> SSR ~ 10.0
        truth_over = torch.randn(100) * 1.0
        ens_over = torch.randn(M, 100) * 10.0
        res_over = engine_ssr(ens_over.numpy(), truth_over.numpy())
        assert res_over["ssr_corrected"] > 1.10
        assert res_over["calibration_status"] == "OVER-DISPERSIVE"

    def test_ensemble_batch_accumulation_equals_unbatched(self):
        """Verify streaming ensemble members in batches produces identical SSR to all-at-once."""
        torch.manual_seed(888)
        total_M = 40
        batch_size = 10
        H, W = 12, 16

        x_total = torch.randn(total_M, H, W) * 3.0 + 285.0
        y = torch.randn(H, W) * 3.0 + 285.0

        coords_total = OrderedDict(
            {
                "ensemble": np.arange(total_M),
                "lat": np.linspace(90, -90, H),
                "lon": np.linspace(0, 360, W, endpoint=False),
            }
        )
        y_coords = OrderedDict(
            {
                "lat": np.linspace(90, -90, H),
                "lon": np.linspace(0, 360, W, endpoint=False),
            }
        )

        # 1. Unbatched full evaluation
        ssr_unbatched = spread_skill_ratio(
            "ensemble", ["lat", "lon"], correct_finite=True
        )
        res_unbatched, _ = ssr_unbatched(x_total, coords_total, y, y_coords)

        # 2. Batched streaming evaluation
        ssr_batched = spread_skill_ratio(
            "ensemble", ["lat", "lon"], correct_finite=True, ensemble_batch_update=True
        )

        final_res_batched = None
        for start_idx in range(0, total_M, batch_size):
            end_idx = start_idx + batch_size
            x_batch = x_total[start_idx:end_idx]
            coords_batch = coords_total.copy()
            coords_batch["ensemble"] = coords_total["ensemble"][start_idx:end_idx]

            final_res_batched, _ = ssr_batched(x_batch, coords_batch, y, y_coords)

        assert torch.allclose(final_res_batched, res_unbatched, atol=1e-4, rtol=1e-4), (
            f"Batched SSR {final_res_batched.item()} != Unbatched SSR {res_unbatched.item()}"
        )

    def test_area_weighted_crps_and_ssr(self):
        """Verify that area-weighted CRPS and SSR correctly incorporate cosine latitude weights."""
        M = 6
        H, W = 18, 36
        x = torch.randn(M, H, W) + 280.0
        y = torch.randn(H, W) + 280.0
        lat = np.linspace(90, -90, H)
        lon = np.linspace(0, 360, W, endpoint=False)
        coords = OrderedDict({"ensemble": np.arange(M), "lat": lat, "lon": lon})
        y_coords = OrderedDict({"lat": lat, "lon": lon})

        cos_lat = np.cos(np.deg2rad(lat))
        weights_2d = torch.as_tensor(
            cos_lat[:, None].repeat(W, axis=1), dtype=torch.float32
        )

        # CRPS with weights
        crps_w = crps("ensemble", ["lat", "lon"], weights=weights_2d, fair=True)
        res_crps, _ = crps_w(x, coords, y, y_coords)

        grid_crps = compute_crps(x, y, dim=0, fair=True)
        expected_crps = torch.sum(grid_crps * weights_2d) / torch.sum(weights_2d)
        assert torch.allclose(res_crps, expected_crps, atol=1e-5)

        # SSR with weights
        ssr_w = spread_skill_ratio(
            "ensemble",
            ["lat", "lon"],
            reduction_weights=weights_2d,
            correct_finite=True,
        )
        res_ssr, _ = ssr_w(x, coords, y, y_coords)
        assert not torch.isnan(res_ssr)
        assert res_ssr > 0.0


# ==============================================================================
# Focus 5: Stress-Test Edge Cases & Scaling
# ==============================================================================


class TestStressAndEdgeCases:
    """Stress-test NaN handling, division by zero, zero variance, and 721x1440 scaling."""

    def test_nan_propagation_crps(self):
        """Verify behavior when forecast or truth contains NaNs."""
        x = torch.randn(5, 4, 4)
        y = torch.randn(4, 4)
        # Inject NaN into forecast
        x[2, 1, 1] = float("nan")
        res_x = compute_crps(x, y, dim=0)
        assert torch.isnan(res_x[1, 1]), (
            "NaN in ensemble member should produce NaN at grid cell"
        )
        assert not torch.isnan(res_x[0, 0]), "Uncorrupted grid cells must remain finite"

        # Inject NaN into truth
        x_clean = torch.randn(5, 4, 4)
        y_nan = torch.randn(4, 4)
        y_nan[2, 3] = float("nan")
        res_y = compute_crps(x_clean, y_nan, dim=0)
        assert torch.isnan(res_y[2, 3])
        assert not torch.isnan(res_y[0, 0])

    def test_zero_variance_identical_ensemble(self):
        """When all ensemble members are identical, spread is 0 and CRPS == MAE."""
        M = 8
        member = torch.randn(10, 10, dtype=torch.float64) * 5.0 + 280.0
        x = member.unsqueeze(0).repeat(M, 1, 1)  # All M identical
        truth = torch.randn(10, 10, dtype=torch.float64) * 5.0 + 280.0

        # Float64: exact bit-for-bit to machine precision
        crps_val = compute_crps(x, truth, dim=0, fair=False)
        mae_val = torch.abs(member - truth)
        assert torch.allclose(crps_val, mae_val, atol=1e-12)

        # Fair CRPS on identical members (Float64)
        crps_fair = compute_crps(x, truth, dim=0, fair=True)
        assert torch.allclose(crps_fair, mae_val, atol=1e-12)

        # Float32: verify catastrophic cancellation residual is bounded (< 2e-4)
        x32 = x.to(torch.float32)
        truth32 = truth.to(torch.float32)
        member32 = member.to(torch.float32)
        crps_fair_32 = compute_crps(x32, truth32, dim=0, fair=True)
        mae_32 = torch.abs(member32 - truth32)
        max_diff_32 = torch.max(torch.abs(crps_fair_32 - mae_32)).item()
        assert max_diff_32 < 2e-4, (
            f"Float32 cancellation residual {max_diff_32} exceeded bound"
        )

        # SSR: spread = 0 -> SSR = 0
        ssr_metric = spread_skill_ratio("ensemble", ["lat", "lon"])
        coords = OrderedDict(
            {
                "ensemble": np.arange(M),
                "lat": np.arange(10),
                "lon": np.arange(10),
            }
        )
        y_coords = OrderedDict({"lat": np.arange(10), "lon": np.arange(10)})
        # Float64 matches to 1e-12
        ssr_val64, _ = ssr_metric(x, coords, truth, y_coords)
        assert torch.allclose(ssr_val64, torch.zeros_like(ssr_val64), atol=1e-12)

        # Float32 matches within IEEE 754 float32 precision floor (~5e-6)
        ssr_val32, _ = ssr_metric(x32, coords, truth32, y_coords)
        assert torch.allclose(ssr_val32, torch.zeros_like(ssr_val32), atol=1e-5)

    def test_division_by_zero_zero_skill(self):
        """When ensemble mean matches truth exactly, skill RMSE is 0 -> ratio = spread / 0."""
        M = 4
        truth = torch.ones(5, 5)
        # Symmetrically perturbed ensemble with spread > 0, but bit-for-bit exact mean == 1.0
        half = torch.ones(2, 5, 5)
        x = torch.cat([truth.unsqueeze(0) + half, truth.unsqueeze(0) - half], dim=0)

        assert torch.equal(torch.mean(x, dim=0), truth), (
            "Ensemble mean must match truth exactly"
        )

        coords = OrderedDict(
            {
                "ensemble": np.arange(M),
                "lat": np.arange(5),
                "lon": np.arange(5),
            }
        )
        y_coords = OrderedDict({"lat": np.arange(5), "lon": np.arange(5)})

        ssr_metric = spread_skill_ratio("ensemble", ["lat", "lon"])
        ssr_val, _ = ssr_metric(x, coords, truth, y_coords)
        # PyTorch evaluates spread / 0 as inf without crashing
        assert torch.isinf(ssr_val), f"Expected inf, got {ssr_val}"

    def test_ssr_m_equals_one_handling(self):
        """Verify behavior of spread_skill_ratio on M=1 ensemble."""
        x = torch.randn(1, 10, 10)
        truth = torch.randn(10, 10)
        coords = OrderedDict(
            {"ensemble": np.arange(1), "lat": np.arange(10), "lon": np.arange(10)}
        )
        y_coords = OrderedDict({"lat": np.arange(10), "lon": np.arange(10)})

        # With finite correction: M < 2 raises ValueError
        ssr_finite = spread_skill_ratio("ensemble", ["lat", "lon"], correct_finite=True)
        with pytest.raises(
            ValueError, match="requires at least M >= 2 ensemble members"
        ):
            ssr_finite(x, coords, truth, y_coords)

        # Without finite correction: variance divides by M-1=0, returns NaN
        ssr_raw = spread_skill_ratio("ensemble", ["lat", "lon"], correct_finite=False)
        val, _ = ssr_raw(x, coords, truth, y_coords)
        assert torch.isnan(val), "Raw SSR on M=1 should return NaN (0/0 variance)"

    def test_large_spatial_tensor_721x1440(self):
        """Stress-test large operational spatial grid (721 x 1440 = 1,038,240 points) on CPU.
        Verify memory footprint and execution time remain manageable (< 5 seconds).
        """
        M = 10
        H, W = 721, 1440

        t0 = time.perf_counter()
        # Allocate tensors (~41.5 MB each)
        x = torch.randn(M, H, W, dtype=torch.float32) + 280.0
        truth = torch.randn(H, W, dtype=torch.float32) + 280.0
        t_alloc = time.perf_counter() - t0

        # CRPS execution time
        t1 = time.perf_counter()
        crps_result = compute_crps(x, truth, dim=0, fair=False)
        t_crps_std = time.perf_counter() - t1

        t2 = time.perf_counter()
        crps_fair_result = compute_crps(x, truth, dim=0, fair=True)
        t_crps_fair = time.perf_counter() - t2

        assert crps_result.shape == (H, W)
        assert crps_fair_result.shape == (H, W)
        assert not torch.isnan(crps_result).any()
        assert not torch.isnan(crps_fair_result).any()

        # Spread-Skill Ratio on 721x1440
        coords = OrderedDict(
            {
                "ensemble": np.arange(M),
                "lat": np.linspace(90, -90, H),
                "lon": np.linspace(0, 360, W, endpoint=False),
            }
        )
        y_coords = OrderedDict(
            {
                "lat": np.linspace(90, -90, H),
                "lon": np.linspace(0, 360, W, endpoint=False),
            }
        )

        t3 = time.perf_counter()
        ssr_metric = spread_skill_ratio("ensemble", ["lat", "lon"], correct_finite=True)
        ssr_val, _ = ssr_metric(x, coords, truth, y_coords)
        t_ssr = time.perf_counter() - t3

        assert not torch.isnan(ssr_val)
        assert ssr_val > 0.0

        # Performance benchmarks
        print(
            f"\n[721x1440 Benchmark] Alloc: {t_alloc:.3f}s | "
            f"CRPS Std: {t_crps_std:.3f}s | CRPS Fair: {t_crps_fair:.3f}s | SSR: {t_ssr:.3f}s"
        )
        assert t_crps_std < 5.0, f"CRPS Standard took {t_crps_std:.2f}s, expected < 5s"
        assert t_crps_fair < 5.0, f"CRPS Fair took {t_crps_fair:.2f}s, expected < 5s"
        assert t_ssr < 5.0, f"SSR took {t_ssr:.2f}s, expected < 5s"
