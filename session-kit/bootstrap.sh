#!/usr/bin/env bash
# Thin wrapper so you can run the bootstrapper from a POSIX shell.
# Usage:
#   ./session-kit/bootstrap.sh --target ../my-campaign --group winterfell --title "Winterfell Falls"
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$here/bootstrap.py" "$@"
