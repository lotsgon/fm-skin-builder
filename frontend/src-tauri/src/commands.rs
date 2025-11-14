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

    // For now, we'll use the first installer URL
    // In a full implementation, you'd want to handle different installer types
    let installer_url = platform_info
        .installers
        .first()
        .map(|installer| &installer.url)
        .ok_or_else(|| "No installer URL found".to_string())?;

    println!("Downloading update from: {}", installer_url);

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
    let installer_path = temp_dir.join(format!("fm-skin-builder-update-{}", metadata.version));

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

    // Run the installer
    println!("Running installer...");

    let install_result = if cfg!(target_os = "macos") {
        if installer_path.extension().and_then(|s| s.to_str()) == Some("dmg") {
            // For DMG files, we need to mount and copy the app
            // This is a simplified version - in production you'd want more robust handling
            Command::new("hdiutil")
                .args(["attach", installer_path.to_str().unwrap()])
                .status()
                .map_err(|e| format!("Failed to mount DMG: {}", e))?;

            // For now, just return success - proper DMG handling would be more complex
            Ok(std::process::ExitStatus::default())
        } else {
            // Assume it's an app bundle that can be run directly
            Command::new(&installer_path)
                .status()
                .map_err(|e| format!("Failed to run installer: {}", e))
        }
    } else if cfg!(target_os = "windows") {
        Command::new(&installer_path)
            .args(["/S"]) // Silent install
            .status()
            .map_err(|e| format!("Failed to run installer: {}", e))
    } else {
        // Linux - assume AppImage or similar
        Command::new(&installer_path)
            .status()
            .map_err(|e| format!("Failed to run installer: {}", e))
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
