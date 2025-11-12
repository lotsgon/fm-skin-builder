use std::fs;
use tauri::{AppHandle, Manager};
use tauri_plugin_shell::ShellExt;

/// Recursively calculate the size of a directory in bytes
fn calculate_dir_size(path: &std::path::Path) -> Result<u64, std::io::Error> {
    let mut total_size = 0u64;

    if path.is_dir() {
        for entry in fs::read_dir(path)? {
            let entry = entry?;
            let entry_path = entry.path();

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

/// Clear all files in the cache directory
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

    // Get size before clearing
    let size_before = calculate_dir_size(&cache_dir)
        .map_err(|e| format!("Failed to calculate cache size: {}", e))?;

    println!(
        "[DEBUG] Size before clearing: {} bytes ({:.2} MB)",
        size_before,
        size_before as f64 / 1_048_576.0
    );

    // Remove all contents but keep the directory
    let mut items_deleted = 0;
    if let Ok(entries) = fs::read_dir(&cache_dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            println!("[DEBUG] Removing: {:?}", path);
            if path.is_dir() {
                fs::remove_dir_all(&path)
                    .map_err(|e| format!("Failed to remove directory {:?}: {}", path, e))?;
                items_deleted += 1;
            } else {
                fs::remove_file(&path)
                    .map_err(|e| format!("Failed to remove file {:?}: {}", path, e))?;
                items_deleted += 1;
            }
        }
    }

    println!("[DEBUG] Deleted {} items", items_deleted);

    let mb_cleared = size_before as f64 / 1_048_576.0;
    Ok(format!(
        "Cleared {:.2} MB from cache ({} items)",
        mb_cleared, items_deleted
    ))
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
