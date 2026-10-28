"""Scientific meteorological metrics engine for Earth-2 evaluation.

Provides:
- Latitude-cosine weighted RMSE
- Anomaly Correlation Coefficient (ACC)
- Mean Bias Error (MBE)
- Skill Score relative to persistence baseline: SS = 1 - (RMSE_model / RMSE_persistence)
"""

from __future__ import annotations

import numpy as np
from typing import Dict, Any, Tuple, Optional


def compute_latitude_weights(lats: np.ndarray) -> np.ndarray:
    """Compute normalized cosine latitude weights.
    
    w_i = cos(lat_i) / mean(cos(lat))
    """
    rad = np.deg2rad(np.asarray(lats, dtype=np.float64))
    cos_lat = np.cos(rad)
    cos_lat = np.clip(cos_lat, 0.0, None)
    mean_cos = np.mean(cos_lat)
    if mean_cos <= 0:
        return np.ones_like(cos_lat)
    return cos_lat / mean_cos


def weighted_rmse(
    forecast: np.ndarray,
    truth: np.ndarray,
    lats: Optional[np.ndarray] = None,
) -> float:
    """Compute latitude-weighted Root Mean Square Error.
    
    If lats is None, defaults to uniform weighting.
    """
    diff = forecast - truth
    sq_err = np.square(diff)
    
    if lats is not None:
        w = compute_latitude_weights(lats)
        # Broadcast weights along latitude axis
        if sq_err.ndim >= 2:
            # Assume latitude is second-to-last axis (-2)
            while w.ndim < sq_err.ndim:
                w = w[:, None] if w.ndim == 1 else w[..., None]
        weighted_sq_err = sq_err * w
        return float(np.sqrt(np.nanmean(weighted_sq_err)))
    return float(np.sqrt(np.nanmean(sq_err)))


def mean_bias(forecast: np.ndarray, truth: np.ndarray) -> float:
    """Compute unweighted or area-averaged mean bias error."""
    return float(np.nanmean(forecast - truth))


def anomaly_correlation_coefficient(
    forecast: np.ndarray,
    truth: np.ndarray,
    climatology: Optional[np.ndarray] = None,
    lats: Optional[np.ndarray] = None,
) -> float:
    """Compute Anomaly Correlation Coefficient (ACC).
    
    ACC = <(f - c) * (t - c)> / sqrt(<(f - c)^2> * <(t - c)^2>)
    If climatology is not provided, spatial mean of truth is used as reference.
    """
    if climatology is None:
        c = np.nanmean(truth)
    else:
        c = climatology

    f_prime = forecast - c
    t_prime = truth - c

    w = 1.0
    if lats is not None:
        w = compute_latitude_weights(lats)
        if f_prime.ndim >= 2:
            while w.ndim < f_prime.ndim:
                w = w[:, None] if w.ndim == 1 else w[..., None]

    num = np.nansum(w * f_prime * t_prime)
    den = np.sqrt(np.nansum(w * np.square(f_prime)) * np.nansum(w * np.square(t_prime)))
    if den == 0:
        return 0.0
    return float(np.clip(num / den, -1.0, 1.0))


def compute_all_metrics(
    forecast: np.ndarray,
    truth: np.ndarray,
    persistence: np.ndarray,
    lats: Optional[np.ndarray] = None,
) -> Dict[str, float]:
    """Calculate comprehensive suite of meteorological verification metrics."""
    rmse_fc = weighted_rmse(forecast, truth, lats=lats)
    rmse_pers = weighted_rmse(persistence, truth, lats=lats)
    mbe = mean_bias(forecast, truth)
    acc = anomaly_correlation_coefficient(forecast, truth, climatology=persistence, lats=lats)
    
    # Forecast skill score over persistence
    if rmse_pers > 0:
        skill_score = 1.0 - (rmse_fc / rmse_pers)
    else:
        skill_score = 0.0

    return {
        "rmse_weighted": round(rmse_fc, 4),
        "rmse_persistence": round(rmse_pers, 4),
        "skill_score_vs_persistence": round(skill_score, 4),
        "mean_bias": round(mbe, 4),
        "acc": round(acc, 4),
    }
