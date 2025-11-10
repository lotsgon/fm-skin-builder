# Running Catalogue Builder with Docker (macOS Solution)

Due to UnityPy's DXT texture decoder crashing on macOS, we provide a Docker-based solution that runs the catalogue builder in a Linux environment where everything works perfectly.

## Prerequisites

- Docker Desktop for Mac installed and running
- Your FM bundles in a local directory

## Quick Start

1. **Make the script executable** (first time only):
   ```bash
   chmod +x run-catalogue-docker.sh
   ```

2. **Run the catalogue builder**:
   ```bash
   ./run-catalogue-docker.sh --bundle test_bundles --fm-version "2025.0.0"
   ```

The first time you run this, Docker will build the image (takes a few minutes). Subsequent runs are fast.

## Usage

```bash
./run-catalogue-docker.sh --bundle <path> --fm-version <version> [OPTIONS]
```

### Required Arguments

- `--bundle <path>` - Path to your bundles directory on your Mac
- `--fm-version <version>` - FM version string (e.g., "2025.0.0")

### Optional Arguments

- `--out <path>` - Output directory (default: `./build/catalogue`)
- `--catalogue-version <n>` - Catalogue version number (default: 1)
- `--pretty` - Pretty-print JSON output for debugging

### Examples

**Basic usage:**
```bash
./run-catalogue-docker.sh \
  --bundle ~/FM2025/bundles \
  --fm-version "2025.0.0"
```

**Custom output directory:**
```bash
./run-catalogue-docker.sh \
  --bundle test_bundles \
  --fm-version "2025.0.0" \
  --out ./my-catalogue
```

**Pretty-printed JSON for debugging:**
```bash
./run-catalogue-docker.sh \
  --bundle test_bundles \
  --fm-version "2025.0.0" \
  --pretty
```

## How It Works

1. **Docker Image**: The script builds a Linux-based Docker image with all dependencies
2. **Volume Mounts**: Your bundle directory is mounted read-only, output directory is mounted read-write
3. **Runs in Linux**: Inside the container, the catalogue builder runs on Linux where UnityPy's decoder works perfectly
4. **Results on Mac**: Output files are written directly to your Mac filesystem via the mounted volume

## Output

The catalogue will be created in your output directory (default: `./build/catalogue/`):

```
build/catalogue/2025.0.0-v1/
├── metadata.json          # Catalogue metadata
├── css_variables.json     # CSS variables (split files)
├── css_classes.json       # CSS classes (split files)
├── sprites.json           # Sprite data (split files)
├── textures.json          # Texture data (split files)
├── fonts.json             # Font data (split files)
├── search/
│   ├── by_color.json      # Color search index
│   └── by_tag.json        # Tag search index
└── thumbnails/            # WebP thumbnails (256x256)
    ├── sprites/
    └── textures/
```

## Troubleshooting

**Docker not found:**
```bash
# Install Docker Desktop for Mac from:
# https://www.docker.com/products/docker-desktop
```

**Permission denied:**
```bash
chmod +x run-catalogue-docker.sh
```

**Image rebuild needed** (after code changes):
```bash
docker build -t fm-skin-builder:latest .
```

**View Docker logs:**
```bash
# The script shows all output by default
# No additional commands needed
```

## Why Docker?

On macOS, UnityPy's DXT1/DXT5 texture decoder causes segmentation faults due to platform-specific issues with the underlying C libraries. Running in Docker:

- ✅ Uses Linux where UnityPy works perfectly
- ✅ No segfaults or crashes
- ✅ Full texture extraction with thumbnails
- ✅ Clean isolation from macOS environment
- ✅ Results available on your Mac immediately

## Performance

- **First run**: 2-5 minutes (builds Docker image)
- **Subsequent runs**: Same speed as native (bundle processing time)
- **Bundle processing**: ~5-10 seconds per bundle depending on size

## Alternative: Native macOS (Limited)

If you don't want to use Docker, you can run natively on macOS, but:
- ❌ All DXT1/DXT5 textures will be skipped (no thumbnails)
- ✅ Metadata still extracted (names, dimensions, bundles)
- ⚠️ Most FM textures use DXT1/DXT5, so you'll miss most previews

```bash
# Native macOS (not recommended)
python -m fm_skin_builder.cli.main catalogue \
  --bundle test_bundles \
  --fm-version "2025.0.0" \
  --out build/catalogue
```
