# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Atmospheric Data Assimilation (DA) increment engine.
Calculates innovation vectors (y - H(x_b)) and assimilates sparse observational networks.
OD-EARTH2-001 / EO-OBSCURA research initiative.
"""

from typing import Any
import numpy as np
from scipy.interpolate import griddata


def run_point_observation_assimilation(
    background_field: np.ndarray,
    lats: np.ndarray,
    lons: np.ndarray,
    obs_points: list[dict[str, float]],
    influence_radius_deg: float = 5.0,
    observation_error_std: float = 0.5,
) -> dict[str, Any]:
    """
    Perform 2D Optimal Interpolation (OI) / Barnes objective analysis
    to produce authentic data assimilation analysis increments:
    x_a = x_b + K * (y - H(x_b))
    
    Parameters
    ----------
    background_field : np.ndarray
        Prior atmospheric background state x_b (e.g. short-range model forecast).
    lats : np.ndarray
        1D latitude coordinates.
    lons : np.ndarray
        1D longitude coordinates.
    obs_points : list of dict
        Sparse in-situ observations with keys 'lat', 'lon', 'value'.
    influence_radius_deg : float
        Gaussian localization scale parameter.
    observation_error_std : float
        Assumed observation instrument error variance.
        
    Returns
    -------
    dict
        Analysis field x_a, analysis increment (x_a - x_b), and innovations (y - H(x_b)).
    """
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    
    innovations = []
    increments = np.zeros_like(background_field)
    weights_sum = np.zeros_like(background_field)
    
    for obs in obs_points:
        olat = obs["lat"]
        olon = obs["lon"]
        oval = obs["value"]
        
        # Forward observation operator H(x_b): bilinear sample background at obs point
        r = np.argmin(np.abs(lats - olat))
        c = np.argmin(np.abs(lons - olon))
        h_xb = background_field[r, c]
        
        # Innovation d = y - H(x_b)
        innov = oval - h_xb
        innovations.append({
            "lat": olat,
            "lon": olon,
            "observed": oval,
            "background": float(h_xb),
            "innovation": float(innov),
        })
        
        # Distance calculation with spherical periodic wrap
        dlat = lat_grid - olat
        dlon = (lon_grid - olon + 180) % 360 - 180
        dist_sq = dlat**2 + dlon**2
        
        # Gaussian correlation weight
        w = np.exp(-dist_sq / (2.0 * influence_radius_deg**2))
        increments += w * innov
        weights_sum += w
        
    # Normalize increment where observations provide signal
    mask = weights_sum > 1e-4
    analysis_increment = np.zeros_like(background_field)
    analysis_increment[mask] = increments[mask] / (weights_sum[mask] + (observation_error_std**2))
    
    # Analysis state: x_a = x_b + increment
    analysis_field = background_field + analysis_increment
    
    return {
        "analysis_field": analysis_field,
        "analysis_increment": analysis_increment,
        "innovations": innovations,
        "mean_absolute_increment": float(np.mean(np.abs(analysis_increment))),
        "max_increment": float(np.max(np.abs(analysis_increment))),
    }
