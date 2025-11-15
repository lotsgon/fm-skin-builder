use serde::Serialize;

#[derive(Serialize, Clone)]
pub struct LogEvent {
    pub message: String,
    pub level: String, // "info", "error", "warning"
}

#[derive(Serialize, Clone)]
pub struct ProgressEvent {
    pub current: u32,
    pub total: u32,
    pub status: String,
}

#[derive(Serialize, Clone)]
pub struct CompletionEvent {
    pub success: bool,
    pub exit_code: i32,
    pub message: String,
}

#[derive(Serialize, Clone)]
pub struct TaskStartedEvent {
    pub message: String,
}

#[derive(Serialize)]
pub struct CommandResult {
    pub stdout: String,
    pub stderr: String,
    pub status: i32,
}
