# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Regression & adversarial verification suite for Milestone M2 remediation items.

Validates the 6 pipeline hardening requirements identified during Gen 1 gate review:
1. Rejection of uninstantiated neural models in run_forecast (no facade persistence fallback).
2. Elimination of dummy constant truth array synthesis in verify_stage.
3. Strict equality enforcement for model family identity in freeze_stage.
4. Dynamic active git commit detection in freeze_stage.
5. Input artifact SHA-256 hash validation in verify_stage.
6. Strict assignment of VERIFIED_GENUINE status only upon actual truth verification.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest

from od_experiments.scientific_study.exceptions import (
    ModelIdentityMismatchError,
    ProvenanceIntegrityError,
)
from od_experiments.scientific_study.pipeline import (
    freeze_forecast,
    run_forecast,
    verify_forecast,
)


def test_uninstantiated_neural_run_raises_value_error(tmp_path: Path) -> None:
    """Invoking run_forecast with a neural model family and model=None must raise ValueError."""
    init_time = datetime.datetime(2026, 10, 25, 0, 0, tzinfo=datetime.timezone.utc)
    for neural_family in ["FourCastNet", "SFNO", "FCN3", "DLWP", "PanguWeather"]:
        with pytest.raises(ValueError, match="Model instance or loader required"):
            run_forecast(
                init_time=init_time,
                lead_time_hours=24,
                model_family=neural_family,
                model=None,
                output_dir=tmp_path / f"forecast_{neural_family}",
            )


def test_dummy_truth_json_without_array_rejected(tmp_path: Path) -> None:
    """verify_forecast must reject JSON metadata descriptors that do not reference authentic array data."""
    f_dir = tmp_path / "forecast_truth_check"
    f_dir.mkdir(parents=True, exist_ok=True)
    init_time = datetime.datetime(2026, 10, 25, 0, 0, tzinfo=datetime.timezone.utc)

    run_forecast(
        init_time=init_time,
        lead_time_hours=24,
        model_family="Persistence",
        output_dir=f_dir,
    )
    manifest = freeze_forecast(f_dir)
    manifest_path = f_dir / "run_manifest.json"

    # JSON descriptor without data_file reference
    dummy_json = tmp_path / "dummy_meta.json"
    dummy_json.write_text(
        json.dumps({
            "valid_time": "2026-10-26T00:00:00Z",
            "shape": [181, 360],
            "variable": "t2m",
        }),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="does not reference an authentic array file"):
        verify_forecast(
            manifest_path=manifest_path,
            verification_dataset_path=dummy_json,
        )


def test_freeze_arbitrary_model_identity_mismatch_rejected(tmp_path: Path) -> None:
    """Persistence runs declared as any other family (e.g. DLWP, GraphCast) must fail freeze."""
    f_dir = tmp_path / "forecast_arbitrary_mismatch"
    f_dir.mkdir(parents=True, exist_ok=True)
    init_time = datetime.datetime(2026, 10, 25, 0, 0, tzinfo=datetime.timezone.utc)

    run_forecast(
        init_time=init_time,
        lead_time_hours=24,
        model_family="Persistence",
        output_dir=f_dir,
    )

    for foreign_family in ["DLWP", "PanguWeather", "GraphCast", "CustomNeural"]:
        with pytest.raises(
            ModelIdentityMismatchError, match="Model identity mismatch"
        ):
            freeze_forecast(
                forecast_dir=f_dir,
                model_family=foreign_family,
                checkpoint="custom.pth",
                checkpoint_sha256="1234567890abcdef",
            )


def test_freeze_resolves_git_commit_dynamically(tmp_path: Path) -> None:
    """freeze_forecast without explicit git_commit must dynamically discover active git HEAD."""
    f_dir = tmp_path / "forecast_dyn_git"
    f_dir.mkdir(parents=True, exist_ok=True)
    init_time = datetime.datetime(2026, 10, 25, 0, 0, tzinfo=datetime.timezone.utc)

    run_forecast(
        init_time=init_time,
        lead_time_hours=24,
        model_family="Persistence",
        output_dir=f_dir,
    )
    manifest = freeze_forecast(f_dir)

    expected_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    assert manifest["git_commit"] == expected_sha, (
        f"Expected dynamic git commit {expected_sha}, got {manifest['git_commit']}"
    )
    assert manifest["git_commit"] != "364dba83fa61856d23a3882be46c899ebcfed2a1"


def test_input_artifact_tampering_detected(tmp_path: Path) -> None:
    """Tampering with an input artifact (e.g. initial_condition.npy) must raise ProvenanceIntegrityError."""
    f_dir = tmp_path / "forecast_input_tamper"
    f_dir.mkdir(parents=True, exist_ok=True)
    init_time = datetime.datetime(2026, 10, 25, 0, 0, tzinfo=datetime.timezone.utc)

    run_forecast(
        init_time=init_time,
        lead_time_hours=24,
        model_family="Persistence",
        output_dir=f_dir,
    )
    manifest = freeze_forecast(f_dir)
    manifest_path = f_dir / "run_manifest.json"

    # Tamper with initial_condition.npy
    init_file = f_dir / "initial_condition.npy"
    arr = np.load(init_file)
    arr[0, 0] += 10.0
    np.save(init_file, arr)

    with pytest.raises(
        ProvenanceIntegrityError, match="SHA-256 hash mismatch for input artifact"
    ):
        verify_forecast(manifest_path=manifest_path)


def test_status_pending_vs_verified_genuine(tmp_path: Path) -> None:
    """Status must be HASH_VERIFIED_PENDING_TRUTH when no truth is provided, and VERIFIED_GENUINE when verified."""
    f_dir = tmp_path / "forecast_status_check"
    f_dir.mkdir(parents=True, exist_ok=True)
    init_time = datetime.datetime(2026, 10, 25, 0, 0, tzinfo=datetime.timezone.utc)

    run_forecast(
        init_time=init_time,
        lead_time_hours=24,
        model_family="Persistence",
        output_dir=f_dir,
    )
    manifest = freeze_forecast(f_dir)
    manifest_path = f_dir / "run_manifest.json"

    # 1. Without truth verification: status is HASH_VERIFIED_PENDING_TRUTH
    res_no_truth = verify_forecast(manifest_path=manifest_path)
    assert res_no_truth["status"] == "HASH_VERIFIED_PENDING_TRUTH"

    # 2. With authentic truth array: status becomes VERIFIED_GENUINE
    truth_array = np.full((181, 360), 288.15, dtype=np.float32)
    truth_file = tmp_path / "truth_t2m.npy"
    np.save(truth_file, truth_array)

    res_with_truth = verify_forecast(
        manifest_path=manifest_path,
        verification_dataset_path=truth_file,
    )
    assert res_with_truth["status"] == "VERIFIED_GENUINE"
    assert "rmse_weighted" in res_with_truth
