//! SIGTERM stops the process after the in-flight request and flushes the snapshot.

use std::io::{Read, Write};
use std::net::TcpListener;
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

#[test]
fn sigterm_drains_and_exits_zero() {
    let probe = TcpListener::bind("127.0.0.1:0").unwrap();
    let port = probe.local_addr().unwrap().port();
    drop(probe);
    let dir = std::env::temp_dir().join(format!("vatcomply-shutdown-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    let mut child = Command::new(env!("CARGO_BIN_EXE_vatcomply"))
        .env("PORT", port.to_string())
        .env("BIND", "127.0.0.1")
        .env("DATA_DIR", &dir)
        .env("LOG_LEVEL", "error")
        .env("ECB_HIST_URL", "http://127.0.0.1:1/hist.xml")
        .env("ECB_HIST_90D_URL", "http://127.0.0.1:1/90d.xml")
        .env("VIES_URL", "http://127.0.0.1:1/vies")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .unwrap();
    let ready = wait_health(port, Duration::from_secs(10));
    assert!(ready, "server did not open /healthz");
    let body = http_get(port, "/rates").expect("rates before signal");
    assert!(body.contains("\"base\":\"EUR\""), "{body}");
    libc_kill(child.id());
    let started = Instant::now();
    let status = loop {
        if let Some(status) = child.try_wait().unwrap() {
            break status;
        }
        if started.elapsed() > Duration::from_secs(8) {
            let _ = child.kill();
            panic!("process did not exit after SIGTERM");
        }
        std::thread::sleep(Duration::from_millis(50));
    };
    assert!(status.success(), "exit {status}");
    let snapshot = dir.join("rates-snapshot.json.gz");
    assert!(snapshot.is_file(), "snapshot was not flushed");
    let _ = std::fs::remove_dir_all(&dir);
}

fn wait_health(port: u16, budget: Duration) -> bool {
    let start = Instant::now();
    while start.elapsed() < budget {
        if http_get(port, "/healthz").is_some_and(|body| body.contains("ok")) {
            return true;
        }
        std::thread::sleep(Duration::from_millis(30));
    }
    false
}

fn http_get(port: u16, path: &str) -> Option<String> {
    let mut stream = std::net::TcpStream::connect(format!("127.0.0.1:{port}")).ok()?;
    stream.set_read_timeout(Some(Duration::from_secs(2))).ok()?;
    stream
        .set_write_timeout(Some(Duration::from_secs(2)))
        .ok()?;
    let request = format!("GET {path} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n");
    stream.write_all(request.as_bytes()).ok()?;
    let mut buf = Vec::new();
    stream.read_to_end(&mut buf).ok()?;
    let text = String::from_utf8_lossy(&buf).into_owned();
    if text.contains("HTTP/1.1 200") || text.contains("HTTP/1.0 200") {
        Some(text)
    } else {
        None
    }
}

fn libc_kill(pid: u32) {
    let _ = std::process::Command::new("kill")
        .args(["-TERM", &pid.to_string()])
        .status();
}
