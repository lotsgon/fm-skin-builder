#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use rfd::FileDialog;
use serde::{Deserialize, Serialize};
use std::{path::PathBuf, process::Command};
use tauri::{path::BaseDirectory, AppHandle, Manager};

#[derive(Serialize)]
struct CommandResult {
    stdout: String,
    stderr: String,
    status: i32,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct TaskConfig {
    skin_path: String,
    bundles_path: String,
    debug_export: bool,
    dry_run: bool,
}

fn workspace_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(|path| path.parent())
        .map(|path| path.to_path_buf())
        .unwrap_or_else(|| PathBuf::from("."))
}

fn python_command() -> PathBuf {
    let root = workspace_root();
    let mut unix_path = root.clone();
    unix_path.push(".venv/bin/python3");

    if unix_path.exists() {
        return unix_path;
    }

    let mut win_path = root.clone();
    win_path.push(".venv/Scripts/python.exe");
    if win_path.exists() {
        return win_path;
    }

    if cfg!(windows) {
        PathBuf::from("python.exe")
    } else {
        PathBuf::from("python3")
    }
}

fn build_cli_args(config: &TaskConfig) -> Result<Vec<String>, String> {
    let skin = config.skin_path.trim();
    if skin.is_empty() {
        return Err("Skin folder is required.".to_string());
    }

    let mut args = vec!["patch".to_string(), skin.to_string()];

    let bundles = config.bundles_path.trim();
    if !bundles.is_empty() {
        args.push("--bundle".to_string());
        args.push(bundles.to_string());
    }

    if config.debug_export {
        args.push("--debug-export".to_string());
    }

    if config.dry_run {
        args.push("--dry-run".to_string());
    }

    Ok(args)
}

#[tauri::command]
fn run_python_task(app_handle: AppHandle, config: TaskConfig) -> Result<CommandResult, String> {
    let cli_args = build_cli_args(&config)?;

    let mut command = if cfg!(debug_assertions) {
        let mut cmd = Command::new(python_command());
        cmd.arg("-m").arg("fm_skin_builder");
        cmd.current_dir(workspace_root());
        cmd.env("PYTHONPATH", "fm_skin_builder");
        cmd
    } else {
        let backend_binary = app_handle
            .path()
            .resolve("backend/fm_skin_builder", BaseDirectory::Resource)
            .map_err(|error| format!("Failed to resolve backend binary: {error}"))?;
        if !backend_binary.exists() {
            return Err("Backend binary missing. Run scripts/build_backend.sh".to_string());
        }
        Command::new(backend_binary)
    };

    command.args(&cli_args);

    let output = command
        .output()
        .map_err(|error| format!("Failed to run backend: {error}"))?;

    Ok(CommandResult {
        stdout: String::from_utf8_lossy(&output.stdout).to_string(),
        stderr: String::from_utf8_lossy(&output.stderr).to_string(),
        status: output.status.code().unwrap_or(-1),
    })
}

#[tauri::command]
fn select_folder(dialog_title: Option<String>, initial_path: Option<String>) -> Option<String> {
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

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![run_python_task, select_folder])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
