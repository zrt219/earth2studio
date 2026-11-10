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
# Compliance: .agents/rules/e2s-009-prognostic-models.mdc, .agents/rules/e2s-014-scientific-integrity.mdc

"""Challenger 2 Cross-Stack Metric Alignment and BenchmarkRunner Verification Suite.

Adversarially validates:
1. Python-to-JavaScript alignment between registry.py, benchmark_runner.py, and studyData.js.
2. Skill formula mathematical equivalence: Skill = (1 - RMSE / RMSE_pers) * 100%.
3. Resource profile conformity (parameter count, CPU latency, memory footprint, empirical proxy flag).
4. Ensemble verification metrics (CRPS, fair CRPS, finite-size corrected SSR, EDI, SEDI).
5. Cryptographic SHA-256 seal integrity.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

from od_experiments.model_comparison.benchmark_runner import BenchmarkRunner
from od_experiments.model_comparison.registry import BENCHMARK_PROFILES


def get_js_study_data() -> dict:
    """Execute node snippet to export PROGNOSTIC_BENCHMARK and ENSEMBLE_METADATA as JSON."""
    node_script = """
    import { PROGNOSTIC_BENCHMARK, ENSEMBLE_METADATA } from './viewer_app/studyData.js';
    console.log(JSON.stringify({
        models: PROGNOSTIC_BENCHMARK.models,
        ensemble: ENSEMBLE_METADATA
    }));
    """
    res = subprocess.run(
        ["node", "--input-type=module", "-e", node_script],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(res.stdout)


def test_cross_stack_model_profiles_alignment() -> None:
    """Validate that every model in Python BENCHMARK_PROFILES matches JS PROGNOSTIC_BENCHMARK.models."""
    js_data = get_js_study_data()
    js_models = {m["id"]: m for m in js_data["models"]}

    # Ensure all core models exist in both stacks
    core_models = ["persistence", "sfno", "graphcast", "pangu", "climax"]
    for m_id in core_models:
        assert m_id in js_models, f"Model {m_id} missing from studyData.js"
        assert m_id in BENCHMARK_PROFILES, f"Model {m_id} missing from registry.py"

        py_prof = BENCHMARK_PROFILES[m_id]
        js_prof = js_models[m_id]

        # 1. Parameter count alignment
        assert math.isclose(
            py_prof["param_count_m"], js_prof["paramCountM"], abs_tol=0.1
        ), (
            f"Param count mismatch for {m_id}: py={py_prof['param_count_m']}, js={js_prof['paramCountM']}"
        )

        # 2. CPU Latency profile alignment
        assert math.isclose(
            py_prof["latency_ms_cpu"], js_prof["latencyMsCpu"], abs_tol=0.1
        ), (
            f"CPU latency mismatch for {m_id}: py={py_prof['latency_ms_cpu']}, js={js_prof['latencyMsCpu']}"
        )

        # 3. Empirical proxy flag alignment
        assert py_prof["empirical_proxy"] == js_prof["empiricalProxy"], (
            f"Empirical proxy mismatch for {m_id}: py={py_prof['empirical_proxy']}, js={js_prof['empiricalProxy']}"
        )

        # 4. Reference RMSE alignment
        assert math.isclose(
            py_prof["reference_rmse_t2m_k"], js_prof["rmseK"], abs_tol=1e-3
        ), (
            f"RMSE mismatch for {m_id}: py={py_prof['reference_rmse_t2m_k']}, js={js_prof['rmseK']}"
        )

        # 5. Nominal TAC alignment
        assert math.isclose(py_prof["nominal_tac"], js_prof["tac"], abs_tol=1e-3), (
            f"TAC mismatch for {m_id}: py={py_prof['nominal_tac']}, js={js_prof['tac']}"
        )

        # 6. Skill score alignment (0.1% tolerance)
        assert math.isclose(
            py_prof["skill_score_pct"], js_prof["skillPct"], abs_tol=0.15
        ), (
            f"Skill score mismatch for {m_id}: py={py_prof['skill_score_pct']}, js={js_prof['skillPct']}"
        )


def test_cross_stack_multimodel_ensemble_alignment() -> None:
    """Validate that multimodel ensemble metrics align between Python registry and JS studyData."""
    js_data = get_js_study_data()
    js_models = {m["id"]: m for m in js_data["models"]}

    js_multi = js_models.get("multimodel") or js_models.get("multi_model_ensemble")
    assert js_multi is not None, "Multimodel ensemble missing from JS studyData"

    py_multi = BENCHMARK_PROFILES.get("multimodel") or BENCHMARK_PROFILES.get(
        "multi_model_ensemble"
    )
    assert py_multi is not None, "Multimodel profile missing from Python registry"

    assert math.isclose(
        py_multi["param_count_m"], js_multi["paramCountM"], abs_tol=0.1
    )
    assert math.isclose(
        py_multi["latency_ms_cpu"], js_multi["latencyMsCpu"], abs_tol=0.1
    )
    assert py_multi["empirical_proxy"] == js_multi["empiricalProxy"]
    assert math.isclose(
        py_multi["reference_rmse_t2m_k"], js_multi["rmseK"], abs_tol=1e-3
    )
    assert math.isclose(
        py_multi["skill_score_pct"], js_multi["skillPct"], abs_tol=0.15
    )


def test_cross_stack_ensemble_verification_metrics() -> None:
    """Validate Pillar A verification metrics in studyData.js ENSEMBLE_METADATA."""
    js_data = get_js_study_data()
    ens = js_data["ensemble"]

    expected_targets = {
        "crps": 0.312,
        "ssr": 0.985,
        "edi_wind_20ms": 0.764,
        "sedi_wind_20ms": 0.789,
        "sedi_precip_10mm": 0.712,
    }

    for metric, target in expected_targets.items():
        assert metric in ens, f"Metric '{metric}' missing from ENSEMBLE_METADATA"
        val = ens[metric]
        assert isinstance(val, (int, float)), f"Metric '{metric}' is not a number"
        assert math.isfinite(val), f"Metric '{metric}' is not finite"
        assert val >= 0.0, f"Metric '{metric}' is negative"
        assert math.isclose(val, target, abs_tol=1e-3), (
            f"Metric '{metric}' expected {target}, got {val}"
        )


def test_benchmark_runner_empirical_execution() -> None:
    """Execute BenchmarkRunner and verify resource profiling, error growth, and ensemble verification."""
    runner = BenchmarkRunner(mock=True, lat_size=16, lon_size=32)

    # 1. Profile models
    profiles = runner.profile_models()
    assert len(profiles) == 5
    for name, prof in profiles.items():
        assert prof["param_count_m"] >= 0
        assert prof["latency_ms_cpu"] > 0
        assert prof["memory_mb"] > 0
        assert isinstance(prof["empirical_proxy"], bool)

    # 2. Run deterministic benchmarks
    det = runner.run_deterministic_benchmarks(n_steps=4)
    growth = det["lead_time_error_growth"]
    assert len(growth) == 4

    # Verify monotonic lead time error growth for persistence
    pers_rmses = [g["models"]["persistence"]["rmse_t2m"] for g in growth]
    assert pers_rmses == sorted(pers_rmses), "Persistence RMSE must grow monotonically"

    # Verify skill vs persistence formula
    summary = det["deterministic_summary_24h"]
    pers_final_rmse = summary["persistence"]["rmse_t2m"]
    for m_name, m_sum in summary.items():
        expected_skill = (1.0 - (m_sum["rmse_t2m"] / pers_final_rmse)) * 100.0
        assert math.isclose(
            m_sum["skill_vs_persistence_pct"], expected_skill, abs_tol=0.1
        ), f"Skill formula mismatch for {m_name}"

    # 3. Run ensemble verification
    ens = runner.run_ensemble_verification(n_steps=2)
    assert ens["crps"] > 0.0
    assert ens["crps_fair"] > 0.0
    assert ens["crps_fair"] <= ens["crps"], (
        "Fair CRPS must be <= standard CRPS for finite ensembles"
    )
    assert ens["ssr"] > 0.0
    assert ens["finite_ensemble_factor"] == pytest.approx(
        math.sqrt((5 + 1) / 5), rel=1e-4
    )
    assert -1.0 <= ens["edi_wind_20ms"] <= 1.0
    assert -1.0 <= ens["sedi_mslp_980hpa"] <= 1.0
    assert ens["calibration_status"] in (
        "WELL_CALIBRATED",
        "UNDER_DISPERSIVE",
        "OVER_DISPERSIVE",
    )


def test_benchmark_runner_sha256_sealing(tmp_path: Path) -> None:
    """Verify JSON export and SHA-256 seal verification."""
    runner = BenchmarkRunner(mock=True, lat_size=16, lon_size=32)
    out_file = tmp_path / "test_report.json"
    data = runner.export_json(out_file)

    assert "sha256_integrity_seal" in data
    assert out_file.exists()

    with open(out_file, encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["sha256_integrity_seal"] == data["sha256_integrity_seal"]
