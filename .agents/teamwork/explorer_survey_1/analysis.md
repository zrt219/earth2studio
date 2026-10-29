# Comprehensive Survey & Environment Analysis: Earth2Studio (OD-EARTH2-001)

**Date**: 2026-10-26  
**Agent**: `explorer_survey_1`  
**Working Directory**: `d:\programming\Blockchain development\Z-space\earth2studio\.agents\teamwork\explorer_survey_1`  
**Project**: Origin Datum Earth-2 Research Lab (`OD-EARTH2-001`)  
**Reference Request**: `ORIGINAL_REQUEST.md`  

---

## Executive Summary

A comprehensive, non-destructive read-only investigation of the Earth2Studio codebase and execution environment was conducted. Key conclusions:
1. **Host Environment**: The host is Windows 10 Pro with an AMD Ryzen 5 3600 (6-core / 12-thread) CPU, 32 GB RAM, and an **AMD Radeon RX 9060 XT GPU**. Because there is no NVIDIA GPU, **NVIDIA CUDA is not available**. All PyTorch and Earth2Studio workflows must execute in **CPU mode** (`device="cpu"`), which Earth2Studio natively supports.
2. **WSL2 Runtime**: WSL2 Ubuntu 24.04.4 LTS is running with Linux kernel 6.18.54.1, GCC 13.3.0, Make 4.3, Python 3.12.3 (`/usr/bin/python3`), Python 3.13.17 (`/home/zrt/.local/bin/python3.13`), and `uv 0.13.5`.
3. **Virtual Environments**: Two pre-created virtual environment roots exist: `.venv` (configured for Python 3.13.17) and `.venv_wsl` (configured for Python 3.12.3). Both are currently clean (unpopulated). `uv sync --dry-run` against `uv.lock` resolves 452 packages in 17 ms, cleanly supporting editable `earth2studio==0.20.0a0`. Due to Linux symlinks in `.venv/lib64`, operations inside WSL2 via Linux `uv` avoid Windows NTFS reparse point errors.
4. **Candidate Models & Verification**: Earth2Studio has 39 prognostic models, 20 diagnostic models, and 53 data sources. For an offline, zero-cost, CPU-compatible baseline, the built-in `Persistence` model paired with the `Random` data source or `GFS` (NOAA open AWS S3 bucket `s3://noaa-gfs-bdp-pds`, zero authentication) fulfills R1–R3 without cloud billing.
5. **Coding & Architectural Conventions**: All Python code requires SPDX Apache-2.0 license headers, strict MyPy typing, `loguru.logger` logging, and PyTest coverage >= 90%.

---

## 1. Project Structure, Git & Packaging Status

### 1.1 Git Status & Branch Topology
- **Active Working Branch**: `main`
- **Working Tree**: Clean (untracked files restricted to `.agents/teamwork/`).
- **Remotes**:
  - `origin`: `https://github.com/zrt219/earth2studio.git` (fetch & push)
  - `upstream`: `https://github.com/NVIDIA/earth2studio.git` (fetch & push)
- **Local & Tracking Branches**:
  - `main` -> tracking `origin/main` at commit `39ef89c` ("Stop compounding lead times in datasource_to_file (#1274)").
  - `feat/od-earth2-001` -> tracking `origin/feat/od-earth2-001` at commit `39ef89c`.
  - There are currently 0 divergent commits between `main` and `feat/od-earth2-001`.

### 1.2 `pyproject.toml` & Packaging Configuration
- **Build Backend**: `hatchling` (`hatchling.build`).
- **Package Name & Version**: `earth2studio`, version `0.20.0a0` (dynamic from `earth2studio/__init__.py`).
- **Python Version Constraint**: `>=3.11, <3.15`.
- **Lockfile**: `uv.lock` is present, up to date, and pins 452 packages.
- **Core Dependencies**:
  `cftime`, `fsspec>=2024.2.0`, `gcsfs`, `h5py>=3.2.0`, `h5netcdf>=1.0.0`, `huggingface-hub>=0.27.0`, `loguru`, `netCDF4>=1.6.4,<1.7.3`, `obspec>=0.1`, `obstore>=0.8`, `pygrib`, `python-dotenv`, `pandas`, `pyarrow>=14.0.0`, `rich`, `s3fs>=2023.5.0`, `torch>=2.5.0`, `tqdm>=4.65.0`, `xarray[parallel]>=2023.1.0`, `zarr>=3.1.3`.
- **Key Optional Dependency Groups**:
  - `data`: `arraylake`, `cdsapi`, `cfgrib`, `eccodes`, `eccodeslib`, `ecmwf-opendata`, `gribberish`, `icechunk`, `intake-esgf`, `pcodec`, `pybufrkit`, `pystac-client`, `rasterio`, `rioxarray`, `pyproj`, `scipy`, `eumdac`.
  - `dlwp`: `nvidia-physicsnemo>=1.0.1`, `importlib_metadata`.
  - `fcn`: `nvidia-physicsnemo>=1.0.1`.
  - `statistics`: `nvidia-physicsnemo>=1.0.1`.
  - `utils`: `scipy>=1.15.2`, `earth2grid`.
  - `dev`: `black==26.5.1`, `coverage`, `interrogate`, `hatch`, `mypy`, `pre-commit`, `pytest`, `pytest-cov`, `pytest-timeout`, `pytest-skip-slow`, `pytest-testmon`, `ruff`, `tox-uv`.

---

## 2. Hardware Capabilities & Runtime Matrix

### 2.1 Hardware Metrics
| Subsystem | Specification / Observed State | Practical Implication |
|---|---|---|
| **OS** | Microsoft Windows 10 Pro (Build 19045, 22H2) | Primary host operating system |
| **CPU** | AMD Ryzen 5 3600 6-Core Processor (12 logical CPUs) | Host & WSL2 CPU compute engine |
| **RAM** | 31.95 GiB Physical RAM (Host: ~1.0 GiB free; WSL2: 15 GiB allocated, ~7.2 GiB free, 14 GiB available) | Sufficient for medium-resolution model inference and CPU tensor operations |
| **Disk Storage** | Drive D: 3,592 GB used, **133.22 GB free**<br>Drive C: 901 GB used, **50.97 GB free** | Drive D has ample headroom (>133 GB) for virtual environments, checkpoints, and forecast test outputs |
| **GPU Adapter** | **AMD Radeon RX 9060 XT** (Driver: 32.0.32015.7029) | **Non-NVIDIA GPU**. No CUDA drivers (`nvidia-smi` absent) |
| **Acceleration** | **CUDA Unavailable** (`torch.cuda.is_available() == False`) | **All inference must default to `device="cpu"`**. GPU-only extras (e.g. `da-healda`, `cyclone`, CuPy/cuDF) cannot run natively without CUDA |

### 2.2 WSL2 Environment Status
- **Distribution**: Ubuntu 24.04.4 LTS (Noble Numbat) on kernel `6.18.54.1-microsoft-standard-WSL2`.
- **User**: `zrt` (UID 1000).
- **Compilers & Build Tools**: `gcc` 13.3.0, `make` 4.3 installed in Ubuntu.
- **Python Runtimes Available in WSL2**:
  - `/usr/bin/python3` -> Python 3.12.3.
  - `/home/zrt/.local/bin/python3.13` -> Python 3.13.17 (managed via uv).
- **Package Manager in WSL2**:
  - `/home/zrt/.local/bin/uv` -> `uv 0.13.5 (x86_64-unknown-linux-gnu)`.

### 2.3 Virtual Environments Comparison
| Path | Target Python | Creation Tool | Current State | Windows Host Compatibility | WSL2 Compatibility |
|---|---|---|---|---|---|
| `.venv` | Python 3.13.17 | `uv 0.13.5` (Linux) | Clean / Unsynced | ⚠️ Reparse point (`lib64`) issues on Windows host | ✅ Recommended default for Linux `uv sync` |
| `.venv_wsl` | Python 3.12.3 | `uv 0.13.5` (Linux) | Clean / Unsynced | ⚠️ Reparse point (`lib64`) issues on Windows host | ✅ Clean secondary environment |
| Windows Host | Python 3.10.11 | Python installer | System | ❌ Fails `pyproject.toml` requirement (`>=3.11`) | N/A |
| Windows UV | Python 3.13.15 | UV Windows | Standalone | ✅ Can import `earth2studio` from source | N/A |

**Key Finding on Reparse Points**:
Because `.venv` was initialized in WSL2, it contains a Linux symlink `lib64 -> lib`. Windows `uv` attempting to modify or clear `.venv` reports `Access is denied (os error 5)`. All dependency installation and test execution should therefore be driven through **WSL2** using `/home/zrt/.local/bin/uv` or a Windows-isolated environment if running on host.

---

## 3. Package Architecture, Models, Data Sources & Testing

### 3.1 Earth2Studio Architecture
Earth2Studio organizes meteorological deep learning inference into composable primitives:
- **`earth2studio.run`**: Pipeline runners (`deterministic`, `ensemble`, `diagnostic`).
- **`earth2studio.data`**: Standardized data ingestion adhering to `DataSource` (analysis), `ForecastSource` (forecast lead times), `DataFrameSource` (tabular/station data), and `ForecastFrameSource`.
- **`earth2studio.models.px`**: Prognostic models that advance atmospheric states over time via `PrognosticModel` protocol (`__call__`, `create_iterator`, `input_coords`, `output_coords`, `to`).
- **`earth2studio.models.dx`**: Diagnostic models that map atmospheric states to secondary variables or high-resolution grids via `DiagnosticModel` protocol.
- **`earth2studio.models.da`**: Data assimilation models (beta).
- **`earth2studio.statistics`**: Metric and statistical evaluators (`rmse`, `mae`, `acc`, `crps`, `energy_score`, `mean`, `variance`, `std`).
- **`earth2studio.io`**: Pluggable storage outputs (`ZarrBackend`, `NetCDF4Backend`, `XarrayBackend`).

### 3.2 Candidate Models Assessment for OD-EARTH2-001
| Model | Type | Architecture / Scope | External Weights | CPU Support | Cost / Auth | Fit for OD-EARTH2-001 |
|---|---|---|---|---|---|---|
| **`Persistence`** | Prognostic (Baseline) | Identity operator, 6h step, arbitrary lat-lon domain | **None (built-in)** | **Yes (Fast, lightweight)** | **Zero cost, offline** | **Ideal immediate verification baseline** |
| **`DLWP`** | Prognostic | Cubed-sphere CNN (64x64 faces), 6h step, 7 vars (`t850`, `z1000`, `z700`, `z500`, `z300`, `tcwv`, `t2m`) | `ngc://models/nvidia/modulus/modulus_dlwp_cubesphere@v0.2` (~500 MB) | Yes (via CPU tensors) | Zero cost (public NGC) | **Strong candidate for genuine neural forecast** |
| **`FCN` (FourCastNet)** | Prognostic | AFNO on 0.25° global grid (720x1440), 6h step, 26 vars | `hf://nvidia/fourcastnet1` (~1.2 GB) | Yes, but high CPU memory/time | Zero cost (HuggingFace) | Candidate for subsequent benchmark |
| **`StormScope`** | Prognostic / Diagnostic | Regional high-res nowcasting (MRMS / GOES / Meteosat) | HuggingFace / NGC | Heavy CPU load; requires `natten` | Zero cost | Requires complex `natten` build |
| **`CorrDiff`** | Diagnostic (Downscaling) | Diffusion model (e.g. Taiwan, HRRR, COSMO) | NGC / HuggingFace | Very slow on CPU (diffusion sampling) | Zero cost | Recommended once GPU/ROCm available |
| **`HealDA`** | Data Assimilation | HEALPix assimilation wrapper | Git repo `NVlabs/HealDA` | ❌ Requires CUDA / CuPy / cuDF | Zero cost | Incompatible with CPU-only runtime |

### 3.3 Data Sources Assessment
| Data Source | Module | Description | Access Protocol | Auth / Billing | Fit for OD-EARTH2-001 |
|---|---|---|---|---|---|
| **`Random`** | `earth2studio.data.rand` | Generates Gaussian synthetic tensors matching any domain | In-memory NumPy/xarray | **Zero network, zero cost** | **Perfect for offline testing and CLI `doctor` checks** |
| **`GFS`** | `earth2studio.data.gfs` | NOAA Global Forecast System analysis (0.25° grid, 6h interval) | Open AWS S3 bucket `s3://noaa-gfs-bdp-pds` via `obstore` | **Zero credentials, free public bucket** | **Ideal for genuine baseline weather forecast** |
| **`CDS`** | `earth2studio.data.cds` | ECMWF ERA5 reanalysis | Copernicus CDS API | Free account, but requires CDS API key | Requires credentials setup |
| **`HRRR`** | `earth2studio.data.hrrr` | NOAA High-Resolution Rapid Refresh (CONUS) | AWS Open Data | Free, zero credentials | High resolution regional option |

### 3.4 Test Suite & Mock Architecture
The test suite in `test/` contains 155 test modules.
- **Fixtures & Isolation (`test/conftest.py`)**: Tests automatically skip optional dependencies when absent via `_TEST_DEPENDENCIES` inspection in `pytest_ignore_collect` and `pytest_collection_modifyitems`.
- **Model Package Flag**: Model downloads are gated behind `--package-download` or `--package` (environment variables `EARTH2STUDIO_TEST_PACKAGES` and `EARTH2STUDIO_DOWNLOAD_PACKAGES`).
- **Offline Mocks**: Tests for models like DLWP use `PhooDLWPModel` and synthetic sparse tensors to test tensor transformations and iterations without downloading model weights.

---

## 4. Development Rules & Skills Conventions

### 4.1 Development Rules (`.agents/rules/`)
1. **`e2s-000-python-style-guide.mdc`**:
   - Formatter: `black` (version specified in `pyproject.toml`).
   - Typing: Strict MyPy compliance; all functions and methods must have parameter and return type hints using modern PEP 585/604 syntax (`list[str]`, `str | None`).
   - License Header: Every `.py` source file MUST begin with the verbatim SPDX Apache-2.0 header.
   - Logging: Use `loguru.logger` or `rich.console`. Native `print()` inside `earth2studio/` is strictly prohibited.
2. **`e2s-001-dependency-management.mdc`**:
   - Always use `uv` for dependency management.
   - Optional imports must follow the 3-step pattern:
     ```python
     try:
         import optional_package
     except ImportError:
         OptionalDependencyFailure("group_name")
         optional_package = None
     ```
     Decorate dependent classes and methods with `@check_optional_dependencies()`.
3. **`e2s-003-unit-testing.mdc`**:
   - PyTest framework, target coverage >= 90%.
   - No docstrings inside test functions.
   - Parametrization must be strategic and concise.
   - Mark tests with `@pytest.mark.slow`, `@pytest.mark.timeout`, `@pytest.mark.skipif`.
4. **`e2s-009-prognostic-models.mdc`**:
   - Prognostics inherit from `torch.nn.Module`, `AutoModelMixin`, and `PrognosticMixin`.
   - Implement `input_coords()`, `output_coords()`, `create_iterator()`, `load_default_package()`, and `load_model()`.

### 4.2 Installation Skill Guardrails (`skills/earth2studio-install/SKILL.md`)
- **Strict Prohibition**: "You MUST NOT install, upgrade, or modify packages on the user's behalf. Provide the exact command; the user runs it. No exceptions. Forbidden: running `pip install`, `uv pip install`, `uv add`, `uv sync`, `conda install`, `apt install`, or any package manager."
- All setup workflows should provide explicit copy-paste commands and clear architectural guidance.

---

## 5. Synthesis: Blueprint for OD-EARTH2-001

Based on the survey, the optimal architecture for `OD-EARTH2-001` is:

1. **Environment Setup (R1)**:
   - Target runtime: **WSL2 Ubuntu 24.04** using `/home/zrt/.local/bin/uv`.
   - Target environment: `.venv` (Python 3.13.17) in editable mode:
     ```bash
     wsl -d Ubuntu -u zrt -- bash -l -c "cd '/mnt/d/programming/Blockchain development/Z-space/earth2studio' && uv sync"
     ```
   - Optional extras for forecasting:
     ```bash
     uv sync --extra dlwp --extra data
     ```
   - Hardware detection logic must accurately identify CPU mode, AMD Radeon RX 9060 XT GPU, and set `device = "cpu"`.

2. **Isolated Research Architecture `od_experiments/earth2_001` (R2)**:
   - Create isolated package `od_experiments/earth2_001` at repository root with:
     - `cli.py`: Click/Typer CLI with commands `doctor`, `inspect`, `run`, `validate`.
     - `config.py`: Dataclass or Pydantic config with provenance parameters.
     - `provenance.py`: SHA-256 calculation for code commits, weights, inputs, and outputs.
     - `doctor.py`: Offline health check verifying imports, hardware, memory, and zero-cost operation.
   - Zero credential leakage: Ensure no hardcoded API keys; all GFS access uses open S3 URLs.

3. **Genuine Forecasting & Scientific Validation (R3)**:
   - Baseline Tier 1 (Offline verification): `Persistence` model on `Random` or cached GFS initial conditions.
   - Forecast Tier 2 (Genuine weather forecast): `DLWP` prognostic model on NOAA GFS initial state from AWS Open Data (`s3://noaa-gfs-bdp-pds`).
   - Validation Metrics: Evaluate forecast against reference data using `earth2studio.statistics.rmse.rmse`, `mae`, and bias via `moments.mean`.

4. **Model Registry & Documentation (R4)**:
   - Create `docs/origin_datum/EARTH2_SETUP.md` detailing the step-by-step reproducible setup, hardware compatibility matrix, and experiment execution instructions.

---
