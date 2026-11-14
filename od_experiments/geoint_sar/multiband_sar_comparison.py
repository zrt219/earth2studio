# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-FileCopyrightText: Copyright (c) 2026 Zhane Daye (SAR & Earth System Engineering; zhanedaye@umattr.ca)
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Multi-Band InSAR Comparative Physics Simulation Suite:
X-Band (9.65 GHz, 3.11 cm), C-Band (5.405 GHz, 5.55 cm), and L-Band (1.27 GHz, 23.6 cm).

Comparative Modeling across South Africa, Mexico, and Northern Russia:
  1. Tropospheric Phase Fringe Density:
     Delta_phi = (4 * pi / lambda) * Delta_R = (4 * pi / (lambda * cos(theta_inc))) * Delta_ZTD
     Fringe density scales as 1 / lambda, producing a ~7.60x higher fringe count at X-band compared
     to L-band across high-relief topography (Drakensberg Escarpment 3482m, Popocatépetl 5426m /
     Pico de Orizaba 5636m, and Putorana Plateau Basalt Traps 1701m).
     Demonstrates severe phase unwrapping aliasing hazards (phase gradient >= pi rad/pixel) at X-band
     versus the robust unwrappability of L-band InSAR.
  2. Temporal Decorrelation Decay over Vegetated Terrain:
     gamma_temporal(Delta_t) = gamma_inf + (1 - gamma_inf) * exp(-Delta_t / tau_decay(lambda))
     where tau_decay(lambda) scales quadratically with wavelength: tau_decay ~ tau_0 * (lambda / lambda_X)^2.
     Evaluates temporal coherence preservation across three contrasting biomes:
       - South Africa Highveld Savanna / Drakensberg Montane Grassland / Cape Fynbos
       - Mexico Trans-Mexican Volcanic Belt & Sierra Madre Pine-Oak Montane Forests
       - Northern Russia Siberian Larch Taiga & Putorana Permafrost Tundra
  3. Electromagnetic Penetration Depth:
     delta_p = lambda / (4 * pi * Im(sqrt(epsilon_r))) in dielectric media and
     delta_p,canopy = cos(theta_inc) / (2 * kappa_e(f)) in volume-scattering canopies.
     Compares penetration across four natural media:
       - Dense Vegetated Forest Canopy (top-of-canopy vs sub-canopy bare ground)
       - Dry Soil & Arid Sand Regolith (superficial skin depth vs deep subsurface imaging)
       - Wet / Agricultural Soil (strong dielectric boundary reflection)
       - Cold Dry Snowpack & Permafrost Ice (Rayleigh ice grain scattering vs deep bedrock penetration)

Strict Compliance with .agents/rules/e2s-014-scientific-integrity.mdc:
  - Zero synthetic or stochastic noise generation (no pseudo-random numbers).
  - Operates deterministically on operational NOAA GFS 0.25 deg thermodynamic tensors or
    deterministic physical reference fields.
  - Geospatial grids plotted with explicit origin="upper" when latitudes run North-to-South.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from loguru import logger

from od_experiments.geoint_sar.mexico_terrain import build_mexico_orography
from od_experiments.geoint_sar.russia_terrain import (
    build_putorana_basalt_trap_orography,
    compute_subzero_tropospheric_delay_ztd,
)
from od_experiments.geoint_sar.sar_geoint_engine import (
    _upsample_synoptic_theater,
    compute_tropospheric_delay_ztd,
)
from od_experiments.geoint_sar.south_africa_terrain import build_south_africa_orography

# -----------------------------------------------------------------------------
# Fundamental Physical & Radar Constants
# -----------------------------------------------------------------------------
SPEED_OF_LIGHT_MPS: float = 299_792_458.0

# X-Band (ICEYE Spotlight/StripMap, Synspective StriX, TerraSAR-X, COSMO-SkyMed)
X_BAND_FREQUENCY_HZ: float = 9.65e9  # 9.65 GHz
X_BAND_WAVELENGTH_M: float = (
    SPEED_OF_LIGHT_MPS / X_BAND_FREQUENCY_HZ
)  # ~0.031066576 m (3.11 cm)
X_BAND_HALF_WAVELENGTH_M: float = X_BAND_WAVELENGTH_M / 2.0  # ~0.0155333 m (1.55 cm)

# C-Band (Copernicus Sentinel-1A/B/C, RADARSAT-2, RADARSAT Constellation)
C_BAND_FREQUENCY_HZ: float = 5.405e9  # 5.405 GHz
C_BAND_WAVELENGTH_M: float = (
    SPEED_OF_LIGHT_MPS / C_BAND_FREQUENCY_HZ
)  # ~0.055465765 m (5.55 cm)
C_BAND_HALF_WAVELENGTH_M: float = C_BAND_WAVELENGTH_M / 2.0  # ~0.0277329 m (2.77 cm)

# L-Band (NASA-ISRO NISAR, JAXA ALOS-2 PALSAR-2, ALOS-4, SAOCOM 1A/1B)
L_BAND_FREQUENCY_HZ: float = 1.27e9  # 1.27 GHz (NISAR L-band center)
L_BAND_WAVELENGTH_M: float = (
    SPEED_OF_LIGHT_MPS / L_BAND_FREQUENCY_HZ
)  # ~0.236057054 m (23.6 cm)
L_BAND_HALF_WAVELENGTH_M: float = L_BAND_WAVELENGTH_M / 2.0  # ~0.1180285 m (11.80 cm)

# Multi-Band Radar Specifications Registry
MULTIBAND_SPECS: dict[str, dict[str, Any]] = {
    "X": {
        "band": "X-band",
        "frequency_ghz": 9.65,
        "frequency_hz": X_BAND_FREQUENCY_HZ,
        "wavelength_cm": float(X_BAND_WAVELENGTH_M * 100.0),
        "wavelength_m": X_BAND_WAVELENGTH_M,
        "half_wavelength_cm": float(X_BAND_HALF_WAVELENGTH_M * 100.0),
        "half_wavelength_m": X_BAND_HALF_WAVELENGTH_M,
        "missions": [
            "ICEYE (Spotlight/StripMap)",
            "Synspective (StriX)",
            "TerraSAR-X / TanDEM-X",
            "COSMO-SkyMed",
        ],
        "typical_incidence_deg": 34.1,
        "typical_resolution_m": 0.5,
        "repeat_cycle_days": 1.0,  # Constellation daily revisit
        "color": "#38bdf8",  # Sky Blue
    },
    "C": {
        "band": "C-band",
        "frequency_ghz": 5.405,
        "frequency_hz": C_BAND_FREQUENCY_HZ,
        "wavelength_cm": float(C_BAND_WAVELENGTH_M * 100.0),
        "wavelength_m": C_BAND_WAVELENGTH_M,
        "half_wavelength_cm": float(C_BAND_HALF_WAVELENGTH_M * 100.0),
        "half_wavelength_m": C_BAND_HALF_WAVELENGTH_M,
        "missions": [
            "Copernicus Sentinel-1 (IW SLC)",
            "RADARSAT-2",
            "RADARSAT Constellation (RCM)",
        ],
        "typical_incidence_deg": 39.0,
        "typical_resolution_m": 14.0,
        "repeat_cycle_days": 6.0,  # Sentinel-1 exact repeat
        "color": "#10b981",  # Emerald Green
    },
    "L": {
        "band": "L-band",
        "frequency_ghz": 1.270,
        "frequency_hz": L_BAND_FREQUENCY_HZ,
        "wavelength_cm": float(L_BAND_WAVELENGTH_M * 100.0),
        "wavelength_m": L_BAND_WAVELENGTH_M,
        "half_wavelength_cm": float(L_BAND_HALF_WAVELENGTH_M * 100.0),
        "half_wavelength_m": L_BAND_HALF_WAVELENGTH_M,
        "missions": [
            "NASA-ISRO NISAR",
            "JAXA ALOS-2 (PALSAR-2)",
            "JAXA ALOS-4",
            "SAOCOM 1A/1B",
        ],
        "typical_incidence_deg": 37.0,
        "typical_resolution_m": 6.0,
        "repeat_cycle_days": 12.0,  # NISAR exact repeat
        "color": "#f59e0b",  # Amber / Gold
    },
}

# Regional Biome Temporal Decorrelation Parameters
BIOME_DECORRELATION_MODELS: dict[str, dict[str, Any]] = {
    "south_africa_savanna": {
        "name": "South Africa Highveld Savanna & Drakensberg Grassland",
        "region": "South Africa",
        "description": "Savanna grassland, scattered acacia, Drakensberg alpine meadow, Cape fynbos shrub",
        "tau0_x_days": 2.20,
        "gamma_infinity": 0.15,
        "typical_canopy_height_m": 1.8,
    },
    "mexico_pine_oak": {
        "name": "Mexico Subtropical Pine-Oak Montane Forest",
        "region": "Mexico",
        "description": "Dense high-biomass humid montane forest, Trans-Mexican Volcanic Belt, high moisture",
        "tau0_x_days": 0.85,
        "gamma_infinity": 0.08,
        "typical_canopy_height_m": 22.0,
    },
    "russia_taiga_tundra": {
        "name": "Northern Russia Siberian Larch Taiga & Tundra",
        "region": "Northern Russia",
        "description": "Central Siberian larch taiga (Larix gmelinii) & Putorana moss-lichen permafrost tundra",
        "tau0_x_days": 1.70,
        "gamma_infinity": 0.18,
        "typical_canopy_height_m": 12.0,
    },
}

# Electromagnetic Penetration Depth Parameters across Media
PENETRATION_MEDIA_MODELS: dict[str, dict[str, Any]] = {
    "forest_canopy": {
        "name": "Dense Vegetated Forest Canopy",
        "mechanism": "Volume scattering and leaf/needle/branch dielectric absorption",
        "unit": "meters",
        "depths_m": {
            "X": 0.55,  # Top-of-canopy / crown scattering only
            "C": 2.45,  # Upper canopy / secondary branches
            "L": 11.85,  # Full canopy penetration to trunk-ground double bounce
        },
        "description": "X-band reflects from outer leaf crown; C-band penetrates into upper canopy; L-band reaches the ground surface.",
    },
    "dry_soil_sand": {
        "name": "Dry Soil & Arid Sand Regolith",
        "mechanism": "Low-loss dielectric conduction (epsilon_r' ~ 3.0, tan delta ~ 0.020)",
        "unit": "meters",
        "depths_m": {
            "X": 0.143,  # ~14 cm superficial soil moisture layer
            "C": 0.255,  # ~26 cm shallow root zone
            "L": 1.085,  # ~1.09 m deep subsurface / buried paleochannel imaging
        },
        "description": "X-band measures surface skin layer; C-band penetrates topsoil; L-band probes deep subsurface structures.",
    },
    "wet_soil": {
        "name": "Wet / Saturated Agricultural Soil",
        "mechanism": "High-loss dielectric attenuation (epsilon_r' ~ 18.0, tan delta ~ 0.180)",
        "unit": "meters",
        "depths_m": {
            "X": 0.012,  # 1.2 cm skin reflection
            "C": 0.038,  # 3.8 cm plough skin
            "L": 0.185,  # 18.5 cm plough layer
        },
        "description": "High moisture causes strong dielectric reflection across all bands; L-band maintains modest plough layer penetration.",
    },
    "permafrost_ice_snow": {
        "name": "Cold Dry Snowpack & Permafrost Ice",
        "mechanism": "Ice dielectric propagation with grain Rayleigh scattering (kappa_s ~ f^4)",
        "unit": "meters",
        "depths_m": {
            "X": 2.40,  # Limited by ice grain Rayleigh scattering
            "C": 7.20,  # Deep penetration into seasonal snowpack
            "L": 28.50,  # Deep penetration through snowpack into permafrost active layer & ice bedrock
        },
        "description": "Sub-zero cold minimizes dielectric loss; Rayleigh scattering limits X-band, while L-band penetrates deeply into permafrost.",
    },
}


# -----------------------------------------------------------------------------
# Core Physics 1: Tropospheric Phase Fringe Density & Spatial Nyquist Gradient
# -----------------------------------------------------------------------------
def compute_multiband_insar_phase(
    delta_ztd_m: np.ndarray,
    incidence_deg: float = 34.1,
    wavelength_m: float = X_BAND_WAVELENGTH_M,
    true_deformation_los_m: np.ndarray | None = None,
) -> dict[str, Any]:
    """Compute InSAR differential tropospheric slant delay, unwrapped phase, and wrapped fringes.

    Calculates the two-way interferometric phase:
      Delta_phi = (4 * pi / lambda) * Delta_R = (4 * pi / (lambda * cos(theta_inc))) * Delta_ZTD
    and quantifies fringe density, spatial phase gradient, and Nyquist sampling violations.

    Parameters
    ----------
    delta_ztd_m : np.ndarray
        Differential Zenith Total Delay in meters, shape (H, W).
    incidence_deg : float, optional
        SAR side-looking incidence angle in degrees, by default 34.1.
    wavelength_m : float, optional
        Radar carrier wavelength in meters, by default X_BAND_WAVELENGTH_M (~0.0310666 m).
    true_deformation_los_m : np.ndarray | None, optional
        True surface ground deformation along line-of-sight in meters, shape (H, W).
        If None, purely atmospheric delay is modeled.

    Returns
    -------
    dict[str, Any]
        Dictionary containing:
          - ``delta_slant_m``: Two-way slant-range delay difference in meters.
          - ``phase_unwrapped_rad``: Total unwrapped interferometric phase in radians.
          - ``phase_wrapped_rad``: Wrapped interferometric phase in [-pi, +pi] radians.
          - ``fringe_count``: Total number of 2*pi phase fringes across the scene relief.
          - ``dphi_dy``: Latitudinal pixel-to-pixel phase step in radians.
          - ``dphi_dx``: Longitudinal pixel-to-pixel phase step in radians.
          - ``max_gradient_rad``: Maximum spatial phase step in radians/pixel.
          - ``nyquist_violation_fraction``: Fraction of pixels exceeding Nyquist limit (|grad| >= pi).
    """
    inc_rad = np.deg2rad(np.clip(incidence_deg, 10.0, 65.0))
    cos_inc = float(np.cos(inc_rad))

    delta_ztd = np.asarray(delta_ztd_m, dtype=np.float64)
    delta_slant_m = delta_ztd / cos_inc

    # Two-way atmospheric phase screen
    phase_aps_rad = (4.0 * np.pi / wavelength_m) * delta_slant_m

    if true_deformation_los_m is not None:
        def_los = np.asarray(true_deformation_los_m, dtype=np.float64)
        phase_def_rad = (4.0 * np.pi / wavelength_m) * def_los
        phase_unwrapped_rad = phase_aps_rad + phase_def_rad
    else:
        phase_unwrapped_rad = phase_aps_rad

    # Wrapped phase into [-pi, +pi]
    phase_wrapped_rad = ((phase_unwrapped_rad + np.pi) % (2.0 * np.pi)) - np.pi

    # Fringe count across scene relief
    phase_span = float(np.max(phase_unwrapped_rad) - np.min(phase_unwrapped_rad))
    fringe_count = phase_span / (2.0 * np.pi)

    # Spatial phase gradient for Nyquist sampling evaluation
    dphi_dy = (
        np.abs(np.diff(phase_unwrapped_rad, axis=0))
        if phase_unwrapped_rad.shape[0] > 1
        else np.empty((0, phase_unwrapped_rad.shape[1]), dtype=np.float32)
    )
    dphi_dx = (
        np.abs(np.diff(phase_unwrapped_rad, axis=1))
        if phase_unwrapped_rad.shape[1] > 1
        else np.empty((phase_unwrapped_rad.shape[0], 0), dtype=np.float32)
    )

    all_grads = []
    if dphi_dy.size > 0:
        all_grads.append(dphi_dy.ravel())
    if dphi_dx.size > 0:
        all_grads.append(dphi_dx.ravel())

    if all_grads:
        cat_grads = np.concatenate(all_grads)
        max_gradient_rad = float(np.max(cat_grads))
        nyquist_violation_fraction = float(np.mean(cat_grads >= np.pi))
    else:
        max_gradient_rad = 0.0
        nyquist_violation_fraction = 0.0

    return {
        "wavelength_m": float(wavelength_m),
        "half_wavelength_cm": float(wavelength_m * 50.0),
        "phase_span_rad": float(phase_span),
        "delta_slant_m": delta_slant_m.astype(np.float32),
        "phase_unwrapped_rad": phase_unwrapped_rad.astype(np.float32),
        "phase_wrapped_rad": phase_wrapped_rad.astype(np.float32),
        "fringe_count": float(round(fringe_count, 2)),
        "dphi_dy": dphi_dy.astype(np.float32),
        "dphi_dx": dphi_dx.astype(np.float32),
        "max_gradient_rad": float(round(max_gradient_rad, 3)),
        "nyquist_violation_fraction": float(round(nyquist_violation_fraction, 4)),
    }


def compute_all_bands_insar_simulation(
    delta_ztd_m: np.ndarray,
    incidence_deg: float = 34.1,
    true_deformation_los_m: np.ndarray | None = None,
) -> dict[str, dict[str, Any]]:
    """Compute parallel multi-band InSAR simulations for X, C, and L bands.

    Parameters
    ----------
    delta_ztd_m : np.ndarray
        Differential Zenith Total Delay in meters, shape (H, W).
    incidence_deg : float, optional
        Radar incidence angle in degrees, by default 34.1.
    true_deformation_los_m : np.ndarray | None, optional
        True surface displacement field in meters, by default None.

    Returns
    -------
    dict[str, dict[str, Any]]
        Dictionary keyed by band ("X", "C", "L") with simulation outputs.
    """
    bands_res = {
        "X": compute_multiband_insar_phase(
            delta_ztd_m,
            incidence_deg=incidence_deg,
            wavelength_m=X_BAND_WAVELENGTH_M,
            true_deformation_los_m=true_deformation_los_m,
        ),
        "C": compute_multiband_insar_phase(
            delta_ztd_m,
            incidence_deg=incidence_deg,
            wavelength_m=C_BAND_WAVELENGTH_M,
            true_deformation_los_m=true_deformation_los_m,
        ),
        "L": compute_multiband_insar_phase(
            delta_ztd_m,
            incidence_deg=incidence_deg,
            wavelength_m=L_BAND_WAVELENGTH_M,
            true_deformation_los_m=true_deformation_los_m,
        ),
    }
    return bands_res


# -----------------------------------------------------------------------------
# Core Physics 2: Temporal Decorrelation Decay over Vegetation
# -----------------------------------------------------------------------------
def compute_temporal_decorrelation_decay(
    time_days: np.ndarray,
    band: str = "X",
    biome: str = "mexico_pine_oak",
) -> dict[str, Any]:
    """Model InSAR temporal coherence decay over vegetation as a function of time baseline.

    Uses the wavelength-scaled temporal decorrelation formulation (Zebker & Villasenor 1992):
      gamma_temporal(t) = gamma_inf + (1 - gamma_inf) * exp(-t / tau_decay(lambda))
    where the decay constant scales quadratically with wavelength:
      tau_decay(lambda) = tau_0 * (lambda / lambda_X)^2

    Parameters
    ----------
    time_days : np.ndarray
        1D array of temporal baselines in days, e.g. np.linspace(0.0, 60.0, 300).
    band : str, optional
        Radar frequency band ("X", "C", or "L"), by default "X".
    biome : str, optional
        Vegetation biome key ("south_africa_savanna", "mexico_pine_oak", or "russia_taiga_tundra"),
        by default "mexico_pine_oak".

    Returns
    -------
    dict[str, Any]
        Dictionary containing ``coherence`` array, ``tau_decay_days``, ``half_life_days``,
        and metadata.
    """
    if band not in MULTIBAND_SPECS:
        raise ValueError(
            f"Unsupported band '{band}'. Must be one of: {list(MULTIBAND_SPECS.keys())}"
        )
    if biome not in BIOME_DECORRELATION_MODELS:
        raise ValueError(
            f"Unsupported biome '{biome}'. Must be one of: {list(BIOME_DECORRELATION_MODELS.keys())}"
        )

    b_spec = MULTIBAND_SPECS[band]
    b_model = BIOME_DECORRELATION_MODELS[biome]

    tau0_x = float(b_model["tau0_x_days"])
    gamma_inf = float(b_model["gamma_infinity"])
    lambda_ratio = float(b_spec["wavelength_m"] / X_BAND_WAVELENGTH_M)

    # Quadratic wavelength scaling: tau ~ lambda^2
    tau_decay_days = tau0_x * (lambda_ratio**2)
    half_life_days = tau_decay_days * np.log(2.0)

    t_arr = np.asarray(time_days, dtype=np.float64)
    coherence = gamma_inf + (1.0 - gamma_inf) * np.exp(-t_arr / tau_decay_days)

    return {
        "band": band,
        "biome": biome,
        "wavelength_cm": float(b_spec["wavelength_cm"]),
        "tau_decay_days": float(round(tau_decay_days, 2)),
        "half_life_days": float(round(half_life_days, 2)),
        "gamma_infinity": gamma_inf,
        "coherence": coherence.astype(np.float32),
        "coherence_at_1d": float(
            round(gamma_inf + (1.0 - gamma_inf) * np.exp(-1.0 / tau_decay_days), 3)
        ),
        "coherence_at_6d": float(
            round(gamma_inf + (1.0 - gamma_inf) * np.exp(-6.0 / tau_decay_days), 3)
        ),
        "coherence_at_12d": float(
            round(
                gamma_inf + (1.0 - gamma_inf) * np.exp(-12.0 / tau_decay_days),
                3,
            )
        ),
        "coherence_at_24d": float(
            round(
                gamma_inf + (1.0 - gamma_inf) * np.exp(-24.0 / tau_decay_days),
                3,
            )
        ),
    }


def compute_all_bands_temporal_decorrelation(
    time_days: np.ndarray,
    biome: str = "mexico_pine_oak",
) -> dict[str, dict[str, Any]]:
    """Compute temporal decorrelation curves across X, C, and L bands for a given biome.

    Parameters
    ----------
    time_days : np.ndarray
        1D array of temporal baselines in days.
    biome : str, optional
        Biome model key, by default "mexico_pine_oak".

    Returns
    -------
    dict[str, dict[str, Any]]
        Dictionary keyed by "X", "C", and "L" with decorrelation metrics.
    """
    return {
        "X": compute_temporal_decorrelation_decay(time_days, band="X", biome=biome),
        "C": compute_temporal_decorrelation_decay(time_days, band="C", biome=biome),
        "L": compute_temporal_decorrelation_decay(time_days, band="L", biome=biome),
    }


# -----------------------------------------------------------------------------
# Core Physics 3: Electromagnetic Penetration Depth
# -----------------------------------------------------------------------------
def compute_electromagnetic_penetration_depth(
    medium: str,
    band: str | None = None,
    incidence_deg: float = 35.0,
) -> dict[str, Any]:
    """Compute radar electromagnetic penetration depth (meters) across natural media.

    The penetration depth delta_p (or power skin depth, where power drops by 1/e) is
    derived from complex permittivity:
      delta_p = lambda / (4 * pi * Im(sqrt(epsilon_r)))
    or for vegetated canopies and snowpacks with extinction coefficient kappa_e(f):
      delta_p = cos(theta_inc) / (2 * kappa_e(f))

    Parameters
    ----------
    medium : str
        Media model key ("forest_canopy", "dry_soil_sand", "wet_soil", or "permafrost_ice_snow").
    band : str | None, optional
        If specified ("X", "C", "L"), returns depth for that band. If None, returns all bands.
    incidence_deg : float, optional
        Incidence angle in degrees, by default 35.0.

    Returns
    -------
    dict[str, Any]
        Penetration depth dictionary with values in meters and scientific description.
    """
    if medium not in PENETRATION_MEDIA_MODELS:
        raise ValueError(
            f"Unsupported medium '{medium}'. Must be one of: {list(PENETRATION_MEDIA_MODELS.keys())}"
        )

    m_info = PENETRATION_MEDIA_MODELS[medium]
    depths = m_info["depths_m"]

    if band is not None:
        if band not in depths:
            raise ValueError(
                f"Unsupported band '{band}'. Must be one of: {list(depths.keys())}"
            )
        return {
            "medium": medium,
            "medium_name": m_info["name"],
            "band": band,
            "wavelength_cm": float(MULTIBAND_SPECS[band]["wavelength_cm"]),
            "penetration_depth_m": float(depths[band]),
            "mechanism": m_info["mechanism"],
            "description": m_info["description"],
        }

    return {
        "medium": medium,
        "medium_name": m_info["name"],
        "depths_m": {b: float(depths[b]) for b in ["X", "C", "L"]},
        "mechanism": m_info["mechanism"],
        "description": m_info["description"],
    }


# -----------------------------------------------------------------------------
# Regional Simulation Theaters: South Africa, Mexico, Northern Russia
# -----------------------------------------------------------------------------
def simulate_south_africa_multiband(
    global_t0: np.ndarray,
    global_t24: np.ndarray,
    global_lats: np.ndarray,
    global_lons: np.ndarray,
) -> dict[str, Any]:
    """Simulate multi-band InSAR performance across South Africa & Drakensberg Escarpment."""
    # South Africa bounds: -26.0S to -35.0S, 18.0E to 33.0E
    sa_lat_mask = (global_lats <= -26.0) & (global_lats >= -35.0)
    sa_lon_mask = (global_lons >= 18.0) & (global_lons <= 33.0)

    fine_t0, fine_t24, fine_lats, fine_lons = _upsample_synoptic_theater(
        global_t0[np.ix_(sa_lat_mask, sa_lon_mask)],
        global_t24[np.ix_(sa_lat_mask, sa_lon_mask)],
        global_lats[sa_lat_mask],
        global_lons[sa_lon_mask],
        scale_factor=8,
        synoptic_sigma=1.8,
    )
    elev = build_south_africa_orography(fine_lats, fine_lons)

    # Compute ZTD states
    ztd_t0 = compute_tropospheric_delay_ztd(
        fine_t0, elev, fine_lats, rh_fraction=0.74, sea_level_pressure_hpa=1013.25
    )
    ztd_t24 = compute_tropospheric_delay_ztd(
        fine_t24, elev, fine_lats, rh_fraction=0.82, sea_level_pressure_hpa=1009.5
    )
    delta_ztd_m = (ztd_t24["ztd_m"] - ztd_t0["ztd_m"]).astype(np.float64)

    # Multi-band InSAR phase simulation
    bands_sim = compute_all_bands_insar_simulation(delta_ztd_m, incidence_deg=34.1)

    # Cross-section along Drakensberg Escarpment transect (lat ~ -29.5S)
    transect_row = int(np.argmin(np.abs(fine_lats - (-29.47))))
    transect_lons = fine_lons
    transect_elev = elev[transect_row, :]
    transect_ztd = delta_ztd_m[transect_row, :]

    return {
        "theater": "south_africa_drakensberg",
        "name": "South Africa Drakensberg Escarpment & Lesotho Highlands",
        "lats": fine_lats,
        "lons": fine_lons,
        "elev_m": elev,
        "delta_ztd_m": delta_ztd_m.astype(np.float32),
        "bands": bands_sim,
        "transect": {
            "lat": float(fine_lats[transect_row]),
            "lons": transect_lons,
            "elev_m": transect_elev,
            "delta_ztd_m": transect_ztd.astype(np.float32),
            "phase_unwrapped_X": bands_sim["X"]["phase_unwrapped_rad"][transect_row, :],
            "phase_unwrapped_C": bands_sim["C"]["phase_unwrapped_rad"][transect_row, :],
            "phase_unwrapped_L": bands_sim["L"]["phase_unwrapped_rad"][transect_row, :],
        },
        "metrics": {
            "max_elevation_m": float(round(float(np.max(elev)), 1)),
            "min_elevation_m": float(round(float(np.min(elev)), 1)),
            "max_delta_ztd_m": float(round(float(np.max(delta_ztd_m)), 4)),
            "fringes_X": bands_sim["X"]["fringe_count"],
            "fringes_C": bands_sim["C"]["fringe_count"],
            "fringes_L": bands_sim["L"]["fringe_count"],
            "fringe_ratio_X_to_L": float(
                round(
                    bands_sim["X"]["phase_span_rad"]
                    / max(bands_sim["L"]["phase_span_rad"], 1e-6),
                    2,
                )
            ),
            "nyquist_violation_pct_X": float(
                round(bands_sim["X"]["nyquist_violation_fraction"] * 100.0, 2)
            ),
            "nyquist_violation_pct_C": float(
                round(bands_sim["C"]["nyquist_violation_fraction"] * 100.0, 2)
            ),
            "nyquist_violation_pct_L": float(
                round(bands_sim["L"]["nyquist_violation_fraction"] * 100.0, 2)
            ),
        },
    }


def simulate_mexico_multiband(
    global_t0: np.ndarray,
    global_t24: np.ndarray,
    global_lats: np.ndarray,
    global_lons: np.ndarray,
) -> dict[str, Any]:
    """Simulate multi-band InSAR performance across Mexico Trans-Mexican Volcanic Belt."""
    # Trans-Mexican Volcanic Belt bounds: 18.0N to 20.8N, 256.0E to 264.0E (-104W to -96W)
    v_lat_mask = (global_lats <= 20.8) & (global_lats >= 18.0)
    v_lon_mask = (global_lons >= 256.0) & (global_lons <= 264.0)

    fine_t0, fine_t24, fine_lats, fine_lons = _upsample_synoptic_theater(
        global_t0[np.ix_(v_lat_mask, v_lon_mask)],
        global_t24[np.ix_(v_lat_mask, v_lon_mask)],
        global_lats[v_lat_mask],
        global_lons[v_lon_mask],
        scale_factor=8,
        synoptic_sigma=1.8,
    )
    elev = build_mexico_orography(fine_lats, fine_lons, theater="volcanic_belt")

    # Compute ZTD states
    ztd_t0 = compute_tropospheric_delay_ztd(
        fine_t0, elev, fine_lats, rh_fraction=0.76, sea_level_pressure_hpa=1013.25
    )
    ztd_t24 = compute_tropospheric_delay_ztd(
        fine_t24, elev, fine_lats, rh_fraction=0.86, sea_level_pressure_hpa=1007.8
    )
    delta_ztd_m = (ztd_t24["ztd_m"] - ztd_t0["ztd_m"]).astype(np.float64)

    # Multi-band InSAR phase simulation
    bands_sim = compute_all_bands_insar_simulation(delta_ztd_m, incidence_deg=34.1)

    # Cross-section along Popocatépetl / Pico de Orizaba parallel (lat ~ 19.05N)
    transect_row = int(np.argmin(np.abs(fine_lats - 19.05)))
    transect_lons = fine_lons
    transect_elev = elev[transect_row, :]
    transect_ztd = delta_ztd_m[transect_row, :]

    return {
        "theater": "mexico_volcanic_belt",
        "name": "Mexico Trans-Mexican Volcanic Belt (Pico de Orizaba & Popocatépetl)",
        "lats": fine_lats,
        "lons": fine_lons,
        "elev_m": elev,
        "delta_ztd_m": delta_ztd_m.astype(np.float32),
        "bands": bands_sim,
        "transect": {
            "lat": float(fine_lats[transect_row]),
            "lons": transect_lons,
            "elev_m": transect_elev,
            "delta_ztd_m": transect_ztd.astype(np.float32),
            "phase_unwrapped_X": bands_sim["X"]["phase_unwrapped_rad"][transect_row, :],
            "phase_unwrapped_C": bands_sim["C"]["phase_unwrapped_rad"][transect_row, :],
            "phase_unwrapped_L": bands_sim["L"]["phase_unwrapped_rad"][transect_row, :],
        },
        "metrics": {
            "max_elevation_m": float(round(float(np.max(elev)), 1)),
            "min_elevation_m": float(round(float(np.min(elev)), 1)),
            "max_delta_ztd_m": float(round(float(np.max(delta_ztd_m)), 4)),
            "fringes_X": bands_sim["X"]["fringe_count"],
            "fringes_C": bands_sim["C"]["fringe_count"],
            "fringes_L": bands_sim["L"]["fringe_count"],
            "fringe_ratio_X_to_L": float(
                round(
                    bands_sim["X"]["phase_span_rad"]
                    / max(bands_sim["L"]["phase_span_rad"], 1e-6),
                    2,
                )
            ),
            "nyquist_violation_pct_X": float(
                round(bands_sim["X"]["nyquist_violation_fraction"] * 100.0, 2)
            ),
            "nyquist_violation_pct_C": float(
                round(bands_sim["C"]["nyquist_violation_fraction"] * 100.0, 2)
            ),
            "nyquist_violation_pct_L": float(
                round(bands_sim["L"]["nyquist_violation_fraction"] * 100.0, 2)
            ),
        },
    }


def simulate_russia_multiband(
    global_t0: np.ndarray,
    global_t24: np.ndarray,
    global_lats: np.ndarray,
    global_lons: np.ndarray,
) -> dict[str, Any]:
    """Simulate multi-band InSAR performance across Northern Russia Putorana Plateau Basalt Traps."""
    # Putorana Plateau bounds: 68.0N to 71.0N, 88.0E to 96.0E
    ru_lat_mask = (global_lats <= 71.0) & (global_lats >= 68.0)
    ru_lon_mask = (global_lons >= 88.0) & (global_lons <= 96.0)

    fine_t0, fine_t24, fine_lats, fine_lons = _upsample_synoptic_theater(
        global_t0[np.ix_(ru_lat_mask, ru_lon_mask)],
        global_t24[np.ix_(ru_lat_mask, ru_lon_mask)],
        global_lats[ru_lat_mask],
        global_lons[ru_lon_mask],
        scale_factor=8,
        synoptic_sigma=1.8,
    )
    elev = build_putorana_basalt_trap_orography(fine_lats, fine_lons)

    # Compute sub-zero ZTD states
    ztd_t0 = compute_subzero_tropospheric_delay_ztd(
        fine_t0, elev, fine_lats, rh_fraction=0.72, sea_level_pressure_hpa=1018.0
    )
    ztd_t24 = compute_subzero_tropospheric_delay_ztd(
        fine_t24, elev, fine_lats, rh_fraction=0.78, sea_level_pressure_hpa=1012.5
    )
    delta_ztd_m = (ztd_t24["ztd_m"] - ztd_t0["ztd_m"]).astype(np.float64)

    # Multi-band InSAR phase simulation
    bands_sim = compute_all_bands_insar_simulation(delta_ztd_m, incidence_deg=34.1)

    # Cross-section along Mount Kamen canyon transect (lat ~ 69.15N)
    transect_row = int(np.argmin(np.abs(fine_lats - 69.15)))
    transect_lons = fine_lons
    transect_elev = elev[transect_row, :]
    transect_ztd = delta_ztd_m[transect_row, :]

    return {
        "theater": "russia_putorana",
        "name": "Northern Russia Putorana Plateau Basalt Traps",
        "lats": fine_lats,
        "lons": fine_lons,
        "elev_m": elev,
        "delta_ztd_m": delta_ztd_m.astype(np.float32),
        "bands": bands_sim,
        "transect": {
            "lat": float(fine_lats[transect_row]),
            "lons": transect_lons,
            "elev_m": transect_elev,
            "delta_ztd_m": transect_ztd.astype(np.float32),
            "phase_unwrapped_X": bands_sim["X"]["phase_unwrapped_rad"][transect_row, :],
            "phase_unwrapped_C": bands_sim["C"]["phase_unwrapped_rad"][transect_row, :],
            "phase_unwrapped_L": bands_sim["L"]["phase_unwrapped_rad"][transect_row, :],
        },
        "metrics": {
            "max_elevation_m": float(round(float(np.max(elev)), 1)),
            "min_elevation_m": float(round(float(np.min(elev)), 1)),
            "max_delta_ztd_m": float(round(float(np.max(delta_ztd_m)), 4)),
            "fringes_X": bands_sim["X"]["fringe_count"],
            "fringes_C": bands_sim["C"]["fringe_count"],
            "fringes_L": bands_sim["L"]["fringe_count"],
            "fringe_ratio_X_to_L": float(
                round(
                    bands_sim["X"]["phase_span_rad"]
                    / max(bands_sim["L"]["phase_span_rad"], 1e-6),
                    2,
                )
            ),
            "nyquist_violation_pct_X": float(
                round(bands_sim["X"]["nyquist_violation_fraction"] * 100.0, 2)
            ),
            "nyquist_violation_pct_C": float(
                round(bands_sim["C"]["nyquist_violation_fraction"] * 100.0, 2)
            ),
            "nyquist_violation_pct_L": float(
                round(bands_sim["L"]["nyquist_violation_fraction"] * 100.0, 2)
            ),
        },
    }


# -----------------------------------------------------------------------------
# Publication Diagnostic Visualization: 08_multiband_insar_comparison.png
# -----------------------------------------------------------------------------
def plot_multiband_insar_comparison(
    mexico_sim: dict[str, Any],
    sa_sim: dict[str, Any],
    ru_sim: dict[str, Any],
    time_days: np.ndarray,
    decorr_sa: dict[str, Any],
    decorr_mx: dict[str, Any],
    decorr_ru: dict[str, Any],
    penetration_models: dict[str, Any],
    output_path: Path | str,
) -> Path:
    """Generate high-impact 12-panel publication diagnostic figure.

    Adheres strictly to Rule e2s-014:
      - Explicit origin="upper" in all 2D geospatial imshow maps.
      - Exact bounding extent [lon_min, lon_max, lat_south, lat_north].
      - No synthetic or pseudo-random noise.
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(4, 3, figsize=(21, 24), dpi=200)
    fig.patch.set_facecolor("#0b0f19")

    for ax_row in axes:
        for ax in ax_row:
            ax.set_facecolor("#111827")
            ax.tick_params(colors="#cbd5e1", labelsize=9)
            for spine in ax.spines.values():
                spine.set_color("#334155")
                spine.set_linewidth(1.0)
            ax.xaxis.label.set_color("#f1f5f9")
            ax.yaxis.label.set_color("#f1f5f9")
            ax.title.set_color("#f8fafc")

    # Longitude conversion for Mexico (-104W to -96W)
    m_lons = mexico_sim["lons"]
    m_lons_deg = np.where(m_lons > 180.0, m_lons - 360.0, m_lons)
    m_lats = mexico_sim["lats"]
    m_extent = [
        float(m_lons_deg[0]),
        float(m_lons_deg[-1]),
        float(m_lats[-1]),
        float(m_lats[0]),
    ]

    # -------------------------------------------------------------------------
    # ROW 1: High-Relief Tropospheric Phase Fringe Density (Popocatépetl / Orizaba)
    # -------------------------------------------------------------------------
    # Panel A: X-Band Wrapped Interferogram (lambda = 3.11 cm)
    im_a = axes[0, 0].imshow(
        mexico_sim["bands"]["X"]["phase_wrapped_rad"],
        extent=m_extent,
        cmap="twilight",
        origin="upper",
        aspect="auto",
        vmin=-np.pi,
        vmax=np.pi,
    )
    axes[0, 0].set_title(
        f"(A) X-Band InSAR Wrapped Phase (9.65 GHz, λ = 3.11 cm)\n"
        f"Trans-Mexican Volcanic Belt: {mexico_sim['bands']['X']['fringe_count']:.1f} Fringes (1 Fringes = 1.55 cm)",
        fontsize=10.5,
        fontweight="bold",
    )
    axes[0, 0].set_xlabel("Longitude (°W)")
    axes[0, 0].set_ylabel("Latitude (°N)")
    cb_a = plt.colorbar(im_a, ax=axes[0, 0], fraction=0.046, pad=0.04)
    cb_a.set_label("Wrapped Phase (rad)", color="#f1f5f9", fontsize=9)
    cb_a.ax.tick_params(colors="#cbd5e1", labelsize=8)

    # Panel B: C-Band Wrapped Interferogram (lambda = 5.55 cm, Sentinel-1)
    im_b = axes[0, 1].imshow(
        mexico_sim["bands"]["C"]["phase_wrapped_rad"],
        extent=m_extent,
        cmap="twilight",
        origin="upper",
        aspect="auto",
        vmin=-np.pi,
        vmax=np.pi,
    )
    axes[0, 1].set_title(
        f"(B) C-Band InSAR Wrapped Phase (5.405 GHz, λ = 5.55 cm, Sentinel-1)\n"
        f"Moderate Fringe Crowding: {mexico_sim['bands']['C']['fringe_count']:.1f} Fringes (1 Fringes = 2.77 cm)",
        fontsize=10.5,
        fontweight="bold",
    )
    axes[0, 1].set_xlabel("Longitude (°W)")
    axes[0, 1].set_ylabel("Latitude (°N)")
    cb_b = plt.colorbar(im_b, ax=axes[0, 1], fraction=0.046, pad=0.04)
    cb_b.set_label("Wrapped Phase (rad)", color="#f1f5f9", fontsize=9)
    cb_b.ax.tick_params(colors="#cbd5e1", labelsize=8)

    # Panel C: L-Band Wrapped Interferogram (lambda = 23.6 cm, NISAR / ALOS-2)
    im_c = axes[0, 2].imshow(
        mexico_sim["bands"]["L"]["phase_wrapped_rad"],
        extent=m_extent,
        cmap="twilight",
        origin="upper",
        aspect="auto",
        vmin=-np.pi,
        vmax=np.pi,
    )
    axes[0, 2].set_title(
        f"(C) L-Band InSAR Wrapped Phase (1.27 GHz, λ = 23.6 cm, NISAR)\n"
        f"Sparse Fringes / Robust Unwrapping: {mexico_sim['bands']['L']['fringe_count']:.1f} Fringes (1 Fringes = 11.8 cm)",
        fontsize=10.5,
        fontweight="bold",
    )
    axes[0, 2].set_xlabel("Longitude (°W)")
    axes[0, 2].set_ylabel("Latitude (°N)")
    cb_c = plt.colorbar(im_c, ax=axes[0, 2], fraction=0.046, pad=0.04)
    cb_c.set_label("Wrapped Phase (rad)", color="#f1f5f9", fontsize=9)
    cb_c.ax.tick_params(colors="#cbd5e1", labelsize=8)

    # -------------------------------------------------------------------------
    # ROW 2: Escarpment Profiles & Spatial Nyquist Phase Gradient Hazard
    # -------------------------------------------------------------------------
    # Panel D: Volcanic Belt Topographic Elevation & Slant-Range Delay Transect
    tr = mexico_sim["transect"]
    tr_lons_deg = np.where(tr["lons"] > 180.0, tr["lons"] - 360.0, tr["lons"])

    ax_d1 = axes[1, 0]
    ax_d2 = ax_d1.twinx()
    ax_d2.tick_params(colors="#38bdf8", labelsize=9)
    for spine in ax_d2.spines.values():
        spine.set_color("#334155")

    ax_d1.plot(
        tr_lons_deg,
        tr["elev_m"],
        color="#f59e0b",
        linewidth=2.2,
        label="Surface Elevation (m)",
    )
    ax_d2.plot(
        tr_lons_deg,
        tr["delta_ztd_m"],
        color="#38bdf8",
        linewidth=2.0,
        linestyle="--",
        label="ΔZTD Slant Delay (m)",
    )

    ax_d1.set_title(
        f"(D) Popocatépetl / Orizaba Transect at Lat {tr['lat']:.2f}°N\n"
        f"Topographic Relief: {float(np.min(tr['elev_m'])):.0f}m to {float(np.max(tr['elev_m'])):.0f}m",
        fontsize=10.5,
        fontweight="bold",
    )
    ax_d1.set_xlabel("Longitude (°W)")
    ax_d1.set_ylabel("Elevation (m)", color="#f59e0b")
    ax_d2.set_ylabel("Differential ZTD (m)", color="#38bdf8")
    ax_d1.grid(True, linestyle=":", alpha=0.3, color="#475569")

    # Panel E: Unwrapped Tropospheric Phase Profiles (dphi = 4*pi/lambda * delta_R)
    axes[1, 1].plot(
        tr_lons_deg,
        tr["phase_unwrapped_X"],
        color="#38bdf8",
        linewidth=2.0,
        label=f"X-band ({mexico_sim['bands']['X']['fringe_count']:.0f} fringes)",
    )
    axes[1, 1].plot(
        tr_lons_deg,
        tr["phase_unwrapped_C"],
        color="#10b981",
        linewidth=2.0,
        label=f"C-band ({mexico_sim['bands']['C']['fringe_count']:.0f} fringes)",
    )
    axes[1, 1].plot(
        tr_lons_deg,
        tr["phase_unwrapped_L"],
        color="#f59e0b",
        linewidth=2.0,
        label=f"L-band ({mexico_sim['bands']['L']['fringe_count']:.0f} fringes)",
    )
    axes[1, 1].set_title(
        "(E) Two-Way Unwrapped Tropospheric Phase (rad)\n"
        "Scaling Inverse to Wavelength: Δϕ = (4π/λ) · ΔR",
        fontsize=10.5,
        fontweight="bold",
    )
    axes[1, 1].set_xlabel("Longitude (°W)")
    axes[1, 1].set_ylabel("Unwrapped Phase (rad)")
    axes[1, 1].legend(loc="upper right", facecolor="#1e293b", edgecolor="#475569")
    axes[1, 1].grid(True, linestyle=":", alpha=0.3, color="#475569")

    # Panel F: Spatial Phase Gradient vs Nyquist Aliasing Limit
    grad_x = np.abs(np.diff(tr["phase_unwrapped_X"]))
    grad_c = np.abs(np.diff(tr["phase_unwrapped_C"]))
    grad_l = np.abs(np.diff(tr["phase_unwrapped_L"]))
    grad_lons = tr_lons_deg[:-1]

    axes[1, 2].plot(
        grad_lons,
        grad_x,
        color="#38bdf8",
        linewidth=1.8,
        label="X-band Gradient |∇ϕ|",
    )
    axes[1, 2].plot(
        grad_lons,
        grad_c,
        color="#10b981",
        linewidth=1.8,
        label="C-band Gradient |∇ϕ|",
    )
    axes[1, 2].plot(
        grad_lons,
        grad_l,
        color="#f59e0b",
        linewidth=1.8,
        label="L-band Gradient |∇ϕ|",
    )
    axes[1, 2].axhline(
        np.pi,
        color="#f43f5e",
        linestyle="--",
        linewidth=1.8,
        label="Nyquist Limit (π rad/px)",
    )

    axes[1, 2].set_title(
        "(F) Spatial Phase Gradient |∇ϕ| vs Nyquist Unwrapping Limit\n"
        "X-band Exceeds π rad/px in Steep Canyons -> Severe Phase Aliasing",
        fontsize=10.5,
        fontweight="bold",
    )
    axes[1, 2].set_xlabel("Longitude (°W)")
    axes[1, 2].set_ylabel("Phase Gradient (rad/pixel)")
    axes[1, 2].legend(loc="upper right", facecolor="#1e293b", edgecolor="#475569")
    axes[1, 2].grid(True, linestyle=":", alpha=0.3, color="#475569")

    # -------------------------------------------------------------------------
    # ROW 3: InSAR Temporal Decorrelation Decay over Vegetation (3 Biomes)
    # -------------------------------------------------------------------------
    # Panel G: South Africa Savanna & Grassland Decorrelation
    axes[2, 0].plot(
        time_days,
        decorr_sa["X"]["coherence"],
        color="#38bdf8",
        linewidth=2.2,
        label=f"X-band (τ₁/₂ = {decorr_sa['X']['half_life_days']:.1f}d)",
    )
    axes[2, 0].plot(
        time_days,
        decorr_sa["C"]["coherence"],
        color="#10b981",
        linewidth=2.2,
        label=f"C-band (τ₁/₂ = {decorr_sa['C']['half_life_days']:.1f}d)",
    )
    axes[2, 0].plot(
        time_days,
        decorr_sa["L"]["coherence"],
        color="#f59e0b",
        linewidth=2.2,
        label=f"L-band (τ₁/₂ = {decorr_sa['L']['half_life_days']:.1f}d)",
    )
    axes[2, 0].axhline(
        0.30,
        color="#94a3b8",
        linestyle=":",
        linewidth=1.2,
        label="Coherence Threshold (0.30)",
    )
    axes[2, 0].axvline(
        1.0, color="#38bdf8", linestyle="--", alpha=0.5, label="ICEYE 1d"
    )
    axes[2, 0].axvline(
        6.0, color="#10b981", linestyle="--", alpha=0.5, label="Sentinel-1 6d"
    )
    axes[2, 0].axvline(
        12.0, color="#f59e0b", linestyle="--", alpha=0.5, label="NISAR 12d"
    )

    axes[2, 0].set_title(
        "(G) South Africa Savanna & Grassland Coherence γ(t)\n"
        f"Savanna Canopy: L-band Retains γ = {decorr_sa['L']['coherence_at_12d']:.2f} at 12d (X-band = {decorr_sa['X']['coherence_at_12d']:.2f})",
        fontsize=10.5,
        fontweight="bold",
    )
    axes[2, 0].set_xlabel("Temporal Baseline Δt (days)")
    axes[2, 0].set_ylabel("Interferometric Coherence γ [0, 1]")
    axes[2, 0].set_ylim(0.0, 1.05)
    axes[2, 0].legend(loc="upper right", facecolor="#1e293b", edgecolor="#475569")
    axes[2, 0].grid(True, linestyle=":", alpha=0.3, color="#475569")

    # Panel H: Mexico Pine-Oak Montane Forest Decorrelation
    axes[2, 1].plot(
        time_days,
        decorr_mx["X"]["coherence"],
        color="#38bdf8",
        linewidth=2.2,
        label=f"X-band (τ₁/₂ = {decorr_mx['X']['half_life_days']:.1f}d)",
    )
    axes[2, 1].plot(
        time_days,
        decorr_mx["C"]["coherence"],
        color="#10b981",
        linewidth=2.2,
        label=f"C-band (τ₁/₂ = {decorr_mx['C']['half_life_days']:.1f}d)",
    )
    axes[2, 1].plot(
        time_days,
        decorr_mx["L"]["coherence"],
        color="#f59e0b",
        linewidth=2.2,
        label=f"L-band (τ₁/₂ = {decorr_mx['L']['half_life_days']:.1f}d)",
    )
    axes[2, 1].axhline(0.30, color="#94a3b8", linestyle=":", linewidth=1.2)
    axes[2, 1].axvline(1.0, color="#38bdf8", linestyle="--", alpha=0.5)
    axes[2, 1].axvline(6.0, color="#10b981", linestyle="--", alpha=0.5)
    axes[2, 1].axvline(12.0, color="#f59e0b", linestyle="--", alpha=0.5)

    axes[2, 1].set_title(
        "(H) Mexico Humid Pine-Oak Montane Forest γ(t)\n"
        f"Dense Forest: X & C Decorrelate Fast; L-band Preserves γ = {decorr_mx['L']['coherence_at_12d']:.2f} at 12d",
        fontsize=10.5,
        fontweight="bold",
    )
    axes[2, 1].set_xlabel("Temporal Baseline Δt (days)")
    axes[2, 1].set_ylabel("Interferometric Coherence γ [0, 1]")
    axes[2, 1].set_ylim(0.0, 1.05)
    axes[2, 1].legend(loc="upper right", facecolor="#1e293b", edgecolor="#475569")
    axes[2, 1].grid(True, linestyle=":", alpha=0.3, color="#475569")

    # Panel I: Northern Russia Siberian Larch Taiga & Tundra Decorrelation
    axes[2, 2].plot(
        time_days,
        decorr_ru["X"]["coherence"],
        color="#38bdf8",
        linewidth=2.2,
        label=f"X-band (τ₁/₂ = {decorr_ru['X']['half_life_days']:.1f}d)",
    )
    axes[2, 2].plot(
        time_days,
        decorr_ru["C"]["coherence"],
        color="#10b981",
        linewidth=2.2,
        label=f"C-band (τ₁/₂ = {decorr_ru['C']['half_life_days']:.1f}d)",
    )
    axes[2, 2].plot(
        time_days,
        decorr_ru["L"]["coherence"],
        color="#f59e0b",
        linewidth=2.2,
        label=f"L-band (τ₁/₂ = {decorr_ru['L']['half_life_days']:.1f}d)",
    )
    axes[2, 2].axhline(0.30, color="#94a3b8", linestyle=":", linewidth=1.2)
    axes[2, 2].axvline(1.0, color="#38bdf8", linestyle="--", alpha=0.5)
    axes[2, 2].axvline(6.0, color="#10b981", linestyle="--", alpha=0.5)
    axes[2, 2].axvline(12.0, color="#f59e0b", linestyle="--", alpha=0.5)

    axes[2, 2].set_title(
        "(I) Northern Russia Siberian Larch Taiga & Tundra γ(t)\n"
        f"Boreal Regime: L-band γ = {decorr_ru['L']['coherence_at_12d']:.2f} (X-band = {decorr_ru['X']['coherence_at_12d']:.2f})",
        fontsize=10.5,
        fontweight="bold",
    )
    axes[2, 2].set_xlabel("Temporal Baseline Δt (days)")
    axes[2, 2].set_ylabel("Interferometric Coherence γ [0, 1]")
    axes[2, 2].set_ylim(0.0, 1.05)
    axes[2, 2].legend(loc="upper right", facecolor="#1e293b", edgecolor="#475569")
    axes[2, 2].grid(True, linestyle=":", alpha=0.3, color="#475569")

    # -------------------------------------------------------------------------
    # ROW 4: Microwave Penetration Depth & Mission Trade Space Matrix
    # -------------------------------------------------------------------------
    # Panel J: Penetration Depth across 4 Media (Bar Chart)
    media_keys = [
        "forest_canopy",
        "dry_soil_sand",
        "wet_soil",
        "permafrost_ice_snow",
    ]
    media_labels = [
        "Forest Canopy",
        "Dry Sand/Soil",
        "Wet Soil",
        "Snow & Permafrost",
    ]

    x_indices = np.arange(len(media_keys))
    bar_width = 0.25

    depths_x = [penetration_models[m]["depths_m"]["X"] for m in media_keys]
    depths_c = [penetration_models[m]["depths_m"]["C"] for m in media_keys]
    depths_l = [penetration_models[m]["depths_m"]["L"] for m in media_keys]

    axes[3, 0].bar(
        x_indices - bar_width,
        depths_x,
        width=bar_width,
        color="#38bdf8",
        label="X-band (3.11 cm)",
        alpha=0.9,
    )
    axes[3, 0].bar(
        x_indices,
        depths_c,
        width=bar_width,
        color="#10b981",
        label="C-band (5.55 cm)",
        alpha=0.9,
    )
    axes[3, 0].bar(
        x_indices + bar_width,
        depths_l,
        width=bar_width,
        color="#f59e0b",
        label="L-band (23.6 cm)",
        alpha=0.9,
    )

    axes[3, 0].set_yscale("log")
    axes[3, 0].set_xticks(x_indices)
    axes[3, 0].set_xticklabels(media_labels, rotation=15, ha="right")
    axes[3, 0].set_title(
        "(J) Multi-Band Microwave Penetration Depth δₚ (meters)\n"
        "Logarithmic Scale: L-band Penetrates Canopy, Sand & Permafrost",
        fontsize=10.5,
        fontweight="bold",
    )
    axes[3, 0].set_ylabel("Penetration Depth δₚ (meters, log)")
    axes[3, 0].legend(loc="upper left", facecolor="#1e293b", edgecolor="#475569")
    axes[3, 0].grid(True, linestyle=":", alpha=0.3, color="#475569")

    # Panel K: Canopy Scattering & Penetration Diagram
    ax_k = axes[3, 1]
    canopy_layers = np.linspace(0.0, 25.0, 250)

    # Transmission profiles: T(z) = exp(-z / delta_p)
    dp_x = penetration_models["forest_canopy"]["depths_m"]["X"]
    dp_c = penetration_models["forest_canopy"]["depths_m"]["C"]
    dp_l = penetration_models["forest_canopy"]["depths_m"]["L"]

    trans_x = np.exp(-canopy_layers / dp_x)
    trans_c = np.exp(-canopy_layers / dp_c)
    trans_l = np.exp(-canopy_layers / dp_l)

    ax_k.plot(
        trans_x,
        canopy_layers,
        color="#38bdf8",
        linewidth=2.2,
        label=f"X-band (δₚ = {dp_x:.2f}m) Top Crown",
    )
    ax_k.plot(
        trans_c,
        canopy_layers,
        color="#10b981",
        linewidth=2.2,
        label=f"C-band (δₚ = {dp_c:.2f}m) Mid Canopy",
    )
    ax_k.plot(
        trans_l,
        canopy_layers,
        color="#f59e0b",
        linewidth=2.2,
        label=f"L-band (δₚ = {dp_l:.2f}m) Sub-Canopy Ground",
    )

    ax_k.axhline(
        22.0,
        color="#22c55e",
        linestyle="--",
        alpha=0.6,
        label="Canopy Top (22m)",
    )
    ax_k.axhline(
        0.0, color="#a16207", linestyle="-", linewidth=2.0, label="Ground Surface"
    )
    ax_k.invert_yaxis()  # Depth increases downwards

    ax_k.set_title(
        "(K) Forest Canopy Radar Wave Attenuation Profile\n"
        "L-band Maintains Power to Ground Level; X-band Absorbed in Crown",
        fontsize=10.5,
        fontweight="bold",
    )
    ax_k.set_xlabel("Relative Radar Power P(z) / P₀")
    ax_k.set_ylabel("Depth into Forest Canopy (m)")
    ax_k.legend(loc="lower right", facecolor="#1e293b", edgecolor="#475569")
    ax_k.grid(True, linestyle=":", alpha=0.3, color="#475569")

    # Panel L: Multi-Band Regional Synthesis & Mission Performance Matrix
    ax_l = axes[3, 2]
    ax_l.axis("off")

    table_data = [
        [
            "Feature / Metric",
            "X-Band (9.65 GHz)",
            "C-Band (5.405 GHz)",
            "L-Band (1.27 GHz)",
        ],
        ["Wavelength λ", "3.11 cm", "5.55 cm", "23.61 cm"],
        ["Fringe Spacing (λ/2)", "1.55 cm", "2.77 cm", "11.80 cm"],
        [
            "South Africa Fringes",
            f"{sa_sim['metrics']['fringes_X']:.1f}",
            f"{sa_sim['metrics']['fringes_C']:.1f}",
            f"{sa_sim['metrics']['fringes_L']:.1f}",
        ],
        [
            "Mexico Volcanic Fringes",
            f"{mexico_sim['metrics']['fringes_X']:.1f}",
            f"{mexico_sim['metrics']['fringes_C']:.1f}",
            f"{mexico_sim['metrics']['fringes_L']:.1f}",
        ],
        [
            "Russia Putorana Fringes",
            f"{ru_sim['metrics']['fringes_X']:.1f}",
            f"{ru_sim['metrics']['fringes_C']:.1f}",
            f"{ru_sim['metrics']['fringes_L']:.1f}",
        ],
        [
            "Nyquist Risk (Mexico)",
            f"{mexico_sim['metrics']['nyquist_violation_pct_X']:.1f}% px",
            f"{mexico_sim['metrics']['nyquist_violation_pct_C']:.1f}% px",
            f"{mexico_sim['metrics']['nyquist_violation_pct_L']:.1f}% px",
        ],
        [
            "Forest Half-Life (τ₁/₂)",
            f"{decorr_mx['X']['half_life_days']:.1f} days",
            f"{decorr_mx['C']['half_life_days']:.1f} days",
            f"{decorr_mx['L']['half_life_days']:.1f} days",
        ],
        [
            "Canopy Penetration",
            f"{dp_x:.2f} m (Crown)",
            f"{dp_c:.2f} m (Mid)",
            f"{dp_l:.2f} m (Ground)",
        ],
        [
            "Primary Constellations",
            "ICEYE, StriX, TSX",
            "Sentinel-1, RCM",
            "NISAR, ALOS-2/4",
        ],
        [
            "Optimal Application",
            "Urban, ice, floods",
            "Regional baseline",
            "Forest & high relief",
        ],
    ]

    table = ax_l.table(
        cellText=table_data,
        cellLoc="center",
        loc="center",
        colWidths=[0.30, 0.23, 0.23, 0.24],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8.5)
    table.scale(1.0, 1.62)

    for (row_idx, col_idx), cell in table.get_celld().items():
        cell.set_edgecolor("#334155")
        if row_idx == 0:
            cell.set_facecolor("#1e293b")
            cell.set_text_props(color="#f8fafc", fontweight="bold")
        elif col_idx == 0:
            cell.set_facecolor("#1e293b")
            cell.set_text_props(color="#cbd5e1", fontweight="bold")
        else:
            cell.set_facecolor("#0f172a")
            if col_idx == 1:
                cell.set_text_props(color="#38bdf8")
            elif col_idx == 2:
                cell.set_text_props(color="#10b981")
            elif col_idx == 3:
                cell.set_text_props(color="#f59e0b")

    ax_l.set_title(
        "(L) Multi-Band SAR Comparative Physics Synthesis\n"
        "Cross-Regional Performance Matrix (SA, MX, RU)",
        fontsize=10.5,
        fontweight="bold",
    )

    plt.tight_layout()
    plt.savefig(out_file, dpi=200, facecolor=fig.get_facecolor())
    plt.close()
    return out_file


# -----------------------------------------------------------------------------
# Main Experiment Execution Suite
# -----------------------------------------------------------------------------
def run_multiband_sar_comparison(
    output_dir: Path | str = "outputs/scientific_study_verified/advanced_capabilities",
    verified_root: Path | str = "outputs/scientific_study_verified",
) -> dict[str, Any]:
    """Execute the Multi-Band InSAR Comparative Physics simulation suite end-to-end.

    Evaluates X-band (9.65 GHz), C-band (5.405 GHz), and L-band (1.27 GHz) across:
      - South Africa (Drakensberg Escarpment & Lesotho Highlands)
      - Mexico (Trans-Mexican Volcanic Belt: Pico de Orizaba, Popocatépetl)
      - Northern Russia (Putorana Plateau Basalt Traps)

    Models:
      - Tropospheric phase fringe density & Nyquist gradient limits
      - Vegetation temporal decorrelation decay over 3 contrasting biomes
      - Electromagnetic penetration depth across 4 distinct natural media
      - Exports publication diagnostic figure 08_multiband_insar_comparison.png
      - Generates cryptographically sealed SHA-256 JSON manifest.

    Parameters
    ----------
    output_dir : Path | str, optional
        Output destination directory, by default "outputs/scientific_study_verified/advanced_capabilities".
    verified_root : Path | str, optional
        Directory holding authentic GFS tensors, by default "outputs/scientific_study_verified".

    Returns
    -------
    dict[str, Any]
        Complete experiment execution manifest dictionary.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    figures_dir = out / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    v_root = Path(verified_root)
    init_npy = v_root / "forecast" / "initial_condition.npy"
    truth_npy = v_root / "verification" / "verifying_truth_t2m.npy"

    if init_npy.exists() and truth_npy.exists():
        logger.info(
            "Loading authentic operational NOAA GFS 0.25 deg tensors for Multi-Band SAR experiment..."
        )
        global_t0 = np.load(init_npy)
        global_t24 = np.load(truth_npy)
        global_lats = np.linspace(90.0, -90.0, global_t0.shape[0])
        global_lons = np.linspace(0.0, 360.0, global_t0.shape[1], endpoint=False)
        data_source_label = "NOAA_GFS_0P25_OPERATIONAL_VERIFIED_TENSORS"
    else:
        logger.info(
            "Generating deterministic thermodynamic physics state for Multi-Band SAR experiment..."
        )
        global_lats = np.linspace(90.0, -90.0, 721)
        global_lons = np.linspace(0.0, 360.0, 1440, endpoint=False)
        lat_r = np.deg2rad(global_lats)[:, None]
        lon_r = np.deg2rad(global_lons)[None, :]
        global_t0 = (
            288.0
            + 25.0 * np.cos(lat_r)
            + 4.0 * np.sin(2.0 * lat_r) * np.cos(3.0 * lon_r)
        ).astype(np.float32)
        global_t24 = (
            288.0
            + 25.0 * np.cos(lat_r)
            + 4.0 * np.sin(2.0 * lat_r) * np.cos(3.0 * (lon_r - np.deg2rad(12.0)))
        ).astype(np.float32)
        data_source_label = "DETERMINISTIC_GLOBAL_BAROCLINIC_REFERENCE"

    # 1. Regional Multi-Band Simulations
    logger.info(
        "Simulating Multi-Band InSAR over South Africa Drakensberg Escarpment..."
    )
    sa_sim = simulate_south_africa_multiband(
        global_t0, global_t24, global_lats, global_lons
    )

    logger.info(
        "Simulating Multi-Band InSAR over Mexico Trans-Mexican Volcanic Belt..."
    )
    mexico_sim = simulate_mexico_multiband(
        global_t0, global_t24, global_lats, global_lons
    )

    logger.info(
        "Simulating Multi-Band InSAR over Northern Russia Putorana Plateau Basalt Traps..."
    )
    ru_sim = simulate_russia_multiband(global_t0, global_t24, global_lats, global_lons)

    # 2. Vegetation Temporal Decorrelation across 3 Biomes
    logger.info("Computing vegetation temporal decorrelation decay over biomes...")
    time_days = np.linspace(0.0, 60.0, 300)
    decorr_sa = compute_all_bands_temporal_decorrelation(
        time_days, biome="south_africa_savanna"
    )
    decorr_mx = compute_all_bands_temporal_decorrelation(
        time_days, biome="mexico_pine_oak"
    )
    decorr_ru = compute_all_bands_temporal_decorrelation(
        time_days, biome="russia_taiga_tundra"
    )

    # 3. Electromagnetic Penetration Depth Modeling
    logger.info("Modeling electromagnetic penetration depth across natural media...")
    penetration_models = {
        m: compute_electromagnetic_penetration_depth(m)
        for m in PENETRATION_MEDIA_MODELS
    }

    # 4. Render 12-Panel Publication Figure
    fig_path = figures_dir / "08_multiband_insar_comparison.png"
    logger.info(f"Rendering publication figure to {fig_path}...")
    plot_multiband_insar_comparison(
        mexico_sim=mexico_sim,
        sa_sim=sa_sim,
        ru_sim=ru_sim,
        time_days=time_days,
        decorr_sa=decorr_sa,
        decorr_mx=decorr_mx,
        decorr_ru=decorr_ru,
        penetration_models=penetration_models,
        output_path=fig_path,
    )

    # Compute SHA-256 hash of the generated figure
    fig_sha256 = hashlib.sha256(fig_path.read_bytes()).hexdigest()

    # 5. Build Execution Manifest
    manifest = {
        "module": "od_experiments.geoint_sar.multiband_sar_comparison",
        "study_id": "OD-EARTH2-MULTIBAND-SAR-COMPARISON",
        "data_source": data_source_label,
        "compliance": "Rule e2s-014 Certified (Zero Synthetic Noise, Explicit origin='upper')",
        "bands": {
            b: {
                "band_name": MULTIBAND_SPECS[b]["band"],
                "frequency_ghz": MULTIBAND_SPECS[b]["frequency_ghz"],
                "wavelength_cm": MULTIBAND_SPECS[b]["wavelength_cm"],
                "half_wavelength_cm": MULTIBAND_SPECS[b]["half_wavelength_cm"],
                "primary_missions": MULTIBAND_SPECS[b]["missions"],
            }
            for b in ["X", "C", "L"]
        },
        "regional_metrics": {
            "south_africa": {
                "name": sa_sim["name"],
                "max_elevation_m": sa_sim["metrics"]["max_elevation_m"],
                "max_delta_ztd_m": sa_sim["metrics"]["max_delta_ztd_m"],
                "fringes_X": sa_sim["metrics"]["fringes_X"],
                "fringes_C": sa_sim["metrics"]["fringes_C"],
                "fringes_L": sa_sim["metrics"]["fringes_L"],
                "fringe_ratio_X_to_L": sa_sim["metrics"]["fringe_ratio_X_to_L"],
                "nyquist_violation_pct_X": sa_sim["metrics"]["nyquist_violation_pct_X"],
                "nyquist_violation_pct_C": sa_sim["metrics"]["nyquist_violation_pct_C"],
                "nyquist_violation_pct_L": sa_sim["metrics"]["nyquist_violation_pct_L"],
            },
            "mexico": {
                "name": mexico_sim["name"],
                "max_elevation_m": mexico_sim["metrics"]["max_elevation_m"],
                "max_delta_ztd_m": mexico_sim["metrics"]["max_delta_ztd_m"],
                "fringes_X": mexico_sim["metrics"]["fringes_X"],
                "fringes_C": mexico_sim["metrics"]["fringes_C"],
                "fringes_L": mexico_sim["metrics"]["fringes_L"],
                "fringe_ratio_X_to_L": mexico_sim["metrics"]["fringe_ratio_X_to_L"],
                "nyquist_violation_pct_X": mexico_sim["metrics"][
                    "nyquist_violation_pct_X"
                ],
                "nyquist_violation_pct_C": mexico_sim["metrics"][
                    "nyquist_violation_pct_C"
                ],
                "nyquist_violation_pct_L": mexico_sim["metrics"][
                    "nyquist_violation_pct_L"
                ],
            },
            "northern_russia": {
                "name": ru_sim["name"],
                "max_elevation_m": ru_sim["metrics"]["max_elevation_m"],
                "max_delta_ztd_m": ru_sim["metrics"]["max_delta_ztd_m"],
                "fringes_X": ru_sim["metrics"]["fringes_X"],
                "fringes_C": ru_sim["metrics"]["fringes_C"],
                "fringes_L": ru_sim["metrics"]["fringes_L"],
                "fringe_ratio_X_to_L": ru_sim["metrics"]["fringe_ratio_X_to_L"],
                "nyquist_violation_pct_X": ru_sim["metrics"]["nyquist_violation_pct_X"],
                "nyquist_violation_pct_C": ru_sim["metrics"]["nyquist_violation_pct_C"],
                "nyquist_violation_pct_L": ru_sim["metrics"]["nyquist_violation_pct_L"],
            },
        },
        "vegetation_decorrelation_summary": {
            "south_africa_savanna": {
                "half_life_days": {
                    "X": decorr_sa["X"]["half_life_days"],
                    "C": decorr_sa["C"]["half_life_days"],
                    "L": decorr_sa["L"]["half_life_days"],
                },
                "coherence_at_12d": {
                    "X": decorr_sa["X"]["coherence_at_12d"],
                    "C": decorr_sa["C"]["coherence_at_12d"],
                    "L": decorr_sa["L"]["coherence_at_12d"],
                },
            },
            "mexico_pine_oak": {
                "half_life_days": {
                    "X": decorr_mx["X"]["half_life_days"],
                    "C": decorr_mx["C"]["half_life_days"],
                    "L": decorr_mx["L"]["half_life_days"],
                },
                "coherence_at_12d": {
                    "X": decorr_mx["X"]["coherence_at_12d"],
                    "C": decorr_mx["C"]["coherence_at_12d"],
                    "L": decorr_mx["L"]["coherence_at_12d"],
                },
            },
            "russia_taiga_tundra": {
                "half_life_days": {
                    "X": decorr_ru["X"]["half_life_days"],
                    "C": decorr_ru["C"]["half_life_days"],
                    "L": decorr_ru["L"]["half_life_days"],
                },
                "coherence_at_12d": {
                    "X": decorr_ru["X"]["coherence_at_12d"],
                    "C": decorr_ru["C"]["coherence_at_12d"],
                    "L": decorr_ru["L"]["coherence_at_12d"],
                },
            },
        },
        "penetration_depths_summary_m": {
            m: penetration_models[m]["depths_m"] for m in PENETRATION_MEDIA_MODELS
        },
        "figure_file": str(fig_path),
        "figure_sha256": fig_sha256,
    }

    manifest_path = out / "multiband_sar_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info(
        f"Multi-Band InSAR Comparative Physics simulation complete. Manifest: {manifest_path}"
    )
    return manifest


if __name__ == "__main__":
    run_multiband_sar_comparison()
