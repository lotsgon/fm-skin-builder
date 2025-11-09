#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_BIN="$FRONTEND_DIR/src-tauri/resources/backend/fm_skin_builder"
SETUP_SCRIPT_SH="$ROOT_DIR/scripts/setup_python_env.sh"
SETUP_SCRIPT_PS1="$ROOT_DIR/scripts/setup_python_env.ps1"

if [[ "${OS:-}" == "Windows_NT" || "$(uname -s)" == MINGW* || "$(uname -s)" == CYGWIN* || "$(uname -s)" == MSYS* ]]; then
  if command -v pwsh >/dev/null 2>&1; then
    pwsh -NoLogo -NoProfile -ExecutionPolicy Bypass -File "$SETUP_SCRIPT_PS1"
  else
    bash "$SETUP_SCRIPT_SH"
  fi
else
  bash "$SETUP_SCRIPT_SH"
fi

if [[ "${FORCE_BACKEND_BUILD:-0}" == "1" || ! -x "$BACKEND_BIN" ]]; then
  echo "[tauri] Ensuring backend binary is available..."
  "$ROOT_DIR/scripts/build_backend.sh"
fi

cd "$FRONTEND_DIR"
npm run tauri -- "$@"
