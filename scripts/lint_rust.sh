#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$ROOT_DIR/frontend/src-tauri"

pushd "$APP_DIR" >/dev/null
cargo fmt -- --check
cargo clippy --no-deps -- -D warnings
popd >/dev/null
