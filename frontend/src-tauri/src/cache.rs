use std::fs;
use tauri::{AppHandle, Manager};
use tauri_plugin_shell::ShellExt;

/// Recursively calculate the size of a directory in bytes
/// Excludes the WebView2 folder (EBWebView) on Windows
fn calculate_dir_size(path: &std::path::Path) -> Result<u64, std::io::Error> {
    let mut total_size = 0u64;

    if path.is_dir() {
        for entry in fs::read_dir(path)? {
            let entry = entry?;
            let entry_path = entry.path();

            // Skip WebView2 folder on Windows
            if let Some(file_name) = entry_path.file_name() {
                if file_name == "EBWebView" {
                    println!("[DEBUG] Skipping EBWebView folder in size calculation");
                    continue;
                }
            }

            if entry_path.is_dir() {
                total_size += calculate_dir_size(&entry_path)?;
            } else {
                total_size += entry.metadata()?.len();
            }
        }
    }

    Ok(total_size)
}

/// Get the size of the cache directory in bytes
#[tauri::command]
pub fn get_cache_size(app_handle: AppHandle) -> Result<u64, String> {
    let cache_dir = app_handle
        .path()
        .app_cache_dir()
        .map_err(|e| format!("Failed to get cache directory: {}", e))?;

    println!("[DEBUG] Cache directory path: {:?}", cache_dir);

    if !cache_dir.exists() {
        println!("[DEBUG] Cache directory does not exist");
        return Ok(0);
    }

    let size = calculate_dir_size(&cache_dir)
        .map_err(|e| format!("Failed to calculate cache size: {}", e))?;
    println!(
        "[DEBUG] Calculated cache size: {} bytes ({:.2} MB)",
        size,
        size as f64 / 1_048_576.0
    );

    Ok(size)
}

/// Clear specific cache folders, excluding WebView2 runtime folder
/// Only deletes: cache/, bundles/, skins/, temp/
/// Never deletes: EBWebView/ (WebView2 runtime - locked on Windows)
#[tauri::command]
pub fn clear_cache(app_handle: AppHandle) -> Result<String, String> {
    let cache_dir = app_handle
        .path()
        .app_cache_dir()
        .map_err(|e| format!("Failed to get cache directory: {}", e))?;

    println!("[DEBUG] clear_cache called for: {:?}", cache_dir);

    if !cache_dir.exists() {
        println!("[DEBUG] Cache directory does not exist");
        return Ok("Cache directory is already empty".to_string());
    }

    // Get size before clearing (excludes EBWebView)
    let size_before = calculate_dir_size(&cache_dir)
        .map_err(|e| format!("Failed to calculate cache size: {}", e))?;

    println!(
        "[DEBUG] Size before clearing: {} bytes ({:.2} MB)",
        size_before,
        size_before as f64 / 1_048_576.0
    );

    // Whitelist of directories to delete
    // These are safe to delete and won't interfere with WebView2
    let folders_to_clear = ["cache", "bundles", "skins", "temp"];

    let mut items_deleted = 0;
    let mut total_errors = 0;

    // Only delete whitelisted folders
    for folder_name in &folders_to_clear {
        let folder_path = cache_dir.join(folder_name);

        if folder_path.exists() {
            println!("[DEBUG] Attempting to remove: {:?}", folder_path);

            match fs::remove_dir_all(&folder_path) {
                Ok(_) => {
                    println!("[DEBUG] Successfully removed: {:?}", folder_path);
                    items_deleted += 1;
                }
                Err(e) => {
                    // Log error but don't fail - this makes the operation more resilient
                    println!(
                        "[WARNING] Failed to remove {:?}: {} (continuing anyway)",
                        folder_path, e
                    );
                    total_errors += 1;
                }
            }
        } else {
            println!(
                "[DEBUG] Folder does not exist (skipping): {:?}",
                folder_path
            );
        }
    }

    println!(
        "[DEBUG] Deleted {} items ({} errors encountered)",
        items_deleted, total_errors
    );

    // Calculate actual size cleared
    let size_after = calculate_dir_size(&cache_dir).unwrap_or(0);
    let size_cleared = size_before.saturating_sub(size_after);
    let mb_cleared = size_cleared as f64 / 1_048_576.0;

    // Build result message
    let result_message = if total_errors > 0 {
        format!(
            "Cleared {:.2} MB from cache ({} folders cleared, {} errors)",
            mb_cleared, items_deleted, total_errors
        )
    } else if items_deleted == 0 {
        "Cache folders are already empty".to_string()
    } else {
        format!(
            "Cleared {:.2} MB from cache ({} folders)",
            mb_cleared, items_deleted
        )
    };

    Ok(result_message)
}

/// Open the cache directory in the system file browser
#[tauri::command]
pub async fn open_cache_dir(app_handle: AppHandle) -> Result<(), String> {
    let cache_dir = app_handle
        .path()
        .app_cache_dir()
        .map_err(|e| format!("Failed to get cache directory: {}", e))?;

    // Create cache directory if it doesn't exist
    if !cache_dir.exists() {
        fs::create_dir_all(&cache_dir)
            .map_err(|e| format!("Failed to create cache directory: {}", e))?;
    }

    // Use tauri-plugin-shell to open the directory
    let shell = app_handle.shell();

    #[cfg(target_os = "macos")]
    {
        shell
            .command("open")
            .arg(cache_dir.to_string_lossy().to_string())
            .spawn()
            .map_err(|e| format!("Failed to open cache directory: {}", e))?;
    }

    #[cfg(target_os = "windows")]
    {
        shell
            .command("explorer")
            .arg(cache_dir.to_string_lossy().to_string())
            .spawn()
            .map_err(|e| format!("Failed to open cache directory: {}", e))?;
    }

    #[cfg(target_os = "linux")]
    {
        shell
            .command("xdg-open")
            .arg(cache_dir.to_string_lossy().to_string())
            .spawn()
            .map_err(|e| format!("Failed to open cache directory: {}", e))?;
    }

    Ok(())
}

/// Get app version from Cargo.toml
#[tauri::command]
pub fn get_app_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

/// Get platform information
#[tauri::command]
pub fn get_platform_info() -> serde_json::Value {
    serde_json::json!({
        "os": std::env::consts::OS,
        "arch": std::env::consts::ARCH,
        "family": std::env::consts::FAMILY,
    })
}
