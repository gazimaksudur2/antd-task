#!/usr/bin/env bash
# Render.com Linux build — CPU-only PyTorch first (smaller/faster than CUDA wheels;
# Render Web Services do not expose GPUs on standard plans).
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pip install --upgrade pip setuptools wheel
# Pin CPU wheels before the rest of the stack so ultralytics does not pull a CUDA build.
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
