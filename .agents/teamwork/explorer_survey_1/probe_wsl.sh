#!/usr/bin/env bash
set -e
REPO_DIR="/mnt/d/programming/Blockchain development/Z-space/earth2studio"
cd "$REPO_DIR"

echo "=== System & Kernel ==="
uname -a
lsb_release -a

echo "=== CPU Info ==="
lscpu | grep -E 'Model name|CPU\(s\):|Thread\(s\) per core|Core\(s\) per socket'

echo "=== Memory & Swap ==="
free -h

echo "=== Disk Usage ==="
df -h "$REPO_DIR"

echo "=== Python Versions in WSL ==="
which python3 || true
python3 --version || true
which /home/zrt/.local/bin/python3.13 || true
/home/zrt/.local/bin/python3.13 --version || true

echo "=== UV in WSL ==="
which /home/zrt/.local/bin/uv || true
/home/zrt/.local/bin/uv --version || true

echo "=== Virtual Environments ==="
if [ -d "$REPO_DIR/.venv" ]; then
    echo ".venv exists. Contents:"
    ls -la "$REPO_DIR/.venv"
    if [ -f "$REPO_DIR/.venv/bin/python" ]; then
        "$REPO_DIR/.venv/bin/python" --version
    fi
fi

echo "=== PyTorch / CUDA Check in WSL ==="
/home/zrt/.local/bin/python3.13 -c '
try:
    import torch
    print("PyTorch version:", torch.__version__)
    print("CUDA available:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("Device count:", torch.cuda.device_count())
        print("Device name:", torch.cuda.get_device_name(0))
except ImportError:
    print("PyTorch not installed in system python3.13")
'

echo "=== Earth2Studio Import in WSL ==="
/home/zrt/.local/bin/python3.13 -c '
import sys
sys.path.insert(0, ".")
try:
    import earth2studio
    print("earth2studio imported successfully! Version:", earth2studio.__version__)
except Exception as e:
    print("Failed to import earth2studio:", e)
'
