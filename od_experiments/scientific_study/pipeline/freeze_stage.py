# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Stage B: Genuine Freeze Stage (Cryptographic Hashing & Provenance Sealing).

Computes SHA-256 digests for all serialized prediction tensors and initial fields,
validates model identity invariants, captures execution environment metadata,
and seals run_manifest.json before verification retrieval.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import platform
from pathlib import Path
from typing import Any, Optional

import numpy as np

from od_experiments.scientific_study.exceptions import ModelIdentityMismatchError


def compute_sha256(file_path: Path | str) -> str:
    """Compute SHA-256 digest of a file using buffered reading."""
    p = Path(file_path)
    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def freeze_forecast(
    forecast_dir: Path | str,
    output_dir: Optional[Path | str] = None,
    classification: Optional[str] = None,
    git_commit: Optional[str] = None,
    model_family: Optional[str] = None,
    checkpoint: Optional[str] = None,
    checkpoint_sha256: Optional[str] = None,
) -> dict[str, Any]:
    """Freeze forecast stage artifacts and seal run_manifest.json.

    Parameters
    ----------
    forecast_dir : Path | str
        Directory produced by Stage A containing forecast_t2m.npy and forecast_meta.json.
    output_dir : Optional[Path | str], optional
        Destination directory for sealed manifest (defaults to forecast_dir).
    classification : Optional[str], optional
        Experiment classification. Defaults to BASELINE_PERSISTENCE or REAL_MODEL_FORECAST.
    git_commit : Optional[str], optional
        Git commit hash. If None, dynamically resolved via git rev-parse HEAD.
    model_family : Optional[str], optional
        Declared model architecture family.
    checkpoint : Optional[str], optional
        Model checkpoint identifier.
    checkpoint_sha256 : Optional[str], optional
        Digest of model weights.

    Returns
    -------
    dict[str, Any]
        Sealed Schema 2.0.0 manifest dictionary.
    """
    f_dir = Path(forecast_dir)
    out_dir = Path(output_dir) if output_dir is not None else f_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Dynamic git commit resolution if not explicitly specified
    if git_commit is None:
        try:
            from od_experiments.earth2_001.provenance import get_git_info

            git_commit = get_git_info().get("commit_sha", "unknown")
        except Exception:
            try:
                import subprocess

                git_commit = subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
                ).strip()
            except Exception:
                git_commit = "unknown"

    meta_file = f_dir / "forecast_meta.json"
    if meta_file.exists():
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    else:
        meta = {}

    executed_family = meta.get("model_family", "Persistence")
    declared_family = model_family or executed_family
    ckpt = checkpoint or meta.get("checkpoint", "identity")
    ckpt_hash = checkpoint_sha256 or meta.get("checkpoint_sha256", None)

    # Invariant F: Model Identity Validation
    # Under NO circumstances may Persistence be labeled or attributed as FourCastNet or SFNO,
    # and declared model family must strictly equal executed model family.
    if declared_family != executed_family:
        raise ModelIdentityMismatchError(
            f"Model identity mismatch: Persistence cannot be labeled as {declared_family}! "
            f"Executed '{executed_family}' cannot be declared as '{declared_family}'."
        )

    # Neural models require non-null checkpoint_sha256
    if declared_family in ["FourCastNet", "SFNO", "FCN3"] and ckpt_hash is None:
        raise ModelIdentityMismatchError(
            f"Neural model {declared_family} requires non-null checkpoint_sha256 digest!"
        )

    # Classify experiment
    if classification is None:
        if declared_family == "Persistence":
            classification = "BASELINE_PERSISTENCE"
        else:
            classification = "REAL_MODEL_FORECAST"

    # Compute SHA-256 for all forecast and input artifacts
    forecast_artifacts = []
    input_artifacts = []
    hashes_manifest_lines = []

    for file_path in sorted(f_dir.glob("*.npy")):
        digest = compute_sha256(file_path)
        hashes_manifest_lines.append(f"{digest}  {file_path.name}")
        arr = np.load(file_path)
        entry = {
            "name": file_path.name,
            "sha256": digest,
            "shape": list(arr.shape),
            "dtype": str(arr.dtype),
        }
        if "init" in file_path.name:
            input_artifacts.append(entry)
        else:
            entry["units"] = "Kelvin"
            forecast_artifacts.append(entry)

    # Environment capture
    env_info = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
    }

    manifest = {
        "$schema": "https://origindatum.space/schemas/weather-run-manifest-v2.json",
        "manifest_version": "2.0.0",
        "experiment_classification": classification,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "git_commit": git_commit,
        "init_time": meta.get("init_time", "2026-10-25T00:00:00Z"),
        "valid_time": meta.get("valid_time", "2026-10-26T00:00:00Z"),
        "lead_time_hours": meta.get("lead_time_hours", 24),
        "model": {
            "family": declared_family,
            "checkpoint": ckpt,
            "checkpoint_sha256": ckpt_hash,
        },
        "environment": env_info,
        "input_artifacts": input_artifacts,
        "forecast_artifacts": forecast_artifacts,
    }

    manifest_file = out_dir / "run_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    hashes_file = out_dir / "hashes.sha256"
    hashes_file.write_text("\n".join(hashes_manifest_lines) + "\n", encoding="utf-8")

    return manifest
