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
# Compliance: .agents/rules/e2s-014-scientific-integrity.mdc

"""Permanent Anti-Leakage Guardrails Regression Test Suite.

Tests:
1. Runtime Signature, AST & Call-Stack Isolation (`forecast_stage.py`, `earth2_001/forecast_stage.py`)
2. Statistical Residual & Correlation Anomaly Detection (`verify_stage.py`, `earth2_001/verify_stage.py`)
3. Cryptographic Sealing of `execution_manifest.json` in `outputs/scientific_study_verified/`
4. Mandatory Quarantine Stamping (`QUARANTINED_DEFECTIVE_SYNTHETIC`) across Historical Scripts
5. Edge Cases (NaN/Inf arrays, zero variance fields, boundary alpha slopes, dimension mismatches)

Attribution: Zhane Daye, Origin Datum (https://origindatum.space, contact@origindatum.space)
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import xarray as xr

from od_experiments.earth2_001.forecast_stage import (
    anti_leakage_forecast_guard,
    enforce_call_stack_isolation,
    inspect_callable_for_leakage,
    run_forecast,
)
from od_experiments.earth2_001.verify_stage import (
    DEFAULT_VERIFIED_MANIFEST_PATH,
    ChronologyError,
    ProvenanceIntegrityError,
    SyntheticSubstitutionError,
    TargetLeakageError,
    compute_sha256,
    detect_residual_leakage_anomaly,
    seal_execution_manifest,
    validate_execution_manifest,
    verify_forecast,
)
from od_experiments.scientific_study.historical import (
    QUARANTINE_STAMP,
    assert_quarantine_stamped,
    stamp_quarantined_dict,
    study_runner_historical,
)
from od_experiments.scientific_study.historical import (
    study_runner as historical_alias_runner,
)
from od_experiments.scientific_study.pipeline.freeze_stage import freeze_forecast


class TestSignatureAndASTIsolation:
    """Verify signature, AST, closure, and call-stack isolation guardrails."""

    @pytest.mark.parametrize(
        "forbidden_kwarg",
        ["y_truth", "target", "verification_data", "ground_truth"],
    )
    def test_run_forecast_rejects_forbidden_target_kwargs(
        self, tmp_path: Path, forbidden_kwarg: str
    ) -> None:
        """run_forecast must immediately raise TargetLeakageError if called with forbidden target kwargs."""
        t0 = datetime.datetime(2026, 10, 28, 0, 0, tzinfo=datetime.timezone.utc)
        x0 = np.full((16, 32), 288.0, dtype=np.float32)
        truth = np.full((16, 32), 290.0, dtype=np.float32)

        with pytest.raises(TargetLeakageError, match="Signature isolation violation"):
            run_forecast(
                init_time=t0,
                initial_condition=x0,
                output_dir=tmp_path,
                **{forbidden_kwarg: truth},
            )

    def test_model_accepting_y_truth_in_signature_is_blocked(
        self, tmp_path: Path
    ) -> None:
        """A model whose forward() signature accepts y_truth/target/verification_data is blocked."""

        class LeakedSignatureModel:
            def forward(
                self, x0: np.ndarray, y_truth: np.ndarray | None = None
            ) -> np.ndarray:
                return x0

        t0 = datetime.datetime(2026, 10, 28, 0, 0, tzinfo=datetime.timezone.utc)
        x0 = np.ones((16, 32), dtype=np.float32)

        with pytest.raises(TargetLeakageError, match="Signature isolation violation"):
            run_forecast(
                init_time=t0,
                model_family="FourCastNet",
                model=LeakedSignatureModel(),
                initial_condition=x0,
                output_dir=tmp_path,
            )

    def test_model_referencing_y_truth_in_ast_is_blocked(self, tmp_path: Path) -> None:
        """A model whose AST references y_truth or linear shrinkage formula is blocked before execution."""

        class LeakedASTModel:
            def forward(self, x0: np.ndarray) -> np.ndarray:
                # Simulates hidden reference to y_truth inside AST
                y_truth = x0 + 2.0
                return x0 + 0.72 * (y_truth - x0)

        t0 = datetime.datetime(2026, 10, 28, 0, 0, tzinfo=datetime.timezone.utc)
        x0 = np.ones((16, 32), dtype=np.float32)

        with pytest.raises(TargetLeakageError, match="AST isolation violation"):
            run_forecast(
                init_time=t0,
                model_family="FourCastNet",
                model=LeakedASTModel(),
                initial_condition=x0,
                output_dir=tmp_path,
            )

    def test_model_storing_forbidden_target_attribute_is_blocked(
        self, tmp_path: Path
    ) -> None:
        """A model storing `y_truth` or `verification_data` as an instance attribute is blocked."""

        class AttributeLeakedModel:
            def __init__(self, hidden_truth: np.ndarray) -> None:
                self.y_truth = hidden_truth

            def forward(self, x0: np.ndarray) -> np.ndarray:
                return x0.copy()

        t0 = datetime.datetime(2026, 10, 28, 0, 0, tzinfo=datetime.timezone.utc)
        x0 = np.ones((16, 32), dtype=np.float32)

        with pytest.raises(
            TargetLeakageError, match="Object attribute isolation violation"
        ):
            run_forecast(
                init_time=t0,
                model_family="FourCastNet",
                model=AttributeLeakedModel(x0),
                initial_condition=x0,
                output_dir=tmp_path,
            )

    def test_decorator_blocks_function_with_target_param(self) -> None:
        """@anti_leakage_forecast_guard blocks decorating a function that accepts target/verification_data."""
        with pytest.raises(TargetLeakageError, match="Signature isolation violation"):

            @anti_leakage_forecast_guard
            def bad_forecast_fn(
                x0: np.ndarray, verification_data: np.ndarray
            ) -> np.ndarray:
                return x0

    def test_call_stack_isolation_blocks_caller_with_target_parameter(
        self, tmp_path: Path
    ) -> None:
        """If a caller function accepts `y_truth` as a parameter and invokes run_forecast, call-stack isolation blocks it."""
        t0 = datetime.datetime(2026, 10, 28, 0, 0, tzinfo=datetime.timezone.utc)
        x0 = np.ones((16, 32), dtype=np.float32)

        def leaky_wrapper(init_state: np.ndarray, y_truth: np.ndarray) -> Path:
            return run_forecast(
                init_time=t0,
                initial_condition=init_state,
                output_dir=tmp_path,
            )

        with pytest.raises(
            TargetLeakageError, match="Call-stack signature isolation violation"
        ):
            leaky_wrapper(x0, x0)

    def test_call_stack_locals_isolation(self) -> None:
        """enforce_call_stack_isolation(check_caller_locals=True) blocks frames holding y_truth in locals."""

        def inner_check() -> None:
            enforce_call_stack_isolation(check_caller_locals=True, max_depth=2)

        def caller_with_local_truth() -> None:
            y_truth = np.ones((4, 4))  # noqa: F841
            inner_check()

        with pytest.raises(
            TargetLeakageError, match="Call-stack variable isolation violation"
        ):
            caller_with_local_truth()

    def test_clean_model_passes_signature_and_ast_inspection(self) -> None:
        """A genuine initial-condition-only model passes inspect_callable_for_leakage."""

        class CleanPrognosticModel:
            def forward(self, initial_condition: np.ndarray) -> np.ndarray:
                return initial_condition * 0.999

        audit = inspect_callable_for_leakage(CleanPrognosticModel())
        assert audit["signature_verified"] is True
        assert audit["ast_verified"] is True


class TestStatisticalResidualAnomalyDetection:
    """Verify statistical residual & correlation anomaly detection against linear target shrinkage."""

    def test_historical_072_synthetic_leakage_raises_target_leakage_error(
        self, tmp_path: Path
    ) -> None:
        """The exact historical formula `x0 + 0.72 * (y_truth - x0) + N(0, 0.45)` raises TargetLeakageError."""
        rng = np.random.default_rng(42)
        x0 = rng.normal(288.0, 5.0, size=(64, 128)).astype(np.float32)
        y_truth = x0 + rng.normal(0.0, 2.5, size=(64, 128)).astype(np.float32)
        leaked_forecast = (
            x0
            + 0.72 * (y_truth - x0)
            + rng.normal(0.0, 0.45, size=(64, 128)).astype(np.float32)
        )

        with pytest.raises(TargetLeakageError) as exc_info:
            detect_residual_leakage_anomaly(
                forecast=leaked_forecast,
                truth=y_truth,
                initial_condition=x0,
                checkpoint_sha256=None,
            )
        # Ensure subclass relationship with SyntheticSubstitutionError holds
        assert isinstance(exc_info.value, SyntheticSubstitutionError)
        assert "Synthetic residual correlation detected" in str(exc_info.value)

    @pytest.mark.parametrize("alpha", [0.25, 0.50, 0.72, 0.90])
    def test_arbitrary_linear_shrinkage_toward_truth_is_rejected(
        self, alpha: float
    ) -> None:
        """Linear shrinkage across a wide range of alpha values without verified checkpoint hash is rejected."""
        rng = np.random.default_rng(100 + int(alpha * 100))
        x0 = rng.normal(285.0, 8.0, size=(64, 128)).astype(np.float32)
        y_truth = x0 + rng.normal(0.0, 3.0, size=(64, 128)).astype(np.float32)
        leaked_fc = (
            x0
            + alpha * (y_truth - x0)
            + rng.normal(0.0, 0.35, size=(64, 128)).astype(np.float32)
        )

        with pytest.raises(TargetLeakageError):
            detect_residual_leakage_anomaly(
                forecast=leaked_fc,
                truth=y_truth,
                initial_condition=x0,
                checkpoint_sha256=None,
            )

    def test_verify_forecast_pipeline_rejects_leaked_forecast_artifact(
        self, tmp_path: Path
    ) -> None:
        """End-to-end verify_forecast rejects a frozen manifest whose forecast tensor has target shrinkage."""
        rng = np.random.default_rng(7)
        x0 = rng.normal(288.0, 6.0, size=(45, 90)).astype(np.float32)
        y_truth = x0 + rng.normal(0.0, 2.5, size=(45, 90)).astype(np.float32)
        leaked_fc = (
            x0
            + 0.72 * (y_truth - x0)
            + rng.normal(0.0, 0.45, size=(45, 90)).astype(np.float32)
        )

        fc_dir = tmp_path / "forecast"
        fc_dir.mkdir(parents=True, exist_ok=True)
        np.save(fc_dir / "initial_condition.npy", x0)
        np.save(fc_dir / "forecast_t2m.npy", leaked_fc)
        meta = {
            "init_time": "2026-10-28T00:00:00+00:00",
            "valid_time": "2026-10-29T00:00:00+00:00",
            "lead_time_hours": 24,
            "model_family": "Persistence",
            "checkpoint": "identity",
            "checkpoint_sha256": None,
        }
        (fc_dir / "forecast_meta.json").write_text(json.dumps(meta), encoding="utf-8")
        freeze_forecast(forecast_dir=fc_dir, output_dir=fc_dir)

        truth_file = tmp_path / "truth.npy"
        np.save(truth_file, y_truth)

        with pytest.raises(TargetLeakageError):
            verify_forecast(
                manifest_path=fc_dir / "run_manifest.json",
                verification_dataset_path=truth_file,
                benchmark_mode=True,
            )

    def test_authentic_persistence_forecast_passes_residual_check(self) -> None:
        """Genuine Persistence (y_hat == x_0) has alpha=0.0 and passes residual anomaly detection."""
        rng = np.random.default_rng(99)
        x0 = rng.normal(288.0, 6.0, size=(32, 64)).astype(np.float32)
        y_truth = x0 + rng.normal(0.0, 2.2, size=(32, 64)).astype(np.float32)
        pers_fc = x0.copy()

        audit = detect_residual_leakage_anomaly(
            forecast=pers_fc,
            truth=y_truth,
            initial_condition=x0,
            checkpoint_sha256=None,
        )
        assert audit["target_leakage_detected"] is False
        assert audit["empirical_alpha_slope"] == 0.0


class TestCryptographicSealingValidation:
    """Verify cryptographic sealing of execution_manifest.json in outputs/scientific_study_verified/."""

    def test_verified_execution_manifest_on_disk_is_valid(self) -> None:
        """The production execution_manifest.json in outputs/scientific_study_verified/ must pass full cryptographic validation."""
        assert DEFAULT_VERIFIED_MANIFEST_PATH.exists(), (
            f"Expected {DEFAULT_VERIFIED_MANIFEST_PATH} to exist on disk"
        )
        manifest = validate_execution_manifest(
            DEFAULT_VERIFIED_MANIFEST_PATH, verify_files_on_disk=True
        )
        assert manifest["manifest_version"] == "2.0.0"
        assert len(manifest["input_artifacts"]) >= 1
        assert len(manifest["forecast_outputs"]) >= 1
        assert len(manifest["ground_truth_analysis"]) >= 1
        assert manifest["zero_leakage_audit"]["status"] == "VERIFIED_ZERO_LEAKAGE"

    def test_verify_forecast_with_require_execution_manifest_succeeds_on_verified_dir(
        self,
    ) -> None:
        """verify_forecast(..., require_execution_manifest=True) succeeds on outputs/scientific_study_verified/execution_manifest.json."""
        results = verify_forecast(
            manifest_path=DEFAULT_VERIFIED_MANIFEST_PATH,
            require_execution_manifest=True,
        )
        assert results["status"] == "VERIFIED_GENUINE"
        assert results["skill_score_vs_persistence"] == 0.0
        assert results["residual_leakage_audit"]["target_leakage_detected"] is False

    def test_tampered_artifact_hash_in_execution_manifest_raises_error(
        self, tmp_path: Path
    ) -> None:
        """Modifying a single byte of any sealed artifact invalidates execution_manifest.json."""
        x0 = np.full((16, 32), 285.0, dtype=np.float32)
        fc = x0.copy()
        gt = np.full((16, 32), 286.5, dtype=np.float32)

        np.save(tmp_path / "initial_condition.npy", x0)
        np.save(tmp_path / "forecast_t2m.npy", fc)
        np.save(tmp_path / "verifying_truth_t2m.npy", gt)

        seal_execution_manifest(output_dir=tmp_path)
        # Validate clean manifest first
        validate_execution_manifest(tmp_path / "execution_manifest.json")

        # Tamper with ground truth file on disk
        gt_tampered = gt + 0.01
        np.save(tmp_path / "verifying_truth_t2m.npy", gt_tampered)

        with pytest.raises(ProvenanceIntegrityError, match="SHA-256 mismatch"):
            validate_execution_manifest(tmp_path / "execution_manifest.json")

    def test_neural_model_without_checkpoint_sha256_is_rejected(
        self, tmp_path: Path
    ) -> None:
        """A non-Persistence model in execution_manifest.json without a valid 64-char SHA-256 checkpoint hash is rejected."""
        x0 = np.full((8, 16), 285.0, dtype=np.float32)
        np.save(tmp_path / "initial_condition.npy", x0)
        np.save(tmp_path / "forecast_t2m.npy", x0)
        np.save(tmp_path / "verifying_truth_t2m.npy", x0)

        seal_execution_manifest(
            output_dir=tmp_path,
            model_family="FourCastNet",
            checkpoint="fcn_weights.pt",
            checkpoint_sha256=None,
        )

        with pytest.raises(
            ProvenanceIntegrityError,
            match="requires a valid 64-char SHA-256 'checkpoint_sha256'",
        ):
            validate_execution_manifest(tmp_path / "execution_manifest.json")

    def test_missing_ground_truth_section_in_execution_manifest_is_rejected(
        self, tmp_path: Path
    ) -> None:
        """execution_manifest.json missing ground_truth_analysis or input_artifacts is rejected."""
        bad_manifest = {
            "manifest_version": "2.0.0",
            "model_checkpoints": {
                "family": "Persistence",
                "checkpoint": "identity",
            },
            "input_artifacts": [],
            "forecast_outputs": [],
            "ground_truth_analysis": [],
        }
        m_file = tmp_path / "execution_manifest.json"
        m_file.write_text(json.dumps(bad_manifest), encoding="utf-8")

        with pytest.raises(ProvenanceIntegrityError, match="missing non-empty"):
            validate_execution_manifest(m_file, verify_files_on_disk=False)


class TestHistoricalScriptsQuarantine:
    """Ensure all historical scripts stamp QUARANTINED_DEFECTIVE_SYNTHETIC in every output dict and report header."""

    def test_stored_historical_study_metrics_json_is_quarantined(self) -> None:
        """outputs/scientific_study/study_metrics.json must carry QUARANTINED_DEFECTIVE_SYNTHETIC in root and all cycles."""
        metrics_path = Path("outputs/scientific_study/study_metrics.json")
        assert metrics_path.exists()
        data = json.loads(metrics_path.read_text(encoding="utf-8"))
        assert_quarantine_stamped(data)
        assert data["quarantine_status"] == QUARANTINE_STAMP
        assert QUARANTINE_STAMP in data["experiment_classification"]
        for cycle in data["cycles"]:
            assert cycle["quarantine_status"] == QUARANTINE_STAMP

    def test_historical_runner_execution_stamps_every_output_dict_and_header(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Executing run_full_study in study_runner_historical stamps QUARANTINED_DEFECTIVE_SYNTHETIC everywhere."""
        lats = np.linspace(90, -90, 721)
        lons = np.linspace(0, 359.75, 1440)
        rng = np.random.default_rng(42)

        def mock_fetch_cycle_pair(
            init_time: datetime.datetime,
            lead_hours: int = 24,
            variables: list[str] = ["t2m", "msl"],
        ) -> tuple[xr.DataArray, xr.DataArray]:
            t2m_0 = 285.0 + rng.normal(0, 2.0, (1, 1, 721, 1440)).astype(np.float32)
            msl_0 = 101325.0 + rng.normal(0, 300.0, (1, 1, 721, 1440)).astype(
                np.float32
            )
            t2m_1 = t2m_0 + rng.normal(0, 1.5, (1, 1, 721, 1440)).astype(np.float32)
            msl_1 = msl_0 + rng.normal(0, 200.0, (1, 1, 721, 1440)).astype(np.float32)

            da0 = xr.DataArray(
                np.concatenate([t2m_0, msl_0], axis=1),
                coords={
                    "time": [init_time],
                    "variable": ["t2m", "msl"],
                    "lat": lats,
                    "lon": lons,
                },
                dims=["time", "variable", "lat", "lon"],
            )
            da1 = xr.DataArray(
                np.concatenate([t2m_1, msl_1], axis=1),
                coords={
                    "time": [init_time + datetime.timedelta(hours=lead_hours)],
                    "variable": ["t2m", "msl"],
                    "lat": lats,
                    "lon": lons,
                },
                dims=["time", "variable", "lat", "lon"],
            )
            return da0, da1

        out_dir = tmp_path / "scientific_study"
        rep_path = tmp_path / "SCIENTIFIC_STUDY_REPORT.md"
        monkeypatch.setattr(study_runner_historical, "STUDY_OUTPUT_DIR", out_dir)
        monkeypatch.setattr(study_runner_historical, "REPORT_PATH", rep_path)
        monkeypatch.setattr(
            study_runner_historical, "fetch_cycle_pair", mock_fetch_cycle_pair
        )

        summary = study_runner_historical.run_full_study(num_days=1)
        report_md = rep_path.read_text(encoding="utf-8")

        assert_quarantine_stamped(summary, report_text=report_md)
        assert summary["quarantine_status"] == QUARANTINE_STAMP
        assert QUARANTINE_STAMP in summary["study_title"]
        assert QUARANTINE_STAMP in summary["experiment_classification"]
        assert summary["cycles"][0]["quarantine_status"] == QUARANTINE_STAMP
        assert (
            summary["cycles"][0]["metrics_t2m"]["quarantine_status"] == QUARANTINE_STAMP
        )
        assert report_md.startswith(f"# [{QUARANTINE_STAMP}]")

    def test_unquarantined_dict_is_blocked_by_assert_quarantine_stamped(
        self,
    ) -> None:
        """assert_quarantine_stamped raises RuntimeError if any dict or header lacks QUARANTINED_DEFECTIVE_SYNTHETIC."""
        unquarantined: dict[str, Any] = {
            "experiment_classification": "TRUTH_CONDITIONED_SYNTHETIC_DIAGNOSTIC",
            "cycles": [{"cycle": "2026-10-20"}],
        }
        with pytest.raises(
            RuntimeError, match="Unquarantined historical output blocked"
        ):
            assert_quarantine_stamped(unquarantined)

        stamped = stamp_quarantined_dict(unquarantined)
        assert_quarantine_stamped(stamped)

        with pytest.raises(RuntimeError, match="Unquarantined report header blocked"):
            assert_quarantine_stamped(
                stamped, report_text="# Clean Looking Report Header\nNo stamp"
            )

    def test_legacy_study_runner_entrypoints_are_identical_to_quarantined(
        self,
    ) -> None:
        """Both od_experiments.scientific_study.study_runner and historical.study_runner point to the quarantined implementation."""
        from od_experiments.scientific_study import study_runner as root_runner

        assert root_runner.QUARANTINE_STAMP == QUARANTINE_STAMP
        assert historical_alias_runner.QUARANTINE_STAMP == QUARANTINE_STAMP
        assert root_runner.run_full_study is study_runner_historical.run_full_study


class TestEdgeCasesAndBoundaries:
    """Test edge cases: NaN/Inf inputs, small arrays, zero-variance fields, and shape mismatches."""

    def test_residual_anomaly_handles_nan_and_small_valid_arrays(self) -> None:
        """Arrays with fewer than 4 finite values return a safe non-leaked audit dict without crashing."""
        fc = np.array([[np.nan, np.nan], [np.inf, 288.0]], dtype=np.float32)
        tr = np.array([[np.nan, 289.0], [287.0, 288.0]], dtype=np.float32)
        x0 = np.array([[288.0, 288.0], [288.0, 288.0]], dtype=np.float32)

        res = detect_residual_leakage_anomaly(fc, tr, x0)
        assert res["target_leakage_detected"] is False
        assert res["empirical_alpha_slope"] == 0.0

    def test_residual_anomaly_raises_chronology_error_on_shape_mismatch(
        self,
    ) -> None:
        """Mismatched grid shapes between forecast, truth, and initial condition raise ChronologyError."""
        fc = np.zeros((16, 32), dtype=np.float32)
        tr = np.zeros((16, 64), dtype=np.float32)
        x0 = np.zeros((16, 32), dtype=np.float32)

        with pytest.raises(ChronologyError, match="Grid dimension mismatch"):
            detect_residual_leakage_anomaly(fc, tr, x0)

    def test_residual_anomaly_allows_verified_checkpoint_hash_on_disk(
        self, tmp_path: Path
    ) -> None:
        """When a genuine model checkpoint file exists on disk and its SHA-256 matches checkpoint_sha256, it is recognized."""
        ckpt_file = tmp_path / "real_weights.pt"
        ckpt_file.write_bytes(b"AUTHENTIC_MODEL_WEIGHTS_BINARY_PAYLOAD")
        ckpt_sha = compute_sha256(ckpt_file)

        rng = np.random.default_rng(11)
        x0 = rng.normal(288.0, 5.0, size=(32, 64)).astype(np.float32)
        y_truth = x0 + rng.normal(0.0, 2.5, size=(32, 64)).astype(np.float32)
        # Skilful forecast that is NOT the exact 0.72 historical synthetic signature
        fc = (
            x0
            + 0.45 * (y_truth - x0)
            + rng.normal(0.0, 0.8, size=(32, 64)).astype(np.float32)
        )

        audit = detect_residual_leakage_anomaly(
            forecast=fc,
            truth=y_truth,
            initial_condition=x0,
            checkpoint_sha256=ckpt_sha,
            checkpoint_path=ckpt_file,
        )
        assert audit["has_verified_checkpoint"] is True
        assert audit["target_leakage_detected"] is False

    def test_nonlinear_tanh_shrinkage_toward_truth_is_rejected(self) -> None:
        """Non-linear shrinkage y_hat = x_0 + tanh(0.72 * (y_truth - x_0)) + noise is caught by residual anomaly detection."""
        rng = np.random.default_rng(314)
        x0 = rng.normal(288.0, 5.0, size=(64, 128)).astype(np.float32)
        y_truth = x0 + rng.normal(0.0, 2.0, size=(64, 128)).astype(np.float32)
        nonlinear_leaked = (
            x0
            + 1.8 * np.tanh(0.55 * (y_truth - x0))
            + rng.normal(0.0, 0.30, size=(64, 128)).astype(np.float32)
        )

        with pytest.raises(TargetLeakageError):
            detect_residual_leakage_anomaly(
                forecast=nonlinear_leaked,
                truth=y_truth,
                initial_condition=x0,
                checkpoint_sha256=None,
            )

    def test_closure_capturing_forbidden_nonlocal_in_model_method_is_blocked(
        self, tmp_path: Path
    ) -> None:
        """A model whose forward() captures a forbidden nonlocal (`y_truth`) from enclosing scope is blocked."""
        y_truth = np.full((16, 32), 295.0, dtype=np.float32)

        class ClosureLeakedModel:
            def forward(self, x0: np.ndarray) -> np.ndarray:
                return (x0 + y_truth) * 0.5

        t0 = datetime.datetime(2026, 10, 28, 0, 0, tzinfo=datetime.timezone.utc)
        x0 = np.full((16, 32), 288.0, dtype=np.float32)

        with pytest.raises(
            TargetLeakageError,
            match="Closure isolation violation|AST isolation violation",
        ):
            run_forecast(
                init_time=t0,
                model_family="FourCastNet",
                model=ClosureLeakedModel(),
                initial_condition=x0,
                output_dir=tmp_path,
            )

    def test_ast_blocks_string_literal_dictionary_lookup_of_y_truth(
        self, tmp_path: Path
    ) -> None:
        """A model attempting to read `_cache['y_truth']` via string literal is blocked by AST inspection."""
        _cache = {"y_truth": np.full((16, 32), 295.0, dtype=np.float32)}

        class DictLookupLeakedModel:
            def forward(self, x0: np.ndarray) -> np.ndarray:
                return x0 + 0.5 * (_cache["y_truth"] - x0)

        t0 = datetime.datetime(2026, 10, 28, 0, 0, tzinfo=datetime.timezone.utc)
        x0 = np.full((16, 32), 288.0, dtype=np.float32)

        with pytest.raises(TargetLeakageError, match="AST isolation violation"):
            run_forecast(
                init_time=t0,
                model_family="FourCastNet",
                model=DictLookupLeakedModel(),
                initial_condition=x0,
                output_dir=tmp_path,
            )

    def test_benchmark_runner_rejects_leaked_candidate_forecast(self) -> None:
        """BenchmarkRunner.audit_candidate_forecast_against_leakage raises TargetLeakageError on leaked arrays."""
        from od_experiments.model_comparison.benchmark_runner import BenchmarkRunner

        runner = BenchmarkRunner(mock=True, lat_size=16, lon_size=32)
        rng = np.random.default_rng(77)
        x0 = rng.normal(288.0, 5.0, size=(16, 32)).astype(np.float32)
        truth = x0 + rng.normal(0.0, 2.5, size=(16, 32)).astype(np.float32)
        leaked = (
            x0
            + 0.72 * (truth - x0)
            + rng.normal(0.0, 0.45, size=(16, 32)).astype(np.float32)
        )

        with pytest.raises(TargetLeakageError):
            runner.audit_candidate_forecast_against_leakage(
                forecast=leaked,
                truth=truth,
                initial_condition=x0,
            )

    def test_stored_historical_markdown_report_is_quarantine_stamped(self) -> None:
        """docs/origin_datum/SCIENTIFIC_STUDY_REPORT.md on disk must carry QUARANTINED_DEFECTIVE_SYNTHETIC in its header."""
        report_path = Path("docs/origin_datum/SCIENTIFIC_STUDY_REPORT.md")
        assert report_path.exists()
        report_text = report_path.read_text(encoding="utf-8")
        metrics_data = json.loads(
            Path("outputs/scientific_study/study_metrics.json").read_text(
                encoding="utf-8"
            )
        )
        assert_quarantine_stamped(metrics_data, report_text=report_text)
        assert report_text.startswith(f"# [{QUARANTINE_STAMP}]")

    def test_advanced_capabilities_and_real_experiment_have_no_target_leakage_or_hardcoded_literals(
        self,
    ) -> None:
        """Verify run_all_advanced_capabilities.py does not reference v_truth in candidate forecasts and execute_real_experiment.py contains no hardcoded literals."""
        import ast

        adv_path = Path("od_experiments/run_all_advanced_capabilities.py")
        assert adv_path.exists()
        adv_source = adv_path.read_text(encoding="utf-8")
        adv_tree = ast.parse(adv_source)

        target_vars = {"p_init", "fcn_pred", "sfno_pred", "graphcast_pred"}
        found_assignments: set[str] = set()
        for node in ast.walk(adv_tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in target_vars:
                        found_assignments.add(target.id)
                        rhs_names = {
                            n.id
                            for n in ast.walk(node.value)
                            if isinstance(n, ast.Name)
                        }
                        assert "v_truth" not in rhs_names, (
                            f"Target leakage detected in {adv_path}: '{target.id}' references 'v_truth'"
                        )
        assert found_assignments == target_vars

        real_exp_path = Path("od_experiments/earth2_001/execute_real_experiment.py")
        assert real_exp_path.exists()
        real_exp_source = real_exp_path.read_text(encoding="utf-8")
        for forbidden_literal in (
            "0.3120",
            "0.312",
            "0.9850",
            "0.985",
            "0.7640",
            "0.764",
            "0.7890",
            "0.789",
        ):
            assert forbidden_literal not in real_exp_source, (
                f"Hardcoded float literal {forbidden_literal} found in {real_exp_path}"
            )
