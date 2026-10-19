//! The OS's screen, played through the driver with no Hive and no display:
//! a crash, the offers, an approval and its result, what each shows as
//! data, and the picture of each compared pixel for pixel with the
//! reference frames in tests/screens/ (UPDATE_SCREENS=1 rewrites them).

use serde_json::{json, Value};
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};

struct Screen {
    child: Child,
    stdin: std::process::ChildStdin,
    lines: std::io::Lines<BufReader<std::process::ChildStdout>>,
}

fn os_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .unwrap()
}

impl Screen {
    fn start() -> Screen {
        let mut child = Command::new(env!("CARGO_BIN_EXE_hive-screen"))
            .arg("--scene")
            .arg(os_dir().join("config/screen/screen.toml"))
            .arg("--no-hive")
            .arg("--play")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit())
            .spawn()
            .expect("hive-screen starts");
        let stdin = child.stdin.take().unwrap();
        let lines = BufReader::new(child.stdout.take().unwrap()).lines();
        Screen {
            child,
            stdin,
            lines,
        }
    }

    fn request(&mut self, req: Value) -> Value {
        writeln!(self.stdin, "{}", req).unwrap();
        for line in self.lines.by_ref() {
            let line = line.unwrap();
            if let Some(rest) = line.strip_prefix("QPP ") {
                let v: Value = serde_json::from_str(rest).unwrap();
                assert!(v.get("error").is_none(), "{}", v);
                return v;
            }
        }
        panic!("hive-screen ended without answering {}", req);
    }

    fn frame(&mut self, name: &str) -> Value {
        let path =
            PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(format!("tests/screens/{}.png", name));
        let v = self.request(json!({"op": "frame", "expect": path}));
        assert_eq!(v["ok"], true, "frame {} is not the reference: {}", name, v);
        v
    }
}

impl Drop for Screen {
    fn drop(&mut self) {
        let _ = writeln!(self.stdin, "{}", json!({"op": "end"}));
        let _ = self.child.wait();
    }
}

fn crash() -> Value {
    json!({"Notification": {
        "id": "11111111-2222-3333-4444-555555555555",
        "title": "Service Crashed", "body": "nginx.service exited with code 1", "severity": "Error",
        "actions": [], "timeout_secs": 10,
        "kind": "service-crash", "fields": {"unit": "nginx.service", "service": "nginx", "exit_code": "1"}}})
}

fn offers() -> Value {
    json!({"Notification": {
        "id": "11111111-2222-3333-4444-666666666666",
        "title": "Hive Suggestion", "body": "2 suggestion(s) available", "severity": "Info",
        "actions": [
            {"id": 1, "title": "Restart nginx", "description": "", "action": {"RestartService": {"name": "nginx"}},
             "learn_more": null, "confidence": 0.9},
            {"id": 2, "title": "Remove nginx", "description": "", "action": {"RemovePackage": {"name": "nginx", "purge": false}},
             "learn_more": null, "confidence": 0.5}],
        "timeout_secs": 0, "kind": "offer", "fields": {"count": "2"}}})
}

fn done() -> Value {
    json!({"ActionResponse": {
        "request_id": "11111111-2222-3333-4444-777777777777",
        "action": {"RestartService": {"name": "nginx"}}, "success": true, "output": null, "exit_code": 0}})
}

#[test]
fn a_crash_an_offer_an_approval_and_its_result() {
    let mut s = Screen::start();
    let obs = s.request(json!({"op": "act", "ticks": 30}));
    assert_eq!(obs["tick"], 30);
    assert_eq!(
        obs["sprites"]["nginx"]["frame"], 1,
        "an empty cell to begin with"
    );
    assert_eq!(obs["sprites"]["bee"]["animation"], "fly");
    s.frame("idle");

    // the crash: the rule on service-crash plays smoke on the cell named by {service}
    let obs = s.request(json!({"op": "inject", "message": crash()}));
    assert_eq!(obs["sprites"]["nginx"]["animation"], "smoke");
    assert_eq!(obs["toast"], "nginx stopped (exit 1)");
    assert_eq!(obs["events"][0]["event"], "service-crash");
    let obs = s.request(json!({"op": "act", "ticks": 20}));
    assert_eq!(
        obs["sprites"]["nginx"]["frame"], 3,
        "the first puff of smoke"
    );
    s.frame("crash");
    let obs = s.request(json!({"op": "act", "ticks": 80}));
    assert_eq!(
        obs["sprites"]["nginx"]["frame"], 2,
        "cracked, once the smoke is gone"
    );
    assert_eq!(obs["sprites"]["nginx"]["animation"], Value::Null);

    // the offers: rows, the first with the focus; the dangerous one asks twice
    let obs = s.request(json!({"op": "inject", "message": offers()}));
    assert_eq!(obs["offers"].as_array().unwrap().len(), 2);
    assert_eq!(obs["offers"][0]["title"], "Restart nginx");
    assert_eq!(obs["offers"][0]["focus"], true);
    assert_eq!(obs["offers"][1]["dangerous"], true);
    assert!(obs["toast"]
        .as_str()
        .unwrap()
        .starts_with("the Hive offers 2"));
    let obs = s.request(json!({"op": "act", "ticks": 10}));
    assert!(
        obs["sprites"]["bee"]["y"].as_f64().unwrap() > 2.0,
        "the bee bobs on an offer"
    );
    s.frame("offer");
    let obs = s.request(json!({"op": "act", "tap": ["down", "enter"], "ticks": 1}));
    assert_eq!(
        obs["offers"][1]["armed"], true,
        "a dangerous action asks for Enter again"
    );
    assert_eq!(obs["offers"][1]["outcome"], Value::Null);
    let obs = s.request(json!({"op": "act", "tap": ["up"], "ticks": 1}));
    assert_eq!(obs["offers"][1]["armed"], false, "moving away disarms it");

    // the approval: Enter on the first row sends it; the actuator's answer is `done`
    let obs = s.request(json!({"op": "act", "tap": ["enter"], "ticks": 1}));
    assert_eq!(obs["offers"][0]["outcome"], "sent");
    assert!(obs["events"]
        .as_array()
        .unwrap()
        .iter()
        .any(|e| e["kind"] == "approve"));
    let obs = s.request(json!({"op": "inject", "message": done()}));
    assert_eq!(obs["offers"][0]["outcome"], "succeeded");
    assert_eq!(
        obs["sprites"]["nginx"]["frame"], 0,
        "honey again: the service runs"
    );
    assert_eq!(obs["events"][0]["event"], "done");
    assert_eq!(obs["events"][0]["fields"]["service"], "nginx");
    assert_eq!(obs["toast"], "restart-service: done");
    s.request(json!({"op": "act", "ticks": 60}));
    s.frame("done");

    // dismissing takes the whole notification's rows away
    let obs = s.request(json!({"op": "act", "tap": ["escape"], "ticks": 1}));
    assert_eq!(obs["offers"].as_array().unwrap().len(), 0);
    assert!(obs["events"]
        .as_array()
        .unwrap()
        .iter()
        .any(|e| e["kind"] == "dismiss"));
}

#[test]
fn until_waits_for_a_condition_and_a_plain_notice_is_said() {
    let mut s = Screen::start();
    let notice = json!({"Notification": {
        "id": "11111111-2222-3333-4444-888888888888",
        "title": "Disk", "body": "/var is nearly full", "severity": "Warning",
        "actions": [], "timeout_secs": 10, "kind": null, "fields": {}}});
    s.request(json!({"op": "inject", "message": notice}));
    let obs = s.request(json!({"op": "until", "toast": "nearly full", "max_ticks": 5}));
    assert_eq!(obs["stopped"], "condition");
    assert_eq!(obs["notices"][0], "Disk: /var is nearly full");
    let obs = s.request(json!({"op": "until", "offer": "nothing", "max_ticks": 3}));
    assert_eq!(obs["stopped"], "max_ticks");
    assert_eq!(obs["tick"], 4);
    // an event with no rule and a field the scene has no sprite for do nothing, quietly
    let obs = s.request(json!({"op": "inject", "message": {"Notification": {
        "id": "11111111-2222-3333-4444-999999999999",
        "title": "Service Crashed", "body": "x", "severity": "Error", "actions": [], "timeout_secs": 10,
        "kind": "service-crash", "fields": {"unit": "ghost.service", "service": "ghost", "exit_code": "2"}}}}));
    assert_eq!(obs["toast"], "ghost stopped (exit 2)");
    assert_eq!(obs["sprites"]["nginx"]["animation"], Value::Null);
}
