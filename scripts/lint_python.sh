#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "$(uname -s)" == "Darwin" || "$(uname -s)" == "Linux" ]]; then
  VENV_PY="$ROOT_DIR/.venv/bin/python3"
else
  VENV_PY="$ROOT_DIR/.venv/Scripts/python.exe"
fi

if [[ ! -x "$VENV_PY" ]]; then
  echo "[lint-python] Missing virtual environment. Run scripts/setup_python_env.sh first."
  exit 1
fi

echo "[lint-python] Running ruff check..."
"$VENV_PY" -m ruff check .

echo "[lint-python] Running ruff format..."
"$VENV_PY" -m ruff format .
