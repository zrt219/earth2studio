# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
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

"""
Forecast and Ensemble Validation Engine.
OD-EARTH2-001 / EO-OBSCURA research initiative.
Attribution: Zhane Daye, Origin Datum (https://origindatum.space, contact@origindatum.space)
Strict adherence to .agents/rules/e2s-014-scientific-integrity.mdc.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from od_experiments.scientific_study.metrics_engine import (
    crps_ensemble,
    extreme_dependency_index,
    spread_skill_ratio,
    symmetric_extremal_dependence_index,
    tendency_anomaly_correlation,
)


def compute_metrics(
    forecast: np.ndarray,
    reference: np.ndarray,
    lats: np.ndarray | None = None,
    threshold: float | None = None,
    persistence: np.ndarray | None = None,
) -> dict[str, Any]:
    """
    Computes latitude-weighted verification metrics between forecast and reference fields.
    Supports both 2D/3D deterministic fields and 3D/4D multi-member ensemble fields.
    Validates array shapes, handles NaNs gracefully, and normalizes cosine latitude weights correctly.
    """
    forecast_arr = np.asarray(forecast, dtype=np.float64)
    reference_arr = np.asarray(reference, dtype=np.float64)

    is_ensemble = forecast_arr.ndim == reference_arr.ndim + 1

    if not is_ensemble and forecast_arr.shape != reference_arr.shape:
        raise ValueError(
            f"Shape mismatch: forecast shape {forecast_arr.shape} does not match reference shape {reference_arr.shape}"
        )

    if is_ensemble:
        target_forecast = np.mean(forecast_arr, axis=0)
    else:
        target_forecast = forecast_arr

    diff = target_forecast - reference_arr

    # Mask valid (non-NaN, non-Inf) values
    valid_mask = np.isfinite(diff)
    if not np.any(valid_mask):
        return {"mae": float("nan"), "rmse": float("nan"), "mean_bias": float("nan")}

    if lats is not None:
        lats_arr = np.asarray(lats, dtype=np.float64)
        weights_1d = np.cos(np.deg2rad(lats_arr))
        weights_1d = np.clip(weights_1d, 0.0, None)

        lat_dim_idx = None
        for idx, dim_len in enumerate(diff.shape):
            if dim_len == len(lats_arr):
                lat_dim_idx = idx
                break

        if lat_dim_idx is not None:
            shape = [1] * diff.ndim
            shape[lat_dim_idx] = len(lats_arr)
            weights = np.reshape(weights_1d, shape)
            weights = np.broadcast_to(weights, diff.shape)
        else:
            weights = np.ones_like(diff)

        weights = np.where(valid_mask, weights, 0.0)
        total_weight = np.sum(weights)

        if total_weight > 0:
            mae = float(np.sum(np.abs(diff) * weights) / total_weight)
            rmse = float(np.sqrt(np.sum((diff**2) * weights) / total_weight))
            bias = float(np.sum(diff * weights) / total_weight)
        else:
            mae = float(np.mean(np.abs(diff[valid_mask])))
            rmse = float(np.sqrt(np.mean(diff[valid_mask] ** 2)))
            bias = float(np.mean(diff[valid_mask]))
    else:
        valid_diff = diff[valid_mask]
        mae = float(np.mean(np.abs(valid_diff)))
        rmse = float(np.sqrt(np.mean(valid_diff**2)))
        bias = float(np.mean(valid_diff))

    metrics: dict[str, Any] = {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "mean_bias": round(bias, 4),
    }

    # TAC if persistence baseline is provided
    if persistence is not None:
        pers_arr = np.asarray(persistence, dtype=np.float64)
        tac = tendency_anomaly_correlation(
            target_forecast, reference_arr, pers_arr, lats=lats
        )
        metrics["tac"] = round(tac, 4)

    # Probabilistic metrics if ensemble
    if is_ensemble:
        M = forecast_arr.shape[0]
        crps_std = crps_ensemble(forecast_arr, reference_arr, lats=lats, fair=False)
        crps_fair_val = (
            crps_ensemble(forecast_arr, reference_arr, lats=lats, fair=True)
            if M >= 2
            else crps_std
        )
        ssr_dict = spread_skill_ratio(forecast_arr, reference_arr, lats=lats)

        metrics["crps"] = round(crps_std, 4)
        metrics["crps_fair"] = round(crps_fair_val, 4)
        metrics["ensemble_spread"] = round(ssr_dict["spread"], 4)
        metrics["ssr_raw"] = round(ssr_dict["ssr_raw"], 4)
        metrics["ssr_corrected"] = round(ssr_dict["ssr_corrected"], 4)
        metrics["calibration_status"] = ssr_dict["calibration_status"]

    # Extreme threshold metrics if threshold is specified
    if threshold is not None:
        edi_res = extreme_dependency_index(
            target_forecast, reference_arr, threshold=threshold, lats=lats
        )
        sedi_res = symmetric_extremal_dependence_index(
            target_forecast, reference_arr, threshold=threshold, lats=lats
        )
        metrics["threshold"] = threshold
        metrics["edi"] = round(edi_res["edi"], 4)
        metrics["sedi"] = round(sedi_res["sedi"], 4)
        metrics["hit_rate"] = round(edi_res["hit_rate"], 4)
        metrics["false_alarm_rate"] = round(edi_res["false_alarm_rate"], 4)
        metrics["base_rate"] = round(edi_res["base_rate"], 6)

    return metrics


def evaluate_forecast(
    forecast_data: dict[str, np.ndarray],
    reference_data: dict[str, np.ndarray] | None = None,
    persistence_data: dict[str, np.ndarray] | None = None,
    lats: np.ndarray | None = None,
    thresholds: dict[str, float] | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """
    Validates forecast against reference truth observations.
    If reference_data is None or empty, strictly reports NOT_VALIDATED without inventing data.
    """
    if not reference_data:
        results = {
            "validation_status": "NOT_VALIDATED",
            "reason": "No reference verification data was provided for the target verification time.",
            "metrics": {},
            "evaluation_metadata": {
                "lat_weighted": lats is not None,
                "variables": list(forecast_data.keys()),
            },
        }
    else:
        results = {
            "validation_status": "VALIDATED",
            "metrics": {},
            "evaluation_metadata": {
                "lat_weighted": lats is not None,
                "variables": [v for v in forecast_data.keys() if v in reference_data],
            },
        }
        for var_name, fcast_arr in forecast_data.items():
            if var_name not in reference_data:
                continue
            ref_arr = reference_data[var_name]
            pers_arr = persistence_data.get(var_name) if persistence_data else None
            theta = thresholds.get(var_name) if thresholds else None

            results["metrics"][var_name] = compute_metrics(
                forecast=fcast_arr,
                reference=ref_arr,
                lats=lats,
                threshold=theta,
                persistence=pers_arr,
            )

    if output_dir:
        out_file = Path(output_dir) / "validation_report.json"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

    return results
