# Technical Analysis: OD-EARTH2-001 Forecasting, Validation, and CLI Infrastructure

**Agent**: `explorer_survey_2`  
**Working Directory**: `d:\programming\Blockchain development\Z-space\earth2studio\.agents\teamwork\explorer_survey_2`  
**Date**: 2026-10-26  
**Status**: Completed  

---

## 1. Executive Summary

This investigation surveys the forecasting, validation, testing, and CLI infrastructure for **OD-EARTH2-001 (Origin Datum Earth-2 Research Lab)** within the Earth2Studio fork. 

Key conclusions:
1. **Zero-Cost Models**: NVIDIA's DLWP (Deep Learning Weather Prediction) model is 100% freely downloadable without credentials or paid cloud costs via NVIDIA NGC public endpoints (`ngc://models/nvidia/modulus/modulus_dlwp_cubesphere@v0.2`). Earth2Studio's `Persistence` and `DataReplay` models require zero weights, zero downloads, and zero cloud cost, serving as immediate, robust offline baselines.
2. **Zero-Cost Data Sources**: NOAA's Global Forecast System (GFS) initial conditions are publicly available at zero cost via AWS Open Data (`s3://noaa-gfs-bdp-pds`) using anonymous S3 access (`anon=True`). Google Cloud's ARCO-ERA5 dataset (`gs://gcp-public-data-arco-era5`) is similarly public and unauthenticated (`skip_signature=True`). Synthetic offline data sources (`Random`, `Constant`) provide completely offline test data.
3. **Hardware Execution Realities**: The physical host is an AMD Ryzen 5 3600 (12 vCPUs, 16 GB RAM) with Ubuntu 24.04 on WSL2 and Python 3.13.17 (`/home/zrt/.local/bin/python3.13`), with no active NVIDIA GPU. All baseline forecasts, validation pipelines, and tests must support seamless CPU execution.
4. **Statistical Metrics**: Earth2Studio provides `rmse` and `mae` in `earth2studio.statistics.rmse` with cosine-latitude weighting (`earth2studio.statistics.lat_weight`). A complementary `mean_bias` metric is readily implemented using `earth2studio.statistics.mean` to evaluate directional forecasting bias.
5. **CLI & Secret Exclusion Architecture**: `od_experiments.earth2_001.cli` should expose four commands: `doctor`, `inspect`, `run`, and `validate`. `doctor` leverages Earth2Studio's built-in offline package inspection (`earth2studio.utils.imports._check_package`). A dedicated security module scrubs known secret environment variables (`*KEY*`, `*TOKEN*`, `*SECRET*`) to guarantee zero credential leakage into provenance manifests or terminal outputs.

---

## 2. Zero-Cost Models & Data Sources Investigation

### 2.1 Feasible Forecasting Models

| Model | Implementation Path | Weights / Checkpoint Source | Credentials Needed | CPU Viability | Memory / Compute Footprint |
|---|---|---|---|---|---|
| **DLWP** (Deep Learning Weather Prediction) | `earth2studio/models/px/dlwp.py` | `ngc://models/nvidia/modulus/modulus_dlwp_cubesphere@v0.2/dlwp_cubesphere.zip` | None (Public anonymous NGC HTTP API) | High (PyTorch CNN on 6 cubed sphere faces `[6, 64, 64]`) | ~200 MB download, ~1-2 GB RAM, ~2-5s per step on CPU |
| **Persistence** | `earth2studio/models/px/persistence.py` | None (Identity operator: $x(t+\tau) = x(t)$) | None (100% offline) | Extremely High (<10 ms per step) | Negligible (<50 MB RAM) |
| **DataReplay** | `earth2studio/models/px/datareplay.py` | None (Replays data from DataSource / ForecastSource) | None (Inherits source access) | Extremely High | Dependent on source slice |
| **FourCastNet (FCN)** | `earth2studio/models/px/fcn.py` | `hf://nvidia/fourcastnet1@c67a63995f6c8e0e557eb3d791f32f437e9b02d5` | None (Public Hugging Face repository) | Moderate (AFNO on 720x1440 grid) | ~300 MB weights, higher RAM, ~15-30s per step on CPU |

#### DLWP Deep Dive
- **Resolution & Variables**: DLWP accepts equirectangular grid `[721, 1440]` and interpolates to cubed sphere `[6, 64, 64]`. It predicts 7 atmospheric variables:
  `["t850", "z1000", "z700", "z500", "z300", "tcwv", "t2m"]`.
- **Time Stepping**: Time step size is 6 hours (`dt = np.timedelta64(6, "h")`). Requires 2 history steps ($t-6\text{h}$ and $t_0$).
- **Checkpoint Retrieval**: `DLWP.load_default_package()` initializes `Package("ngc://models/nvidia/modulus/modulus_dlwp_cubesphere@v0.2")`. As implemented in `earth2studio/models/auto/ngc.py:301-307`, when `authenticated_api=False`, it hits the public NGC REST API (`https://api.ngc.nvidia.com/v2/models/...`) to obtain direct download presigned links without requiring `NGC_CLI_API_KEY`.
- **Dependency**: Requires `nvidia-physicsnemo>=1.0.1` and `importlib_metadata`.

#### Persistence Baseline Deep Dive
- Built directly into `earth2studio.models.px.Persistence`.
- Accepts any variable list and spatial domain coordinates.
- Advances lead time by `dt` while holding physical fields constant.
- In scientific meteorological verification (e.g., WeatherBench, ECMWF standards), Persistence is the foundational non-learned reference baseline against which AI models are evaluated.

### 2.2 Zero-Cost Data Sources

| Data Source | Implementation Path | Remote Location / Provider | Access Protocol / Authentication | Zero-Cost Guarantee |
|---|---|---|---|---|
| **GFS** (Global Forecast System) | `earth2studio/data/gfs.py` | AWS Open Data (`s3://noaa-gfs-bdp-pds`) | Anonymous S3 (`obstore` / `s3fs` with no credentials) | Guaranteed free under NOAA Open Data Dissemination (NODD) |
| **GFS (NCEP)** | `earth2studio/data/gfs.py` | NOAA NOMADS (`https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/`) | Direct HTTPS range requests | Free public government service (past 10 days) |
| **ARCO-ERA5** | `earth2studio/data/arco.py` | Google Cloud (`gs://gcp-public-data-arco-era5`) | Zarr over GCS (`skip_signature: True`) | Guaranteed free public dataset on GCP |
| **Random / Constant** | `earth2studio/data/rand.py`, `earth2studio/data/const.py` | In-memory local numpy/xarray | 100% offline, synthetic | Zero cost, zero network |

#### GFS Source Mechanism
- `GFS` pulls 0.25° analyses (lat `[90, -90, 721]`, lon `[0, 359.75, 1440]`) at 6-hour intervals from 2021-01-01 to present.
- Downloaded chunks are automatically cached locally in `~/.cache/earth2studio` (or `$EARTH2STUDIO_CACHE`), preventing repeated network transfers.
- Compatible with all 7 variables needed by DLWP (`t850`, `z1000`, `z700`, `z500`, `z300`, `tcwv`, `t2m`).

---

## 3. Statistical Metrics & Reference Validation Data

### 3.1 Existing Metric Infrastructure in Earth2Studio

Earth2Studio provides a dedicated statistics subpackage in `earth2studio/statistics/`:
- `Metric` protocol (`earth2studio/statistics/base.py:72-123`):
  Requires:
  - `reduction_dimensions -> list[str]`
  - `output_coords(input_coords: CoordSystem) -> CoordSystem`
  - `__call__(x: torch.Tensor, x_coords: CoordSystem, y: torch.Tensor, y_coords: CoordSystem) -> tuple[torch.Tensor, CoordSystem]`
- `rmse` (`earth2studio/statistics/rmse.py:26-141`):
  Computes $\sqrt{\frac{1}{\sum w} \sum w \cdot (x - y)^2}$ across specified dimensions (e.g., `["lat", "lon"]`).
- `mae` (`earth2studio/statistics/rmse.py:142-210`):
  Computes $\frac{1}{\sum w} \sum w \cdot |x - y|$.
- `lat_weight` (`earth2studio/statistics/weights.py:25-49`):
  Calculates cosine latitude weighting $w(\phi) = \frac{\cos(\phi)}{\frac{1}{N} \sum \cos(\phi)}$, ensuring proper spherical area normalization without polar over-weighting.

### 3.2 Mean Bias Implementation Design

While `rmse` and `mae` exist, a dedicated `Mean Bias` (mean error) metric must be provided for R3.
$$\text{Bias} = \frac{1}{\sum_{i} w_i} \sum_{i} w_i \cdot (x_i - y_i)$$

Implementation using `earth2studio.statistics.mean`:
```python
from collections import OrderedDict
import torch
from earth2studio.statistics.base import Metric
from earth2studio.statistics.moments import mean
from earth2studio.utils.coords import handshake_dim
from earth2studio.utils.type import CoordSystem

class MeanBias(Metric):
    """Mean Bias (Mean Error) statistic between prediction x and observation y."""

    def __init__(
        self,
        reduction_dimensions: list[str],
        weights: torch.Tensor | None = None,
        ensemble_dimension: str | None = None,
    ):
        self._reduction_dimensions = reduction_dimensions
        self.weights = weights
        self.ensemble_dimension = ensemble_dimension
        self.mean = mean(reduction_dimensions, weights=weights)
        if ensemble_dimension:
            self.ensemble_mean = mean([ensemble_dimension])

    @property
    def reduction_dimensions(self) -> list[str]:
        return self._reduction_dimensions

    def output_coords(self, input_coords: CoordSystem) -> CoordSystem:
        output = input_coords.copy()
        for dim in self.reduction_dimensions:
            handshake_dim(input_coords, dim)
            output.pop(dim)
        if self.ensemble_dimension:
            output.pop(self.ensemble_dimension)
        return output

    def __call__(
        self,
        x: torch.Tensor,
        x_coords: CoordSystem,
        y: torch.Tensor,
        y_coords: CoordSystem,
    ) -> tuple[torch.Tensor, CoordSystem]:
        if self.ensemble_dimension:
            x, x_coords = self.ensemble_mean(x, x_coords)
        # Compute signed difference x - y (forecast minus reference)
        diff = x - y
        bias, out_coords = self.mean(diff, x_coords)
        return bias, out_coords
```

### 3.3 Reference Validation Data Structure

When a forecast starts at $t_0$ with lead times $\tau \in \{0\text{h}, 6\text{h}, 12\text{h}, 18\text{h}, 24\text{h}\}$:
1. **Forecast Array ($x$)**:
   - Shape: `[batch=1, time=1, lead_time=5, variable=7, lat=721, lon=1440]`
   - Coordinates: `OrderedDict({'batch': [0], 'time': [t0], 'lead_time': [0, 6, 12, 18, 24], 'variable': [...], 'lat': [...], 'lon': [...]})`
2. **Reference Validation Array ($y$)**:
   - Sourced from ground-truth analysis (e.g. `GFS` or `ARCO_ERA5`) sampled at the exact target valid times $t_{\text{valid}} = t_0 + \tau$.
   - Converted to PyTorch tensor and reshaped to align with $x$'s coordinate system.
3. **Evaluation Computation**:
   - Applying `rmse`, `mae`, and `MeanBias` with reduction over `["lat", "lon"]` and cosine weights produces reduced arrays of shape `[lead_time=5, variable=7]`.
   - These represent the forecast degradation curve over lead time, conforming to standard meteorological scorecards.

---

## 4. Isolated Origin Datum Research Architecture & CLI Design

### 4.1 Target Package Hierarchy

All experiment code lives strictly inside `od_experiments/earth2_001/` to ensure zero pollution of the upstream `earth2studio/` library:

```
od_experiments/
└── earth2_001/
    ├── __init__.py
    ├── cli.py             # Main entry point (argparse / rich CLI dispatch)
    ├── config.py          # Strongly-typed Dataclasses and YAML configuration parser
    ├── doctor.py          # Offline environment, hardware, dependency & secret check
    ├── inspect.py         # Introspects model coords and data source schemas
    ├── pipeline.py        # Orchestrates forecast runs with deterministic workflow
    ├── validate.py        # Computes RMSE, MAE, Mean Bias & emits validation report
    ├── provenance.py      # Git SHA, metadata, and SHA-256 artifact digest generation
    └── security.py        # Environment sanitizer & secret scrubbing engine
```

### 4.2 Detailed Command Specifications

#### 1. `python -m od_experiments.earth2_001.cli doctor`
- **Design Principle**: Must run **100% offline** without any network socket connections.
- **Checks Performed**:
  - **OS & Kernel**: Windows version / WSL2 Linux kernel detection (`platform.uname()`).
  - **Python Runtime**: Verify Python $\ge 3.11$ and $< 3.15$ (reports `sys.version`).
  - **Hardware & Accelerators**: CPU core count, system RAM availability, PyTorch CUDA capability (`torch.cuda.is_available()`, device name or CPU fallback).
  - **Editable Installation**: Confirms `earth2studio` imports cleanly and points to repository root.
  - **Dependency Audit**: Calls `earth2studio.utils.imports._check_package` on required packages (`torch`, `xarray`, `zarr`, `fsspec`, `obstore`, `loguru`, `rich`, `packaging`, `physicsnemo`).
  - **Cache & Storage**: Verifies write permissions on `$EARTH2STUDIO_CACHE` and available disk space.
  - **Secret Audit**: Checks for environment variables with secret keywords; confirms masking.
- **Exit Code**: `0` on healthy environment, `1` if critical dependency is missing.

#### 2. `python -m od_experiments.earth2_001.cli inspect`
- **Arguments**: `--model <name>` (e.g. `dlwp`, `persistence`, `fcn`) and/or `--source <name>` (e.g. `gfs`, `arco`, `random`), `--json` (optional machine-readable flag).
- **Output**:
  - Displays input/output coordinates, time step sizes, expected variables, and grid dimensions.
  - Formatted with `rich.table.Table` or serialized as JSON.

#### 3. `python -m od_experiments.earth2_001.cli run`
- **Arguments**:
  - `--model` (default: `dlwp`)
  - `--source` (default: `gfs`)
  - `--time` (default: `2024-01-01T00:00:00`)
  - `--nsteps` (default: `4`, which equals 24 hours at 6h steps)
  - `--output-dir` (default: `outputs/earth2_001_run`)
  - `--device` (default: `auto` -> cpu or cuda)
  - `--offline` (boolean flag to use synthetic or local cached data only)
- **Workflow**:
  1. Instantiates model and data source.
  2. Runs `earth2studio.run.deterministic`.
  3. Saves forecast output to Zarr / NetCDF.
  4. Calls `provenance.py` to generate `provenance_manifest.json` containing SHA-256 digests of all outputs.

#### 4. `python -m od_experiments.earth2_001.cli validate`
- **Arguments**:
  - `--forecast-dir` / `--forecast-path` (path to forecast output Zarr/NetCDF)
  - `--reference-source` (e.g. `gfs`, `arco`, or pre-downloaded reference)
  - `--metrics` (comma-separated: `rmse,mae,bias`)
  - `--output-dir` (destination for `validation_metrics.json` and summary table)
- **Workflow**:
  1. Loads forecast predictions and matches valid forecast times $t_0 + \tau$.
  2. Fetches matching ground-truth verification data.
  3. Computes area-weighted RMSE, MAE, and Mean Bias per variable and lead time.
  4. Generates formatted Rich summary table and saves `validation_metrics.json`.

### 4.3 Secret Exclusion & Sanitization Protocol

To satisfy R2 and pass the security audit:
- **Sensitive Key Patterns**:
  Any environment variable containing substring (case-insensitive):
  `KEY`, `TOKEN`, `SECRET`, `PASS`, `AUTH`, `CREDENTIAL`, `BEARER`, `SIGNATURE`, `PRIVATE`, `WEBHOOK`.
- **Known Targets**:
  `NGC_CLI_API_KEY`, `CDSAPI_KEY`, `S3FS_KEY`, `S3FS_SECRET`, `HF_TOKEN`, `EUMETSAT_CONSUMER_KEY`, `EUMETSAT_CONSUMER_SECRET`, `EARTHMOVER_API_KEY`, `AWS_SECRET_ACCESS_KEY`.
- **Sanitization Rule**:
  `security.sanitize_dict(env_dict)` replaces sensitive values with `"[REDACTED]"`.
  When generating provenance manifests or logging environment snapshots, only the sanitized dictionary is serialized.
  Manifest generation explicitly verifies that no value contains high-entropy secret tokens.

---

## 5. Provenance Manifest Specification

Every execution of `run` or `validate` generates a machine-readable JSON manifest (`provenance_manifest.json`):

```json
{
  "manifest_version": "1.0.0",
  "experiment_id": "OD-EARTH2-001",
  "timestamp_utc": "2026-10-26T04:15:00Z",
  "invocation": {
    "entrypoint": "od_experiments.earth2_001.cli",
    "command": "run",
    "arguments": {
      "model": "dlwp",
      "source": "gfs",
      "time": "2024-01-01T00:00:00",
      "nsteps": 4,
      "device": "cpu"
    }
  },
  "git": {
    "commit_sha": "a1b2c3d4e5f6...",
    "branch": "feat/od-earth2-001",
    "dirty": false
  },
  "environment": {
    "python_version": "3.13.17",
    "earth2studio_version": "0.20.0a0",
    "torch_version": "2.5.0",
    "cuda_available": false,
    "platform": "Linux-6.18.54.1-microsoft-standard-WSL2-x86_64",
    "sanitized_env_vars": {
      "EARTH2STUDIO_CACHE": "/home/zrt/.cache/earth2studio",
      "NGC_CLI_API_KEY": "[REDACTED]",
      "HF_TOKEN": "[REDACTED]"
    }
  },
  "artifacts": [
    {
      "path": "forecast.zarr",
      "type": "forecast_store",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "size_bytes": 10485760
    }
  ]
}
```

---

## 6. Testing Strategies & Verification Plan

### 6.1 Test Suite Structure

Unit and integration tests for `od_experiments` will be located in `test/od_experiments/`:

| Test Module | Coverage Scope | Strategy & Mocking |
|---|---|---|
| `test_doctor.py` | `doctor` command | Runs offline; verifies system detection; tests behavior when optional dependencies are mocked as missing. |
| `test_inspect.py` | `inspect` command | Verifies schema outputs for `dlwp`, `persistence`, `gfs`, `arco`, and `random`. |
| `test_security.py` | Secret exclusion & scrubbing | Injects dummy secrets (`MOCK_SECRET_KEY="secret123"`); verifies that output manifests, terminal output, and logs contain `[REDACTED]` and never leak the plaintext value. |
| `test_provenance.py` | Manifest generation | Verifies Git SHA retrieval, environment capture, and SHA-256 checksum correctness against sample files. |
| `test_validation.py` | RMSE, MAE, Mean Bias | Unit test with synthetic tensors with known analytical error (e.g. $x = y + 3.0 \Rightarrow \text{MAE}=3.0, \text{RMSE}=3.0, \text{Bias}=3.0$); verifies cosine-latitude weights. |
| `test_cli_e2e.py` | End-to-end workflow | Tests full execution cycle `doctor` -> `inspect` -> `run` -> `validate` using `persistence` and `random` data in CPU mode without network access. |

### 6.2 Test Execution Protocol
- Test command:
  ```bash
  uv run pytest test/od_experiments/ -v
  ```
- Compliance: Must adhere to `e2s-000-python-style-guide.mdc` (SPDX license headers, type hints, black, ruff) and `e2s-003-unit-testing.mdc` (no docstrings on tests, strategic parametrization, high coverage).
