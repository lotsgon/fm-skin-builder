use crate::events::{CommandResult, CompletionEvent, LogEvent, ProgressEvent, TaskStartedEvent};
use serde::Deserialize;
use std::path::PathBuf;
use std::process::Stdio;
use std::sync::Arc;
use tauri::{path::BaseDirectory, AppHandle, Emitter, Manager, State};
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::{Child, Command};
use tokio::sync::Mutex;

// Global state for managing the running process
pub struct ProcessState {
    pub child: Arc<Mutex<Option<Child>>>,
}

impl Default for ProcessState {
    fn default() -> Self {
        Self {
            child: Arc::new(Mutex::new(None)),
        }
    }
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TaskConfig {
    pub skin_path: String,
    pub bundles_path: String,
    pub debug_export: bool,
    pub dry_run: bool,
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
                    let status = if i + 4 < parts.len() {
                        format!("Processing bundle {}", parts[i + 4..].join(" "))
                    } else {
                        "Processing bundle".to_string()
                    };
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
                if let (Ok(current), Ok(total)) =
                    (words[i].parse::<u32>(), words[i + 2].parse::<u32>())
                {
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

    // Check for explicit log level markers (Python logging format)
    if line_upper.contains("ERROR") || line_upper.contains("✗") || line_upper.contains("CRITICAL")
    {
        "error".to_string()
    } else if line_upper.contains("WARN") || line_upper.contains("WARNING") {
        "warning".to_string()
    } else if line_upper.contains("DEBUG") {
        "info".to_string()
    } else {
        // Default to info for normal messages
        "info".to_string()
    }
}

#[tauri::command]
pub async fn run_python_task(
    app_handle: AppHandle,
    config: TaskConfig,
    state: State<'_, ProcessState>,
) -> Result<CommandResult, String> {
    eprintln!("[RUST] run_python_task called!");
    eprintln!(
        "[RUST] Config: skin_path={}, bundles_path={}, dry_run={}",
        config.skin_path, config.bundles_path, config.dry_run
    );

    // Get the window to emit events to
    let window = app_handle.get_webview_window("main").ok_or_else(|| {
        eprintln!("[RUST] ERROR: 'main' window not found.");
        "'main' window not found".to_string()
    })?;

    // Emit startup event
    window
        .emit(
            "task_started",
            TaskStartedEvent {
                message: "Initializing backend...".to_string(),
            },
        )
        .map_err(|e| format!("Failed to emit task_started: {}", e))?;

    window
        .emit(
            "build_log",
            LogEvent {
                message: "Validating configuration...".to_string(),
                level: "info".to_string(),
            },
        )
        .map_err(|e| format!("Failed to emit build_log: {}", e))?;

    let cli_args = build_cli_args(&config).map_err(|e| {
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

    // Emit status update
    window
        .emit(
            "build_log",
            LogEvent {
                message: "Starting Python backend (cold start may take a moment)...".to_string(),
                level: "info".to_string(),
            },
        )
        .map_err(|e| format!("Failed to emit: {}", e))?;

    // Build the command
    let python_path = python_command();

    window
        .emit(
            "build_log",
            LogEvent {
                message: format!("Using Python: {}", python_path.display()),
                level: "info".to_string(),
            },
        )
        .map_err(|e| format!("Failed to emit: {}", e))?;

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
            .map_err(|error| format!("Failed to resolve backend binary path: {error}"))?;

        if !backend_binary.exists() {
            return Err(format!(
                "Backend binary not found at: {}\nExpected binary name: {}",
                backend_binary.display(),
                binary_name
            ));
        }

        Command::new(backend_binary)
    };

    command.args(&cli_args);
    command.stdout(Stdio::piped());
    command.stderr(Stdio::piped());

    // Set cache directory environment variable
    let cache_dir = app_handle
        .path()
        .app_cache_dir()
        .map_err(|e| format!("Failed to get cache dir: {}", e))?;

    if !cache_dir.exists() {
        std::fs::create_dir_all(&cache_dir)
            .map_err(|e| format!("Failed to create cache dir: {}", e))?;
    }

    command.env("FM_CACHE_DIR", cache_dir.to_string_lossy().to_string());

    window
        .emit(
            "build_log",
            LogEvent {
                message: format!("Using cache directory: {}", cache_dir.display()),
                level: "info".to_string(),
            },
        )
        .map_err(|e| format!("Failed to emit: {}", e))?;

    // Hide console window on Windows
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        command.creation_flags(CREATE_NO_WINDOW);
    }

    window
        .emit(
            "build_log",
            LogEvent {
                message: format!("Spawning process with args: {:?}", cli_args),
                level: "info".to_string(),
            },
        )
        .map_err(|e| format!("Failed to emit: {}", e))?;

    // Spawn the process
    let mut child = command.spawn().map_err(|error| {
        format!(
            "Failed to spawn Python process: {}. Check that Python is installed and accessible.",
            error
        )
    })?;

    window
        .emit(
            "build_log",
            LogEvent {
                message: "Backend process spawned successfully, processing...".to_string(),
                level: "info".to_string(),
            },
        )
        .map_err(|e| format!("Failed to emit: {}", e))?;

    // Take stdout and stderr BEFORE storing the child in the mutex
    let stdout = child.stdout.take().ok_or("Failed to capture stdout")?;
    let stderr = child.stderr.take().ok_or("Failed to capture stderr")?;

    // Store child process for potential cancellation
    {
        let mut child_guard = state.child.lock().await;
        *child_guard = Some(child);
    }

    // Create buffered readers
    let mut stdout_reader = BufReader::new(stdout).lines();
    let mut stderr_reader = BufReader::new(stderr).lines();

    // Stream stdout
    let window_stdout = window.clone();
    let stdout_task = tokio::spawn(async move {
        let mut lines = Vec::new();
        while let Ok(Some(line)) = stdout_reader.next_line().await {
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
        lines
    });

    // Stream stderr
    let window_stderr = window.clone();
    let stderr_task = tokio::spawn(async move {
        let mut lines = Vec::new();
        while let Ok(Some(line)) = stderr_reader.next_line().await {
            lines.push(line.clone());

            // Parse for progress information
            if let Some((current, total, status)) = parse_progress(&line) {
                if total > 0 {
                    let _ = window_stderr.emit(
                        "build_progress",
                        ProgressEvent {
                            current,
                            total,
                            status,
                        },
                    );
                }
            }

            // Parse stderr for log level
            let level = get_log_level(&line);
            let _ = window_stderr.emit(
                "build_log",
                LogEvent {
                    message: line,
                    level,
                },
            );
        }
        lines
    });

    // Wait for process to complete while keeping it in the mutex
    let exit_status = loop {
        let child_ref = state.child.clone();
        let mut child_guard = child_ref.lock().await;

        if let Some(child) = child_guard.as_mut() {
            match child.try_wait() {
                Ok(Some(status)) => {
                    *child_guard = None;
                    drop(child_guard);
                    break status;
                }
                Ok(None) => {
                    drop(child_guard);
                    tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
                }
                Err(error) => {
                    let err_msg = format!("Failed to check process status: {error}");
                    let _ = window.emit(
                        "build_log",
                        LogEvent {
                            message: err_msg.clone(),
                            level: "error".to_string(),
                        },
                    );
                    *child_guard = None;
                    drop(child_guard);
                    return Err(err_msg);
                }
            }
        } else {
            drop(child_guard);
            return Err("Task was cancelled".to_string());
        }
    };

    // Wait for all output to be consumed
    let stdout_lines: Vec<String> = stdout_task
        .await
        .map_err(|error| format!("Failed to read stdout: {error}"))?;
    let stderr_lines: Vec<String> = stderr_task
        .await
        .map_err(|error| format!("Failed to read stderr: {error}"))?;

    let exit_code = exit_status.code().unwrap_or(-1);
    let success = exit_status.success();

    // Emit completion event
    let completion_message = if success {
        if config.dry_run {
            "✓ Preview completed successfully. No bundles were modified during this dry run."
                .to_string()
        } else {
            "✓ Build completed successfully. All bundles have been created.".to_string()
        }
    } else if config.dry_run {
        format!(
            "✗ Preview failed with exit code {}. Check the logs for details.",
            exit_code
        )
    } else {
        format!(
            "✗ Build failed with exit code {}. Check the logs for details.",
            exit_code
        )
    };

    window
        .emit(
            "build_complete",
            CompletionEvent {
                success,
                exit_code,
                message: completion_message,
            },
        )
        .map_err(|e| format!("Failed to emit completion: {}", e))?;

    Ok(CommandResult {
        stdout: stdout_lines.join("\n"),
        stderr: stderr_lines.join("\n"),
        status: exit_code,
    })
}

#[tauri::command]
pub async fn stop_python_task(state: State<'_, ProcessState>) -> Result<String, String> {
    let child_ref = state.child.clone();
    let mut child_guard = child_ref.lock().await;

    if let Some(child) = child_guard.as_mut() {
        match child.kill().await {
            Ok(_) => {
                *child_guard = None;
                Ok("Task cancelled successfully".to_string())
            }
            Err(e) => {
                let err_str = e.to_string();
                if err_str.contains("already exited") || err_str.contains("No such process") {
                    *child_guard = None;
                    Ok("Task already completed".to_string())
                } else {
                    Err(format!("Failed to cancel task: {}", e))
                }
            }
        }
    } else {
        Err("No task is currently running".to_string())
    }
}
