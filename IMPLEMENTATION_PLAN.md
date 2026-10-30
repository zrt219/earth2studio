# OD-EARTH2-001 / EO-OBSCURA: 3D WebGL Digital Twin Upgrade Implementation Plan

**Project:** OD-EARTH2-001 / EO-OBSCURA  
**Author:** Zhane Daye  
**Affiliation:** Origin Datum — Independent Research Initiative  
**Target Application:** `viewer_app/` (Vite + Three.js)  
**Production URL:** https://viewerapp.vercel.app  

---

## 1. Executive Summary & Goals
Upgrade the 3D WebGL Digital Twin in `viewer_app/` from a single-state global atmosphere viewer into an interactive research-grade digital twin showcasing the scientific trajectory of the entire study across its three versions and 7 advanced capability pillars:
- **Version 1 (V1 - Quarantined Synthetic Leakage Audit):** Historical baseline exposing the synthetic target leakage artifact ($\hat{y} = x_0 + 0.72\Delta + \epsilon$) and contrasting synthetic vs genuine atmospheric dynamics.
- **Version 2 (V2 - Decoupled 3-Stage Persistence Baseline):** Rigorous 3-stage architecture (Forecast $\to$ Freeze $\to$ Verify) running on operational NOAA GFS $0.25^\circ$ analysis ($2.129\text{ K}$ RMSE, $\text{TAC} = 0$, $\text{ACC} = \text{null}$, AMD GPU hardware blocker).
- **Version 3 (V3 - The 7 Advanced Capability Pillars):** Full multi-capability operational suite:
  1. Massive Ensembles ($N=25$, ensemble spread $\bar{\sigma} = 0.4273\text{ K}$).
  2. Cyclone Trajectory Tracking (`WPAC_TYPHOON_SIM` 5 waypoints, 3D trajectory spline tube, intensity colormapping, cone of uncertainty).
  3. Multi-Source Ingestion (NOAA GFS, ECMWF ERA5, ARCO-ERA5 Zarr, NCEP GEFS).
  4. Prognostic Architecture Benchmark (Persistence vs AFNO vs SFNO vs GraphCast).
  5. Mesoscale Super-Resolution Downscaling ($8\times$ Alpine orographic lapse-rate cooling domain).
  6. Data Assimilation Increments (Milan, Rome, Florence, Naples radiosonde observations and analysis increments).
  7. 3D Spherical Digital Twin (Interactive Three.js globe with real-time HUD and controls).

---

## 2. Technical Architecture & File Layout

```
viewer_app/
├── index.html            <- Enhanced HTML5 layout with timeline slider, layer controls, and glassmorphic HUD
├── main.js               <- Core scene graph, animation loop, camera transitions, and texture coordination
├── studyData.js          <- Central scientific data store (V1, V2, V3, 7 Pillars, coordinates, invariants)
├── layers3D.js           <- Three.js 3D visual layer generators (tube, waypoints, pins, spread shell, insets)
├── uiController.js       <- Glassmorphic UI controllers, timeline state machine, comparison modal, popups
├── vercel.json           <- Production headers, security policies, texture caching
└── test/
    └── e2e_test_suite.js <- Requirement-driven opaque-box verification test suite
```

### Radial Shell Hierarchy (Anti-Z-Fighting)
To guarantee depth buffer stability across all WebGL platforms:
- **$R = 5.000$**: Base Earth Mesh (SphereGeometry with T2m / Tendency / Bump textures)
- **$R = 5.020$**: Ensemble Spread Shell (Plasma colormap ShaderMaterial with dynamic opacity)
- **$R = 5.035$**: Mesoscale Insets (Alpine & Japan curvilinear spherical quad meshes with orographic shading)
- **$R = 5.045$**: Forward Cyclone Uncertainty Envelope strip
- **$R = 5.050$**: 3D Cyclone Trajectory Tube (`CatmullRomCurve3` with intensity-based vertex colors)
- **$R = 5.050 \to 5.350$**: Data Assimilation Station Beacons (Surface normal-aligned pins with pulsing caps)
- **$R = 5.150$**: Atmospheric Rayleigh scattering glow shell

---

## 3. Milestones & Task Breakdown

### Milestone 1: Scientific Data Models & Study Version State (`studyData.js`)
- Construct immutable, authentic data models for V1, V2, and V3.
- Embed exact coordinates and metrics for the 5 Typhoon waypoints, 4 Italian DA stations, and Alpine mesoscale bounding box.
- Implement reactive state machine emitting `study-version-changed` events upon user selection.

### Milestone 2: 3D Visualization Layers Engine (`layers3D.js`)
- Implement 3D Cyclone Trajectory Tube using `CatmullRomCurve3` and `TubeGeometry` with MSLP color gradient and uncertainty cone.
- Implement 3D DA Station Pins aligned along normal vector $\mathbf{\hat{n}}$ with pulsating beacon caps and ground innovation rings.
- Implement 3D Ensemble Spread Concentric Shell with custom GLSL fragment shader and interactive opacity controller.
- Implement 3D Mesoscale Insets conforming to the spherical curvature of the Alpine and Japan domains with neon boundaries.
- Implement selective raycasting with drag-vs-click threshold ($>6\text{px}$) and front-hemisphere occlusion filter.

### Milestone 3: Interactive UI, Timeline Slider & Comparison Mode (`uiController.js`, `index.html`)
- Integrate segmented Study Version Timeline Bar (V1 Audit $\to$ V2 Decoupled $\to$ V3 7-Pillars) with dynamic status indicators.
- Implement Version Comparison Modal/Drawer showing side-by-side metrics table (RMSE, MAE, TAC, ACC, Hardware Status).
- Implement interactive Layer HUD with toggles for Cyclone Track, DA Pins, Ensemble Spread, Mesoscale Insets, and Topo Relief.
- Implement screen-space pinned glassmorphic popup cards for station soundings and cyclone waypoints.
- Implement dynamic colormap legends switching between T2m (Turbo), Tendency (RdBu), Spread (Plasma), and DA Increments (Inferno).

### Milestone 4: Integration, E2E Verification & Production Vercel Redeployment
- Wire all modules cleanly into `main.js`.
- Execute full E2E test suite (Tiers 1-4) covering all features, boundary conditions, and user flows.
- Verify production build (`npm run build`) in `viewer_app/` produces clean, zero-warning bundle.
- Deploy to Vercel production (`vercel --prod --yes`) and verify live availability at `https://viewerapp.vercel.app`.
