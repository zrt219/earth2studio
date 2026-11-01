# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-FileCopyrightText: Copyright (c) 2026 Zhane Daye, Origin Datum (https://origindatum.space, contact@origindatum.space)
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
# Author: Zhane Daye, Origin Datum (https://origindatum.space, contact@origindatum.space)
# Compliance: .agents/rules/e2s-000-python-style-guide.mdc, .agents/rules/e2s-014-scientific-integrity.mdc

"""Integration Tests for Earth2Studio CLI Subcommands.

Validates:
- 'benchmark-models' and 'verify-ensemble' CLI commands.
- --help argument documentation and parsing.
- Execution in mock mode returning exit code 0.
- Custom thresholds, JSON serialization, and SHA-256 seal generation.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from od_experiments.earth2_001.cli import main


def test_cli_help_verify_ensemble():
    """Verify --help for 'verify-ensemble' subcommand exits 0 and prints usage."""
    cmd = [
        sys.executable,
        "-m",
        "od_experiments.earth2_001.cli",
        "verify-ensemble",
        "--help",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603

    assert res.returncode == 0
    assert "verify-ensemble" in res.stdout
    assert "--threshold-wind" in res.stdout
    assert "--threshold-precip" in res.stdout
    assert "--mock" in res.stdout


def test_cli_help_benchmark_models():
    """Verify --help for 'benchmark-models' subcommand exits 0 and prints usage."""
    cmd = [
        sys.executable,
        "-m",
        "od_experiments.earth2_001.cli",
        "benchmark-models",
        "--help",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603

    assert res.returncode == 0
    assert "benchmark-models" in res.stdout
    assert "--mock" in res.stdout
    assert "--steps" in res.stdout
    assert "--output-dir" in res.stdout


def test_cli_verify_ensemble_mock_execution(tmp_path: Path):
    """Verify 'verify-ensemble' execution in mock mode completes with exit code 0."""
    out_dir = tmp_path / "cli_verification"
    cmd = [
        sys.executable,
        "-m",
        "od_experiments.earth2_001.cli",
        "verify-ensemble",
        "--mock",
        "--output-dir",
        str(out_dir),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603

    assert res.returncode == 0
    assert "OPERATIONAL ENSEMBLE VERIFICATION REPORT" in res.stdout
    assert "CRPS" in res.stdout
    assert "SSR" in res.stdout
    assert "SHA-256" in res.stdout

    report_file = out_dir / "verification_report.json"
    assert report_file.exists()
    with open(report_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["verification_status"] == "VALIDATED"
    assert "sha256_integrity_seal" in data


def test_cli_benchmark_models_mock_execution(tmp_path: Path):
    """Verify 'benchmark-models' execution in mock mode completes with exit code 0."""
    out_dir = tmp_path / "cli_benchmark"
    cmd = [
        sys.executable,
        "-m",
        "od_experiments.earth2_001.cli",
        "benchmark-models",
        "--mock",
        "--steps",
        "2",
        "--output-dir",
        str(out_dir),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603

    assert res.returncode == 0
    assert "EARTH2STUDIO MULTI-MODEL PROGNOSTIC BENCHMARK SUITE" in res.stdout
    assert "GraphCast" in res.stdout
    assert "Persistence" in res.stdout
    assert "SHA-256" in res.stdout

    report_file = out_dir / "benchmark_report.json"
    assert report_file.exists()
    with open(report_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["mock_mode"] is True
    assert data["steps"] == 2
    assert "sha256_integrity_seal" in data


def test_cli_in_process_json_modes(tmp_path: Path):
    """Verify in-process CLI invocation with --json outputs valid JSON."""
    out_dir = tmp_path / "in_process_test"

    # Test benchmark-models in-process
    with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
        main(
            [
                "benchmark-models",
                "--mock",
                "--steps",
                "1",
                "--output-dir",
                str(out_dir / "bm"),
                "--json",
            ]
        )
        output = mock_out.getvalue().strip()
        if "{" in output:
            output = output[output.find("{") :]
        bm_json = json.loads(output)
        assert "models" in bm_json
        assert "sha256_integrity_seal" in bm_json

    # Test verify-ensemble in-process
    with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
        main(
            [
                "verify-ensemble",
                "--mock",
                "--steps",
                "6,12",
                "--threshold-wind",
                "25.0",
                "--threshold-precip",
                "15.0",
                "--output-dir",
                str(out_dir / "ve"),
                "--json",
            ]
        )
        output = mock_out.getvalue().strip()
        if "{" in output:
            output = output[output.find("{") :]
        ve_json = json.loads(output)
        assert ve_json["verification_status"] == "VALIDATED"
        assert "sha256_integrity_seal" in ve_json
