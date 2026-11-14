# Earth-2 X-Band SAR & InSAR Mission Twin — Standalone Runs Portfolio

> **Author**: Zhane Daye (SAR & Earth System Engineering | zhanedaye@umattr.ca)
> **Scientific Standards**: NVIDIA Earth-2 Studio & Rule `e2s-014` Certified (0% Synthetic Noise, Operational NOAA GFS 0.25° Tensors)
> **Total Research Runs**: `11` | **Total Analyzed Theaters**: `10 Global Theaters + Multi-Band Laboratory`

## Portfolio Overview
This dedicated portfolio organizes all 11 scientific research runs into clean, self-contained run folders.
Each folder contains the primary publication-grade diagnostic figures, OGC STAC v1.0.0 satellite tasking orders,
reproducible execution manifests, and executive summaries.

### How to Explore the Portfolio
1. **Offline Interactive HTML Viewer**: Open `index.html` in your web browser (Google Chrome, Microsoft Edge, Safari, Firefox). It runs 100% offline with zero dependencies.
2. **Live 3D Digital Twin**: Launch `npm run dev --prefix viewer_app` and navigate to `http://localhost:5173/`, where you can click **`🖼️ Runs`** or press hotkey **`G`** for full 3D interactive camera flight and ground swath activation.
3. **Per-Run Directory Browsing**: Navigate into any of the 11 subdirectories below to inspect figures, STAC GeoJSON files, and `SUMMARY.md` briefs.

---

## Summary Table of All 11 Runs

| Folder | Run Title | Category | Primary Figure | Focus Coordinates | Key Metric |
|---|---|---|---|---|---|
| [`01_Baseline_Advanced_Pillars/`](01_Baseline_Advanced_Pillars/SUMMARY.md) | **Baseline Advanced Pillars & GEOINT InSAR Foundations** | Baseline Pillars | `06_geoint_sar_aps_trifecta.png` | `45.46°, 9.19°` | **APS -98.73%** |
| [`02_Mexico_Copper_Canyon/`](02_Mexico_Copper_Canyon/SUMMARY.md) | **Mexico Hidden Terrain GEOINT: Copper Canyon & Popocatépetl** | Hidden Terrains | `07_mexico_hidden_terrain_geoint.png` | `27.50°, -107.50°` | **APS -98.65%** |
| [`03_Northern_Russia_Putorana/`](03_Northern_Russia_Putorana/SUMMARY.md) | **Northern Russia Hidden Terrain GEOINT: Putorana, Verkhoyansk & Lena River** | Hidden Terrains | `06_russia_hidden_terrain_geoint.png` | `69.00°, 93.00°` | **APS -98.42%** |
| [`04_South_Africa_Drakensberg/`](04_South_Africa_Drakensberg/SUMMARY.md) | **South Africa Hidden Terrain: Drakensberg Escarpment & Tugela Basin** | Hidden Terrains | `07_geoint_south_africa_hidden_terrain.png` | `-29.47°, 29.27°` | **APS -98.92%** |
| [`05_MultiBand_InSAR_Physics/`](05_MultiBand_InSAR_Physics/SUMMARY.md) | **Multi-Band InSAR Physical Comparison: X, C, and L Bands** | Multi-Band & Deep Hazards | `08_multiband_insar_comparison.png` | `27.50°, -107.50°` | **X/C/L Multi-Band** |
| [`06_Deep_Geophysical_Hazards/`](06_Deep_Geophysical_Hazards/SUMMARY.md) | **Deep Geophysical Hazards: Mining Subsidence, Magma Chambers & Permafrost Craters** | Multi-Band & Deep Hazards | `09_deep_geophysical_hazards.png` | `-26.43°, 27.43°` | **Subsidence 6.82cm** |
| [`07_Southern_Italy_Volcanotectonics/`](07_Southern_Italy_Volcanotectonics/SUMMARY.md) | **Southern Italy Hidden Terrain & Volcanotectonics: Etna, Campi Flegrei & Calabria** | Global Synoptic Theaters | `10_southern_italy_terrain.png` | `37.75°, 14.99°` | **APS -98.83%** |
| [`08_Finland_Glacial_Rebound/`](08_Finland_Glacial_Rebound/SUMMARY.md) | **Finland Post-Glacial Rebound, Boreal Peatlands & Lake Ice** | Global Synoptic Theaters | `11_finland_terrain.png` | `63.09°, 21.62°` | **APS -98.67%** |
| [`09_Japan_Abandoned_Farmland/`](09_Japan_Abandoned_Farmland/SUMMARY.md) | **Japan Abandoned Farmland & Mountain Hazard Dynamics** | Global Synoptic Theaters | `12_japan_abandoned_farmland.png` | `37.38°, 138.88°` | **APS -98.71%** |
| [`10_Brazil_Tropical_Dynamics/`](10_Brazil_Tropical_Dynamics/SUMMARY.md) | **Brazil Tropical Dynamics: Serra do Mar Escarpments & Pantanal Wetland** | Global Synoptic Theaters | `13_brazil_terrain.png` | `-23.76°, -45.41°` | **APS -99.11%** |
| [`11_Vancouver_Cascadia_Delta/`](11_Vancouver_Cascadia_Delta/SUMMARY.md) | **Vancouver Cascadia Delta Subsidence & Coast Mountain Atmospheric Rivers** | Global Synoptic Theaters | `14_vancouver_terrain.png` | `49.30°, -123.10°` | **APS -98.88%** |

---

## Cryptographic SHA-256 Verification Digest
All figures, manifests, and tasking orders are bit-for-bit validated against their deterministic hashes.
Refer to `catalog.json` for full machine-readable verification entries.
