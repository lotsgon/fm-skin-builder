#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FORCE_BACKEND_BUILD=1 "$ROOT_DIR/scripts/run_tauri.sh" dev
