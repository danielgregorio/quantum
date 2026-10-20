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
fn the_fine_level_draws_two_pixels_to_the_scene_s_one_the_same_in_any_number_of_bands() {
    let mut s = Screen::start();
    let obs = s.request(json!({"op": "act", "ticks": 30}));
    assert_eq!(obs["level"], 1, "the scene as declared, with its effects");
    assert_eq!(obs["level_name"], "effects");
    assert_eq!(obs["effects"], 0, "the snow is kept for the fine level");
    let obs = s.request(json!({"op": "level", "level": 2}));
    assert_eq!(obs["level_name"], "fine");
    assert_eq!(obs["effects"], 1, "the snow emitter plays");
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

/// A page as `quantum pixel` sends it: Tarefas, with a form, a table
/// with a button a row, a link and a search field.
fn tarefas() -> Value {
    json!({"title": "Tarefas", "flash": "Criada: ligar para a Ana", "view": [
        {"id": 1, "type": "window", "props": {"title": "Tarefas"}, "children": [
            {"id": 2, "type": "form", "props": {}, "event": {"action": "criar", "fields": {"filtro": "todas"}}, "children": [
                {"id": 3, "type": "formitem", "props": {"label": "Nova tarefa"}, "children": [
                    {"id": 4, "type": "input", "props": {"bind": "titulo", "placeholder": "O que fazer?"}}]},
                {"id": 5, "type": "hbox", "props": {}, "children": [
                    {"id": 6, "type": "select", "props": {"bind": "prioridade", "options": "media,alta,baixa", "value": "alta"}},
                    {"id": 7, "type": "checkbox", "props": {"bind": "urgente", "label": "Urgente", "checked": "true"}},
                    {"id": 8, "type": "button", "props": {"text": "Criar", "variant": "primary"}}]}]},
            {"id": 9, "type": "table", "props": {}, "children": [],
             "columns": [{"label": "Tarefa"}, {"label": "Estado"}, {"label": ""}],
             "rows": [[[{"id": 10, "type": "text", "props": {"text": "ligar para a Ana"}}],
                       [{"id": 11, "type": "badge", "props": {"text": "feita", "variant": "success"}}],
                       [{"id": 12, "type": "button", "props": {"text": "Desfazer"}, "event": {"action": "alternar", "fields": {"id": "1"}}}]],
                      [[{"id": 13, "type": "text", "props": {"text": "comprar pão"}}],
                       [{"id": 14, "type": "badge", "props": {"text": "pendente"}}],
                       [{"id": 15, "type": "button", "props": {"text": "Concluir"}, "event": {"action": "alternar", "fields": {"id": "2"}}}]]]},
            {"id": 16, "type": "link", "props": {"text": "Ver a planilha", "to": "/planilha"}},
            {"id": 17, "type": "input", "props": {"bind": "busca", "placeholder": "buscar", "search": "true", "delay": "100"}}]}]})
}

fn find<'a>(obs: &'a Value, event: &str) -> Option<&'a Value> {
    obs["events"]
        .as_array()
        .unwrap()
        .iter()
        .find(|e| e["kind"] == "pixel" && e["event"] == event)
}

#[test]
fn a_page_on_the_screen_is_typed_into_and_answers_with_events() {
    let mut s = Screen::start();
    s.request(json!({"op": "act", "ticks": 10}));
    let obs = s.request(json!({"op": "show", "page": tarefas()}));
    let w = &obs["window"];
    assert_eq!(w["title"], "Tarefas");
    assert_eq!(w["flash"], "Criada: ligar para a Ana");
    assert_eq!(w["items"][0]["bind"], "titulo");
    assert_eq!(
        w["items"][0]["focus"], true,
        "the first field has the focus"
    );
    assert_eq!(obs["events"][0]["kind"], "show");
    assert!(w["texts"]
        .as_array()
        .unwrap()
        .iter()
        .any(|t| t == "comprar pão"));
    // typed, with the keyboard alone, then Enter: the form goes with what was typed and left
    s.request(json!({"op": "act", "type": "ligar de novo", "ticks": 1}));
    let obs = s.request(json!({"op": "act", "tap": ["home", "delete", "L"], "ticks": 1}));
    assert_eq!(obs["window"]["items"][0]["value"], "Ligar de novo");
    s.frame("window");
    let obs = s.request(json!({"op": "act", "tap": ["enter"], "ticks": 1}));
    let submit = find(&obs, "submit").expect("a submit event");
    assert_eq!(submit["action"], "criar");
    assert_eq!(submit["fields"]["titulo"], "Ligar de novo");
    assert_eq!(submit["fields"]["prioridade"], "alta");
    assert_eq!(submit["fields"]["urgente"], "on");
    assert_eq!(
        submit["fields"]["filtro"], "todas",
        "the form's own fields go too"
    );
    // the page shown again keeps the focus where it was, by what the element is
    let mut again = tarefas();
    again["flash"] = json!("Criada: Ligar de novo");
    s.request(json!({"op": "act", "tap": ["tab", "tab"], "ticks": 1}));
    let obs = s.request(json!({"op": "show", "page": again}));
    assert_eq!(obs["window"]["shown"], 2);
    assert_eq!(obs["window"]["items"][2]["bind"], "urgente");
    assert_eq!(obs["window"]["items"][2]["focus"], true);
    // the table: a row, its button; Enter clicks it
    let obs = s.request(json!({"op": "act", "tap": ["tab", "tab", "down"], "ticks": 1}));
    let table = &obs["window"]["items"][4];
    assert_eq!(table["kind"], "table");
    assert_eq!(table["row"], 1);
    assert_eq!(table["actions"][0], "Concluir");
    assert_eq!(table["rows"][0][0], "Desfazer");
    let obs = s.request(json!({"op": "act", "tap": ["enter"], "ticks": 1}));
    let click = find(&obs, "click").expect("a click event");
    assert_eq!(click["action"], "alternar");
    assert_eq!(click["fields"]["id"], "2");
    // the link navigates
    let obs = s.request(json!({"op": "act", "tap": ["tab", "enter"], "ticks": 1}));
    assert_eq!(find(&obs, "navigate").unwrap()["to"], "/planilha");
    // a search field says its change after the pause it names (100 ms: 6 ticks), not at once
    s.request(json!({"op": "act", "tap": ["tab"], "ticks": 1}));
    s.request(json!({"op": "act", "type": "pa", "ticks": 1}));
    let obs = s.request(json!({"op": "until", "pixel": "change", "max_ticks": 2}));
    assert_eq!(obs["stopped"], "max_ticks");
    let obs = s.request(json!({"op": "until", "pixel": "change", "max_ticks": 20}));
    assert_eq!(obs["stopped"], "condition");
    let change = find(&obs, "change").unwrap();
    assert_eq!(change["bind"], "busca");
    assert_eq!(change["value"], "pa");
    // Esc closes: the scene is whole again
    let obs = s.request(json!({"op": "act", "tap": ["escape"], "ticks": 1}));
    assert!(find(&obs, "close").is_some());
    assert_eq!(obs["window"], Value::Null);
}

#[test]
fn the_page_flows_again_when_the_level_changes_and_keeps_its_focus() {
    let mut s = Screen::start();
    let obs = s.request(json!({"op": "show", "page": tarefas()}));
    assert_eq!(obs["window"]["cols"], 53);
    assert_eq!(obs["window"]["rows"], 18);
    // Down from the one-line field goes to the next element (the select, which
    // then takes Down for its options: Tab leaves it)
    let obs = s.request(json!({"op": "act", "tap": ["down"], "ticks": 1}));
    assert_eq!(obs["window"]["items"][1]["bind"], "prioridade");
    assert_eq!(obs["window"]["items"][1]["focus"], true);
    let obs = s.request(json!({"op": "act", "tap": ["down", "tab"], "ticks": 1}));
    assert_eq!(
        obs["window"]["items"][1]["value"], "baixa",
        "Down chose the next option"
    );
    assert_eq!(obs["window"]["items"][2]["bind"], "urgente");
    assert_eq!(obs["window"]["items"][2]["focus"], true);
    // the fine level: twice the pixels, twice the cells, the same focus
    let obs = s.request(json!({"op": "level", "level": 2}));
    assert_eq!(obs["window"]["cols"], 106);
    assert_eq!(obs["window"]["rows"], 36);
    assert_eq!(obs["window"]["items"][2]["focus"], true);
    for bands in [1, 4] {
        let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/screens/window-fine.png");
        let v = s.request(json!({"op": "frame", "expect": path, "bands": bands}));
        assert_eq!(v["ok"], true, "the fine page in {} bands: {}", bands, v);
    }
    let obs = s.request(json!({"op": "level", "level": 0}));
    assert_eq!(obs["window"]["cols"], 53);
    assert_eq!(obs["window"]["items"][2]["focus"], true);
    // typed text is the same whatever the layout: the play driver types characters
    s.request(json!({"op": "act", "tap": ["home"], "ticks": 1}));
    let obs = s.request(json!({"op": "act", "type": "ação", "ticks": 1}));
    assert_eq!(
        obs["window"]["items"][0]["focus"], true,
        "Home went to the first element"
    );
    assert_eq!(obs["window"]["items"][0]["value"], "ação");
}
