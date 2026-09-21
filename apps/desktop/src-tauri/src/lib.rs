use std::{
    fs::{self, OpenOptions},
    io::Write,
    net::{TcpListener, TcpStream},
    path::PathBuf,
    process::Command,
    sync::Mutex,
    thread,
    time::{Duration, Instant},
};

use tauri::{Manager, RunEvent, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_shell::{process::CommandChild, process::CommandEvent, ShellExt};
use uuid::Uuid;

const SIDECAR_NAME: &str = "agent-career-harness-sidecar";
const SIDECAR_STARTUP_TIMEOUT: Duration = Duration::from_secs(90);

struct SidecarState(Mutex<Option<CommandChild>>);

fn sidecar_log_path() -> PathBuf {
    let data_root = std::env::var_os("ACH_DATA_DIR")
        .map(PathBuf::from)
        .or_else(|| {
            std::env::var_os("LOCALAPPDATA")
                .map(PathBuf::from)
                .map(|path| path.join("AgentCareerHarness"))
        })
        .unwrap_or_else(|| PathBuf::from("."));
    data_root.join("logs").join("desktop-sidecar.log")
}

fn capture_sidecar_events(
    mut events: tauri::async_runtime::Receiver<CommandEvent>,
    log_path: PathBuf,
) {
    tauri::async_runtime::spawn(async move {
        let Ok(mut log) = OpenOptions::new().create(true).append(true).open(log_path) else {
            return;
        };
        while let Some(event) = events.recv().await {
            let line = match event {
                CommandEvent::Stdout(bytes) | CommandEvent::Stderr(bytes) => {
                    String::from_utf8_lossy(&bytes).into_owned()
                }
                CommandEvent::Error(error) => format!("sidecar event error: {error}"),
                CommandEvent::Terminated(payload) => {
                    format!("sidecar terminated with code {:?}", payload.code)
                }
                _ => continue,
            };
            let _ = writeln!(log, "{line}");
            let _ = log.flush();
        }
    });
}

fn available_loopback_port() -> Result<u16, Box<dyn std::error::Error>> {
    let listener = TcpListener::bind(("127.0.0.1", 0))?;
    Ok(listener.local_addr()?.port())
}

fn wait_for_sidecar(port: u16) -> Result<(), Box<dyn std::error::Error>> {
    let deadline = Instant::now() + SIDECAR_STARTUP_TIMEOUT;
    while Instant::now() < deadline {
        if TcpStream::connect(("127.0.0.1", port)).is_ok() {
            return Ok(());
        }
        thread::sleep(Duration::from_millis(100));
    }
    Err(format!("local API did not start within {SIDECAR_STARTUP_TIMEOUT:?}").into())
}

fn stop_sidecar(app: &tauri::AppHandle) {
    let state = app.state::<SidecarState>();
    if let Ok(mut child) = state.0.lock() {
        if let Some(child) = child.take() {
            #[cfg(target_os = "windows")]
            let _ = Command::new("taskkill")
                .args(["/PID", &child.pid().to_string(), "/T", "/F"])
                .status();
            let _ = child.kill();
        }
    };
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let port = available_loopback_port()?;
            let token = format!("{}{}", Uuid::new_v4().simple(), Uuid::new_v4().simple());
            let log_path = sidecar_log_path();
            if let Some(log_dir) = log_path.parent() {
                fs::create_dir_all(log_dir)?;
            }
            let (events, child) = app
                .shell()
                .sidecar(SIDECAR_NAME)?
                .env("ACH_HOST", "127.0.0.1")
                .env("ACH_PORT", port.to_string())
                .env("ACH_LAUNCH_TOKEN", token.clone())
                .env("ACH_ENV", "desktop")
                .env("ACH_ALLOWED_ORIGIN", "http://tauri.localhost")
                .spawn()?;
            capture_sidecar_events(events, log_path);
            app.manage(SidecarState(Mutex::new(Some(child))));

            if let Err(error) = wait_for_sidecar(port) {
                stop_sidecar(app.handle());
                return Err(error);
            }

            let frontend_config = serde_json::json!({
                "apiBaseUrl": format!("http://127.0.0.1:{port}"),
                "launchToken": token,
            });
            let initialization_script = format!(
                "window.__ACH_CONFIG__ = Object.freeze({});",
                serde_json::to_string(&frontend_config)?
            );

            WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
                .title("观复职业工作台")
                .inner_size(1240.0, 800.0)
                .min_inner_size(720.0, 560.0)
                .resizable(true)
                .initialization_script(initialization_script)
                .build()?;
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("failed to build Agent Career Harness desktop shell");

    app.run(|app_handle, event| {
        if matches!(event, RunEvent::ExitRequested { .. } | RunEvent::Exit) {
            stop_sidecar(app_handle);
        }
    });
}
