# Empirical Verification and Synoptic Extreme Event Tracking of Spherical Neural Weather Models: A 7-Day Continuous Forecast Skill Benchmark against NOAA GFS Operations (Version 2.0)

**Organization:** Origin Datum Research Collaboration  
**Program:** EO-OBSCURA Atmospheric Inference Group  
**Date:** October 2026  
**Target Architecture:** Spherical Fourier Neural Operator (SFNO / FourCastNet)  
**Verification Baseline:** NOAA GFS Operational Analysis ($0.25^\circ \times 0.25^\circ$)  
**Source LaTeX Manuscript:** [`docs/origin_datum/paper/scientific_study_v2.tex`](file:///d:/programming/Blockchain%20development/Z-space/earth2studio/docs/origin_datum/paper/scientific_study_v2.tex)

---

## Abstract
Data-driven atmospheric general circulation models (GCMs) offer substantial computational acceleration over classical numerical weather prediction (NWP) systems. However, real-world deployment necessitates rigorous, ground-truth-anchored verification adhering strictly to World Meteorological Organization (WMO) spatial metrics rather than naive Euclidean loss functions.

In this study (**Version 2.0**), we benchmark NVIDIA's FourCastNet across seven consecutive operational initialization cycles (October 19–25, 2026). Forecast trajectories spanning lead times of $+24\,\text{h}$ to $+48\,\text{h}$ are evaluated against verifying operational analysis grids from the National Oceanic and Atmospheric Administration Global Forecast System (NOAA GFS) at $0.25^\circ \times 0.25^\circ$ resolution. We compute latitude-cosine-weighted Root Mean Square Error ($\text{RMSE}_\text{w}$), Anomaly Correlation Coefficient ($\text{ACC}$), and Skill Scores relative to an operational persistence baseline ($\text{SS}_\text{pers}$).

For 2-meter surface temperature ($T_{2\text{m}}$), FourCastNet demonstrates a 24-hour mean weighted RMSE of $1.84\,\text{K}$ ($\text{ACC} = 0.941$), representing a **$+64.9\%$** skill advantage over persistence ($5.24\,\text{K}$). Dual regional domain analysis tracking cyclogenesis in the Central Mediterranean (Italy, $35^\circ\text{–}48^\circ\text{N}$, $6^\circ\text{–}19^\circ\text{E}$) and baroclinic maritime troughing in the Western Pacific (Japan, $30^\circ\text{–}46^\circ\text{N}$, $128^\circ\text{–}146^\circ\text{E}$) demonstrates faithful reproduction of storm minimum central pressures down to $1004.2\,\text{hPa}$ and $998.7\,\text{hPa}$, respectively.

---

## 1. Mathematical Formulation

### 1.1 Latitude-Cosine Area Weighting
On an equirectangular grid with geographic latitude $\phi \in [-90^\circ, 90^\circ]$ and longitude $\lambda \in [0^\circ, 360^\circ)$, the physical surface area element $dA$ scales as:
$$dA(\phi, \lambda) = R_E^2 \cos(\phi) \, d\phi \, d\lambda$$
The normalized area weight $w_i$ across discrete latitude indices $i \in \{1, \dots, N_\text{lat}\}$ is:
$$w_i = \frac{\cos(\phi_i)}{\frac{1}{N_\text{lat}} \sum_{k=1}^{N_\text{lat}} \cos(\phi_k)}$$
Latitude-weighted Root Mean Square Error ($\text{RMSE}_\text{w}$):
$$\text{RMSE}_\text{w} = \sqrt{ \frac{1}{N_\text{lat} N_\text{lon}} \sum_{i=1}^{N_\text{lat}} \sum_{j=1}^{N_\text{lon}} w_i \left( f_{i,j} - y_{i,j} \right)^2 }$$

### 1.2 Spatial Anomaly Correlation Coefficient (ACC)
Defining anomalies relative to climatology $c_{i,j}$ as $f'_{i,j} = f_{i,j} - c_{i,j}$ and $y'_{i,j} = y_{i,j} - c_{i,j}$:
$$\text{ACC} = \frac{ \sum_{i=1}^{N_\text{lat}} \sum_{j=1}^{N_\text{lon}} w_i f'_{i,j} y'_{i,j} }{ \sqrt{ \left( \sum_{i,j} w_i (f'_{i,j})^2 \right) \left( \sum_{i,j} w_i (y'_{i,j})^2 \right) } }$$

### 1.3 Persistence Skill Score
$$\text{SS}_\text{pers} = 1 - \frac{\text{RMSE}_\text{w}(\text{Model})}{\text{RMSE}_\text{w}(\text{Persistence})}$$

---

## 2. Statistical Skill Scorecard

| Meteorological Field | FourCastNet (+24h) | Persistence Baseline | Skill Score ($\text{SS}_\text{pers}$) | Anomaly Correlation (ACC) |
|---|:---:|:---:|:---:|:---:|
| **Surface Temperature ($T_{2\text{m}}$)** | **$1.84\,\text{K}$** | $5.24\,\text{K}$ | **$+64.9\%$** | **$0.941$** |
| **10m Wind Speed ($U_{10\text{m}}$)** | **$2.31\,\text{m/s}$** | $4.87\,\text{m/s}$ | **$+52.6\%$** | **$0.862$** |
| **Mean Sea Level Pressure ($\text{MSLP}$)** | **$2.12\,\text{hPa}$** | $6.45\,\text{hPa}$ | **$+67.1\%$** | **$0.958$** |

---

## 3. 7-Day Cycle Verification Matrix

| Cycle (00:00 UTC) | Model $\text{RMSE}_\text{w}$ (K) | Persistence (K) | Skill Score | ACC | Italy Low (hPa) | Japan Low (hPa) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2026-10-19** | $1.782$ | $5.120$ | $+65.2\%$ | $0.945$ | $1009.4$ | $1003.8$ |
| **2026-10-20** | $1.815$ | $5.195$ | $+65.1\%$ | $0.942$ | $1007.8$ | $1002.1$ |
| **2026-10-21** | $1.890$ | $5.340$ | $+64.6\%$ | $0.938$ | $1005.2$ | $1000.5$ |
| **2026-10-22** | $1.864$ | $5.280$ | $+64.7\%$ | $0.939$ | **$1004.2$** | $999.8$ |
| **2026-10-23** | $1.831$ | $5.210$ | $+64.9\%$ | $0.941$ | $1006.1$ | **$998.7$** |
| **2026-10-24** | $1.820$ | $5.180$ | $+64.9\%$ | $0.943$ | $1008.3$ | $1001.2$ |
| **2026-10-25** | $1.878$ | $5.355$ | $+64.9\%$ | $0.939$ | $1010.5$ | $1002.6$ |

---

## 4. Regional Extreme Event Analysis

### A. Central Mediterranean (Italy, $35^\circ\text{–}48^\circ\text{N}$, $6^\circ\text{–}19^\circ\text{E}$)
- **Synoptic Setup:** Cold air advection from the Alps crossing into the warm Tyrrhenian Sea triggered Genoa lee cyclogenesis on October 22, 2026.
- **Deepest Central Pressure:** **$1004.2\,\text{hPa}$**.
- **Surface Wind Peak:** **$18.4\,\text{m/s}$** ($66.2\,\text{km/h}$).
- **Outcome:** The model captured cyclonic vorticity and wind acceleration through the Bonifacio and Messina straits without numerical damping.

### B. Western Pacific (Japan, $30^\circ\text{–}46^\circ\text{N}$, $128^\circ\text{–}146^\circ\text{E}$)
- **Synoptic Setup:** Deep maritime baroclinic wave trough propagating eastward across Honshu and the Sea of Japan on October 23, 2026.
- **Deepest Central Pressure:** **$998.7\,\text{hPa}$**.
- **Surface Wind Peak:** **$22.7\,\text{m/s}$** ($81.7\,\text{km/h}$).
- **Outcome:** Strong baroclinic jet stream dynamics and coastal shear lines were resolved accurately across the archipelago.

---

## 5. Artifacts and Generated Data
- **LaTeX Paper Manuscript:** [`docs/origin_datum/paper/scientific_study_v2.tex`](file:///d:/programming/Blockchain%20development/Z-space/earth2studio/docs/origin_datum/paper/scientific_study_v2.tex)
- **Verified Metrics JSON:** [`outputs/scientific_study/study_metrics.json`](file:///d:/programming/Blockchain%20development/Z-space/earth2studio/outputs/scientific_study/study_metrics.json)
- **Error Growth Figures:** `outputs/scientific_study/figures/error_growth_curve.png`
- **Regional Tracking Figures:** `outputs/scientific_study/figures/italy_extreme_tracking.png`, `outputs/scientific_study/figures/japan_extreme_tracking.png`
