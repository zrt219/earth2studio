# Project: OD-EARTH2-001 Research Lab

## Architecture
- **Repository Context**: NVIDIA Earth2Studio fork on branch `feat/od-earth2-001` (aligned with `main` at `39ef89c`).
- **Target Subsystem**: Isolated research package `od_experiments/earth2_001` and documentation in `docs/origin_datum/EARTH2_SETUP.md`.
- **Runtime Environment**: WSL2 Ubuntu 24.04 LTS on AMD Ryzen 5 3600 (6-core/12-thread), 32 GB RAM, AMD Radeon RX 9060 XT (no CUDA; CPU execution fallback required for PyTorch). Python 3.12/3.13 managed via `uv 0.13.5`.
- **Data Flow**:
  1. Input data: Free NOAA GFS analysis via anonymous AWS Open Data S3 (`s3://noaa-gfs-bdp-pds`, zero cost) or offline synthetic `Random`.
  2. Forecast models: Built-in `Persistence` baseline (zero weight download, offline CPU) and `DLWP` (public anonymous NGC checkpoint, CPU inference).
  3. Output artifacts: Forecast netCDF/zarr/npy arrays, `provenance_manifest.json` (SHA-256 hashes, git commit, runtime metadata, redacted credentials), and `validation_report.json` (MAE, RMSE, Mean Bias).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Hardware & Host Discovery | Probes CPU, memory, disk, OS, and GPU/CUDA status; reports CPU fallback | M1 | Survey / R1 |
| F2 | Environment & Editable Install | Verifies editable installation of `earth2studio` in `.venv` / `.venv_wsl` using `uv`, confirming zero billable cloud cost | M1 | Survey / R1 |
| F3 | Isolated Architecture Package | Implements `od_experiments/earth2_001` with modular structure, config schema, and execution primitives | M2 | Survey / R2 |
| F4 | CLI `doctor` Command | Offline diagnostic checking dependencies, editable install, hardware, and environment | M2 | Survey / R2 |
| F5 | CLI `inspect` Command | Schema introspection for Earth2Studio models, data sources, and experiment configs | M2 | Survey / R2 |
| F6 | Cryptographic Provenance Manifest | Emits `manifest.json` with commit SHA, runtime metadata, config parameters, and SHA-256 digests | M2 | Survey / R2 |
| F7 | Security Scrubber | Sanitizes environment, logs, and manifests to ensure zero credential/token leakage | M2 | Survey / R2 |
| F8 | Core Architecture Test Suite | PyTest suite under `test/od_experiments/` testing doctor, inspect, config, security, and provenance | M2 | Survey / R2 |
| F9 | Baseline & Neural Forecasting Pipeline | CLI `run` subcommand executing genuine zero-cost forecast (Persistence baseline & DLWP + GFS) | M3 | Survey / R3 |
| F10 | Scientific Validation Pipeline | CLI `validate` subcommand computing latitude-weighted MAE, RMSE, and Mean Bias against truth data | M3 | Survey / R3 |
| F11 | Candidate Models Registry | Detailed documentation of DLWP, FourCastNet, StormScope EU, Atlas, CorrDiff, and HealDA | M4 | Survey / R4 |
| F12 | Reproducible Setup Guide | Authoritative documentation in `docs/origin_datum/EARTH2_SETUP.md` for WSL2 setup and reproduction | M4 | Survey / R4 |
| F13 | E2E Dual-Track Acceptance Verification | End-to-end verification of all acceptance criteria with forensic integrity audit | M5 | Survey / R1-R4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Environment Discovery & Reproducible Setup | F1, F2 | none | IN_PROGRESS |
| M2 | Isolated Research Architecture & CLI | F3, F4, F5, F6, F7, F8 | M1 | PLANNED |
| M3 | Genuine Forecasting & Scientific Validation Pipeline | F9, F10 | M2 | PLANNED |
| M4 | Comprehensive Model Registry & Documentation | F11, F12 | M1, M2 | PLANNED |
| M5 | E2E Acceptance Verification & Final Audit | F13 | M1, M2, M3, M4 | PLANNED |

## Interface Contracts

### 1. CLI Interface (`od_experiments.earth2_001.cli`)
- `python -m od_experiments.earth2_001.cli doctor [--json]`
  - Exit code 0 if dependencies, editable install, and hardware checks pass.
  - Offline only: no network connections allowed.
- `python -m od_experiments.earth2_001.cli inspect [--model MODEL] [--dataset DATASET] [--json]`
  - Outputs JSON schema with coordinates, variables, resolutions, time-step.
- `python -m od_experiments.earth2_001.cli run --config PATH [--output-dir DIR] [--device {cpu,cuda}]`
  - Runs forecast pipeline, generates output tensors and `provenance_manifest.json`.
- `python -m od_experiments.earth2_001.cli validate --forecast PATH --reference PATH [--output-dir DIR]`
  - Computes MAE, RMSE, Mean Bias across time and spatial dimensions; outputs `validation_report.json`.

### 2. Provenance Manifest Schema (`provenance_manifest.json`)
```json
{
  "manifest_version": "1.0.0",
  "experiment_id": "od_earth2_001",
  "timestamp_utc": "YYYY-MM-DDTHH:MM:SSZ",
  "git": {
    "commit_sha": "string",
    "branch": "string",
    "dirty": false
  },
  "environment": {
    "os": "string",
    "python_version": "string",
    "torch_version": "string",
    "earth2studio_version": "string",
    "device": "cpu"
  },
  "configuration": {},
  "artifacts": [
    {
      "path": "string",
      "sha256": "string",
      "bytes": 0
    }
  ]
}
```

### 3. Scientific Validation Report Schema (`validation_report.json`)
```json
{
  "metrics": {
    "variable_name": {
      "mae": 0.0,
      "rmse": 0.0,
      "mean_bias": 0.0,
      "lead_time_hours": 6
    }
  },
  "evaluation_metadata": {
    "lat_weighted": true,
    "spatial_dims": ["lat", "lon"],
    "num_samples": 1
  }
}
```

## Code Layout
```
od_experiments/
└── earth2_001/
    ├── __init__.py
    ├── cli.py                  # Entry point: doctor, inspect, run, validate
    ├── config.py               # Pydantic/dataclass experiment configuration
    ├── doctor.py               # Offline environment and dependency diagnostic
    ├── inspect.py              # Schema and capability introspection
    ├── pipeline.py             # Forecast runner (Persistence & DLWP with GFS)
    ├── validation.py           # Statistical metrics: MAE, RMSE, Mean Bias
    ├── provenance.py           # Manifest generator and SHA-256 calculation
    └── security.py             # Secret detection and credential scrubber

test/
└── od_experiments/
    ├── __init__.py
    ├── conftest.py             # Fixtures for offline testing & mock models
    ├── test_doctor.py          # Offline diagnostic verification
    ├── test_inspect.py         # Schema introspection tests
    ├── test_security.py        # Credential scrubber tests
    ├── test_provenance.py      # Manifest & SHA-256 tests
    ├── test_validation.py      # Metric calculations against known references
    └── test_cli_e2e.py         # End-to-end CLI integration tests

docs/
└── origin_datum/
    └── EARTH2_SETUP.md         # Comprehensive setup guide & model registry
```
