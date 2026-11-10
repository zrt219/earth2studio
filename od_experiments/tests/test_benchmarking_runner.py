# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-FileCopyrightText: Copyright (c) 2026 Zhane Daye (SAR & Earth System Engineering; zhanedaye@umattr.ca)
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
#
# Author: Zhane Daye (SAR & Earth System Engineering; zhanedaye@umattr.ca)
# Compliance: .agents/rules/e2s-000-python-style-guide.mdc, .agents/rules/e2s-014-scientific-integrity.mdc

"""Integration test suite for the 5-Model Prognostic Benchmark Runner and CLI integration.

Validates:
1. Default 5-model runner instantiation conforming to PrognosticModel protocol.
2. Resource profiling (parameter counts, CPU inference latency per step via monotonic timer, memory MB, empirical proxy disclosure).
3. 4-step multi-horizon forecast trajectory execution.
4. Lead-time error growth evaluation (area-weighted RMSE, MAE, bias).
5. Relative skill calculation vs persistence baseline.
6. TAC qualification and strict separation from ACC per e2s-014 Rule 2.
7. Multi-model ensemble probabilistic verification (standard and fair CRPS, SSR with finite-size correction, EDI, and SEDI).
8. JSON report writing and cryptographic SHA-256 seal verification.
9. CLI benchmark subcommand execution via subprocess.
10. CLI verify-ensemble subcommand execution via subprocess.
11. Web app schema contract synchronization in viewer_app/studyData.js.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from earth2studio.models.px.base import PrognosticModel
from od_experiments.model_comparison.benchmark_runner import BenchmarkRunner


@pytest.fixture
def runner_coarse() -> BenchmarkRunner:
    """Fixture returning a lightweight CPU BenchmarkRunner instance on coarse grid."""
    return BenchmarkRunner(mock=True, lat_size=16, lon_size=32)


def test_runner_initialization(runner_coarse: BenchmarkRunner) -> None:
    """Case 1: Verify BenchmarkRunner instantiates default 5-model mock suite."""
    assert len(runner_coarse.models) == 5
    expected_models = {"graphcast", "sfno", "pangu", "climax", "persistence"}
    assert set(runner_coarse.models.keys()) == expected_models

    for name, model in runner_coarse.models.items():
        assert isinstance(model, PrognosticModel), (
            f"Model {name} must implement PrognosticModel"
        )

    # Verify descending latitude vector per e2s-014 Rule 4
    assert runner_coarse.lats[0] > runner_coarse.lats[-1], (
        "Latitude vector must be descending (+90 to -90)"
    )


def test_runner_resource_profiling(runner_coarse: BenchmarkRunner) -> None:
    """Case 2: Verify parameter counts, positive latencies, and proxy disclosure."""
    profiles = runner_coarse.profile_models()
    assert len(profiles) == 5

    pers = profiles["persistence"]
    assert pers["param_count_m"] == 0.0
    assert pers["latency_ms_cpu"] > 0.0
    assert pers["empirical_proxy"] is False
    assert pers["memory_mb"] > 0.0

    for m in ["graphcast", "sfno", "pangu", "climax"]:
        p = profiles[m]
        assert p["param_count_m"] > 0.0
        assert p["latency_ms_cpu"] > 0.0
        assert p["empirical_proxy"] is True
        assert p["memory_mb"] > 0.0


def test_runner_lead_time_trajectory(runner_coarse: BenchmarkRunner) -> None:
    """Case 3: Run 4 steps (24h) and verify forecast trajectories are produced for each model."""
    res = runner_coarse.run_deterministic_benchmarks(n_steps=4)
    growth = res["lead_time_error_growth"]
    assert len(growth) == 4

    for step_idx, step_eval in enumerate(growth, start=1):
        assert step_eval["step"] == step_idx
        assert step_eval["lead_hours"] == step_idx * 6
        assert len(step_eval["models"]) == 5
        for m in ["graphcast", "sfno", "pangu", "climax", "persistence"]:
            assert m in step_eval["models"]


def test_runner_lead_time_error_growth(runner_coarse: BenchmarkRunner) -> None:
    """Case 4: Verify RMSE, MAE, and bias across lead steps (6h, 12h, 18h, 24h)."""
    res = runner_coarse.run_deterministic_benchmarks(n_steps=4)
    growth = res["lead_time_error_growth"]

    for step_eval in growth:
        for metrics in step_eval["models"].values():
            assert metrics["rmse_t2m"] >= 0.0
            assert metrics["mae_t2m"] >= 0.0
            assert np.isfinite(metrics["bias_t2m"])
            # Variables map verification
            vars_map = metrics["variables"]
            assert "t2m" in vars_map
            assert "u10m" in vars_map
            assert "msl" in vars_map


def test_runner_skill_relative_to_persistence(runner_coarse: BenchmarkRunner) -> None:
    """Case 5: Verify persistence skill is 0.0% and neural models show positive skill."""
    res = runner_coarse.run_deterministic_benchmarks(n_steps=4)
    summary_24h = res["deterministic_summary_24h"]

    # Persistence baseline has zero skill vs itself
    assert summary_24h["persistence"]["skill_vs_persistence_pct"] == 0.0

    # Advecting wave neural models track moving dynamics and outperform frozen persistence
    pers_rmse = summary_24h["persistence"]["rmse_t2m"]
    assert pers_rmse > 0.0

    for m in ["graphcast", "pangu", "climax"]:
        m_rmse = summary_24h[m]["rmse_t2m"]
        expected_skill = (1.0 - (m_rmse / pers_rmse)) * 100.0
        reported_skill = summary_24h[m]["skill_vs_persistence_pct"]
        assert pytest.approx(reported_skill, abs=0.1) == expected_skill
        assert reported_skill > 0.0


def test_runner_tac_integrity(runner_coarse: BenchmarkRunner) -> None:
    """Case 6: Verify TAC is computed against t0 and qualified per e2s-014 Rule 2."""
    res = runner_coarse.run_deterministic_benchmarks(n_steps=2)
    summary = res["deterministic_summary_24h"]

    # Persistence forecast change is 0, so TAC vs persistence is 0
    assert summary["persistence"]["tac_t2m"] == 0.0

    # Neural models tracking physical phase change have positive tendency correlation
    for m in ["graphcast", "sfno", "pangu", "climax"]:
        tac_val = summary[m]["tac_t2m"]
        assert -1.0 <= tac_val <= 1.0
        assert tac_val > 0.8  # Strong phase tracking of the dynamic wave

    report = runner_coarse.run_benchmark(n_steps=1)
    assert report["tac_qualification"]["qualified_per_e2s_014"] is True
    assert (
        report["tac_qualification"]["reference_baseline"] == "initialization_state_t0"
    )


def test_runner_multi_model_probabilistic_verification(
    runner_coarse: BenchmarkRunner,
) -> None:
    """Case 7: Verify CRPS, SSR with finite-size correction, and EDI/SEDI extreme threshold metrics."""
    ens_res = runner_coarse.run_ensemble_verification(n_steps=2)
    assert ens_res["members_count"] == 5
    assert ens_res["members"] == ["graphcast", "sfno", "pangu", "climax", "persistence"]

    # Finite-size ensemble correction factor sqrt((M+1)/M) = sqrt(6/5)
    expected_finite_factor = float(np.sqrt(6.0 / 5.0))
    assert (
        pytest.approx(ens_res["finite_size_factor"], rel=1e-3) == expected_finite_factor
    )

    summary = ens_res["summary_24h"]
    assert summary["crps"] > 0.0
    assert summary["crps_fair"] > 0.0
    assert (
        summary["crps_fair"] <= summary["crps"]
    )  # Fair CRPS finite ensemble correction
    assert summary["ssr"] > 0.0
    assert summary["ssr"] == pytest.approx(
        summary["ssr_raw"] * expected_finite_factor, rel=1e-3
    )

    # Extreme threshold metrics
    assert -1.0 <= summary["edi_wind_20ms"] <= 1.0
    assert -1.0 <= summary["sedi_wind_20ms"] <= 1.0
    assert -1.0 <= summary["sedi_mslp_980hpa"] <= 1.0


def test_runner_json_export_and_sha256(
    runner_coarse: BenchmarkRunner, tmp_path: Path
) -> None:
    """Case 8: Verify report file generation and SHA-256 seal verification."""
    report = runner_coarse.run_benchmark(output_dir=tmp_path, n_steps=2)
    assert report["verification_status"] == "SUCCESS"

    report_file = tmp_path / "benchmark_report.json"
    results_file = tmp_path / "benchmark_results.json"
    assert report_file.exists()
    assert results_file.exists()

    with open(report_file, "r", encoding="utf-8") as f:
        disk_data = json.load(f)

    seal = disk_data.get("sha256_integrity_seal")
    assert seal is not None and len(seal) == 64

    # Verify SHA-256 cryptographic seal
    clean_dict = {k: v for k, v in disk_data.items() if k != "sha256_integrity_seal"}
    expected_seal = hashlib.sha256(
        json.dumps(clean_dict, indent=2, sort_keys=True).encode("utf-8")
    ).hexdigest()
    assert seal == expected_seal


def test_cli_benchmark_command(tmp_path: Path) -> None:
    """Case 9: Call CLI benchmark subcommand via subprocess and assert exit code 0 and JSON output."""
    out_dir = tmp_path / "cli_bench"
    cmd = [
        sys.executable,
        "-m",
        "od_experiments.earth2_001.cli",
        "benchmark",
        "--mock",
        "--steps",
        "2",
        "--output-dir",
        str(out_dir),
        "--json",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)  # noqa: S603
    assert res.returncode == 0

    stdout_json = json.loads(
        res.stdout[res.stdout.find("{") : res.stdout.rfind("}") + 1]
    )
    assert "benchmark_suite" in stdout_json
    assert stdout_json["sha256_integrity_seal"] is not None
    assert len(stdout_json["models_evaluated"]) == 5
    assert (out_dir / "benchmark_report.json").exists()


def test_cli_verify_ensemble_command(tmp_path: Path) -> None:
    """Case 10: Call CLI verify-ensemble subcommand via subprocess and assert exit code 0 and JSON output."""
    out_dir = tmp_path / "cli_verif"
    cmd = [
        sys.executable,
        "-m",
        "od_experiments.earth2_001.cli",
        "verify-ensemble",
        "--source",
        "mock",
        "--steps",
        "6,12",
        "--variables",
        "t2m,u10m,msl",
        "--output-dir",
        str(out_dir),
        "--json",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)  # noqa: S603
    assert res.returncode == 0

    stdout_json = json.loads(
        res.stdout[res.stdout.find("{") : res.stdout.rfind("}") + 1]
    )
    assert stdout_json["pipeline"] == "EnsembleVerificationPipeline"
    assert stdout_json["verification_status"] == "VALIDATED"
    assert stdout_json["sha256_integrity_seal"] is not None
    assert (out_dir / "verification_report.json").exists()


def test_webapp_study_data_schema_compliance() -> None:
    """Case 11: Verify viewer_app/studyData.js defines 5 models and Pillar A verification metrics."""
    study_data_path = Path("viewer_app/studyData.js")
    assert study_data_path.exists(), "viewer_app/studyData.js must exist"

    content = study_data_path.read_text(encoding="utf-8")

    # Verify all 5 models are present in studyData.js
    for model_id in ['"persistence"', '"sfno"', '"pangu"', '"graphcast"', '"climax"']:
        assert model_id in content, f"Model {model_id} must be defined in studyData.js"

    # Verify resource profiling attributes are defined
    for attr in ["paramCountM", "latencyMsCpu", "memoryMb", "empiricalProxy"]:
        assert attr in content, (
            f"Attribute {attr} must be present in PROGNOSTIC_BENCHMARK models"
        )

    # Verify Pillar A verification metrics in ENSEMBLE_METADATA
    for metric_key in [
        "crps: 0.312",
        "ssr: 0.985",
        "edi_wind_20ms: 0.764",
        "sedi_wind_20ms: 0.789",
        "sedi_precip_10mm: 0.712",
    ]:
        assert metric_key in content, (
            f"Metric {metric_key} must be defined in ENSEMBLE_METADATA"
        )

    # Verify validateStudyData allows 5 to 7 models
    assert (
        "PROGNOSTIC_BENCHMARK.models.length >= 5 && PROGNOSTIC_BENCHMARK.models.length <= 7"
        in content
    )
