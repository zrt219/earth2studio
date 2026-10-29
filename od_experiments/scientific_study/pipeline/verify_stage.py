# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Stage C: Genuine Verify Stage (Independent Verification & Anti-Leakage Guards).

Verifies frozen forecast artifacts against authentic GFS operational analyses.
Recalculates and enforces cryptographic SHA-256 integrity before reading data,
rejects synthetic substitutions, verifies chronological and coordinate alignment,
and calculates latitude-weighted verification metrics.
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
)
from od_experiments.scientific_study.metrics_engine import (
    compute_all_metrics,
    compute_latitude_weights,
)


def compute_sha256(file_path: Path | str) -> str:
    """Compute SHA-256 digest of a file using buffered reading."""
    p = Path(file_path)
    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_forecast(
    manifest_path: Path | str,
    verification_data_source: Optional[Any] = None,
    verification_dataset_path: Optional[Path | str] = None,
    output_dir: Optional[Path | str] = None,
    benchmark_mode: bool = False,
    climatology: Optional[np.ndarray] = None,
) -> dict[str, Any]:
    """Independently verify frozen forecast against held-out operational analysis.

    Parameters
    ----------
    manifest_path : Path | str
        Path to sealed run_manifest.json from Stage B.
    verification_data_source : Optional[Any], optional
        Data source for GFS operational analysis.
    verification_dataset_path : Optional[Path | str], optional
        Pre-retrieved verification dataset or metadata JSON.
    output_dir : Optional[Path | str], optional
        Destination directory for verification metrics and logs.
    benchmark_mode : bool, optional
        If True, enforces strict benchmark guards rejecting synthetic data.
    climatology : Optional[np.ndarray], optional
        Multi-decadal climatology array for ACC computation.

    Returns
    -------
    dict[str, Any]
        Dictionary of computed verification metrics.
    """
    m_path = Path(manifest_path)
    if not m_path.exists():
        raise FileNotFoundError(f"Run manifest not found at {m_path}")

    manifest = json.loads(m_path.read_text(encoding="utf-8"))
    forecast_dir = m_path.parent

    # -----------------------------------------------------------------------
    # Step 1: Manifest & Hash Integrity Verification (Test D / Gate 3)
    # -----------------------------------------------------------------------
    forecast_artifacts = manifest.get("forecast_artifacts", [])
    if not forecast_artifacts:
        raise ProvenanceIntegrityError("Manifest contains no forecast_artifacts entries!")

    input_artifacts = manifest.get("input_artifacts", [])

    verified_arrays: dict[str, np.ndarray] = {}

    def _resolve_artifact(filename: str) -> Path:
        for candidate in [forecast_dir / filename, forecast_dir / "forecast" / filename]:
            if candidate.exists():
                return candidate
        return forecast_dir / filename

    # Validate input artifacts (initial conditions, etc.)
    for art in input_artifacts:
        art_name = art.get("name")
        recorded_hash = art.get("sha256")
        art_file = _resolve_artifact(art_name)

        if not art_file.exists():
            raise ProvenanceIntegrityError(f"Missing input artifact on disk: {art_name}")

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
            raise ProvenanceIntegrityError(f"Missing forecast artifact on disk: {art_name}")

        computed_hash = compute_sha256(art_file)
        if computed_hash != recorded_hash:
            raise ProvenanceIntegrityError(
                f"SHA-256 hash mismatch for {art_name}: "
                f"expected {recorded_hash}, got {computed_hash}"
            )

        if art_file.suffix == ".npy":
            verified_arrays[art_name] = np.load(art_file)

    # -----------------------------------------------------------------------
    # Step 2: Synthetic Substitution Rejection (Test C / Gate 1)
    # -----------------------------------------------------------------------
    classification = manifest.get("experiment_classification", "")
    model_family = manifest.get("model", {}).get("family", "")

    if benchmark_mode:
        if "SYNTHETIC" in classification.upper() or "DIAGNOSTIC" in classification.upper():
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
    init_time_str = manifest.get("init_time")
    valid_time_str = manifest.get("valid_time")
    lead_time_hours = manifest.get("lead_time_hours", 24)

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
                    raise FileNotFoundError(f"Referenced verification array file not found: {data_target}")
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

    # -----------------------------------------------------------------------
    # Step 4: Metric Computation (Gate 5)
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
        metrics = compute_all_metrics(forecast_array, truth_array, persistence=x0, lats=lats)
        results.update(metrics)

        # Statistical residual check against synthetic formula
        if benchmark_mode:
            pers_err = x0 - truth_array
            fc_err = forecast_array - truth_array
            var_pers = float(np.var(pers_err))
            var_fc = float(np.var(fc_err))
            if var_pers > 1e-6 and var_fc > 1e-6:
                corr = float(np.corrcoef(pers_err.flatten(), fc_err.flatten())[0, 1])
                # In the historical formula: fc_err = 0.28 * pers_err + noise, corr is ~0.7-0.9
                # and residual has high correlation with pers_err
                if 0.70 <= corr <= 0.95 and np.isclose(metrics["skill_score_vs_persistence"], 0.649, atol=0.05):
                    raise SyntheticSubstitutionError("Synthetic residual correlation detected")

        # Explicitly separate ACC vs TAC:
        if climatology is not None:
            weights = compute_latitude_weights(lats)[:, None]
            fc_anom = forecast_array - climatology
            tr_anom = truth_array - climatology
            num = np.sum(weights * fc_anom * tr_anom)
            den = np.sqrt(np.sum(weights * (fc_anom**2)) * np.sum(weights * (tr_anom**2)))
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
