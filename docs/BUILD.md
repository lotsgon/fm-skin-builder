# Building FM Skin Builder

This document describes how to build FM Skin Builder for all platforms and set up automated builds with code signing.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start - Local Build](#quick-start---local-build)
- [Platform-Specific Builds](#platform-specific-builds)
- [Code Signing](#code-signing)
- [Automated Builds (GitHub Actions)](#automated-builds-github-actions)
- [Future: Auto-Updates with R2](#future-auto-updates-with-r2)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### All Platforms

- **Node.js** 18 or higher ([download](https://nodejs.org/))
- **Rust** latest stable ([install](https://rustup.rs/))
- **Python** 3.10 or higher (3.11+ recommended) ([download](https://www.python.org/downloads/))

### Platform-Specific Requirements

#### Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install -y \
  libwebkit2gtk-4.1-dev \
  libappindicator3-dev \
  librsvg2-dev \
  patchelf \
  libcairo2-dev \
  libgdk-pixbuf2.0-dev \
  libpango1.0-dev
```

#### macOS

Install Xcode Command Line Tools:

```bash
xcode-select --install
```

#### Windows

Install [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/) with the following workloads:
- "Desktop development with C++"
- Windows 10/11 SDK

## Quick Start - Local Build

The easiest way to build the application locally:

```bash
# Clone the repository
git clone https://github.com/yourusername/fm-skin-builder.git
cd fm-skin-builder

# Run the build script
./scripts/build_local.sh
```

This script will:
1. Set up the Python virtual environment
2. Build the Python backend with PyInstaller
3. Install frontend dependencies
4. Build the Tauri application bundle

Your build artifacts will be in `frontend/src-tauri/target/release/bundle/`:

- **Linux**: `appimage/*.AppImage` and `deb/*.deb`
- **macOS**: `dmg/*.dmg` and `macos/*.app`
- **Windows**: `nsis/*.exe` and `msi/*.msi`

## Platform-Specific Builds

### Manual Build Steps

If you want more control over the build process:

1. **Set up Python environment**:

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt pyinstaller
```

2. **Build the Python backend**:

```bash
./scripts/build_backend.sh
```

3. **Install frontend dependencies**:

```bash
cd frontend
npm install
```

4. **Build the Tauri app**:

```bash
# For the current platform
npm run tauri build

# For specific target (macOS only)
npm run tauri build -- --target aarch64-apple-darwin
```

### Cross-Platform Builds

Currently, cross-compilation is limited. Each platform should be built on its native OS:

- **Linux builds**: Build on Linux (Ubuntu 22.04 recommended)
- **Windows builds**: Build on Windows (Windows 11 recommended)
- **macOS Intel**: Build on macOS Intel or M1/M2 with Rosetta
- **macOS Apple Silicon**: Build on macOS M1/M2

The GitHub Actions workflow handles this automatically by using a build matrix.

## Code Signing

Code signing helps users trust your application and, on some platforms, is required for certain features.

### Windows Code Signing

#### Option 1: Self-Signed Certificate (Testing Only)

For local testing, generate a self-signed certificate:

```powershell
# Run in PowerShell as Administrator
.\scripts\setup_windows_signing.ps1
```

This will:
- Create a self-signed certificate
- Export it as a .pfx file
- Show you the thumbprint to add to `tauri.conf.json`

**Warning**: Self-signed certificates will show security warnings to users.

#### Option 2: Trusted Certificate Authority (Production)

For production releases, obtain a code signing certificate from a trusted CA:

1. Purchase a certificate from providers like:
   - [DigiCert](https://www.digecert.com/)
   - [Sectigo](https://www.sectigo.com/)
   - [SSL.com](https://www.ssl.com/)

2. Export the certificate as a .pfx file with a strong password

3. Update `frontend/src-tauri/tauri.conf.json`:

```json
{
  "bundle": {
    "windows": {
      "certificateThumbprint": "YOUR_CERTIFICATE_THUMBPRINT_HERE"
    }
  }
}
```

4. For GitHub Actions, add secrets (see below)

### macOS Code Signing

macOS code signing requires an Apple Developer account ($99/year):

1. Join the [Apple Developer Program](https://developer.apple.com/programs/)
2. Create certificates in Xcode or the Developer Portal
3. Configure Tauri to use your certificate

**Note**: Until you have a Developer account, macOS builds will be unsigned. Users will need to right-click and select "Open" to run the app.

### Tauri Update Signing (All Platforms)

For future auto-update functionality, generate signing keys:

```bash
./scripts/generate_tauri_keys.sh
```

This generates:
- A **private key** (keep secret, used to sign updates)
- A **public key** (embedded in the app, used to verify updates)

Store the private key and password securely (e.g., in GitHub Secrets for CI/CD).

## Automated Builds (GitHub Actions)

The project includes a comprehensive GitHub Actions workflow that builds for all platforms.

### Setting Up GitHub Actions

1. **Fork/clone the repository**

2. **Add GitHub Secrets** (Settings → Secrets and variables → Actions):

   **For Windows Code Signing** (optional):
   ```
   WINDOWS_CERTIFICATE: <base64-encoded .pfx file>
   WINDOWS_CERTIFICATE_PASSWORD: <certificate password>
   ```

   To encode the certificate:
   ```powershell
   [Convert]::ToBase64String([IO.File]::ReadAllBytes("path\to\cert.pfx"))
   ```

   **For Tauri Update Signing** (recommended):
   ```
   TAURI_SIGNING_PRIVATE_KEY: <private key from generate_tauri_keys.sh>
   TAURI_SIGNING_PRIVATE_KEY_PASSWORD: <password from generate_tauri_keys.sh>
   ```

3. **Trigger a build**:

   - Push to `main` branch
   - Create a pull request
   - Run workflow manually (Actions → Build Application → Run workflow)

### Workflow Overview

The build system uses **two separate workflows** for optimal performance:

#### CI Tests (`.github/workflows/ci.yml`)
Runs on every push and PR:
- **Python tests**: Runs pytest suite
- **Frontend tests**: Runs Vitest suite
- **Linting**: Ruff (Python), ESLint (TypeScript), cargo fmt/clippy (Rust)
- Fast feedback (~2-3 minutes)

#### Build Application (`.github/workflows/build-app.yml`)
Optimized multi-stage build process:

1. **Test Stage** (parallel):
   - Runs Python and frontend tests
   - Ensures code quality before building

2. **Backend Build Stage** (parallel, ~2-3 minutes per platform):
   - Builds Python backend with PyInstaller on each platform
   - Caches backend binaries as artifacts
   - Platforms:
     - ubuntu-latest (Linux)
     - macos-15-intel (macOS Intel)
     - windows-latest (Windows)

3. **Application Build Stage** (~5-7 minutes per platform):
   - Downloads pre-built backend for platform
   - Installs minimal dependencies (faster than before)
   - Builds frontend assets
   - Uses `tauri-apps/tauri-action` for optimized builds
   - Signs builds (if configured)
   - Creates native installers:
     - **Linux**: AppImage + .deb (ubuntu-latest)
     - **Windows**: NSIS installer + MSI (windows-latest, embedded WebView2)
     - **macOS**: Separate builds:
       - Intel x86_64 (macos-15-intel)
       - ARM64 (macos-latest)
       - Universal binary (macos-latest)

4. **Release Stage** (on version tags):
   - Automatically creates GitHub release
   - Uploads all platform artifacts
   - Generates release notes

**Supported macOS Versions**: 10.13+ through latest (including 15.6.1)

**Key Optimizations**:
- Backend built once per platform, reused for all builds
- Tests run in parallel, don't block builds
- Minimal Linux dependencies (only WebKit essentials)
- Embedded WebView2 on Windows (no runtime download)
- Universal macOS binaries for maximum compatibility
- Total build time: **~8-12 minutes** for all platforms

### Downloading Artifacts

After a successful build:

1. Go to Actions tab in GitHub
2. Click on the workflow run
3. Scroll down to "Artifacts"
4. Download the build for your platform

## Future: Auto-Updates with R2

The build system is designed with future auto-update functionality in mind:

### Planned Architecture

1. **Build artifacts uploaded to Cloudflare R2**:
   - Each release is uploaded with version number
   - JSON manifest tracks latest versions per platform

2. **Tauri auto-updater**:
   - Periodically checks R2 for updates
   - Downloads and verifies signature
   - Installs update seamlessly

3. **Direct downloads**:
   - Website links directly to R2 URLs
   - No GitHub dependency for distribution

### Preparation

To prepare for this:

1. **Generate signing keys** (if not already done):
   ```bash
   ./scripts/generate_tauri_keys.sh
   ```

2. **Store keys securely** in GitHub Secrets

3. **When ready**, update the workflow to:
   - Upload to R2 after building
   - Update version manifest
   - Configure Tauri updater in `tauri.conf.json`

## Troubleshooting

### Build Failures

**"Backend binary missing"**:
- Run `./scripts/build_backend.sh` manually
- Check that Python 3.10+ is installed
- Verify all Python dependencies are installed

**"failed to bundle project"**:
- Ensure all platform-specific dependencies are installed
- Check that Node modules are installed (`npm install`)
- Verify Rust is up to date (`rustup update`)

**PyInstaller errors**:
- Check Python version matches `pyproject.toml`
- Try rebuilding the virtual environment
- Look for missing Python packages

### Code Signing Issues

**Windows "certificate not found"**:
- Verify certificate is imported to `Cert:\CurrentUser\My`
- Check thumbprint matches `tauri.conf.json`
- Ensure certificate is valid and not expired

**macOS "app is damaged"**:
- This happens with unsigned apps
- Users should right-click and select "Open"
- Or sign the app with a Developer certificate

**Tauri signing key errors**:
- Ensure the private key is correctly formatted
- Verify the password is correct
- Check that the public key is in `tauri.conf.json`

### Platform-Specific Issues

**Linux: Missing libraries**:
```bash
ldd frontend/src-tauri/target/release/fm-skin-builder
# Install any missing libraries shown
```

**macOS: "cannot be opened because the developer cannot be verified"**:
```bash
xattr -cr /path/to/FM\ Skin\ Builder.app
```

**Windows: "VCRUNTIME140.dll not found"**:
- Install [Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)

## Additional Resources

- [Tauri Documentation](https://tauri.app/v1/guides/)
- [PyInstaller Documentation](https://pyinstaller.org/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Windows Code Signing Guide](https://docs.microsoft.com/en-us/windows/win32/seccrypto/using-signtool-to-sign-a-file)

## Getting Help

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Search [existing issues](https://github.com/yourusername/fm-skin-builder/issues)
3. Create a new issue with:
   - Your OS and version
   - Error messages (full output)
   - Steps to reproduce
