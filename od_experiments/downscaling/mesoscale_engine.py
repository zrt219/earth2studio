# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Regional mesoscale downscaling and super-resolution diagnostic engine.
Topography-conditioned downscaling preserving physical gradients.
OD-EARTH2-001 / EO-OBSCURA research initiative.
"""

from typing import Any
import numpy as np
from scipy.ndimage import zoom


def downscale_regional_grid(
    coarse_field: np.ndarray,
    scale_factor: int = 4,
    elevation_highres: np.ndarray | None = None,
    lapse_rate_k_per_km: float = 6.5,
) -> np.ndarray:
    """
    Downscale coarse resolution atmospheric fields to high-resolution grid.
    Optionally applies standard environmental lapse rate correction over complex topography.
    
    Parameters
    ----------
    coarse_field : np.ndarray
        2D coarse grid array (e.g. 0.25 deg).
    scale_factor : int
        Refinement ratio (e.g. 4x downscaling to ~0.0625 deg).
    elevation_highres : np.ndarray, optional
        High-resolution terrain elevation in meters.
    lapse_rate_k_per_km : float
        Standard atmospheric lapse rate (default 6.5 K/km).
        
    Returns
    -------
    np.ndarray
        High-resolution physical field.
    """
    # High-order cubic spline interpolation
    fine_field = zoom(coarse_field, scale_factor, order=3)
    
    # Topographic orographic adjustment
    if elevation_highres is not None:
        if elevation_highres.shape != fine_field.shape:
            elev_resized = zoom(
                elevation_highres,
                (fine_field.shape[0] / elevation_highres.shape[0], fine_field.shape[1] / elevation_highres.shape[1]),
                order=1
            )
        else:
            elev_resized = elevation_highres
            
        # Delta elevation relative to coarse mean
        elev_anomaly_km = (elev_resized - np.mean(elev_resized)) / 1000.0
        # Lapse-rate orographic cooling
        fine_field = fine_field - (lapse_rate_k_per_km * elev_anomaly_km)
        
    return fine_field
