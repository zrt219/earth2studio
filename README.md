<!-- markdownlint-disable MD002 MD033 MD041 MD053 -->
<div align="center">

# Earth-2 X-Band SAR & InSAR Mission Twin

### Operational Tropospheric Phase Screen (APS) Compensation, Flood Backscatter Attribution, and Autonomous OGC STAC v1.0.0 Tasking on Verified NOAA GFS $0.25^\circ$ Analyses

[![Live 3D Mission Twin](https://img.shields.io/badge/Live_3D_Mission_Twin-earth2--sar--insar.vercel.app-0284c7?style=for-the-badge&logo=vercel)](https://earth2-sar-insar.vercel.app)
[![Viewer Mirror](https://img.shields.io/badge/Production_Mirror-viewerapp.vercel.app-0ea5e9?style=for-the-badge&logo=vercel)](https://viewerapp.vercel.app)
[![Engineering Report PDF](https://img.shields.io/badge/Engineering_Report_PDF-Read_Full_Paper-e11d48?style=for-the-badge&logo=adobeacrobatreader)](./docs/engineering_reports/EARTH2_X_BAND_SAR_INSAR_ENGINEERING_REPORT.pdf)
[![Career Dossier](https://img.shields.io/badge/Geospatial_Career_Dossier-Target_Companies_%26_Pitches-8b5cf6?style=for-the-badge&logo=target)](./docs/engineering_reports/GEOSPATIAL_JOB_PROSPECTING_DOSSIER.md)
[![STAC v1.0.0 Tasking Orders](https://img.shields.io/badge/OGC_STAC_v1.0.0-SAR_Tasking_GeoJSON-10b981?style=for-the-badge&logo=json)](./docs/engineering_reports/stac_tasking_orders.geojson)
[![Pytest Suite](https://img.shields.io/badge/Pytest_Suite-321%2F321_Passing-success?style=for-the-badge&logo=pytest)](./od_experiments/tests/)
[![WebGL E2E Suite](https://img.shields.io/badge/WebGL_E2E_Suite-105%2F105_Passing-success?style=for-the-badge&logo=javascript)](./viewer_app/test/)
[![LinkedIn](https://img.shields.io/badge/Zhane_Daye-SAR_%26_Earth_System_Engineering-0a66c2?style=for-the-badge&logo=linkedin)](https://www.linkedin.com/in/zhane-umattr)

**Author:** **Zhane Daye** — *SAR & Earth System Engineering | Edmonton, AB, Canada*  
📧 [`zhanedaye@umattr.ca`](mailto:zhanedaye@umattr.ca) · 🔗 [`linkedin.com/in/zhane-umattr`](https://www.linkedin.com/in/zhane-umattr) · 💻 [`github.com/zrt219/earth2studio`](https://github.com/zrt219/earth2studio) · 🌐 [**Live 3D Mission Twin (`earth2-sar-insar.vercel.app`)**](https://earth2-sar-insar.vercel.app)

</div>

---

## 🌐 The Live Web Application: Interactive 3D Mission Twin

The centerpiece of this repository is the **Earth-2 X-Band SAR & InSAR Mission Twin Web Application**, deployed in production at:

### 🚀 **[https://earth2-sar-insar.vercel.app](https://earth2-sar-insar.vercel.app)** *(Mirror: [https://viewerapp.vercel.app](https://viewerapp.vercel.app))*

This high-performance WebGL digital twin bridges numerical weather prediction (NWP) with commercial spaceborne radar operations. It couples global atmospheric fields from NVIDIA Earth2Studio and NOAA GFS analyses directly with physical radar propagation models and constellation ground segments.

<div align="center">

### Operational 4-Panel InSAR APS Correction, Flood Backscatter & Coherence Diagnostics
![4-Panel SAR & InSAR Mission Diagnostic](./docs/engineering_reports/figures/06_geoint_sar_aps_trifecta.png)

*Figure 1: **(A)** Po Valley & Alpine Foothills raw wrapped X-band interferogram ($\lambda = 3.11\text{ cm}$, $\theta_{\text{inc}} = 28.4^\circ$) exhibiting $12.20$ atmospheric fringes ($\text{RMSE} = 14.78\text{ rad}$) obscuring ground motion. **(B)** CATALYST NWP-assisted APS-compensated interferogram reducing phase RMSE by **98.73%** to $0.1874\text{ rad}$ and cleanly recovering the true Po Valley subsidence bowl. **(C)** ICEYE-X38 Spotlight VV backscatter ($\sigma^0_{\text{VV}}$) delineating $735.27\text{ km}^2$ of specular open-water flood inundation ($< -16.5\text{ dB}$, cyan contour). **(D)** Synspective StriX-3 repeat-pass coherence ($\gamma_{\text{CCD}}$) over Honshu during Typhoon Megi, isolating $550.73\text{ km}^2$ of severe mountain slope decorrelation ($\gamma < 0.32$, crimson contour).*

</div>

<div align="center">

| Interactive 3D Spherical Mission Twin (`R = 5.000 → 5.420`) | Multi-Model AI-NWP Prognostic Benchmark |
| :---: | :---: |
| ![3D Spherical Model](./docs/engineering_reports/figures/earth_3d_spherical_model.png) | ![Prognostic Benchmark](./docs/engineering_reports/figures/03_prognostic_model_benchmark.png) |

</div>

### ✨ Core Interactive Capabilities in the Web Application

- 🌍 **Tiled Multi-Resolution LOD Globe (4K / 16K / 131K)**: Seamlessly transitions from an 8K photorealistic global albedo to 8 tiled $4096\times 4096$ 16K global octants, down to ultra-high-resolution regional Sentinel-2 true-color surface imagery over northern Italy and Honshu Japan (equivalent to $131,072 \times 65,536 = 131\text{K}$ global resolution).
- 🛰️ **3D Orbital Constellations & Dynamic Look-Cones**: Real-time 3D orbit propagation for **ICEYE-X38** ($i = 97.7^\circ$ SSO, altitude $570\text{ km}$, $\theta_{\text{inc}} = 28.4^\circ$) and **Synspective StriX-3** ($i = 97.6^\circ$ SSO, altitude $561\text{ km}$, $\theta_{\text{inc}} = 34.1^\circ$), featuring dynamic volumetric look-cone frustums projecting directly down to ground swath footprints.
- 📡 **Interactive CATALYST APS InSAR Correction**: Real-time GLSL shader uniform toggling (`uApsCorrected`) that dynamically strips 12.20 atmospheric water vapor fringes from raw interferograms, revealing true tectonic and infrastructure deformation fields in real-time.
- 🏙️ **13 Verified Target Cities with Real-Time Search**: Instant boresight camera targeting across 13 verified urban and industrial corridors (Milan, Venice, Bologna, Turin, Genoa, Florence, Verona in Italy; Tokyo, Yokohama, Osaka, Nagoya, Kyoto, Kobe in Japan) equipped with real-time fuzzy search filtering (`#city-search-input`).
- 🧭 **6-Step Guided Mission Briefing Tour**: Step-by-step interactive onboarding (`#tour-modal`) walking new operators and executives through orbital tracks, severe weather steering, SAR swath tasking, APS phase correction, and STAC tasking orders.
- 💡 **Executive '?' Contextual Explainer**: Instant modal explaining the commercial ROI and physical mechanisms of weather-to-SAR satellite tip-and-cue workflows.
- ⚡ **Live WebGL Performance & Telemetry Badge**: Real-time HUD badge (`#perf-telemetry-badge`) monitoring FPS (solid 60 FPS), active draw calls, polygon count, and estimated GPU VRAM ($248\text{ MB}$, down from $1.29\text{ GiB}$).
- 🔗 **Stateful URL Deep-Linking**: Shareable deep-links encoding city selection, view presets, governance stages, and lead times (e.g., `#city=milan&preset=sar_focus&stage=v3&leadtime=12`) with animated clipboard feedback (`#share-toast`).
- ⌨️ **Keyboard Shortcuts Cheat-Sheet Modal**: Instant keyboard control (`?` or `H` for shortcuts modal, `Space` for auto-rotation, `1`-`4` for view presets, `R` for camera reset, `T` for mission tour, `Esc` to dismiss).
- 🎯 **Clean-Boot Presets & Scientific Governance**: Default-OFF overlay architecture (`Active: 0/8 overlays`) guaranteeing a clean, pristine Earth at boot, paired with 4 instant 1-click Quick View Presets (`SAR Focus`, `Clean Globe`, `Extreme Weather`, `All Telemetry`), clear "AI Trust & Governance Stage" selectors (V1 Audit, V2 Decoupled, V3 7-Pillar Benchmark), and an independent 24h storm lead-time scrubber.

---

## 🛰️ Executive Summary & Commercial SAR Alignment

Commercial X-band ($f_c = 9.65\text{ GHz}$, $\lambda = 3.1067\text{ cm}$) Synthetic Aperture Radar (SAR) constellations—such as **ICEYE** and **Synspective (StriX)**—deliver sub-meter to 3-meter all-weather Earth observation for emergency flood response and structural displacement monitoring. However, X-band Interferometric SAR (InSAR) is notoriously vulnerable to lower-tropospheric water vapor and hydrostatic gradients: a minute $1.5533\text{ cm}$ ($\lambda/2$) two-way slant-range path delay causes a complete $2\pi$ phase wrap. In severe weather scenarios, $9\text{--}15$ turbulent atmospheric fringes easily overwhelm millimeter-scale subsidence or pre-landslide slope creep.

Built upon **NVIDIA Earth2Studio** and an audited, leakage-free 3-stage atmospheric verification pipeline (**Forecast $\to$ Freeze $\to$ Verify**) running on authentic **NOAA GFS $0.25^\circ$ global analyses ($721 \times 1440$)**, this platform delivers an end-to-end **Weather-to-SAR Tip-and-Cue & InSAR Atmospheric Phase Screen (APS) Mission Twin**:

| Target Domain / Organization | Engineered Subsystem | Physical & Algorithmic Implementation | Verified Quantitative Result |
| :--- | :--- | :--- | :--- |
| **CATALYST** *(PCI Geomatics / InSAR)* | [`sar_geoint_engine.py`](./od_experiments/geoint_sar/sar_geoint_engine.py)<br>[`sarTasking.js`](./viewer_app/sarTasking.js) | Two-way X-band ($9.65\text{ GHz}$) tropospheric path delay integration ($\text{ZHD} + \text{ZWD}$) with $8\times$ bicubic Nyquist-resolved mesoscale upsampling ($0.03125^\circ \approx 3.4\text{ km}$) and hydrostatic scale filtering ($\sigma = 1.8$ coarse cells) for DEM-coupled APS removal. | **Italy / Alps:** **98.73% phase RMSE reduction** ($14.7763 \to 0.1874\text{ rad}$), **12.20 fringes** removed.<br>**Japan / Honshu:** **98.81% phase RMSE reduction** ($13.8243 \to 0.1641\text{ rad}$), **9.24 fringes** removed. |
| **ICEYE** *(X-Band SAR Constellation)* | [`sar_geoint_engine.py`](./od_experiments/geoint_sar/sar_geoint_engine.py)<br>[`sarTasking.js`](./viewer_app/sarTasking.js) | **ICEYE-X38** ascending pass ($i = 97.7^\circ$ SSO, $\theta_{\text{inc}} = 28.4^\circ$, $0.5\text{ m}$ Spotlight VV) physical backscatter forward model ($\sigma^0_{\text{VV}}$) for specular open-water flood segmentation and Bragg capillary wind roughening. | Delineates **$735.27\text{ km}^2$** ($1,380$ mesoscale pixels) of Po Valley riverine flood inundation below $-16.5\text{ dB}$ ($\sigma^0_{\text{VV,min}} = -31.77\text{ dB}$ vs. $-7.71\text{ dB}$ land mean). |
| **Synspective** *(StriX Constellation)* | [`sar_geoint_engine.py`](./od_experiments/geoint_sar/sar_geoint_engine.py)<br>[`sarTasking.js`](./viewer_app/sarTasking.js) | **StriX-3** descending pass ($i = 97.6^\circ$ SSO, $\theta_{\text{inc}} = 34.1^\circ$, $3.0\text{ m}$ StripMap VV/VH) repeat-pass Coherent Change Detection ($\gamma_{\text{CCD}}$) coupling wind/moisture volume decorrelation with steep topographic slope geometry. | Isolates **$550.73\text{ km}^2$** ($5,294$ mesoscale pixels) of high-risk Honshu mountain slope decorrelation ($\gamma_{\text{CCD}} < 0.32$, $\gamma_{\text{min}} = 0.080$, land mean $\bar{\gamma} = 0.786$). |
| **Autonomous Ground Segment** *(Tip-and-Cue)* | [`sar_geoint_engine.py`](./od_experiments/geoint_sar/sar_geoint_engine.py)<br>[`uiController.js`](./viewer_app/uiController.js) | Automated anomaly-to-tasking translator exporting OGC STAC v1.0.0 `FeatureCollection` GeoJSON with `sar:*` extensions (`sar:frequency_band="X"`, `sar:center_frequency=9.65`, `sar:product_type="SLC"`) and 3D orbital look-cone frustums. | 2 valid STAC v1.0.0 tasking orders (`ICEYE-X38`, `StriX-3`) sealed with SHA-256 digest `3fecc248...0d47035`; 1-click browser GeoJSON export. |

---

## 🛠️ Step-by-Step Engineering Execution Pipeline (Steps 1 through 9)

The development of this operational mission twin followed a rigorous 9-stage engineering lifecycle, bridging foundational atmospheric science, physical radar modeling, 3D WebGL engine optimization, and enterprise governance:

```mermaid
flowchart TD
    S1["Step 1: Audit & Anti-Leakage Quarantine<br>• Purge synthetic leakage formula<br>• Decoupled Forecast → Freeze → Verify"] --> S2["Step 2: APS Formulation & SAR Sensor Physics<br>• Saastamoinen ZHD + Askne-Nordius ZWD<br>• 8x mesoscale upsampling (0.03125°)<br>• 98.73% / 98.81% InSAR phase RMSE reduction"]
    S2 --> S3["Step 3: Autonomous OGC STAC v1.0.0 Engine<br>• Anomaly detection → Tip-and-Cue tasking<br>• sar:* extensions & SHA-256 manifest"]
    S3 --> S4["Step 4: Three.js 3D Mission Twin Architecture<br>• Concentric shells R=5.000 to 5.420<br>• Custom GLSL fringe & backscatter shaders"]
    S4 --> S5["Step 5: 16K Global Octants & 131K Regional LOD<br>• 8x 4096² octants + Sentinel-2 crops<br>• Boresight projection & LRU caching"]
    S5 --> S6["Step 6: GPU Memory & Texture Optimization<br>• Fix 1.29 GiB VRAM crash → 248 MB (-81%)<br>• Frustum/distance gating & DynamicDrawUsage"]
    S6 --> S7["Step 7: CEO Clarity & Clean-Boot Governance<br>• Default-OFF 0/8 overlays & Quick Presets<br>• Plain-English AI Trust Stage (V1/V2/V3)<br>• Separated 24h storm lead-time scrubber"]
    S7 --> S8["Step 8: 900IQ Enterprise Polish<br>• Fuzzy city search & URL deep-linking<br>• Shortcuts modal & WebGL telemetry badge"]
    S8 --> S9["Step 9: Multi-Tier Verification & Deployment<br>• Pytest 321/321 & E2E 105/105 passed<br>• Headless Chrome CDP desktop & mobile QA<br>• Vercel production deployment"]
```

### 🔹 Step 1: Architectural Audit & Cryptographic Anti-Leakage Quarantine
- **Discovery**: An initial architectural inspection of early repository scripts revealed a synthetic target-leakage heuristic ($\hat{y} = x_0 + 0.72\Delta + \epsilon$) where future verifying truth $Y(t_0 + 24\text{h})$ was linearly blended into model predictions prior to evaluation, fabricating an unphysical $\text{RMSE} = 0.747\text{ K}$ and $\text{ACC} = 0.941$.
- **Remediation**: All contaminated code paths were permanently quarantined under `od_experiments/scientific_study/historical/` and classified as invalid. AST static analysis and runtime test suites ([`test_anti_leakage_guardrails.py`](./od_experiments/tests/test_anti_leakage_guardrails.py)) were instituted to strictly prohibit any target-leakage references.
- **Protocol**: Enforced a cryptographically audited 3-stage pipeline:
  $$\text{Stage A (Forecast)} \xrightarrow{\text{Temporal Air-Gap}} \text{Stage B (SHA-256 Freeze)} \xrightarrow{\text{Independent Fetch}} \text{Stage C (Verification)}$$
  All baseline benchmarks run strictly on authentic operational **NOAA GFS $0.25^\circ$ analyses** ($721 \times 1440$, $1,038,240$ cells), yielding a genuine baseline $\text{RMSE}_w = 2.1290\text{ K}$ and $\text{MAE}_w = 1.0369\text{ K}$.

### 🔹 Step 2: Atmospheric Phase Screen (APS) Formulation & SAR Sensor Physics
- **Physical Modeling**: X-band radar signals experience two-way path delays through the neutral troposphere. The total zenith delay ($\text{ZTD}$) is decomposed into hydrostatic ($\text{ZHD}$) and wet ($\text{ZWD}$) components via Saastamoinen and Askne–Nordius refractivity integration:
  $$\text{ZHD} = 0.0022768 \cdot \frac{P_s}{1 - 0.00266 \cos(2\phi) - 0.00028 \cdot H}$$
  $$\text{ZWD} = 10^{-6} \left( k'_2 + \frac{k_3}{T_m} \right) \frac{R_d}{M_w (\lambda + 1)} \cdot \text{TCWV}$$
  $$\Delta\phi_{\text{APS}} = -\frac{4\pi}{\lambda \cos(\theta_{\text{inc}})} (\text{ZTD}_2 - \text{ZTD}_1)$$
- **Spatial Resolution & Nyquist Criterion**: To eliminate phase unwrapping ambiguities, interferometric fringes must satisfy the spatial Nyquist condition:
  $$|\nabla \phi_{\text{APS}}| < \pi \text{ rad/pixel}$$
  Raw GFS $0.25^\circ$ grids ($\sim 27\text{ km}$) violate this condition across steep topography. The engine implements an $8\times$ bicubic spline interpolation down to **$0.03125^\circ \approx 3.4\text{ km}$**, satisfying the criterion.
- **Quantitative Results**:
  - **Po Valley / Italian Alps**: Phase RMSE reduced by **98.73%** ($14.7763\text{ rad} \to 0.1874\text{ rad}$), removing **$12.20$ atmospheric fringes**.
  - **Honshu / Japan**: Phase RMSE reduced by **98.81%** ($13.8243\text{ rad} \to 0.1641\text{ rad}$), removing **$9.24$ atmospheric fringes**.
- **Sensor Forward Models**:
  - *ICEYE-X38 Spotlight*: Parameterized $\sigma^0_{\text{VV}}$ forward model segregates specular open-water flood inundation below $-16.5\text{ dB}$, delineating **$735.27\text{ km}^2$** of inundated Po plain.
  - *Synspective StriX-3 StripMap*: Repeat-pass coherence $\gamma_{\text{CCD}}$ forward model isolates **$550.73\text{ km}^2$** of unstable mountain slope decorrelation ($\gamma < 0.32$).

### 🔹 Step 3: OGC STAC v1.0.0 Autonomous Tip-and-Cue Tasking Engine
- **Autonomous Triggering**: Severe meteorological anomalies detected in the AI-NWP forecasts (cyclonic pressure drops $>24\text{ hPa/day}$, wind gusts $>30\text{ m/s}$, precipitation $>50\text{ mm/day}$) trigger the ground segment tasking engine.
- **Standardized Metadata**: Generates valid OGC STAC v1.0.0 `FeatureCollection` GeoJSON incorporating the `sar:*` STAC extension:
  - `sar:instrument_mode`: Spotlight (ICEYE) / StripMap (Synspective)
  - `sar:frequency_band`: `"X"` ($9.65\text{ GHz}$, $\lambda = 3.1067\text{ cm}$)
  - `sar:polarizations`: `["VV"]` (ICEYE) / `["VV", "VH"]` (Synspective)
  - `sar:product_type`: `"SLC"` (Single Look Complex)
- **Sealing & Delivery**: Tasking orders are cryptographically sealed with SHA-256 (`3fecc248...0d47035`) and integrated with a client-side 1-click browser export button.

### 🔹 Step 4: Three.js 3D Spherical Mission Twin Architecture
- **Concentric Radial Shell Hierarchy**: Constructed a collision-free, Z-fighting-immune scene graph of nested spherical shells ($R=5.000$ to $R=5.420$):
  - **$R = 5.000$**: Base photorealistic Earth sphere with 8K Day/Night satellite albedo, 4K normal bathymetry, 4K night city lights, and specular roughness.
  - **$R = 5.020$**: Mesoscale hydrostatic elevation relief and thermal anomaly displacement.
  - **$R = 5.060$**: Global 2-meter temperature ($T_{2m}$) and 24h prognostic tendency ($\Delta T_{2m}$) heatmaps with custom dynamic fragment colormaps.
  - **$R = 5.120$**: Dynamic rotating photorealistic cloud layer with atmospheric Rayleigh scattering atmosphere shell ($R=5.180$).
  - **$R = 5.220$**: Animated 3D Lagrangian wind particle velocity vector field ($12,000$ particles).
  - **$R = 5.280$**: InSAR APS wrapped interferometric fringes ($[-\pi, +\pi]$ cyclic colormap) and unwrapped surface deformation displacement fields.
  - **$R = 5.350$**: ICEYE specular flood backscatter masks and Synspective coherence decorrelation swaths.
  - **$R = 5.420$**: Low Earth Orbit (LEO) orbital satellite paths, nadir ground tracks, and volumetric look-cone frustums pointing at target swaths.
- **Custom GLSL ShaderMaterials**: Developed specialized WebGL shaders executing real-time cyclic phase wrapping ($\text{mod}(\phi, 2\pi) - \pi$), color ramps, and alpha blending.

### 🔹 Step 5: 16K Global Octants & 131K Sentinel-2 Regional LOD Streaming
- **Tiled Architecture**: To overcome WebGL texture dimension limits ($4096\times 4096$ or $8192\times 8192$), the globe is partitioned into 8 octants ($2\times 4$ grid, each $4096\times 4096$, delivering an aggregate $16,384\times 8,192 = 16\text{K}$ global resolution).
- **Sub-Kilometer Regional Insets**: Embedded $4096\times 4096$ Sentinel-2 true-color surface tiles cropped over northern Italy ($38^\circ\text{--}48^\circ\text{N}, 6^\circ\text{--}18^\circ\text{E}$) and Japan ($30^\circ\text{--}42^\circ\text{N}, 128^\circ\text{--}145^\circ\text{E}$). Over these $10^\circ \times 12^\circ$ domains, pixel spacing corresponds to $0.03125^\circ$, delivering the equivalent of **$131,072 \times 65,536 = 131\text{K}$ global resolution**.
- **Boresight Projection & LRU Cache**: Implemented camera boresight dot-product and frustum intersection tests to dynamically load and release high-resolution textures via an asynchronous LRU tile cache.

### 🔹 Step 6: GPU Memory & Texture Optimization (Fixing the 1.29 GiB VRAM Bottleneck)
- **The Bottleneck**: Startup telemetry revealed that naively pre-loading all 8 16K octants, 2 regional Sentinel-2 insets, and 7 global textures consumed **1,290 MB (1.29 GiB)** of GPU VRAM, causing browser stutter and OOM crashes on mobile and integrated GPUs.
- **Architectural Solution**:
  1. *Distance/Frustum-Gated Lazy Loading*: Octants and Sentinel-2 regional insets remain completely unallocated at boot, loading only when the camera zooms within distance threshold $\text{dist} < 12.2$.
  2. *Off-Thread ImageBitmap Decoding*: Replaced synchronous `THREE.TextureLoader` with worker-assisted `THREE.ImageBitmapLoader` (`createImageBitmap`), eliminating main-thread execution stalls during texture transfer.
  3. *Zero-Allocation Particle Arrays*: Refactored the $12,000$-particle Lagrangian wind vector loop to write into pre-allocated static typed buffers with `THREE.DynamicDrawUsage` (`Float32Array(12000 * 3)`), preventing garbage collection pauses.
- **Measured Result**:
  $$\text{GPU VRAM: } 1,290\text{ MB} \longrightarrow \mathbf{248\text{ MB}} \quad (-80.8\% \text{ reduction})$$
  Maintained a locked **60 FPS** on both high-end desktop workstations and resource-constrained mobile devices.

### 🔹 Step 7: CEO Clarity, Clean-Boot Presets & Scientific Governance
- **Executive UX Transformation**: An evaluation by executive leadership highlighted that opening a 3D Earth with 8 overlapping telemetry layers active created visual noise and hindered rapid decision-making.
- **Interventions Implemented**:
  1. *Clean-Boot Default*: All 8 telemetry layers start OFF by default (`Active: 0/8 overlays`), showcasing the pristine photorealistic Earth globe.
  2. *4 Quick View Presets*: Added 1-click preset pills:
     - 📡 **SAR Focus**: Activates ICEYE flood masks, StriX coherence swaths, and InSAR APS fringes.
     - 🌍 **Clean Globe**: Shows photorealistic Earth albedo and rotating cloud layers.
     - 🌪️ **Extreme Weather**: Displays cyclone tracks, wind streamlines, and hazard alerts.
     - 📊 **All Telemetry**: Full multi-layer diagnostic view.
     - ✖️ **Clear All**: Instantly resets to clean Earth.
  3. *Plain-English AI Trust & Governance Stages*: Replaced confusing "Study Trajectory (V1/V2/V3)" with transparent executive labeling:
     - **Stage 1 (V1)**: Legacy Benchmark & Anti-Leakage Audit (quarantined synthetic heuristic).
     - **Stage 2 (V2)**: Decoupled GFS Forecast & Freeze (genuine persistence baseline).
     - **Stage 3 (V3)**: Operational 7-Pillar Multi-Model Verification (multi-model neural ensemble).
  4. *Independent 24h Scrubber*: Completely decoupled the 24-hour storm evolution scrubber (0h, +6h, +12h, +18h, +24h) from the governance stage selector.
  5. *Data Assimilation Formatting*: Corrected DA sounding station temperature increments from raw Kelvin to intuitive Celsius anomalies ($\Delta T = -0.42^\circ\text{C}$).

### 🔹 Step 8: 900IQ Enterprise Polish & Interactive UX
- **Real-Time Target City Search**: Added an instant fuzzy search bar (`#city-search-input`) allowing operators to type and instantly snap the camera to any of the 13 verified target cities across Italy and Japan.
- **Stateful Deep-Linking**: Implemented URL hash synchronization (`#city=milan&preset=sar_focus&stage=v3&leadtime=12`) with an animated share toast (`#share-toast`).
- **Keyboard Shortcuts Cheat-Sheet**: Added an accessible cheat-sheet modal (`#shortcuts-modal`, toggled via `?` or `H`) outlining all camera, preset, and layer controls.
- **Live Telemetry Badge**: Implemented an unobtrusive HUD telemetry badge (`#perf-telemetry-badge`) monitoring live FPS, WebGL draw calls, triangle count, and memory allocation in real-time.

### 🔹 Step 9: Multi-Tier Verification & Production Deployment
- **Verification Hierarchy**: Every subsystem is locked under an exhaustive 3-tier automated test harness:
  - **Pytest (321/321 passing)**: Validates Saastamoinen/Askne physical integrals, AST anti-leakage static AST analysis, STAC v1.0.0 GeoJSON schema, and mathematical invariants.
  - **Node.js E2E Test Suite (105/105 passing)**: Validates 3D scene-graph contracts, GLSL shader uniforms, raycast picking, and boundary conditions.
  - **GEOINT SAR E2E Suite (25/25 passing)**: Validates orbital geometry, look-cone intersections, STAC export, and APS toggles.
  - **Automated Headless Chrome CDP Verifier**: Scripted browser testing via Chrome DevTools Protocol across Desktop ($1920\times 1080$), Mobile ($390\times 844$ iPhone 14/15, asserting $\text{HUD height} \le 40\text{vh}$), and Ultra-Narrow ($320\times 568$, asserting zero horizontal overflow).
- **Deployment**: Continuously deployed to Vercel production edge infrastructure ([`earth2-sar-insar.vercel.app`](https://earth2-sar-insar.vercel.app)).

---

## 🔬 Scientific Provenance & Validation Boundaries

In strict compliance with [`.agents/rules/e2s-014-scientific-integrity.mdc`](./.agents/rules/e2s-014-scientific-integrity.mdc), this platform maintains a transparent, audited boundary separating **real operational observations**, **deterministic forward physics**, and **computational simulations**:

```mermaid
graph TD
    subgraph "Real Operational Atmosphere"
        GFS["NOAA GFS 0.25° Global Analysis<br>(721 x 1440 Gridded Analyses)"]
    end

    subgraph "Deterministic Physical Forward Operators"
        GFS --> APS["Tropospheric Delay Operator (APS)<br>• Saastamoinen ZHD (Hydrostatic)<br>• Askne-Nordius ZWD (Wet Refractivity)<br>• 8x Bicubic Spline (0.03125° / 3.4 km)"]
        GFS --> SAR["Radar Backscatter & Coherence Models<br>• ICEYE-X38 Spotlight σ0_VV Model<br>• Synspective StriX-3 γ_CCD Coherence"]
    end

    subgraph "Spaceborne Mission Twin & Tasking"
        APS --> WEBGL["3D WebGL Digital Twin (Three.js)<br>• Wrapped Phase Fringes [-π, +π]<br>• Unwrapped InSAR Deformation Fields"]
        SAR --> STAC["Autonomous Tip-and-Cue Tasking<br>• OGC STAC v1.0.0 FeatureCollection<br>• sar:* Extensions & SHA-256 Manifest"]
    end
```

1. **Validated Real Operational Meteorological Analyses (`outputs/scientific_study_verified/`):**
   - Global 2-meter temperature ($T_{2m}$) initial (`initial_condition.npy`) and +24h verifying (`verifying_truth_t2m.npy`) fields are **authentic NOAA Global Forecast System (GFS) $0.25^\circ$ operational analyses** ($721 \times 1440$, $1,038,240$ grid cells).
   - Verified through the decoupled 3-stage **Forecast $\to$ Freeze (SHA-256) $\to$ Verify** pipeline ($\text{RMSE}_w = 2.1290\text{ K}$, $\text{MAE}_w = 1.0369\text{ K}$).
2. **Deterministic Forward-Modeled SAR & InSAR Physics Operators (`od_experiments/geoint_sar/sar_geoint_engine.py`):**
   - **Tropospheric Phase Screens ($\Delta\phi_{\text{APS}}$)**: Calculated by integrating GFS atmospheric density and moisture profiles along two-way radar slant paths down to the Earth's surface.
   - **Radar Backscatter ($\sigma^0_{\text{VV}}$) and Coherence ($\gamma_{\text{CCD}}$)**: Physically parameterized forward models driven by GFS boundary-layer forcing, hydrological catchment zones, and topographic slopes to simulate commercial radar responses.
3. **Hardware Boundaries & Local Rollout**:
   - Workstation testing was conducted on AMD Ryzen / Radeon hardware (no local NVIDIA CUDA tensor cores). Local neural checkpoint rollout requires CUDA; cloud inference was independently validated against the live NVIDIA Earth-2 Hosted FourCastNet API.

---

## 📚 Technical Reports & Research Portfolio

The complete mathematical derivations, architectural diagrams, and empirical validations are published in the accompanying engineering reports:

- 📄 **[Earth-2 X-Band SAR & InSAR Mission Twin — Full Engineering Report (PDF)](./docs/engineering_reports/EARTH2_X_BAND_SAR_INSAR_ENGINEERING_REPORT.pdf)** ([LaTeX Source](./docs/engineering_reports/EARTH2_X_BAND_SAR_INSAR_ENGINEERING_REPORT.tex))
- 📄 **[Executive Research Summary: Overhaul, Verification & 7-Pillar Expansion (PDF)](./docs/engineering_reports/OD_EARTH2_RESEARCH_SUMMARY.pdf)** ([LaTeX Source](./docs/engineering_reports/OD_EARTH2_RESEARCH_SUMMARY.tex))
- 📄 **[Comprehensive Scientific Study v3.1: CRPS, SSR, EDI/SEDI & Multi-Model Ensembles (PDF)](./docs/engineering_reports/paper/scientific_study_v3.pdf)** ([LaTeX Source](./docs/engineering_reports/paper/scientific_study_v3.tex))
- 📄 **[34-Figure Visual Scientific Atlas & SHA-256 Compendium (PDF)](./docs/engineering_reports/OD_EARTH2_VISUAL_RECAP.pdf)** ([LaTeX Source](./docs/engineering_reports/OD_EARTH2_VISUAL_RECAP.tex))
- 🗺️ **[OGC STAC v1.0.0 Autonomous SAR Tasking Orders (`stac_tasking_orders.geojson`)](./docs/engineering_reports/stac_tasking_orders.geojson)** ([Manifest JSON](./outputs/scientific_study_verified/advanced_capabilities/geoint_sar_manifest.json))

---

## ⚡ Quick-Start Reproduction & Verification

To verify the scientific algorithms, run the test suites, or launch the 3D WebGL Mission Twin locally:

```bash
# 1. Run the complete 7-Pillar + X-Band SAR/InSAR APS & STAC Tasking Pipeline
python -m od_experiments.run_all_advanced_capabilities

# 2. Run the Python Scientific & SAR Physics Test Suite (321 tests, 100% passing)
pytest od_experiments/tests/ -v

# 3. Run the 3D WebGL Digital Twin E2E & SAR/STAC Test Suites (105 + 25 tests, 100% passing)
node viewer_app/test/run_e2e_tests.js
node viewer_app/test/geoint_sar_e2e.test.js

# 4. Run the Automated Headless Chrome CDP Verification (Desktop & Mobile)
node viewer_app/test/automated_cdp_verifier.mjs --local-only

# 5. Launch the 3D WebGL Mission Twin Web Application locally
npm --prefix viewer_app install
npm --prefix viewer_app run dev

# 6. Build production static bundle
npm --prefix viewer_app run build
```

---

<div align="center">

# Upstream Framework: NVIDIA Earth2Studio

[![python version][e2studio_python_img]][e2studio_python_url]
[![license][e2studio_license_img]][e2studio_license_url]
[![format][e2studio_format_img]][e2studio_format_url]
[![mypy][e2studio_mypy_img]][e2studio_mypy_url]
[![ruff][e2studio_ruff_img]][e2studio_ruff_url]

Earth2Studio is a Python-based open-source framework designed to get researchers and engineers up and running with AI Earth system models *fast*.
This mission twin extends Earth2Studio by coupling its AI atmospheric forecasts directly to spaceborne radar simulation and commercial constellation tasking.

[Documentation][e2studio_docs_url] | [User Guide][e2studio_userguide_url] | [Examples][e2studio_examples_url] | [API Reference][e2studio_api_url]

![Earth2Studio README hero](https://huggingface.co/datasets/nvidia/earth2studio-assets/resolve/main/readme/v2/earth2studio-readme-hero.png?v2)

</div>

### NVIDIA FourCastNet3 Prognostic Example

```python
from earth2studio.models.px import FCN3
from earth2studio.data import GFS
from earth2studio.io import ZarrBackend
from earth2studio.run import deterministic as run

model = FCN3.load_model(FCN3.load_default_package())
data = GFS()
io = ZarrBackend("outputs/fcn3_forecast.zarr")
run(["2025-01-01T00:00:00"], 10, model, data, io)
```

### ECMWF AIFS Prognostic Example

```python
from earth2studio.models.px import AIFS
from earth2studio.data import IFS
from earth2studio.io import ZarrBackend
from earth2studio.run import deterministic as run

model = AIFS.load_model(AIFS.load_default_package())
data = IFS()
io = ZarrBackend("outputs/aifs_forecast.zarr")
run(["2025-01-01T00:00:00"], 10, model, data, io)
```

### Google GraphCast Operational Example

```python
from earth2studio.models.px import GraphCastOperational
from earth2studio.data import GFS
from earth2studio.io import ZarrBackend
from earth2studio.run import deterministic as run

package = GraphCastOperational.load_default_package()
model = GraphCastOperational.load_model(package)
data = GFS()
io = ZarrBackend("outputs/graphcast_operational_forecast.zarr")
run(["2025-01-01T00:00:00"], 4, model, data, io)
```

---

## 👤 Attribution & Citation

This operational SAR/InSAR mission twin architecture, WebGL digital twin, and empirical verification suite was engineered by:

**Zhane Daye**  
*SAR & Earth System Engineering | Edmonton, AB, Canada*  
📧 Email: [`zhanedaye@umattr.ca`](mailto:zhanedaye@umattr.ca)  
🔗 LinkedIn: [`https://www.linkedin.com/in/zhane-umattr`](https://www.linkedin.com/in/zhane-umattr)  
🌐 Production Twin: [`https://earth2-sar-insar.vercel.app`](https://earth2-sar-insar.vercel.app)  
🏛️ Repository: [`https://github.com/zrt219/earth2studio`](https://github.com/zrt219/earth2studio)

```bibtex
@software{daye2026earth2sar,
  author       = {Daye, Zhane},
  title        = {{Earth-2 X-Band SAR & InSAR Mission Twin: Operational Tropospheric Phase Screen Compensation, Flood Backscatter Attribution, and Autonomous OGC STAC v1.0.0 Tasking}},
  year         = {2026},
  url          = {https://earth2-sar-insar.vercel.app},
  publisher    = {GitHub},
  address      = {Edmonton, AB, Canada}
}
```

## 📄 License

Earth2Studio is licensed under the Apache License 2.0. Refer to [LICENSE](./LICENSE) for the full license text.

<!-- Badges and Links -->
[e2studio_python_img]: https://img.shields.io/badge/Python-3.11%20|%203.12%20|%203.13%20|%203.14-blue?style=flat-square&logo=python
[e2studio_license_img]: https://img.shields.io/badge/License-Apache%202.0-green?style=flat-square
[e2studio_format_img]: https://img.shields.io/badge/Code%20Style-Black-black?style=flat-square
[e2studio_mypy_img]: https://img.shields.io/badge/mypy-Checked-blue?style=flat-square&labelColor=grey
[e2studio_ruff_img]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json&style=flat-square

[e2studio_python_url]: https://www.python.org/downloads/
[e2studio_license_url]: ./LICENSE
[e2studio_format_url]: https://github.com/psf/black
[e2studio_mypy_url]: https://mypy-lang.org/
[e2studio_ruff_url]: https://github.com/astral-sh/ruff

[e2studio_docs_url]: https://nvidia.github.io/earth2studio/
[e2studio_install_url]: https://nvidia.github.io/earth2studio/main/userguide/about/install/
[e2studio_userguide_url]: https://nvidia.github.io/earth2studio/main/userguide/
[e2studio_examples_url]: https://nvidia.github.io/earth2studio/main/examples/
[e2studio_api_url]: https://nvidia.github.io/earth2studio/main/modules/
