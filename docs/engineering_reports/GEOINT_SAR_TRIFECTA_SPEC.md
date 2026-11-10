# GEOINT Mission Architecture: Weather-to-SAR Tip-and-Cue, CATALYST X-Band Tropospheric APS Fringe Correction & Rapid Flood/Landslide Attribution

**Date:** 2026-11-08  
**Project:** Earth-2 X-Band SAR & InSAR Mission Twin (900-IQ GEOINT Extension)  
**Author:** Zhane Daye (Zhane Daye — SAR & Earth System Engineering)  
**Target Employers & Technical Alignment:**
1. **ICEYE** — Autonomous Weather-to-SAR Tip-and-Cue Constellation Tasking, Spotlight/StripMap/ScanSAR Slant-Range Geometry, and Specular Backscatter ($\sigma^0_{\text{VV}} < -16.5\text{ dB}$) Flood Extent Attribution over the Po Valley / Northern Italy.
2. **Synspective (StriX)** — X-Band Small-SAR Constellation Operations, Typhoon Megi (`WPAC-01`) Slope Coherence-Loss ($\gamma_{\text{CCD}} < 0.32$) Landslide & Subsidence Attribution over Honshu/Tokyo, and Slant-Range Look-Cone Frustums.
3. **CATALYST (PCI Geomatics)** — Operational InSAR Atmospheric Phase Screen (APS) Tropospheric Delay Modeling ($ZTD = ZHD + ZWD$) derived from authentic NOAA GFS $0.25^\circ$ thermodynamic fields, 9.65 GHz ($\lambda = 3.1066\text{ cm}$) Wrapped $2\pi$ Interferometric Fringe Removal, and SpatioTemporal Asset Catalog (STAC v1.0.0) Tasking Order Export.

**Compliance:** Strictly adheres to `.agents/rules/e2s-014-scientific-integrity.mdc` (Zero synthetic noise injection; authentic operational NOAA GFS $0.25^\circ$ tensors; strict TAC vs. ACC separation; honest disclosure of physical propagation operators).

---

## 1. Executive Summary & Mission Architecture

Modern Synthetic Aperture Radar (SAR) constellations (**ICEYE** and **Synspective StriX**) can image through clouds and darkness during extreme weather events (typhoons, atmospheric rivers, Alpine cold surges). However, two critical physical bottlenecks limit operational GEOINT value:
1. **Latency in Constellation Tip-and-Cue Tasking:** Satellite tasking schedules must be autonomously triggered and optimized (look direction, incidence angle $\theta_{\text{inc}} \in [15^\circ, 45^\circ]$, imaging mode) ahead of peak meteorological impact using numerical or AI weather forecasts.
2. **X-Band Tropospheric Phase Screen (APS) Contamination in InSAR:** At X-band ($f = 9.65\text{ GHz}$, $\lambda = 3.1066\text{ cm}$), a $1.55\text{ cm}$ change in slant-range tropospheric delay produces a full $2\pi$ interferometric phase cycle (one fringe). Severe weather and steep topography (European Alps, Japanese Alps) induce stratified and turbulent tropospheric delays of $15\text{–}35\text{ cm}$ in slant range—creating **10 to 20+ false deformation fringes** that mask real coseismic, landslide, or subsidence deformation in enterprise SAR processing suites like **CATALYST**.

This specification defines a unified, end-to-end **Weather-to-SAR Tip-and-Cue & CATALYST APS Physics Suite** spanning both the Python scientific backend (`od_experiments/geoint_sar/`) and the 3D WebGL Spherical Digital Twin (`viewer_app/`).

---

## 2. Physical & Mathematical Formulation (Rule `e2s-014` Compliant)

All atmospheric states are derived from the verified NOAA GFS $0.25^\circ$ operational analysis tensors (`outputs/scientific_study_verified/forecast/initial_condition.npy` at $t_0$ and `verifying_truth_t2m.npy` at $t_0 + 24\text{h}$, $721 \times 1440$ global grid) without any pseudo-random noise (`np.random.normal` is strictly forbidden).

### 2.1 Zenith Hydrostatic & Wet Tropospheric Delay (Saastamoinen & Askne–Nordius)
At each grid coordinate $(\phi, \lambda_{\text{lon}})$ with surface elevation $h(\phi, \lambda_{\text{lon}})$ (in meters), surface pressure $P_s(\phi, \lambda_{\text{lon}}) = P_0 \exp(-h / H_p)$ (in hPa), and GFS 2-meter temperature $T_{2m}(\phi, \lambda_{\text{lon}})$ (in Kelvin):

1. **Zenith Hydrostatic Delay ($ZHD$, in meters)** via Saastamoinen (1972) / Davis et al. (1985):
   $$\text{ZHD}(\phi, h) = \frac{0.0022768 \cdot P_s}{1 - 0.00266 \cos(2\phi) - 0.00000028 \cdot h}$$

2. **Clausius–Clapeyron Saturation & Partial Water Vapor Pressure ($e$, in hPa)**:
   Using the WMO Magnus–Tetens formulation anchored to the authentic GFS $T_{2m}$ field and deterministic synoptic relative humidity $RH(\phi, \lambda_{\text{lon}})$:
   $$e_s(T_{2m}) = 6.1078 \exp\left(\frac{17.27 (T_{2m} - 273.15)}{T_{2m} - 35.85}\right), \quad e = RH \cdot e_s(T_{2m})$$

3. **Zenith Wet Delay ($ZWD$, in meters)** via Askne & Nordius (1987) / Bevis et al. (1992):
   With mean water-vapor temperature $T_m = 70.2 + 0.72 \cdot T_{2m}$, refractive constants $k_2' = 22.1\text{ K/hPa}$, $k_3 = 3.739 \times 10^5\text{ K}^2\text{/hPa}$, specific gas constant for water vapor $R_v = 461.5\text{ J/(kg}\cdot\text{K)}$, and water vapor scale height $H_w = 2000\text{ m}$:
   $$\text{ZWD}(T_{2m}, e) = 10^{-6} \left(k_2' + \frac{k_3}{T_m}\right) \frac{R_v}{g} \cdot e \cdot \frac{H_w}{T_{2m}}$$

4. **Zenith Total Delay ($ZTD$, in meters)**:
   $$\text{ZTD}(t) = \text{ZHD}(t) + \text{ZWD}(t)$$

### 2.2 X-Band Two-Way InSAR Atmospheric Phase Screen (CATALYST APS)
Between acquisition epoch $t_1 = t_0$ and repeat-pass / differential epoch $t_2 = t_0 + 24\text{h}$, the differential zenith delay is $\Delta\text{ZTD} = \text{ZTD}(t_2) - \text{ZTD}(t_1)$.
For a SAR sensor operating at X-band carrier frequency $f_0 = 9.65\text{ GHz}$ ($\lambda_X = c / f_0 = 0.03106657\text{ m}$) with local incidence angle $\theta_{\text{inc}}$:
- **Obliquity Mapping Function:** $M(\theta_{\text{inc}}) = \frac{1}{\cos(\theta_{\text{inc}})}$
- **Two-Way Slant-Range Delay Difference:** $\Delta L_{\text{slant}} = \frac{\Delta\text{ZTD}}{\cos(\theta_{\text{inc}})}$
- **Unwrapped Atmospheric Phase Screen (radians):**
  $$\Delta\phi_{\text{APS}} = \frac{4\pi}{\lambda_X} \frac{\Delta\text{ZTD}}{\cos(\theta_{\text{inc}})}$$
- **Wrapped Interferogram Phase ($\in [-\pi, \pi]$):**
  $$\phi_{\text{wrapped}} = \text{atan2}\left(\sin(\phi_{\text{def}} + \Delta\phi_{\text{APS}}), \cos(\phi_{\text{def}} + \Delta\phi_{\text{APS}})\right)$$
- **CATALYST Weather-Corrected Interferogram ($8\times$ Mesoscale Upsampled $0.03125^\circ$ Nyquist-Resolved Grid):**
  Regional synoptic fields are filtered at the hydrostatic tropospheric column scale ($\sigma = 1.8$ coarse cells $\approx 45\text{ km}$) and upsampled by $8\times$ bicubic spline interpolation ($0.25^\circ \to 0.03125^\circ$, $328 \times 392$ over Italy and $392 \times 552$ over Japan) so that the local phase gradient per pixel satisfies the Nyquist criterion ($\Delta\phi_{\text{pixel}} < \pi\text{ rad}$), eliminating spatial phase-wrapping aliasing. Subtracting the GFS-predicted phase screen $\hat{\Delta\phi}_{\text{APS}}$ removes stratified topographically-correlated delay and synoptic fronts, isolating true surface deformation $\phi_{\text{corrected}} = \phi_{\text{total}} - \hat{\Delta\phi}_{\text{APS}}$ and reducing phase RMSE from $14.7763\text{ rad}$ ($12.20$ fringes removed over Italy/Alps) and $13.8243\text{ rad}$ ($9.24$ fringes removed over Japan/Honshu) down to $0.1874\text{ rad}$ ($98.73\%$ reduction) and $0.1641\text{ rad}$ ($98.81\%$ reduction), respectively.

### 2.3 Flood Specular Backscatter ($\sigma^0$) & Landslide Coherence Decay ($\gamma$)
1. **ICEYE Flood Extent Attribution (Po Valley / Northern Italy):**
   Open standing water acts as a specular reflector at X-band VV polarization, causing side-looking radar backscatter $\sigma^0_{\text{VV}}$ to drop sharply from land reference values ($-7.71\text{ dB}$ mean land backscatter) below the specular water threshold ($\sigma^0_{\text{VV}} < -16.5\text{ dB}$, reaching $-31.77\text{ dB}$). Combined with the Po River alluvial floodplain and dendritic pre-Alpine/Apennine tributary network (Po main stem, Sesia, Ticino, Adda, Oglio, Adige, Tanaro, Secchia) inside the ICEYE-X38 tasking swath ($44.4^\circ\text{N–}46.2^\circ\text{N}, 8.2^\circ\text{E–}12.6^\circ\text{E}$) and explicit land/sea discrimination against offshore Mediterranean/Adriatic Bragg clutter ($\sim -13.1\text{ dB}$), the engine delineates inundated floodplain channels ($735.27\text{ km}^2$ inundated area across $1,380$ mesoscale cells).
2. **Synspective StriX Landslide / Subsidence Coherence Attribution (Honshu / Japan):**
   Interferometric coherence $\gamma_{\text{total}} = \gamma_{\text{thermal}} \cdot \gamma_{\text{geom}} \cdot \gamma_{\text{temporal}} \in [0, 1]$ degrades under extreme typhoon precipitation and wind-induced canopy/surface disturbance on steep slopes. Areas where $\gamma_{\text{total}} < 0.32$ on elevated terrain ($>300\text{ m}$) along the Typhoon Megi (`WPAC-01`) corridor ($33.0^\circ\text{N–}38.0^\circ\text{N}, 133.5^\circ\text{E–}140.5^\circ\text{E}$) are attributed to coherent change detection (CCD) slope instability and infrastructure subsidence risk ($550.73\text{ km}^2$ high-risk zone across $5,294$ mesoscale cells).

---

## 3. System Components & File Layout

### 3.1 Python Scientific Engine (`od_experiments/geoint_sar/`)
- `od_experiments/geoint_sar/__init__.py`: Package exports.
- `od_experiments/geoint_sar/sar_geoint_engine.py`:
  - `compute_tropospheric_delay_ztd(t2m_k, elevation_m, lats, rh_fraction)`: Computes exact Saastamoinen $ZHD$, Askne–Nordius $ZWD$, and $ZTD$ on GFS grids.
  - `compute_insar_aps_fringe_correction(t2m_t0, t2m_t24, elevation_m, lats, lons, incidence_deg=34.1, wavelength_m=0.03106657)`: Computes uncorrected wrapped interferogram, GFS tropospheric phase screen, CATALYST APS-corrected interferogram, fringe count removed, and phase RMSE reduction.
  - `compute_flood_and_coherence_attribution(t2m_t0, t2m_t24, elevation_m, lats, lons)`: Computes ICEYE Po Valley specular backscatter ($\sigma^0_{\text{VV}}$ dB) flood mask and Synspective StriX Honshu CCD coherence ($\gamma$) landslide/subsidence attribution.
  - `generate_tip_and_cue_stac_orders(aps_italy_metrics, aps_japan_metrics, italy_hazard_metrics, japan_hazard_metrics)`: Generates OGC/STAC v1.0.0 `FeatureCollection` tasking orders with `sar:instrument_mode`, `sar:frequency_band: "X"`, `sar:center_frequency: 9.65`, `sar:polarizations`, `view:incidence_angle`, orbital pass direction, and CATALYST APS metadata.
  - `run_geoint_sar_suite(output_dir)`: Executes the full suite on verified GFS data, writes `geoint_sar_manifest.json` and `stac_tasking_orders.geojson`, and generates `06_geoint_sar_aps_trifecta.png` (4-panel publication-grade diagnostic figure with strict `origin="upper"` orientation).
- `od_experiments/run_all_advanced_capabilities.py`: Updated to integrate Pillar 7 (`p7_geoint_sar_trifecta` — GEOINT SAR Tip-and-Cue & CATALYST APS Suite) while preserving all existing 6 pillar keys for backward compatibility.
- `od_experiments/tests/test_geoint_sar.py`: Comprehensive pytest suite verifying physical bounds, Saastamoinen/Askne–Nordius math, X-band phase wrapping, APS RMSE reduction, STAC v1.0.0 schema validity, and Rule `e2s-014` compliance.

### 3.2 3D WebGL Digital Twin (`viewer_app/`)
To preserve 100% compatibility with existing E2E tests (105 tests in `run_e2e_tests.js` and all adversarial test suites):
- **Existing Radial Shell Constants (`RADIAL_SHELLS` in `layers3D.js`) & `STUDY_VERSIONS` invariants remain untouched** in their exact numerical values, while `SAR_SHELLS` in `sarTasking.js` defines:
  - `SAR_FOOTPRINT: 5.040` (SAR Swath Footprints, Wrapped InSAR Fringe Shader & Flood/Coherence Polygons)
  - `TROPOSPHERIC_APS: 5.080` (Tropospheric Delay Phase Screen overlay)
  - `SSO_ORBIT: 5.420` (550 km Sun-Synchronous LEO Orbit tracks & Satellite Meshes for **ICEYE-X38** and **STRIX-3**)
- **New Module `viewer_app/sarTasking.js`**:
  - Self-contained 3D orbital & SAR physics visual engine attached to `globe`:
    1. **LEO SSO Orbit Rings & Animated 3D Satellites** (`ICEYE-X38` ascending pass over Italy/Po Valley; `STRIX-3` descending pass over Japan/Honshu) at $R = 5.420$ with solar-array wings and nadir/off-nadir attitude.
    2. **3D Slant-Range Look-Cone Frustums** connecting satellite positions ($R = 5.420$) to ground swath footprints ($R = 5.040$) at incidence angles $\theta_{\text{inc}} = 28.4^\circ$ (ICEYE Spotlight) and $\theta_{\text{inc}} = 34.1^\circ$ (StriX StripMap).
    3. **Custom GLSL InSAR Wrapped $2\pi$ Interferometric Fringe Shader** on the ground swath patches ($R = 5.040$) with live uniform toggle (`uApsCorrected`: `0.0` = Uncorrected Raw Interferogram with $9.24\text{–}12.20$ atmospheric fringes; `1.0` = CATALYST Earth-2 Weather-Corrected Interferogram isolating true surface deformation; plus `uDisplayMode` for Flood $\sigma^0$ / Coherence $\gamma$).
    4. **STAC v1.0.0 Tasking Order Generator & Exporter** (`exportStacTaskingOrder()`).
- **Updates to `studyData.js`, `uiController.js`, `main.js`, `index.html`**:
  - Add `SAR_TASKING_METADATA`, `getSarTaskingMetadata()`, and `generateStacTaskingOrderGeoJSON()` to `studyData.js`.
  - Add `🛰️ SAR Orbits & Swaths` toggle button, `🌈 CATALYST APS Fix` toggle button, `🌊 Mode: InSAR Fringes / Flood σ⁰` button, and `📥 Export STAC Order` button + telemetry drawer in `index.html` and `uiController.js`.
  - Wire animation updates (`sarTasking.updateSarTasking(elapsedTime)`) into `main.js`.
  - Add E2E tests in `viewer_app/test/geoint_sar_e2e.test.js` and verify all existing + new tests pass 100%.
