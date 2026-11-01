# Specification Mining Report: OD-EARTH2-001 Research Lab Architecture

**Project**: Origin Datum Earth-2 Research Lab (OD-EARTH2-001)  
**Investigator**: `spec_miner_survey_1`  
**Date**: 2026-10-26  
**Working Directory**: `d:\programming\Blockchain development\Z-space\earth2studio`  
**Reference Branch**: `feat/od-earth2-001`  
**Integrity Mode**: development  

---

## 1. Executive Summary & Authoritative Specification Sources

This specification mining report defines the precise technical contracts, interfaces, data schemas, error behaviors, and boundary conditions for the **OD-EARTH2-001** project. The objective is to transform the `earth2studio` fork into an isolated, reproducible, zero-cloud-cost scientific research environment prepared for the first genuine AI weather-forecasting experiment for **EO-OBSCURA**.

### Authoritative Sources Probed:
1. **User Requirements**: `.agents/teamwork/ORIGINAL_REQUEST.md` (R1-R4, Acceptance Criteria).
2. **Earth2Studio Core Architecture**:
   - Workflows: `earth2studio/run.py` (`deterministic`, `diagnostic`, `ensemble`).
   - Prognostic Models: `earth2studio/models/px/` (`dlwp.py`, `fcn.py`, `stormscope.py`, `stormscope_meteosat.py`, `atlas.py`, `persistence.py`).
   - Diagnostic Models: `earth2studio/models/dx/` (`corrdiff.py`, `corrdiff_cosmo_era5.py`, `corrdiff_era5_hrrr.py`).
   - Data Assimilation Models: `earth2studio/models/da/` (`healda.py`, `healda_v2.py`).
   - Data Sources: `earth2studio/data/` (`gfs.py`, `arco.py`, `rand.py`, `utils.py`).
   - Statistics & Metrics: `earth2studio/statistics/` (`rmse.py`, `moments.py`, `weights.py`).
   - IO Backends: `earth2studio/io/` (`zarr.py`, `netcdf4.py`, `xarray.py`).
   - Dependency & Import Manager: `earth2studio/utils/imports.py` (`_check_package`, `_parse_optional_dependencies`, `_get_group_packages`).
3. **Repository Packaging & Rules**:
   - `pyproject.toml` (PEP 517/518 build, uv configuration, optional-dependencies, tool configurations).
   - `docs/userguide/about/install_options.yml` (Single source of truth for extra dependencies and install instructions).
   - Coding Rules: `.agents/rules/` (`e2s-000` through `e2s-013`).
   - Antigravity Skills: `skills/` (`earth2studio-install`, `earth2studio-discover`, `earth2studio-deterministic-forecast`, `earth2studio-data-fetch`).
4. **Target Host Environment Probe**:
   - Host OS: Windows 10 (Build 19045-SP0, x86_64).
   - WSL2 Subsystem: Ubuntu 24.04.4 LTS (Noble Numbat, Kernel 6.18.54.1-microsoft-standard-WSL2).
   - Package Manager: `uv 0.13.5` located at `/home/zrt/.local/bin/uv` in WSL.
   - Hardware: AMD Ryzen 5 3600 6-Core (12 threads), 15 GiB RAM allocated to WSL (14 GiB available), 134 GB free disk space on `/mnt/d`.
   - GPU / Accelerator: Discrete NVIDIA GPU / CUDA driver not active in WSL/Windows (`nvidia-smi` unavailable). All baseline forecasting, tests, and CLI tools must support CPU fallback seamlessly.

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | R1: Discovery | Host & WSL2 Hardware Probing | Introspects OS, kernel, CPU model, memory, disk, and CUDA status | None (system calls) | Dict/JSON of system metrics | Returns fallback info if commands fail | System probe / `wsl`, `platform` |
| 2 | R1: Discovery | Virtual Environment Verification | Detects `.venv` or `.venv_wsl`, validates Python >= 3.11, confirms editable install | Path to venv | Status boolean, python path, editable flag | Reports missing venv or non-editable package | `earth2studio/utils/imports.py` |
| 3 | R1: Discovery | Zero Billable Cloud Cost Auditor | Verifies that data sources use public/free buckets without billing or credential leakage | Environment vars, config | Verification report (Passed/Failed) | Raises error or warning if billable credentials configured | `ORIGINAL_REQUEST.md`, `gfs.py` |
| 4 | R2: Architecture | CLI Command: `doctor` | Offline diagnostic command verifying environment, dependencies, and editable install without downloading | `--format`, `--check-optional` | Formatted status table / JSON | Exit code 1 on failed core checks, 0 on pass | `ORIGINAL_REQUEST.md` R2 |
| 5 | R2: Architecture | CLI Command: `inspect` | Offline introspection of models and data sources (schemas, coordinates, variables) | `--model`, `--dataset`, `--format` | Detailed coordinate and metadata JSON/text | Exit code 1 if model/dataset unknown | `ORIGINAL_REQUEST.md` R2 |
| 6 | R2: Architecture | CLI Command: `run` | Executes baseline or prognostic forecast rollout pipeline with provenance tracking | Config path, model name, data source, lead times | Forecast artifacts + `manifest.json` | Exit code 1 on data fetch or model execution failure | `earth2studio/run.py`, R2 |
| 7 | R2: Architecture | CLI Command: `validate` | Evaluates forecast outputs against reference data using scientific statistical metrics | Forecast path, reference path, metrics list | `validation_report.json` + summary | Exit code 1 on coordinate mismatch or NaN metrics | `earth2studio/statistics/`, R2 |
| 8 | R2: Architecture | Configuration Management | Declarative YAML/JSON experiment configuration parser and validator | Path to config file | Validated ExperimentConfig object | ValidationError with line and field info | `pyproject.toml`, standard schemas |
| 9 | R2: Architecture | Provenance Tracker | Hashes all inputs/outputs with SHA-256 and records git SHA, versions, runtime info | Run context, output files | Machine-readable `manifest.json` | Raises IOError if artifact cannot be hashed | `ORIGINAL_REQUEST.md` R2 |
| 10 | R2: Architecture | Credential Scrubber | Scans environment, config, and metadata to scrub any API keys, tokens, or credentials | Dict/object with config/runtime info | Cleaned dictionary with sensitive values redacted | Raises SecurityError if leak detected in public field | `ORIGINAL_REQUEST.md` R2 |
| 11 | R2: Architecture | Test Suite | Comprehensive pytest test suite for config, doctor, inspect, provenance, security, validation | pytest invocation | Test reports and coverage | Assertion failures with precise diffs | `pyproject.toml`, `test/` |
| 12 | R3: Pipeline | Baseline Forecast: Persistence | Built-in zero-download, CPU-capable forecast baseline using identity operator over time | Time, variables, domain coords, lead steps | IOBackend array with forecast states | Validates input coordinates against domain | `earth2studio/models/px/persistence.py` |
| 13 | R3: Pipeline | Baseline Forecast: DLWP | 7-variable global weather forecast model (6h time step) on cubed sphere | t-6h, t0 initial state (t2m, t850, z500, etc.) | Rollout states at +6h, +12h, ... | Raises OptionalDependencyError if dlwp extra missing | `earth2studio/models/px/dlwp.py` |
| 14 | R3: Pipeline | Open Data Ingestion: GFS / GFS_FX | Fetches NOAA GFS analyses and operational forecasts from AWS Open Data (no billing) | Time, lead_time, variable | xarray DataArray / tensor | Retries transient errors, fails on missing time | `earth2studio/data/gfs.py` |
| 15 | R3: Pipeline | Offline Test Ingestion: Random | Generates synthetic Gaussian atmospheric fields matching coordinate schemas | Time, variable, domain coords | Synthesized DataArray | Raises ValueError on bad domain coords | `earth2studio/data/rand.py` |
| 16 | R3: Pipeline | Metric: MAE | Latitude-weighted Mean Absolute Error between forecast and reference tensors | Pred tensor, True tensor, coords | Metric scalar/tensor per variable | Raises CoordinateError if dimensions mismatched | `earth2studio/statistics/rmse.py` |
| 17 | R3: Pipeline | Metric: RMSE | Latitude-weighted Root Mean Square Error between forecast and reference | Pred tensor, True tensor, coords | Metric scalar/tensor per variable | Raises CoordinateError if dimensions mismatched | `earth2studio/statistics/rmse.py` |
| 18 | R3: Pipeline | Metric: Mean Bias | Latitude-weighted signed mean error ($\text{pred} - \text{ref}$) | Pred tensor, True tensor, coords | Metric scalar/tensor per variable | Raises CoordinateError if dimensions mismatched | `earth2studio/statistics/moments.py` |
| 19 | R4: Registry | DLWP Model Entry | Documents DLWP architecture, variables, resolution, weights, hardware, extra dependencies | Registry query | DLWP specification card | N/A (Documentation/Registry) | `earth2studio/models/px/dlwp.py` |
| 20 | R4: Registry | FourCastNet Model Entry | Documents FCN/FCN3 AFNO global forecast models (26 variables, 0.25°, 6h step) | Registry query | FCN specification card | N/A (Documentation/Registry) | `earth2studio/models/px/fcn.py` |
| 21 | R4: Registry | StormScope EU Model Entry | Documents StormScopeMeteosatEU generative diffusion nowcaster (16 FCI channels, 2km) | Registry query | StormScope EU specification card | N/A (Documentation/Registry) | `earth2studio/models/px/stormscope_meteosat.py` |
| 22 | R4: Registry | Atlas Model Entry | Documents Atlas stochastic interpolant multi-scale prognostic model (73 variables) | Registry query | Atlas specification card | N/A (Documentation/Registry) | `earth2studio/models/px/atlas.py` |
| 23 | R4: Registry | CorrDiff Model Entry | Documents CorrDiff km-scale super-resolution diffusion models (COSMO, HRRR, Taiwan) | Registry query | CorrDiff specification card | N/A (Documentation/Registry) | `earth2studio/models/dx/corrdiff.py` |
| 24 | R4: Registry | HealDA Model Entry | Documents HealDA spherical variational data assimilation on HEALPix grid | Registry query | HealDA specification card | N/A (Documentation/Registry) | `earth2studio/models/da/healda.py` |
| 25 | R4: Registry | Setup Guide: `EARTH2_SETUP.md` | Step-by-step reproducible setup guide for WSL2/Windows, uv virtualenv, CLI usage | User reading guide | Markdown documentation | N/A (Documentation) | `ORIGINAL_REQUEST.md` R4 |

---

## 3. Edge Cases & Boundary Conditions

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | `doctor` CLI | System with no NVIDIA GPU (CPU-only) | Detects `torch.cuda.is_available() == False`; gracefully reports CPU mode without failing; confirms core operations remain functional. |
| 2 | `doctor` CLI | Network offline / airgapped execution | Offline flag ensures no HTTP requests or socket connections to remote servers; tests local packages only. |
| 3 | `doctor` CLI | Package installed in non-editable mode | Detects package location outside git root directory; warns or flags that development edits will not take effect. |
| 4 | `inspect` CLI | Non-existent model name (e.g. `--model nonexistent`) | Returns clean error listing available models (`dlwp`, `fcn`, `atlas`, `persistence`, etc.) with exit code 1. |
| 5 | `run` CLI | Input data containing NaNs | Sanitizes NaNs or raises clear DataIntegrityError before feeding to prognostic model iterator. |
| 6 | `run` CLI | Lead time mismatch with model step size | DLWP/FCN expect 6h step intervals; non-multiple lead times (e.g. 5h) trigger coordinate alignment error. |
| 7 | `run` CLI | Interrupted execution / partial rollout | Checkpoint mechanism or manifest status records incomplete run; prevents corrupt manifest generation. |
| 8 | `validate` CLI | Spatial grid mismatch between forecast and reference | Validates `lat` and `lon` arrays with `handshake_coords`; raises coordinate mismatch error before computing metrics. |
| 9 | `validate` CLI | Reference data has missing timestamps | Fails with informative MissingTimestampsError rather than silently computing metrics on partial data. |
| 10 | Provenance Tracker | Git working tree is dirty (uncommitted changes) | Manifest records `git.dirty: true` and logs warning while preserving exact commit SHA. |
| 11 | Credential Scrubber | User sets `AWS_SECRET_ACCESS_KEY` or `HUGGINGFACE_TOKEN` | Scrubber redacts value to `"[REDACTED]"` in all outputs and manifests; raises security warning if detected in public config. |
| 12 | Latitude Weighting | Latitudes including exact poles (-90, +90 degrees) | $\cos(\pm 90^\circ) = 0$; weights clamp to zero at poles without generating NaN or division-by-zero during normalization. |

---

## 4. Detailed Specification per User Requirement

### 4.1 Requirement R1: Environment Discovery & Reproducible Setup

#### Objective:
Discover hardware capabilities across Windows 10 and WSL2/Ubuntu, establish an isolated virtual environment (`.venv` or `.venv_wsl`) with editable installation of `earth2studio`, and enforce a zero-billable-cloud-cost guarantee.

#### Hardware Discovery Specifications:
- **Host Detection**:
  - Windows OS: `platform.system() == "Windows"`, `platform.release() == "10"`, `platform.version() == "10.0.19045"`.
  - Architecture: `x86_64` (AMD64).
  - WSL2 Presence: Detected via `wsl --status` or `wsl --list --verbose` returning Ubuntu (version 2).
- **Subsystem & Kernel (WSL2)**:
  - Linux Kernel: `6.18.54.1-microsoft-standard-WSL2`.
  - Distribution: `Ubuntu 24.04.4 LTS (Noble Numbat)`.
  - CPU: AMD Ryzen 5 3600 6-Core Processor (12 threads).
  - Memory: 15 GiB total RAM in WSL (14 GiB available).
  - Storage: Filesystem `/mnt/d` (3.7 TB, 134 GB available).
  - Acceleration Status: CUDA is currently not exposed in WSL2 (CPU-only execution).
- **Python Runtime**:
  - Windows Python: Python 3.10.11 (Note: `pyproject.toml` requires `>=3.11,<3.15`).
  - WSL2 Python: Python 3.12.3 (`/usr/bin/python3.12`) and Python 3.13 (`/home/zrt/.local/share/uv/python/cpython-3.13-linux-x86_64-gnu/bin/python3.13`).
  - Recommended Target Environment: WSL2 with Python 3.12 or 3.13 using `uv 0.13.5`.

#### Virtual Environment & Editable Install Specification:
- Virtual environment path: `.venv` (Python 3.13) or `.venv_wsl` (Python 3.12).
- Creation command:
  ```bash
  /home/zrt/.local/bin/uv venv .venv --python 3.13
  # or
  /home/zrt/.local/bin/uv venv .venv_wsl --python 3.12
  ```
- Editable Installation Command:
  ```bash
  uv pip install -e .
  ```
- Verification Rule:
  Executing:
  ```python
  import earth2studio
  assert "earth2studio" in earth2studio.__file__
  ```
  must return the local repository path rather than site-packages.

#### Zero Billable Cloud Cost Specification:
- **Permitted Sources**:
  1. NOAA GFS Open Data (`s3://noaa-gfs-bdp-pds`): Public S3 bucket hosted by NOAA Open Data Program. Requester pays nothing, no AWS account or billing required.
  2. Google Cloud ARCO ERA5: Open public Google Cloud dataset. Free public access.
  3. Local synthetic sources (`earth2studio.data.Random`).
  4. Local cached datasets in `$EARTH2STUDIO_CACHE` or `.cache/`.
- **Prohibited Sources / Configurations**:
  1. Billable AWS buckets without requester pays waiver.
  2. Commercial weather APIs requiring metered credit cards.
  3. Any process invoking billable cloud provisioning tools (`gcloud`, `aws`, `terraform`).

---

### 4.2 Requirement R2: Isolated Origin Datum Research Architecture

#### Objective:
Implement `od_experiments/earth2_001` as an isolated, standalone research CLI package with commands (`doctor`, `inspect`, `run`, `validate`), robust configuration management, provenance tracking with SHA-256 digests, and strict credential exclusion.

#### Code Architecture & File Layout:
```
earth2studio/
├── od_experiments/
│   ├── __init__.py
│   └── earth2_001/
│       ├── __init__.py
│       ├── cli.py             # Main CLI dispatcher (argparse/click/typer)
│       ├── config.py          # Experiment configuration model & validator
│       ├── doctor.py          # Offline environment & hardware auditor
│       ├── inspect.py         # Model & dataset schema introspector
│       ├── run.py             # Forecast pipeline execution engine
│       ├── validate.py        # Statistical validation engine (MAE, RMSE, Bias)
│       ├── provenance.py      # Manifest generator & SHA-256 integrity manager
│       └── security.py        # Secret scanner & environment scrubber
├── test/
│   └── od_experiments/
│       ├── __init__.py
│       ├── test_config.py
│       ├── test_doctor.py
│       ├── test_inspect.py
│       ├── test_provenance.py
│       ├── test_security.py
│       ├── test_validation.py
│       └── test_cli.py
└── docs/
    └── origin_datum/
        └── EARTH2_SETUP.md
```

#### CLI Interface Contracts:

##### 1. `python -m od_experiments.earth2_001.cli doctor`
- **Purpose**: Offline environment verification and hardware capability discovery.
- **Parameters**:
  - `--format`: `text` (default) or `json`.
  - `--check-optional`: List of optional extra groups to inspect (e.g. `dlwp`, `fcn`, `data`).
  - `--offline`: Flag enforcing zero network calls (default: `true`).
- **Exit Codes**:
  - `0`: All core requirements satisfied (Python >= 3.11, editable install valid, core packages present).
  - `1`: Core requirement failed (Python version incompatible, earth2studio not importable, missing core dependencies).
  - `2`: Configuration error or invalid flags.
- **Console Output Example**:
  ```text
  [OD-EARTH2-001] Environment Diagnostic (Offline Mode)
  ======================================================
  OS: Linux 6.18.54.1-microsoft-standard-WSL2 (Ubuntu 24.04.4 LTS)
  CPU: AMD Ryzen 5 3600 6-Core Processor (12 cores)
  RAM: 15.0 GiB Total (14.0 GiB Available)
  Disk Space: 134.0 GiB Available on /mnt/d
  CUDA Status: Not Available (CPU Fallback Enabled)
  Python Version: 3.13.2 (/mnt/d/programming/.../.venv/bin/python)
  Earth2Studio Install: Editable (Local Path: ./earth2studio)
  Core Dependencies: All Satisfied (torch, numpy, xarray, obstore, loguru)
  Zero Billable Cost Status: Verified (No billable cloud credentials detected)
  Status: PASSED
  ```

##### 2. `python -m od_experiments.earth2_001.cli inspect`
- **Purpose**: Schema and metadata inspection of prognostic models and data sources without downloading checkpoints.
- **Parameters**:
  - `--model`: Model identifier (`dlwp`, `fcn`, `stormscope`, `atlas`, `corrdiff`, `healda`, `persistence`).
  - `--dataset`: Dataset identifier (`gfs`, `gfs_fx`, `arco`, `random`).
  - `--list`: `models`, `datasets`, or `all`.
  - `--format`: `text` (default) or `json`.
- **Exit Codes**:
  - `0`: Schema resolved and emitted successfully.
  - `1`: Requested model or dataset not recognized.

##### 3. `python -m od_experiments.earth2_001.cli run`
- **Purpose**: Execute forecast experiment with parameter validation, rollout generation, and provenance tracking.
- **Parameters**:
  - `--config`: Path to experiment YAML or JSON configuration file.
  - `--model`: Override model name (e.g. `persistence` or `dlwp`).
  - `--data-source`: Override data source (`gfs`, `arco`, `random`).
  - `--start-time`: Forecast initialization timestamp in ISO-8601 (e.g. `2024-01-01T00:00:00`).
  - `--nsteps`: Number of forecast rollout steps (integer >= 1).
  - `--output-dir`: Output destination directory for forecast data and manifest.
  - `--device`: Target execution device (`cpu` or `cuda`).
  - `--dry-run`: Validate pipeline configuration and coordinates without executing rollout.
- **Exit Codes**:
  - `0`: Forecast completed, artifacts written, and manifest signed.
  - `1`: Runtime execution failed (data fetch error, model forward error).
  - `2`: Configuration or coordinate handshake failure.

##### 4. `python -m od_experiments.earth2_001.cli validate`
- **Purpose**: Calculate statistical scientific validation metrics (MAE, RMSE, Mean Bias) against reference baseline data.
- **Parameters**:
  - `--forecast`: Path to forecast artifact (Zarr, NetCDF4, or NPZ).
  - `--reference`: Path to reference truth dataset or reference source specification.
  - `--metrics`: Comma-separated list of metrics (e.g. `mae,rmse,mean_bias`).
  - `--reduction-dims`: Comma-separated reduction dimensions (default: `lat,lon`).
  - `--latitude-weighting`: Boolean toggle for cosine latitude weighting (default: `true`).
  - `--output`: Path to write output `validation_report.json`.
- **Exit Codes**:
  - `0`: Validation computed successfully, report generated.
  - `1`: Validation failed (coordinate mismatch, NaN encounter, missing variable).

#### Provenance Manifest Specification (`manifest.json`):
Every forecast execution must create a canonical `manifest.json` in the run's output directory.
JSON Schema structure:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "OriginDatumExperimentManifest",
  "type": "object",
  "required": [
    "manifest_version",
    "experiment_id",
    "timestamp_utc",
    "git",
    "environment",
    "parameters",
    "artifacts",
    "security_audit"
  ],
  "properties": {
    "manifest_version": { "type": "string", "enum": ["1.0.0"] },
    "experiment_id": { "type": "string" },
    "timestamp_utc": { "type": "string", "format": "date-time" },
    "git": {
      "type": "object",
      "required": ["commit_sha", "branch", "dirty"],
      "properties": {
        "commit_sha": { "type": "string" },
        "branch": { "type": "string" },
        "dirty": { "type": "boolean" },
        "remote_url": { "type": "string" }
      }
    },
    "environment": {
      "type": "object",
      "required": ["os", "python_version", "editable_install", "device"],
      "properties": {
        "os": { "type": "string" },
        "kernel": { "type": "string" },
        "python_version": { "type": "string" },
        "python_path": { "type": "string" },
        "editable_install": { "type": "boolean" },
        "device": { "type": "string" },
        "cuda_available": { "type": "boolean" },
        "cpu_model": { "type": "string" },
        "ram_total_gb": { "type": "number" }
      }
    },
    "parameters": {
      "type": "object",
      "properties": {
        "model": { "type": "string" },
        "data_source": { "type": "string" },
        "start_time": { "type": "string" },
        "nsteps": { "type": "integer" },
        "variables": { "type": "array", "items": { "type": "string" } }
      }
    },
    "artifacts": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["file_name", "file_size_bytes", "sha256", "content_type"],
        "properties": {
          "file_name": { "type": "string" },
          "file_size_bytes": { "type": "integer" },
          "sha256": { "type": "string", "pattern": "^[a-f0-9]{64}$" },
          "content_type": { "type": "string" }
        }
      }
    },
    "security_audit": {
      "type": "object",
      "required": ["secrets_scrubbed", "credential_leakage_detected"],
      "properties": {
        "secrets_scrubbed": { "type": "boolean" },
        "credential_leakage_detected": { "type": "boolean" },
        "scanned_variable_count": { "type": "integer" }
      }
    }
  }
}
```

#### Secret Exclusion & Zero Credential Leakage:
1. **Scrubbing Engine**:
   All runtime metadata, configuration dumps, environment snapshots, and log messages must pass through a strict filter regex:
   ```python
   SENSITIVE_PATTERNS = [
       r"(?i).*API_?KEY.*",
       r"(?i).*TOKEN.*",
       r"(?i).*SECRET.*",
       r"(?i).*PASSWORD.*",
       r"(?i).*AUTH.*",
       r"(?i).*CREDENTIAL.*",
       r"(?i).*AWS_.*",
       r"(?i).*CDSAPI.*",
       r"(?i).*HF_.*",
       r"(?i).*NGC_.*",
   ]
   ```
2. Any matched keys must have their values replaced with `"[REDACTED]"`.
3. If any sensitive string matching token formats (e.g. `hf_[a-zA-Z0-9]{34}`, `AKIA[0-9A-Z]{16}`) is detected in any written artifact, the process must immediately abort and raise `CredentialLeakageError`.

---

### 4.3 Requirement R3: Genuine Forecasting & Scientific Validation Pipeline

#### Objective:
Execute a verified, zero-cost baseline weather forecast and evaluate it against reference atmospheric data using rigorous statistical metrics (MAE, RMSE, Mean Bias).

#### Forecast Execution Workflow:
1. **Initial Condition Ingestion**:
   - Primary: NOAA GFS Analysis via `earth2studio.data.GFS` (public AWS bucket, no billing).
   - Offline/Test: `earth2studio.data.Random` (pure synthetic Gaussian field matching GFS coordinate schema).
2. **Forecast Model Rollout**:
   - Baseline Model: `earth2studio.models.px.Persistence` (built-in baseline, zero download, executes on CPU in milliseconds).
   - AI Weather Model: `earth2studio.models.px.DLWP` (7 atmospheric variables, 6h step) or `earth2studio.models.px.FCN` where checkpoint cache is available.
3. **Artifact Storage**:
   - Forecast output stored in NetCDF4, Zarr, or NPZ format with coordinate axes `[time, lead_time, variable, lat, lon]`.
   - SHA-256 digest computed for every output file.

#### Reference Truth Data:
- Operational Verification: NOAA GFS Forecast (`earth2studio.data.GFS_FX`) or analysis at $t + \Delta t$ (`earth2studio.data.GFS`).
- Evaluation Timesteps: $t + 6\text{h}, t + 12\text{h}, t + 18\text{h}, t + 24\text{h}$.

#### Mathematical Metric Formulations:
For forecast tensor $\hat{Y}$ and reference tensor $Y$ over grid points with latitude $\phi_j$:

1. **Latitude Cosine Weighting**:
   $$w_j = \cos\left(\frac{\pi \cdot \phi_j}{180}\right)$$
   Normalized weights: $\tilde{w}_j = \frac{w_j}{\frac{1}{N_{\text{lat}}} \sum_k w_k}$.

2. **Mean Absolute Error (MAE)**:
   $$\text{MAE}(v, \tau) = \frac{1}{\sum_{j=1}^{N_{\text{lat}}} \tilde{w}_j \cdot N_{\text{lon}}} \sum_{j=1}^{N_{\text{lat}}} \sum_{k=1}^{N_{\text{lon}}} \tilde{w}_j \left| \hat{Y}(\tau, v, j, k) - Y(\tau, v, j, k) \right|$$

3. **Root Mean Square Error (RMSE)**:
   $$\text{RMSE}(v, \tau) = \sqrt{\frac{1}{\sum_{j=1}^{N_{\text{lat}}} \tilde{w}_j \cdot N_{\text{lon}}} \sum_{j=1}^{N_{\text{lat}}} \sum_{k=1}^{N_{\text{lon}}} \tilde{w}_j \left( \hat{Y}(\tau, v, j, k) - Y(\tau, v, j, k) \right)^2}$$

4. **Mean Bias (Mean Signed Difference)**:
   $$\text{Bias}(v, \tau) = \frac{1}{\sum_{j=1}^{N_{\text{lat}}} \tilde{w}_j \cdot N_{\text{lon}}} \sum_{j=1}^{N_{\text{lat}}} \sum_{k=1}^{N_{\text{lon}}} \tilde{w}_j \left( \hat{Y}(\tau, v, j, k) - Y(\tau, v, j, k) \right)$$

#### Output Validation Report Schema (`validation_report.json`):
```json
{
  "validation_version": "1.0.0",
  "experiment_id": "exp_baseline_001",
  "timestamp_utc": "2026-10-26T04:30:00Z",
  "forecast_source": "persistence",
  "reference_source": "gfs",
  "latitude_weighted": true,
  "summary_metrics": {
    "t2m": {
      "mae": 1.84,
      "rmse": 2.35,
      "mean_bias": -0.12
    },
    "z500": {
      "mae": 42.1,
      "rmse": 55.4,
      "mean_bias": 1.25
    }
  },
  "metrics_by_lead_time": {
    "6h": {
      "t2m": { "mae": 1.12, "rmse": 1.45, "mean_bias": -0.05 },
      "z500": { "mae": 22.4, "rmse": 28.9, "mean_bias": 0.45 }
    },
    "12h": {
      "t2m": { "mae": 1.65, "rmse": 2.10, "mean_bias": -0.10 },
      "z500": { "mae": 38.2, "rmse": 48.7, "mean_bias": 0.90 }
    }
  }
}
```

---

### 4.4 Requirement R4: Comprehensive Model Registry & Documentation

#### Objective:
Catalog and document the 6 candidate AI models (DLWP, FourCastNet, StormScope EU, Atlas, CorrDiff, HealDA) and provide a reproducible setup and operation guide in `docs/origin_datum/EARTH2_SETUP.md`.

#### Model Registry Specifications:

| Model | Class / Package | Domain | Resolution / Grid | Variables | Step Size | Checkpoint Source | Target Hardware | Optional Extra |
|---|---|---|---|---|---|---|---|---|
| **DLWP** | `earth2studio.models.px.DLWP` | Global | 0.25° (721×1440) Equirectangular / [6,64,64] Cubed Sphere | 7 vars (`t850`, `z1000`, `z700`, `z500`, `z300`, `tcwv`, `t2m`) | 6 hours | NGC (`ngc://models/nvidia/modulus/modulus_dlwp_cubesphere@v0.2`) | GPU (40GB) or CPU (small batch) | `earth2studio[dlwp]` |
| **FourCastNet** | `earth2studio.models.px.FCN` | Global | 0.25° (720×1440) Equirectangular (South Pole excluded) | 26 atmospheric surface & upper-air variables | 6 hours | HuggingFace (`hf://nvidia/fourcastnet1@c67a63995f6...`) | GPU (40GB badge) | `earth2studio[fcn]` |
| **StormScope EU** | `earth2studio.models.px.StormScopeMeteosatEU` | Europe Regional | 2 km MTG-I1 FCI Native Pixel Grid | 16 FCI visible, NIR, and IR channels | 10 minutes | HuggingFace (`hf://nvidia/stormscope-meteosat@17148d...`) | CUDA GPU (BF16 autocast) | `earth2studio[stormscope]` |
| **Atlas** | `earth2studio.models.px.Atlas` | Global | 0.25° (721×1440) Equirectangular | 73 vars (multi-level u, v, z, t across 13 pressure levels + surface) | 6 hours | HuggingFace (`hf://nvidia/atlas-era5@893a38550aa...`) | High-end GPU (TF32 override enabled) | `earth2studio[atlas]` |
| **CorrDiff** | `earth2studio.models.dx.CorrDiff` (variants: `CorrDiffCosmoEra5`, `CorrDiffEra5Hrrr`) | Regional (Europe, CONUS, Taiwan) | 2 km - 3 km km-scale target grid | Radar reflectivity, 10m wind, 2m temp, precipitation | Diagnostic (Single Step) | NGC (`catalog.ngc.nvidia.com/.../corrdiff_inference_package`) & HF | High-memory GPU (40GB-80GB) | `earth2studio[corrdiff]`, `cosmo` |
| **HealDA** | `earth2studio.models.da.HealDA` (and `HealDAv2`) | Global | HEALPix spherical grid or 181×360 / 721×1440 Lat-Lon | 70+ vars (satellite radiances & conventional observations) | Analysis window (-21h to +3h) | HuggingFace (`hf://nvidia/healda@28e22277aab...`) | CUDA GPU (requires CuPy & cuDF) | `earth2studio[da-healda]` |

#### Setup Guide Structure (`docs/origin_datum/EARTH2_SETUP.md`):
1. **Introduction & Scientific Context (EO-OBSCURA / Origin Datum)**.
2. **Hardware & Prerequisite Discovery**:
   - Supported operating systems (WSL2 Ubuntu 24.04 LTS recommended, Windows 10 host).
   - CPU vs. GPU operation modes.
   - Package manager installation (`uv`).
3. **Step-by-Step Environment Setup**:
   - Cloning repository and checking out `feat/od-earth2-001`.
   - Creating `.venv` or `.venv_wsl`.
   - Performing editable install (`uv pip install -e .`).
4. **Offline Diagnostic Verification**:
   - Running `python -m od_experiments.earth2_001.cli doctor`.
   - Verifying zero-billable-cost compliance.
5. **Running Baseline & AI Forecasts**:
   - Step 1: Introspect model schema (`python -m od_experiments.earth2_001.cli inspect --model persistence`).
   - Step 2: Execute forecast rollout (`python -m od_experiments.earth2_001.cli run --config configs/baseline.yaml`).
   - Step 3: Run validation metrics (`python -m od_experiments.earth2_001.cli validate --forecast ... --reference ...`).
6. **Provenance & Security Auditing**:
   - Inspecting `manifest.json` and checking SHA-256 digests.
   - Verifying zero credential leakage.

---

## 5. Verification & Acceptance Criteria Matrix

| Criterion | Requirement | Verification Method | Target Output / Acceptance Condition |
|---|---|---|---|
| AC-1 | R1: Editable Install | `python -c "import earth2studio; print(earth2studio.__file__)"` inside virtualenv | Must point to local workspace `.../earth2studio/__init__.py`. |
| AC-2 | R1: Hardware Discovery | `python -m od_experiments.earth2_001.cli doctor` | Accurately prints OS, CPU, RAM, disk, and CUDA status without crashing on CPU. |
| AC-3 | R1: Zero Billable Cost | `doctor` auditor check | Reports `PASSED` when no billable cloud account or paid API key is present. |
| AC-4 | R2: Offline Doctor | `python -m od_experiments.earth2_001.cli doctor --offline` | Succeeds without any outbound network calls or model downloads. |
| AC-5 | R2: Schema Inspection | `python -m od_experiments.earth2_001.cli inspect --model dlwp` | Prints input/output dimensions, lead times, variables, and resolution. |
| AC-6 | R2: Test Suite | `pytest test/od_experiments/` | 100% tests pass covering config, doctor, inspect, provenance, security, validation. |
| AC-7 | R2: Provenance Manifest | `python -m od_experiments.earth2_001.cli run` | Produces `manifest.json` matching JSON schema with valid git SHA and SHA-256 hashes. |
| AC-8 | R2: Secret Exclusion | Unit test with injected dummy API tokens | Scrubber scrubs tokens; test fails if any token appears in manifest or console output. |
| AC-9 | R3: Scientific Validation | `python -m od_experiments.earth2_001.cli validate` | Produces `validation_report.json` with MAE, RMSE, and Mean Bias per variable. |
| AC-10 | R4: Registry & Guide | Inspection of `docs/origin_datum/EARTH2_SETUP.md` | Contains complete documentation of 6 candidate models and reproducible instructions. |
