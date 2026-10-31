# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Authoritative Anti-Leakage Test Suite (Tests A through F).

Implements the mandatory scientific validation suite for Milestone M2 of
Project OD-EARTH2-001 / EO-OBSCURA. Demonstrates initial RED state on historical
defective logic and certifies GREEN state on the decoupled 3-stage pipeline.

Requirements:
- Test A: Future-truth independence (forecast invariant to verification truth)
- Test B: Prediction-before-verification (stage A completes under temporal isolation)
- Test C: No synthetic substitution (reject synthetic formulas and mock residuals)
- Test D: Provenance integrity (reject tampered forecast artifacts via SHA-256)
- Test E: Chronological correctness (enforce t_valid = t0 + dt and reject cross-epoch)
- Test F: Real model identity (prohibit labeling Persistence as FourCastNet)
"""

from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from od_experiments.scientific_study.exceptions import (
    ChronologyError,
    ForbiddenFutureAccessError,
    ModelIdentityMismatchError,
    ProvenanceIntegrityError,
    SyntheticSubstitutionError,
)
from od_experiments.scientific_study.pipeline import (
    freeze_forecast,
    run_forecast,
    verify_forecast,
)


class TestA_FutureTruthIndependence:
    """Test A: Future-truth independence.

    Prove that the forecast tensor does not change when the held-out
    verification truth is altered or perturbed.
    """

    def test_future_truth_independence(self, tmp_path: Path) -> None:
        """Forecast output must be bit-for-bit invariant to held-out verification truth."""
        shape = (181, 360)
        rng = np.random.default_rng(2026)
        x0 = 288.15 + rng.normal(0, 5, shape).astype(np.float32)

        # Create two different held-out verification truth fields
        truth_1 = x0 + rng.normal(0, 2, shape).astype(np.float32)
        truth_2 = truth_1.copy()
        # Perturb quadrant by +5.0 K in truth_2
        truth_2[50:100, 100:150] += 5.0

        dir_1 = tmp_path / "run_1"
        dir_2 = tmp_path / "run_2"

        init_time = datetime.datetime(2026, 10, 25, 0, 0, tzinfo=datetime.timezone.utc)

        # Run forecast generator twice with identical initial conditions, model, and seed,
        # but in the presence of verification truth 1 vs verification truth 2.
        file_1 = run_forecast(
            init_time=init_time,
            lead_time_hours=24,
            model_family="Persistence",
            initial_condition=x0,
            verification_truth=truth_1,
            output_dir=dir_1,
            seed=42,
        )
        file_2 = run_forecast(
            init_time=init_time,
            lead_time_hours=24,
            model_family="Persistence",
            initial_condition=x0,
            verification_truth=truth_2,
            output_dir=dir_2,
            seed=42,
        )

        forecast_1 = np.load(file_1)
        forecast_2 = np.load(file_2)

        # Invariant assertion: forecast must NOT change when verification truth changes
        np.testing.assert_array_equal(
            forecast_1,
            forecast_2,
            err_msg="Future-truth independence violation: Forecast changed when verification truth was perturbed!",
        )


class TestB_PredictionBeforeVerification:
    """Test B: Prediction-before-verification.

    Prove prediction runs to completion without accessing verification dataset.
    """

    def test_prediction_before_verification(self, tmp_path: Path) -> None:
        """Prediction stage must succeed when future operational analysis is inaccessible."""
        init_time = datetime.datetime(2026, 10, 25, 0, 0, tzinfo=datetime.timezone.utc)
        lead_time_hours = 24
        valid_time = init_time + datetime.timedelta(hours=lead_time_hours)

        # Information barrier data source
        class IsolatedDataSource:
            def __call__(self, time: datetime.datetime, variable: list[str]) -> np.ndarray:
                if time >= valid_time:
                    raise ForbiddenFutureAccessError(
                        f"Access forbidden to future verification timestamp: {time}"
                    )
                return np.full((181, 360), 288.15, dtype=np.float32)

        isolated_source = IsolatedDataSource()

        # The prediction stage must complete without querying future verification analysis
        forecast_file = run_forecast(
            init_time=init_time,
            lead_time_hours=lead_time_hours,
            model_family="Persistence",
            data_source=isolated_source,
            output_dir=tmp_path / "forecast_b",
        )

        assert forecast_file.exists(), "Forecast file was not produced!"
        assert forecast_file.stat().st_size > 0, "Forecast file is empty!"


class TestC_NoSyntheticSubstitution:
    """Test C: No synthetic substitution.

    Reject forecasts produced through random residuals, truth-based delta, or mock predictions.
    """

    def test_no_synthetic_substitution(self, tmp_path: Path) -> None:
        """Production benchmark mode must reject synthetic diagnostic classification and residuals."""
        forecast_file = tmp_path / "forecast_t2m.npy"
        np.save(forecast_file, np.zeros((181, 360), dtype=np.float32))
        with open(forecast_file, "rb") as f:
            valid_hash = hashlib.sha256(f.read()).hexdigest()

        manifest_data = {
            "manifest_version": "2.0.0",
            "experiment_classification": "TRUTH_CONDITIONED_SYNTHETIC_DIAGNOSTIC",
            "init_time": "2026-10-25T00:00:00Z",
            "valid_time": "2026-10-26T00:00:00Z",
            "lead_time_hours": 24,
            "model": {"family": "synthetic_formula", "checkpoint": "none"},
            "forecast_artifacts": [
                {"name": "forecast_t2m.npy", "sha256": valid_hash}
            ],
        }

        # Save synthetic manifest
        manifest_path = tmp_path / "run_manifest.json"
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        # Benchmark verification must strictly reject synthetic classification
        with pytest.raises(
            SyntheticSubstitutionError,
            match="[Ss]ynthetic.*rejected|[Ss]ynthetic substitution detected",
        ):
            verify_forecast(manifest_path=manifest_path, benchmark_mode=True)


class TestD_ProvenanceIntegrity:
    """Test D: Provenance integrity.

    Reject forecast artifact if hash has been altered after freezing.
    """

    def test_provenance_integrity(self, tmp_path: Path) -> None:
        """Verification stage must reject forecast artifacts whose SHA-256 digest was altered."""
        f_dir = tmp_path / "forecast_d"
        f_dir.mkdir(parents=True, exist_ok=True)
        forecast_file = f_dir / "forecast_t2m.npy"

        arr = np.full((181, 360), 288.15, dtype=np.float32)
        np.save(forecast_file, arr)

        # Compute authentic SHA-256 hash of original file
        with open(forecast_file, "rb") as f:
            authentic_hash = hashlib.sha256(f.read()).hexdigest()

        manifest_data = {
            "manifest_version": "2.0.0",
            "experiment_classification": "BASELINE_PERSISTENCE",
            "init_time": "2026-10-25T00:00:00Z",
            "valid_time": "2026-10-26T00:00:00Z",
            "lead_time_hours": 24,
            "model": {"family": "Persistence", "checkpoint": "identity"},
            "forecast_artifacts": [
                {"name": "forecast_t2m.npy", "sha256": authentic_hash}
            ],
        }
        manifest_path = f_dir / "run_manifest.json"
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        # Post-freeze tampering: alter a single pixel value on disk
        tampered_arr = arr.copy()
        tampered_arr[90, 180] += 50.0  # +50 K perturbation
        np.save(forecast_file, tampered_arr)

        # Verification must detect hash mismatch and abort before computing metrics
        with pytest.raises(
            ProvenanceIntegrityError, match="[Hh]ash mismatch|[Pp]rovenance"
        ):
            verify_forecast(manifest_path=manifest_path)


class TestE_ChronologicalCorrectness:
    """Test E: Chronological correctness.

    Verify t_valid = t0 + delta_t and reject cross-epoch comparisons like 2026 vs 2024.
    """

    def test_chronological_correctness(self, tmp_path: Path) -> None:
        """Verification must reject cross-epoch datasets and timestamp mismatches."""
        forecast_dir = tmp_path / "forecast_e"
        forecast_dir.mkdir(parents=True, exist_ok=True)
        forecast_file = forecast_dir / "forecast_t2m.npy"
        np.save(forecast_file, np.full((181, 360), 288.15, dtype=np.float32))

        with open(forecast_file, "rb") as f:
            f_hash = hashlib.sha256(f.read()).hexdigest()

        # Forecast valid for October 26, 2026 00:00 UTC
        manifest_data = {
            "manifest_version": "2.0.0",
            "experiment_classification": "BASELINE_PERSISTENCE",
            "init_time": "2026-10-25T00:00:00Z",
            "valid_time": "2026-10-26T00:00:00Z",
            "lead_time_hours": 24,
            "model": {"family": "Persistence", "checkpoint": "identity"},
            "forecast_artifacts": [
                {"name": "forecast_t2m.npy", "sha256": f_hash}
            ],
        }
        manifest_path = forecast_dir / "run_manifest.json"
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        # Held-out verification truth stamped for January 1, 2024 (historical 34-month cross-epoch bug)
        verif_data = {
            "valid_time": "2024-01-01T00:00:00Z",
            "variable": "t2m",
            "shape": [181, 360],
        }
        verif_file = tmp_path / "verif_2024.json"
        verif_file.write_text(json.dumps(verif_data, indent=2), encoding="utf-8")

        # Must detect that 2026-10-26 != 2024-01-01 and raise ChronologyError
        with pytest.raises(
            ChronologyError,
            match="Temporal alignment error|[Tt]imestamp mismatch|[Cc]hronolog",
        ):
            verify_forecast(
                manifest_path=manifest_path,
                verification_dataset_path=verif_file,
            )


class TestF_RealModelIdentity:
    """Test F: Real model identity.

    Ensure benchmark records actual model family/checkpoint and never labels Persistence as FourCastNet.
    """

    def test_real_model_identity(self, tmp_path: Path) -> None:
        """Prohibit labeling Persistence baseline executions as FourCastNet or SFNO."""
        forecast_dir = tmp_path / "forecast_f"
        forecast_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "init_time": "2026-10-25T00:00:00Z",
            "valid_time": "2026-10-26T00:00:00Z",
            "lead_time_hours": 24,
            "model_family": "Persistence",
            "checkpoint": "identity",
        }
        (forecast_dir / "forecast_meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        np.save(
            forecast_dir / "forecast_t2m.npy",
            np.full((181, 360), 288.15, dtype=np.float32),
        )

        # Attempt to misrepresent model: run was Persistence, but claim FourCastNet in freeze
        with pytest.raises(
            ModelIdentityMismatchError,
            match="Model identity mismatch|[Pp]ersistence cannot be labeled as FourCastNet",
        ):
            freeze_forecast(
                forecast_dir=forecast_dir,
                model_family="FourCastNet",
                checkpoint="identity",
                checkpoint_sha256=None,
            )
