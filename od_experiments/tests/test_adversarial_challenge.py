# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Adversarial stress-testing suite for Tests C, D, E, and F.

Empirical verification harness authored by challenger_m2_2.
Stress-tests cryptographic provenance, synthetic substitution rejection,
chronological verification guards, and model identity invariants.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from od_experiments.scientific_study.exceptions import (
    ChronologyError,
    ModelIdentityMismatchError,
    ProvenanceIntegrityError,
    SyntheticSubstitutionError,
)
from od_experiments.scientific_study.pipeline import (
    freeze_forecast,
    verify_forecast,
)


class TestD_ProvenanceIntegrity_Adversarial:
    """Adversarial challenge suite for Test D (Provenance Integrity)."""

    def test_single_byte_flip_in_forecast_array(self, tmp_path: Path) -> None:
        """Tampering with a single byte in forecast_t2m.npy must trigger ProvenanceIntegrityError."""
        f_dir = tmp_path / "forecast_d_byte_flip"
        f_dir.mkdir(parents=True, exist_ok=True)
        forecast_file = f_dir / "forecast_t2m.npy"

        data = np.full((181, 360), 288.15, dtype=np.float32)
        np.save(forecast_file, data)

        with open(forecast_file, "rb") as f:
            authentic_bytes = bytearray(f.read())
        authentic_hash = hashlib.sha256(authentic_bytes).hexdigest()

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

        # Adversarial attack: flip exactly 1 bit in byte 250 (inside binary data payload)
        tampered_bytes = bytearray(authentic_bytes)
        tampered_bytes[250] ^= 0x01
        with open(forecast_file, "wb") as f:
            f.write(tampered_bytes)

        with pytest.raises(
            ProvenanceIntegrityError, match="[Hh]ash mismatch|[Pp]rovenance"
        ) as exc_info:
            verify_forecast(manifest_path=manifest_path)

        assert authentic_hash in str(exc_info.value)

    def test_tampering_aborts_strictly_before_truth_retrieval(
        self, tmp_path: Path
    ) -> None:
        """Pipeline must abort before querying verification data source when hash fails."""
        f_dir = tmp_path / "forecast_d_abort_check"
        f_dir.mkdir(parents=True, exist_ok=True)
        forecast_file = f_dir / "forecast_t2m.npy"

        np.save(forecast_file, np.zeros((10, 10), dtype=np.float32))
        manifest_path = f_dir / "run_manifest.json"
        manifest_data = {
            "manifest_version": "2.0.0",
            "experiment_classification": "BASELINE_PERSISTENCE",
            "init_time": "2026-10-25T00:00:00Z",
            "valid_time": "2026-10-26T00:00:00Z",
            "lead_time_hours": 24,
            "model": {"family": "Persistence", "checkpoint": "identity"},
            "forecast_artifacts": [
                {"name": "forecast_t2m.npy", "sha256": "0" * 64}  # Bad hash
            ],
        }
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        class SentinelDataSource:
            def __init__(self) -> None:
                self.called = False

            def __call__(self, time: Any, variable: Any) -> np.ndarray:
                self.called = True
                raise AssertionError("Verification data source was illegally called!")

        sentinel = SentinelDataSource()

        with pytest.raises(ProvenanceIntegrityError):
            verify_forecast(
                manifest_path=manifest_path,
                verification_data_source=sentinel,
            )

        assert not sentinel.called, "Verification source was queried despite hash failure!"

    def test_truncated_forecast_file_detected(self, tmp_path: Path) -> None:
        """Truncating forecast artifact bytes must trigger ProvenanceIntegrityError."""
        f_dir = tmp_path / "forecast_d_trunc"
        f_dir.mkdir(parents=True, exist_ok=True)
        forecast_file = f_dir / "forecast_t2m.npy"

        np.save(forecast_file, np.ones((50, 50), dtype=np.float32))
        with open(forecast_file, "rb") as f:
            content = f.read()
        valid_hash = hashlib.sha256(content).hexdigest()

        manifest_path = f_dir / "run_manifest.json"
        manifest_data = {
            "manifest_version": "2.0.0",
            "experiment_classification": "BASELINE_PERSISTENCE",
            "init_time": "2026-10-25T00:00:00Z",
            "valid_time": "2026-10-26T00:00:00Z",
            "lead_time_hours": 24,
            "model": {"family": "Persistence", "checkpoint": "identity"},
            "forecast_artifacts": [
                {"name": "forecast_t2m.npy", "sha256": valid_hash}
            ],
        }
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        # Truncate file by 128 bytes
        with open(forecast_file, "wb") as f:
            f.write(content[:-128])

        with pytest.raises(ProvenanceIntegrityError):
            verify_forecast(manifest_path=manifest_path)

    def test_deleted_forecast_artifact_detected(self, tmp_path: Path) -> None:
        """Missing forecast artifact on disk must trigger ProvenanceIntegrityError."""
        f_dir = tmp_path / "forecast_d_missing"
        f_dir.mkdir(parents=True, exist_ok=True)
        forecast_file = f_dir / "forecast_t2m.npy"

        np.save(forecast_file, np.ones((20, 20), dtype=np.float32))
        with open(forecast_file, "rb") as f:
            valid_hash = hashlib.sha256(f.read()).hexdigest()

        manifest_path = f_dir / "run_manifest.json"
        manifest_data = {
            "manifest_version": "2.0.0",
            "experiment_classification": "BASELINE_PERSISTENCE",
            "init_time": "2026-10-25T00:00:00Z",
            "valid_time": "2026-10-26T00:00:00Z",
            "lead_time_hours": 24,
            "model": {"family": "Persistence", "checkpoint": "identity"},
            "forecast_artifacts": [
                {"name": "forecast_t2m.npy", "sha256": valid_hash}
            ],
        }
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        # Delete the file
        forecast_file.unlink()

        with pytest.raises(ProvenanceIntegrityError, match="Missing forecast artifact"):
            verify_forecast(manifest_path=manifest_path)

    def test_empty_forecast_artifacts_list_detected(self, tmp_path: Path) -> None:
        """Manifest with empty forecast_artifacts must trigger ProvenanceIntegrityError."""
        f_dir = tmp_path / "forecast_d_empty_arts"
        f_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = f_dir / "run_manifest.json"
        manifest_data = {
            "manifest_version": "2.0.0",
            "experiment_classification": "BASELINE_PERSISTENCE",
            "init_time": "2026-10-25T00:00:00Z",
            "valid_time": "2026-10-26T00:00:00Z",
            "lead_time_hours": 24,
            "model": {"family": "Persistence", "checkpoint": "identity"},
            "forecast_artifacts": [],
        }
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        with pytest.raises(
            ProvenanceIntegrityError, match="no forecast_artifacts entries"
        ):
            verify_forecast(manifest_path=manifest_path)

    def test_multi_artifact_partial_tampering_detected(self, tmp_path: Path) -> None:
        """In a multi-artifact forecast, tampering with only one artifact must fail verification."""
        f_dir = tmp_path / "forecast_d_multi"
        f_dir.mkdir(parents=True, exist_ok=True)
        f_t2m = f_dir / "forecast_t2m.npy"
        f_u10 = f_dir / "forecast_u10m.npy"

        np.save(f_t2m, np.full((10, 10), 288.15, dtype=np.float32))
        np.save(f_u10, np.full((10, 10), 10.0, dtype=np.float32))

        with open(f_t2m, "rb") as f:
            h_t2m = hashlib.sha256(f.read()).hexdigest()
        with open(f_u10, "rb") as f:
            h_u10 = hashlib.sha256(f.read()).hexdigest()

        manifest_path = f_dir / "run_manifest.json"
        manifest_data = {
            "manifest_version": "2.0.0",
            "experiment_classification": "BASELINE_PERSISTENCE",
            "init_time": "2026-10-25T00:00:00Z",
            "valid_time": "2026-10-26T00:00:00Z",
            "lead_time_hours": 24,
            "model": {"family": "Persistence", "checkpoint": "identity"},
            "forecast_artifacts": [
                {"name": "forecast_t2m.npy", "sha256": h_t2m},
                {"name": "forecast_u10m.npy", "sha256": h_u10},
            ],
        }
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        # Keep t2m untouched, tamper only with u10
        tampered_u10 = np.full((10, 10), 99.0, dtype=np.float32)
        np.save(f_u10, tampered_u10)

        with pytest.raises(
            ProvenanceIntegrityError, match="forecast_u10m.npy"
        ):
            verify_forecast(manifest_path=manifest_path)


class TestC_NoSyntheticSubstitution_Adversarial:
    """Adversarial challenge suite for Test C (No Synthetic Substitution)."""

    @pytest.mark.parametrize(
        "bad_classification",
        [
            "TRUTH_CONDITIONED_SYNTHETIC_DIAGNOSTIC",
            "SYNTHETIC_RUN",
            "SYNTHETIC_EXPERIMENT",
            "HISTORICAL_DIAGNOSTIC",
            "diagnostic_evaluation",
        ],
    )
    def test_synthetic_classification_rejected(
        self, tmp_path: Path, bad_classification: str
    ) -> None:
        """Any synthetic or diagnostic classification must be rejected in benchmark_mode."""
        f_dir = tmp_path / f"forecast_c_class_{abs(hash(bad_classification))}"
        f_dir.mkdir(parents=True, exist_ok=True)
        f_file = f_dir / "forecast_t2m.npy"
        np.save(f_file, np.zeros((10, 10), dtype=np.float32))

        with open(f_file, "rb") as f:
            valid_hash = hashlib.sha256(f.read()).hexdigest()

        manifest_path = f_dir / "run_manifest.json"
        manifest_data = {
            "manifest_version": "2.0.0",
            "experiment_classification": bad_classification,
            "init_time": "2026-10-25T00:00:00Z",
            "valid_time": "2026-10-26T00:00:00Z",
            "lead_time_hours": 24,
            "model": {"family": "Persistence", "checkpoint": "identity"},
            "forecast_artifacts": [
                {"name": "forecast_t2m.npy", "sha256": valid_hash}
            ],
        }
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        with pytest.raises(
            SyntheticSubstitutionError, match="[Ss]ynthetic.*rejected"
        ):
            verify_forecast(manifest_path=manifest_path, benchmark_mode=True)

    @pytest.mark.parametrize(
        "bad_model_family",
        ["synthetic_formula", "MOCK_NEURAL", "mock_forecast", "synthetic_proxy"],
    )
    def test_synthetic_model_family_rejected(
        self, tmp_path: Path, bad_model_family: str
    ) -> None:
        """Any synthetic or mock model family must be rejected in benchmark_mode."""
        f_dir = tmp_path / f"forecast_c_mod_{abs(hash(bad_model_family))}"
        f_dir.mkdir(parents=True, exist_ok=True)
        f_file = f_dir / "forecast_t2m.npy"
        np.save(f_file, np.zeros((10, 10), dtype=np.float32))

        with open(f_file, "rb") as f:
            valid_hash = hashlib.sha256(f.read()).hexdigest()

        manifest_path = f_dir / "run_manifest.json"
        manifest_data = {
            "manifest_version": "2.0.0",
            "experiment_classification": "REAL_MODEL_FORECAST",
            "init_time": "2026-10-25T00:00:00Z",
            "valid_time": "2026-10-26T00:00:00Z",
            "lead_time_hours": 24,
            "model": {"family": bad_model_family, "checkpoint": "none"},
            "forecast_artifacts": [
                {"name": "forecast_t2m.npy", "sha256": valid_hash}
            ],
        }
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        with pytest.raises(
            SyntheticSubstitutionError, match="[Ss]ynthetic.*rejected"
        ):
            verify_forecast(manifest_path=manifest_path, benchmark_mode=True)

    def test_historical_synthetic_formula_array_detected(
        self, tmp_path: Path
    ) -> None:
        """Historical formula (skill=0.72 + noise) must be detected by statistical residual check."""
        f_dir = tmp_path / "forecast_c_formula"
        f_dir.mkdir(parents=True, exist_ok=True)
        shape = (181, 360)
        rng = np.random.default_rng(42)

        truth = 288.15 + rng.normal(0, 5, shape).astype(np.float32)
        pers = truth + rng.normal(0, 2, shape).astype(np.float32)
        np.save(f_dir / "initial_condition.npy", pers)

        # Historical leakage formula
        delta = truth - pers
        noise = rng.normal(0, 0.45, shape).astype(np.float32)
        fc = (pers + delta * 0.72 + noise).astype(np.float32)

        f_file = f_dir / "forecast_t2m.npy"
        np.save(f_file, fc)

        with open(f_file, "rb") as f:
            valid_hash = hashlib.sha256(f.read()).hexdigest()

        # Adversary attempts to pass it off as genuine FourCastNet
        manifest_path = f_dir / "run_manifest.json"
        manifest_data = {
            "manifest_version": "2.0.0",
            "experiment_classification": "REAL_MODEL_FORECAST",
            "init_time": "2026-10-25T00:00:00Z",
            "valid_time": "2026-10-26T00:00:00Z",
            "lead_time_hours": 24,
            "model": {
                "family": "FourCastNet",
                "checkpoint": "fcn_v1.pth",
                "checkpoint_sha256": "abcdef123456",
            },
            "forecast_artifacts": [
                {"name": "forecast_t2m.npy", "sha256": valid_hash}
            ],
        }
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        verif_file = f_dir / "verif_truth.npy"
        np.save(verif_file, truth)

        with pytest.raises(
            SyntheticSubstitutionError,
            match="Synthetic residual correlation detected",
        ):
            verify_forecast(
                manifest_path=manifest_path,
                verification_dataset_path=verif_file,
                benchmark_mode=True,
            )


class TestE_ChronologicalCorrectness_Adversarial:
    """Adversarial challenge suite for Test E (Chronological Correctness)."""

    def test_manifest_internal_valid_time_inconsistency(
        self, tmp_path: Path
    ) -> None:
        """Manifest where valid_time != init_time + lead_time must raise ChronologyError."""
        f_dir = tmp_path / "forecast_e_math_inconsistency"
        f_dir.mkdir(parents=True, exist_ok=True)
        f_file = f_dir / "forecast_t2m.npy"
        np.save(f_file, np.zeros((10, 10), dtype=np.float32))

        with open(f_file, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()

        # Math inconsistency: init=00:00, lead=24h, valid claimed=12:00
        manifest_path = f_dir / "run_manifest.json"
        manifest_data = {
            "manifest_version": "2.0.0",
            "experiment_classification": "BASELINE_PERSISTENCE",
            "init_time": "2026-10-25T00:00:00Z",
            "valid_time": "2026-10-25T12:00:00Z",
            "lead_time_hours": 24,
            "model": {"family": "Persistence", "checkpoint": "identity"},
            "forecast_artifacts": [
                {"name": "forecast_t2m.npy", "sha256": h}
            ],
        }
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        with pytest.raises(ChronologyError, match="Invalid valid_time in manifest"):
            verify_forecast(manifest_path=manifest_path)

    def test_cross_epoch_historical_2026_vs_2024_rejection(
        self, tmp_path: Path
    ) -> None:
        """Comparing 2026 forecast to 2024 verification truth must raise ChronologyError."""
        f_dir = tmp_path / "forecast_e_cross_epoch"
        f_dir.mkdir(parents=True, exist_ok=True)
        f_file = f_dir / "forecast_t2m.npy"
        np.save(f_file, np.full((181, 360), 288.15, dtype=np.float32))

        with open(f_file, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()

        manifest_path = f_dir / "run_manifest.json"
        manifest_data = {
            "manifest_version": "2.0.0",
            "experiment_classification": "BASELINE_PERSISTENCE",
            "init_time": "2026-10-25T00:00:00Z",
            "valid_time": "2026-10-26T00:00:00Z",
            "lead_time_hours": 24,
            "model": {"family": "Persistence", "checkpoint": "identity"},
            "forecast_artifacts": [
                {"name": "forecast_t2m.npy", "sha256": h}
            ],
        }
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        # Held-out dataset from 2024-01-01 (34-month cross-epoch discrepancy)
        verif_data = {
            "valid_time": "2024-01-01T00:00:00Z",
            "variable": "t2m",
            "shape": [181, 360],
        }
        verif_file = tmp_path / "verif_cross_epoch.json"
        verif_file.write_text(json.dumps(verif_data, indent=2), encoding="utf-8")

        with pytest.raises(
            ChronologyError, match="Temporal alignment error|does not match"
        ):
            verify_forecast(
                manifest_path=manifest_path,
                verification_dataset_path=verif_file,
            )

    def test_sub_daily_hour_mismatch_rejection(self, tmp_path: Path) -> None:
        """Forecast valid at 00:00 UTC verified against 06:00 UTC must raise ChronologyError."""
        f_dir = tmp_path / "forecast_e_hour_mismatch"
        f_dir.mkdir(parents=True, exist_ok=True)
        f_file = f_dir / "forecast_t2m.npy"
        np.save(f_file, np.full((10, 10), 288.15, dtype=np.float32))

        with open(f_file, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()

        manifest_path = f_dir / "run_manifest.json"
        manifest_data = {
            "manifest_version": "2.0.0",
            "experiment_classification": "BASELINE_PERSISTENCE",
            "init_time": "2026-10-25T00:00:00Z",
            "valid_time": "2026-10-26T00:00:00Z",
            "lead_time_hours": 24,
            "model": {"family": "Persistence", "checkpoint": "identity"},
            "forecast_artifacts": [
                {"name": "forecast_t2m.npy", "sha256": h}
            ],
        }
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        verif_data = {
            "valid_time": "2026-10-26T06:00:00Z",
            "variable": "t2m",
            "shape": [10, 10],
        }
        verif_file = tmp_path / "verif_offset.json"
        verif_file.write_text(json.dumps(verif_data, indent=2), encoding="utf-8")

        with pytest.raises(ChronologyError, match="Temporal alignment error"):
            verify_forecast(
                manifest_path=manifest_path,
                verification_dataset_path=verif_file,
            )

    def test_spatial_grid_shape_mismatch_rejection(self, tmp_path: Path) -> None:
        """Forecast grid shape mismatch against truth array must raise ChronologyError."""
        f_dir = tmp_path / "forecast_e_grid_mismatch"
        f_dir.mkdir(parents=True, exist_ok=True)
        f_file = f_dir / "forecast_t2m.npy"
        np.save(f_file, np.full((181, 360), 288.15, dtype=np.float32))

        with open(f_file, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()

        manifest_path = f_dir / "run_manifest.json"
        manifest_data = {
            "manifest_version": "2.0.0",
            "experiment_classification": "BASELINE_PERSISTENCE",
            "init_time": "2026-10-25T00:00:00Z",
            "valid_time": "2026-10-26T00:00:00Z",
            "lead_time_hours": 24,
            "model": {"family": "Persistence", "checkpoint": "identity"},
            "forecast_artifacts": [
                {"name": "forecast_t2m.npy", "sha256": h}
            ],
        }
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        # Incompatible truth grid shape (721, 1440)
        verif_truth = np.full((721, 1440), 288.15, dtype=np.float32)
        verif_file = f_dir / "verif_highres.npy"
        np.save(verif_file, verif_truth)

        with pytest.raises(ChronologyError, match="Grid dimension mismatch"):
            verify_forecast(
                manifest_path=manifest_path,
                verification_dataset_path=verif_file,
            )


class TestF_RealModelIdentity_Adversarial:
    """Adversarial challenge suite for Test F (Real Model Identity)."""

    @pytest.mark.parametrize(
        "target_model",
        ["FourCastNet", "SFNO", "FourCastNet_v3", "FCN3"],
    )
    def test_persistence_cannot_be_labeled_as_neural_model(
        self, tmp_path: Path, target_model: str
    ) -> None:
        """Attempting to label executed Persistence as any neural model must strictly fail."""
        f_dir = tmp_path / f"forecast_f_pers_{target_model}"
        f_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "init_time": "2026-10-25T00:00:00Z",
            "valid_time": "2026-10-26T00:00:00Z",
            "lead_time_hours": 24,
            "model_family": "Persistence",
            "checkpoint": "identity",
        }
        (f_dir / "forecast_meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        np.save(
            f_dir / "forecast_t2m.npy",
            np.full((20, 20), 288.15, dtype=np.float32),
        )

        with pytest.raises(
            ModelIdentityMismatchError,
            match=f"Persistence cannot be labeled as {target_model}",
        ):
            freeze_forecast(
                forecast_dir=f_dir,
                model_family=target_model,
                checkpoint="fcn_v1.pth",
                checkpoint_sha256="abcdef123456",
            )

    def test_neural_model_freeze_requires_checkpoint_sha256(
        self, tmp_path: Path
    ) -> None:
        """Freezing a neural model without a non-null checkpoint_sha256 must raise ModelIdentityMismatchError."""
        f_dir = tmp_path / "forecast_f_missing_ckpt_hash"
        f_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "init_time": "2026-10-25T00:00:00Z",
            "valid_time": "2026-10-26T00:00:00Z",
            "lead_time_hours": 24,
            "model_family": "FourCastNet",
            "checkpoint": "fcn_v1.pth",
        }
        (f_dir / "forecast_meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        np.save(
            f_dir / "forecast_t2m.npy",
            np.full((20, 20), 288.15, dtype=np.float32),
        )

        with pytest.raises(
            ModelIdentityMismatchError,
            match="requires non-null checkpoint_sha256",
        ):
            freeze_forecast(
                forecast_dir=f_dir,
                model_family="FourCastNet",
                checkpoint="fcn_v1.pth",
                checkpoint_sha256=None,
            )

    def test_default_family_when_meta_missing_is_persistence(
        self, tmp_path: Path
    ) -> None:
        """When forecast_meta.json is missing, execution defaults to Persistence, preventing neural freeze."""
        f_dir = tmp_path / "forecast_f_no_meta"
        f_dir.mkdir(parents=True, exist_ok=True)
        np.save(
            f_dir / "forecast_t2m.npy",
            np.full((20, 20), 288.15, dtype=np.float32),
        )

        # Missing forecast_meta.json -> defaults executed_family to Persistence
        with pytest.raises(
            ModelIdentityMismatchError,
            match="Persistence cannot be labeled as FourCastNet",
        ):
            freeze_forecast(
                forecast_dir=f_dir,
                model_family="FourCastNet",
                checkpoint="fcn_v1.pth",
                checkpoint_sha256="abcdef123456",
            )
