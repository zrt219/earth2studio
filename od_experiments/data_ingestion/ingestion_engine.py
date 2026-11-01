# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Unified multi-source atmospheric data ingestion pipeline.
Handles GFS, ERA5, ARCO-ERA5 Zarr, and GEFS coordinate harmonization.
OD-EARTH2-001 / EO-OBSCURA research initiative.
"""

from typing import Any
import numpy as np


class MultiSourceIngestionEngine:
    """
    Harmonizes coordinates, physical dimensions, and variable standards
    across NOAA GFS, ECMWF ERA5, ARCO-ERA5, and NOAA GEFS.
    """

    SUPPORTED_SOURCES = ["GFS", "ERA5", "ARCO_ERA5", "GEFS"]
    VARIABLE_MAP = {
        "t2m": {"name": "2m_temperature", "canonical_units": "K"},
        "u10m": {"name": "10m_u_wind_component", "canonical_units": "m/s"},
        "v10m": {"name": "10m_v_wind_component", "canonical_units": "m/s"},
        "msl": {"name": "mean_sea_level_pressure", "canonical_units": "Pa"},
    }

    @staticmethod
    def standardize_coordinates(
        data: np.ndarray,
        lats: np.ndarray,
        lons: np.ndarray,
        source_name: str,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Normalize coordinate conventions:
        - Latitudes ordered North (+90) to South (-90) for Earth2Studio convention
        - Longitudes normalized to [0, 360)
        """
        arr = np.copy(data)
        out_lats = np.copy(lats)
        out_lons = np.copy(lons)

        # Check if latitude is ascending (-90 to +90) and invert if necessary
        if out_lats[0] < out_lats[-1]:
            out_lats = out_lats[::-1]
            arr = np.flip(arr, axis=0)

        # Check if longitude is [-180, 180) and shift to [0, 360)
        if np.any(out_lons < 0):
            out_lons = np.where(out_lons < 0, out_lons + 360, out_lons)
            sort_idx = np.argsort(out_lons)
            out_lons = out_lons[sort_idx]
            arr = arr[:, sort_idx]

        return arr, out_lats, out_lons

    @staticmethod
    def validate_physical_consistency(
        variable: str,
        data: np.ndarray,
    ) -> bool:
        """
        Enforce thermodynamic bounds to prevent bogus or corrupt field ingestion.
        """
        if variable == "t2m":
            # Realistic physical atmospheric temperature bounds (170 K to 345 K)
            return bool(np.all(data >= 170.0) and np.all(data <= 345.0))
        elif variable == "msl":
            # Realistic Mean Sea Level Pressure (850 hPa to 1090 hPa in Pa)
            return bool(np.all(data >= 80000.0) and np.all(data <= 115000.0))
        return True
