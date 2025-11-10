#!/bin/bash
# run-catalogue-docker.sh
# Runs the FM Skin Builder catalogue command in Docker (Linux environment)
# This solves the macOS UnityPy decoder crash issues

set -e

# Default values
FM_VERSION=""
BUNDLE_PATH=""
OUTPUT_PATH="./build/catalogue"
CATALOGUE_VERSION="1"
PRETTY=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --bundle)
            BUNDLE_PATH="$2"
            shift 2
            ;;
        --fm-version)
            FM_VERSION="$2"
            shift 2
            ;;
        --out)
            OUTPUT_PATH="$2"
            shift 2
            ;;
        --catalogue-version)
            CATALOGUE_VERSION="$2"
            shift 2
            ;;
        --pretty)
            PRETTY="--pretty"
            shift
            ;;
        --help)
            echo "Usage: ./run-catalogue-docker.sh --bundle <path> --fm-version <version> [OPTIONS]"
            echo ""
            echo "Required:"
            echo "  --bundle <path>           Path to bundles directory (on host machine)"
            echo "  --fm-version <version>    FM version (e.g., '2025.0.0')"
            echo ""
            echo "Optional:"
            echo "  --out <path>              Output directory (default: ./build/catalogue)"
            echo "  --catalogue-version <n>   Catalogue version number (default: 1)"
            echo "  --pretty                  Pretty-print JSON output"
            echo ""
            echo "Example:"
            echo "  ./run-catalogue-docker.sh --bundle test_bundles --fm-version '2025.0.0'"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [ -z "$BUNDLE_PATH" ]; then
    echo "Error: --bundle is required"
    echo "Use --help for usage information"
    exit 1
fi

if [ -z "$FM_VERSION" ]; then
    echo "Error: --fm-version is required"
    echo "Use --help for usage information"
    exit 1
fi

# Expand ~ to home directory
BUNDLE_PATH="${BUNDLE_PATH/#\~/$HOME}"
OUTPUT_PATH="${OUTPUT_PATH/#\~/$HOME}"

# Convert to absolute paths
if [[ ! "$BUNDLE_PATH" = /* ]]; then
    BUNDLE_PATH="$(pwd)/$BUNDLE_PATH"
fi
if [[ ! "$OUTPUT_PATH" = /* ]]; then
    OUTPUT_PATH="$(pwd)/$OUTPUT_PATH"
fi

# Verify bundle path exists
if [ ! -d "$BUNDLE_PATH" ]; then
    echo "Error: Bundle path does not exist: $BUNDLE_PATH"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_PATH"

# Resolve to canonical path (handles symlinks and normalizes path)
BUNDLE_PATH=$(cd "$BUNDLE_PATH" && pwd)
OUTPUT_PATH=$(cd "$OUTPUT_PATH" && pwd)

echo "======================================"
echo "FM Skin Builder - Docker Catalogue"
echo "======================================"
echo "Bundle path:  $BUNDLE_PATH"
echo "Output path:  $OUTPUT_PATH"
echo "FM version:   $FM_VERSION"
echo "======================================"
echo ""

# Check if Docker image exists, build if not
if ! docker image inspect fm-skin-builder:latest >/dev/null 2>&1; then
    echo "Docker image not found. Building..."
    docker build -t fm-skin-builder:latest .
    echo ""
fi

# Run the catalogue command in Docker
echo "Running catalogue builder in Docker..."
docker run --rm \
    -v "$BUNDLE_PATH:/bundles:ro" \
    -v "$OUTPUT_PATH:/output" \
    fm-skin-builder:latest \
    --bundle /bundles \
    --fm-version "$FM_VERSION" \
    --out /output \
    --catalogue-version "$CATALOGUE_VERSION" \
    $PRETTY

echo ""
echo "✅ Done! Catalogue output is in: $OUTPUT_PATH"
