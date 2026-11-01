# Handoff Report: Milestone 1 Environment Setup & Verification (Hard Handoff)

**Sender**: `explorer_m1_1`  
**Recipient**: `77a68bcc-3e86-4665-9fe7-9fe95b669349` (Orchestrator)  
**Milestone**: Milestone 1 (F1: Hardware Discovery, F2: Environment & Editable Install)  
**Artifact Path**: `.agents/teamwork/explorer_m1_1/handoff.md`  

---

## 1. Observation

1. **Host Hardware Probing**:
   - `wsl -e bash -c "lscpu; free -h; df -h .; cat /etc/os-release"`
     - CPU: `AMD Ryzen 5 3600 6-Core Processor` (12 threads online: 0-11)
     - Memory: `15Gi` total allocated to WSL2 (723Mi used, 14Gi available), 4.0Gi swap
     - Storage: Drive D: 3.7T total, 134G available mounted at `/mnt/d`
     - OS: `Ubuntu 24.04.4 LTS (Noble Numbat)`, Linux 6.18.54.1-microsoft-standard-WSL2
   - `wsl -e bash -c "which nvidia-smi || true; ls -l /dev/dxg /dev/kfd /dev/dri 2>/dev/null || true"`
     - `nvidia-smi` is absent.
     - `/dev/dxg` exists (DirectX GPU passthrough).
     - `/dev/dri/card0` and `/dev/dri/renderD128` exist (AMD Radeon RX 9060 XT).
     - No NVIDIA CUDA hardware/driver present.

2. **Python & Tooling Discovery**:
   - `wsl -e bash -c "whoami; which uv; /home/zrt/.local/bin/uv --version"`
     - User: `zrt`
     - `uv 0.13.5 (x86_64-unknown-linux-gnu)` at `/home/zrt/.local/bin/uv`
   - `wsl -e bash -c "/home/zrt/.local/bin/uv python list"`
     - Managed Python 3.13: `/home/zrt/.local/share/uv/python/cpython-3.13-linux-x86_64-gnu/bin/python3.13`
     - System Python 3.12: `/usr/bin/python3.12`
   - UV Cache: `/home/zrt/.cache/uv` contains 8.0 GB of cached wheels and git repos.

3. **Filesystem Collision & Space Bug**:
   - Directory path: `/mnt/d/programming/Blockchain development/Z-space/earth2studio`
   - In `/mnt/d/programming/`, there exists a file named `Blockchain` (`-rwxrwxrwx 1 zrt zrt 645 May 20 21:04 Blockchain`).
   - Verbatim error when executing unquoted commands:
     `/mnt/d/programming/Blockchain: line 2: usage:: command not found`
     `/mnt/d/programming/Blockchain: line 6: syntax error near unexpected token '('`

4. **Git Safe Directory Behavior**:
   - Running `git` inside WSL2 on `/mnt/d/...` initially hung or blocked because `safe.directory` was not set on the DrvFs mount.
   - Command `wsl -e git -c safe.directory="*" rev-parse HEAD` immediately succeeded with commit `39ef89c08c4f8a2c374f9a19a155a5f165665dc2`.

5. **Existing Virtual Environments & False Positive Import**:
   - `.venv` exists with `pyvenv.cfg` pointing to Python 3.13.17 (`home = /home/zrt/.local/share/uv/python/cpython-3.13-linux-x86_64-gnu/bin`).
   - `.venv/lib/python3.13/site-packages` is completely empty (`total 0`).
   - When running `.venv/bin/python -c 'import earth2studio; print(earth2studio.__file__)'` inside the repository directory, it printed `/mnt/d/.../earth2studio/__init__.py 0.20.0a0` because `sys.path[0]` is `''` (current working directory).
   - When running isolated path import `.venv/bin/python -P -c "import earth2studio"`, it produced verbatim error:
     `ModuleNotFoundError: No module named 'earth2studio'`
   - When running from outside the repo (`wsl --cd /tmp`), it produced verbatim error:
     `ModuleNotFoundError: No module named 'earth2studio'`

6. **Lockfile & Dry-run Output**:
   - `uv.lock` is present at revision 5 (10,743 lines), completely pinned.
   - Running `/home/zrt/.local/bin/uv sync --dry-run` yielded:
     ```
     Would use project environment at: .venv
     Resolved 452 packages in 22ms
     Found up-to-date lockfile at: uv.lock
     Would download 144 packages
     Would install 191 packages
     ...
     + earth2studio==0.20.0a0 (from file:///mnt/d/programming/Blockchain%20development/Z-space/earth2studio)
     ```

7. **Data Sources & Cloud Cost Audit**:
   - `earth2studio/data/utils.py` lines 968-1008:
     `def obstore_store_from_url(url: str, anonymous: bool = True, ...)` sets `kwargs["skip_signature"] = True` for S3/GS URLs.
   - `earth2studio/data/gfs.py` lines 110-135:
     `GFS_BUCKET_NAME = "noaa-gfs-bdp-pds"`, accessed via AWS Open Data Sponsorship Program at $0.00 cost.
   - `earth2studio/models/auto/ngc.py` lines 103-145:
     `authenticated_api: bool = False` by default; downloads public modulus weights via anonymous HTTP GET.
   - Symlink check: `/home/zrt/.aws -> /mnt/c/Users/Zhane/.aws` exists in WSL2, containing host AWS credentials.

---

## 2. Logic Chain

1. **From Observation 1**: The host has an AMD Ryzen 5 3600 CPU and an AMD Radeon RX 9060 XT GPU. Because CUDA is proprietary to NVIDIA hardware, PyTorch running under Linux/WSL2 cannot utilize CUDA acceleration. Therefore, all Earth2Studio workflows in this environment must explicitly run with CPU execution fallback (`device="cpu"`).
2. **From Observation 3**: The parent directory `/mnt/d/programming/` contains a file named `Blockchain` with executable permissions. When a bash command does not quote `/mnt/d/programming/Blockchain development/...`, bash splits the string at the space, interpreting `/mnt/d/programming/Blockchain` as an executable script and `development/...` as its arguments. Therefore, every shell invocation in scripts, documentation, and automated tests must quote the repository path.
3. **From Observation 4**: Git on WSL2 strictly verifies ownership of repository directories. On DrvFs mounts (`/mnt/d`), ownership mapping can trigger git security restrictions. Configuring `git config --global --add safe.directory "/mnt/d/programming/Blockchain development/Z-space/earth2studio"` resolves this deterministically.
4. **From Observation 5**: Python automatically inserts `''` (current working directory) into `sys.path[0]` when run interactively or via `-c`. This causes a false appearance that `earth2studio` is installed in `.venv`, even when `site-packages` is completely empty. The isolated flag `-P` (PEP 538/632) suppresses `sys.path[0]` insertion, providing an unambiguous test for true editable installation in `.venv`.
5. **From Observation 6**: `uv sync` reads `pyproject.toml` and `uv.lock`. In `pyproject.toml`, `default-groups = ["dev", "build"]` is defined, and `uv sync` installs the workspace root package in PEP 660 editable mode (`-e .`) by default. Running `/home/zrt/.local/bin/uv sync` will populate `.venv` with all 191 locked dependencies and create the editable pointer `_earth2studio.pth`.
6. **From Observation 7**: While Earth2Studio's `obstore_store_from_url` injects `skip_signature=True`, standard AWS SDKs (e.g. `boto3` or `s3fs`) may automatically read the symlinked `/home/zrt/.aws/credentials`. Therefore, to guarantee zero billable cost and eliminate credential leakage, the execution environment must set `AWS_NO_SIGN_REQUEST=YES`, `AWS_SHARED_CREDENTIALS_FILE=/dev/null`, and `AWS_CONFIG_FILE=/dev/null`.

---

## 3. Caveats

1. **Internet Access During Initial Sync**: `uv sync` requires downloading 144 wheels (or pulling them from the 8.0 GB cache) on the first execution. Once `.venv` is populated, subsequent `doctor` runs and test suites can execute completely offline.
2. **PyTorch Wheel Size**: PyTorch CPU/CUDA wheels can be large (~1-2 GB). However, PyPI is verified reachable with fast latency (~3ms HTTP/2 response).
3. **Optional Model Extras**: Milestone 1 focuses on the core editable installation and dev/build dependency groups. Heavy optional model extras with specialized CUDA C-extensions (like `flash-attn`, `natten`, or `cupy`) were excluded from `uv.lock`'s default groups and should remain uninstalled since the host does not have CUDA.

---

## 4. Conclusion

1. **The Exact WSL2 Bash Command Sequence** to set up the environment in editable mode is:
   ```bash
   git config --global --add safe.directory "/mnt/d/programming/Blockchain development/Z-space/earth2studio"
   cd "/mnt/d/programming/Blockchain development/Z-space/earth2studio"
   /home/zrt/.local/bin/uv sync
   ```
2. **The Verification Method for Editable Install** requires:
   - Isolated path import: `.venv/bin/python -P -c "import earth2studio; print(earth2studio.__file__)"` confirming it points to `/mnt/d/.../earth2studio/__init__.py`.
   - External directory test from `/tmp`.
   - Inspection of `.venv/lib/python3.13/site-packages/earth2studio-*.dist-info/direct_url.json` confirming `"editable": true`.
   - Live code modification roundtrip test (adding a canary variable, asserting presence without reinstall, and reverting via git).
3. **Zero Billable Cloud Cost Proof** is established by:
   - Verifying `AWS_NO_SIGN_REQUEST=YES` and `AWS_SHARED_CREDENTIALS_FILE=/dev/null` to isolate host credentials in `/home/zrt/.aws`.
   - Verifying that GFS fetches use `skip_signature=True` against AWS Open Data (`s3://noaa-gfs-bdp-pds`, $0.00).
   - Verifying that DLWP model weights use anonymous HTTP GET against NVIDIA NGC public catalog ($0.00).
   - Verifying that baseline models (`Persistence`) and synthetic data (`Random`) operate 100% offline with zero network requests.

---

## 5. Verification Method

To independently verify the environment and findings:

1. **Verify Path Space Quoting & Git Safe Directory**:
   ```bash
   wsl -e bash -c 'git config --global --add safe.directory "/mnt/d/programming/Blockchain development/Z-space/earth2studio" && git status -s'
   ```
2. **Verify UV Sync Dry-Run**:
   ```bash
   wsl -e bash -c 'cd "/mnt/d/programming/Blockchain development/Z-space/earth2studio" && /home/zrt/.local/bin/uv sync --dry-run'
   ```
3. **Verify Isolated Import Rejection Prior to Sync (Negative Control)**:
   ```bash
   wsl -e bash -c 'cd "/mnt/d/programming/Blockchain development/Z-space/earth2studio" && .venv/bin/python -P -c "import earth2studio"'
   # Must fail with ModuleNotFoundError until uv sync is completed
   ```
4. **Verify Host Credential Isolation**:
   ```bash
   wsl -e bash -c 'export AWS_NO_SIGN_REQUEST=YES AWS_SHARED_CREDENTIALS_FILE=/dev/null; env | grep -E "AWS_NO_SIGN_REQUEST|AWS_SHARED_CREDENTIALS_FILE"'
   ```

**Invalidation Conditions**:
- If `uv sync` fails with conflict errors across optional dependencies.
- If `python -P -c "import earth2studio"` fails after `uv sync`.
- If modifying `earth2studio/__init__.py` requires running `uv pip install` or `uv sync` again to be visible.
- If any billing-enabled AWS or GCP account is contacted during pipeline execution.
