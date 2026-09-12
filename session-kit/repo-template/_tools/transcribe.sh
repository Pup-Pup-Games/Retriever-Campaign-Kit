#!/usr/bin/env bash
# Linux / macOS launcher for transcribe.py.
#
# Does two things you'd otherwise do by hand every run:
#
#   1. Runs the repo venv's python, so faster-whisper is on the path.
#   2. Picks the fastest device that actually works here, and — on NVIDIA —
#      puts the pip-installed cuBLAS/cuDNN on LD_LIBRARY_PATH. ctranslate2
#      (under faster-whisper) links those at runtime and cannot find them
#      on its own, so without this every GPU run dies on a library load.
#
# Usage — anything you pass is handed straight to transcribe.py:
#
#   ./_tools/transcribe.sh --input session.m4a
#   ./_tools/transcribe.sh --track "GM=gm.wav" --track "Brann=brann.wav" \
#       --group your-campaign
#
# An explicit --device or --compute-type always wins over the auto-choice.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO/.venv"

if [[ ! -x "$VENV/bin/python" ]]; then
  cat >&2 <<'MSG'
No .venv in this repo. Create it once:

  python3 -m venv .venv
  .venv/bin/pip install faster-whisper

  # NVIDIA GPU only — makes --device cuda work:
  .venv/bin/pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
MSG
  exit 1
fi

# The nvidia wheels land under a python-version-specific path; don't hardcode it.
nvidia_dir=""
for d in "$VENV"/lib/python*/site-packages/nvidia; do
  [[ -d "$d" ]] && nvidia_dir="$d" && break
done

# Use the GPU only if the libraries are installed AND the driver actually
# answers. A half-upgraded NVIDIA driver makes nvidia-smi fail, and CUDA then
# reports a misleading "out of memory" — falling back to the CPU is friendlier
# than dying. macOS never has any of this and lands on the CPU path.
device="cpu" ; compute="int8"
if [[ -n "$nvidia_dir" && -d "$nvidia_dir/cublas/lib" ]] \
   && command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
  export LD_LIBRARY_PATH="$nvidia_dir/cublas/lib:$nvidia_dir/cudnn/lib:${LD_LIBRARY_PATH:-}"
  device="cuda" ; compute="float16"
fi

extra=()
if [[ " $* " == *" --device "* ]]; then
  : # caller chose; say nothing
else
  extra+=(--device "$device")
  echo "transcribe.sh: using --device $device" >&2
  [[ "$device" == "cpu" ]] && echo "transcribe.sh: no usable NVIDIA GPU found; this will be slow on a long session." >&2
fi
[[ " $* " == *" --compute-type "* ]] || extra+=(--compute-type "$compute")

exec "$VENV/bin/python" "$REPO/_tools/transcribe.py" "${extra[@]}" "$@"
