#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/frontend/src-tauri/resources/backend"
ENTRY_POINT="$ROOT_DIR/fm_skin_builder/cli/main.py"
BINARY_NAME="fm_skin_builder"

if [[ "$(uname -s)" == "Darwin" || "$(uname -s)" == "Linux" ]]; then
  VENV_PY="$ROOT_DIR/.venv/bin/python3"
else
  VENV_PY="$ROOT_DIR/.venv/Scripts/python.exe"
fi

if [[ ! -x "$VENV_PY" ]]; then
  echo "[build-backend] Virtual environment missing. Run scripts/setup_python_env.sh first."
  exit 1
fi

pushd "$ROOT_DIR" >/dev/null

"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install -r requirements.txt pyinstaller

rm -rf build dist "$BINARY_NAME.spec"
"$VENV_PY" -m PyInstaller --onefile --name "$BINARY_NAME" "$ENTRY_POINT"

mkdir -p "$DIST_DIR"
rm -f "$DIST_DIR/$BINARY_NAME"
cp "dist/$BINARY_NAME" "$DIST_DIR/"

popd >/dev/null

echo "Backend binary available at $DIST_DIR/$BINARY_NAME"
