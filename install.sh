#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_PATH="${1:-/Applications/Antigravity.app}"

python3 "${SCRIPT_DIR}/patch.py" install --app "${APP_PATH}"
