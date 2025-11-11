#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use rfd::FileDialog;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use std::{path::PathBuf, process::Stdio};
use tauri::{path::BaseDirectory, AppHandle, Emitter, Manager, State};
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::{Child, Command};
use tokio::sync::Mutex;

// Global state for managing the running process
struct ProcessState {
    child: Arc<Mutex<Option<Child>>>,
}

impl Default for ProcessState {
    fn default() -> Self {
        Self {
            child: Arc::new(Mutex::new(None)),
        }
    }
}

#[derive(Serialize, Clone)]
struct LogEvent {
    message: String,
    level: String, // "info", "error", "warning"
}

#[derive(Serialize, Clone)]
struct ProgressEvent {
    current: u32,
    total: u32,
    status: String,
}

#[derive(Serialize, Clone)]
struct CompletionEvent {
    success: bool,
    exit_code: i32,
    message: String,
}

#[derive(Serialize, Clone)]
struct TaskStartedEvent {
    message: String,
}

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

/// Parse progress information from log lines
fn parse_progress(line: &str) -> Option<(u32, u32, String)> {
    // Pattern 1: "=== Processing bundle X of Y: ..."
    if line.contains("=== Processing bundle") {
        let parts: Vec<&str> = line.split_whitespace().collect();
        for i in 0..parts.len().saturating_sub(3) {
            if parts[i] == "bundle" && parts.get(i + 2) == Some(&"of") {
                if let (Ok(current), Ok(total)) = (
                    parts[i + 1].parse::<u32>(),
                    parts[i + 3].trim_end_matches(':').parse::<u32>(),
                ) {
                    let status = format!("Processing bundle {}", parts.get(i + 4).unwrap_or(&""));
                    return Some((current, total, status));
                }
            }
        }
    }

    // Pattern 2: Look for general "X of Y" patterns
    if line.contains(" of ") {
        let words: Vec<&str> = line.split_whitespace().collect();
        for i in 0..words.len().saturating_sub(2) {
            if words[i + 1] == "of" {
                if let (Ok(current), Ok(total)) = (words[i].parse::<u32>(), words[i + 2].parse::<u32>()) {
                    let status = line.split("===").next().unwrap_or(line).trim().to_string();
                    return Some((current, total, status));
                }
            }
        }
    }

    None
}

/// Determine log level from line content
fn get_log_level(line: &str) -> String {
    let line_upper = line.to_uppercase();
    if line_upper.contains("ERROR") || line_upper.contains("✗") || line_upper.contains("[STDERR]") {
        "error".to_string()
    } else if line_upper.contains("WARN") || line_upper.contains("WARNING") {
        "warning".to_string()
    } else {
        "info".to_string()
    }
}

#[tauri::command]
async fn run_python_task(
    app_handle: AppHandle,
    config: TaskConfig,
    state: State<'_, ProcessState>,
) -> Result<CommandResult, String> {
    eprintln!("[RUST] run_python_task called!");
    eprintln!("[RUST] Config: skin_path={}, bundles_path={}, dry_run={}",
        config.skin_path, config.bundles_path, config.dry_run);

    // Get the window to emit events to
    // Try "main" first, then try to get any available webview window
    let window = app_handle.get_webview_window("main")
        .or_else(|| {
            eprintln!("[RUST] 'main' window not found, trying to get first available window");
            app_handle.webview_windows().into_iter().next().map(|(_, w)| w)
        })
        .ok_or_else(|| {
            eprintln!("[RUST] ERROR: No webview windows available");
            "No webview windows available".to_string()
        })?;
    eprintln!("[RUST] Got window successfully: {:?}", window.label());

    // Emit startup event - check for errors
    eprintln!("[RUST] About to emit task_started event...");
    window.emit(
        "task_started",
        TaskStartedEvent {
            message: "Initializing backend...".to_string(),
        },
    ).map_err(|e| {
        eprintln!("[RUST] ERROR: Failed to emit task_started: {}", e);
        format!("Failed to emit task_started: {}", e)
    })?;
    eprintln!("[RUST] task_started event emitted successfully");

    eprintln!("[RUST] About to emit build_log (validating)...");
    window.emit(
        "build_log",
        LogEvent {
            message: "Validating configuration...".to_string(),
            level: "info".to_string(),
        },
    ).map_err(|e| {
        eprintln!("[RUST] ERROR: Failed to emit build_log: {}", e);
        format!("Failed to emit build_log: {}", e)
    })?;
    eprintln!("[RUST] build_log emitted successfully");

    eprintln!("[RUST] Building CLI args...");
    let cli_args = build_cli_args(&config).map_err(|e| {
        eprintln!("[RUST] ERROR: Failed to build CLI args: {}", e);
        let err_msg = format!("Configuration error: {}", e);
        let _ = window.emit(
            "build_log",
            LogEvent {
                message: err_msg.clone(),
                level: "error".to_string(),
            },
        );
        err_msg
    })?;
    eprintln!("[RUST] CLI args built: {:?}", cli_args);

    // Emit status update
    window.emit(
        "build_log",
        LogEvent {
            message: "Starting Python backend (cold start may take a moment)...".to_string(),
            level: "info".to_string(),
        },
    ).map_err(|e| format!("Failed to emit: {}", e))?;

    // Build the command
    let python_path = python_command();

    window.emit(
        "build_log",
        LogEvent {
            message: format!("Using Python: {}", python_path.display()),
            level: "info".to_string(),
        },
    ).map_err(|e| format!("Failed to emit: {}", e))?;

    let mut command = if cfg!(debug_assertions) {
        let mut cmd = Command::new(&python_path);
        cmd.arg("-m").arg("fm_skin_builder");
        cmd.current_dir(workspace_root());
        cmd.env("PYTHONPATH", "fm_skin_builder");
        cmd
    } else {
        let binary_name = if cfg!(windows) {
            "resources/backend/fm_skin_builder.exe"
        } else {
            "resources/backend/fm_skin_builder"
        };

        let backend_binary = app_handle
            .path()
            .resolve(binary_name, BaseDirectory::Resource)
            .map_err(|error| {
                let err_msg = format!("Failed to resolve backend binary path: {error}");
                let _ = window.emit(
                    "build_log",
                    LogEvent {
                        message: err_msg.clone(),
                        level: "error".to_string(),
                    },
                );
                err_msg
            })?;

        if !backend_binary.exists() {
            let err_msg = format!(
                "Backend binary not found at: {}\nExpected binary name: {}",
                backend_binary.display(),
                binary_name
            );
            let _ = window.emit(
                "build_log",
                LogEvent {
                    message: err_msg.clone(),
                    level: "error".to_string(),
                },
            );
            return Err(err_msg);
        }

        Command::new(backend_binary)
    };

    command.args(&cli_args);
    command.stdout(Stdio::piped());
    command.stderr(Stdio::piped());

    // Hide console window on Windows
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        command.creation_flags(CREATE_NO_WINDOW);
    }

    eprintln!("[RUST] About to emit spawning message...");
    window.emit(
        "build_log",
        LogEvent {
            message: format!("Spawning process with args: {:?}", cli_args),
            level: "info".to_string(),
        },
    ).map_err(|e| {
        eprintln!("[RUST] ERROR: Failed to emit: {}", e);
        format!("Failed to emit: {}", e)
    })?;
    eprintln!("[RUST] Spawning message emitted");

    // Spawn the process
    eprintln!("[RUST] About to spawn child process...");
    let mut child = command
        .spawn()
        .map_err(|error| {
            eprintln!("[RUST] ERROR: Failed to spawn process: {}", error);
            let err_msg = format!("Failed to spawn Python process: {}. Check that Python is installed and accessible.", error);
            let _ = window.emit(
                "build_log",
                LogEvent {
                    message: err_msg.clone(),
                    level: "error".to_string(),
                },
            );
            err_msg
        })?;
    eprintln!("[RUST] Child process spawned successfully!");

    // Emit that backend has started
    window.emit(
        "build_log",
        LogEvent {
            message: "Backend process spawned successfully, processing...".to_string(),
            level: "info".to_string(),
        },
    ).map_err(|e| format!("Failed to emit: {}", e))?;

    // CRITICAL: Take stdout and stderr BEFORE storing the child in the mutex
    eprintln!("[RUST] Taking stdout from child...");
    let stdout = child.stdout.take().ok_or_else(|| {
        eprintln!("[RUST] ERROR: Failed to capture stdout");
        let err_msg = "Failed to capture stdout".to_string();
        let _ = window.emit(
            "build_log",
            LogEvent {
                message: err_msg.clone(),
                level: "error".to_string(),
            },
        );
        err_msg
    })?;
    eprintln!("[RUST] Stdout captured");

    eprintln!("[RUST] Taking stderr from child...");
    let stderr = child.stderr.take().ok_or_else(|| {
        eprintln!("[RUST] ERROR: Failed to capture stderr");
        let err_msg = "Failed to capture stderr".to_string();
        let _ = window.emit(
            "build_log",
            LogEvent {
                message: err_msg.clone(),
                level: "error".to_string(),
            },
        );
        err_msg
    })?;
    eprintln!("[RUST] Stderr captured");

    // NOW store child process for potential cancellation (after taking stdout/stderr)
    eprintln!("[RUST] About to lock mutex and store child...");
    {
        let mut child_guard = state.child.lock().await;
        *child_guard = Some(child);
        eprintln!("[RUST] Child stored in mutex");
    }
    eprintln!("[RUST] Mutex lock released");

    // Create buffered readers
    let mut stdout_reader = BufReader::new(stdout).lines();
    let mut stderr_reader = BufReader::new(stderr).lines();

    // Storage for complete output
    let stdout_lines: Vec<String>;
    let stderr_lines: Vec<String>;

    // Stream stdout
    eprintln!("[RUST] Spawning stdout reader task...");
    let window_stdout = window.clone();
    let stdout_task = tokio::spawn(async move {
        eprintln!("[RUST STDOUT TASK] Started reading stdout...");
        let mut lines = Vec::new();
        while let Ok(Some(line)) = stdout_reader.next_line().await {
            eprintln!("[RUST STDOUT] {}", line);
            lines.push(line.clone());

            // Parse for progress information
            if let Some((current, total, status)) = parse_progress(&line) {
                if total > 0 {
                    let _ = window_stdout.emit(
                        "build_progress",
                        ProgressEvent {
                            current,
                            total,
                            status,
                        },
                    );
                }
            }

            // Emit log event
            let level = get_log_level(&line);
            let _ = window_stdout.emit(
                "build_log",
                LogEvent {
                    message: line,
                    level,
                },
            );
        }
        eprintln!("[RUST STDOUT TASK] Finished reading stdout, {} lines", lines.len());
        lines
    });
    eprintln!("[RUST] Stdout reader task spawned");

    // Stream stderr
    let window_stderr = window.clone();
    let stderr_task = tokio::spawn(async move {
        let mut lines = Vec::new();
        while let Ok(Some(line)) = stderr_reader.next_line().await {
            lines.push(line.clone());

            // Emit stderr as error log
            let _ = window_stderr.emit(
                "build_log",
                LogEvent {
                    message: format!("[STDERR] {}", line),
                    level: "error".to_string(),
                },
            );
        }
        lines
    });

    // Wait for process to complete
    eprintln!("[RUST] About to wait for child process to complete...");
    let exit_status = {
        let child_ref = state.child.clone();
        eprintln!("[RUST] Acquiring mutex lock to get child...");
        let mut child_guard = child_ref.lock().await;
        eprintln!("[RUST] Mutex lock acquired");

        if let Some(child_mut) = child_guard.as_mut() {
            eprintln!("[RUST] Child found in mutex, calling wait()...");
            let status = child_mut
                .wait()
                .await
                .map_err(|error| {
                    eprintln!("[RUST] ERROR: Failed to wait for process: {}", error);
                    let err_msg = format!("Failed to wait for process: {error}");
                    let _ = window.emit(
                        "build_log",
                        LogEvent {
                            message: err_msg.clone(),
                            level: "error".to_string(),
                        },
                    );
                    err_msg
                })?;
            eprintln!("[RUST] Child process completed with status: {:?}", status);

            // Clear the stored child process
            *child_guard = None;
            eprintln!("[RUST] Child cleared from mutex");
            status
        } else {
            eprintln!("[RUST] ERROR: Child not found in mutex (was cancelled?)");
            let err_msg = "Child process was cancelled".to_string();
            let _ = window.emit(
                "build_log",
                LogEvent {
                    message: err_msg.clone(),
                    level: "warning".to_string(),
                },
            );
            return Err(err_msg);
        }
    };
    eprintln!("[RUST] Mutex lock released after wait");

    // Wait for all output to be consumed
    eprintln!("[RUST] Waiting for stdout task to complete...");
    stdout_lines = stdout_task
        .await
        .map_err(|error| {
            eprintln!("[RUST] ERROR: Failed to read stdout: {}", error);
            format!("Failed to read stdout: {error}")
        })?;
    eprintln!("[RUST] Stdout task complete, got {} lines", stdout_lines.len());

    eprintln!("[RUST] Waiting for stderr task to complete...");
    stderr_lines = stderr_task
        .await
        .map_err(|error| {
            eprintln!("[RUST] ERROR: Failed to read stderr: {}", error);
            format!("Failed to read stderr: {error}")
        })?;
    eprintln!("[RUST] Stderr task complete, got {} lines", stderr_lines.len());

    let exit_code = exit_status.code().unwrap_or(-1);
    let success = exit_status.success();
    eprintln!("[RUST] Process exit code: {}, success: {}", exit_code, success);

    // Emit completion event
    eprintln!("[RUST] Emitting build_complete event...");
    window.emit(
        "build_complete",
        CompletionEvent {
            success,
            exit_code,
            message: if success {
                "Build completed successfully".to_string()
            } else {
                format!("Build failed with exit code {}", exit_code)
            },
        },
    ).map_err(|e| {
        eprintln!("[RUST] ERROR: Failed to emit completion: {}", e);
        format!("Failed to emit completion: {}", e)
    })?;
    eprintln!("[RUST] build_complete event emitted");

    eprintln!("[RUST] run_python_task returning successfully");
    Ok(CommandResult {
        stdout: stdout_lines.join("\n"),
        stderr: stderr_lines.join("\n"),
        status: exit_code,
    })
}

#[tauri::command]
async fn stop_python_task(state: State<'_, ProcessState>) -> Result<String, String> {
    let child_ref = state.child.clone();
    let mut child_guard = child_ref.lock().await;

    if let Some(mut child) = child_guard.take() {
        // Try to kill the child process
        match child.kill().await {
            Ok(_) => Ok("Task cancelled successfully".to_string()),
            Err(e) => Err(format!("Failed to cancel task: {}", e)),
        }
    } else {
        Err("No task is currently running".to_string())
    }
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

#[cfg_attr(mobile, tauri::mobile_entry_point)]
fn main() {
    tauri::Builder::default()
        .manage(ProcessState::default())
        .invoke_handler(tauri::generate_handler![
            run_python_task,
            stop_python_task,
            select_folder
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
