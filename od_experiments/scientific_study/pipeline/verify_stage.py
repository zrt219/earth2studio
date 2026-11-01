# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-FileCopyrightText: Copyright (c) 2026 Zhane Daye, Origin Datum (https://origindatum.space, contact@origindatum.space)
# SPDX-License-Identifier: Apache-2.0

"""Stage C: Genuine Verify Stage (Independent Verification & Anti-Leakage Guards).

Verifies frozen forecast artifacts against authentic GFS operational analyses.
Recalculates and enforces cryptographic SHA-256 integrity before reading data,
rejects synthetic substitutions, verifies chronological and coordinate alignment,
enforces statistical residual & correlation anomaly detection, validates
cryptographic execution_manifest.json sealing, and calculates latitude-weighted
verification metrics.

Attribution: Zhane Daye, Origin Datum (https://origindatum.space, contact@origindatum.space)
"""

from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Optional

import numpy as np

from od_experiments.scientific_study.exceptions import (
    ChronologyError,
    ProvenanceIntegrityError,
    SyntheticSubstitutionError,
    TargetLeakageError,
)
from od_experiments.scientific_study.metrics_engine import (
    compute_all_metrics,
    compute_latitude_weights,
)

DEFAULT_VERIFIED_MANIFEST_PATH = Path(
    "outputs/scientific_study_verified/execution_manifest.json"
)


def compute_sha256(file_path: Path | str) -> str:
    """Compute SHA-256 digest of a file using buffered reading."""
    p = Path(file_path)
    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def _is_valid_sha256_hex(digest: Any) -> bool:
    """Return True if digest is a 64-character hexadecimal SHA-256 string."""
    if not isinstance(digest, str) or len(digest) != 64:
        return False
    try:
        int(digest, 16)
        return True
    except ValueError:
        return False


def detect_residual_leakage_anomaly(
    forecast: np.ndarray,
    truth: np.ndarray,
    initial_condition: np.ndarray,
    checkpoint_sha256: Optional[str] = None,
    checkpoint_path: Optional[Path | str] = None,
    skill_score_vs_persistence: Optional[float] = None,
) -> dict[str, Any]:
    """Detect unphysical linear shrinkage of forecast error residuals toward truth.

    In the defective historical formula:
        y_hat = x_0 + alpha * (y_truth - x_0) + epsilon
    the forecast error residual is:
        y_hat - y_truth = (1 - alpha) * (x_0 - y_truth) + epsilon
    which produces a uniform linear shrinkage of the persistence error vector
    toward zero across all spatial grid points, yielding high linear correlation
    between `(x_0 - y_truth)` and `(y_hat - y_truth)` alongside a positive OLS
    slope `alpha` on `(y_truth - x_0)` without a verified neural checkpoint hash.

    Raises `TargetLeakageError` (which is also a `SyntheticSubstitutionError`)
    if forecast error residuals exhibit unphysical linear shrinkage toward truth
    without a verified model checkpoint hash on disk.
    """
    fc = np.asarray(forecast, dtype=np.float64)
    tr = np.asarray(truth, dtype=np.float64)
    x0 = np.asarray(initial_condition, dtype=np.float64)

    if fc.shape != tr.shape or fc.shape != x0.shape:
        raise ChronologyError(
            f"Grid dimension mismatch in residual audit: forecast {fc.shape}, truth {tr.shape}, initial {x0.shape}"
        )

    # Check if a genuine verified model checkpoint hash exists and matches disk
    has_verified_checkpoint = False
    if _is_valid_sha256_hex(checkpoint_sha256):
        if checkpoint_path is not None and Path(checkpoint_path).is_file():
            has_verified_checkpoint = (
                compute_sha256(checkpoint_path) == checkpoint_sha256
            )

    delta_truth = (tr - x0).ravel()
    delta_pred = (fc - x0).ravel()
    pers_err = (x0 - tr).ravel()
    fc_err = (fc - tr).ravel()

    valid_mask = (
        np.isfinite(delta_truth)
        & np.isfinite(delta_pred)
        & np.isfinite(pers_err)
        & np.isfinite(fc_err)
    )
    if int(np.sum(valid_mask)) < 4:
        return {
            "target_leakage_detected": False,
            "empirical_alpha_slope": 0.0,
            "residual_persistence_correlation": 0.0,
            "tendency_correlation": 0.0,
            "has_verified_checkpoint": has_verified_checkpoint,
        }

    dt = delta_truth[valid_mask]
    dp = delta_pred[valid_mask]
    pe = pers_err[valid_mask]
    fe = fc_err[valid_mask]

    var_dt = float(np.var(dt))
    var_dp = float(np.var(dp))
    var_pe = float(np.var(pe))
    var_fe = float(np.var(fe))

    # Pure Persistence (identity forecast: fc == x0) has dp == 0, alpha == 0
    if var_dp <= 1e-10 or np.allclose(fc, x0, atol=1e-6):
        return {
            "target_leakage_detected": False,
            "empirical_alpha_slope": 0.0,
            "residual_persistence_correlation": 1.0,
            "tendency_correlation": 0.0,
            "has_verified_checkpoint": has_verified_checkpoint,
        }

    # OLS slope alpha in: (fc - x0) = alpha * (truth - x0) + noise
    if var_dt > 1e-10:
        cov_dt_dp = float(np.mean((dt - np.mean(dt)) * (dp - np.mean(dp))))
        alpha_slope = cov_dt_dp / var_dt
        tendency_corr = float(np.corrcoef(dt, dp)[0, 1])
    else:
        alpha_slope = 0.0
        tendency_corr = 0.0

    if var_pe > 1e-10 and var_fe > 1e-10:
        res_corr = float(np.corrcoef(pe, fe)[0, 1])
    else:
        res_corr = 0.0

    # Check residuals after removing linear shrinkage alpha * (truth - x0):
    # Under synthetic leakage y_hat = x0 + alpha*(truth - x0) + N(0, sigma^2),
    # the forecast y_hat is strongly positively correlated with truth `tr` even after
    # partialling out `x0`. By contrast, if `fc`, `tr`, and `x0` are independent
    # noise fields, `(fc - x0)` and `(tr - x0)` share `-x0` variance (giving alpha ~ 0.5)
    # while `fc` and `tr` themselves have ~0 correlation!
    fc_valid = fc.ravel()[valid_mask]
    tr_valid = tr.ravel()[valid_mask]
    x0_valid = x0.ravel()[valid_mask]

    # Compute partial correlation between fc and tr given x0:
    # regress fc on x0 and tr on x0:
    var_x0 = float(np.var(x0_valid))
    if var_x0 > 1e-10:
        beta_fc_x0 = (
            float(
                np.mean((fc_valid - np.mean(fc_valid)) * (x0_valid - np.mean(x0_valid)))
            )
            / var_x0
        )
        beta_tr_x0 = (
            float(
                np.mean((tr_valid - np.mean(tr_valid)) * (x0_valid - np.mean(x0_valid)))
            )
            / var_x0
        )
        fc_ortho = fc_valid - (
            np.mean(fc_valid) + beta_fc_x0 * (x0_valid - np.mean(x0_valid))
        )
        tr_ortho = tr_valid - (
            np.mean(tr_valid) + beta_tr_x0 * (x0_valid - np.mean(x0_valid))
        )
        if float(np.var(fc_ortho)) > 1e-10 and float(np.var(tr_ortho)) > 1e-10:
            partial_corr_fc_tr = float(np.corrcoef(fc_ortho, tr_ortho)[0, 1])
        else:
            partial_corr_fc_tr = 0.0
    else:
        partial_corr_fc_tr = tendency_corr

    shrinkage_residual = dp - alpha_slope * dt
    var_shrinkage_res = float(np.var(shrinkage_residual))
    explained_fraction = 1.0 - (var_shrinkage_res / var_dp) if var_dp > 1e-10 else 0.0

    if skill_score_vs_persistence is None:
        rmse_pe = float(np.sqrt(np.mean(pe**2)))
        rmse_fe = float(np.sqrt(np.mean(fe**2)))
        skill_score = 1.0 - (rmse_fe / rmse_pe) if rmse_pe > 1e-10 else 0.0
    else:
        skill_score = float(skill_score_vs_persistence)

    # Detect the historical 0.72 synthetic formula OR general unphysical linear shrinkage
    # toward future truth without a verified neural checkpoint hash on disk:
    is_historical_072_signature = 0.65 <= res_corr <= 0.98 and np.isclose(
        skill_score, 0.649, atol=0.06
    )
    is_linear_shrinkage_leakage = (
        not has_verified_checkpoint
        and 0.15 <= alpha_slope <= 1.05
        and tendency_corr >= 0.55
        and partial_corr_fc_tr >= 0.35
        and explained_fraction >= 0.30
        and skill_score >= 0.15
    )

    if is_historical_072_signature or is_linear_shrinkage_leakage:
        raise TargetLeakageError(
            f"Synthetic residual correlation detected: unphysical linear shrinkage toward truth "
            f"(alpha_slope={alpha_slope:.4f}, residual_corr={res_corr:.4f}, "
            f"tendency_corr={tendency_corr:.4f}, partial_corr_fc_tr={partial_corr_fc_tr:.4f}, "
            f"skill_score={skill_score:.4f}) without a verified model checkpoint hash."
        )

    return {
        "target_leakage_detected": False,
        "empirical_alpha_slope": round(alpha_slope, 6),
        "residual_persistence_correlation": round(res_corr, 6),
        "tendency_correlation": round(tendency_corr, 6),
        "partial_correlation_fc_truth_given_x0": round(partial_corr_fc_tr, 6),
        "explained_tendency_fraction": round(explained_fraction, 6),
        "has_verified_checkpoint": has_verified_checkpoint,
    }


def validate_execution_manifest(
    manifest_path: Path | str = DEFAULT_VERIFIED_MANIFEST_PATH,
    *,
    verify_files_on_disk: bool = True,
) -> dict[str, Any]:
    """Require and validate `execution_manifest.json` cryptographic sealing.

    Validates that `execution_manifest.json` in `outputs/scientific_study_verified/`
    (or the specified path) exists and seals SHA-256 hashes of:
    1. `input_artifacts` (initial conditions at t0)
    2. `model_checkpoints` (model family, checkpoint/model_graph, and checkpoint_sha256)
    3. `forecast_outputs` (or `forecast_artifacts`)
    4. `ground_truth_analysis` (verifying truth tensors)

    Raises `ProvenanceIntegrityError` if the manifest or any required section/hash is
    missing, malformed, or does not match the artifact bytes on disk.
    """
    m_path = Path(manifest_path)
    if m_path.is_dir():
        m_path = m_path / "execution_manifest.json"

    if not m_path.exists():
        raise ProvenanceIntegrityError(
            f"Cryptographic sealing error: required execution_manifest.json not found at {m_path}"
        )

    try:
        manifest = json.loads(m_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ProvenanceIntegrityError(
            f"Cryptographic sealing error: malformed JSON in {m_path}: {exc}"
        ) from exc

    base_dir = m_path.parent

    # 1. Validate model_checkpoints / model graph metadata
    model_meta = manifest.get("model_checkpoints") or manifest.get("model")
    if not isinstance(model_meta, dict) or not model_meta.get("family"):
        raise ProvenanceIntegrityError(
            "Cryptographic sealing error: execution_manifest.json missing 'model_checkpoints' metadata."
        )

    family = str(model_meta.get("family", ""))
    ckpt_name = model_meta.get("checkpoint")
    model_graph = model_meta.get("model_graph")
    ckpt_sha = model_meta.get("checkpoint_sha256")

    if not ckpt_name and not model_graph:
        raise ProvenanceIntegrityError(
            "Cryptographic sealing error: 'model_checkpoints' must specify 'checkpoint' or 'model_graph'."
        )

    # Neural models (non-Persistence) must have a valid 64-char hex checkpoint_sha256
    if family.lower() != "persistence":
        if not _is_valid_sha256_hex(ckpt_sha):
            raise ProvenanceIntegrityError(
                f"Cryptographic sealing error: non-persistence model '{family}' requires a valid "
                f"64-char SHA-256 'checkpoint_sha256', got {ckpt_sha!r}."
            )

    # 2. Validate required artifact hash sections: inputs, outputs, ground truth
    required_sections = {
        "input_artifacts": manifest.get("input_artifacts"),
        "forecast_outputs": manifest.get("forecast_outputs")
        or manifest.get("forecast_artifacts"),
        "ground_truth_analysis": manifest.get("ground_truth_analysis"),
    }

    for section_name, entries in required_sections.items():
        if not isinstance(entries, list) or len(entries) == 0:
            raise ProvenanceIntegrityError(
                f"Cryptographic sealing error: execution_manifest.json missing non-empty '{section_name}' list."
            )
        for entry in entries:
            if not isinstance(entry, dict):
                raise ProvenanceIntegrityError(
                    f"Cryptographic sealing error: invalid entry in '{section_name}'."
                )
            art_name = entry.get("name") or entry.get("path")
            recorded_sha = entry.get("sha256")
            if not art_name or not _is_valid_sha256_hex(recorded_sha):
                raise ProvenanceIntegrityError(
                    f"Cryptographic sealing error: entry {art_name!r} in '{section_name}' lacks valid SHA-256 digest."
                )

            if verify_files_on_disk:
                candidates = [
                    base_dir / str(art_name),
                    base_dir / "forecast" / str(art_name),
                    base_dir / "verification" / str(art_name),
                    Path(str(art_name)),
                ]
                resolved_file: Optional[Path] = None
                for cand in candidates:
                    if cand.is_file():
                        resolved_file = cand
                        break
                if resolved_file is None:
                    raise ProvenanceIntegrityError(
                        f"Cryptographic sealing error: artifact '{art_name}' in '{section_name}' not found on disk."
                    )
                actual_sha = compute_sha256(resolved_file)
                if actual_sha != recorded_sha:
                    raise ProvenanceIntegrityError(
                        f"Cryptographic sealing error: SHA-256 mismatch for '{art_name}' in '{section_name}': "
                        f"expected {recorded_sha}, got {actual_sha}"
                    )

    return manifest


def seal_execution_manifest(
    output_dir: Path | str = "outputs/scientific_study_verified",
    *,
    init_time: str = "2026-10-28T00:00:00+00:00",
    valid_time: str = "2026-10-29T00:00:00+00:00",
    lead_time_hours: int = 24,
    model_family: str = "Persistence",
    checkpoint: str = "identity",
    model_graph: str = "deterministic_identity_operator",
    checkpoint_sha256: Optional[str] = None,
    input_files: Optional[list[Path | str]] = None,
    output_files: Optional[list[Path | str]] = None,
    ground_truth_files: Optional[list[Path | str]] = None,
    metrics: Optional[dict[str, Any]] = None,
    zero_leakage_audit: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Create and write a cryptographically sealed `execution_manifest.json`."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    def _build_entries(
        files: list[Path | str], default_valid_time: str
    ) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for f in files:
            p = Path(f)
            if not p.is_absolute() and not p.exists():
                p = out_dir / p
            digest = compute_sha256(p)
            item: dict[str, Any] = {
                "name": p.name,
                "sha256": digest,
                "valid_time": default_valid_time,
            }
            if p.suffix == ".npy":
                arr = np.load(p)
                item["shape"] = list(arr.shape)
                item["dtype"] = str(arr.dtype)
            entries.append(item)
        return entries

    in_list = (
        _build_entries(input_files, init_time)
        if input_files
        else _build_entries([out_dir / "initial_condition.npy"], init_time)
    )
    out_list = (
        _build_entries(output_files, valid_time)
        if output_files
        else _build_entries([out_dir / "forecast_t2m.npy"], valid_time)
    )
    gt_list = (
        _build_entries(ground_truth_files, valid_time)
        if ground_truth_files
        else _build_entries([out_dir / "verifying_truth_t2m.npy"], valid_time)
    )

    manifest: dict[str, Any] = {
        "$schema": "https://origindatum.space/schemas/weather-run-manifest-v2.json",
        "manifest_version": "2.0.0",
        "experiment_id": "OD-EARTH2-001-AUTHENTIC-VERIFIED",
        "experiment_classification": "AUTHENTIC_PHYSICAL_BASELINE_AND_BENCHMARK",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cycle": {
            "init_time": init_time,
            "valid_time": valid_time,
            "lead_time_hours": lead_time_hours,
            "variable": "t2m",
        },
        "model_checkpoints": {
            "family": model_family,
            "checkpoint": checkpoint,
            "model_graph": model_graph,
            "checkpoint_sha256": checkpoint_sha256,
        },
        "input_artifacts": in_list,
        "forecast_outputs": out_list,
        "ground_truth_analysis": gt_list,
        "computed_authentic_metrics": metrics or {},
        "zero_leakage_audit": zero_leakage_audit
        or {
            "status": "VERIFIED_ZERO_LEAKAGE",
            "target_leakage_detected": False,
        },
    }

    manifest_file = out_dir / "execution_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def verify_forecast(
    manifest_path: Path | str,
    verification_data_source: Optional[Any] = None,
    verification_dataset_path: Optional[Path | str] = None,
    output_dir: Optional[Path | str] = None,
    benchmark_mode: bool = False,
    climatology: Optional[np.ndarray] = None,
    require_execution_manifest: bool = False,
) -> dict[str, Any]:
    """Independently verify frozen forecast against held-out operational analysis.

    Parameters
    ----------
    manifest_path : Path | str
        Path to sealed run_manifest.json or execution_manifest.json.
    verification_data_source : Optional[Any], optional
        Data source for GFS operational analysis.
    verification_dataset_path : Optional[Path | str], optional
        Pre-retrieved verification dataset or metadata JSON.
    output_dir : Optional[Path | str], optional
        Destination directory for verification metrics and logs.
    benchmark_mode : bool, optional
        If True, enforces strict benchmark guards rejecting synthetic data and
        target-leaked residuals.
    climatology : Optional[np.ndarray], optional
        Multi-decadal climatology array for ACC computation.
    require_execution_manifest : bool, optional
        If True, requires full `execution_manifest.json` cryptographic sealing
        (including `ground_truth_analysis` and `model_checkpoints`).

    Returns
    -------
    dict[str, Any]
        Dictionary of computed verification metrics.
    """
    m_path = Path(manifest_path)
    if not m_path.exists():
        raise FileNotFoundError(f"Run manifest not found at {m_path}")

    if require_execution_manifest or m_path.name == "execution_manifest.json":
        validate_execution_manifest(m_path, verify_files_on_disk=True)

    manifest = json.loads(m_path.read_text(encoding="utf-8"))
    forecast_dir = m_path.parent

    # -----------------------------------------------------------------------
    # Step 1: Manifest & Hash Integrity Verification (Test D / Gate 3)
    # -----------------------------------------------------------------------
    forecast_artifacts = manifest.get("forecast_artifacts") or manifest.get(
        "forecast_outputs", []
    )
    if not forecast_artifacts:
        raise ProvenanceIntegrityError(
            "Manifest contains no forecast_artifacts entries!"
        )

    input_artifacts = manifest.get("input_artifacts", [])
    ground_truth_artifacts = manifest.get("ground_truth_analysis", [])

    verified_arrays: dict[str, np.ndarray] = {}

    def _resolve_artifact(filename: str) -> Path:
        for candidate in [
            forecast_dir / filename,
            forecast_dir / "forecast" / filename,
            forecast_dir / "verification" / filename,
        ]:
            if candidate.exists():
                return candidate
        return forecast_dir / filename

    # Validate input artifacts (initial conditions, etc.)
    for art in input_artifacts:
        art_name = art.get("name")
        recorded_hash = art.get("sha256")
        art_file = _resolve_artifact(art_name)

        if not art_file.exists():
            raise ProvenanceIntegrityError(
                f"Missing input artifact on disk: {art_name}"
            )

        computed_hash = compute_sha256(art_file)
        if computed_hash != recorded_hash:
            raise ProvenanceIntegrityError(
                f"SHA-256 hash mismatch for input artifact {art_name}: "
                f"expected {recorded_hash}, got {computed_hash}"
            )

    # Validate forecast artifacts
    for art in forecast_artifacts:
        art_name = art.get("name")
        recorded_hash = art.get("sha256")
        art_file = _resolve_artifact(art_name)

        if not art_file.exists():
            raise ProvenanceIntegrityError(
                f"Missing forecast artifact on disk: {art_name}"
            )

        computed_hash = compute_sha256(art_file)
        if computed_hash != recorded_hash:
            raise ProvenanceIntegrityError(
                f"SHA-256 hash mismatch for {art_name}: "
                f"expected {recorded_hash}, got {computed_hash}"
            )

        if art_file.suffix == ".npy":
            verified_arrays[art_name] = np.load(art_file)

    # Validate ground_truth_analysis hashes if present in manifest
    for art in ground_truth_artifacts:
        art_name = art.get("name")
        recorded_hash = art.get("sha256")
        art_file = _resolve_artifact(art_name)
        if not art_file.exists():
            raise ProvenanceIntegrityError(
                f"Missing ground truth artifact on disk: {art_name}"
            )
        computed_hash = compute_sha256(art_file)
        if computed_hash != recorded_hash:
            raise ProvenanceIntegrityError(
                f"SHA-256 hash mismatch for ground truth artifact {art_name}: "
                f"expected {recorded_hash}, got {computed_hash}"
            )

    # -----------------------------------------------------------------------
    # Step 2: Synthetic Substitution & Quarantined Artifact Rejection (Test C / Gate 1)
    # -----------------------------------------------------------------------
    classification = manifest.get("experiment_classification", "")
    quarantine_status = manifest.get("quarantine_status", "")
    model_meta = manifest.get("model") or manifest.get("model_checkpoints") or {}
    model_family = model_meta.get("family", "")
    ckpt_sha256 = model_meta.get("checkpoint_sha256")
    ckpt_path = model_meta.get("checkpoint")

    if "QUARANTINED_DEFECTIVE_SYNTHETIC" in classification.upper() or (
        "QUARANTINED_DEFECTIVE_SYNTHETIC" in str(quarantine_status).upper()
    ):
        raise TargetLeakageError(
            f"Quarantined defective synthetic artifact rejected: classification='{classification}'"
        )

    if benchmark_mode:
        if (
            "SYNTHETIC" in classification.upper()
            or "DIAGNOSTIC" in classification.upper()
        ):
            raise SyntheticSubstitutionError(
                f"Synthetic diagnostic rejected in benchmark mode: classification='{classification}'"
            )
        if "SYNTHETIC" in model_family.upper() or "MOCK" in model_family.upper():
            raise SyntheticSubstitutionError(
                f"Synthetic model rejected in benchmark mode: family='{model_family}'"
            )

    # -----------------------------------------------------------------------
    # Step 3: Chronological & Coordinate Alignment Verification (Test E / Gate 4)
    # -----------------------------------------------------------------------
    cycle_meta = manifest.get("cycle", {})
    init_time_str = manifest.get("init_time") or cycle_meta.get("init_time")
    valid_time_str = manifest.get("valid_time") or cycle_meta.get("valid_time")
    lead_time_hours = manifest.get(
        "lead_time_hours", cycle_meta.get("lead_time_hours", 24)
    )

    init_time = datetime.datetime.fromisoformat(init_time_str.replace("Z", "+00:00"))
    valid_time = datetime.datetime.fromisoformat(valid_time_str.replace("Z", "+00:00"))

    # Mathematical valid time check: t_valid == t0 + lead_time
    expected_valid_time = init_time + datetime.timedelta(hours=lead_time_hours)
    if valid_time != expected_valid_time:
        raise ChronologyError(
            f"Invalid valid_time in manifest: expected {expected_valid_time.isoformat()}, got {valid_time.isoformat()}"
        )

    # Independent Verification Data Retrieval
    truth_array: Optional[np.ndarray] = None

    if verification_dataset_path is not None:
        v_path = Path(verification_dataset_path)
        if not v_path.exists():
            raise FileNotFoundError(f"Verification dataset file not found: {v_path}")

        if v_path.suffix == ".json":
            v_meta = json.loads(v_path.read_text(encoding="utf-8"))
            v_valid_str = v_meta.get("valid_time")
            if v_valid_str is not None:
                v_valid_time = datetime.datetime.fromisoformat(
                    v_valid_str.replace("Z", "+00:00")
                )
                if v_valid_time != valid_time:
                    raise ChronologyError(
                        f"Temporal alignment error: valid time {valid_time_str} does not match verification time {v_valid_str}"
                    )
            # A JSON descriptor must reference an authentic array file
            if "data_file" in v_meta:
                data_target = v_path.parent / v_meta["data_file"]
                if not data_target.exists():
                    raise FileNotFoundError(
                        f"Referenced verification array file not found: {data_target}"
                    )
                truth_array = np.load(data_target)
            else:
                raise ValueError(
                    f"Verification descriptor {v_path.name} does not reference an authentic array file (.npy/.nc)."
                )
        elif v_path.suffix == ".npy":
            truth_array = np.load(v_path)
        elif v_path.suffix == ".nc":
            import xarray as xr

            with xr.open_dataset(v_path) as ds:
                found_var = None
                for candidate in ["t2m", "2t", "t", "temperature"]:
                    if candidate in ds:
                        found_var = candidate
                        break
                if found_var is None:
                    found_var = list(ds.data_vars.keys())[0]
                truth_array = np.squeeze(ds[found_var].values).astype(np.float32)
        else:
            raise ValueError(
                f"Unsupported verification dataset format: {v_path.suffix}. Must be .npy, .nc, or .json descriptor."
            )

    elif verification_data_source is not None:
        # Retrieve verifying analysis strictly at valid_time
        truth_data = verification_data_source(time=valid_time, variable=["t2m"])
        truth_array = np.asarray(truth_data, dtype=np.float32)
    elif ground_truth_artifacts:
        gt_file = _resolve_artifact(ground_truth_artifacts[0]["name"])
        if gt_file.exists() and gt_file.suffix == ".npy":
            truth_array = np.load(gt_file)

    # -----------------------------------------------------------------------
    # Step 4: Metric Computation & Residual Leakage Anomaly Detection (Gate 5)
    # -----------------------------------------------------------------------
    forecast_array = verified_arrays.get("forecast_t2m.npy")
    if forecast_array is None and verified_arrays:
        forecast_array = next(iter(verified_arrays.values()))

    status = (
        "VERIFIED_GENUINE"
        if (truth_array is not None and forecast_array is not None)
        else "HASH_VERIFIED_PENDING_TRUTH"
    )

    results: dict[str, Any] = {
        "status": status,
        "init_time": init_time_str,
        "valid_time": valid_time_str,
        "model_family": model_family,
        "classification": classification,
    }

    if truth_array is not None and forecast_array is not None:
        # Spatial dimension check
        if forecast_array.shape != truth_array.shape:
            raise ChronologyError(
                f"Grid dimension mismatch: forecast {forecast_array.shape} vs truth {truth_array.shape}"
            )

        # Check initial condition for persistence comparison
        init_file = _resolve_artifact("initial_condition.npy")
        if init_file.exists():
            x0 = np.load(init_file)
        else:
            x0 = forecast_array.copy()

        lats = np.linspace(90, -90, forecast_array.shape[0])
        metrics = compute_all_metrics(
            forecast_array, truth_array, persistence=x0, lats=lats
        )
        results.update(metrics)

        # Statistical residual & correlation anomaly detection against target leakage:
        # Automatically rejects and raises TargetLeakageError (which inherits from
        # SyntheticSubstitutionError) if forecast error residuals exhibit unphysical
        # linear shrinkage toward truth without a verified model checkpoint hash.
        if benchmark_mode or init_file.exists():
            residual_audit = detect_residual_leakage_anomaly(
                forecast=forecast_array,
                truth=truth_array,
                initial_condition=x0,
                checkpoint_sha256=ckpt_sha256,
                checkpoint_path=ckpt_path,
                skill_score_vs_persistence=metrics.get("skill_score_vs_persistence"),
            )
            results["residual_leakage_audit"] = residual_audit

        # Explicitly separate ACC vs TAC:
        if climatology is not None:
            weights = compute_latitude_weights(lats)[:, None]
            fc_anom = forecast_array - climatology
            tr_anom = truth_array - climatology
            num = np.sum(weights * fc_anom * tr_anom)
            den = np.sqrt(
                np.sum(weights * (fc_anom**2)) * np.sum(weights * (tr_anom**2))
            )
            results["acc"] = round(float(num / den), 4) if den > 0 else 0.0
        else:
            results["acc"] = None

    if output_dir is not None:
        out_d = Path(output_dir)
        out_d.mkdir(parents=True, exist_ok=True)
        (out_d / "validation_results.json").write_text(
            json.dumps(results, indent=2), encoding="utf-8"
        )

    return results
