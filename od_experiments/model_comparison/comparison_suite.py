# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Multi-model prognostic benchmark suite.
Fair, zero-leakage evaluation of Persistence, Neural Benchmarks, and Diagnostic baselines.
OD-EARTH2-001 / EO-OBSCURA research initiative.
"""

from typing import Any
import numpy as np
from od_experiments.scientific_study.metrics_engine import (
    compute_latitude_weights,
    weighted_rmse,
    weighted_mae,
    mean_bias,
    tendency_anomaly_correlation,
)


def benchmark_model_suite(
    init_state: np.ndarray,
    verifying_truth: np.ndarray,
    lats: np.ndarray,
    candidate_forecasts: dict[str, np.ndarray],
) -> dict[str, dict[str, float]]:
    """
    Evaluate multiple model forecasts against an independent verifying operational analysis.
    
    Parameters
    ----------
    init_state : np.ndarray
        Atmospheric state at t=0 (persistence baseline).
    verifying_truth : np.ndarray
        Held-out operational analysis at valid forecast time t=valid.
    lats : np.ndarray
        1D latitude coordinates for area-weighting.
    candidate_forecasts : dict of {model_name: forecast_array}
        Predicted fields from independent prognostic models.
        
    Returns
    -------
    dict
        Comparative metrics (RMSE, MAE, TAC, Relative Skill vs Persistence).
    """
    weights = compute_latitude_weights(lats)
    pers_rmse = weighted_rmse(init_state, verifying_truth, weights)
    
    results = {}
    for model_name, fcast in candidate_forecasts.items():
        # Verify shape
        if fcast.shape != verifying_truth.shape:
            raise ValueError(f"Shape mismatch: {fcast.shape} vs {verifying_truth.shape}")
            
        rmse = weighted_rmse(fcast, verifying_truth, weights)
        mae = weighted_mae(fcast, verifying_truth, weights)
        bias = mean_bias(fcast, verifying_truth)
        
        # Tendency Anomaly Correlation (strictly initialization-referenced per e2s-014)
        tac = tendency_anomaly_correlation(fcast, verifying_truth, init_state, weights)
        
        # Skill relative to persistence: 1 - RMSE_model / RMSE_persistence
        rel_skill = 1.0 - (rmse / pers_rmse) if pers_rmse > 0 else 0.0
        
        results[model_name] = {
            "rmse": round(rmse, 4),
            "mae": round(mae, 4),
            "bias": round(bias, 4),
            "tac": round(tac, 4),
            "skill_vs_persistence_pct": round(rel_skill * 100.0, 2),
        }
        
    return results
