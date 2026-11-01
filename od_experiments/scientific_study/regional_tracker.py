"""Regional sub-grid extraction and extreme event tracking.

Supports:
- Italy Regional Domain (Mediterranean storm tracking)
- Japan Regional Domain (Typhoon / Pacific storm tracking)
"""

from __future__ import annotations

import numpy as np
from typing import Dict, Any, Tuple


# Bounding boxes: (lat_min, lat_max, lon_min, lon_max)
DOMAINS = {
    "italy": {
        "name": "Italy & Central Mediterranean",
        "lat_bounds": (35.0, 48.0),
        "lon_bounds": (6.0, 19.0),
        "description": "Mediterranean cyclogenesis, Alpine wind shear, Ligurian Sea low pressures",
    },
    "japan": {
        "name": "Japan & Western Pacific",
        "lat_bounds": (30.0, 46.0),
        "lon_bounds": (128.0, 146.0),
        "description": "Pacific typhoons, coastal pressure drops, jet stream interaction",
    },
}


def extract_regional_domain(
    grid_data: np.ndarray,
    lats: np.ndarray,
    lons: np.ndarray,
    domain_name: str,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Extract geographical slice for target domain.
    
    grid_data shape: (..., lat, lon)
    Returns: (sliced_data, sliced_lats, sliced_lons)
    """
    if domain_name.lower() not in DOMAINS:
        raise ValueError(f"Unknown domain '{domain_name}'. Valid: {list(DOMAINS.keys())}")
        
    bounds = DOMAINS[domain_name.lower()]
    lat_min, lat_max = bounds["lat_bounds"]
    lon_min, lon_max = bounds["lon_bounds"]

    # Convert lons to 0..360 or -180..180 matching source
    lons_wrapped = np.where(lons > 180.0, lons - 360.0, lons) if np.max(lons) > 180.0 else lons

    lat_idx = np.where((lats >= lat_min) & (lats <= lat_max))[0]
    lon_idx = np.where((lons_wrapped >= lon_min) & (lons_wrapped <= lon_max))[0]

    if len(lat_idx) == 0 or len(lon_idx) == 0:
        raise ValueError(f"No grid coordinates matched bounding box for {domain_name}")

    sliced_lats = lats[lat_idx]
    sliced_lons = lons_wrapped[lon_idx]

    # Index along last two axes
    sliced_data = grid_data[..., lat_idx, :][..., :, lon_idx]
    return sliced_data, sliced_lats, sliced_lons


def find_pressure_minimum(
    msl_grid: np.ndarray,
    lats: np.ndarray,
    lons: np.ndarray,
) -> Dict[str, Any]:
    """Identify cyclone center / low pressure minimum in regional domain."""
    min_idx = np.unravel_index(np.nanargmin(msl_grid), msl_grid.shape)
    min_lat = float(lats[min_idx[-2]])
    min_lon = float(lons[min_idx[-1]])
    min_val = float(msl_grid[min_idx])
    
    return {
        "min_pressure_pa": min_val,
        "center_lat": round(min_lat, 2),
        "center_lon": round(min_lon, 2),
    }


def find_maximum_wind(
    w10m_grid: np.ndarray,
    lats: np.ndarray,
    lons: np.ndarray,
) -> Dict[str, Any]:
    """Identify peak wind speed location in regional domain."""
    max_idx = np.unravel_index(np.nanargmax(w10m_grid), w10m_grid.shape)
    max_lat = float(lats[max_idx[-2]])
    max_lon = float(lons[max_idx[-1]])
    max_val = float(w10m_grid[max_idx])
    
    return {
        "max_wind_speed_ms": round(max_val, 2),
        "peak_lat": round(max_lat, 2),
        "peak_lon": round(max_lon, 2),
    }
