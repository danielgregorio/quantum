extends RefCounted
# The TUI in a browser (SPEC.md UI-22: `quantum package <app> --on tui --target web`): what the browser does
# there in place of what the TUI does for itself elsewhere (tui.gd).
#
# The page is served by the application's own server (/static/tui/index.html), so its origin is the server: a
# request goes through the browser's fetch, the browser keeps the session's cookies and follows the redirects
# (the final address is where the TUI is). A stream is read as it is written; a file field opens the browser's
# own file picker. Bodies cross between Godot and JavaScript as base64 both ways, so a picture or a multipart
# form goes as it is.
#
# And the play protocol: window.quantumTui.request(json) is a Promise of the answer's JSON, the same requests and
# answers as the TUI's stdin and stdout elsewhere (tui.gd's _serve_play; quantum/runtime/ui_tui.py, TuiInBrowser).

signal answered(id: int)

const HELPER := """(function () {
  if (window.quantumTuiNet) return;
  const waiting = [];
  function bytes(b64) {
    const s = atob(b64), out = new Uint8Array(s.length);
    for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i);
    return out;
  }
  function base64(data) {
    let s = '';
    for (let i = 0; i < data.length; i += 0x8000) s += String.fromCharCode.apply(null, data.subarray(i, i + 0x8000));
    return btoa(s);
  }
  function headers(r) {
    const lines = [];
    r.headers.forEach((v, k) => lines.push(k + ': ' + v));
    return lines.join('\\n');
  }
  const net = window.quantumTuiNet = {
    // one request: done(id, status, the address it ended at, headers, body); status 0 when it could not be made
    request(id, method, url, accept, type, referrer, body, done) {
      const init = {method: method, credentials: 'same-origin', redirect: 'follow', headers: {'Accept': accept},
                    cache: accept.indexOf('image/') === 0 ? 'default' : 'no-store'};
      if (type) init.headers['Content-Type'] = type;
      if (referrer) init.referrer = referrer;
      if (method !== 'GET') init.body = bytes(body);
      fetch(url, init)
        .then(r => r.arrayBuffer().then(b => done(id, r.status, r.url, headers(r), base64(new Uint8Array(b)))))
        .catch(() => done(id, 0, '', '', ''));
    },
    // a stream as it is written: on(id, 'head', status), then on(id, 'chunk', base64) for each part, on(id, 'end')
    stream(id, url, on) {
      let headed = false;
      fetch(url, {credentials: 'same-origin', cache: 'no-store', headers: {'Accept': 'text/plain'}})
        .then(async r => {
          headed = true;
          on(id, 'head', r.status);
          if (r.status === 200 && r.body) {
            const reader = r.body.getReader();
            for (;;) {
              const part = await reader.read();
              if (part.done) break;
              on(id, 'chunk', base64(part.value));
            }
          }
          on(id, 'end', '');
        })
        .catch(() => {
          if (!headed) on(id, 'head', 0);
          on(id, 'end', '');
        });
    },
    // the browser's own file picker: done(id, name, base64) once a file is chosen
    pick(id, accept, done) {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = accept;
      input.style.display = 'none';
      input.addEventListener('change', () => {
        const file = input.files[0];
        input.remove();
        if (file) file.arrayBuffer().then(b => done(id, file.name, base64(new Uint8Array(b))));
      });
      input.addEventListener('cancel', () => input.remove());
      document.body.appendChild(input);
      input.click();
    },
    deliver: null,                 // the TUI's: a request of the play protocol, as its JSON
    answer(text) {
      const resolve = waiting.shift();
      if (resolve) resolve(text);
    },
  };
  // the play protocol, answered in order as on stdin and stdout
  window.quantumTui = {
    request(req) {
      return new Promise(resolve => {
        waiting.push(resolve);
        net.deliver(typeof req === 'string' ? req : JSON.stringify(req));
      });
    },
  };
})();"""

var _tui: Node
var _net = null                  # window.quantumTuiNet
var _callbacks: Array = []       # held, or JavaScript would call freed callables
var _done = null
var _on_stream = null
var _picked = null
var _answers := {}               # a request's answer by its id, until the request takes it
var _next := 0
var _streams := {}               # a stream's url by its id
var _picks := {}                 # a file field's key by the id of its picker


func _init(tui: Node) -> void:
	_tui = tui
	JavaScriptBridge.eval(HELPER, true)
	_net = JavaScriptBridge.get_interface("quantumTuiNet")
	_done = _callback("_js_done")
	_on_stream = _callback("_js_stream")
	_picked = _callback("_js_picked")
	_net.deliver = _callback("_js_deliver")


func _callback(method: String):
	var cb = JavaScriptBridge.create_callback(Callable(self, method))
	_callbacks.append(cb)
	return cb


func origin() -> String:
	return str(JavaScriptBridge.eval("location.origin", true)).rstrip("/")


func first_page() -> String:
	# the TUI's page's ?page=, else the application's first page
	var page := str(JavaScriptBridge.eval("new URLSearchParams(location.search).get('page') || '/'", true))
	return page if page.begins_with("/") else "/" + page


func request(method: String, url: String, body: PackedByteArray, content_type: String, accept: String,
		referrer: String) -> Dictionary:
	# {code, headers, body, url}: as tui.gd's http answers, and the address the redirects ended at
	_next += 1
	var id := _next
	_net.request(id, method, url, accept, content_type, referrer,
				 Marshalls.raw_to_base64(body) if body.size() > 0 else "", _done)
	while not _answers.has(id):
		await answered
	var answer: Dictionary = _answers[id]
	_answers.erase(id)
	return answer


static func _raw(b64: Variant) -> PackedByteArray:
	# what JavaScript sent as base64 (Godot says an empty one is an error)
	var text := str(b64)
	return Marshalls.base64_to_raw(text) if text != "" else PackedByteArray()


func _js_done(args: Array) -> void:
	var lines := PackedStringArray()
	for line in str(args[3]).split("\n", false):
		lines.append(line)
	var id := int(args[0])
	_answers[id] = {"code": int(args[1]), "url": str(args[2]), "headers": lines,
					"body": _raw(args[4])}
	answered.emit(id)


func stream(url: String) -> void:
	# read as it is written: the TUI is told of its head, each part and its end (tui.gd's _web_stream)
	_next += 1
	_streams[_next] = url
	_net.stream(_next, url, _on_stream)


func _js_stream(args: Array) -> void:
	var id := int(args[0])
	var kind := str(args[1])
	if not _streams.has(id):
		return
	var url: String = _streams[id]
	if kind == "chunk":
		_tui._web_stream(url, kind, _raw(args[2]))
	else:
		if kind == "end":
			_streams.erase(id)
		_tui._web_stream(url, kind, int(args[2]) if kind == "head" else 0)


func pick(accept: String, key: String) -> void:
	# the browser's file picker for the field `key`; the file chosen goes to tui.gd's _web_picked
	_next += 1
	_picks[_next] = key
	_net.pick(_next, accept, _picked)


func _js_picked(args: Array) -> void:
	var id := int(args[0])
	if _picks.has(id):
		_tui._web_picked(_picks[id], str(args[1]), _raw(args[2]))
		_picks.erase(id)


func _js_deliver(args: Array) -> void:
	_tui._web_inbox(str(args[0]) if args.size() > 0 else "")


func answer(text: String) -> void:
	_net.answer(text)
