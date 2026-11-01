# ORIGIN DATUM — EO-OBSCURA
# SCIENTIFIC VERIFICATION PROTOCOL: DECOUPLED NUMERICAL FORECASTING & INDEPENDENT OPERATIONAL ANALYSIS VALIDATION

- **Protocol Identifier:** `EO-EARTH2-VERIF-PROTO-V2`
- **Project:** OD-EARTH2-001 / EO-OBSCURA
- **Author:** Zhane Daye
- **Affiliation:** Origin Datum — Independent Research Initiative
- **Location:** Edmonton, Alberta, Canada
- **Contact:** `contact@origindatum.space` | `https://origindatum.space/`
- **Effective Date:** 2026-10-29
- **Governing Standard:** WMO Manual on the Global Data-Processing and Forecasting System (GDPFS) & NVIDIA Earth2Studio Validation Guidelines

---

## 1. Executive Summary & Purpose

This protocol defines the authoritative, mandatory procedure for executing, cryptographically sealing, and independently verifying numerical and data-driven atmospheric weather forecasts within Project OD-EARTH2-001.

Following the forensic discovery of target leakage in historical scripts (where predictions were synthesized using linear interpolation against the held-out verifying analysis), this protocol establishes an immutable architectural barrier between **Prediction Generation** and **Verification Evaluation**. 

Under this protocol:
1. **No forecast generation routine may access, inspect, or receive data with timestamp $t \ge t_0 + \Delta t$.**
2. **Every forecast artifact must be cryptographically hashed and sealed in a signed manifest before verification analysis is retrieved.**
3. **Verification must validate the physical integrity and cryptographic hashes of all input and forecast tensors before calculating evaluation metrics.**
4. **All metric computations must employ area-weighted spherical integrals and maintain strict separation between Tendency Anomaly Correlation (TAC) and Climatological Anomaly Correlation (ACC).**

---

## 2. Architectural Separation: The 3-Stage Pipeline

The forecasting and verification workflow is partitioned into three strictly decoupled, sequentially enforced stages:

```
+-------------------------------------------------------------------------+
| STAGE A: FORECAST EXECUTION                                             |
| Input: t0 timestamp, Initial State X(t0), Model Checkpoint & Config     |
| Invariant: Complete information barrier against verifying analysis     |
| Output: forecast_t2m.npy, initial_condition.npy, forecast_meta.json     |
+-------------------------------------------------------------------------+
                                    │
                                    ▼
+-------------------------------------------------------------------------+
| STAGE B: FREEZE & PROVENANCE SEALING                                    |
| Computes SHA-256 for all serialized arrays                              |
| Records git commit SHA, platform environment, model identity invariants |
| Seals: run_manifest.json, hashes.sha256 (Read-Only)                     |
+-------------------------------------------------------------------------+
                                    │
                                    ▼
+-------------------------------------------------------------------------+
| STAGE C: INDEPENDENT VERIFICATION                                       |
| Reads run_manifest.json & validates SHA-256 of all input & forecast npy |
| Retrieves verifying NOAA GFS analysis strictly at t_valid = t0 + dt     |
| Computes latitude-weighted RMSE, MAE, Mean Bias, Skill Score, and TAC   |
| Output: validation_results.json                                         |
+-------------------------------------------------------------------------+
```

### 2.1 Stage A — Forecast Execution (`forecast_stage.py`)
- **Authorized Inputs:**
  - Initialization timestamp $t_0$ (UTC).
  - Atmospheric initial conditions $X(t_0)$ retrieved strictly at $t_0$ from an operational data source (e.g. NOAA GFS 0.25° analysis) or pre-loaded serialized tensor.
  - Model architecture identifier (`model_family`).
  - Model checkpoint weights path and cryptographic digest (`checkpoint_sha256`).
  - Forecast lead time $\Delta t$ (hours).
  - Deterministic random seed (for reproducibility).
- **Prohibited Operations:**
  - Passing future verification data (`verification_truth`) to any model parameter, normalization routine, or residual calculation.
  - Falling back to initial condition persistence while recording neural model family names (facade execution is an integrity violation).
  - Extrapolating or regridding future operational fields to construct predictions.
- **Outputs:**
  - `forecast_t2m.npy`: Predicted meteorological field at $t_0 + \Delta t$.
  - `initial_condition.npy`: Authentic atmospheric state at $t_0$.
  - `forecast_meta.json`: Run parameters, model metadata, and timestamp declarations.

### 2.2 Stage B — Freeze & Cryptographic Sealing (`freeze_stage.py`)
- **Execution Condition:** Invoked strictly after Stage A inference has terminated and arrays are written to disk.
- **Required Operations:**
  - Compute SHA-256 cryptographic digests of all `.npy` array files using 64-KB buffered streams.
  - Dynamically discover the active git commit SHA of the executing code via `git rev-parse HEAD`.
  - Validate model identity invariants: under no circumstances may a Persistence baseline run be declared as a neural model (`FourCastNet`, `SFNO`, `FCN3`, `DLWP`, etc.).
  - Enforce strict equality: declared model family must equal executed model family.
  - Require non-null `checkpoint_sha256` for all neural model architectures.
  - Classify experiment explicitly: `BASELINE_PERSISTENCE` or `REAL_MODEL_FORECAST`.
- **Outputs:**
  - `run_manifest.json`: Cryptographically sealed metadata adhering to Manifest Schema 2.0.0.
  - `hashes.sha256`: SHA-256 checksum manifest compatible with `sha256sum -c`.

### 2.3 Stage C — Independent Verification (`verify_stage.py`)
- **Execution Condition:** Invoked strictly after Stage B manifest is sealed.
- **Required Operations:**
  - Re-read `run_manifest.json` and independently compute SHA-256 digests of all `input_artifacts` and `forecast_artifacts`. If any byte has been tampered with or truncated, raise `ProvenanceIntegrityError` immediately before data retrieval.
  - Validate temporal consistency: $t_{valid} = t_0 + \Delta t$. If timestamps mismatch or cross epochs (e.g. 2026 vs 2024), raise `ChronologyError`.
  - Reject synthetic substitutions: in benchmark mode, reject manifests declaring `TRUTH_CONDITIONED_SYNTHETIC_DIAGNOSTIC` or synthetic model families. Compute statistical residual correlation against the historical leakage formula; if residual correlation exceeds threshold, raise `SyntheticSubstitutionError`.
  - Retrieve verifying NOAA GFS operational analysis strictly at valid time $t_{valid} = t_0 + \Delta t$. Disallow synthetic dummy arrays (e.g. constant 288.15 K).
  - Compute latitude-weighted spatial metrics and tendency anomaly correlations.
- **Outputs:**
  - `validation_results.json`: Summary of verified metrics, status (`VERIFIED_GENUINE`), and baseline comparisons.

---

## 3. Mathematical Foundations & Verification Metrics

All meteorological evaluations must follow spherical geometry principles and standard numerical weather prediction (NWP) scoring rules.

### 3.1 Spherical Latitude-Area Weights
On an equirectangular latitude-longitude grid with latitudes $\phi_i \in [-90^\circ, +90^\circ]$, grid cell surface area decreases with the cosine of latitude. The normalized latitude weight for grid cell $i$ is:

$$w_i = \frac{\cos(\phi_i)}{\frac{1}{N_\text{lat}} \sum_{k=1}^{N_\text{lat}} \cos(\phi_k)}$$

where $\sum_{i=1}^{N_\text{lat}} w_i = N_\text{lat}$.

### 3.2 Latitude-Weighted Root Mean Square Error (RMSE)
For forecast field $\hat{y}_{i,j}$ and verifying operational analysis $y_{i,j}$ on grid of size $N_\text{lat} \times N_\text{lon}$:

$$\text{RMSE}_w = \sqrt{\frac{1}{N_\text{lat} N_\text{lon}} \sum_{i=1}^{N_\text{lat}} \sum_{j=1}^{N_\text{lon}} w_i \left(\hat{y}_{i,j} - y_{i,j}\right)^2}$$

### 3.3 Latitude-Weighted Mean Absolute Error (MAE)

$$\text{MAE}_w = \frac{1}{N_\text{lat} N_\text{lon}} \sum_{i=1}^{N_\text{lat}} \sum_{j=1}^{N_\text{lon}} w_i \left|\hat{y}_{i,j} - y_{i,j}\right|$$

### 3.4 Latitude-Weighted Mean Bias

$$\text{Bias}_w = \frac{1}{N_\text{lat} N_\text{lon}} \sum_{i=1}^{N_\text{lat}} \sum_{j=1}^{N_\text{lon}} w_i \left(\hat{y}_{i,j} - y_{i,j}\right)$$

### 3.5 Forecast Skill Score Relative to Persistence
Persistence is the primary physical baseline, defined as the atmospheric state remaining frozen at initialization: $\hat{y}_\text{pers}(t_0 + \Delta t) = X(t_0)$. The skill score ($\text{SS}$) over persistence is:

$$\text{SS} = 1 - \frac{\text{RMSE}_w(\text{model})}{\text{RMSE}_w(\text{persistence})}$$

- $\text{SS} > 0$: Forecast exhibits predictive skill superior to climatological persistence.
- $\text{SS} = 0$: Forecast performs identically to the initial condition.
- $\text{SS} < 0$: Forecast performs worse than assuming the atmosphere does not change.

### 3.6 Correlation Metrics: ACC vs. TAC
A critical methodological distinction enforced by this protocol is the difference between Climatological Anomaly Correlation (ACC) and Tendency Anomaly Correlation (TAC):

1. **Climatological Anomaly Correlation (ACC):**
   Evaluates deviations from multi-decadal climatological mean fields $\bar{C}$:

   $$\text{ACC} = \frac{\sum_{i,j} w_i (\hat{y}_{i,j} - \bar{C}_{i,j})(y_{i,j} - \bar{C}_{i,j})}{\sqrt{\sum_{i,j} w_i (\hat{y}_{i,j} - \bar{C}_{i,j})^2 \sum_{i,j} w_i (y_{i,j} - \bar{C}_{i,j})^2}}$$

   The universal World Meteorological Organization (WMO) synoptic forecast skill limit of $\text{ACC} \ge 0.60$ applies strictly to 500 hPa geopotential height ($Z_{500}$) climatological anomalies over multi-day horizons.

2. **Tendency Anomaly Correlation (TAC):**
   Evaluates forecast atmospheric change relative to the initial state $X(t_0)$:

   $$\Delta \hat{y}_{i,j} = \hat{y}_{i,j} - X(t_0)_{i,j}, \quad \Delta y_{i,j} = y_{i,j} - X(t_0)_{i,j}$$

   $$\text{TAC} = \frac{\sum_{i,j} w_i \Delta \hat{y}_{i,j} \Delta y_{i,j}}{\sqrt{\sum_{i,j} w_i (\Delta \hat{y}_{i,j})^2 \sum_{i,j} w_i (\Delta y_{i,j})^2}}$$

   **Mandatory Rule:** In short lead-time evaluations ($\Delta t = 24\text{h}$) where multi-decadal climatology is unavailable, researchers must explicitly report metrics as **TAC** (Tendency Anomaly Correlation) and **never** claim compliance with the WMO 0.60 synoptic threshold without explicitly citing reference datasets and climatology baselines.

---

## 4. Manifest Schema 2.0.0 Specification

All frozen forecast stages must produce a `run_manifest.json` conforming to Schema 2.0.0:

```json
{
  "$schema": "https://origindatum.space/schemas/weather-run-manifest-v2.json",
  "manifest_version": "2.0.0",
  "experiment_classification": "BASELINE_PERSISTENCE | REAL_MODEL_FORECAST",
  "timestamp_utc": "ISO-8601 UTC string",
  "git_commit": "40-character hexadecimal git commit SHA",
  "init_time": "ISO-8601 UTC string (t0)",
  "valid_time": "ISO-8601 UTC string (t0 + lead_time_hours)",
  "lead_time_hours": 24,
  "model": {
    "family": "Persistence | FourCastNet | SFNO | FCN3",
    "checkpoint": "model checkpoint path or 'identity'",
    "checkpoint_sha256": "SHA-256 hex digest or null for persistence",
    "configuration": {}
  },
  "environment": {
    "python_version": "3.10.x",
    "platform": "Windows-10-x.x | Linux-x.x",
    "processor": "processor identifier"
  },
  "input_artifacts": [
    {
      "name": "initial_condition.npy",
      "sha256": "64-character hex digest",
      "shape": [721, 1440],
      "dtype": "float32"
    }
  ],
  "forecast_artifacts": [
    {
      "name": "forecast_t2m.npy",
      "sha256": "64-character hex digest",
      "shape": [721, 1440],
      "dtype": "float32",
      "units": "Kelvin"
    }
  ]
}
```

---

## 5. Hardware Constraints & Blocker Policy

Scientific integrity requires complete transparency regarding execution environments and computational resources:

1. **Host Hardware Reality:**
   - Where the host platform lacks CUDA-capable NVIDIA GPUs (e.g. running on AMD GPU or CPU-only with `torch+cpu`), full neural inference forward passes of large transformer or spherical harmonic weights may be computationally infeasible or unsupported by pre-compiled binary wheels.
2. **Blocker Declaration Protocol:**
   - If a neural model cannot be executed due to missing CUDA drivers, missing model weights checkpoints, or API endpoint unavailability, the benchmark runner must:
     a. Explicitly record the status in all reports as `NOT VERIFIED (HARDWARE_BLOCKER: AMD GPU / NO CUDA / MISSING CHECKPOINT)`.
     b. Execute the genuine physical **Persistence baseline** on authentic NOAA GFS operational analysis.
     c. Refuse to manufacture simulated, synthetic, or interpolated neural outputs.
     d. Provide the exact, reproducible execution command for verification on CUDA-enabled hardware.

---

## 6. Anti-Leakage Compliance Certification (Tests A–F)

Before any forecast experiment results are published or accepted into scientific manuscripts, the test suite `od_experiments/tests/test_anti_leakage.py` and `od_experiments/tests/test_remediation_m2.py` must execute cleanly:

| Test Identifier | Test Invariant | Failure Condition | Verification Invariant |
|---|---|---|---|
| **Test A** | Future-Truth Independence | Forecast changes when verifying truth is perturbed | $\partial \hat{y} / \partial y_\text{truth} = 0$ |
| **Test B** | Prediction-Before-Verification | Stage A queries future operational analysis | Zero queries for $t \ge t_0 + \Delta t$ |
| **Test C** | No Synthetic Substitution | Benchmark accepts synthetic residuals or mock formulas | `SyntheticSubstitutionError` raised |
| **Test D** | Provenance Integrity | Modified file bytes accepted during verification | `ProvenanceIntegrityError` raised |
| **Test E** | Chronological Correctness | Mismatched timestamps or cross-epoch truth accepted | `ChronologyError` raised |
| **Test F** | Real Model Identity | Persistence labeled as FourCastNet or model mismatch | `ModelIdentityMismatchError` raised |

---

## 7. Traceable Figure Generation Protocol

All scientific visualizations (spatial maps, error difference fields, and skill time series) must adhere to these rules:
1. Every plot script must load a valid `run_manifest.json` and verify the SHA-256 hashes of input arrays prior to plotting.
2. Figures must strictly separate:
   - Verifying GFS Operational Analysis maps (labeled "NOAA GFS Analysis").
   - Persistence baseline maps (labeled "Persistence Baseline $X(t_0)$").
   - Model forecast predictions (labeled with the exact model name, or omitted if uninstantiated).
   - Real-model error fields ($\hat{y} - y_\text{truth}$).
   - Regional analysis tracking (e.g., minimum sea level pressure centers must be explicitly attributed to the verifying GFS analysis or to the model that actually resolved them).
3. The figure generator must refuse to render plots if array hashes do not match the sealed manifest.
