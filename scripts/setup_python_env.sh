#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$ROOT_DIR/.python-version" ]]; then
  DEFAULT_PY_VERSION="$(tr -d '\r' < "$ROOT_DIR/.python-version")"
else
  DEFAULT_PY_VERSION="3.9.19"
fi
PY_VERSION="${PY_VERSION:-$DEFAULT_PY_VERSION}"
PYTHON_BIN=""

if command -v pyenv >/dev/null 2>&1; then
  if ! pyenv versions --bare | grep -Fxq "$PY_VERSION"; then
    echo "[setup-python] Installing Python $PY_VERSION via pyenv..."
    pyenv install "$PY_VERSION"
  fi
  PYTHON_BIN="$(pyenv root)/versions/$PY_VERSION/bin/python3"
else
  if [[ -n "${PYTHON_BIN_OVERRIDE:-}" ]]; then
    PYTHON_BIN="$PYTHON_BIN_OVERRIDE"
  else
    PYTHON_BIN="$(command -v python3 || command -v python || true)"
  fi

  if [[ -z "$PYTHON_BIN" ]]; then
    echo "[setup-python] python3 not found. Install Python $PY_VERSION or set PYTHON_BIN_OVERRIDE."
    exit 1
  fi

  DETECTED_VERSION="$($PYTHON_BIN -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])')"
  if [[ "$DETECTED_VERSION" != "$PY_VERSION" ]]; then
    cat <<MSG
[setup-python] Expected Python $PY_VERSION but found $DETECTED_VERSION at $PYTHON_BIN.
Install pyenv (https://github.com/pyenv/pyenv) or set PYTHON_BIN_OVERRIDE to a $PY_VERSION interpreter.
MSG
    exit 1
  fi
fi

VENV_DIR="$ROOT_DIR/.venv"
if [[ -d "$VENV_DIR" ]]; then
  echo "[setup-python] Reusing existing virtual environment at $VENV_DIR"
else
  echo "[setup-python] Creating virtual environment at $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

if [[ "$(uname -s)" == "Darwin" || "$(uname -s)" == "Linux" ]]; then
  VENV_PY="$VENV_DIR/bin/python3"
else
  VENV_PY="$VENV_DIR/Scripts/python.exe"
fi

"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install -r "$ROOT_DIR/requirements-dev.txt"

echo "[setup-python] Environment ready. Activate with: source $VENV_DIR/bin/activate"
