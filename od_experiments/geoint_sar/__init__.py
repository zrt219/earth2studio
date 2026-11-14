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
GEOINT Weather-to-SAR Tip-and-Cue, CATALYST X-Band Tropospheric Phase Screen (APS),
and Flood/Landslide Attribution Suite (ICEYE, Synspective StriX, CATALYST).
Includes regional modules for Italy/Japan, Mexico Hidden Terrain, etc.
"""

from od_experiments.geoint_sar.brazil_terrain import (
    BRAZIL_TARGET_CITIES,
    build_brazil_orography,
    compute_amazon_deforestation_texture,
    compute_high_moisture_tropical_ztd,
    compute_pantanal_flood_pulse,
    compute_serra_do_mar_landslide_dynamics,
    compute_terrain_slope,
    generate_brazil_stac_orders,
    plot_brazil_tropical_suite,
    run_brazil_terrain_experiment,
    run_brazil_terrain_suite,
)
from od_experiments.geoint_sar.deep_geophysical_hazards import (
    GEOPHYSICAL_TARGET_LOCATIONS,
    compute_popocatepetl_mogi_inflation,
    compute_siberian_permafrost_thaw_and_crater_deformation,
    compute_witwatersrand_mining_subsidence_and_slip,
    generate_deep_geophysical_hazards_manifest,
    knothe_stope_subsidence_2d,
    okada_strike_slip_dislocation,
    plot_deep_geophysical_hazards_suite,
    run_deep_geophysical_hazards_suite,
)
from od_experiments.geoint_sar.finland_terrain import (
    FINLAND_TARGET_CITIES,
    build_finland_hydrology,
    build_finland_orography,
    compute_boreal_peatland_breathing,
    compute_finland_insar_aps_and_deformation,
    compute_lake_ice_freeze_thaw,
    compute_postglacial_uplift_rate,
    compute_subpolar_tropospheric_delay_ztd,
    generate_finland_stac_orders,
    run_finland_terrain_experiment,
    run_finland_terrain_suite,
)
from od_experiments.geoint_sar.japan_abandoned_farmland import (
    JAPAN_FARMLAND_TARGET_CITIES,
    build_japan_farmland_orography,
    compute_farmland_abandonment_and_vegetation_succession,
    compute_japan_insar_aps_correction,
    compute_japan_storm_precipitation,
    compute_saastamoinen_askne_delay_japan,
    compute_strix_coherence_and_backscatter,
    compute_terrace_levee_collapse_and_slope_failure,
    generate_japan_farmland_stac_tasking_orders,
    plot_japan_abandoned_farmland_suite,
    run_japan_abandoned_farmland_experiment,
)
from od_experiments.geoint_sar.mexico_terrain import (
    MEXICO_TARGET_CITIES,
    build_mexico_orography,
    compute_mexico_flood_and_slope_coherence,
    compute_mexico_insar_aps_correction,
    compute_orographic_precipitation_and_monsoon_forcing,
    compute_saastamoinen_askne_delay,
    generate_mexico_stac_tasking_orders,
    run_mexico_terrain_experiment,
)
from od_experiments.geoint_sar.multiband_sar_comparison import (
    BIOME_DECORRELATION_MODELS,
    C_BAND_FREQUENCY_HZ,
    C_BAND_HALF_WAVELENGTH_M,
    C_BAND_WAVELENGTH_M,
    L_BAND_FREQUENCY_HZ,
    L_BAND_HALF_WAVELENGTH_M,
    L_BAND_WAVELENGTH_M,
    MULTIBAND_SPECS,
    PENETRATION_MEDIA_MODELS,
    compute_all_bands_insar_simulation,
    compute_all_bands_temporal_decorrelation,
    compute_electromagnetic_penetration_depth,
    compute_multiband_insar_phase,
    compute_temporal_decorrelation_decay,
    run_multiband_sar_comparison,
)
from od_experiments.geoint_sar.russia_terrain import (
    RUSSIA_TARGET_CITIES,
    build_lena_river_hydrology,
    build_putorana_basalt_trap_orography,
    build_verkhoyansk_permafrost_orography,
    compute_iceye_lena_flood_backscatter,
    compute_putorana_insar_aps,
    compute_subzero_tropospheric_delay_ztd,
    compute_verkhoyansk_permafrost_insar_coherence,
    generate_russia_stac_tasking_orders,
    run_russia_terrain_experiment,
)
from od_experiments.geoint_sar.sar_geoint_engine import (
    X_BAND_FREQUENCY_HZ,
    X_BAND_WAVELENGTH_M,
    compute_flood_and_coherence_attribution,
    compute_insar_aps_fringe_correction,
    compute_tropospheric_delay_ztd,
    generate_tip_and_cue_stac_orders,
    run_geoint_sar_suite,
)
from od_experiments.geoint_sar.south_africa_terrain import (
    SOUTH_AFRICA_TARGET_CITIES,
    build_south_africa_orography,
    compute_south_africa_flood_and_coherence,
    compute_south_africa_hydrology,
    generate_south_africa_stac_orders,
    run_south_africa_terrain_experiment,
    run_south_africa_terrain_suite,
)
from od_experiments.geoint_sar.southern_italy_terrain import (
    SOUTHERN_ITALY_TARGET_CITIES,
    build_southern_italy_orography,
    compute_southern_italy_flood_and_coherence,
    compute_southern_italy_hydrology,
    compute_southern_italy_volcanotectonic_deformation,
    generate_southern_italy_stac_orders,
    plot_southern_italy_terrain_suite,
    run_southern_italy_terrain_experiment,
    run_southern_italy_terrain_suite,
)
from od_experiments.geoint_sar.vancouver_terrain import (
    VANCOUVER_TARGET_CITIES,
    build_vancouver_orography,
    compute_fraser_delta_subsidence,
    compute_vancouver_flood_and_coherence,
    compute_vancouver_hydrology,
    generate_vancouver_stac_orders,
    run_vancouver_terrain_experiment,
    run_vancouver_terrain_suite,
)

__all__ = [
    "X_BAND_FREQUENCY_HZ",
    "X_BAND_WAVELENGTH_M",
    "compute_tropospheric_delay_ztd",
    "compute_insar_aps_fringe_correction",
    "compute_flood_and_coherence_attribution",
    "generate_tip_and_cue_stac_orders",
    "run_geoint_sar_suite",
    # Mexico Hidden Terrain Suite
    "MEXICO_TARGET_CITIES",
    "build_mexico_orography",
    "compute_saastamoinen_askne_delay",
    "compute_orographic_precipitation_and_monsoon_forcing",
    "compute_mexico_insar_aps_correction",
    "compute_mexico_flood_and_slope_coherence",
    "generate_mexico_stac_tasking_orders",
    "run_mexico_terrain_experiment",
    # Northern Russia Hidden Terrain Suite
    "RUSSIA_TARGET_CITIES",
    "build_putorana_basalt_trap_orography",
    "build_verkhoyansk_permafrost_orography",
    "build_lena_river_hydrology",
    "compute_subzero_tropospheric_delay_ztd",
    "compute_putorana_insar_aps",
    "compute_verkhoyansk_permafrost_insar_coherence",
    "compute_iceye_lena_flood_backscatter",
    "generate_russia_stac_tasking_orders",
    "run_russia_terrain_experiment",
    # South Africa Hidden Terrain Suite
    "SOUTH_AFRICA_TARGET_CITIES",
    "build_south_africa_orography",
    "compute_south_africa_hydrology",
    "compute_south_africa_flood_and_coherence",
    "generate_south_africa_stac_orders",
    "run_south_africa_terrain_experiment",
    "run_south_africa_terrain_suite",
    # Southern Italy Hidden Terrain & Volcanotectonics Suite
    "SOUTHERN_ITALY_TARGET_CITIES",
    "build_southern_italy_orography",
    "compute_southern_italy_volcanotectonic_deformation",
    "compute_southern_italy_hydrology",
    "compute_southern_italy_flood_and_coherence",
    "generate_southern_italy_stac_orders",
    "plot_southern_italy_terrain_suite",
    "run_southern_italy_terrain_experiment",
    "run_southern_italy_terrain_suite",
    # Multi-Band InSAR Comparative Suite
    "C_BAND_FREQUENCY_HZ",
    "C_BAND_WAVELENGTH_M",
    "C_BAND_HALF_WAVELENGTH_M",
    "L_BAND_FREQUENCY_HZ",
    "L_BAND_WAVELENGTH_M",
    "L_BAND_HALF_WAVELENGTH_M",
    "MULTIBAND_SPECS",
    "BIOME_DECORRELATION_MODELS",
    "PENETRATION_MEDIA_MODELS",
    "compute_multiband_insar_phase",
    "compute_all_bands_insar_simulation",
    "compute_temporal_decorrelation_decay",
    "compute_all_bands_temporal_decorrelation",
    "compute_electromagnetic_penetration_depth",
    "run_multiband_sar_comparison",
    # Deep Geophysical Hazards Suite
    "GEOPHYSICAL_TARGET_LOCATIONS",
    "knothe_stope_subsidence_2d",
    "okada_strike_slip_dislocation",
    "compute_witwatersrand_mining_subsidence_and_slip",
    "compute_popocatepetl_mogi_inflation",
    "compute_siberian_permafrost_thaw_and_crater_deformation",
    "plot_deep_geophysical_hazards_suite",
    "generate_deep_geophysical_hazards_manifest",
    "run_deep_geophysical_hazards_suite",
    # Japan Abandoned Farmland Suite
    "JAPAN_FARMLAND_TARGET_CITIES",
    "build_japan_farmland_orography",
    "compute_saastamoinen_askne_delay_japan",
    "compute_japan_storm_precipitation",
    "compute_farmland_abandonment_and_vegetation_succession",
    "compute_terrace_levee_collapse_and_slope_failure",
    "compute_strix_coherence_and_backscatter",
    "compute_japan_insar_aps_correction",
    "generate_japan_farmland_stac_tasking_orders",
    "plot_japan_abandoned_farmland_suite",
    "run_japan_abandoned_farmland_experiment",
    # Vancouver Cascadia Suite
    "VANCOUVER_TARGET_CITIES",
    "build_vancouver_orography",
    "compute_fraser_delta_subsidence",
    "compute_vancouver_hydrology",
    "compute_vancouver_flood_and_coherence",
    "generate_vancouver_stac_orders",
    "run_vancouver_terrain_experiment",
    "run_vancouver_terrain_suite",
    # Brazil Tropical Dynamics Suite
    "BRAZIL_TARGET_CITIES",
    "build_brazil_orography",
    "compute_terrain_slope",
    "compute_high_moisture_tropical_ztd",
    "compute_serra_do_mar_landslide_dynamics",
    "compute_pantanal_flood_pulse",
    "compute_amazon_deforestation_texture",
    "generate_brazil_stac_orders",
    "plot_brazil_tropical_suite",
    "run_brazil_terrain_suite",
    "run_brazil_terrain_experiment",
    # Finland Hidden Terrain Suite
    "FINLAND_TARGET_CITIES",
    "build_finland_orography",
    "build_finland_hydrology",
    "compute_postglacial_uplift_rate",
    "compute_boreal_peatland_breathing",
    "compute_lake_ice_freeze_thaw",
    "compute_subpolar_tropospheric_delay_ztd",
    "compute_finland_insar_aps_and_deformation",
    "generate_finland_stac_orders",
    "run_finland_terrain_experiment",
    "run_finland_terrain_suite",
]
