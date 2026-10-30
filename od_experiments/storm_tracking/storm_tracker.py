# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Operational tropical cyclone and severe mid-latitude storm tracking engine.
OD-EARTH2-001 / EO-OBSCURA research initiative.
"""

from typing import Any
import numpy as np
from scipy.ndimage import minimum_filter


def detect_mslp_minima(
    mslp_field: np.ndarray,
    lats: np.ndarray,
    lons: np.ndarray,
    neighborhood_size: int = 15,
    threshold_hpa: float = 1005.0,
) -> list[dict[str, float]]:
    """
    Detect local Mean Sea Level Pressure (MSLP) minima centers.
    
    Parameters
    ----------
    mslp_field : np.ndarray
        2D grid of MSLP in hPa or Pa (automatically normalized to hPa).
    lats : np.ndarray
        1D latitude coordinates.
    lons : np.ndarray
        1D longitude coordinates.
    neighborhood_size : int
        Window diameter in grid points for local extrema search.
    threshold_hpa : float
        Maximum MSLP threshold to qualify as a cyclone/depression.
        
    Returns
    -------
    list of dict
        Detected storm centers with lat, lon, and min_mslp_hpa.
    """
    field = np.copy(mslp_field)
    if np.nanmean(field) > 50000.0:  # In Pascals, convert to hPa
        field = field / 100.0
        
    local_min = minimum_filter(field, size=neighborhood_size, mode="wrap")
    is_min = (field == local_min) & (field <= threshold_hpa)
    
    min_indices = np.argwhere(is_min)
    storm_centers = []
    
    for r, c in min_indices:
        storm_centers.append({
            "lat": float(lats[r]),
            "lon": float(lons[c]),
            "min_mslp_hpa": float(field[r, c]),
            "grid_row": int(r),
            "grid_col": int(c),
        })
        
    # Sort from deepest minimum (most intense)
    storm_centers.sort(key=lambda x: x["min_mslp_hpa"])
    return storm_centers


def track_cyclone_trajectory(
    mslp_rollout: np.ndarray,
    lats: np.ndarray,
    lons: np.ndarray,
    init_center_lat: float,
    init_center_lon: float,
    search_radius_deg: float = 8.0,
) -> list[dict[str, Any]]:
    """
    Track a specific storm's core through time steps across a forecast rollout.
    """
    n_steps = mslp_rollout.shape[0]
    trajectory = []
    
    current_lat = init_center_lat
    current_lon = init_center_lon
    
    for step in range(n_steps):
        centers = detect_mslp_minima(mslp_rollout[step], lats, lons, neighborhood_size=9, threshold_hpa=1020.0)
        
        # Find candidate closest to current position
        best_candidate = None
        min_dist = float("inf")
        for cand in centers:
            dlat = cand["lat"] - current_lat
            dlon = (cand["lon"] - current_lon + 180) % 360 - 180
            dist = np.sqrt(dlat**2 + dlon**2)
            if dist < search_radius_deg and dist < min_dist:
                min_dist = dist
                best_candidate = cand
                
        if best_candidate is not None:
            current_lat = best_candidate["lat"]
            current_lon = best_candidate["lon"]
            trajectory.append({
                "step": step,
                "lat": current_lat,
                "lon": current_lon,
                "min_mslp_hpa": best_candidate["min_mslp_hpa"],
            })
        else:
            # Persistent extrapolation if storm dissipates or moves out
            trajectory.append({
                "step": step,
                "lat": current_lat,
                "lon": current_lon,
                "min_mslp_hpa": float("nan"),
            })
            
    return trajectory
