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

"""Scientific meteorological metrics engine for Earth-2 evaluation.

Author: Zhane Daye, Origin Datum (https://origindatum.space, contact@origindatum.space)
Strict adherence to .agents/rules/e2s-014-scientific-integrity.mdc.

Provides:
- Latitude-cosine weighted RMSE
- Anomaly Correlation Coefficient (ACC) using true climatology or spatial reference
- Tendency Anomaly Correlation (TAC) when persistence is used as reference
- Mean Bias Error (MBE)
- Continuous Ranked Probability Score (CRPS, O(M log M) standard and fair)
- Spread-Skill Ratio (SSR) with finite ensemble size calibration factor sqrt((M+1)/M)
- Area-weighted 2x2 contingency table for extreme thresholds
- Extreme Dependency Index (EDI) & Symmetric Extremal Dependence Index (SEDI)
- Skill Score relative to persistence baseline: SS = 1 - (RMSE_model / RMSE_persistence)
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np


def compute_latitude_weights(lats: np.ndarray) -> np.ndarray:
    """Compute normalized cosine latitude weights.

    w_i = cos(lat_i) / mean(cos(lat))
    Clamped at 0 to avoid negative weights at poles.
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


def weighted_mae(
    forecast: np.ndarray,
    truth: np.ndarray,
    lats: Optional[np.ndarray] = None,
) -> float:
    """Compute latitude-weighted Mean Absolute Error."""
    abs_err = np.abs(forecast - truth)
    if lats is not None:
        w = compute_latitude_weights(lats)
        if abs_err.ndim >= 2:
            while w.ndim < abs_err.ndim:
                w = w[:, None] if w.ndim == 1 else w[..., None]
        weighted_abs_err = abs_err * w
        return float(np.nanmean(weighted_abs_err))
    return float(np.nanmean(abs_err))


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

    Important Qualification:
    In operational NWP (ECMWF, WMO, NOAA), ACC is strictly defined against a multi-decadal
    climatological reference field c = \\bar{C}(day_of_year, hour), typically derived from
    30 years of reanalysis (e.g., ERA5 1979-2018). ECMWF's widely cited 0.60 threshold denotes
    the boundary where synoptic weather patterns retain useful predictive value beyond climatology.

    When climatology is not provided, spatial mean of truth is used as reference.
    Note: If c is persistence (T0), this measures the Tendency Anomaly Correlation (TAC),
    which is the correlation of the forecast change (f - T0) with the observed change (t - T0).
    The operational 0.60 threshold cannot be automatically transferred to TAC without qualification,
    as tendency departures have fundamentally different variance spectra and persistence baselines.
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


def tendency_anomaly_correlation(
    forecast: np.ndarray,
    truth: np.ndarray,
    persistence: np.ndarray,
    lats: Optional[np.ndarray] = None,
) -> float:
    """Compute Tendency Anomaly Correlation (TAC) relative to initial persistence state T0.

    TAC = <(f - T0) * (truth - T0)> / sqrt(<(f - T0)^2> * <(truth - T0)^2>)

    Quantifies correlation between predicted atmospheric tendency and observed tendency.
    Unlike climatological ACC (which references multi-decadal monthly/daily climatology),
    TAC isolates short-term dynamic tendencies. While high TAC values (> 0.90) indicate
    accurate phase tracking of 24h tendency vectors, the operational 0.60 threshold
    defined by ECMWF/WMO for ACC does not directly apply as a validated synoptic cutoff
    for TAC without dedicated empirical calibration.
    """
    return anomaly_correlation_coefficient(
        forecast=forecast,
        truth=truth,
        climatology=persistence,
        lats=lats,
    )


def crps_ensemble(
    forecast: np.ndarray,
    truth: np.ndarray,
    lats: Optional[np.ndarray] = None,
    fair: bool = False,
    ensemble_axis: int = 0,
) -> float:
    """Compute domain-averaged latitude-weighted CRPS in O(M log M) time.

    Parameters
    ----------
    forecast : np.ndarray
        Ensemble prediction tensor with shape (M, lat, lon) or matching ensemble_axis.
    truth : np.ndarray
        Verifying observation matching forecast shape without ensemble_axis.
    lats : np.ndarray, optional
        1D latitude coordinates for area weighting.
    fair : bool
        If True, applies finite-ensemble unbiased correction factor 1 / (2*M*(M-1)).
    ensemble_axis : int
        Dimension corresponding to ensemble members.
    """
    forecast_arr = np.asarray(forecast, dtype=np.float32)
    truth_arr = np.asarray(truth, dtype=np.float32)

    if ensemble_axis != 0:
        forecast_arr = np.moveaxis(forecast_arr, ensemble_axis, 0)

    M = forecast_arr.shape[0]
    if M < 2 and fair:
        raise ValueError("Fair CRPS requires at least M >= 2 ensemble members.")

    # 1. First term: E|X - y|
    term1 = np.mean(np.abs(forecast_arr - truth_arr[None, ...]), axis=0)

    if M == 1:
        crps_grid = term1
    else:
        # 2. Second term: 0.5 * E|X - X'| via sorted order statistics in O(M log M)
        sorted_ens = np.sort(forecast_arr, axis=0)
        indices = np.arange(M, dtype=np.float32)
        weights = 2.0 * indices + 1.0 - float(M)

        shape = [1] * forecast_arr.ndim
        shape[0] = M
        weights = weights.reshape(shape)

        pairwise_sum = 2.0 * np.sum(weights * sorted_ens, axis=0)

        if fair:
            term2 = pairwise_sum / (2.0 * float(M) * float(M - 1))
        else:
            term2 = pairwise_sum / (2.0 * float(M) * float(M))

        crps_grid = term1 - term2

    if lats is not None:
        w = compute_latitude_weights(lats)
        while w.ndim < crps_grid.ndim:
            w = w[:, None] if w.ndim == 1 else w[..., None]
        return float(np.nanmean(crps_grid * w))

    return float(np.nanmean(crps_grid))


def spread_skill_ratio(
    forecast: np.ndarray,
    truth: np.ndarray,
    lats: Optional[np.ndarray] = None,
    ensemble_axis: int = 0,
    correct_finite: bool = True,
) -> Dict[str, float]:
    """Compute domain-averaged latitude-weighted Spread-Skill Ratio (SSR)."""
    forecast_arr = np.asarray(forecast, dtype=np.float32)
    truth_arr = np.asarray(truth, dtype=np.float32)

    if ensemble_axis != 0:
        forecast_arr = np.moveaxis(forecast_arr, ensemble_axis, 0)

    M = forecast_arr.shape[0]
    ens_mean = np.mean(forecast_arr, axis=0)
    ens_var = np.var(forecast_arr, axis=0, ddof=1) if M > 1 else np.zeros_like(ens_mean)

    w = 1.0
    if lats is not None:
        w = compute_latitude_weights(lats)
        while w.ndim < ens_mean.ndim:
            w = w[:, None] if w.ndim == 1 else w[..., None]

    spread = float(np.sqrt(np.nanmean(ens_var * w)))
    skill = float(np.sqrt(np.nanmean(np.square(ens_mean - truth_arr) * w)))

    ssr_raw = spread / skill if skill > 0 else float("nan")
    finite_factor = float(np.sqrt((M + 1.0) / M)) if M > 0 else 1.0
    ssr_corrected = ssr_raw * finite_factor if correct_finite else ssr_raw

    if ssr_corrected < 0.90:
        status = "UNDER-DISPERSIVE"
    elif ssr_corrected > 1.10:
        status = "OVER-DISPERSIVE"
    else:
        status = "WELL-CALIBRATED"

    return {
        "spread": spread,
        "skill_rmse": skill,
        "ssr_raw": ssr_raw,
        "ssr_corrected": ssr_corrected,
        "finite_factor": finite_factor,
        "calibration_status": status,
    }


def contingency_table(
    forecast: np.ndarray,
    truth: np.ndarray,
    threshold: float,
    lats: Optional[np.ndarray] = None,
    is_upper_threshold: bool = True,
) -> Dict[str, float]:
    """Compute area-weighted 2x2 contingency table for extreme events."""
    f = np.asarray(forecast, dtype=np.float32)
    t = np.asarray(truth, dtype=np.float32)

    if is_upper_threshold:
        f_event = f >= threshold
        t_event = t >= threshold
    else:
        f_event = f <= threshold
        t_event = t <= threshold

    w = np.ones_like(f)
    if lats is not None:
        w_1d = compute_latitude_weights(lats)
        while w_1d.ndim < f.ndim:
            w_1d = w_1d[:, None] if w_1d.ndim == 1 else w_1d[..., None]
        w = np.broadcast_to(w_1d, f.shape)

    a = float(np.sum(w * (f_event & t_event)))
    b = float(np.sum(w * (f_event & (~t_event))))
    c = float(np.sum(w * ((~f_event) & t_event)))
    d = float(np.sum(w * ((~f_event) & (~t_event))))

    tot = a + b + c + d
    H = a / (a + c) if (a + c) > 0 else 0.0
    F = b / (b + d) if (b + d) > 0 else 0.0
    p = (a + c) / tot if tot > 0 else 0.0

    return {
        "hits": a,
        "false_alarms": b,
        "misses": c,
        "correct_negatives": d,
        "total_weight": tot,
        "hit_rate": H,
        "false_alarm_rate": F,
        "base_rate": p,
    }


def extreme_dependency_index(
    forecast: np.ndarray,
    truth: np.ndarray,
    threshold: float,
    lats: Optional[np.ndarray] = None,
    epsilon: float = 1e-7,
    is_upper_threshold: bool = True,
) -> Dict[str, float]:
    """Compute Extreme Dependency Index (EDI)."""
    tbl = contingency_table(
        forecast, truth, threshold, lats=lats, is_upper_threshold=is_upper_threshold
    )
    H = np.clip(tbl["hit_rate"], epsilon, 1.0 - epsilon)
    F = np.clip(tbl["false_alarm_rate"], epsilon, 1.0 - epsilon)

    edi = (np.log(F) - np.log(H)) / (np.log(F) + np.log(H))
    tbl["edi"] = float(np.clip(edi, -1.0, 1.0))
    return tbl


def symmetric_extremal_dependence_index(
    forecast: np.ndarray,
    truth: np.ndarray,
    threshold: float,
    lats: Optional[np.ndarray] = None,
    epsilon: float = 1e-7,
    is_upper_threshold: bool = True,
) -> Dict[str, float]:
    """Compute Symmetric Extremal Dependence Index (SEDI)."""
    tbl = contingency_table(
        forecast, truth, threshold, lats=lats, is_upper_threshold=is_upper_threshold
    )
    H = np.clip(tbl["hit_rate"], epsilon, 1.0 - epsilon)
    F = np.clip(tbl["false_alarm_rate"], epsilon, 1.0 - epsilon)

    num = np.log(F) - np.log(H) - np.log(1.0 - F) + np.log(1.0 - H)
    den = np.log(F) + np.log(H) + np.log(1.0 - F) + np.log(1.0 - H)

    sedi = num / den if den != 0 else 0.0
    tbl["sedi"] = float(np.clip(sedi, -1.0, 1.0))
    return tbl


def compute_all_metrics(
    forecast: np.ndarray,
    truth: np.ndarray,
    persistence: np.ndarray,
    lats: Optional[np.ndarray] = None,
) -> Dict[str, float]:
    """Calculate comprehensive suite of meteorological verification metrics."""
    rmse_fc = weighted_rmse(forecast, truth, lats=lats)
    rmse_pers = weighted_rmse(persistence, truth, lats=lats)
    mae = weighted_mae(forecast, truth, lats=lats)
    mbe = mean_bias(forecast, truth)
    tac = tendency_anomaly_correlation(
        forecast, truth, persistence=persistence, lats=lats
    )

    if rmse_pers > 0:
        skill_score = 1.0 - (rmse_fc / rmse_pers)
    else:
        skill_score = 0.0

    return {
        "rmse_weighted": round(rmse_fc, 4),
        "rmse_persistence": round(rmse_pers, 4),
        "mae_weighted": round(mae, 4),
        "skill_score_vs_persistence": round(skill_score, 4),
        "mean_bias": round(mbe, 4),
        "acc": round(tac, 4),  # Maintained for backwards-compatibility
        "tac": round(tac, 4),  # Explicit Tendency Anomaly Correlation
    }
