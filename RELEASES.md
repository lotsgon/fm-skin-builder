# Release Strategy

This document describes the release process for FM Skin Builder, including versioning, beta releases, and auto-updates.

## Release Channels

FM Skin Builder supports two release channels:

### Stable Releases
- Tagged with version numbers (e.g., `v0.2.0`)
- Thoroughly tested and ready for production use
- Auto-updates enabled by default for all users
- Published to GitHub Releases and R2 storage

### Beta Releases
- Auto-generated from `beta` branch commits
- Versioned as `X.Y.Z-beta.{commit-sha}` (e.g., `0.2.0-beta.79f77d5`)
- **Opt-in only** - users must explicitly enable beta updates
- Used for testing new features before stable release
- Users can disable beta channel at any time to revert to stable

## Versioning

Versions follow [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH** (e.g., `0.2.0`)
- Calculated automatically from conventional commit messages

### Version Bump Rules

The `scripts/get_next_version.py` script analyzes commit messages to determine the next version:

- **BREAKING CHANGE** or `!` suffix → Minor bump (for 0.x versions) or Major bump (for 1.x+)
  - Example: `feat!: redesign UI` → `0.1.0` → `0.2.0`
- **feat:** → Minor version bump
  - Example: `feat: add texture swap` → `0.1.0` → `0.2.0`
- **fix:**, **perf:**, **refactor:** → Patch version bump
  - Example: `fix: resolve crash on startup` → `0.1.0` → `0.1.1`
- **docs:**, **chore:**, **style:**, **test:** → No version bump

## Release Workflows

### Beta Releases (Automatic)

Beta releases are automatically created when pushing to the `beta` branch:

1. Push to `beta` branch
2. GitHub Actions workflow triggers:
   - Runs all tests (Python + frontend)
   - Calculates next beta version using conventional commits
   - Updates version in all config files
   - Builds for all platforms (Linux, macOS, Windows)
   - Uploads to R2 bucket at `beta/` path
   - Creates GitHub pre-release with artifacts
3. Version format: `X.Y.Z-beta.{short-commit-sha}`
   - Example: `0.2.0-beta.79f77d5`

**Workflow File:** `.github/workflows/build-app.yml` → `publish-beta` job

### Stable Releases (Manual)

Stable releases are created by tagging a commit:

1. Ensure all changes are committed to `main` branch
2. Create and push a version tag:
   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```
3. GitHub Actions workflow triggers:
   - Runs all tests
   - Extracts version from tag name
   - Updates version in all config files
   - Builds for all platforms
   - Uploads to R2 bucket at `releases/` path
   - Creates GitHub release with artifacts

**Workflow File:** `.github/workflows/build-app.yml` → `publish` job

## Auto-Update System

### Current Status: Disabled

Auto-updates are currently **disabled** while we finalize deployment strategy.

When enabled, the system will work as follows:

### Planned Behavior

#### Stable Channel (Default)
- Users receive updates only from stable releases
- Updates checked on app startup
- Update notifications appear in-app
- Users can choose to install immediately or defer

#### Beta Channel (Opt-in)
- Users must explicitly enable beta updates in settings
- Receive both beta and stable releases
- Beta builds marked with "BETA" badge in version number
- Can disable beta channel to revert to stable-only updates

### Configuration Files

The auto-update system requires:

1. **Updater Configuration** (`frontend/src-tauri/tauri.conf.json`):
   ```json
   "updater": {
     "active": true,
     "endpoints": [
       "https://your-r2-domain.com/releases/latest.json"
     ],
     "pubkey": "YOUR_PUBLIC_KEY_HERE"
   }
   ```

2. **Signing Keys** (GitHub Secrets):
   - `TAURI_SIGNING_PRIVATE_KEY` - Private key for signing updates
   - `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` - Password for private key

3. **Update Manifests**:
   - `latest.json` - Stable channel manifest
   - `beta/latest.json` - Beta channel manifest

### Enabling Auto-Updates

To enable auto-updates in the future:

1. **Generate signing keys:**
   ```bash
   cd frontend
   npm run tauri signer generate
   ```

2. **Set GitHub secrets:**
   - Add private key and password to repository secrets
   - Keys are used to sign update artifacts

3. **Update tauri.conf.json:**
   - Uncomment updater configuration
   - Add public key from step 1
   - Set endpoint to R2 bucket URL

4. **Configure R2 bucket:**
   - Make releases path publicly readable
   - Or keep private and use custom domain with public access

5. **Deploy update manifests:**
   - Scripts automatically generate `latest.json` files
   - R2 upload includes manifest updates

## Build Artifacts

Each build generates the following artifacts:

### User Installers
- **Linux**: `.AppImage`, `.deb`
- **macOS**: `.dmg` (Intel and ARM64)
- **Windows**: `.exe` (NSIS), `.msi`

### Auto-Update Files (when enabled)
- **Linux**: `.AppImage.tar.gz`, `.AppImage.tar.gz.sig`
- **macOS**: `.app.tar.gz`, `.app.tar.gz.sig`
- **Windows**: `.msi.zip`, `.msi.zip.sig`

### Version Display

The app displays its version in the bottom-left corner:
- Stable: `v0.2.0`
- Beta: `v0.2.0-beta.79f77d5`
- Dev: `vdev` (when running locally)

## Testing Releases

### Testing Beta Releases

1. Download beta build from GitHub Releases
2. Install on target platform
3. Verify version shows `X.Y.Z-beta.{sha}` in bottom-left
4. Test new features thoroughly
5. Report issues to GitHub

### Promoting Beta to Stable

When a beta is ready for stable release:

1. Merge `beta` branch to `main`
2. Create stable release tag on `main`:
   ```bash
   git checkout main
   git merge beta
   git tag v0.2.0
   git push origin main --tags
   ```
3. Stable release workflow builds and publishes

## R2 Configuration

### Required GitHub Variables

The following GitHub repository variables must be set for R2 uploads:

**Secrets:**
- `R2_ACCOUNT_ID` - Your Cloudflare R2 account ID
- `R2_ACCESS_KEY` - R2 access key ID
- `R2_SECRET_ACCESS_KEY` - R2 secret access key
- `TAURI_SIGNING_PRIVATE_KEY` - Private key for signing updates (when auto-update enabled)
- `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` - Password for private key (when auto-update enabled)

**Variables:**
- `R2_RELEASES_BUCKET` - Name of your R2 bucket (e.g., `fm-skin-builder-releases`)

### Setting Up R2

1. Create an R2 bucket in Cloudflare
2. Configure public access for the `/releases` and `/beta` paths (or entire bucket)
3. Set up a custom domain (e.g., `releases.fm-skin-builder.com`) pointing to your bucket
4. Update the hardcoded domain in `scripts/update_latest_metadata.py` if using a different domain
5. Add credentials to GitHub repository secrets/variables
6. Ensure bucket allows public reads for the release paths

## R2 Storage Structure

Releases are stored in R2 with this structure:

```
releases/
├── 0.2.0/
│   ├── FM Skin Builder_0.2.0_aarch64.dmg              # macOS ARM installer
│   ├── FM Skin Builder_0.2.0_aarch64.app.tar.gz      # macOS ARM updater archive
│   ├── FM Skin Builder_0.2.0_aarch64.app.tar.gz.sig  # macOS ARM updater signature
│   ├── FM Skin Builder_0.2.0_x64.dmg                 # macOS Intel installer
│   ├── FM Skin Builder_0.2.0_x64.app.tar.gz          # macOS Intel updater archive
│   ├── FM Skin Builder_0.2.0_x64.app.tar.gz.sig      # macOS Intel updater signature
│   ├── FM Skin Builder_0.2.0_x64-setup.exe           # Windows NSIS installer
│   ├── FM Skin Builder_0.2.0_x64_en-US.msi           # Windows MSI installer
│   ├── FM Skin Builder_0.2.0_x64_en-US.msi.zip       # Windows updater archive
│   ├── FM Skin Builder_0.2.0_x64_en-US.msi.zip.sig   # Windows updater signature
│   ├── FM Skin Builder_0.2.0_amd64.AppImage          # Linux AppImage
│   ├── FM Skin Builder_0.2.0_amd64.AppImage.tar.gz   # Linux updater archive
│   ├── FM Skin Builder_0.2.0_amd64.AppImage.tar.gz.sig # Linux updater signature
│   └── FM Skin Builder_0.2.0_amd64.deb               # Linux Debian package
├── latest.json          # Stable channel manifest (for auto-updater)
├── metadata/
│   └── 0.2.0.json      # Version-specific metadata
└── beta/
    ├── 0.2.0-beta.79f77d5/
    │   ├── ... (same structure as stable)
    ├── latest.json      # Beta channel manifest (for auto-updater)
    └── metadata/
        └── 0.2.0-beta.79f77d5.json
```

## Troubleshooting

### Build Version Stuck at 0.1.0

The version is hardcoded in three files and gets updated by the workflow:
- `frontend/package.json`
- `frontend/src-tauri/tauri.conf.json`
- `frontend/src-tauri/Cargo.toml`

The workflow automatically updates these before building. If building locally, manually update all three files.

### 404 Error During Release Upload

This was caused by nested artifact directories. Fixed by adding a "flatten artifacts" step that moves all build files to the root artifacts directory before upload.

### Missing Auto-Update Files

The updater artifacts (.sig, .tar.gz, .zip) are only generated when `createUpdaterArtifacts: "v1Compatible"` is set in the bundle configuration AND the signing keys are configured. These files are currently being generated but won't be functional until the updater is enabled.

### R2 Upload Issues

**Scripts Not Finding Files:**
The workflow flattens artifacts before uploading. Both `upload_release_to_r2.py` and `update_latest_metadata.py` use `os.walk()` to find files recursively, so they work with both flat and nested structures.

**latest.json Structure:**
The `latest.json` file serves dual purposes:
1. **Tauri Updater**: Uses the `url` and `signature` fields per platform for auto-updates
2. **Website Downloads**: Uses the `installers` array per platform to show download options

Each platform entry contains:
- `url` + `signature` - Updater archive (.tar.gz or .zip) for Tauri
- `installers[]` - Array of user installers (.dmg, .exe, .AppImage, .deb) for website

Example structure:
```json
{
  "darwin-aarch64": {
    "url": "https://releases.fm-skin-builder.com/releases/0.2.0/FM_Skin_Builder_0.2.0_aarch64.app.tar.gz",
    "signature": "dW50cnVzdGVkIGNvbW1lbnQ...",
    "installers": [
      {
        "url": "https://releases.fm-skin-builder.com/releases/0.2.0/FM Skin Builder_0.2.0_aarch64.dmg",
        "format": "dmg",
        "size": 50123456
      }
    ]
  }
}
```

## References

- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Tauri Updater Documentation](https://v2.tauri.app/plugin/updater/)
- [GitHub Actions Workflows](.github/workflows/)
