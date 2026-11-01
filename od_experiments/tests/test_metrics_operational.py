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

"""
Operational Diagnostic Metrics & Ensemble Verification Suite Test Suite.
Fast CPU execution (< 5 seconds) without network downloads or model checkpoints.
OD-EARTH2-001 research initiative.
Attribution: Zhane Daye, Origin Datum (https://origindatum.space, contact@origindatum.space)
Compliance: .agents/rules/e2s-014-scientific-integrity.mdc
"""

import json
from collections import OrderedDict
from datetime import datetime

import numpy as np
import pytest
import torch
import xarray as xr

from earth2studio.statistics import crps, edi, sedi, spread_skill_ratio
from earth2studio.statistics.crps import compute_crps
from earth2studio.statistics.edi import compute_edi, compute_sedi
from od_experiments.earth2_001.validate import compute_metrics, evaluate_forecast
from od_experiments.ensemble.verification import EnsembleVerificationPipeline
from od_experiments.scientific_study.metrics_engine import (
    extreme_dependency_index,
    symmetric_extremal_dependence_index,
    tendency_anomaly_correlation,
)
from od_experiments.scientific_study.metrics_engine import (
    spread_skill_ratio as engine_ssr,
)


class MockGroundTruthSource:
    """In-memory authentic physical test data source without network calls."""

    def __init__(self, lats: np.ndarray, lons: np.ndarray, seed: int = 42):
        self.lats = lats
        self.lons = lons
        self.seed = seed

    def __call__(self, time: list[datetime], variable: list[str]) -> xr.DataArray:
        rng = np.random.default_rng(self.seed)
        n_times = len(time)
        n_vars = len(variable)
        n_lat = len(self.lats)
        n_lon = len(self.lons)

        data = np.zeros((n_times, n_vars, n_lat, n_lon), dtype=np.float32)
        for v_idx, var in enumerate(variable):
            if var == "t2m":
                data[:, v_idx] = rng.uniform(250.0, 310.0, (n_times, n_lat, n_lon))
            elif var in ["w10m", "u10m", "v10m"]:
                data[:, v_idx] = rng.exponential(
                    scale=6.0, size=(n_times, n_lat, n_lon)
                )
                data[:, v_idx, 0:3, 0:3] = 25.0  # Explicit gale-force points (> 20 m/s)
            elif var == "tp":
                data[:, v_idx] = rng.exponential(
                    scale=5.0, size=(n_times, n_lat, n_lon)
                )
                data[:, v_idx, 0:2, 0:2] = (
                    30.0  # Explicit heavy precip points (> 20 mm)
                )
            elif var == "msl":
                data[:, v_idx] = rng.uniform(99000.0, 103000.0, (n_times, n_lat, n_lon))
                data[:, v_idx, 0:2, 0:2] = 97500.0  # Deep cyclone (< 980 hPa)
            else:
                data[:, v_idx] = rng.normal(100.0, 10.0, (n_times, n_lat, n_lon))

        return xr.DataArray(
            data,
            dims=["time", "variable", "lat", "lon"],
            coords={
                "time": time,
                "variable": variable,
                "lat": self.lats,
                "lon": self.lons,
            },
        )


# =====================================================================
# Unit Tests: CRPS (Pure PyTorch & Engine)
# =====================================================================


def test_crps_identical_ensemble_equals_zero():
    truth = torch.full((10, 10), 285.0, dtype=torch.float32)
    ens = torch.full((5, 10, 10), 285.0, dtype=torch.float32)
    val = compute_crps(ens, truth, dim=0, fair=False)
    assert torch.allclose(val, torch.zeros_like(val))


def test_crps_single_member_equals_mae():
    truth = torch.full((10, 10), 280.0, dtype=torch.float32)
    ens = torch.full((1, 10, 10), 285.0, dtype=torch.float32)  # diff = 5.0
    val = compute_crps(ens, truth, dim=0, fair=False)
    assert torch.allclose(val, torch.full_like(val, 5.0))


def test_crps_gaussian_analytical_benchmark():
    # Analytical: CRPS(N(0, 1), 0) = (sqrt(2) - 1) / sqrt(pi) ~ 0.23369
    torch.manual_seed(42)
    N = 50000
    samples = torch.randn(N, 1)
    truth = torch.zeros(1)
    score = compute_crps(samples, truth, dim=0, fair=True)
    expected = (np.sqrt(2.0) - 1.0) / np.sqrt(np.pi)
    assert torch.isclose(
        score.squeeze(), torch.tensor(expected, dtype=torch.float32), atol=0.01
    )


def test_crps_fair_vs_standard_relationship():
    torch.manual_seed(42)
    truth = torch.randn(10, 10)
    ens = torch.randn(5, 10, 10)
    std_val = compute_crps(ens, truth, dim=0, fair=False)
    fair_val = compute_crps(ens, truth, dim=0, fair=True)
    # Fair CRPS subtracts less or equal penalty, so fair CRPS <= standard CRPS
    assert torch.all(fair_val <= std_val + 1e-6)


def test_crps_earth2studio_metric_protocol():
    M = 8
    x = torch.randn(M, 2, 19, 36)
    x_coords = OrderedDict(
        {
            "ensemble": np.arange(M),
            "variable": np.array(["t2m", "tcwv"]),
            "lat": np.linspace(90, -90, 19),
            "lon": np.linspace(0, 350, 36),
        }
    )
    y = torch.randn(2, 19, 36)
    y_coords = OrderedDict(
        {
            "variable": np.array(["t2m", "tcwv"]),
            "lat": np.linspace(90, -90, 19),
            "lon": np.linspace(0, 350, 36),
        }
    )

    metric = crps(
        ensemble_dimension="ensemble", reduction_dimensions=["lat", "lon"], fair=True
    )
    out, out_coords = metric(x, x_coords, y, y_coords)
    assert "ensemble" not in out_coords
    assert "lat" not in out_coords
    assert "lon" not in out_coords
    assert "variable" in out_coords
    assert out.shape == torch.Size([2])


# =====================================================================
# Unit Tests: Spread-Skill Ratio (SSR)
# =====================================================================


def test_ssr_calibrated_ensemble():
    torch.manual_seed(42)
    M = 20
    sigma = 3.0
    mu = torch.randn(50, 50) * 10.0 + 280.0
    truth = mu + torch.randn(50, 50) * sigma
    ens = mu.unsqueeze(0) + torch.randn(M, 50, 50) * sigma

    res = engine_ssr(ens.numpy(), truth.numpy())
    assert 0.90 <= res["ssr_corrected"] <= 1.10
    assert res["calibration_status"] == "WELL-CALIBRATED"


def test_ssr_under_dispersive():
    torch.manual_seed(42)
    M = 20
    mu = torch.randn(50, 50) * 10.0 + 280.0
    truth = mu + torch.randn(50, 50) * 10.0  # Large error
    ens = mu.unsqueeze(0) + torch.randn(M, 50, 50) * 2.0  # Small spread

    res = engine_ssr(ens.numpy(), truth.numpy())
    assert res["ssr_corrected"] < 0.90
    assert res["calibration_status"] == "UNDER-DISPERSIVE"


def test_ssr_over_dispersive():
    torch.manual_seed(42)
    M = 20
    mu = torch.randn(50, 50) * 10.0 + 280.0
    truth = mu + torch.randn(50, 50) * 1.0  # Tiny error
    ens = mu.unsqueeze(0) + torch.randn(M, 50, 50) * 15.0  # Huge spread

    res = engine_ssr(ens.numpy(), truth.numpy())
    assert res["ssr_corrected"] > 1.10
    assert res["calibration_status"] == "OVER-DISPERSIVE"


def test_ssr_finite_correction_multiplier():
    M = 5
    torch.manual_seed(42)
    truth = torch.randn(20, 20) * 5.0 + 280.0
    ens = truth.unsqueeze(0) + torch.randn(M, 20, 20) * 5.0
    res = engine_ssr(ens.numpy(), truth.numpy(), correct_finite=True)
    expected_multiplier = np.sqrt((M + 1.0) / M)
    assert np.isclose(res["finite_factor"], expected_multiplier)
    assert np.isclose(res["ssr_corrected"], res["ssr_raw"] * expected_multiplier)


def test_ssr_earth2studio_metric_protocol():
    M = 10
    x = torch.randn(M, 19, 36)
    x_coords = OrderedDict(
        {
            "ensemble": np.arange(M),
            "lat": np.linspace(90, -90, 19),
            "lon": np.linspace(0, 350, 36),
        }
    )
    y = torch.randn(19, 36)
    y_coords = OrderedDict(
        {
            "lat": np.linspace(90, -90, 19),
            "lon": np.linspace(0, 350, 36),
        }
    )

    metric = spread_skill_ratio("ensemble", ["lat", "lon"], correct_finite=True)
    out, out_coords = metric(x, x_coords, y, y_coords)
    assert "ensemble" not in out_coords
    assert "lat" not in out_coords
    assert "lon" not in out_coords
    assert out.ndim == 0 or out.numel() == 1


# =====================================================================
# Unit Tests: Extreme Dependency Index (EDI & SEDI)
# =====================================================================


def test_edi_sedi_perfect_forecast():
    truth = torch.tensor([[25.0, 10.0], [5.0, 30.0]])
    res_edi = compute_edi(truth, truth, threshold=20.0, reduction_dims=[0, 1])
    res_sedi = compute_sedi(truth, truth, threshold=20.0, reduction_dims=[0, 1])
    assert torch.isclose(res_edi, torch.tensor(1.0), atol=1e-3)
    assert torch.isclose(res_sedi, torch.tensor(1.0), atol=1e-3)


def test_edi_sedi_perverse_inverted_forecast():
    truth = torch.tensor([[25.0, 25.0], [5.0, 5.0]])
    fc = torch.tensor([[5.0, 5.0], [25.0, 25.0]])
    res_edi = compute_edi(fc, truth, threshold=20.0, reduction_dims=[0, 1])
    res_sedi = compute_sedi(fc, truth, threshold=20.0, reduction_dims=[0, 1])
    assert torch.isclose(res_edi, torch.tensor(-1.0), atol=1e-3)
    assert torch.isclose(res_sedi, torch.tensor(-1.0), atol=1e-3)


def test_edi_sedi_base_rate_invariance():
    # As base-rate drops from 0.5 to 0.001, EDI and SEDI must remain strictly constant
    H = 0.8
    F = 0.05
    edi_vals = []
    sedi_vals = []

    for p in [0.5, 0.1, 0.01, 0.001]:
        ac = 10000.0
        a = int(round(H * ac))
        c = int(round((1.0 - H) * ac))
        bd = int(round(ac * (1.0 - p) / p))
        b = int(round(F * bd))
        d = bd - b

        fc = np.concatenate([np.ones(a), np.ones(b), np.zeros(c), np.zeros(d)])
        truth = np.concatenate([np.ones(a), np.zeros(b), np.ones(c), np.zeros(d)])

        edi_dict = extreme_dependency_index(fc, truth, threshold=0.5)
        sedi_dict = symmetric_extremal_dependence_index(fc, truth, threshold=0.5)
        edi_vals.append(edi_dict["edi"])
        sedi_vals.append(sedi_dict["sedi"])

    assert np.allclose(edi_vals, edi_vals[0], atol=1e-3)
    assert np.allclose(sedi_vals, sedi_vals[0], atol=1e-3)


def test_gale_wind_extreme_threshold():
    truth = np.array([[22.0, 15.0], [10.0, 25.0]], dtype=np.float32)
    fc = np.array([[21.0, 18.0], [8.0, 24.0]], dtype=np.float32)
    res = extreme_dependency_index(fc, truth, threshold=20.0)
    assert res["hits"] == 2.0
    assert res["false_alarms"] == 0.0
    assert res["misses"] == 0.0
    assert res["correct_negatives"] == 2.0
    assert np.isclose(res["edi"], 1.0, atol=1e-3)


def test_cyclone_mslp_lower_threshold():
    # Cyclone depression: event is MSLP <= 98000 Pa
    truth = np.array([[97500.0, 101000.0], [100500.0, 97800.0]], dtype=np.float32)
    fc = np.array([[97600.0, 101200.0], [100200.0, 97900.0]], dtype=np.float32)
    res = extreme_dependency_index(
        fc, truth, threshold=98000.0, is_upper_threshold=False
    )
    assert res["hits"] == 2.0
    assert res["false_alarms"] == 0.0
    assert res["misses"] == 0.0
    assert res["correct_negatives"] == 2.0
    assert np.isclose(res["edi"], 1.0, atol=1e-3)


def test_edi_sedi_earth2studio_metric_protocol():
    x = torch.tensor([[25.0, 5.0], [15.0, 22.0]])
    y = torch.tensor([[24.0, 8.0], [10.0, 21.0]])
    coords = OrderedDict({"lat": np.array([10, -10]), "lon": np.array([0, 180])})

    edi_metric = edi(thresholds=20.0, reduction_dimensions=["lat", "lon"])
    out, out_coords = edi_metric(x, coords, y, coords)
    assert "lat" not in out_coords
    assert "lon" not in out_coords
    assert torch.isclose(out, torch.tensor(1.0), atol=1e-3)

    sedi_metric = sedi(thresholds=20.0, reduction_dimensions=["lat", "lon"])
    s_out, s_out_coords = sedi_metric(x, coords, y, coords)
    assert torch.isclose(s_out, torch.tensor(1.0), atol=1e-3)


# =====================================================================
# Unit Tests: Decoupling & Scientific Integrity (e2s-014)
# =====================================================================


def test_acc_clean_decoupling_without_zarr_abc():
    # Verifies earth2studio.statistics imports cleanly without zarr.abc crash
    import earth2studio.statistics as e2s_stat

    assert hasattr(e2s_stat, "acc")
    assert hasattr(e2s_stat, "crps")
    assert hasattr(e2s_stat, "spread_skill_ratio")
    assert hasattr(e2s_stat, "edi")
    assert hasattr(e2s_stat, "sedi")


def test_tac_vs_acc_integrity():
    fc = np.full((10, 10), 280.0, dtype=np.float32)
    truth = np.full((10, 10), 282.0, dtype=np.float32)
    pers = np.full((10, 10), 280.0, dtype=np.float32)
    tac = tendency_anomaly_correlation(fc, truth, persistence=pers)
    assert tac == 0.0


# =====================================================================
# Integration Test: End-to-End Operational Verification Pipeline
# =====================================================================


def test_operational_verification_pipeline_fast_cpu(tmp_path):
    lats = np.linspace(90, -90, 19)
    lons = np.linspace(0, 350, 36)
    mock_source = MockGroundTruthSource(lats, lons, seed=42)

    pipeline = EnsembleVerificationPipeline(
        ground_truth_source=mock_source,
        source_name="mock_gfs",
        target_lats=lats,
    )

    lead_steps = [0, 6, 12, 24]
    rng = np.random.default_rng(123)
    forecast_data = {
        "w10m": [
            rng.exponential(6.0, (5, 19, 36)).astype(np.float32) for _ in lead_steps
        ],
        "t2m": [
            rng.uniform(250.0, 310.0, (5, 19, 36)).astype(np.float32)
            for _ in lead_steps
        ],
    }

    report = pipeline.verify_forecast_dataset(
        forecast_dataset=forecast_data,
        init_time="2024-01-01T00:00:00",
        lead_steps_hours=lead_steps,
        output_dir=tmp_path,
    )

    assert report["verification_status"] == "VALIDATED"
    assert "w10m" in report["variables"]
    assert "t2m" in report["variables"]
    assert len(report["variables"]["w10m"]["lead_trajectory"]) == 4

    # Verify JSON file written with SHA-256 integrity seal
    report_file = tmp_path / "verification_report.json"
    assert report_file.exists()
    with open(report_file) as f:
        data = json.load(f)
    assert "sha256_integrity_seal" in data
    assert len(data["sha256_integrity_seal"]) == 64


def test_validate_with_ensemble_crps_and_ssr():
    fc_ens = np.random.randn(5, 10, 10) * 2.0 + 280.0
    ref = np.random.randn(10, 10) * 2.0 + 280.0
    pers = np.random.randn(10, 10) * 2.0 + 280.0

    metrics = compute_metrics(
        forecast=fc_ens,
        reference=ref,
        persistence=pers,
        threshold=282.0,
    )

    assert "mae" in metrics
    assert "rmse" in metrics
    assert "crps" in metrics
    assert "crps_fair" in metrics
    assert "ensemble_spread" in metrics
    assert "ssr_raw" in metrics
    assert "ssr_corrected" in metrics
    assert "calibration_status" in metrics
    assert "tac" in metrics
    assert "edi" in metrics
    assert "sedi" in metrics


def test_validate_evaluate_forecast_integration(tmp_path):
    forecast_data = {
        "t2m": np.random.randn(4, 8, 8) + 280.0,
        "w10m": np.random.randn(4, 8, 8) + 15.0,
    }
    reference_data = {
        "t2m": np.random.randn(8, 8) + 280.0,
        "w10m": np.random.randn(8, 8) + 15.0,
    }
    thresholds = {"w10m": 20.0}

    report = evaluate_forecast(
        forecast_data=forecast_data,
        reference_data=reference_data,
        thresholds=thresholds,
        output_dir=tmp_path,
    )

    assert report["validation_status"] == "VALIDATED"
    assert "t2m" in report["metrics"]
    assert "w10m" in report["metrics"]
    assert "edi" in report["metrics"]["w10m"]
    assert (tmp_path / "validation_report.json").exists()


def test_edi_ensemble_dimension_no_index_error():
    """Verify edi and sedi with ensemble_dimension execute without IndexError coordinate mismatch."""
    M = 5
    n_lat = 19
    n_lon = 36
    x = torch.randn(M, n_lat, n_lon) * 10.0 + 15.0
    x_coords = OrderedDict(
        {
            "ensemble": np.arange(M),
            "lat": np.linspace(90, -90, n_lat),
            "lon": np.linspace(0, 350, n_lon),
        }
    )
    y = torch.randn(n_lat, n_lon) * 10.0 + 15.0
    y_coords = OrderedDict(
        {
            "lat": np.linspace(90, -90, n_lat),
            "lon": np.linspace(0, 350, n_lon),
        }
    )

    # Test with threshold=20.0
    edi_metric = edi(
        threshold=20.0,
        ensemble_dimension="ensemble",
        reduction_dimensions=["lat", "lon"],
    )
    out, out_coords = edi_metric(x, x_coords, y, y_coords)
    assert "ensemble" not in out_coords
    assert "lat" not in out_coords
    assert "lon" not in out_coords
    assert out.ndim == 0 or out.numel() == 1
    assert not torch.isnan(out)

    # Test with thresholds=20.0
    edi_metric_plural = edi(
        thresholds=20.0,
        ensemble_dimension="ensemble",
        reduction_dimensions=["lat", "lon"],
    )
    out_p, out_coords_p = edi_metric_plural(x, x_coords, y, y_coords)
    assert torch.equal(out, out_p)
    assert out_coords == out_coords_p

    # Test sedi with ensemble_dimension
    sedi_metric = sedi(
        threshold=20.0,
        ensemble_dimension="ensemble",
        reduction_dimensions=["lat", "lon"],
    )
    s_out, s_out_coords = sedi_metric(x, x_coords, y, y_coords)
    assert "ensemble" not in s_out_coords
    assert "lat" not in s_out_coords
    assert "lon" not in s_out_coords
    assert s_out.ndim == 0 or s_out.numel() == 1
    assert not torch.isnan(s_out)


def test_crps_fair_single_member_raises_value_error():
    """Verify fair CRPS raises ValueError when M < 2 before returning single member MAE."""
    truth = torch.full((10, 10), 280.0, dtype=torch.float32)
    ens = torch.full((1, 10, 10), 285.0, dtype=torch.float32)
    with pytest.raises(ValueError, match="Fair CRPS requires at least M >= 2"):
        compute_crps(ens, truth, dim=0, fair=True)


def test_crps_functional_signature_without_coords():
    """Verify crps.__new__ cleanly handles 2-argument tensor calls without coordinate systems."""
    ens = torch.randn(5, 10, 10)
    truth = torch.randn(10, 10)
    out, out_coords = crps(ens, truth)
    assert out_coords == {}
    assert out.shape == torch.Size([10, 10])
    assert not torch.isnan(out).any()


def test_ssr_division_by_zero_guard():
    """Verify spread_skill_ratio guards against division by zero when skill == 0.0."""
    M = 4
    truth = torch.ones(5, 5)
    half = torch.ones(2, 5, 5)
    x = torch.cat([truth.unsqueeze(0) + half, truth.unsqueeze(0) - half], dim=0)
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
    assert torch.isinf(ssr_val)
