# Original User Request

## 2026-10-26T04:01:44Z

Build Origin Datum Earth-2 Research Lab: Set up our Earth2Studio fork into a working, reproducible scientific research environment (OD-EARTH2-001), verify dependencies, and prepare the first genuine AI weather-forecasting experiment for EO-OBSCURA.

Working directory: d:\programming\Blockchain development\Z-space\earth2studio
Integrity mode: development

Reference: https://github.com/zrt219/earth2studio/tree/feat/od-earth2-001

## Requirements

### R1. Environment Discovery & Reproducible Setup
Discover hardware capabilities (Windows 10 + WSL2/Ubuntu, CPU/GPU, memory, storage) and configure Earth2Studio in an isolated virtual environment (`.venv_wsl` or `.venv`) with editable installation and zero billable cloud costs.

### R2. Isolated Origin Datum Research Architecture
Implement `od_experiments/earth2_001` with CLI (`doctor`, `inspect`, `run`, `validate`), configuration management, provenance tracking (SHA-256 digests, runtime metadata), and zero credential leakage.

### R3. Genuine Forecasting & Scientific Validation Pipeline
Execute a verified, no-cost baseline weather forecast (e.g. DLWP / GFS or NVIDIA FourCastNet API where available) and evaluate with statistical metrics (MAE, RMSE, Mean Bias).

### R4. Comprehensive Model Registry & Documentation
Document candidate models (DLWP, FourCastNet, StormScope EU, Atlas, CorrDiff, HealDA) and provide a reproducible step-by-step setup guide in `docs/origin_datum/EARTH2_SETUP.md`.

## Acceptance Criteria

### Environment Verification
- [ ] Working virtual environment successfully imports `earth2studio` in editable mode.
- [ ] Hardware capabilities, OS, Python version, and CUDA/CPU status accurately reported.

### Architecture & CLI
- [ ] `python -m od_experiments.earth2_001.cli doctor` runs offline and verifies dependencies without downloads.
- [ ] `python -m od_experiments.earth2_001.cli inspect` reports model and dataset schemas.
- [ ] Automated tests cover config, environment, provenance, secret exclusion, and validation calculations.

### Provenance & Validation
- [ ] Every execution produces a machine-readable JSON manifest recording commit SHA, versions, parameters, and artifact hashes.
- [ ] Statistical metrics (MAE, RMSE, Mean Bias) are evaluated against independent or baseline reference data.
