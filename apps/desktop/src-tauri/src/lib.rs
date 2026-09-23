use std::{
    fs::{self, OpenOptions},
    io::{Read, Write},
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

#[cfg(windows)]
use std::os::windows::process::CommandExt;

const SIDECAR_NAME: &str = "agent-career-harness-sidecar";
const SIDECAR_STARTUP_TIMEOUT: Duration = Duration::from_secs(20);
#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

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
    app_handle: tauri::AppHandle,
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
                    if payload.code != Some(0) {
                        if let Some(window) = app_handle.get_webview_window("main") {
                            let _ = window.eval(
                                "window.__ACH_RUNTIME_ERROR__ = '本地职业核心意外退出。请检查本地日志并重新打开应用。'; window.dispatchEvent(new Event('ach-runtime-error'));",
                            );
                        }
                    }
                    format!("sidecar terminated with code {:?}", payload.code)
                }
                _ => continue,
            };
            let _ = writeln!(log, "{line}");
            let _ = log.flush();
        }
    });
}

fn append_sidecar_log(log_path: &PathBuf, message: &str) {
    if let Some(parent) = log_path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    if let Ok(mut log) = OpenOptions::new().create(true).append(true).open(log_path) {
        let _ = writeln!(log, "{message}");
        let _ = log.flush();
    }
}

fn available_loopback_port() -> Result<u16, Box<dyn std::error::Error>> {
    let listener = TcpListener::bind(("127.0.0.1", 0))?;
    Ok(listener.local_addr()?.port())
}

fn wait_for_sidecar(port: u16, token: &str) -> Result<(), String> {
    let deadline = Instant::now() + SIDECAR_STARTUP_TIMEOUT;
    while Instant::now() < deadline {
        if let Ok(mut stream) = TcpStream::connect(("127.0.0.1", port)) {
            let _ = stream.set_read_timeout(Some(Duration::from_millis(500)));
            let request = format!(
                "GET /health HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nAuthorization: Bearer {token}\r\nConnection: close\r\n\r\n"
            );
            if stream.write_all(request.as_bytes()).is_ok() {
                let mut response = Vec::new();
                if let Err(error) = stream.read_to_end(&mut response) {
                    if matches!(
                        error.kind(),
                        std::io::ErrorKind::TimedOut | std::io::ErrorKind::WouldBlock
                    ) {
                        return Err(format!("loopback port {port} is occupied by a non-API service"));
                    }
                }
                let response = String::from_utf8_lossy(&response);
                if (response.starts_with("HTTP/1.1 200") || response.starts_with("HTTP/1.0 200"))
                    && response.contains("\"service\":\"agent-career-harness\"")
                {
                    return Ok(());
                }
                if response.starts_with("HTTP/") {
                    return Err(format!("loopback port {port} is occupied by another service"));
                }
                if !response.is_empty() {
                    return Err(format!("loopback port {port} returned an invalid local API response"));
                }
            }
        }
        thread::sleep(Duration::from_millis(100));
    }
    Err(format!("local API did not become healthy within {SIDECAR_STARTUP_TIMEOUT:?}"))
}

fn terminate_sidecar(child: CommandChild) {
    #[cfg(windows)]
    let _ = {
        let mut command = Command::new("taskkill");
        command.args(["/PID", &child.pid().to_string(), "/T", "/F"]);
        command.creation_flags(CREATE_NO_WINDOW).status()
    };
    let _ = child.kill();
}

fn stop_sidecar(app: &tauri::AppHandle) {
    let state = app.state::<SidecarState>();
    if let Ok(mut child) = state.0.lock() {
        if let Some(child) = child.take() {
            terminate_sidecar(child);
        }
    };
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let demo_mode = std::env::var("ACH_DESKTOP_DEMO").as_deref() == Ok("1");
            let token = if demo_mode {
                String::new()
            } else {
                format!("{}{}", Uuid::new_v4().simple(), Uuid::new_v4().simple())
            };
            let log_path = sidecar_log_path();
            if let Some(log_dir) = log_path.parent() {
                fs::create_dir_all(log_dir)?;
            }
            let mut active_port = available_loopback_port()?;
            let mut active_child = None;
            let mut startup_error = None;
            for attempt in 0..3 {
                let forced_test_port = (attempt == 0)
                    .then(|| std::env::var("ACH_DESKTOP_TEST_PORT").ok())
                    .flatten()
                    .and_then(|value| value.parse::<u16>().ok());
                let port = match forced_test_port {
                    Some(port) => port,
                    None => available_loopback_port()?,
                };
                let child_result = app
                    .shell()
                    .sidecar(SIDECAR_NAME)
                    .map(|command| {
                        command
                            .args([
                                "--host".to_string(),
                                "127.0.0.1".to_string(),
                                "--port".to_string(),
                                port.to_string(),
                                "--environment".to_string(),
                                if demo_mode { "demo" } else { "desktop" }.to_string(),
                                "--allowed-origin".to_string(),
                                "http://tauri.localhost".to_string(),
                            ])
                            .env("ACH_HOST", "127.0.0.1")
                            .env("ACH_PORT", port.to_string())
                            .env("ACH_LAUNCH_TOKEN", token.clone())
                            .env("ACH_ENV", if demo_mode { "demo" } else { "desktop" })
                            .env("ACH_ALLOWED_ORIGIN", "http://tauri.localhost")
                    })
                    .and_then(|command| command.spawn());
                let (events, child) = match child_result {
                    Ok(started) => started,
                    Err(error) => {
                        startup_error = Some(error.to_string());
                        append_sidecar_log(&log_path, &format!("sidecar spawn failed: {error}"));
                        break;
                    }
                };
                append_sidecar_log(
                    &log_path,
                    &format!("sidecar started pid={} port={port}", child.pid()),
                );
                capture_sidecar_events(events, log_path.clone(), app.handle().clone());
                match wait_for_sidecar(port, &token) {
                    Ok(()) => {
                        active_port = port;
                        active_child = Some(child);
                        append_sidecar_log(&log_path, &format!("local API ready on port {port}"));
                        break;
                    }
                    Err(error) => {
                        append_sidecar_log(&log_path, &format!("sidecar readiness failed: {error}"));
                        terminate_sidecar(child);
                        startup_error = Some(error.clone());
                        if !error.contains("occupied") || attempt == 2 {
                            break;
                        }
                    }
                }
            }
            app.manage(SidecarState(Mutex::new(active_child)));

            let frontend_config = serde_json::json!({
                "apiBaseUrl": format!("http://127.0.0.1:{active_port}"),
                "launchToken": token,
                "demoMode": demo_mode,
                "startupError": startup_error.as_ref().map(|_| "本地职业核心未能启动。请关闭并重新打开应用；诊断信息已写入本地日志。"),
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
