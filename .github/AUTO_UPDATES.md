# Auto-Update System

This document explains the auto-update metadata system used for:

- Website download links (latest stable/beta)
- Tauri auto-updater (checking for updates)

## Metadata Files in R2

### `latest.json` (Root of bucket)

This file contains information about the latest stable and beta releases:

```json
{
  "stable": {
    "version": "0.2.0",
    "date": "2025-01-15T10:30:00Z",
    "platforms": {
      "linux-x86_64": [
        {
          "url": "https://release.fmskinbuilder.com/releases/0.2.0/fm-skin-builder-linux-x86_64.AppImage",
          "signature": "sha256_hash_here",
          "format": "AppImage",
          "size": 12345678
        },
        {
          "url": "https://release.fmskinbuilder.com/releases/0.2.0/fm-skin-builder-linux-x86_64.deb",
          "signature": "sha256_hash_here",
          "format": "deb",
          "size": 12345678
        }
      ],
      "windows-x86_64": [
        {
          "url": "https://release.fmskinbuilder.com/releases/0.2.0/fm-skin-builder-windows-x86_64.msi",
          "signature": "sha256_hash_here",
          "format": "msi",
          "size": 12345678
        }
      ],
      "darwin-aarch64": [
        {
          "url": "https://release.fmskinbuilder.com/releases/0.2.0/fm-skin-builder-macos-arm64.dmg",
          "signature": "sha256_hash_here",
          "format": "dmg",
          "size": 12345678
        }
      ],
      "darwin-x86_64": [
        {
          "url": "https://release.fmskinbuilder.com/releases/0.2.0/fm-skin-builder-macos-intel.dmg",
          "signature": "sha256_hash_here",
          "format": "dmg",
          "size": 12345678
        }
      ]
    },
    "notes": "Release notes here"
  },
  "beta": {
    "version": "0.3.0-beta.abc123",
    "date": "2025-01-16T14:00:00Z",
    "platforms": {
      // Same structure as stable
    },
    "notes": ""
  },
  "last_updated": "2025-01-16T14:00:00Z"
}
```

### `metadata/{version}.json` (Version-specific)

Each release also has version-specific metadata:

```json
{
  "version": "0.2.0",
  "pub_date": "2025-01-15T10:30:00Z",
  "platforms": {
    // Same platforms structure as latest.json
  },
  "notes": "Release notes"
}
```

## Using in Website

### Fetch Latest Stable Release

```typescript
const response = await fetch("https://release.fmskinbuilder.com/latest.json");
const data = await response.json();

if (data.stable) {
  const version = data.stable.version;
  const platforms = data.stable.platforms;

  // Get download URLs for each platform
  const linuxAppImage = platforms["linux-x86_64"][0].url;
  const windowsMsi = platforms["windows-x86_64"][0].url;
  const macARM = platforms["darwin-aarch64"][0].url;
  const macIntel = platforms["darwin-x86_64"][0].url;
}
```

### Fetch Latest Beta Release

```typescript
const response = await fetch("https://release.fmskinbuilder.com/latest.json");
const data = await response.json();

if (data.beta) {
  const version = data.beta.version;
  const platforms = data.beta.platforms;
  // Use platforms to get download URLs
}
```

### Download Page Example

```html
<div class="downloads">
  <h2>Latest Release: <span id="version"></span></h2>

  <div class="platform">
    <h3>Windows</h3>
    <a id="windows-download" href="#">Download MSI</a>
    <p class="checksum" id="windows-checksum"></p>
  </div>

  <div class="platform">
    <h3>macOS (Apple Silicon)</h3>
    <a id="mac-arm-download" href="#">Download DMG</a>
    <p class="checksum" id="mac-arm-checksum"></p>
  </div>

  <div class="platform">
    <h3>macOS (Intel)</h3>
    <a id="mac-intel-download" href="#">Download DMG</a>
    <p class="checksum" id="mac-intel-checksum"></p>
  </div>

  <div class="platform">
    <h3>Linux</h3>
    <a id="linux-appimage-download" href="#">Download AppImage</a>
    <a id="linux-deb-download" href="#">Download DEB</a>
    <p class="checksum" id="linux-checksum"></p>
  </div>
</div>

<script>
  async function loadDownloads() {
    const response = await fetch(
      "https://release.fmskinbuilder.com/latest.json"
    );
    const data = await response.json();

    if (!data.stable) return;

    const { version, platforms } = data.stable;

    // Update version
    document.getElementById("version").textContent = `v${version}`;

    // Update Windows
    const windowsDownload = platforms["windows-x86_64"]?.[0];
    if (windowsDownload) {
      document.getElementById("windows-download").href = windowsDownload.url;
      document.getElementById(
        "windows-checksum"
      ).textContent = `SHA256: ${windowsDownload.signature.substring(
        0,
        16
      )}...`;
    }

    // Update macOS ARM
    const macArmDownload = platforms["darwin-aarch64"]?.[0];
    if (macArmDownload) {
      document.getElementById("mac-arm-download").href = macArmDownload.url;
      document.getElementById(
        "mac-arm-checksum"
      ).textContent = `SHA256: ${macArmDownload.signature.substring(0, 16)}...`;
    }

    // Update macOS Intel
    const macIntelDownload = platforms["darwin-x86_64"]?.[0];
    if (macIntelDownload) {
      document.getElementById("mac-intel-download").href = macIntelDownload.url;
      document.getElementById(
        "mac-intel-checksum"
      ).textContent = `SHA256: ${macIntelDownload.signature.substring(
        0,
        16
      )}...`;
    }

    // Update Linux
    const linuxAppImage = platforms["linux-x86_64"]?.find(
      (p) => p.format === "AppImage"
    );
    const linuxDeb = platforms["linux-x86_64"]?.find((p) => p.format === "deb");

    if (linuxAppImage) {
      document.getElementById("linux-appimage-download").href =
        linuxAppImage.url;
    }
    if (linuxDeb) {
      document.getElementById("linux-deb-download").href = linuxDeb.url;
    }
    if (linuxAppImage) {
      document.getElementById(
        "linux-checksum"
      ).textContent = `SHA256: ${linuxAppImage.signature.substring(0, 16)}...`;
    }
  }

  loadDownloads();
</script>
```

## Using in Tauri Auto-Updater

### tauri.conf.json Configuration

```json
{
  "tauri": {
    "updater": {
      "active": true,
      "endpoints": ["https://release.fmskinbuilder.com/latest.json"],
      "dialog": true,
      "pubkey": "YOUR_PUBLIC_KEY_HERE"
    }
  }
}
```

### Check for Updates (Manual)

```typescript
import { check } from "@tauri-apps/plugin-updater";
import { ask, message } from "@tauri-apps/plugin-dialog";
import { relaunch } from "@tauri-apps/plugin-process";

async function checkForUpdates() {
  const update = await check();

  if (update?.available) {
    const yes = await ask(
      `Update to ${update.version} is available!\n\nRelease notes: ${update.body}`,
      {
        title: "Update Available",
        kind: "info",
        okLabel: "Update",
        cancelLabel: "Later",
      }
    );

    if (yes) {
      await update.downloadAndInstall();
      await relaunch();
    }
  } else {
    await message("You are on the latest version!", {
      title: "No Updates",
      kind: "info",
    });
  }
}
```

### Auto-Check on Startup

```typescript
import { check } from "@tauri-apps/plugin-updater";

async function checkForUpdatesOnStartup() {
  try {
    const update = await check();
    if (update?.available) {
      // Show notification or prompt user
      console.log(`Update available: ${update.version}`);
    }
  } catch (error) {
    console.error("Update check failed:", error);
  }
}

// Call on app startup
window.addEventListener("DOMContentLoaded", () => {
  checkForUpdatesOnStartup();
});
```

## Beta Channel Support

### Allow Users to Switch Channels

```typescript
// Store user preference
const channel = localStorage.getItem("update-channel") || "stable";

async function checkForUpdates(useChannel: "stable" | "beta" = channel) {
  const response = await fetch("https://release.fmskinbuilder.com/latest.json");
  const data = await response.json();

  const releaseInfo = data[useChannel];
  if (!releaseInfo) return null;

  return releaseInfo;
}

// UI for switching channels
function switchChannel(channel: "stable" | "beta") {
  localStorage.setItem("update-channel", channel);
  checkForUpdates(channel);
}
```

## CDN Caching

The `latest.json` file has a 5-minute cache:

```
Cache-Control: max-age=300
```

This means:

- Users won't hammer R2 on every check
- Updates propagate within 5 minutes
- Cloudflare CDN can cache it globally

## Security

### Signature Verification

Each file includes a SHA256 hash:

```json
"signature": "sha256_hash_here"
```

Users can verify downloads:

```bash
# Linux/macOS
sha256sum fm-skin-builder-linux-x86_64.AppImage

# Windows (PowerShell)
Get-FileHash fm-skin-builder-windows-x86_64.msi -Algorithm SHA256
```

### Tauri Signing

For Tauri auto-updates, builds are also signed with a private key configured in GitHub Secrets (`TAURI_SIGNING_PRIVATE_KEY`).

## Testing

### Test Metadata Locally

```bash
# Generate metadata for a local build
python3 scripts/update_latest_metadata.py \
  --artifacts-dir artifacts \
  --version 0.2.0-test \
  --bucket your-test-bucket \
  --beta

# Check the output
aws s3 cp s3://your-test-bucket/latest.json - | jq
```

### Mock the Endpoint

For local development, serve a mock `latest.json`:

```json
{
  "stable": {
    "version": "1.0.0",
    "date": "2025-01-15T10:00:00Z",
    "platforms": {
      "windows-x86_64": [
        {
          "url": "http://localhost:3000/test.msi",
          "signature": "test",
          "format": "msi",
          "size": 1000
        }
      ]
    }
  }
}
```

## Monitoring

Check metadata is updating:

```bash
# View current metadata
curl https://release.fmskinbuilder.com/latest.json | jq

# Check last update time
curl https://release.fmskinbuilder.com/latest.json | jq .last_updated
```

## Troubleshooting

### Metadata not updating

- Check R2 credentials in GitHub Secrets
- Check GitHub Actions logs for errors
- Verify bucket name matches

### Old version showing

- Wait 5 minutes (cache TTL)
- Check that build completed successfully
- Verify metadata script ran in workflow

### Downloads not working

- Verify R2 bucket is publicly accessible
- Check CORS configuration on R2
- Verify URLs in metadata are correct
