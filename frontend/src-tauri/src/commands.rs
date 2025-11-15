use rfd::FileDialog;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tauri::{AppHandle, Manager};

#[derive(Serialize, Deserialize)]
pub struct UpdateMetadata {
    pub version: String,
    pub pub_date: String,
    pub platforms: HashMap<String, PlatformInfo>,
    pub notes: String,
}

#[derive(Serialize, Deserialize)]
pub struct PlatformInfo {
    pub url: Option<String>,
    pub signature: Option<String>,
    pub installers: Vec<InstallerInfo>,
}

#[derive(Serialize, Deserialize)]
pub struct InstallerInfo {
    pub url: String,
    pub format: String,
    pub size: u64,
}

#[tauri::command]
pub async fn download_and_install_update(
    metadata: UpdateMetadata,
    _channel: String,
) -> Result<(), String> {
    use std::process::Command;

    // Determine the current platform
    let platform = if cfg!(target_os = "macos") {
        if cfg!(target_arch = "aarch64") {
            "darwin-aarch64"
        } else {
            "darwin-x86_64"
        }
    } else if cfg!(target_os = "windows") {
        "windows-x86_64"
    } else if cfg!(target_os = "linux") {
        "linux-x86_64"
    } else {
        return Err("Unsupported platform".to_string());
    };

    // Get the platform-specific info
    let platform_info = metadata
        .platforms
        .get(platform)
        .ok_or_else(|| format!("No update available for platform: {}", platform))?;

    // Get the first installer (prefer MSI for Windows, DMG for macOS, AppImage for Linux)
    let installer = platform_info
        .installers
        .iter()
        .find(|installer| match platform {
            "windows-x86_64" => installer.format == "msi",
            "darwin-aarch64" | "darwin-x86_64" => installer.format == "dmg",
            "linux-x86_64" => installer.format == "AppImage" || installer.format == "deb",
            _ => false,
        })
        .or_else(|| platform_info.installers.first())
        .ok_or_else(|| "No suitable installer found".to_string())?;

    let installer_url = &installer.url;
    let installer_format = &installer.format;

    println!("Downloading update from: {}", installer_url);
    println!("Installer format: {}", installer_format);

    // Download the installer
    let response = reqwest::get(installer_url)
        .await
        .map_err(|e| format!("Failed to download update: {}", e))?;

    if !response.status().is_success() {
        return Err(format!(
            "Download failed with status: {}",
            response.status()
        ));
    }

    let bytes = response
        .bytes()
        .await
        .map_err(|e| format!("Failed to read download: {}", e))?;

    // Save to a temporary location
    let temp_dir = std::env::temp_dir();
    let installer_filename = format!(
        "fm-skin-builder-update-{}.{}",
        metadata.version, installer_format
    );
    let installer_path = temp_dir.join(installer_filename);

    std::fs::write(&installer_path, &bytes)
        .map_err(|e| format!("Failed to save installer: {}", e))?;

    println!("Update downloaded to: {:?}", installer_path);

    // Make executable on Unix systems
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mut perms = std::fs::metadata(&installer_path)
            .map_err(|e| format!("Failed to get file permissions: {}", e))?
            .permissions();
        perms.set_mode(0o755);
        std::fs::set_permissions(&installer_path, perms)
            .map_err(|e| format!("Failed to set executable permissions: {}", e))?;
    }

    // Run the installer based on format
    println!("Running installer...");

    let install_result = match installer_format.as_str() {
        "msi" => {
            // Windows MSI installer
            Command::new("msiexec")
                .args([
                    "/i",
                    &installer_path.to_string_lossy(),
                    "/quiet",
                    "/norestart",
                ])
                .status()
                .map_err(|e| format!("Failed to run MSI installer: {}", e))
        }
        "dmg" => {
            // macOS DMG installer
            install_from_dmg(&installer_path)
        }
        "AppImage" => {
            // Linux AppImage - just make it executable and run
            Command::new(&installer_path)
                .status()
                .map_err(|e| format!("Failed to run AppImage: {}", e))
        }
        "deb" => {
            // Linux DEB package
            Command::new("sudo")
                .args(["dpkg", "-i", &installer_path.to_string_lossy()])
                .status()
                .map_err(|e| format!("Failed to install DEB package: {}", e))
        }
        _ => {
            return Err(format!(
                "Unsupported installer format: {}",
                installer_format
            ));
        }
    };

    match install_result {
        Ok(status) if status.success() => {
            println!("Update installed successfully");
            Ok(())
        }
        Ok(status) => Err(format!(
            "Installer exited with code: {}",
            status.code().unwrap_or(-1)
        )),
        Err(e) => Err(format!("Failed to run installer: {}", e)),
    }
}

fn install_from_dmg(dmg_path: &std::path::Path) -> Result<std::process::ExitStatus, String> {
    use std::process::Command;

    // Create a temporary mount point
    let mount_point = std::env::temp_dir().join("fm-skin-builder-mount");
    if mount_point.exists() {
        std::fs::remove_dir_all(&mount_point)
            .map_err(|e| format!("Failed to clean mount point: {}", e))?;
    }
    std::fs::create_dir_all(&mount_point)
        .map_err(|e| format!("Failed to create mount point: {}", e))?;

    // Mount the DMG
    let mount_result = Command::new("hdiutil")
        .args([
            "attach",
            &dmg_path.to_string_lossy(),
            "-mountpoint",
            &mount_point.to_string_lossy(),
            "-nobrowse",
        ])
        .status()
        .map_err(|e| format!("Failed to mount DMG: {}", e))?;

    if !mount_result.success() {
        return Err("Failed to mount DMG".to_string());
    }

    // Find the .app bundle in the mounted volume
    let app_entries = std::fs::read_dir(&mount_point)
        .map_err(|e| format!("Failed to read mount point: {}", e))?
        .filter_map(|entry| entry.ok())
        .filter(|entry| entry.path().extension().and_then(|ext| ext.to_str()) == Some("app"))
        .collect::<Vec<_>>();

    if app_entries.is_empty() {
        // Try to unmount first
        let _ = Command::new("hdiutil")
            .args(["detach", &mount_point.to_string_lossy()])
            .status();
        return Err("No .app bundle found in DMG".to_string());
    }

    let app_path = app_entries[0].path();
    let app_name = app_path
        .file_name()
        .and_then(|n| n.to_str())
        .ok_or_else(|| "Invalid app name".to_string())?;

    // Copy to Applications folder
    let applications_dir = std::path::PathBuf::from("/Applications");
    let target_path = applications_dir.join(app_name);

    // Remove existing app if it exists
    if target_path.exists() {
        std::fs::remove_dir_all(&target_path)
            .map_err(|e| format!("Failed to remove existing app: {}", e))?;
    }

    // Copy the new app
    copy_dir_recursive(&app_path, &target_path)
        .map_err(|e| format!("Failed to copy app: {}", e))?;

    // Unmount the DMG
    let unmount_result = Command::new("hdiutil")
        .args(["detach", &mount_point.to_string_lossy()])
        .status();

    // Clean up mount point
    let _ = std::fs::remove_dir_all(&mount_point);

    match unmount_result {
        Ok(status) if status.success() => Ok(std::process::ExitStatus::default()),
        _ => Err("Failed to unmount DMG".to_string()),
    }
}

fn copy_dir_recursive(src: &std::path::Path, dst: &std::path::Path) -> Result<(), String> {
    if src.is_dir() {
        std::fs::create_dir_all(dst).map_err(|e| format!("Failed to create directory: {}", e))?;

        for entry in
            std::fs::read_dir(src).map_err(|e| format!("Failed to read directory: {}", e))?
        {
            let entry = entry.map_err(|e| format!("Failed to read entry: {}", e))?;
            let src_path = entry.path();
            let dst_path = dst.join(entry.file_name());

            if src_path.is_dir() {
                copy_dir_recursive(&src_path, &dst_path)?;
            } else {
                std::fs::copy(&src_path, &dst_path)
                    .map_err(|e| format!("Failed to copy file: {}", e))?;
            }
        }
    } else {
        std::fs::copy(src, dst).map_err(|e| format!("Failed to copy file: {}", e))?;
    }

    Ok(())
}

#[tauri::command]
pub fn select_folder(dialog_title: Option<String>, initial_path: Option<String>) -> Option<String> {
    let mut dialog = FileDialog::new();

    if let Some(title) = dialog_title {
        dialog = dialog.set_title(&title);
    }

    if let Some(path) = initial_path {
        if !path.trim().is_empty() {
            dialog = dialog.set_directory(path);
        }
    }

    dialog
        .pick_folder()
        .map(|folder| folder.to_string_lossy().to_string())
}

#[tauri::command]
pub fn get_default_skins_dir(app_handle: AppHandle) -> Result<String, String> {
    let document_dir = app_handle
        .path()
        .document_dir()
        .map_err(|e| format!("Failed to get documents directory: {}", e))?;

    let skins_dir = document_dir.join("FM Skin Builder");
    Ok(skins_dir.to_string_lossy().to_string())
}

#[tauri::command]
pub fn ensure_skins_dir(app_handle: AppHandle) -> Result<String, String> {
    let document_dir = app_handle
        .path()
        .document_dir()
        .map_err(|e| format!("Failed to get documents directory: {}", e))?;

    let skins_dir = document_dir.join("FM Skin Builder");

    if !skins_dir.exists() {
        std::fs::create_dir_all(&skins_dir)
            .map_err(|e| format!("Failed to create skins directory: {}", e))?;
    }

    Ok(skins_dir.to_string_lossy().to_string())
}

#[tauri::command]
pub fn get_cache_dir(app_handle: AppHandle) -> Result<String, String> {
    let cache_dir = app_handle
        .path()
        .app_cache_dir()
        .map_err(|e| format!("Failed to get cache directory: {}", e))?;

    Ok(cache_dir.to_string_lossy().to_string())
}
