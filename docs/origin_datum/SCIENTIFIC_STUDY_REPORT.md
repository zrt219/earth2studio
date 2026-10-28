# Scientific Report: 7-Day Continuous Lead-Time Benchmark & Dual Regional Extreme Event Tracking

**Organization:** ORIGIN DATUM  
**Research Program:** EO-OBSCURA  
**Model Architecture:** Spherical Fourier Neural Operator (FourCastNet / SFNO)  
**Ground Truth Reference:** NOAA GFS Operational Analysis ($0.25^\circ 	imes 0.25^\circ$)  
**Evaluation Period:** 2026-10-20 to 2026-10-26 (7 Consecutive Daily Cycles)  
**Publication Date:** 2026-10-28  

---

## 1. Abstract

This study presents an empirical ground-truth verification of neural weather forecasting models against operational atmospheric analysis grids.
Over seven consecutive global cycles, we evaluated +24h predictions of 2-meter air temperature ($T_{2m}$) and mean sea level pressure ($MSL$) against verified observations.
Additionally, we tracked localized regional storm dynamics across two critical geographic sectors: the Central Mediterranean (Italy) and the Western Pacific (Japan).

---

## 2. Statistical Skill Scorecard

| Meteorological Metric | FourCastNet (+24h) | Persistence Baseline | Operational Threshold | Scientific Conclusion |
|---|:---:|:---:|:---:|---|
| **Latitude-Weighted RMSE** | **0.747 K** | 2.129 K | $< 2.0$ K | **Superior to Baseline** |
| **Skill Score ($SS$)** | **+64.9%** | 0.0% | $> 0.0%$ | **Definitive Forecast Skill** |
| **Anomaly Correlation (ACC)** | **0.959** | N/A | $> 0.60$ | **High Synoptic Correlation** |

---

## 3. Daily 7-Day Evaluation Matrix

| Cycle (00:00 UTC) | Weighted RMSE (K) | Persistence RMSE (K) | Skill Score | ACC | Italy Low (hPa) | Japan Low (hPa) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2026-10-20** | 0.734 | 2.069 | +64.5% | 0.957 | 1006.1 | 1004.1 |
| **2026-10-21** | 0.732 | 2.059 | +64.5% | 0.957 | 1009.1 | 1000.9 |
| **2026-10-22** | 0.755 | 2.165 | +65.1% | 0.961 | 1016.9 | 1015.3 |
| **2026-10-23** | 0.758 | 2.179 | +65.2% | 0.961 | 1013.7 | 1011.0 |
| **2026-10-24** | 0.786 | 2.301 | +65.8% | 0.965 | 1011.8 | 1011.1 |
| **2026-10-25** | 0.731 | 2.061 | +64.5% | 0.957 | 1012.4 | 1006.2 |
| **2026-10-26** | 0.733 | 2.066 | +64.5% | 0.957 | 1013.3 | 1003.4 |

---

## 4. Regional Extreme Event Analysis

### A. Italy & Central Mediterranean ($35^\circ\text{N}-48^\circ\text{N}, 6^\circ\text{E}-19^\circ\text{E}$)
- **Synoptic Context:** Mediterranean cyclogenesis driven by cold continental air masses interacting with warm maritime sea-surface temperatures.
- **Deepest Low Observed:** `1006.1 hPa`.
- **Artifact:** `outputs/scientific_study/figures/italy_extreme_tracking.png`.

### B. Japan & Western Pacific ($30^\circ\text{N}-46^\circ\text{N}, 128^\circ\text{E}-146^\circ\text{E}$)
- **Synoptic Context:** Maritime trough systems and coastal barometric gradients affecting Honshu and the Sea of Japan.
- **Deepest Low Observed:** `1000.9 hPa`.
- **Artifact:** `outputs/scientific_study/figures/japan_extreme_tracking.png`.

---

## 5. Artifact Provenance & Audit Trail

- **Full Metric Dataset:** [`outputs/scientific_study/study_metrics.json`](file:///outputs/scientific_study/study_metrics.json)
- **Growth Curves:** [`outputs/scientific_study/figures/error_growth_curve.png`](file:///{summary['figures'][0]})
- **Italy Tracking Plot:** [`outputs/scientific_study/figures/italy_extreme_tracking.png`](file:///{summary['figures'][1]})
- **Japan Tracking Plot:** [`outputs/scientific_study/figures/japan_extreme_tracking.png`](file:///{summary['figures'][2]})

<!-- STUDY_COMPLETE -->