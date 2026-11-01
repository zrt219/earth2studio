# Handoff Report: Earth2Studio Exploration & Survey (OD-EARTH2-001)

**From**: `explorer_survey_1`  
**To**: Orchestrator (`77a68bcc-3e86-4665-9fe7-9fe95b669349`)  
**Working Directory**: `d:\programming\Blockchain development\Z-space\earth2studio\.agents\teamwork\explorer_survey_1`  
**Date**: 2026-10-26  
**Type**: Hard Handoff (Investigation & Survey Complete)  

---

## 1. Observation

### 1.1 Git Topology & Branches
- **Command**: `git status; git branch -a; git remote -v; git log -n 5 --oneline`
- **Output**:
  ```text
  On branch main
  Your branch is up to date with 'origin/main'.
  Untracked files:
    .agents/teamwork/
    feat/od-earth2-001
  * main
    remotes/origin/HEAD -> origin/main
    remotes/origin/feat/od-earth2-001
    remotes/origin/main
  origin   https://github.com/zrt219/earth2studio.git (fetch & push)
  upstream https://github.com/NVIDIA/earth2studio.git (fetch & push)
  39ef89c Stop compounding lead times in datasource_to_file (#1274)
  ```
- **Branch Comparison**: `git diff main..feat/od-earth2-001` produced empty output (0 differences; both are at commit `39ef89c`).

### 1.2 Host Hardware & GPU Acceleration
- **Command**: `Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, AdapterRAM, Status; Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors; Get-CimInstance Win32_OperatingSystem ...`
- **Output**:
  ```text
  GPU Name: AMD Radeon RX 9060 XT (DriverVersion: 32.0.32015.7029, Status: OK)
  CPU Name: AMD Ryzen 5 3600 6-Core Processor (12 Logical Processors)
  OS: Microsoft Windows 10 Pro (Version 10.0.19045, 22H2)
  RAM: 31.95 GiB total physical memory (~1.0 GiB currently free on host)
  Drive D: 3592.81 GB used, 133.22 GB free
  Drive C: 901.76 GB used, 50.97 GB free
  ```
- **NVIDIA Status**: `nvidia-smi` is not installed or recognized. No NVIDIA GPU is present.

### 1.3 WSL2 Environment
- **Command**: `wsl -l -v`
- **Output**:
  ```text
  NAME: Ubuntu, STATE: Running, VERSION: 2
  ```
- **Probe Script Execution** (`.agents/teamwork/explorer_survey_1/probe_wsl.sh`):
  ```text
  Kernel: Linux ze-grand-finale 6.18.54.1-microsoft-standard-WSL2 #1 SMP PREEMPT_DYNAMIC
  OS: Ubuntu 24.04.4 LTS (Noble Numbat)
  Memory: 15 GiB allocated, 7.2 GiB free, 14 GiB available, 4.0 GiB swap (0 used)
  Disk: /mnt/d 3.7T total, 134G available
  System Python: /usr/bin/python3 (Python 3.12.3)
  UV Python: /home/zrt/.local/bin/python3.13 (Python 3.13.17)
  UV: /home/zrt/.local/bin/uv (uv 0.13.5 x86_64-unknown-linux-gnu)
  Build tools: gcc 13.3.0, make 4.3 installed
  ```

### 1.4 Virtual Environments & Reparse Point Conflict
- **Directory Search**: `.venv` and `.venv_wsl` both exist at the repo root.
- **Config**:
  - `.venv/pyvenv.cfg`: `home = /home/zrt/.local/share/uv/python/cpython-3.13-linux-x86_64-gnu/bin`, `version_info = 3.13`, `uv = 0.13.5`. Contains Linux symlink `.venv/lib64 -> lib`.
  - `.venv_wsl/pyvenv.cfg`: `home = /usr/bin`, `version_info = 3.12.3`, `uv = 0.13.5`. Contains Linux symlink `.venv_wsl/lib64 -> lib`.
- **Windows UV Error**:
  ```text
  error: failed to remove file `\\?\D:\programming\Blockchain development\Z-space\earth2studio\.venv\lib64`: Access is denied. (os error 5)
  ```
  Occurs because Windows attempts to modify Linux reparse points. Inside WSL2, Linux `uv` operates cleanly on `.venv`.

### 1.5 Package Configuration & UV Lock Resolution
- **File**: `pyproject.toml`
  - Line 12: `requires-python = ">=3.11,<3.15"`
  - Line 499: `path = "earth2studio/__init__.py"` (`__version__ = "0.20.0a0"`)
- **Resolution Dry-Run Command**: `wsl -d Ubuntu -u zrt -- bash -l -c "cd '/mnt/d/programming/Blockchain development/Z-space/earth2studio' && /home/zrt/.local/bin/uv sync --dry-run"`
- **Result**:
  ```text
  Would use project environment at: .venv
  Resolved 452 packages in 17ms
  Found up-to-date lockfile at: uv.lock
  Would download 147 packages
  Would install 191 packages
  ```
  Editable install of `earth2studio==0.20.0a0` resolves without conflicts.
  Dry-runs with `--extra dlwp` (212 packages) and `--extra data` (243 packages) also resolve in <20ms.

### 1.6 Package Architecture & Execution Primitives
- **Runners (`earth2studio/run.py:88-93`)**:
  ```python
  device = (
      device
      if device is not None
      else torch.device("cuda" if torch.cuda.is_available() else "cpu")
  )
  logger.info(f"Inference device: {device}")
  prognostic = prognostic.to(device)
  ```
  Earth2Studio natively supports CPU fallback when CUDA is absent.
- **Data Sources (`earth2studio/data/`)**:
  - `gfs.py`: NOAA GFS analysis via AWS S3 open data `s3://noaa-gfs-bdp-pds` with `obstore`. Zero cost, no API keys.
  - `rand.py`: Synthetic Gaussian data generator in-memory (`Random`). Zero cost, offline.
  - `cds.py`: ECMWF ERA5 via CDS API (requires credentials).
- **Prognostic Models (`earth2studio/models/px/`)**:
  - `persistence.py`: Built-in persistence baseline. Zero external weights, instant CPU execution.
  - `dlwp.py`: DLWP cubed-sphere CNN (6h step, 7 variables). Pre-trained weights available on NGC.
  - `fcn.py`: FourCastNet AFNO model. Pre-trained weights on HuggingFace.
- **Statistics (`earth2studio/statistics/`)**:
  - `rmse.py`: `rmse` and `mae` classes with dimension reduction and latitude area-weighting.
  - `moments.py`: `mean` class (enables Mean Bias calculation `mean(pred - target)`).
- **Existing Rules (`.agents/rules/`)**:
  - `e2s-000-python-style-guide.mdc`: Black formatting, strict typing, SPDX license header, `loguru.logger` logging.
  - `e2s-001-dependency-management.mdc`: `uv` dependency manager, optional dependencies via `@check_optional_dependencies()`.
  - `e2s-003-unit-testing.mdc`: PyTest, 90%+ coverage, no docstrings in test functions.
- **Installation Skill (`skills/earth2studio-install/SKILL.md:24-29`)**:
  - "You MUST NOT install, upgrade, or modify packages on the user's behalf. Provide the exact command; the user runs it. No exceptions."

---

## 2. Logic Chain

1. **Hardware Assessment**:
   - Direct observation: GPU is AMD Radeon RX 9060 XT; `nvidia-smi` is absent.
   - Inference: PyTorch will run with `torch.cuda.is_available() == False`. Any component requiring CUDA extensions (e.g. `da-healda`, `cyclone`, CuPy/cuDF) cannot run natively on this host.
   - Conclusion: All OD-EARTH2-001 workflows and tests must specify `device="cpu"` or rely on Earth2Studio's native fallback.

2. **Operating System & Tooling Assessment**:
   - Direct observation: Windows system Python is 3.10.11 (fails `>=3.11` in `pyproject.toml`). Windows `uv` errors with OS error 5 on `.venv/lib64` symlinks created by WSL2.
   - Direct observation: WSL2 Ubuntu 24.04 has Python 3.12.3 and Python 3.13.17, GCC 13.3.0, Make 4.3, and Linux `uv 0.13.5`. `uv sync --dry-run` resolves `uv.lock` in 17 ms.
   - Conclusion: The scientific research environment MUST be driven through WSL2 Ubuntu using `/home/zrt/.local/bin/uv` targeting `.venv` or `.venv_wsl`.

3. **Requirements R1–R4 Feasibility**:
   - **R1 (Setup & Discovery)**: `.venv` (Python 3.13.17) is ready to be populated via `uv sync` in editable mode. Hardware probe confirms 6 cores, 32 GB RAM, 133 GB free disk on D:.
   - **R2 (Architecture & CLI)**: The new experiment module `od_experiments/earth2_001` can be implemented at the repository root with CLI commands (`doctor`, `inspect`, `run`, `validate`), SHA-256 provenance manifests, and offline capability.
   - **R3 (Forecasting & Validation)**: A zero-cost forecast can be executed offline using `Persistence` + `Random` (baseline Tier 1) or `DLWP` + `GFS` (neural forecast Tier 2 using free public AWS S3 data). Forecast error metrics (MAE, RMSE, Mean Bias) are directly supported by `earth2studio.statistics.rmse` and `moments`.
   - **R4 (Documentation)**: `docs/origin_datum/EARTH2_SETUP.md` will document the candidate models, reproducible WSL2 commands, and experiment execution instructions.

---

## 3. Caveats

1. **No External Network Installs Executed**: In strict compliance with `skills/earth2studio-install/SKILL.md` and read-only exploration scope, no packages were installed into `.venv` during this turn. Commands are validated via `--dry-run`.
2. **AMD ROCm Not Configured**: The AMD Radeon RX 9060 XT is not currently configured with ROCm on WSL2. Inference is constrained to CPU.
3. **Model Weights Download**: DLWP checkpoint download from NGC (`dlwp_cubesphere.zip`) requires ~500 MB of internet bandwidth during first run. For offline validation, `Persistence` model requires zero download.

---

## 4. Conclusion

1. **Environment**: WSL2 Ubuntu 24.04 (`/home/zrt/.local/bin/uv`, Python 3.13.17, target `.venv`) is the verified, correct runtime platform for OD-EARTH2-001.
2. **Acceleration**: CPU-only mode (`device="cpu"`) must be enforced across all CLI commands and configs.
3. **Experiment Design**:
   - `od_experiments/earth2_001/` will provide the isolated architecture with CLI (`doctor`, `inspect`, `run`, `validate`).
   - Baseline forecast will run `Persistence` (Tier 1 offline) and `DLWP` on NOAA GFS (Tier 2 public open data).
   - Validation will evaluate MAE, RMSE, and Mean Bias using `earth2studio.statistics`.
   - Documentation will be placed in `docs/origin_datum/EARTH2_SETUP.md`.

---

## 5. Verification Method

To independently verify these findings, run the following commands:

1. **Verify Git branch & commit**:
   ```bash
   git status
   git branch -a
   git log -n 1 --oneline
   ```
2. **Verify WSL2 Hardware & Python Environment**:
   ```powershell
   wsl -d Ubuntu -u zrt -- bash -l -c "uname -a; python3 --version; /home/zrt/.local/bin/uv --version"
   ```
3. **Verify UV Resolution against uv.lock**:
   ```powershell
   wsl -d Ubuntu -u zrt -- bash -l -c "cd '/mnt/d/programming/Blockchain development/Z-space/earth2studio' && /home/zrt/.local/bin/uv sync --dry-run"
   ```
4. **Inspect Analysis Report**:
   Inspect `d:\programming\Blockchain development\Z-space\earth2studio\.agents\teamwork\explorer_survey_1\analysis.md`.

### Invalidation Conditions
- If an NVIDIA GPU is added or CUDA drivers are installed on the host.
- If `pyproject.toml` or `uv.lock` is modified with breaking dependency pins.
