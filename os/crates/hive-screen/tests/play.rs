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
    // the bars say what the screen knows of itself; a test's screen has no clock and no name
    assert_eq!(obs["bars"]["top"]["title"], "Quantum OS");
    assert_eq!(obs["bars"]["top"]["left"], "");
    assert_eq!(obs["bars"]["top"]["right"], "1 cores · effects · --:--");
    assert_eq!(obs["bars"]["bottom"]["right"], "offers: 0 · F1");
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
        obs["sprites"]["bee"]["y"].as_f64().unwrap() > 36.0,
        "the bee bobs on an offer"
    );
    assert_eq!(obs["bars"]["bottom"]["right"], "offers: 2 · F1");
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
fn a_new_offer_takes_the_focus_once_the_one_with_it_is_answered() {
    let mut s = Screen::start();
    s.request(json!({"op": "inject", "message": offers()}));
    let obs = s.request(json!({"op": "act", "tap": ["enter"], "ticks": 1}));
    assert_eq!(obs["offers"][0]["outcome"], "sent");
    let obs = s.request(json!({"op": "inject", "message": done()}));
    assert_eq!(obs["offers"][0]["outcome"], "succeeded");
    assert_eq!(
        obs["offers"][0]["focus"], true,
        "the focus stays until something else waits"
    );
    // a user's request comes as an offer of its own kind: Enter answers it, not the row already done
    let request = json!({"Notification": {
        "id": "11111111-2222-3333-4444-888888888888",
        "title": "Request", "body": "druid asks: name the machine forge", "severity": "Info",
        "actions": [{"id": 1, "title": "druid asks: name the machine forge", "description": "",
                     "action": {"SetHostname": {"name": "forge"}}, "learn_more": null, "confidence": 1.0}],
        "timeout_secs": 0, "kind": "request",
        "fields": {"user": "druid", "action": "set-hostname", "what": "name the machine forge", "count": "1"}}});
    let obs = s.request(json!({"op": "inject", "message": request}));
    assert_eq!(obs["offers"].as_array().unwrap().len(), 3);
    assert_eq!(obs["offers"][0]["focus"], false);
    assert_eq!(obs["offers"][2]["focus"], true, "the request has the focus");
    assert!(event(&obs, "event")
        .is_some_and(|e| e["event"] == "request" && e["fields"]["user"] == "druid"));
    assert!(obs["toast"]
        .as_str()
        .unwrap()
        .starts_with("druid asks: name the machine forge"));
    let obs = s.request(json!({"op": "act", "tap": ["enter"], "ticks": 1}));
    assert_eq!(obs["offers"][2]["outcome"], "sent");
    assert!(
        event(&obs, "approve").is_some_and(|e| e["title"] == "druid asks: name the machine forge")
    );
}

#[test]
fn the_fine_level_draws_two_pixels_to_the_scene_s_one_the_same_in_any_number_of_bands() {
    let mut s = Screen::start();
    let obs = s.request(json!({"op": "act", "ticks": 30}));
    assert_eq!(obs["level"], 1, "the scene as declared, with its effects");
    assert_eq!(obs["level_name"], "effects");
    assert_eq!(obs["effects"], 0, "the snow is kept for the fine level");
    let obs = s.request(json!({"op": "level", "level": 2}));
    assert_eq!(obs["level_name"], "fine");
    assert_eq!(obs["effects"], 1, "the snow emitter plays");
    assert_eq!(obs["bars"]["top"]["right"], "1 cores · fine · --:--");
    let obs = s.request(json!({"op": "act", "ticks": 90}));
    assert_eq!(obs["tick"], 120);
    // the same frame, drawn whole and in bands: the reference is 640x360
    for bands in [1, 3, 8] {
        let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/screens/fine.png");
        let v = s.request(json!({"op": "frame", "expect": path, "bands": bands}));
        assert_eq!(v["ok"], true, "the fine frame in {} bands: {}", bands, v);
    }
    // plain: no particles at all, and a burst asked for does not start
    let obs = s.request(json!({"op": "level", "level": 0}));
    assert_eq!(obs["effects"], 0);
    let obs = s.request(json!({"op": "inject", "message": crash()}));
    assert_eq!(
        obs["sprites"]["nginx"]["animation"], "smoke",
        "what happens does not change"
    );
    assert_eq!(obs["effects"], 0, "how it shows does: no dust");
    let obs = s.request(json!({"op": "level", "level": 1}));
    assert_eq!(obs["effects"], 0, "a burst missed is not made up");
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

/// A page as `quantum pixel` sends it: Tasks, with a form, a table
/// with a button a row, a link and a search field.
fn tasks() -> Value {
    json!({"title": "Tasks", "flash": "Created: call Ann", "view": [
        {"id": 1, "type": "window", "props": {"title": "Tasks"}, "children": [
            {"id": 2, "type": "form", "props": {}, "event": {"action": "create", "fields": {"filter": "all"}}, "children": [
                {"id": 3, "type": "formitem", "props": {"label": "New task"}, "children": [
                    {"id": 4, "type": "input", "props": {"bind": "title", "placeholder": "What to do?"}}]},
                {"id": 5, "type": "hbox", "props": {}, "children": [
                    {"id": 6, "type": "select", "props": {"bind": "priority", "options": "medium,high,low", "value": "high"}},
                    {"id": 7, "type": "checkbox", "props": {"bind": "urgent", "label": "Urgent", "checked": "true"}},
                    {"id": 8, "type": "button", "props": {"text": "Create", "variant": "primary"}}]}]},
            {"id": 9, "type": "table", "props": {}, "children": [],
             "columns": [{"label": "Task"}, {"label": "State"}, {"label": ""}],
             "rows": [[[{"id": 10, "type": "text", "props": {"text": "call Ann"}}],
                       [{"id": 11, "type": "badge", "props": {"text": "done", "variant": "success"}}],
                       [{"id": 12, "type": "button", "props": {"text": "Undo"}, "event": {"action": "toggle", "fields": {"id": "1"}}}]],
                      [[{"id": 13, "type": "text", "props": {"text": "buy bread"}}],
                       [{"id": 14, "type": "badge", "props": {"text": "pending"}}],
                       [{"id": 15, "type": "button", "props": {"text": "Done"}, "event": {"action": "toggle", "fields": {"id": "2"}}}]]]},
            {"id": 16, "type": "link", "props": {"text": "See the sheet", "to": "/sheet"}},
            {"id": 17, "type": "input", "props": {"bind": "search", "placeholder": "search", "search": "true", "delay": "100"}}]}]})
}

fn find<'a>(obs: &'a Value, event: &str) -> Option<&'a Value> {
    obs["events"]
        .as_array()
        .unwrap()
        .iter()
        .find(|e| e["kind"] == "pixel" && e["event"] == event)
}

/// The first event of the screen's own of that kind (approve, dismiss, menu...).
fn event<'a>(obs: &'a Value, kind: &str) -> Option<&'a Value> {
    obs["events"]
        .as_array()
        .unwrap()
        .iter()
        .find(|e| e["kind"] == kind)
}

#[test]
fn a_page_on_the_screen_is_typed_into_and_answers_with_events() {
    let mut s = Screen::start();
    s.request(json!({"op": "act", "ticks": 10}));
    let obs = s.request(json!({"op": "show", "page": tasks()}));
    let w = &obs["window"];
    assert_eq!(w["title"], "Tasks");
    assert_eq!(
        obs["motion"]["kind"], "jelly",
        "a page opens with the jelly"
    );
    assert_eq!(w["flash"], "Created: call Ann");
    assert_eq!(w["items"][0]["bind"], "title");
    assert_eq!(
        w["items"][0]["focus"], true,
        "the first field has the focus"
    );
    assert_eq!(obs["events"][0]["kind"], "show");
    assert!(w["texts"]
        .as_array()
        .unwrap()
        .iter()
        .any(|t| t == "buy bread"));
    // the frames are of the page at rest: the jelly settles first
    let obs = s.request(json!({"op": "until", "still": true, "max_ticks": 30}));
    assert_eq!(obs["stopped"], "condition");
    assert_eq!(obs["motion"], Value::Null);
    // typed, with the keyboard alone, then Enter: the form goes with what was typed and left
    s.request(json!({"op": "act", "type": "call again", "ticks": 1}));
    let obs = s.request(json!({"op": "act", "tap": ["home", "delete", "C"], "ticks": 1}));
    assert_eq!(obs["window"]["items"][0]["value"], "Call again");
    s.frame("window");
    let obs = s.request(json!({"op": "act", "tap": ["enter"], "ticks": 1}));
    let submit = find(&obs, "submit").expect("a submit event");
    assert_eq!(submit["action"], "create");
    assert_eq!(submit["fields"]["title"], "Call again");
    assert_eq!(submit["fields"]["priority"], "high");
    assert_eq!(submit["fields"]["urgent"], "on");
    assert_eq!(
        submit["fields"]["filter"], "all",
        "the form's own fields go too"
    );
    // the page shown again keeps the focus where it was, by what the element is
    let mut again = tasks();
    again["flash"] = json!("Created: Call again");
    s.request(json!({"op": "act", "tap": ["tab", "tab"], "ticks": 1}));
    let obs = s.request(json!({"op": "show", "page": again}));
    assert_eq!(obs["window"]["shown"], 2);
    assert_eq!(obs["window"]["items"][2]["bind"], "urgent");
    assert_eq!(obs["window"]["items"][2]["focus"], true);
    // the table: a row, its button; Enter clicks it
    let obs = s.request(json!({"op": "act", "tap": ["tab", "tab", "down"], "ticks": 1}));
    let table = &obs["window"]["items"][4];
    assert_eq!(table["kind"], "table");
    assert_eq!(table["row"], 1);
    assert_eq!(table["actions"][0], "Done");
    assert_eq!(table["rows"][0][0], "Undo");
    let obs = s.request(json!({"op": "act", "tap": ["enter"], "ticks": 1}));
    let click = find(&obs, "click").expect("a click event");
    assert_eq!(click["action"], "toggle");
    assert_eq!(click["fields"]["id"], "2");
    // the link navigates
    let obs = s.request(json!({"op": "act", "tap": ["tab", "enter"], "ticks": 1}));
    assert_eq!(find(&obs, "navigate").unwrap()["to"], "/sheet");
    // a search field says its change after the pause it names (100 ms: 6 ticks), not at once
    s.request(json!({"op": "act", "tap": ["tab"], "ticks": 1}));
    s.request(json!({"op": "act", "type": "pa", "ticks": 1}));
    let obs = s.request(json!({"op": "until", "pixel": "change", "max_ticks": 2}));
    assert_eq!(obs["stopped"], "max_ticks");
    let obs = s.request(json!({"op": "until", "pixel": "change", "max_ticks": 20}));
    assert_eq!(obs["stopped"], "condition");
    let change = find(&obs, "change").unwrap();
    assert_eq!(change["bind"], "search");
    assert_eq!(change["value"], "pa");
    // Esc closes: the scene is whole again
    let obs = s.request(json!({"op": "act", "tap": ["escape"], "ticks": 1}));
    assert!(find(&obs, "close").is_some());
    assert_eq!(obs["window"], Value::Null);
}

#[test]
fn the_page_flows_again_when_the_level_changes_and_keeps_its_focus() {
    let mut s = Screen::start();
    s.request(json!({"op": "show", "page": tasks()}));
    let obs = s.request(json!({"op": "until", "still": true, "max_ticks": 30}));
    assert_eq!(obs["window"]["cols"], 49);
    assert!(obs["window"]["rows"].as_u64().unwrap() >= 4);
    // Down from the one-line field goes to the next element (the select, which
    // then takes Down for its options: Tab leaves it)
    let obs = s.request(json!({"op": "act", "tap": ["down"], "ticks": 1}));
    assert_eq!(obs["window"]["items"][1]["bind"], "priority");
    assert_eq!(obs["window"]["items"][1]["focus"], true);
    let obs = s.request(json!({"op": "act", "tap": ["down", "tab"], "ticks": 1}));
    assert_eq!(
        obs["window"]["items"][1]["value"], "low",
        "Down chose the next option"
    );
    assert_eq!(obs["window"]["items"][2]["bind"], "urgent");
    assert_eq!(obs["window"]["items"][2]["focus"], true);
    // the fine level: twice the pixels, twice the cells, the same focus
    let obs = s.request(json!({"op": "level", "level": 2}));
    assert_eq!(obs["window"]["cols"], 100);
    assert_eq!(obs["window"]["items"][2]["focus"], true);
    for bands in [1, 4] {
        let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/screens/window-fine.png");
        let v = s.request(json!({"op": "frame", "expect": path, "bands": bands}));
        assert_eq!(v["ok"], true, "the fine page in {} bands: {}", bands, v);
    }
    let obs = s.request(json!({"op": "level", "level": 0}));
    assert_eq!(obs["window"]["cols"], 49);
    assert_eq!(obs["window"]["items"][2]["focus"], true);
    // typed text is the same whatever the layout: the play driver types characters
    s.request(json!({"op": "act", "tap": ["home"], "ticks": 1}));
    let obs = s.request(json!({"op": "act", "type": "façade", "ticks": 1}));
    assert_eq!(
        obs["window"]["items"][0]["focus"], true,
        "Home went to the first element"
    );
    assert_eq!(obs["window"]["items"][0]["value"], "façade");
}

#[test]
fn pages_move_in_pixel_art_the_jelly_the_lamp_and_the_curtain() {
    let mut s = Screen::start();
    s.request(json!({"op": "act", "ticks": 10}));
    // opening: the jelly, 12 ticks; the frame half way has the window growing
    let obs = s.request(json!({"op": "show", "page": tasks()}));
    assert_eq!(obs["motion"], json!({"kind": "jelly", "t": 0, "ticks": 12}));
    let obs = s.request(json!({"op": "act", "ticks": 6}));
    assert_eq!(obs["motion"]["t"], 6);
    s.frame("window-jelly");
    let obs = s.request(json!({"op": "until", "still": true, "max_ticks": 30}));
    assert_eq!(obs["stopped"], "condition");
    assert_eq!(obs["tick"], 22, "the jelly took the rest of its 12 ticks");
    // the page again after an action: the curtain, the old page through the dither
    let mut again = tasks();
    again["flash"] = json!("Created: Call again");
    let obs = s.request(json!({"op": "show", "page": again}));
    assert_eq!(obs["motion"]["kind"], "curtain");
    s.request(json!({"op": "act", "ticks": 4}));
    s.frame("window-curtain");
    s.request(json!({"op": "until", "still": true, "max_ticks": 30}));
    // Esc: the lamp sucks the window into the corner; the window is gone at once, the picture lingers
    let obs = s.request(json!({"op": "act", "tap": ["escape"], "ticks": 0}));
    assert_eq!(obs["window"], Value::Null);
    assert_eq!(obs["motion"]["kind"], "lamp");
    s.request(json!({"op": "act", "ticks": 7}));
    s.frame("window-lamp");
    let obs = s.request(json!({"op": "until", "still": true, "max_ticks": 30}));
    assert_eq!(obs["motion"], Value::Null);
    // at the plain level nothing moves: the page is there at once
    s.request(json!({"op": "level", "level": 0}));
    let obs = s.request(json!({"op": "show", "page": tasks()}));
    assert_eq!(obs["motion"], Value::Null);
    assert_eq!(obs["window"]["title"], "Tasks");
}

#[test]
fn the_f1_menu_lists_the_offers_over_the_page_and_the_bar_has_the_windows_button() {
    let mut s = Screen::start();
    s.request(json!({"op": "show", "page": tasks()}));
    s.request(json!({"op": "until", "still": true, "max_ticks": 30}));
    // offers arrive while the page is up: the window's status bar says so, the bar counts them
    let obs = s.request(json!({"op": "inject", "message": offers()}));
    assert_eq!(obs["bars"]["bottom"]["right"], "offers: 2 · F1");
    assert_eq!(obs["menu"], Value::Null);
    s.request(json!({"op": "until", "still": true, "max_ticks": 30}));
    s.frame("window-offers");
    // F1: the drawer slides in from the left over the page, the comb pushed aside
    let obs = s.request(json!({"op": "act", "tap": ["f1"], "ticks": 4}));
    assert_eq!(obs["menu"], json!({"open": true, "t": 4, "ticks": 8}));
    assert!(event(&obs, "menu").is_some_and(|e| e["open"] == true));
    s.frame("menu-drawer");
    let obs = s.request(json!({"op": "until", "menu": true, "max_ticks": 20}));
    assert_eq!(obs["stopped"], "condition");
    s.frame("menu");
    // the keys are the menu's: Down and Enter arm the dangerous offer, Enter again approves it
    let obs = s.request(json!({"op": "act", "tap": ["down", "enter"], "ticks": 1}));
    assert_eq!(obs["offers"][1]["focus"], true);
    assert_eq!(obs["offers"][1]["armed"], true);
    assert_eq!(obs["window"]["focus"], 0, "the page did not hear the keys");
    let obs = s.request(json!({"op": "act", "tap": ["enter"], "ticks": 1}));
    assert_eq!(obs["offers"][1]["outcome"], "sent");
    assert!(event(&obs, "approve").is_some_and(|e| e["title"] == "Remove nginx"));
    // Delete dismisses the one with the focus (and the notification's other rows with it)
    let obs = s.request(json!({"op": "act", "tap": ["up", "delete"], "ticks": 1}));
    assert_eq!(obs["offers"].as_array().unwrap().len(), 0);
    assert!(event(&obs, "dismiss").is_some_and(|e| e["title"] == "Restart nginx"));
    // Esc shuts the drawer; the page is still there and has its keys back
    let obs = s.request(json!({"op": "act", "tap": ["escape"], "ticks": 0}));
    assert_eq!(obs["menu"]["open"], false);
    assert_eq!(obs["window"]["title"], "Tasks");
    let obs = s.request(json!({"op": "until", "menu": false, "max_ticks": 20}));
    assert_eq!(obs["menu"], Value::Null);
    assert_eq!(obs["bars"]["bottom"]["right"], "offers: 0 · F1");
    let obs = s.request(json!({"op": "act", "tap": ["tab"], "ticks": 1}));
    assert_eq!(obs["window"]["focus"], 1, "the page hears the keys again");
    // with no page, the menu opens over the comb and says there is nothing
    s.request(json!({"op": "act", "tap": ["escape"], "ticks": 0}));
    s.request(json!({"op": "until", "still": true, "max_ticks": 30}));
    let obs = s.request(json!({"op": "act", "tap": ["f1"], "ticks": 8}));
    assert_eq!(obs["menu"]["open"], true);
    s.frame("menu-empty");
    // at the plain level the drawer is out at once, and shut at once
    s.request(json!({"op": "level", "level": 0}));
    let obs = s.request(json!({"op": "act", "tap": ["f1"], "ticks": 0}));
    assert_eq!(obs["menu"], Value::Null);
    let obs = s.request(json!({"op": "act", "tap": ["f1"], "ticks": 0}));
    assert_eq!(obs["menu"], json!({"open": true, "t": 8, "ticks": 8}));
}
