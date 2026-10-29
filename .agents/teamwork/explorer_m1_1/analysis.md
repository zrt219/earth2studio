# Technical Analysis: Milestone 1 Environment Setup & Verification

**Author**: `explorer_m1_1`  
**Milestone**: Milestone 1 (F1: Hardware Discovery, F2: Environment & Editable Install)  
**Date**: 2026-10-26  

---

## 1. Executive Summary

This investigation designs and verifies the exact environment configuration procedure for Milestone 1 of the **OD-EARTH2-001** research lab. The target environment is Ubuntu 24.04.4 LTS running in WSL2 on Windows 10, utilizing `/home/zrt/.local/bin/uv` (version 0.13.5) to manage an isolated virtual environment (`.venv`) for `earth2studio` in editable mode.

Key findings include:
1. **Critical Path Pitfall**: The repository path contains a space (`/mnt/d/programming/Blockchain development/Z-space/earth2studio`), and a file named `/mnt/d/programming/Blockchain` exists on the filesystem. Any unquoted shell command referencing this path causes bash to attempt executing `/mnt/d/programming/Blockchain`, failing with syntax errors. All bash commands must rigorously quote this path.
2. **Git Safe Directory Requirement**: Because the repository resides on a DrvFs/9P NTFS mount (`/mnt/d`), Git in WSL2 detects divergent user ownership and will block operations unless `safe.directory` is configured.
3. **`uv sync` Mechanism**: The repository contains a fully pinned `uv.lock` (10,743 lines, SHA-256 locked for 191 packages). Running `uv sync` in the repository root automatically uses `.venv`, installs all locked dependencies (core, dev, and build groups), and installs `earth2studio` in PEP 660 editable mode (`earth2studio @ file:///mnt/d/...`).
4. **Editable Verification Caveat**: Testing `python -c "import earth2studio"` from within the repository root can produce false positives because Python places `''` (current working directory) on `sys.path[0]`. We establish two definitive verification methods: `python -P` (isolated path) and execution from an external directory (`/tmp`), coupled with direct inspection of `site-packages/earth2studio-*.dist-info/direct_url.json` and a live attribute edit test.
5. **Zero Billable Cloud Cost & Credential Isolation**: A symlink `/home/zrt/.aws -> /mnt/c/Users/Zhane/.aws` exists in WSL2 containing Windows host credentials. To guarantee 100% zero billable cloud cost and prevent unintentional credential usage or leakage, research scripts and CLI commands must explicitly enforce anonymous access (`skip_signature=True`, `AWS_NO_SIGN_REQUEST=YES`, `AWS_SHARED_CREDENTIALS_FILE=/dev/null`). Public NOAA GFS data (`s3://noaa-gfs-bdp-pds`) and public NVIDIA DLWP checkpoints (`ngc://models/nvidia/modulus/...`) are verified to be zero-cost anonymous downloads.

---

## 2. Hardware & Host Discovery (Feature F1)

Direct probing via WSL2 shell commands (`lscpu`, `free -h`, `df -h`, `cat /etc/os-release`, and device tree inspection) reveals the following host profile:

| Subsystem | Discovered Value | Operational Implication |
|---|---|---|
| **CPU** | AMD Ryzen 5 3600 6-Core Processor (12 threads @ 3.6 GHz base) | 12 threads available for parallel data loading and CPU tensor ops. |
| **System Memory** | 15.0 GiB allocated to WSL2 (out of 32 GB host RAM), 4.0 GiB swap | Sufficient for small-batch global grid inference (DLWP 721x1440 or 64x64 cubed sphere). |
| **Disk Storage** | Drive D: (NTFS, 3.7 TB capacity, 134 GB available mounted at `/mnt/d`) | Plenty of storage for GFS GRIB cache and model checkpoints. |
| **Operating System** | Ubuntu 24.04.4 LTS (Noble Numbat), Linux kernel 6.18.54.1-microsoft-standard-WSL2 | Modern glibc and Linux 6.18 kernel; full support for Python 3.12/3.13 wheels. |
| **GPU / Acceleration** | AMD Radeon RX 9060 XT passed through via DirectX/DRI (`/dev/dxg`, `/dev/dri/card0`, `/dev/dri/renderD128`) | **No NVIDIA CUDA driver / hardware.** `torch.cuda.is_available()` will be `False`. PyTorch and Earth2Studio MUST run in **CPU execution fallback mode** (`device="cpu"`). |
| **Python Runtimes** | Python 3.12.3 at `/usr/bin/python3`, Python 3.13.17 managed by uv at `/home/zrt/.local/share/uv/python/cpython-3.13-linux-x86_64-gnu/bin/python3.13` | `.venv` is configured for Python 3.13.17, satisfying `requires-python = ">=3.11,<3.15"`. |
| **Package Manager** | `uv 0.13.5` installed at `/home/zrt/.local/bin/uv` | High-speed package management with local cache in `/home/zrt/.cache/uv` (8.0 GB). |

---

## 3. Environment & Editable Install Analysis (Feature F2)

### 3.1 Current Workspace State
- `.venv` exists in the repository root (`pyvenv.cfg` points to `cpython-3.13-linux-x86_64-gnu/bin`).
- Currently, `.venv/lib/python3.13/site-packages` is **empty** (no dependencies or editable links installed yet).
- When Python was invoked in the repo root without flags, `import earth2studio` appeared to succeed only because `sys.path[0]` is `''`. When tested with `-P` or from `/tmp`, it properly failed with `ModuleNotFoundError: No module named 'earth2studio'`.

### 3.2 Command Sequence for `uv sync`
The Worker must execute the following bash sequence inside WSL2:

```bash
# 1. Configure git safe directory to prevent dubious ownership errors on DrvFs
git config --global --add safe.directory "/mnt/d/programming/Blockchain development/Z-space/earth2studio"

# 2. Navigate to the repository root
cd "/mnt/d/programming/Blockchain development/Z-space/earth2studio"

# 3. Synchronize virtual environment with lockfile in editable mode
/home/zrt/.local/bin/uv sync
```

### 3.3 What `uv sync` Does
1. Inspects `uv.lock` and compares it against `.venv`.
2. Resolves 191 packages across `dependencies`, `default-groups = ["dev", "build"]`.
3. Installs wheels (PyTorch, xarray, zarr, s3fs, netCDF4, pytest, black, ruff, hatchling, etc.) from `~/.cache/uv` and PyPI.
4. Builds and installs `earth2studio` in editable mode:
   - Emits `.venv/lib/python3.13/site-packages/earth2studio.pth` (or `__editable__.earth2studio-0.20.0a0.pth`) pointing to `/mnt/d/programming/Blockchain development/Z-space/earth2studio`.
   - Emits `site-packages/earth2studio-0.20.0a0.dist-info/direct_url.json` with `{"dir_info": {"editable": true}, "url": "file:///mnt/d/programming/Blockchain%20development/Z-space/earth2studio"}`.

---

## 4. Testing & Verifying the Editable Install

To guarantee zero false positives, the Worker must execute this 4-step verification suite:

### Test 1: Isolated Path Import (`-P` flag)
```bash
cd "/mnt/d/programming/Blockchain development/Z-space/earth2studio"
.venv/bin/python -P -c "import earth2studio; print('Version:', earth2studio.__version__); print('Location:', earth2studio.__file__)"
```
**Expected Outcome**:
- Exit code: 0
- Version: `0.20.0a0`
- Location: `/mnt/d/programming/Blockchain development/Z-space/earth2studio/earth2studio/__init__.py` (pointing to the working repository, not to site-packages).

### Test 2: External Working Directory Import
```bash
(cd /tmp && "/mnt/d/programming/Blockchain development/Z-space/earth2studio/.venv/bin/python" -c "import earth2studio; print('Import from /tmp succeeded:', earth2studio.__version__)")
```
**Expected Outcome**:
- Exit code: 0
- Succeeded without `ModuleNotFoundError`.

### Test 3: PEP 660 Metadata Verification
```bash
python3 -c "
import json, glob
path = glob.glob('.venv/lib/python3.*/site-packages/earth2studio*.dist-info/direct_url.json')[0]
with open(path) as f:
    data = json.load(f)
assert data.get('dir_info', {}).get('editable') is True
print('PEP 660 editable flag confirmed:', data)
"
```
**Expected Outcome**:
- Exit code: 0
- Prints `"editable": True`.

### Test 4: Live Code Modification Reflection (Roundtrip Test)
```bash
# 1. Append a temporary canary variable
echo '__od_editable_canary__ = "M1_VERIFIED_OK"' >> earth2studio/__init__.py

# 2. Check if .venv python immediately sees it without reinstalling
.venv/bin/python -P -c "import earth2studio; assert earth2studio.__od_editable_canary__ == 'M1_VERIFIED_OK'; print('Live reload OK!')"

# 3. Clean up the canary line
git checkout earth2studio/__init__.py

# 4. Confirm clean status
git status -s earth2studio/__init__.py
```
**Expected Outcome**:
- `Live reload OK!` printed.
- Git working directory restored to clean state.

---

## 5. Zero Billable Cloud Cost Verification

### 5.1 The Risk: Symlinked Host AWS Credentials
WSL2 contains a symlink `/home/zrt/.aws -> /mnt/c/Users/Zhane/.aws`, which holds active or historical Windows AWS credentials. Any tool that creates a standard Boto3/AWS session might accidentally read these credentials and make authenticated, potentially billable calls.

### 5.2 Defense & Verification Protocol
1. **Source Code Proof (`skip_signature=True`)**:
   In `earth2studio/data/utils.py` (lines 1003-1008):
   ```python
   if anonymous and url.startswith(("s3://", "gs://")):
       kwargs["skip_signature"] = True
   ```
   `anonymous=True` is the default in all Earth2Studio obstore data sources (including GFS, GEFS, HRRR). The underlying Rust `object_store` library ignores AWS credential chains and sends anonymous HTTP requests.
2. **Sponsorship Proof (AWS Open Data)**:
   The NOAA GFS bucket (`s3://noaa-gfs-bdp-pds`) is enrolled in the AWS Open Data Sponsorship Program (`https://registry.opendata.aws/noaa-gfs-bdp-pds/`). Egress and GET requests are sponsored by AWS; anonymous callers incur exactly $0.00.
3. **NGC Public Catalog Proof**:
   DLWP model weights (`ngc://models/nvidia/modulus/modulus_dlwp_cubesphere@v0.2`) resolve to public HTTPS endpoints. In `earth2studio/models/auto/ngc.py`, `authenticated_api: bool = False` by default. No NGC API key is needed.
4. **Environment Isolation Guardrail**:
   To ensure that neither AWS SDKs nor secondary libraries ever query host credentials, research execution commands must export:
   ```bash
   export AWS_NO_SIGN_REQUEST=YES
   export AWS_EC2_METADATA_DISABLED=true
   export AWS_SHARED_CREDENTIALS_FILE=/dev/null
   export AWS_CONFIG_FILE=/dev/null
   unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN AWS_PROFILE
   ```
5. **Zero-Cost Verification Script**:
   A test asserting:
   - No paid cloud provider credentials in active environment.
   - NOAA GFS fetch initiates with `skip_signature=True`.
   - Offline tests run without network access (`Random` data source and `Persistence` baseline model).

---

## 6. Recommended Implementation Plan for Worker

The Worker should execute the following 4 phases for Milestone 1:

1. **Phase 1: Git Safe Directory & Space Handling Safeguard**
   - Execute `git config --global --add safe.directory "/mnt/d/programming/Blockchain development/Z-space/earth2studio"`.
2. **Phase 2: Environment Sync via `uv sync`**
   - Run `/home/zrt/.local/bin/uv sync` in the repository root.
   - Monitor completion and check `.venv/bin/python --version` (3.13.x).
3. **Phase 3: Editable Verification Suite**
   - Run Test 1 (`python -P`), Test 2 (external `/tmp`), Test 3 (PEP 660 `direct_url.json`), and Test 4 (canary roundtrip edit).
4. **Phase 4: Hardware & Environment Report Generation**
   - Execute hardware probe script to generate a machine-readable `hardware_discovery.json` documenting CPU, RAM, disk, OS, and GPU/CPU fallback.
   - Run zero-cost credential isolation verification.
