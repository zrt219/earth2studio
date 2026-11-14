// SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * runsCatalog.js
 * Authoritative 3D Twin Scientific Run Catalog & High-Resolution Figure Registry.
 * Indexes all 11 scientific research runs across 4 distinct categories.
 * Strict compliance with Rule e2s-014 Scientific Integrity (0 synthetic perturbations).
 */

export const RUN_CATEGORIES = Object.freeze([
  'Baseline Pillars',
  'Hidden Terrains',
  'Multi-Band & Deep Hazards',
  'Global Synoptic Theaters'
]);

export const CATEGORY_THEMES = Object.freeze({
  'Baseline Pillars': Object.freeze({
    icon: '🏛️',
    color: '#38bdf8',
    glow: 'rgba(56, 189, 248, 0.45)',
    bg: 'rgba(56, 189, 248, 0.12)',
    border: 'rgba(56, 189, 248, 0.35)',
    label: 'Baseline Pillars'
  }),
  'Hidden Terrains': Object.freeze({
    icon: '🏔️',
    color: '#34d399',
    glow: 'rgba(52, 211, 153, 0.45)',
    bg: 'rgba(52, 211, 153, 0.12)',
    border: 'rgba(52, 211, 153, 0.35)',
    label: 'Hidden Terrains'
  }),
  'Multi-Band & Deep Hazards': Object.freeze({
    icon: '⚡',
    color: '#fbbf24',
    glow: 'rgba(251, 191, 36, 0.45)',
    bg: 'rgba(251, 191, 36, 0.12)',
    border: 'rgba(251, 191, 36, 0.35)',
    label: 'Multi-Band & Deep Hazards'
  }),
  'Global Synoptic Theaters': Object.freeze({
    icon: '🌐',
    color: '#c084fc',
    glow: 'rgba(192, 132, 252, 0.45)',
    bg: 'rgba(192, 132, 252, 0.12)',
    border: 'rgba(192, 132, 252, 0.35)',
    label: 'Global Synoptic Theaters'
  })
});

function deepFreeze(obj) {
  Object.keys(obj).forEach((prop) => {
    if (obj[prop] !== null && (typeof obj[prop] === 'object' || typeof obj[prop] === 'function') && !Object.isFrozen(obj[prop])) {
      deepFreeze(obj[prop]);
    }
  });
  return Object.freeze(obj);
}

export const RUNS_CATALOG = deepFreeze([
  {
    "run_id": "run_01_baseline_advanced_pillars",
    "run_number": 1,
    "title": "Baseline Advanced Pillars & GEOINT InSAR Foundations",
    "category": "Baseline Pillars",
    "theater_id": "po_valley_alps",
    "camera_target": {
      "lat": 45.4642,
      "lon": 9.19,
      "altitude_km": 450,
      "heading_deg": 15,
      "pitch_deg": -45
    },
    "bounds": {
      "lat_min": 44,
      "lat_max": 47,
      "lon_min": 7,
      "lon_max": 13
    },
    "target_coordinates": [
      {
        "name": "Milan / Po Valley Basin",
        "country": "Italy",
        "country_code": "IT",
        "lat": 45.4642,
        "lon": 9.19,
        "elevation_m": 120,
        "significance": "Alluvial basin with steep thermal inversion boundary and tropospheric water vapor delay gradient"
      },
      {
        "name": "Monte Rosa / Lepontine Alps",
        "country": "Italy / Switzerland",
        "country_code": "IT",
        "lat": 45.9369,
        "lon": 7.8668,
        "elevation_m": 4634,
        "significance": "Alpine high-relief orographic moisture barrier forcing Saastamoinen ZTD contrast of >0.9m"
      },
      {
        "name": "WPAC Typhoon Simulation",
        "country": "Oceanic Basin",
        "country_code": "INT",
        "lat": 18.5,
        "lon": 132,
        "elevation_m": 0,
        "significance": "Deep baroclinic tropical cyclone core tracking with 964.5 hPa central MSLP"
      }
    ],
    "physics_regime": "Multi-pillar validation covering 25-member Monte Carlo ensemble spread, automated baroclinic cyclone minimum SLP trajectory tracking, multi-model prognostic benchmark (Persistence vs FourCastNet/GraphCast), meso-beta super-resolution downscaling (0.25° to 0.05°), 3D-Var / EnKF background innovation assimilation, and ICEYE/StriX X-band InSAR Atmospheric Phase Screen (APS) fringe cancellation.",
    "satellites_and_sensors": [
      "ICEYE-X38 Spotlight (0.5m VV, Inc 28.4°)",
      "Synspective StriX-3 StripMap (3.0m VV/VH)",
      "CATALYST InSAR APS Engine (9.65 GHz, λ=3.107 cm)",
      "NOAA GFS 0.25° Thermodynamic Tensors"
    ],
    "primary_figure_name": "06_geoint_sar_aps_trifecta.png",
    "figures": [
      {
        "filename": "01_probabilistic_ensemble_spread.png",
        "title": "Monte Carlo 25-Member Ensemble Spread",
        "description": "Global and regional 2-meter temperature spread, baroclinic perturbation growth, and ensemble standard deviation.",
        "relative_path": "runs/run_01_baseline_advanced_pillars/01_probabilistic_ensemble_spread.png",
        "viewer_path": "/runs/run_01_baseline_advanced_pillars/01_probabilistic_ensemble_spread.png",
        "sha256": "d583969a32b5fa43823d6f6addc0d3fc351c4bc5cc753b94490d2593456936f0",
        "size_bytes": 238932
      },
      {
        "filename": "02_cyclone_tracking_trajectory.png",
        "title": "Deterministic Cyclone Center Tracking",
        "description": "Automated trajectory path tracking of minimum mean sea level pressure (964.5 hPa) in Western Pacific.",
        "relative_path": "runs/run_01_baseline_advanced_pillars/02_cyclone_tracking_trajectory.png",
        "viewer_path": "/runs/run_01_baseline_advanced_pillars/02_cyclone_tracking_trajectory.png",
        "sha256": "57f641ecf177a039ab75c79084ab415e1e4541fc412d611f961ca0177c436d05",
        "size_bytes": 168967
      },
      {
        "filename": "03_prognostic_model_benchmark.png",
        "title": "Prognostic AI Model Performance Benchmark",
        "description": "Global RMSE, ACC, and spatial spectral energy retention comparing Earth-2 pipelines against climatology.",
        "relative_path": "runs/run_01_baseline_advanced_pillars/03_prognostic_model_benchmark.png",
        "viewer_path": "/runs/run_01_baseline_advanced_pillars/03_prognostic_model_benchmark.png",
        "sha256": "d59b8ca63be3c6e02783302d5602b57f74ca0570860871dd18706b7b5442149d",
        "size_bytes": 94990
      },
      {
        "filename": "04_mesoscale_super_resolution.png",
        "title": "Meso-Beta Super-Resolution Downscaling",
        "description": "Physics-conditioned downscaling from 0.25° synoptic grids to 0.05° high-resolution boundary layer fields.",
        "relative_path": "runs/run_01_baseline_advanced_pillars/04_mesoscale_super_resolution.png",
        "viewer_path": "/runs/run_01_baseline_advanced_pillars/04_mesoscale_super_resolution.png",
        "sha256": "dac5e030782e19bb1c7f768054ef29471ea6ad4a5eff356e84aa1925919f8ecb",
        "size_bytes": 80132
      },
      {
        "filename": "05_data_assimilation_increment.png",
        "title": "Data Assimilation Innovation & Increments",
        "description": "3D-Var and localized EnKF analysis increments showing thermodynamic tensor updates prior to forecast integration.",
        "relative_path": "runs/run_01_baseline_advanced_pillars/05_data_assimilation_increment.png",
        "viewer_path": "/runs/run_01_baseline_advanced_pillars/05_data_assimilation_increment.png",
        "sha256": "a370751fc32ce1bd3c16b1a8c95f9422aa14e3979d3efe729ea1670dabbfb012",
        "size_bytes": 115359
      },
      {
        "filename": "06_geoint_sar_aps_trifecta.png",
        "title": "GEOINT InSAR Atmospheric Phase Screen (APS) Trifecta",
        "description": "Integration of ICEYE spotlight SAR, StriX coherent change detection, and CATALYST APS removing 12.2 fringes (98.73% RMSE reduction).",
        "relative_path": "runs/run_01_baseline_advanced_pillars/06_geoint_sar_aps_trifecta.png",
        "viewer_path": "/runs/run_01_baseline_advanced_pillars/06_geoint_sar_aps_trifecta.png",
        "sha256": "037d6d292aed8c58dab734e48455eba76dc68468aec5784a134a013c42ac5a59",
        "size_bytes": 2892079
      }
    ],
    "artifacts": [
      {
        "filename": "advanced_capabilities_manifest.json",
        "type": "manifest",
        "relative_path": "runs/run_01_baseline_advanced_pillars/advanced_capabilities_manifest.json",
        "viewer_path": "/runs/run_01_baseline_advanced_pillars/advanced_capabilities_manifest.json",
        "sha256": "ea9a5a626bc9ae46aca352ef4fb062d7a0befaba55f54d949a272b0a71412019",
        "size_bytes": 5664
      },
      {
        "filename": "geoint_sar_manifest.json",
        "type": "manifest",
        "relative_path": "runs/run_01_baseline_advanced_pillars/geoint_sar_manifest.json",
        "viewer_path": "/runs/run_01_baseline_advanced_pillars/geoint_sar_manifest.json",
        "sha256": "03bec26159d87049b3da51cb59e91faaf5242d25f1dd639ca716c225d5ffa844",
        "size_bytes": 2772
      },
      {
        "filename": "stac_tasking_orders.geojson",
        "type": "stac_orders",
        "relative_path": "runs/run_01_baseline_advanced_pillars/stac_tasking_orders.geojson",
        "viewer_path": "/runs/run_01_baseline_advanced_pillars/stac_tasking_orders.geojson",
        "sha256": "3fecc24808fad6b7e6e1631b40742b129fc84a8817a43088bc75f71fd0d47035",
        "size_bytes": 4767
      }
    ],
    "metrics": {
      "ensemble_members": 25,
      "min_cyclone_mslp_hpa": 964.5,
      "downscaling_resolution_deg": 0.05,
      "aps_fringes_removed": 12.2,
      "aps_rmse_reduction_pct": 98.73,
      "uncorrected_rmse_rad": 14.78,
      "corrected_rmse_rad": 0.19
    },
    "primary_figure": {
      "filename": "06_geoint_sar_aps_trifecta.png",
      "title": "GEOINT InSAR Atmospheric Phase Screen (APS) Trifecta",
      "description": "Integration of ICEYE spotlight SAR, StriX coherent change detection, and CATALYST APS removing 12.2 fringes (98.73% RMSE reduction).",
      "relative_path": "runs/run_01_baseline_advanced_pillars/06_geoint_sar_aps_trifecta.png",
      "viewer_path": "/runs/run_01_baseline_advanced_pillars/06_geoint_sar_aps_trifecta.png",
      "sha256": "037d6d292aed8c58dab734e48455eba76dc68468aec5784a134a013c42ac5a59",
      "size_bytes": 2892079
    },
    "camera_distance": 8.5
  },
  {
    "run_id": "run_02_mexico_hidden_terrain",
    "run_number": 2,
    "title": "Mexico Hidden Terrain GEOINT: Copper Canyon & Popocatépetl",
    "category": "Hidden Terrains",
    "theater_id": "mexico_copper_canyon",
    "camera_target": {
      "lat": 27.5,
      "lon": -107.5,
      "altitude_km": 350,
      "heading_deg": 25,
      "pitch_deg": -50
    },
    "bounds": {
      "lat_min": 18,
      "lat_max": 30,
      "lon_min": -110,
      "lon_max": -97
    },
    "target_coordinates": [
      {
        "name": "Barrancas del Cobre / Copper Canyon",
        "country": "Mexico",
        "country_code": "MX",
        "lat": 27.5,
        "lon": -107.5,
        "elevation_m": 2400,
        "significance": "Deep volcanic plateau canyon system with 1800m vertical relief and steep thermal inversions"
      },
      {
        "name": "Creel Canyon Rim",
        "country": "Mexico",
        "country_code": "MX",
        "lat": 27.75,
        "lon": -107.63,
        "elevation_m": 2340,
        "significance": "High-altitude plateau rim reference for dry hydrostatic delay"
      },
      {
        "name": "Batopilas Canyon Floor",
        "country": "Mexico",
        "country_code": "MX",
        "lat": 27.03,
        "lon": -107.74,
        "elevation_m": 580,
        "significance": "Subtropical canyon bottom with trapped high moisture troposphere"
      },
      {
        "name": "Popocatépetl Volcanic Summit",
        "country": "Mexico",
        "country_code": "MX",
        "lat": 19.0228,
        "lon": -98.6278,
        "elevation_m": 5426,
        "significance": "Active stratovolcano with summit magma reservoir inflation and steep ash flanks"
      }
    ],
    "physics_regime": "Topographically coupled InSAR phase delay modeling in ultra-deep canyon relief (>1800m vertical gradients) and active stratovolcanic inflation. CATALYST X-Band APS correction accurately isolates true ground motion from intense orographic water vapor gradients across the Sierra Madre Occidental.",
    "satellites_and_sensors": [
      "ICEYE-X38 Spotlight (0.5m VV, Ascending, Inc 28.4°)",
      "Synspective StriX-3 StripMap (3.0m VV/VH)",
      "CATALYST InSAR APS Engine (9.65 GHz, λ=3.107 cm)"
    ],
    "primary_figure_name": "07_mexico_hidden_terrain_geoint.png",
    "figures": [
      {
        "filename": "07_mexico_hidden_terrain_geoint.png",
        "title": "Mexico Hidden Terrain 6-Panel Diagnostic",
        "description": "High-resolution DEM, raw wrapped InSAR interferogram, synthetic GFS atmospheric phase screen, corrected unwrapped interferogram, coherence map, and STAC tasking footprints.",
        "relative_path": "runs/run_02_mexico_hidden_terrain/07_mexico_hidden_terrain_geoint.png",
        "viewer_path": "/runs/run_02_mexico_hidden_terrain/07_mexico_hidden_terrain_geoint.png",
        "sha256": "574b8124acbdf0fc7b6038d7ded274ae05be3e85ba9eaf0c1b8a11d571ba3ca2",
        "size_bytes": 641316
      }
    ],
    "artifacts": [
      {
        "filename": "mexico_terrain_manifest.json",
        "type": "manifest",
        "relative_path": "runs/run_02_mexico_hidden_terrain/mexico_terrain_manifest.json",
        "viewer_path": "/runs/run_02_mexico_hidden_terrain/mexico_terrain_manifest.json",
        "sha256": "19cc9ed90163cefc05a6bf4dc1a5e8f5aaad3881973d9faf5dcc7538bdc43ad6",
        "size_bytes": 7224
      },
      {
        "filename": "mexico_stac_tasking_orders.geojson",
        "type": "stac_orders",
        "relative_path": "runs/run_02_mexico_hidden_terrain/mexico_stac_tasking_orders.geojson",
        "viewer_path": "/runs/run_02_mexico_hidden_terrain/mexico_stac_tasking_orders.geojson",
        "sha256": "7adad42c640581efc82543cb4cfe991332417b851ee39cafc0179c16f24b0788",
        "size_bytes": 6762
      }
    ],
    "metrics": {
      "max_vertical_relief_m": 1820,
      "aps_fringes_removed": 11.4,
      "aps_rmse_reduction_pct": 98.65,
      "stac_orders_count": 4
    },
    "primary_figure": {
      "filename": "07_mexico_hidden_terrain_geoint.png",
      "title": "Mexico Hidden Terrain 6-Panel Diagnostic",
      "description": "High-resolution DEM, raw wrapped InSAR interferogram, synthetic GFS atmospheric phase screen, corrected unwrapped interferogram, coherence map, and STAC tasking footprints.",
      "relative_path": "runs/run_02_mexico_hidden_terrain/07_mexico_hidden_terrain_geoint.png",
      "viewer_path": "/runs/run_02_mexico_hidden_terrain/07_mexico_hidden_terrain_geoint.png",
      "sha256": "574b8124acbdf0fc7b6038d7ded274ae05be3e85ba9eaf0c1b8a11d571ba3ca2",
      "size_bytes": 641316
    },
    "camera_distance": 8.5
  },
  {
    "run_id": "run_03_northern_russia_terrain",
    "run_number": 3,
    "title": "Northern Russia Hidden Terrain GEOINT: Putorana, Verkhoyansk & Lena River",
    "category": "Hidden Terrains",
    "theater_id": "putorana_russia",
    "camera_target": {
      "lat": 69,
      "lon": 93,
      "altitude_km": 400,
      "heading_deg": 0,
      "pitch_deg": -45
    },
    "bounds": {
      "lat_min": 62,
      "lat_max": 72,
      "lon_min": 88,
      "lon_max": 136
    },
    "target_coordinates": [
      {
        "name": "Putorana Plateau Basalt Traps",
        "country": "Russia",
        "country_code": "RU",
        "lat": 69,
        "lon": 93,
        "elevation_m": 1700,
        "significance": "Stepped flood basalt trap staircases and deep sub-Arctic fjord canyons"
      },
      {
        "name": "Batagaika Megaslump / Verkhoyansk",
        "country": "Russia",
        "country_code": "RU",
        "lat": 67.58,
        "lon": 134.77,
        "elevation_m": 305,
        "significance": "Rapidly expanding retrogressive thaw slump in continuous ice-rich Yedoma permafrost"
      },
      {
        "name": "Lena River Ice-Jam Corridor / Yakutsk",
        "country": "Russia",
        "country_code": "RU",
        "lat": 62.03,
        "lon": 129.73,
        "elevation_m": 95,
        "significance": "Major Arctic river break-up with ice jams, river stage surges, and floodplain inundation"
      }
    ],
    "physics_regime": "Cryospheric SAR scattering and permafrost geomechanics. Combines Stefan one-dimensional active-layer thaw subsidence, specular forward scatter on frozen and flooded Arctic river ice corridors, and dry polar Saastamoinen atmospheric phase corrections.",
    "satellites_and_sensors": [
      "ICEYE-X38 Spotlight (0.5m VV, Descending)",
      "Synspective StriX-3 StripMap (3.0m VV)",
      "CATALYST Polar InSAR APS Engine"
    ],
    "primary_figure_name": "06_russia_hidden_terrain_geoint.png",
    "figures": [
      {
        "filename": "06_russia_hidden_terrain_geoint.png",
        "title": "Northern Russia Hidden Terrain 6-Panel Diagnostic",
        "description": "Putorana basalt relief, Verkhoyansk permafrost thaw displacement field, Lena River ice classification, and CATALYST polar APS correction.",
        "relative_path": "runs/run_03_northern_russia_terrain/06_russia_hidden_terrain_geoint.png",
        "viewer_path": "/runs/run_03_northern_russia_terrain/06_russia_hidden_terrain_geoint.png",
        "sha256": "9179ab67ade0c3737b15e9d3b627c260f9a1bfc143fb775e905af463178e0a74",
        "size_bytes": 465017
      }
    ],
    "artifacts": [
      {
        "filename": "russia_terrain_manifest.json",
        "type": "manifest",
        "relative_path": "runs/run_03_northern_russia_terrain/russia_terrain_manifest.json",
        "viewer_path": "/runs/run_03_northern_russia_terrain/russia_terrain_manifest.json",
        "sha256": "e36688d0904d544176e3888ea26fb98b9a808bed43af34e2a4d3943fbeb307d5",
        "size_bytes": 2200
      },
      {
        "filename": "stac_tasking_orders_russia.geojson",
        "type": "stac_orders",
        "relative_path": "runs/run_03_northern_russia_terrain/stac_tasking_orders_russia.geojson",
        "viewer_path": "/runs/run_03_northern_russia_terrain/stac_tasking_orders_russia.geojson",
        "sha256": "3a6d5762cc3f726cad8b384232559e2666c6d57cb434ce2cfd418801111ef8f1",
        "size_bytes": 6560
      }
    ],
    "metrics": {
      "permafrost_active_layer_thaw_cm": 3.8,
      "aps_fringes_removed": 8.9,
      "aps_rmse_reduction_pct": 98.42,
      "stac_orders_count": 4
    },
    "primary_figure": {
      "filename": "06_russia_hidden_terrain_geoint.png",
      "title": "Northern Russia Hidden Terrain 6-Panel Diagnostic",
      "description": "Putorana basalt relief, Verkhoyansk permafrost thaw displacement field, Lena River ice classification, and CATALYST polar APS correction.",
      "relative_path": "runs/run_03_northern_russia_terrain/06_russia_hidden_terrain_geoint.png",
      "viewer_path": "/runs/run_03_northern_russia_terrain/06_russia_hidden_terrain_geoint.png",
      "sha256": "9179ab67ade0c3737b15e9d3b627c260f9a1bfc143fb775e905af463178e0a74",
      "size_bytes": 465017
    },
    "camera_distance": 8.5
  },
  {
    "run_id": "run_04_south_africa_terrain",
    "run_number": 4,
    "title": "South Africa Hidden Terrain: Drakensberg Escarpment & Tugela Basin",
    "category": "Hidden Terrains",
    "theater_id": "south_africa_drakensberg",
    "camera_target": {
      "lat": -29.4686,
      "lon": 29.2694,
      "altitude_km": 400,
      "heading_deg": 330,
      "pitch_deg": -50
    },
    "bounds": {
      "lat_min": -35,
      "lat_max": -26,
      "lon_min": 18,
      "lon_max": 33
    },
    "target_coordinates": [
      {
        "name": "Thabana Ntlenyana (Lesotho Highest Summit)",
        "country": "Lesotho",
        "country_code": "LS",
        "lat": -29.4686,
        "lon": 29.2694,
        "elevation_m": 3482,
        "significance": "High-altitude basalt plateau with extreme dry hydrostatic delay contrast"
      },
      {
        "name": "Mont-aux-Sources / Amphitheatre",
        "country": "South Africa",
        "country_code": "ZA",
        "lat": -28.7561,
        "lon": 28.8833,
        "elevation_m": 3282,
        "significance": "1200m vertical basalt sheer face triggering intense maritime Indian Ocean convective uplift"
      },
      {
        "name": "Durban / eThekwini Coastal Plain",
        "country": "South Africa",
        "country_code": "ZA",
        "lat": -29.8587,
        "lon": 31.0218,
        "elevation_m": 15,
        "significance": "Subtropical coastal zone prone to cut-off low flooding and intense wet tropospheric delay"
      },
      {
        "name": "Tugela River Mouth",
        "country": "South Africa",
        "country_code": "ZA",
        "lat": -29.2239,
        "lon": 31.5033,
        "elevation_m": 5,
        "significance": "Estuarine wetland flood monitoring zone with specular low radar backscatter"
      }
    ],
    "physics_regime": "High-gradient orographic InSAR tropospheric phase screen removal across the Great Escarpment (sea level to 3482m elevation over 150 km). Saastamoinen integration on NOAA GFS 0.25° thermodynamic profiles removes massive phase ramps while preserving slope stability signals.",
    "satellites_and_sensors": [
      "ICEYE-X38 Spotlight (0.5m VV, Ascending, Inc 28.4°)",
      "Synspective StriX-3 StripMap (3.0m VV)",
      "CATALYST InSAR APS Engine (9.65 GHz, λ=3.107 cm)"
    ],
    "primary_figure_name": "07_geoint_south_africa_hidden_terrain.png",
    "figures": [
      {
        "filename": "07_geoint_south_africa_hidden_terrain.png",
        "title": "South Africa Hidden Terrain 6-Panel Diagnostic",
        "description": "Drakensberg orography, uncorrected InSAR phase fringes, GFS Saastamoinen ZTD field, corrected interferogram, flood inundation mask, and STAC footprints.",
        "relative_path": "runs/run_04_south_africa_terrain/07_geoint_south_africa_hidden_terrain.png",
        "viewer_path": "/runs/run_04_south_africa_terrain/07_geoint_south_africa_hidden_terrain.png",
        "sha256": "85fdcc20f5e960412a30a7fc8586771a64497b0bd29d65d0210d71da9a2b4bc6",
        "size_bytes": 3378746
      }
    ],
    "artifacts": [
      {
        "filename": "geoint_south_africa_manifest.json",
        "type": "manifest",
        "relative_path": "runs/run_04_south_africa_terrain/geoint_south_africa_manifest.json",
        "viewer_path": "/runs/run_04_south_africa_terrain/geoint_south_africa_manifest.json",
        "sha256": "aadded104574d1cc072543ce947f1a2f2a3e9a48a5ad9430126807b34afc627f",
        "size_bytes": 3654
      },
      {
        "filename": "stac_south_africa_tasking_orders.geojson",
        "type": "stac_orders",
        "relative_path": "runs/run_04_south_africa_terrain/stac_south_africa_tasking_orders.geojson",
        "viewer_path": "/runs/run_04_south_africa_terrain/stac_south_africa_tasking_orders.geojson",
        "sha256": "61f6e276b2e427b2e55443093aa319e1271dedbe38d388066ec4157962dea369",
        "size_bytes": 6833
      }
    ],
    "metrics": {
      "elevation_span_m": 3477,
      "aps_fringes_removed": 13.8,
      "aps_rmse_reduction_pct": 98.92,
      "flood_inundation_area_km2": 42.8,
      "stac_orders_count": 4
    },
    "primary_figure": {
      "filename": "07_geoint_south_africa_hidden_terrain.png",
      "title": "South Africa Hidden Terrain 6-Panel Diagnostic",
      "description": "Drakensberg orography, uncorrected InSAR phase fringes, GFS Saastamoinen ZTD field, corrected interferogram, flood inundation mask, and STAC footprints.",
      "relative_path": "runs/run_04_south_africa_terrain/07_geoint_south_africa_hidden_terrain.png",
      "viewer_path": "/runs/run_04_south_africa_terrain/07_geoint_south_africa_hidden_terrain.png",
      "sha256": "85fdcc20f5e960412a30a7fc8586771a64497b0bd29d65d0210d71da9a2b4bc6",
      "size_bytes": 3378746
    },
    "camera_distance": 8.5
  },
  {
    "run_id": "run_05_multiband_insar_physics",
    "run_number": 5,
    "title": "Multi-Band InSAR Physical Comparison: X, C, and L Bands",
    "category": "Multi-Band & Deep Hazards",
    "theater_id": "multiband_physics",
    "camera_target": {
      "lat": 27.5,
      "lon": -107.5,
      "altitude_km": 500,
      "heading_deg": 0,
      "pitch_deg": -60
    },
    "bounds": {
      "lat_min": 18,
      "lat_max": 72,
      "lon_min": -110,
      "lon_max": 136
    },
    "target_coordinates": [
      {
        "name": "X-Band Reference (ICEYE / StriX / TerraSAR-X)",
        "country": "Multi-Mission",
        "country_code": "INT",
        "lat": 27.5,
        "lon": -107.5,
        "elevation_m": 2400,
        "significance": "Frequency 9.65 GHz, λ=3.107 cm, fringe spacing 1.553 cm; ultra-high spatial sensitivity to millimeter deformation"
      },
      {
        "name": "C-Band Reference (Sentinel-1 / Radarsat)",
        "country": "Multi-Mission",
        "country_code": "INT",
        "lat": 45.4642,
        "lon": 9.19,
        "elevation_m": 120,
        "significance": "Frequency 5.405 GHz, λ=5.547 cm, fringe spacing 2.773 cm; operational synoptic monitoring with moderate canopy penetration"
      },
      {
        "name": "L-Band Reference (ALOS-2 PALSAR / NISAR)",
        "country": "Multi-Mission",
        "country_code": "INT",
        "lat": -23.5,
        "lon": -44.5,
        "elevation_m": 1200,
        "significance": "Frequency 1.2575 GHz, λ=23.840 cm, fringe spacing 11.920 cm; deep canopy penetration and high temporal coherence in dense forests"
      }
    ],
    "physics_regime": "Rigorous electromagnetic comparison of microwave radar propagation across varying terrain, vegetative cover, and snow/ice. Analyzes canopy penetration depth, volumetric decorrelation, fringe sensitivity, and atmospheric phase screen susceptibility across 9.65 GHz, 5.405 GHz, and 1.2575 GHz.",
    "satellites_and_sensors": [
      "X-Band: ICEYE-X38 / StriX-3 / TerraSAR-X (9.65 GHz, λ=3.107 cm)",
      "C-Band: Sentinel-1 / RADARSAT Constellation (5.405 GHz, λ=5.547 cm)",
      "L-Band: ALOS-2 PALSAR-2 / NISAR (1.2575 GHz, λ=23.840 cm)"
    ],
    "primary_figure_name": "08_multiband_insar_comparison.png",
    "figures": [
      {
        "filename": "08_multiband_insar_comparison.png",
        "title": "Multi-Band InSAR Physical Comparison (X vs C vs L Band)",
        "description": "Side-by-side comparison of wrapped phase fringes, penetration depth profiles, temporal coherence decay in vegetation, and phase sensitivity curves.",
        "relative_path": "runs/run_05_multiband_insar_physics/08_multiband_insar_comparison.png",
        "viewer_path": "/runs/run_05_multiband_insar_physics/08_multiband_insar_comparison.png",
        "sha256": "289847dda97518d0eda4f77f5e9805b42fe4a366801bff0dc35a2741b1bffc5a",
        "size_bytes": 1628834
      }
    ],
    "artifacts": [
      {
        "filename": "multiband_sar_manifest.json",
        "type": "manifest",
        "relative_path": "runs/run_05_multiband_insar_physics/multiband_sar_manifest.json",
        "viewer_path": "/runs/run_05_multiband_insar_physics/multiband_sar_manifest.json",
        "sha256": "cffb512836ea76bfe67fc3d1daecf8dee0d08a1e33ef41bafd5966c14a211f09",
        "size_bytes": 3855
      }
    ],
    "metrics": {
      "x_band_freq_ghz": 9.65,
      "x_band_wavelength_cm": 3.107,
      "c_band_freq_ghz": 5.405,
      "c_band_wavelength_cm": 5.547,
      "l_band_freq_ghz": 1.2575,
      "l_band_wavelength_cm": 23.84,
      "x_band_canopy_pen_m": 0.42,
      "c_band_canopy_pen_m": 1.85,
      "l_band_canopy_pen_m": 6.7
    },
    "primary_figure": {
      "filename": "08_multiband_insar_comparison.png",
      "title": "Multi-Band InSAR Physical Comparison (X vs C vs L Band)",
      "description": "Side-by-side comparison of wrapped phase fringes, penetration depth profiles, temporal coherence decay in vegetation, and phase sensitivity curves.",
      "relative_path": "runs/run_05_multiband_insar_physics/08_multiband_insar_comparison.png",
      "viewer_path": "/runs/run_05_multiband_insar_physics/08_multiband_insar_comparison.png",
      "sha256": "289847dda97518d0eda4f77f5e9805b42fe4a366801bff0dc35a2741b1bffc5a",
      "size_bytes": 1628834
    },
    "camera_distance": 8.5
  },
  {
    "run_id": "run_06_deep_geophysical_hazards",
    "run_number": 6,
    "title": "Deep Geophysical Hazards: Mining Subsidence, Magma Chambers & Permafrost Craters",
    "category": "Multi-Band & Deep Hazards",
    "theater_id": "deep_hazards",
    "camera_target": {
      "lat": -26.435,
      "lon": 27.428,
      "altitude_km": 350,
      "heading_deg": 10,
      "pitch_deg": -50
    },
    "bounds": {
      "lat_min": -30,
      "lat_max": 70,
      "lon_min": -100,
      "lon_max": 140
    },
    "target_coordinates": [
      {
        "name": "Witwatersrand Basin / Carletonville",
        "country": "South Africa",
        "country_code": "ZA",
        "lat": -26.435,
        "lon": 27.428,
        "elevation_m": 1540,
        "significance": "World's deepest tabular gold mines (Mponeng/Savuka, depth 3.8 km) causing Knothe stope subsidence troughs and Okada fault slip"
      },
      {
        "name": "Popocatépetl Magma Chamber",
        "country": "Mexico",
        "country_code": "MX",
        "lat": 19.023,
        "lon": -98.628,
        "elevation_m": 5426,
        "significance": "Mogi point source magma inflation at 5.0 km depth generating concentric circular surface displacement"
      },
      {
        "name": "Siberian Cryovolcanic Gas Craters / Batagaika",
        "country": "Russia",
        "country_code": "RU",
        "lat": 67.58,
        "lon": 134.77,
        "elevation_m": 305,
        "significance": "Explosive methane pingo degassing and thermal permafrost thaw degradation modeled by Stefan moving boundary solutions"
      }
    ],
    "physics_regime": "Analytical and numerical modeling of deep subsurface deformation: Knothe influence function for tabular extraction subsidence, Okada rectangular dislocation for strike/dip slip faulting, Mogi point-dilatation for volcanic pressure expansion, and Stefan phase-change permafrost thaw.",
    "satellites_and_sensors": [
      "ICEYE-X38 Spotlight (0.5m VV)",
      "Synspective StriX-4 (1.0m VV)",
      "CATALYST InSAR Elastic Modeling Suite"
    ],
    "primary_figure_name": "09_deep_geophysical_hazards.png",
    "figures": [
      {
        "filename": "09_deep_geophysical_hazards.png",
        "title": "Deep Geophysical Hazards 6-Panel Suite",
        "description": "Witwatersrand Knothe subsidence profile, Okada fault dislocation fringes, Popocatépetl Mogi inflation ring, Stefan active-layer thaw displacement, and composite geohazard risk map.",
        "relative_path": "runs/run_06_deep_geophysical_hazards/09_deep_geophysical_hazards.png",
        "viewer_path": "/runs/run_06_deep_geophysical_hazards/09_deep_geophysical_hazards.png",
        "sha256": "660855c05af8545b5eb9d24a543c7721b302f96e1a5ee4d7a12c49062bef29de",
        "size_bytes": 1194294
      }
    ],
    "artifacts": [
      {
        "filename": "deep_geophysical_hazards_manifest.json",
        "type": "manifest",
        "relative_path": "runs/run_06_deep_geophysical_hazards/deep_geophysical_hazards_manifest.json",
        "viewer_path": "/runs/run_06_deep_geophysical_hazards/deep_geophysical_hazards_manifest.json",
        "sha256": "54bdf742ffd52c69a8b6cefa48663c60e66abbb4355e3990058ebc30521f5f80",
        "size_bytes": 3274
      }
    ],
    "metrics": {
      "witwatersrand_max_subsidence_cm": 6.82,
      "popocatepetl_mogi_inflation_cm": 4.15,
      "mogi_source_depth_km": 5,
      "permafrost_thaw_rate_mm_day": 1.45
    },
    "primary_figure": {
      "filename": "09_deep_geophysical_hazards.png",
      "title": "Deep Geophysical Hazards 6-Panel Suite",
      "description": "Witwatersrand Knothe subsidence profile, Okada fault dislocation fringes, Popocatépetl Mogi inflation ring, Stefan active-layer thaw displacement, and composite geohazard risk map.",
      "relative_path": "runs/run_06_deep_geophysical_hazards/09_deep_geophysical_hazards.png",
      "viewer_path": "/runs/run_06_deep_geophysical_hazards/09_deep_geophysical_hazards.png",
      "sha256": "660855c05af8545b5eb9d24a543c7721b302f96e1a5ee4d7a12c49062bef29de",
      "size_bytes": 1194294
    },
    "camera_distance": 8.5
  },
  {
    "run_id": "run_07_southern_italy_volcanotectonics",
    "run_number": 7,
    "title": "Southern Italy Hidden Terrain & Volcanotectonics: Etna, Campi Flegrei & Calabria",
    "category": "Global Synoptic Theaters",
    "theater_id": "southern_italy",
    "camera_target": {
      "lat": 37.751,
      "lon": 14.9934,
      "altitude_km": 350,
      "heading_deg": 35,
      "pitch_deg": -45
    },
    "bounds": {
      "lat_min": 36.5,
      "lat_max": 42,
      "lon_min": 12,
      "lon_max": 19
    },
    "target_coordinates": [
      {
        "name": "Mount Etna (Summit & East Flank Collapse)",
        "country": "Italy",
        "country_code": "IT",
        "lat": 37.751,
        "lon": 14.9934,
        "elevation_m": 3357,
        "significance": "Highest active stratovolcano in Europe with Pernicana fault slip and seaward sliding toward Ionian Sea (-4.54 cm LOS)"
      },
      {
        "name": "Campi Flegrei Caldera / Pozzuoli",
        "country": "Italy",
        "country_code": "IT",
        "lat": 40.8272,
        "lon": 14.1394,
        "elevation_m": 45,
        "significance": "Resurgent nested caldera exhibiting rapid bradyseismic uplift (+8.02 cm LOS) centered on Pozzuoli harbor"
      },
      {
        "name": "Calabria Crystalline Massifs (Aspromonte & Sila)",
        "country": "Italy",
        "country_code": "IT",
        "lat": 38.167,
        "lon": 15.917,
        "elevation_m": 1955,
        "significance": "Deep-seated gravitational slope deformations (DSGSD) with active creep (-3.12 cm LOS)"
      },
      {
        "name": "Apulia Karst Platform (Alta Murgia & Salento)",
        "country": "Italy",
        "country_code": "IT",
        "lat": 40.9,
        "lon": 16.5,
        "elevation_m": 450,
        "significance": "Mesozoic carbonate karst platform with doline sinkhole collapse subsidence (-2.48 cm LOS)"
      },
      {
        "name": "Catania Plain & Simeto Flood Corridor",
        "country": "Italy",
        "country_code": "IT",
        "lat": 37.45,
        "lon": 15.08,
        "elevation_m": 10,
        "significance": "Alluvial floodplain subject to flash flooding and specular radar reflection"
      }
    ],
    "physics_regime": "Active volcanotectonics and complex coastal/mountain boundary layer meteorology. Models Mogi magma source inflation, unbuttressed volcanic flank sliding, hydro-magmatic hydrothermal bradyseism, and Saastamoinen atmospheric delay gradients exceeding 0.94m from sea level to summit.",
    "satellites_and_sensors": [
      "ICEYE-X38 Spotlight (0.5m VV, Ascending, Inc 28.4°)",
      "Synspective StriX-4 Spotlight (1.0m VV)",
      "CATALYST InSAR APS Engine (9.65 GHz, λ=3.107 cm)"
    ],
    "primary_figure_name": "10_southern_italy_terrain.png",
    "figures": [
      {
        "filename": "10_southern_italy_terrain.png",
        "title": "Southern Italy Hidden Terrain & Volcanotectonics 6-Panel Diagnostic",
        "description": "DEM & tectonic faults, raw X-band interferogram with atmospheric fringes, GFS Askne-Nordius ZTD screen, corrected InSAR deformation field, StriX-4 slope decorrelation map, and STAC tasking footprints.",
        "relative_path": "runs/run_07_southern_italy_volcanotectonics/10_southern_italy_terrain.png",
        "viewer_path": "/runs/run_07_southern_italy_volcanotectonics/10_southern_italy_terrain.png",
        "sha256": "b472e6e5b20f6a5247404b6ab225bb931119a5db1ebf4ab46d7a3b20a598f2c5",
        "size_bytes": 853063
      }
    ],
    "artifacts": [
      {
        "filename": "geoint_southern_italy_manifest.json",
        "type": "manifest",
        "relative_path": "runs/run_07_southern_italy_volcanotectonics/geoint_southern_italy_manifest.json",
        "viewer_path": "/runs/run_07_southern_italy_volcanotectonics/geoint_southern_italy_manifest.json",
        "sha256": "f3fa855d72e0df29d7ea6776fce5d3939de7cb897d59cd9c06ad3e62ab2a5a7a",
        "size_bytes": 9388
      },
      {
        "filename": "stac_southern_italy_tasking_orders.geojson",
        "type": "stac_orders",
        "relative_path": "runs/run_07_southern_italy_volcanotectonics/stac_southern_italy_tasking_orders.geojson",
        "viewer_path": "/runs/run_07_southern_italy_volcanotectonics/stac_southern_italy_tasking_orders.geojson",
        "sha256": "e1a390464f40f020fef0b5e106303e45545139d5f602b4f68a8be26486c47c17",
        "size_bytes": 9117
      }
    ],
    "metrics": {
      "etna_east_flank_slip_cm": -4.54,
      "campi_flegrei_bradyseism_cm": 8.02,
      "aps_fringes_removed": 11.53,
      "aps_rmse_reduction_pct": 98.83,
      "flood_inundation_area_km2": 16.2,
      "slope_decorrelation_area_km2": 288.7,
      "stac_orders_count": 4
    },
    "primary_figure": {
      "filename": "10_southern_italy_terrain.png",
      "title": "Southern Italy Hidden Terrain & Volcanotectonics 6-Panel Diagnostic",
      "description": "DEM & tectonic faults, raw X-band interferogram with atmospheric fringes, GFS Askne-Nordius ZTD screen, corrected InSAR deformation field, StriX-4 slope decorrelation map, and STAC tasking footprints.",
      "relative_path": "runs/run_07_southern_italy_volcanotectonics/10_southern_italy_terrain.png",
      "viewer_path": "/runs/run_07_southern_italy_volcanotectonics/10_southern_italy_terrain.png",
      "sha256": "b472e6e5b20f6a5247404b6ab225bb931119a5db1ebf4ab46d7a3b20a598f2c5",
      "size_bytes": 853063
    },
    "camera_distance": 8.5
  },
  {
    "run_id": "run_08_finland_glacial_rebound_peatlands",
    "run_number": 8,
    "title": "Finland Post-Glacial Rebound, Boreal Peatlands & Lake Ice",
    "category": "Global Synoptic Theaters",
    "theater_id": "finland_rebound",
    "camera_target": {
      "lat": 63.095,
      "lon": 21.6165,
      "altitude_km": 500,
      "heading_deg": 10,
      "pitch_deg": -55
    },
    "bounds": {
      "lat_min": 59.8,
      "lat_max": 70.2,
      "lon_min": 20,
      "lon_max": 32
    },
    "target_coordinates": [
      {
        "name": "Kvarken Archipelago / Vaasa",
        "country": "Finland",
        "country_code": "FI",
        "lat": 63.095,
        "lon": 21.6165,
        "elevation_m": 12,
        "significance": "UNESCO World Heritage post-glacial land uplift hotspot (8.42 mm/yr) causing moraine emergence from Baltic Sea"
      },
      {
        "name": "Lake Saimaa Labyrinth Basin",
        "country": "Finland",
        "country_code": "FI",
        "lat": 61.25,
        "lon": 28.25,
        "elevation_m": 76,
        "significance": "Fractured bedrock lake system with candled ice sheet backscatter and shoreline uplift tilt"
      },
      {
        "name": "Lake Päijänne Basin",
        "country": "Finland",
        "country_code": "FI",
        "lat": 61.5833,
        "lon": 25.5,
        "elevation_m": 78,
        "significance": "Deep tectonic fracture lake with smooth winter ice cover and specular forward scatter"
      },
      {
        "name": "Siikaneva Boreal Mire Complex",
        "country": "Finland",
        "country_code": "FI",
        "lat": 61.8333,
        "lon": 24.1667,
        "elevation_m": 160,
        "significance": "Pristine Sphagnum peatland with seasonal hydrologic swelling and oscillation (1.75 cm breathing amplitude)"
      },
      {
        "name": "Halti Fell Summit (Lapland)",
        "country": "Finland",
        "country_code": "FI",
        "lat": 69.3083,
        "lon": 21.2792,
        "elevation_m": 1324,
        "significance": "Sub-Arctic periglacial blockfield with active frost heave and seasonal snowpack phase delay"
      }
    ],
    "physics_regime": "Fennoscandian glacial isostatic adjustment (GIA) viscoelastic relaxation, hydro-mechanical peatland 'mire breathing' oscillations governed by water table pore pressure, and dielectric phase transitions during sub-boreal freshwater lake freezing.",
    "satellites_and_sensors": [
      "ICEYE-X41 Spotlight (0.5m VV, Ascending, Inc 27.5°)",
      "Synspective StriX-3 StripMap (3.0m VV)",
      "CATALYST Sub-Arctic InSAR APS Engine"
    ],
    "primary_figure_name": "11_finland_terrain.png",
    "figures": [
      {
        "filename": "11_finland_terrain.png",
        "title": "Finland Post-Glacial Rebound & Peatlands 6-Panel Diagnostic",
        "description": "Elevation & uplift contour map, raw interferogram with sub-Arctic atmospheric delay, GFS Askne-Nordius ZTD screen, corrected land uplift / peat breathing interferogram, lake ice backscatter classification, and STAC tasking orders.",
        "relative_path": "runs/run_08_finland_glacial_rebound_peatlands/11_finland_terrain.png",
        "viewer_path": "/runs/run_08_finland_glacial_rebound_peatlands/11_finland_terrain.png",
        "sha256": "471feb8e569f87835782aa77afebf09ea5886f835f6a0aef9e1dad43f89ccd79",
        "size_bytes": 772414
      }
    ],
    "artifacts": [
      {
        "filename": "geoint_finland_manifest.json",
        "type": "manifest",
        "relative_path": "runs/run_08_finland_glacial_rebound_peatlands/geoint_finland_manifest.json",
        "viewer_path": "/runs/run_08_finland_glacial_rebound_peatlands/geoint_finland_manifest.json",
        "sha256": "e9abbec81229566c60d3722e72c95338f5d07d8bfcff49bfdc0b8977fcf84d94",
        "size_bytes": 9251
      },
      {
        "filename": "stac_finland_tasking_orders.geojson",
        "type": "stac_orders",
        "relative_path": "runs/run_08_finland_glacial_rebound_peatlands/stac_finland_tasking_orders.geojson",
        "viewer_path": "/runs/run_08_finland_glacial_rebound_peatlands/stac_finland_tasking_orders.geojson",
        "sha256": "12a4da0af6187ed132570e9e9519575b01253e32f879ca89c5e8d90ee22bfd7d",
        "size_bytes": 6066
      }
    ],
    "metrics": {
      "kvarken_uplift_rate_mm_yr": 8.42,
      "peatland_breathing_amplitude_cm": 1.75,
      "aps_fringes_removed": 9.18,
      "aps_rmse_reduction_pct": 98.67,
      "lake_ice_cover_area_km2": 4400,
      "stac_orders_count": 4
    },
    "primary_figure": {
      "filename": "11_finland_terrain.png",
      "title": "Finland Post-Glacial Rebound & Peatlands 6-Panel Diagnostic",
      "description": "Elevation & uplift contour map, raw interferogram with sub-Arctic atmospheric delay, GFS Askne-Nordius ZTD screen, corrected land uplift / peat breathing interferogram, lake ice backscatter classification, and STAC tasking orders.",
      "relative_path": "runs/run_08_finland_glacial_rebound_peatlands/11_finland_terrain.png",
      "viewer_path": "/runs/run_08_finland_glacial_rebound_peatlands/11_finland_terrain.png",
      "sha256": "471feb8e569f87835782aa77afebf09ea5886f835f6a0aef9e1dad43f89ccd79",
      "size_bytes": 772414
    },
    "camera_distance": 8.5
  },
  {
    "run_id": "run_09_japan_abandoned_farmland",
    "run_number": 9,
    "title": "Japan Abandoned Farmland & Mountain Hazard Dynamics",
    "category": "Global Synoptic Theaters",
    "theater_id": "japan_abandoned_farmland",
    "camera_target": {
      "lat": 37.3833,
      "lon": 138.8833,
      "altitude_km": 300,
      "heading_deg": 15,
      "pitch_deg": -50
    },
    "bounds": {
      "lat_min": 33,
      "lat_max": 38,
      "lon_min": 133,
      "lon_max": 140
    },
    "target_coordinates": [
      {
        "name": "Yamakoshi Terraced Rice Paddies / Nagaoka",
        "country": "Japan",
        "country_code": "JP",
        "lat": 37.3833,
        "lon": 138.8833,
        "elevation_m": 280,
        "significance": "Steep terraced mountain rice paddies affected by the 2004 Chuetsu earthquake, depopulation, and drainage degradation"
      },
      {
        "name": "Tokamachi Terraced Slopes",
        "country": "Japan",
        "country_code": "JP",
        "lat": 37.1333,
        "lon": 138.75,
        "elevation_m": 210,
        "significance": "Deep heavy-snow zone (Yukiguni) with active snow creep and wet terrace slope collapse"
      },
      {
        "name": "Iya Valley Deep Canyon & Terraces",
        "country": "Japan",
        "country_code": "JP",
        "lat": 33.8667,
        "lon": 133.8167,
        "elevation_m": 650,
        "significance": "Ultra-steep V-shaped schist gorge in Shikoku Mountains with abandoned hillside agricultural hamlets"
      },
      {
        "name": "Mount Tsurugi Summit",
        "country": "Japan",
        "country_code": "JP",
        "lat": 33.8544,
        "lon": 134.0936,
        "elevation_m": 1955,
        "significance": "Second highest peak in western Japan triggering heavy Pacific typhoon orographic rainfall"
      }
    ],
    "physics_regime": "Steep slope stability degradation following agricultural abandonment (耕作放棄地). Models failure of unmaintained stone revetments and clay-layer terrace bunds, rapid bamboo (moso-chiku) and brush encroachment causing radar volume decorrelation, and InSAR coherent change detection under torrential typhoon and snowmelt pore pressures.",
    "satellites_and_sensors": [
      "Synspective StriX-3 StripMap (3.0m VV/VH)",
      "Synspective StriX-4 Spotlight (1.0m VV)",
      "ICEYE-X38 Spotlight (0.5m VV)",
      "CATALYST High-Relief InSAR APS Engine"
    ],
    "primary_figure_name": "12_japan_abandoned_farmland.png",
    "figures": [
      {
        "filename": "12_japan_abandoned_farmland.png",
        "title": "Japan Abandoned Farmland 6-Panel Diagnostic",
        "description": "DEM & terrain slope analysis, raw wrapped InSAR phase with steep terrain fringes, GFS Askne-Nordius ZTD screen, corrected terrace displacement field, StriX-3 coherence & vegetation encroachment map, and STAC tasking orders.",
        "relative_path": "runs/run_09_japan_abandoned_farmland/12_japan_abandoned_farmland.png",
        "viewer_path": "/runs/run_09_japan_abandoned_farmland/12_japan_abandoned_farmland.png",
        "sha256": "29788b7ef4ac07a5807089f30936ab4ed858711d1dbba8a10ff1855725e38928",
        "size_bytes": 465257
      }
    ],
    "artifacts": [
      {
        "filename": "japan_abandoned_farmland_manifest.json",
        "type": "manifest",
        "relative_path": "runs/run_09_japan_abandoned_farmland/japan_abandoned_farmland_manifest.json",
        "viewer_path": "/runs/run_09_japan_abandoned_farmland/japan_abandoned_farmland_manifest.json",
        "sha256": "f0ceab1b08485a99b72951ab21e2a5e390c1cbb2b7a72ba016a65a071f9dbf7b",
        "size_bytes": 8733
      },
      {
        "filename": "stac_japan_farmland_tasking_orders.geojson",
        "type": "stac_orders",
        "relative_path": "runs/run_09_japan_abandoned_farmland/stac_japan_farmland_tasking_orders.geojson",
        "viewer_path": "/runs/run_09_japan_abandoned_farmland/stac_japan_farmland_tasking_orders.geojson",
        "sha256": "855156bd9334421bf720878886780049d9e4cf342585bf625fe2d3d61d59d427",
        "size_bytes": 8746
      }
    ],
    "metrics": {
      "max_slope_deg": 41.6,
      "aps_fringes_removed": 11.12,
      "aps_rmse_reduction_pct": 98.71,
      "abandoned_farmland_decorrelation_area_km2": 78.4,
      "stac_orders_count": 4
    },
    "primary_figure": {
      "filename": "12_japan_abandoned_farmland.png",
      "title": "Japan Abandoned Farmland 6-Panel Diagnostic",
      "description": "DEM & terrain slope analysis, raw wrapped InSAR phase with steep terrain fringes, GFS Askne-Nordius ZTD screen, corrected terrace displacement field, StriX-3 coherence & vegetation encroachment map, and STAC tasking orders.",
      "relative_path": "runs/run_09_japan_abandoned_farmland/12_japan_abandoned_farmland.png",
      "viewer_path": "/runs/run_09_japan_abandoned_farmland/12_japan_abandoned_farmland.png",
      "sha256": "29788b7ef4ac07a5807089f30936ab4ed858711d1dbba8a10ff1855725e38928",
      "size_bytes": 465257
    },
    "camera_distance": 8
  },
  {
    "run_id": "run_10_brazil_tropical_dynamics",
    "run_number": 10,
    "title": "Brazil Tropical Dynamics: Serra do Mar Escarpments & Pantanal Wetland",
    "category": "Global Synoptic Theaters",
    "theater_id": "brazil_serra_do_mar",
    "camera_target": {
      "lat": -23.76,
      "lon": -45.41,
      "altitude_km": 400,
      "heading_deg": 45,
      "pitch_deg": -50
    },
    "bounds": {
      "lat_min": -24.8,
      "lat_max": -9,
      "lon_min": -58,
      "lon_max": -41.8
    },
    "target_coordinates": [
      {
        "name": "São Sebastião Coastal Escarpment",
        "country": "Brazil",
        "country_code": "BR",
        "lat": -23.76,
        "lon": -45.41,
        "elevation_m": 15,
        "significance": "Steep coastal granitic wall (slopes >44.87°) prone to catastrophic debris flows during extreme South Atlantic Convergence Zone (SACZ) rainfall"
      },
      {
        "name": "Petrópolis Granitic Amphitheatre",
        "country": "Brazil",
        "country_code": "BR",
        "lat": -22.505,
        "lon": -43.1789,
        "elevation_m": 845,
        "significance": "High-relief mountain city in Serra dos Órgãos susceptible to rapid-onset regolith stripping and translational rock slides"
      },
      {
        "name": "Corumbá / Pantanal Basin",
        "country": "Brazil",
        "country_code": "BR",
        "lat": -19.01,
        "lon": -57.65,
        "elevation_m": 118,
        "significance": "Massive alluvial wetland basin (~150,000 km²) experiencing seasonal flood pulse dynamics and specular radar scattering"
      },
      {
        "name": "Sinop / Arc of Deforestation",
        "country": "Brazil",
        "country_code": "BR",
        "lat": -11.86,
        "lon": -55.5,
        "elevation_m": 384,
        "significance": "Amazon deforestation frontier along BR-163 with sharp radar texture contrasts between intact forest and clearcut pasture"
      }
    ],
    "physics_regime": "Tropical atmospheric thermodynamics and extreme hydrological events. Accurately simulates South Atlantic Convergence Zone (SACZ) high-moisture column delay (>2.71m ZTD), infinite slope limit equilibrium slope failure on >40° coastal escarpments, and ICEYE specular forward scatter across the world's largest continental wetland.",
    "satellites_and_sensors": [
      "ICEYE-X43 Flood Monitoring (3.0m VV)",
      "Synspective StriX-4 Spotlight (1.0m VV)",
      "CATALYST Tropical InSAR APS Engine"
    ],
    "primary_figure_name": "13_brazil_terrain.png",
    "figures": [
      {
        "filename": "13_brazil_terrain.png",
        "title": "Brazil Tropical Dynamics 6-Panel Diagnostic",
        "description": "DEM & terrain relief, uncorrected InSAR phase fringes, tropical GFS Askne-Nordius ZTD screen, corrected InSAR interferogram, Pantanal flood specular backscatter map, and STAC tasking orders.",
        "relative_path": "runs/run_10_brazil_tropical_dynamics/13_brazil_terrain.png",
        "viewer_path": "/runs/run_10_brazil_tropical_dynamics/13_brazil_terrain.png",
        "sha256": "d8a775bf2afb3bd234c80f746b401ae504a9b3515b029327eae0be8828039907",
        "size_bytes": 1516378
      }
    ],
    "artifacts": [
      {
        "filename": "brazil_terrain_manifest.json",
        "type": "manifest",
        "relative_path": "runs/run_10_brazil_tropical_dynamics/brazil_terrain_manifest.json",
        "viewer_path": "/runs/run_10_brazil_tropical_dynamics/brazil_terrain_manifest.json",
        "sha256": "6dcbfb8ab57745c264e2ded32c806b04609c65e4e9a127a01fb412c784faf827",
        "size_bytes": 9166
      },
      {
        "filename": "stac_brazil_tasking_orders.geojson",
        "type": "stac_orders",
        "relative_path": "runs/run_10_brazil_tropical_dynamics/stac_brazil_tasking_orders.geojson",
        "viewer_path": "/runs/run_10_brazil_tropical_dynamics/stac_brazil_tasking_orders.geojson",
        "sha256": "f6d4a47c9792ae52cacc806f6447ffade6fa72aa787e905e8e745b154f83653d",
        "size_bytes": 8413
      }
    ],
    "metrics": {
      "peak_escarpment_slope_deg": 44.87,
      "debris_flow_decorrelation_area_km2": 120.43,
      "pantanal_flood_inundation_area_km2": 111927.18,
      "aps_fringes_removed": 10.46,
      "aps_rmse_reduction_pct": 99.11,
      "amazon_radar_contrast_db": 5.6,
      "stac_orders_count": 6
    },
    "primary_figure": {
      "filename": "13_brazil_terrain.png",
      "title": "Brazil Tropical Dynamics 6-Panel Diagnostic",
      "description": "DEM & terrain relief, uncorrected InSAR phase fringes, tropical GFS Askne-Nordius ZTD screen, corrected InSAR interferogram, Pantanal flood specular backscatter map, and STAC tasking orders.",
      "relative_path": "runs/run_10_brazil_tropical_dynamics/13_brazil_terrain.png",
      "viewer_path": "/runs/run_10_brazil_tropical_dynamics/13_brazil_terrain.png",
      "sha256": "d8a775bf2afb3bd234c80f746b401ae504a9b3515b029327eae0be8828039907",
      "size_bytes": 1516378
    },
    "camera_distance": 10
  },
  {
    "run_id": "run_11_vancouver_cascadia_delta",
    "run_number": 11,
    "title": "Vancouver Cascadia Delta Subsidence & Coast Mountain Atmospheric Rivers",
    "category": "Global Synoptic Theaters",
    "theater_id": "vancouver_delta",
    "camera_target": {
      "lat": 49.3,
      "lon": -123.1,
      "altitude_km": 350,
      "heading_deg": 350,
      "pitch_deg": -50
    },
    "bounds": {
      "lat_min": 48.6,
      "lat_max": 50.6,
      "lon_min": -124.4,
      "lon_max": -121.6
    },
    "target_coordinates": [
      {
        "name": "Roberts Bank Superport & Deltaport",
        "country": "Canada",
        "country_code": "CA",
        "lat": 49.0194,
        "lon": -123.1583,
        "elevation_m": 2,
        "significance": "Reclaimed tidal delta causeway experiencing long-term consolidation creep and load subsidence (-2.84 mm/yr)"
      },
      {
        "name": "Richmond / Lulu Island Holocene Silt",
        "country": "Canada",
        "country_code": "CA",
        "lat": 49.1666,
        "lon": -123.1336,
        "elevation_m": 1,
        "significance": "Low-lying Holocene delta plain vulnerable to liquefaction, sea level rise, and soil compaction (-2.15 mm/yr)"
      },
      {
        "name": "Mount Garibaldi Volcanic Summit",
        "country": "Canada",
        "country_code": "CA",
        "lat": 49.8517,
        "lon": -123.0044,
        "elevation_m": 2678,
        "significance": "Cascadia volcanic arc peak triggering intense orographic precipitation and 0.81m ZTD atmospheric phase contrast"
      },
      {
        "name": "Howe Sound Fjord & Britannia Beach",
        "country": "Canada",
        "country_code": "CA",
        "lat": 49.6253,
        "lon": -123.2044,
        "elevation_m": 5,
        "significance": "Steep fjord walls prone to catastrophic rock avalanches and debris slides"
      },
      {
        "name": "Vancouver International Airport (YVR)",
        "country": "Canada",
        "country_code": "CA",
        "lat": 49.1967,
        "lon": -123.1815,
        "elevation_m": 4,
        "significance": "Sea Island critical infrastructure monitoring on compressible deltaic sediments"
      },
      {
        "name": "Sumas Prairie Floodplain (Abbotsford)",
        "country": "Canada",
        "country_code": "CA",
        "lat": 49.05,
        "lon": -122.15,
        "elevation_m": 10,
        "significance": "Historic lake bed subject to catastrophic atmospheric river inundation (November 2021 event)"
      }
    ],
    "physics_regime": "Fraser River Holocene deltaic sediment consolidation and primary Terzaghi 1D consolidation creep, coupled with extreme Pacific Atmospheric River ('Pineapple Express') water vapor transport across the steep Pacific Coast Mountains.",
    "satellites_and_sensors": [
      "ICEYE-X38 Spotlight (0.5m VV, Ascending, Inc 28.4°)",
      "Synspective StriX-3 StripMap (3.0m VV)",
      "CATALYST InSAR APS Engine (9.65 GHz, λ=3.107 cm)"
    ],
    "primary_figure_name": "14_vancouver_terrain.png",
    "figures": [
      {
        "filename": "14_vancouver_terrain.png",
        "title": "Vancouver Cascadia Delta 6-Panel Diagnostic",
        "description": "DEM & tectonic delta context, raw wrapped InSAR interferogram with atmospheric river phase delays, GFS Askne-Nordius ZTD screen, corrected InSAR delta subsidence field, flood inundation mask, and STAC tasking orders.",
        "relative_path": "runs/run_11_vancouver_cascadia_delta/14_vancouver_terrain.png",
        "viewer_path": "/runs/run_11_vancouver_cascadia_delta/14_vancouver_terrain.png",
        "sha256": "62997dd9c8905615d00a199d8931d43b0b66cd6abaeaaec74354b32b11b684d0",
        "size_bytes": 456686
      }
    ],
    "artifacts": [
      {
        "filename": "vancouver_terrain_manifest.json",
        "type": "manifest",
        "relative_path": "runs/run_11_vancouver_cascadia_delta/vancouver_terrain_manifest.json",
        "viewer_path": "/runs/run_11_vancouver_cascadia_delta/vancouver_terrain_manifest.json",
        "sha256": "0f097e0f98b2d2fecb99fe2b0bdf8c444d969e4528c0c86ac6308c52223ba735",
        "size_bytes": 9429
      },
      {
        "filename": "stac_vancouver_tasking_orders.geojson",
        "type": "stac_orders",
        "relative_path": "runs/run_11_vancouver_cascadia_delta/stac_vancouver_tasking_orders.geojson",
        "viewer_path": "/runs/run_11_vancouver_cascadia_delta/stac_vancouver_tasking_orders.geojson",
        "sha256": "4ee727dfad721d1e2f0d24f7c5166e0eac10c10e8d1ddd7e870200b2a404c497",
        "size_bytes": 7269
      }
    ],
    "metrics": {
      "roberts_bank_subsidence_mm_yr": -2.84,
      "richmond_subsidence_mm_yr": -2.15,
      "aps_fringes_removed": 10.85,
      "aps_rmse_reduction_pct": 98.88,
      "flood_inundation_area_km2": 38.6,
      "stac_orders_count": 5
    },
    "primary_figure": {
      "filename": "14_vancouver_terrain.png",
      "title": "Vancouver Cascadia Delta 6-Panel Diagnostic",
      "description": "DEM & tectonic delta context, raw wrapped InSAR interferogram with atmospheric river phase delays, GFS Askne-Nordius ZTD screen, corrected InSAR delta subsidence field, flood inundation mask, and STAC tasking orders.",
      "relative_path": "runs/run_11_vancouver_cascadia_delta/14_vancouver_terrain.png",
      "viewer_path": "/runs/run_11_vancouver_cascadia_delta/14_vancouver_terrain.png",
      "sha256": "62997dd9c8905615d00a199d8931d43b0b66cd6abaeaaec74354b32b11b684d0",
      "size_bytes": 456686
    },
    "camera_distance": 7.5
  }
]);

export function getRunCatalog() {
  return RUNS_CATALOG;
}

export function getRunById(runIdOrNumber) {
  if (runIdOrNumber === null || runIdOrNumber === undefined) return null;
  const num = Number(runIdOrNumber);
  if (!isNaN(num) && num >= 1 && num <= 11) {
    return RUNS_CATALOG.find((r) => r.run_number === num) || null;
  }
  const str = String(runIdOrNumber).trim().toLowerCase();
  return RUNS_CATALOG.find((r) => r.run_id.toLowerCase() === str || String(r.run_number) === str) || null;
}

export function getRunsByCategory(category = 'ALL') {
  if (!category || category.toUpperCase() === 'ALL') {
    return RUNS_CATALOG;
  }
  const norm = String(category).trim().toLowerCase();
  return RUNS_CATALOG.filter((r) => r.category.toLowerCase() === norm);
}

export default {
  RUN_CATEGORIES,
  CATEGORY_THEMES,
  RUNS_CATALOG,
  getRunCatalog,
  getRunById,
  getRunsByCategory
};
