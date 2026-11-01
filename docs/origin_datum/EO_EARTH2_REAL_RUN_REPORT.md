# ORIGIN DATUM — EO-OBSCURA
# EMPIRICAL VALIDATION REPORT: REAL FORECAST EXPERIMENT & OPERATIONAL VERIFICATION

- **Report Identifier:** `EO-EARTH2-REAL-RUN-001`
- **Project:** OD-EARTH2-001 / EO-OBSCURA
- **Date:** 2026-10-30T03:34:25.281959+00:00
- **Author:** Zhane Daye
- **Affiliation:** Origin Datum — Independent Research Initiative
- **Target Repository:** NVIDIA Earth2Studio fork (`feat/od-earth2-001`)
- **Active Git Commit:** `f16d7d0be0c229a4c2b3bea6840bf8e281b2e040`

---

## 1. Executive Summary

This report documents the empirical execution and verification of the smallest real atmospheric forecast experiment under the 3-stage decoupled anti-leakage architecture (Stage A Forecast $\to$ Stage B Freeze $\to$ Stage C Verify).

Following the elimination of target leakage in historical study runner routines, this experiment establishes genuine, reproducible physical forecast metrics against operational NOAA GFS analysis without future data access during inference.

### High-Level Outcomes:
1. **Model Executed:** Authentic **Persistence Baseline** ($X(t_0 + 24\text{h}) = X(t_0)$) operating on genuine NOAA GFS 0.25° operational analysis.
2. **Neural Model Status:** **NOT VERIFIED (HARDWARE_BLOCKER: AMD GPU / NO CUDA / MISSING CHECKPOINT)**.
   - The host computational environment lacks NVIDIA CUDA GPU acceleration (running with AMD GPU / CPU-only PyTorch).
   - In accordance with SPEC §5, neural model results are marked strictly as `NOT VERIFIED` rather than fabricating simulated or synthetic outputs.
3. **Information Barrier:** Stage A completed and wrote all array artifacts to disk with zero access to verifying analysis.
4. **Cryptographic Sealing:** SHA-256 digests of all forecast and input tensors were sealed in `run_manifest.json` before verification retrieval.
5. **Operational Verification:** Held-out NOAA GFS analysis at $t_0 + 24\text{h}$ was independently retrieved and evaluated.
6. **Overall Verification Verdict:** **`VERIFIED_GENUINE`** (Baseline Persistence against NOAA GFS Operational Analysis).

---

## 2. Atmospheric Cycle & Initialization Details

| Parameter | Specification | Verification Evidence |
|---|---|---|
| **Initialization Time ($t_0$)** | `2026-10-28T00:00:00 UTC` | Authentic NOAA GFS Operational Cycle |
| **Forecast Lead Time ($\Delta t$)** | `24 hours` | Single-step continuous horizon |
| **Valid Verification Time ($t_\text{valid}$)** | `2026-10-29T00:00:00 UTC` | Exactly matching verifying analysis |
| **Meteorological Variable** | `2-meter Air Temperature (T2m)` | Physical unit: Kelvin (K) |
| **Spatial Grid Resolution** | `721 x 1440` ($0.25^\circ \times 0.25^\circ$ Equirectangular) | Global coverage: $90^\circ\text{N} - 90^\circ\text{S}$, $0^\circ - 359.75^\circ\text{E}$ |
| **Atmospheric State at $t_0$** | Min: 215.37 K, Max: 308.84 K, Mean: 279.28 K | Verified genuine NOAA GFS field |

---

## 3. Cryptographic Provenance & Manifest Integrity

All artifacts were serialized and cryptographically hashed before verification:

### 3.1 Forecast & Input Artifacts (Stage A $\to$ Stage B)
| Artifact Name | Role | Dimensions | Data Type | SHA-256 Cryptographic Digest |
|---|---|---|---|---|
| `initial_condition.npy` | Atmospheric state $X(t_0)$ | `(721, 1440)` | `float32` | `aebf0e84f8c1bc210fc051b44b4a9fca15d39cd76fad323f6fe8c5de6307a7f9` |
| `forecast_t2m.npy` | Prediction $\hat{X}(t_0 + 24\text{h})$ | `(721, 1440)` | `float32` | `aebf0e84f8c1bc210fc051b44b4a9fca15d39cd76fad323f6fe8c5de6307a7f9` |
| `run_manifest.json` | Sealed Schema 2.0.0 Manifest | Text JSON | UTF-8 | Verified on disk |
| `hashes.sha256` | Checksum Manifest | Text | UTF-8 | Verified on disk |

### 3.2 Execution Environment
- **Platform:** `CPU (Host System: AMD GPU / No CUDA Driver)`
- **Python Version:** `3.10.11`
- **PyTorch Version:** `2.14.1+cpu`
- **Active Git Commit SHA:** `f16d7d0be0c229a4c2b3bea6840bf8e281b2e040`

---

## 4. Independent Verification Scorecard

Metrics were calculated using latitude-area spherical cosine weights:

| Meteorological Metric | Measured Value | Physical Interpretation |
|---|:---:|---|
| **Verification Status** | **`VERIFIED_GENUINE`** | Authenticated via held-out analysis |
| **Latitude-Weighted RMSE ($\text{RMSE}_w$)** | **`2.1290 K`** | Standard 24h temperature drift |
| **Persistence RMSE ($\text{RMSE}_\text{pers}$)** | **`2.1290 K`** | Identical to model (pure persistence baseline) |
| **Latitude-Weighted MAE ($\text{MAE}_w$)** | **`1.0369 K`** | Mean global absolute temperature difference |
| **Latitude-Weighted Mean Bias** | **`-0.0000 K`** | Unbiased zero global drift |
| **Skill Score vs. Persistence ($SS$)** | **`0.0000`** | Exact physical baseline boundary ($SS = 0.0$) |
| **Tendency Anomaly Correlation (TAC)** | **`0.0000`** | Zero predicted dynamic tendency departure |

### Critical Clarifications:
1. **The Reported ~0.747 K RMSE in Historical v2 Manuscript was Unsubstantiated:**
   - Historical code manufactured predictions by taking $\hat{y} = X(t_0) + 0.72 \cdot (y_\text{truth} - X(t_0)) + \mathcal{N}(0, 0.45)$, which is mathematically guaranteed to produce $\sim 0.75\text{ K}$ RMSE solely because it cheats by accessing $y_\text{truth}$.
   - When evaluated under genuine temporal isolation, the authentic 24h global temperature root-mean-square drift is **`2.1290 K`**.
2. **Correlation Metrics:**
   - The tendency anomaly correlation of the persistence baseline is strictly 0.0, because $\Delta \hat{y} = 0$.
   - Claiming compliance with the WMO 0.60 synoptic threshold without multi-decadal climatology is scientifically invalid and explicitly prohibited by Protocol `EO-EARTH2-VERIF-PROTO-V2`.

---

## 5. Neural Model Execution Blocker & Reproducible Invocation

Per SPEC §5 and user instructions:
- **Blocker Status:** `NOT VERIFIED (HARDWARE_BLOCKER: AMD GPU / NO CUDA / MISSING CHECKPOINT)`
- **Blocker Description:** Host environment lacks NVIDIA CUDA GPU acceleration (running on CPU/AMD GPU). High-dimensional spherical harmonic transform and neural tensor rollout require CUDA.
- **Reproducible Execution Command for CUDA Hardware:**
  ```bash
  # On a machine equipped with NVIDIA GPU (e.g. A100 / RTX 4090 with CUDA 12.x):
  python -m od_experiments.scientific_study.execute_real_experiment --model FourCastNet --checkpoint checkpoints/fcn_v1.pth
  ```

---

## 6. Artifact Index

- **Forecast Directory:** `outputs/scientific_study_verified/forecast/`
- **Verification Directory:** `outputs/scientific_study_verified/verification/`
- **Run Manifest:** `outputs/scientific_study_verified/run_manifest.json`
- **Hash Digests:** `outputs/scientific_study_verified/hashes.sha256`
- **Execution Log:** `outputs/scientific_study_verified/logs/execution.log`
- **Validation Report:** `outputs/scientific_study_verified/verification/validation_results.json`
