extends Control
# The TUI: a Quantum application's pages on a text screen drawn by Godot (SPEC.md UI-20).
#
# It is a renderer, as the browser, the console and the Hive's screen are (UI-3): it asks the
# application's server for each page's view tree (Accept: application/vnd.quantum.view+json), lays it out
# in cells of one font (layout.gd), draws it, and sends what the user did as the same posts a browser
# sends, with the cookies the server set, following its redirects. Nothing of the page's logic runs here.
#
# A terminal's look without a terminal's limits: any colour, boxes laid out exactly, the mouse (a click,
# the wheel, a hover), scrolling that glides, the motions of UI-19, wide characters, the page's images,
# a file field with a dialog of its own.
#
#   godot --path quantum/runtime/tui -- --url=http://127.0.0.1:8000 [--page=/] [--cols=120 --rows=40]
#
# With --play it is driven from its stdin, a JSON request a line, each answered on stdout with "QTP " and
# what the screen shows (the play protocol, as the games' agents use it; quantum/runtime/ui_tui.py).
#
# Exported by `quantum package` (UI-22), it is the package's program: with no --url, it starts the server
# folder beside it (server/package.json says how) with the package's own Python, waits for the line that says
# where the server is, and holds the server's input open; when the TUI goes, so does the server. Exported with
# --server, it is a hosted application's client: project.godot's quantum/server is the server it asks.
#
# Exported for the browser (`quantum package <app> --on tui --target web`, UI-22), it runs in a page the
# application's server serves (/static/tui/index.html?page=/first): its requests go through the browser's fetch
# on that origin, so the browser keeps the cookies and follows the redirects, a file field opens the browser's
# own picker, and window.quantumTui.request(json) answers the play protocol (web.gd).

const Layout = preload("res://layout.gd")
const Web = preload("res://web.gd")
const VIEW := "application/vnd.quantum.view+json"

var base_url := "http://127.0.0.1:8000"
var path := "/"
var play := false
var cols := 120
var rows := 40
var font_size := 16
var cell := Vector2(10, 20)
var font: Font
var bold_font: Font

var cookies := {}
var page := {}
var lay = Layout.new()
var state := {}
var tabs := {}
var tabs_opened := {}
var motions: Array = []          # UI-19: what ran since the page was shown, {kind, speed, what}
var running: Array = []          # the motions moving now: {region, start}
var motion_on := true
var busy := 0
var pages_loaded := 0
var focus := -1
var focus_id := ""
var hover := -1
var caret := 0
var scroll := 0.0                # the first row shown, where it is going
var scroll_shown := 0.0          # and where it is now: it glides there
var dropdown := {}               # an open select's options: {item, options, index}
var held := {}                   # UI-21: what a tag with a state of its own holds now, by key (layout.gd)
var focus_key := ""              # the key of the item with the focus, and the cell under the mouse: a
var pointer := Vector2i(-1, -1)  # tooltip's tip shows while either is on its element
var toast_due := {}              # UI-21: when each toast shown goes, by key
var play_due := {}               # and when each carousel that plays moves on
var search_due := -1
var search := {}
var textures := {}
var image_sizes := {}
var images_asked := {}
var streams := {}
var streams_read := {}
var stream_bytes := {}           # in a browser: what a stream has said so far, by its url
var dialog: FileDialog = null
var dialog_key := ""
var colors := {}
var palette := {}
var base_tokens := {}             # the colours it was started with; a page's ui:theme goes over them (UI-21)
var spinning := false             # a loading mark is on the screen: it is drawn again as it turns                 # the design tokens' colours, by name (a chart's bars use them)
const SPINNER := "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

# the play protocol
var inbox: Array = []
var inbox_lock := Mutex.new()
var reader: Thread = null
var pending := {}
var settle_frames := 0
var ended := false
var shot := ""                   # --shot=file.png: the window's picture once the page has settled, then quit
var shot_frames := 0

# UI-22: the package's server, started by the TUI: {pid, stdio, stderr} while it runs
const SERVER_READY := "QUANTUM-SERVER "
const SERVER_ERROR := "QUANTUM-ERROR "
var server := {}
var server_reader: Thread = null
var server_title := ""
var server_starting := false

# UI-22: in a browser, what the browser does for the TUI (web.gd); null elsewhere
var web = null


# -- starting -----------------------------------------------------------------

func _ready() -> void:
	var tokens := {}
	var url_given := false
	for arg in OS.get_cmdline_user_args():
		var k := arg.get_slice("=", 0)
		var v := arg.substr(k.length() + 1)
		match k:
			"--url":
				base_url = v.rstrip("/")
				url_given = true
			"--page":
				path = v if v.begins_with("/") else "/" + v
			"--play":
				play = true
			"--cols":
				cols = max(20, v.to_int())
			"--rows":
				rows = max(8, v.to_int())
			"--font-size":
				font_size = max(8, v.to_int())
			"--tokens":
				var parsed = JSON.parse_string(v)
				if parsed is Dictionary:
					tokens = parsed
			"--motion":
				motion_on = v != "off"
			"--shot":
				shot = v
	if OS.has_feature("web"):
		# in a browser, on a page of the application's server: the server is the page's origin
		web = Web.new(self)
		base_url = web.origin()
		path = web.first_page()
	var package := "" if url_given or web != null else _package_dir()
	if package != "":
		var conf = JSON.parse_string(FileAccess.get_file_as_string(package.path_join("package.json")))
		if conf is Dictionary and conf.get("tokens") is Dictionary and tokens.is_empty():
			tokens = conf["tokens"]
	elif not url_given and web == null and ProjectSettings.has_setting("quantum/server"):
		# a hosted application's client (`quantum package --server`, Phase 6): its server is that address
		base_url = str(ProjectSettings.get_setting("quantum/server")).rstrip("/")
		var said = JSON.parse_string(str(ProjectSettings.get_setting("quantum/tokens", "{}")))
		if said is Dictionary and tokens.is_empty():
			tokens = said
	base_tokens = tokens
	_theme(tokens)
	var file := FontFile.new()
	if OS.has_feature("template"):
		# exported (a package, UI-22): the font is an imported resource in the pack
		var loaded = load("res://DejaVuSansMono.ttf")
		font = loaded if loaded is Font else ThemeDB.fallback_font
	elif file.load_dynamic_font("res://DejaVuSansMono.ttf") == OK:
		font = file
	else:
		font = ThemeDB.fallback_font
	var heavy := FontVariation.new()
	heavy.base_font = font
	heavy.variation_embolden = 0.7
	bold_font = heavy
	if DisplayServer.get_name() != "headless":
		var w := font.get_char_size("M".unicode_at(0), font_size).x
		var h := font.get_height(font_size)
		if w > 0 and h > 0:
			cell = Vector2(ceil(w), ceil(h))
		if web == null:
			get_window().size = Vector2i(int(cell.x * cols), int(cell.y * (rows + 2)))
			get_window().min_size = Vector2i(int(cell.x * 40), int(cell.y * 12))
		else:
			_on_resized.call_deferred()          # the browser's window is the size: as many cells as fit
		if not play:
			resized.connect(_on_resized)
	if play:
		reader = Thread.new()
		reader.start(_read_stdin)
	set_anchors_preset(Control.PRESET_FULL_RECT)
	focus_mode = Control.FOCUS_ALL
	mouse_filter = Control.MOUSE_FILTER_STOP
	grab_focus()
	if package != "":
		_start_server(package)
	else:
		load_page(path)


# -- the package's server (UI-22) ---------------------------------------------

func _package_dir() -> String:
	# an exported TUI with the package's server folder beside it (in a Mac's .app, in its Resources)
	if not OS.has_feature("template"):
		return ""
	var here := OS.get_executable_path().get_base_dir()
	for dir in [here.path_join("server"), here.path_join("../Resources/server")]:
		if FileAccess.file_exists(dir.path_join("package.json")):
			return dir.simplify_path()
	return ""


func _start_server(dir: String) -> void:
	var conf = JSON.parse_string(FileAccess.get_file_as_string(dir.path_join("package.json")))
	if not (conf is Dictionary):
		_server_failed("server/package.json cannot be read")
		return
	server_title = str(conf.get("title", ""))
	if path == "/" and str(conf.get("page", "")) != "":
		path = str(conf["page"])
	var args := PackedStringArray()
	for a in conf.get("args", []):
		args.append(str(a).replace("{server}", dir))
	busy += 1                                   # the play protocol waits for the first page, as a person does
	server_starting = true
	get_window().title = "Starting %s — Quantum" % server_title
	server = OS.execute_with_pipe(dir.path_join(str(conf.get("python", ""))), args)
	if server.is_empty():
		_server_failed("the package's Python did not start (%s)" % dir.path_join(str(conf.get("python", ""))))
		return
	server_reader = Thread.new()
	server_reader.start(_read_server)


func _read_server() -> void:
	# on its own thread: the server's first line says where it is, or what went wrong
	var pipe: FileAccess = server["stdio"]
	while true:
		var line := pipe.get_line()
		if line.begins_with(SERVER_READY):
			call_deferred("_server_ready", line.substr(SERVER_READY.length()).strip_edges())
			return
		if line.begins_with(SERVER_ERROR):
			call_deferred("_server_failed", line.substr(SERVER_ERROR.length()).strip_edges())
			return
		if line == "" and pipe.get_error() != OK:
			call_deferred("_server_failed", "the server stopped before it started")
			return


func _server_started() -> void:
	if server_starting:
		server_starting = false
		busy -= 1


func _server_ready(url: String) -> void:
	_server_started()
	base_url = url.rstrip("/")
	load_page(path)


func _server_failed(reason: String) -> void:
	_server_started()
	page = {"title": server_title, "flash": "%s could not start: %s" % [server_title, reason],
			"flashType": "error", "flashShown": false, "view": []}
	get_window().title = "%s — Quantum" % server_title
	relayout()
	pages_loaded += 1
	queue_redraw()


func _stop_server() -> void:
	# its input ends and it shuts down; one that does not within a second is stopped
	if server.is_empty():
		return
	var pid := int(server["pid"])
	(server["stdio"] as FileAccess).close()
	for i in 50:
		if not OS.is_process_running(pid):
			break
		OS.delay_msec(20)
	if OS.is_process_running(pid):
		OS.kill(pid)
	if server_reader != null:
		server_reader.wait_to_finish()
		server_reader = null
	server = {}


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST or what == NOTIFICATION_EXIT_TREE:
		_stop_server()


func _theme(tokens: Dictionary) -> void:
	# the browser's design tokens (ui_html_templates' --q-*), on a terminal's dark ground
	var t := {"primary": "#3b82f6", "secondary": "#64748b", "success": "#22c55e", "danger": "#ef4444",
			  "warning": "#f59e0b", "info": "#06b6d4"}
	for k in tokens:
		t[k] = tokens[k]
	palette = t
	var bg := Color("#0f172a")
	var primary := Color(t["primary"])
	var danger := Color(t["danger"])
	var success := Color(t["success"])
	colors = {
		"bg": bg, "fg": Color("#e2e8f0"), "muted": Color(t["secondary"]).lightened(0.35),
		"border": Color("#334155"), "title": Color("#e2e8f0"), "bar": Color("#1e293b"),
		"accent": primary, "link": primary.lightened(0.25), "bold": Color("#f8fafc"),
		"button": Color("#1e293b"), "button_primary": primary, "button_danger": danger,
		"field": Color("#1e293b"), "field_error": danger.darkened(0.6), "error": danger.lightened(0.2),
		"flash": success.darkened(0.55), "flash_fg": success.lightened(0.45),
		"flash_error": danger.darkened(0.55), "flash_error_fg": danger.lightened(0.45),
		"badge": Color(t["info"]).darkened(0.35), "tab": Color("#1e293b"), "tab_open": primary,
		"focus": Color(t["warning"]), "hover": Color("#ffffff", 0.08), "placeholder": Color(t["secondary"]),
		"unsupported": Color(t["warning"]),
		# UI-21: what is drawn over the page (a modal, a toast, a dropdown's options), and a tooltip's tip
		"layer": Color("#1a2540"), "tip": Color("#e2e8f0"), "tip_fg": bg,
		# a calendar's day that cannot be picked
		"dim": Color(t["secondary"]).lerp(bg, 0.45),
	}


func _on_resized() -> void:
	var c := int(size.x / cell.x)
	var r := int(size.y / cell.y) - 2
	if c != cols or r != rows:
		cols = max(20, c)
		rows = max(4, r)
		relayout()


# -- talking to the server ----------------------------------------------------

func _origin() -> Dictionary:
	var url := base_url
	var tls := url.begins_with("https://")
	var rest := url.substr(8 if tls else 7)
	var host := rest.get_slice("/", 0)
	var port := 443 if tls else 80
	if ":" in host:
		port = host.get_slice(":", 1).to_int()
		host = host.get_slice(":", 0)
	return {"host": host, "port": port, "tls": tls}


func _cookie_header() -> String:
	var parts: Array = []
	for name in cookies:
		parts.append("%s=%s" % [name, cookies[name]])
	return "; ".join(parts)


func _keep_cookies(headers: PackedStringArray) -> void:
	for line in headers:
		if not line.to_lower().begins_with("set-cookie:"):
			continue
		var value := line.substr(11).strip_edges()
		var pair := value.get_slice(";", 0)
		var name := pair.get_slice("=", 0).strip_edges()
		var content := pair.substr(name.length() + 1).strip_edges() if "=" in pair else ""
		var lower := value.to_lower()
		if content == "" or "max-age=0" in lower or "expires=thu, 01 jan 1970" in lower:
			cookies.erase(name)
		else:
			cookies[name] = content


func http(method: int, target: String, body: PackedByteArray, content_type: String = "",
		accept: String = VIEW) -> Dictionary:
	# One request to the application's server: {code, headers, body}; code 0 when it could not be asked.
	if web != null:
		# in a browser: its fetch, with its cookies, its redirects followed ({url}: where they ended)
		return await web.request("POST" if method == HTTPClient.METHOD_POST else "GET", base_url + target, body,
								 content_type, accept, base_url + path)
	var o := _origin()
	var client := HTTPClient.new()
	var error := client.connect_to_host(o["host"], o["port"], TLSOptions.client() if o["tls"] else null)
	if error != OK:
		return {"code": 0, "headers": PackedStringArray(), "body": PackedByteArray()}
	while client.get_status() in [HTTPClient.STATUS_RESOLVING, HTTPClient.STATUS_CONNECTING]:
		client.poll()
		await get_tree().process_frame
	if client.get_status() != HTTPClient.STATUS_CONNECTED:
		return {"code": 0, "headers": PackedStringArray(), "body": PackedByteArray()}
	var headers := PackedStringArray(["Accept: " + accept, "Referer: " + base_url + path, "User-Agent: Quantum-TUI"])
	if not cookies.is_empty():
		headers.append("Cookie: " + _cookie_header())
	if content_type != "":
		headers.append("Content-Type: " + content_type)
	client.request_raw(method, target, headers, body)
	while client.get_status() == HTTPClient.STATUS_REQUESTING:
		client.poll()
		await get_tree().process_frame
	var answer := {"code": 0, "headers": PackedStringArray(), "body": PackedByteArray()}
	if client.has_response():
		answer["code"] = client.get_response_code()
		answer["headers"] = client.get_response_headers()
		var out := PackedByteArray()
		while client.get_status() == HTTPClient.STATUS_BODY:
			client.poll()
			var chunk := client.read_response_body_chunk()
			if chunk.size() == 0:
				await get_tree().process_frame
			else:
				out.append_array(chunk)
		answer["body"] = out
	client.close()
	_keep_cookies(answer["headers"])
	return answer


static func header(headers: PackedStringArray, name: String) -> String:
	var wanted := name.to_lower() + ":"
	for line in headers:
		if line.to_lower().begins_with(wanted):
			return line.substr(wanted.length()).strip_edges()
	return ""


func _target(location: String) -> String:
	# A redirect's Location as a path of this server.
	if location.begins_with("http://") or location.begins_with("https://"):
		var rest := location.substr(location.find("//") + 2)
		var at := rest.find("/")
		return "/" if at < 0 else rest.substr(at)
	if location.begins_with("/"):
		return location
	var here := path.get_slice("?", 0)
	return here.substr(0, here.rfind("/") + 1) + location


static func form_body(data: Dictionary) -> String:
	var parts: Array = []
	for k in data:
		parts.append(str(k).uri_encode() + "=" + str(data[k]).uri_encode())
	return "&".join(parts)


func _multipart(data: Dictionary, files: Dictionary) -> Array:
	var boundary := "----QuantumTUI%d" % (randi() % 1000000000)
	var body := PackedByteArray()
	for k in data:
		body.append_array(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"
						   % [boundary, k, str(data[k])]).to_utf8_buffer())
	for k in files:
		# a file of this machine by its path, or in a browser the one its picker read, {name, bytes}
		var file_path: String = files[k]["name"] if files[k] is Dictionary else files[k]
		var bytes: PackedByteArray = files[k]["bytes"] if files[k] is Dictionary else FileAccess.get_file_as_bytes(file_path)
		body.append_array(("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n"
						   % [boundary, k, file_path.get_file(), _mime(file_path)]).to_utf8_buffer())
		body.append_array(bytes)
		body.append_array("\r\n".to_utf8_buffer())
	body.append_array(("--%s--\r\n" % boundary).to_utf8_buffer())
	return [body, "multipart/form-data; boundary=" + boundary]


static func _mime(file_path: String) -> String:
	match file_path.get_extension().to_lower():
		"png": return "image/png"
		"jpg", "jpeg": return "image/jpeg"
		"gif": return "image/gif"
		"webp": return "image/webp"
		"svg": return "image/svg+xml"
		"pdf": return "application/pdf"
		"txt", "md": return "text/plain"
		"csv": return "text/csv"
		"json": return "application/json"
	return "application/octet-stream"


func fetch(method: String, target: String, data: Dictionary = {}, files: Dictionary = {}) -> Dictionary:
	# A page: the view tree the server answers, after its redirects; an error page as a page that says so.
	var verb := HTTPClient.METHOD_POST if method == "POST" else HTTPClient.METHOD_GET
	var body := PackedByteArray()
	var content_type := ""
	if verb == HTTPClient.METHOD_POST:
		if files.is_empty():
			body = form_body(data).to_utf8_buffer()
			content_type = "application/x-www-form-urlencoded"
		else:
			var made := _multipart(data, files)
			body = made[0]
			content_type = made[1]
	var answer := {}
	for hop in 10:
		answer = await http(verb, target, body, content_type)
		if int(answer["code"]) in [301, 302, 303, 307, 308]:
			target = _target(header(answer["headers"], "Location"))
			if int(answer["code"]) in [301, 302, 303]:
				verb = HTTPClient.METHOD_GET
				body = PackedByteArray()
				content_type = ""
			continue
		break
	path = _target(str(answer["url"])) if str(answer.get("url", "")) != "" else target
	var code := int(answer["code"])
	if header(answer["headers"], "Content-Type").begins_with(VIEW):
		var parsed = JSON.parse_string(answer["body"].get_string_from_utf8())
		if parsed is Dictionary:
			return parsed
	var reason := "the server did not answer" if code == 0 else "the server answered %d" % code
	return {"title": str(code), "flash": reason, "flashType": "error", "flashShown": false, "view": []}


func load_page(target: String, method: String = "GET", data: Dictionary = {}, files: Dictionary = {},
		keep_focus := "") -> void:
	busy += 1
	var answer := await fetch(method, target, data, files)
	page = answer
	# UI-21: a page's ui:theme gives its colours; the TUI's own (the browser's defaults) otherwise
	var page_tokens: Dictionary = answer.get("tokens", {}) if answer.get("tokens") is Dictionary else {}
	_theme(base_tokens.merged(page_tokens, true))
	state = {}
	tabs = {}
	tabs_opened = {}
	dropdown = {}
	held = {}                    # UI-21: a page shown again opens as it says (a modal closed opens again)
	toast_due = {}
	play_due = {}
	focus = -1
	focus_id = ""
	focus_key = ""
	scroll = 0.0
	scroll_shown = 0.0
	motion_on = bool(page.get("motion", true)) and motion_on
	get_window().title = str(page.get("title", "")) + " — Quantum"
	relayout()
	motions = lay.motions.duplicate(true)
	running = []
	var now := Time.get_ticks_msec()
	for r in lay.regions:
		running.append({"region": r, "start": now})
	if keep_focus != "":
		# UI-12: the field searched with keeps the focus, its cursor at the end
		for i in lay.items.size():
			var it: Dictionary = lay.items[i]
			if it.get("bind", "") == keep_focus and it.has("search"):
				_set_focus(i)
				caret = str(it.get("value", "")).length()
				break
	pages_loaded += 1
	busy -= 1
	_after_layout()
	queue_redraw()


func _after_layout() -> void:
	# what the page shows that comes later: its images and its streams
	for image in lay.images:
		var src: String = image["src"]
		if src != "" and not images_asked.has(src):
			images_asked[src] = true
			_load_image(src)
	for it in lay.items:
		if it["kind"] == "stream" and str(it.get("url", "")) != "" and not streams_read.has(it["url"]):
			streams_read[it["url"]] = true
			_read_stream(str(it["url"]))


func _load_image(src: String) -> void:
	var target := src if src.begins_with("/") else _target(src)
	if src.begins_with("http://") or src.begins_with("https://") or src.begins_with("data:"):
		return       # another site's picture is the browser's to fetch; the TUI shows its alt
	busy += 1
	var answer := await http(HTTPClient.METHOD_GET, target, PackedByteArray(), "", "image/*")
	busy -= 1
	queue_redraw()
	if int(answer["code"]) != 200:
		return
	var image := Image.new()
	var kind := header(answer["headers"], "Content-Type")
	var bytes: PackedByteArray = answer["body"]
	var error := ERR_FILE_UNRECOGNIZED
	if "png" in kind:
		error = image.load_png_from_buffer(bytes)
	elif "jpeg" in kind or "jpg" in kind:
		error = image.load_jpg_from_buffer(bytes)
	elif "webp" in kind:
		error = image.load_webp_from_buffer(bytes)
	elif "svg" in kind:
		error = image.load_svg_from_buffer(bytes)
	if error != OK:
		return
	textures[src] = ImageTexture.create_from_image(image)
	image_sizes[src] = Vector2i(clamp(int(ceil(image.get_width() / cell.x)), 2, 48),
								clamp(int(ceil(image.get_height() / cell.y)), 1, 14))
	relayout()


func _read_stream(url: String) -> void:
	# IA-7: the answer as it is written, read from /_stream/<token> as the browser reads it
	if web != null:
		busy += 1                                # until its head, as below
		stream_bytes[url] = PackedByteArray()
		web.stream(url)
		return
	var o := _origin()
	var client := HTTPClient.new()
	if client.connect_to_host(o["host"], o["port"], TLSOptions.client() if o["tls"] else null) != OK:
		return
	busy += 1
	while client.get_status() in [HTTPClient.STATUS_RESOLVING, HTTPClient.STATUS_CONNECTING]:
		client.poll()
		await get_tree().process_frame
	var headers := PackedStringArray(["Accept: text/plain"])
	if not cookies.is_empty():
		headers.append("Cookie: " + _cookie_header())
	client.request(HTTPClient.METHOD_GET, url, headers)
	while client.get_status() == HTTPClient.STATUS_REQUESTING:
		client.poll()
		await get_tree().process_frame
	busy -= 1
	queue_redraw()
	if not client.has_response() or client.get_response_code() != 200:
		streams[url] = "This answer is no longer available."
		relayout()
		return
	var text := PackedByteArray()
	while client.get_status() == HTTPClient.STATUS_BODY:
		client.poll()
		var chunk := client.read_response_body_chunk()
		if chunk.size() == 0:
			await get_tree().process_frame
			continue
		text.append_array(chunk)
		_stream_shows(url, text)
	client.close()


func _stream_shows(url: String, text: PackedByteArray) -> void:
	# a NUL byte and "ERROR:" (llm_stream.ERROR_MARK): what follows is why the answer stopped
	var mark := text.find(0)
	if mark >= 0:
		streams[url] = text.slice(0, mark).get_string_from_utf8() + "\n" + \
			text.slice(mark + 7).get_string_from_utf8()
	else:
		streams[url] = text.get_string_from_utf8()
	relayout()


func _web_stream(url: String, kind: String, data: Variant) -> void:
	# in a browser (web.gd): the stream's head, then each part as it comes
	match kind:
		"head":
			busy -= 1
			queue_redraw()
			if int(data) != 200:
				streams[url] = "This answer is no longer available."
				relayout()
		"chunk":
			var text: PackedByteArray = stream_bytes.get(url, PackedByteArray())
			text.append_array(data)
			stream_bytes[url] = text
			_stream_shows(url, text)
		"end":
			stream_bytes.erase(url)


# -- laying out ---------------------------------------------------------------

func relayout() -> void:
	lay.state = state
	lay.tabs = tabs
	lay.held = held
	lay.pointer = pointer
	lay.focus_key = focus_key
	lay.view_top = int(round(scroll))
	lay.view_rows = rows
	lay.motion_on = motion_on
	lay.streams = streams
	lay.textures = image_sizes
	var flash := ""
	if str(page.get("flash", "")) != "" and not bool(page.get("flashShown", false)):     # UI-16: once
		flash = str(page["flash"])
	lay.run(page.get("view", []), cols, flash, str(page.get("flashType", "")) == "error")
	focus = -1
	if focus_id != "":
		for i in lay.items.size():
			if _id_of(lay.items[i]) == focus_id:
				focus = i
	_clamp_scroll()
	queue_redraw()


static func _id_of(it: Dictionary) -> String:
	# a radio's options share their key, and so do a carousel's or a stepper's controls and a calendar's arrows
	# and days (UI-21)
	var kind := str(it.get("kind", ""))
	var which := ""
	if kind == "radio":
		which = str(it.get("value", ""))
	elif kind == "day":
		which = str(it.get("date", ""))
	elif kind in ["carousel", "stepper", "step", "month"]:
		which = str(it.get("label", ""))
	return "%s|%s|%s" % [it.get("key", ""), kind, which]


func _clamp_scroll() -> void:
	scroll = clamp(scroll, 0.0, max(0.0, float(lay.height - rows)))


func _visible_rows() -> int:
	return rows


# -- what the user does -------------------------------------------------------

func _reacts(it: Dictionary) -> bool:
	return it.get("kind", "") != "stream" and it.get("react", true)


func _set_focus(i: int) -> void:
	focus = i
	focus_id = _id_of(lay.items[i]) if i >= 0 else ""
	focus_key = str(lay.items[i]["key"]) if i >= 0 else ""
	if i >= 0:
		var it: Dictionary = lay.items[i]
		caret = str(it.get("value", "")).length()
		# the focus is always in view
		if it["y"] < scroll:
			scroll = float(it["y"])
		elif it["y"] + it["h"] > scroll + _visible_rows():
			scroll = float(it["y"] + it["h"] - _visible_rows())
		_clamp_scroll()
	_tips_follow()
	queue_redraw()


func _tips_follow() -> void:
	# UI-21: a tooltip's tip shows while the mouse is over its element or the focus is in it
	lay.pointer = pointer
	lay.focus_key = focus_key
	if lay.tips_changed():
		relayout()


func _move_focus(step: int) -> void:
	var n: int = lay.items.size()
	if n == 0:
		return
	var i := focus
	for _k in n:
		i = (i + step + n) % n if i >= 0 else (0 if step > 0 else n - 1)
		# Tab reaches one of a calendar's days; the arrow keys move between them (UI-21)
		if _reacts(lay.items[i]) and bool(lay.items[i].get("tab", true)):
			_set_focus(i)
			return


func _item_at(cx: int, cy: int) -> int:
	# the last laid out first: what is drawn over the page (UI-21) takes the click
	for i in range(lay.items.size() - 1, -1, -1):
		var it: Dictionary = lay.items[i]
		if _reacts(it) and cx >= it["x"] and cx < it["x"] + max(1, it["w"]) and cy >= it["y"] and cy < it["y"] + max(1, it["h"]):
			return i
	return -1


func _cell_at(pos: Vector2) -> Vector2i:
	# the content's cell under a point of the window (the title bar is the first row)
	return Vector2i(int(pos.x / cell.x), int(pos.y / cell.y) - 1 + int(round(scroll_shown)))


func _value(it: Dictionary) -> String:
	var kept: Dictionary = state.get(it["key"], {})
	return str(kept.get("value", it.get("value", "")))


func _set_value(it: Dictionary, value: String) -> void:
	var kept: Dictionary = state.get(it["key"], {})
	kept["value"] = value
	state[it["key"]] = kept


func _form_has_button(form: int) -> bool:
	for it in lay.items:
		if it.get("form", -1) == form and it["kind"] == "button":
			return true
	return false


func submit(form: int) -> void:
	# A form's action with what the user left in it, as a browser posts it: a checked box "on", an unchecked
	# one nothing, the chosen option of a radio, a file chosen in the dialog.
	var f: Dictionary = lay.forms[form]
	var event: Dictionary = f.get("event", {})
	if event.is_empty():
		return
	var data := {"action": str(event.get("action", ""))}
	for k in event.get("fields", {}):
		data[k] = str(event["fields"][k])
	var files := {}
	for i in f["items"]:
		var it: Dictionary = lay.items[i]
		var bind := str(it.get("bind", ""))
		if bind == "":
			continue
		match it["kind"]:
			"input", "textarea", "select":
				data[bind] = _value(it)
			"checkbox", "switch":
				if it.get("checked", false):
					data[bind] = "on"
			"radio":
				if it.get("checked", false):
					data[bind] = str(it.get("value", ""))
			"calendar":
				data[bind] = _value(it)              # UI-21: the day picked, YYYY-MM-DD (empty: none)
			"file":
				var kept: Dictionary = state.get(it["key"], {})
				var chosen := str(kept.get("file", ""))
				if chosen != "":
					files[bind] = {"name": chosen, "bytes": kept["bytes"]} if kept.has("bytes") else chosen
	load_page(path.get_slice("#", 0), "POST", data, files)


func activate(i: int) -> void:
	if i < 0 or i >= lay.items.size():
		return
	var it: Dictionary = lay.items[i]
	_set_focus(i)
	match it["kind"]:
		"link", "button":
			if it["kind"] == "link" and not (it.has("event") and not it["event"].is_empty()):
				load_page(str(it.get("to", "/")))
			elif it.has("event") and not it["event"].is_empty():
				var data := {"action": str(it["event"].get("action", ""))}
				for k in it["event"].get("fields", {}):
					data[k] = str(it["event"]["fields"][k])
				load_page(path, "POST", data)
			elif int(it.get("form", -1)) >= 0:
				submit(int(it["form"]))
		"tab":
			_open_tab(it)
		"checkbox", "switch":
			var kept: Dictionary = state.get(it["key"], {})
			kept["checked"] = not bool(it.get("checked", false))
			state[it["key"]] = kept
			relayout()
			_changed(it)
		"radio":
			_set_value(it, str(it.get("value", "")))
			relayout()
			_changed(it)
		"select":
			var options: Array = it.get("options", [])
			var index := 0
			for k in options.size():
				if str(options[k][1]) == _value(it):
					index = k
			dropdown = {"item": i, "options": options, "index": index}
			queue_redraw()
		"file":
			_choose_file(it)
		"input", "textarea":
			caret = _value(it).length()
		"day":
			# UI-21: a calendar's day picked is its field's value, which its form sends when its button is clicked
			_set_value(it, str(it["date"]))
			relayout()
		"fold", "dropdown", "close", "carousel", "stepper", "step", "month":
			_change_held(it)
	queue_redraw()


func _change_held(it: Dictionary) -> void:
	# UI-21: an item of a tag with a state of its own carries what it changes it to (layout.gd)
	var key := str(it["key"])
	match str(it["kind"]):
		"fold":
			_hold(key, "open", not bool(it.get("open", false)))
		"dropdown":
			_close_menus(key)
			_hold(key, "open", not bool(it.get("open", false)))
		"close":
			_hold(key, "closed" if str(it.get("of", "")) == "modal" else "gone", true)
		"carousel":
			_hold(key, "at", int(it["goto"]))
			play_due.erase(key)                 # moved by hand, it waits its interval again
		"stepper", "step":
			_hold(key, "at", int(it["goto"]))
			_hold(key, "done", it.get("done", []))
		"month":
			_hold(key, "month", str(it["goto"]))
	relayout()


func _hold(key: String, field: String, value: Variant) -> void:
	var kept: Dictionary = held.get(key, {})
	kept[field] = value
	held[key] = kept


func _open_menus() -> Array:
	var keys: Array = []
	for layer in lay.layers:
		if str(layer["kind"]) == "menu":
			keys.append(str(layer["key"]))
	return keys


func _close_menus(but: String = "") -> void:
	for key in _open_menus():
		if key != but:
			_hold(key, "open", false)


func _in_layer(at: Vector2i, kind: String) -> bool:
	for layer in lay.layers:
		if str(layer["kind"]) == kind and Rect2i(layer["x"], layer["y"], layer["w"], layer["h"]).has_point(at):
			return true
	return false


func _top_modal() -> Dictionary:
	var top := {}
	for layer in lay.layers:
		if str(layer["kind"]) == "modal":
			top = layer
	return top


func _escape() -> bool:
	# Esc closes an open dropdown's options, else the modal on top when it can be closed (UI-21)
	if not _open_menus().is_empty():
		_close_menus()
		relayout()
		return true
	var modal := _top_modal()
	if not modal.is_empty() and bool(modal.get("closable", false)):
		_hold(str(modal["key"]), "closed", true)
		relayout()
		return true
	return false


func _timers(now: int) -> void:
	# UI-21: a toast goes after its duration; a carousel that plays moves on after its interval, and waits
	# while the mouse is over it
	var changed := false
	for t in lay.toasts:
		var key := str(t["key"])
		if not toast_due.has(key):
			toast_due[key] = now + int(t["ms"])
		elif now >= int(toast_due[key]):
			_hold(key, "gone", true)
			changed = true
	for c in lay.autoplay:
		var key := str(c["key"])
		var over := Rect2i(c["x"], c["y"], c["w"], c["h"]).has_point(pointer)
		if over or not play_due.has(key):
			play_due[key] = now + int(c["ms"])
		elif now >= int(play_due[key]):
			play_due[key] = now + int(c["ms"])
			_hold(key, "at", int(c["next"]))
			changed = true
	if changed:
		relayout()


func _changed(it: Dictionary) -> void:
	# an editable table's cell is a form of one field: a change sends it (UI-13)
	var form := int(it.get("form", -1))
	if form >= 0 and not _form_has_button(form):
		submit(form)


func _open_tab(it: Dictionary) -> void:
	if it.get("open", false):
		return
	tabs[it["key"]] = it["label"]
	relayout()
	# UI-19: the content of a tab the user opens expands into view
	if motion_on:
		motions.append({"kind": "expand", "speed": "normal", "what": "tab:" + str(it["label"])})
		for r in lay.tab_regions:
			if r["what"] == "tab:" + str(it["label"]):
				running.append({"region": {"kind": "expand", "ms": 250, "x": r["x"], "y": r["y"], "w": r["w"],
										   "h": r["h"]}, "start": Time.get_ticks_msec()})
	queue_redraw()


func _choose_file(it: Dictionary) -> void:
	# UI-14: the TUI's own dialog, on this machine's files; in a browser, the browser's own picker
	if web != null:
		web.pick(str(it.get("accept", "")), str(it["key"]))
		return
	if dialog == null:
		dialog = FileDialog.new()
		dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
		dialog.access = FileDialog.ACCESS_FILESYSTEM
		dialog.use_native_dialog = false
		dialog.title = "Choose a file"
		dialog.file_selected.connect(_file_chosen)
		add_child(dialog)
	dialog_key = it["key"]
	var filters := PackedStringArray()
	for part in str(it.get("accept", "")).split(",", false):
		part = part.strip_edges()
		if part.begins_with("."):
			filters.append("*" + part)
		elif part == "image/*":
			filters.append("*.png, *.jpg, *.jpeg, *.gif, *.webp ; Images")
	dialog.filters = filters
	if not play:
		dialog.popup_centered_ratio(0.7)


func _file_chosen(file_path: String) -> void:
	var kept: Dictionary = state.get(dialog_key, {})
	kept["file"] = file_path
	state[dialog_key] = kept
	relayout()


func _web_picked(key: String, file_name: String, bytes: PackedByteArray) -> void:
	# in a browser: the file its picker read, kept with the field until the form is sent
	var kept: Dictionary = state.get(key, {})
	kept["file"] = file_name
	kept["bytes"] = bytes
	state[key] = kept
	relayout()


func _type(it: Dictionary, text: String) -> void:
	var value := _value(it)
	caret = clamp(caret, 0, value.length())
	value = value.substr(0, caret) + text + value.substr(caret)
	caret += text.length()
	_set_value(it, value)
	relayout()
	_typed(it)


func _typed(it: Dictionary) -> void:
	# UI-12: a search field asks for the page again after a pause
	if it.has("search"):
		search = {"bind": it["bind"], "value": _value(it)}
		search_due = Time.get_ticks_msec() + int(it["search"])


func _search_now() -> void:
	search_due = -1
	var here := path.get_slice("?", 0)
	var query := path.get_slice("?", 1) if "?" in path else ""
	var kept: Array = []
	for pair in query.split("&", false):
		var name := pair.get_slice("=", 0).uri_decode()
		if name != search["bind"] and name != "page":
			kept.append(pair)
	if str(search["value"]) != "":
		kept.append(str(search["bind"]).uri_encode() + "=" + str(search["value"]).uri_encode())
	load_page(here + ("?" + "&".join(kept) if not kept.is_empty() else ""), "GET", {}, {}, str(search["bind"]))


func _key(event: InputEventKey) -> void:
	var it: Dictionary = lay.items[focus] if focus >= 0 and focus < lay.items.size() else {}
	var kind := str(it.get("kind", ""))
	var code := event.keycode
	if not dropdown.is_empty():
		match code:
			KEY_UP:
				dropdown["index"] = max(0, int(dropdown["index"]) - 1)
			KEY_DOWN:
				dropdown["index"] = min(dropdown["options"].size() - 1, int(dropdown["index"]) + 1)
			KEY_ENTER, KEY_KP_ENTER, KEY_SPACE:
				_choose_option(int(dropdown["index"]))
			KEY_ESCAPE:
				dropdown = {}
		queue_redraw()
		return
	if code == KEY_ESCAPE and _escape():
		return
	if event.ctrl_pressed and code == KEY_Q:
		if web == null:                          # in a browser, its tab is closed by the browser
			get_tree().quit()
		return
	if code == KEY_F5:
		load_page(path)
		return
	if code == KEY_TAB:
		_move_focus(-1 if event.shift_pressed else 1)
		return
	if kind in ["input", "textarea"]:
		var value := _value(it)
		match code:
			KEY_BACKSPACE:
				if caret > 0:
					_set_value(it, value.substr(0, caret - 1) + value.substr(caret))
					caret -= 1
					relayout()
					_typed(it)
				return
			KEY_DELETE:
				if caret < value.length():
					_set_value(it, value.substr(0, caret) + value.substr(caret + 1))
					relayout()
					_typed(it)
				return
			KEY_LEFT:
				caret = max(0, caret - 1)
				queue_redraw()
				return
			KEY_RIGHT:
				caret = min(value.length(), caret + 1)
				queue_redraw()
				return
			KEY_HOME:
				caret = 0
				queue_redraw()
				return
			KEY_END:
				caret = value.length()
				queue_redraw()
				return
			KEY_ENTER, KEY_KP_ENTER:
				if kind == "textarea" and not event.ctrl_pressed:
					_type(it, "\n")
				elif int(it.get("form", -1)) >= 0:
					submit(int(it["form"]))
				return
			KEY_U:
				if event.ctrl_pressed:
					_set_value(it, "")
					caret = 0
					relayout()
					_typed(it)
					return
		if event.unicode >= 32 and not event.ctrl_pressed:
			_type(it, char(event.unicode))
		return
	match code:
		KEY_ENTER, KEY_KP_ENTER, KEY_SPACE:
			if focus >= 0:
				activate(focus)
		KEY_DOWN:
			if kind == "select":
				_step_select(it, 1)
			elif kind == "day":
				_step_day(it, 7)
			else:
				_move_focus(1)
		KEY_UP:
			if kind == "select":
				_step_select(it, -1)
			elif kind == "day":
				_step_day(it, -7)
			else:
				_move_focus(-1)
		KEY_RIGHT, KEY_LEFT:
			if kind == "radio":
				_step_radio(it, 1 if code == KEY_RIGHT else -1)
			elif kind == "day":
				_step_day(it, 1 if code == KEY_RIGHT else -1)
			else:
				_move_focus(1 if code == KEY_RIGHT else -1)
		KEY_PAGEDOWN:
			scroll += rows - 2
			_clamp_scroll()
		KEY_PAGEUP:
			scroll -= rows - 2
			_clamp_scroll()
		KEY_HOME:
			scroll = 0.0
		KEY_END:
			scroll = float(lay.height)
			_clamp_scroll()
	queue_redraw()


func _step_select(it: Dictionary, step: int) -> void:
	var options: Array = it.get("options", [])
	for k in options.size():
		if str(options[k][1]) == _value(it):
			var n: int = clamp(k + step, 0, options.size() - 1)
			_set_value(it, str(options[n][1]))
			relayout()
			_changed(it)
			return


func _step_radio(it: Dictionary, step: int) -> void:
	var group: Array = []
	for i in lay.items.size():
		if lay.items[i]["key"] == it["key"] and lay.items[i]["kind"] == "radio":
			group.append(i)
	var at := group.find(focus)
	var next: int = group[clamp(at + step, 0, group.size() - 1)]
	_set_focus(next)
	activate(next)


func _step_day(it: Dictionary, by: int) -> void:
	# UI-21: in a calendar the arrow keys move the focus a day (←→) or a week (↑↓), into the month before or after
	# past this one's ends; a day that cannot be picked is passed over. Enter picks the day.
	var key := str(it["key"])
	var rules := {}
	for other in lay.items:
		if str(other["key"]) == key and str(other["kind"]) == "calendar":
			rules = other.get("rules", {})
	var day := Layout.day_of(str(it["date"]))
	for _k in 400:
		day += by
		var date := Layout.date_of(day)
		if not Layout.day_open(rules, date):
			continue
		if date.substr(0, 7) != str(it["date"]).substr(0, 7):
			_hold(key, "month", date.substr(0, 7))
			relayout()
		for i in lay.items.size():
			var shown: Dictionary = lay.items[i]
			if str(shown["key"]) == key and str(shown["kind"]) == "day" and str(shown.get("date", "")) == date:
				_set_focus(i)
				return
		return


func _choose_option(index: int) -> void:
	var it: Dictionary = lay.items[int(dropdown["item"])]
	var options: Array = dropdown["options"]
	dropdown = {}
	if index >= 0 and index < options.size():
		_set_value(it, str(options[index][1]))
		relayout()
		_changed(it)
	queue_redraw()


func _dropdown_rect() -> Rect2i:
	var it: Dictionary = lay.items[int(dropdown["item"])]
	var widest := 6
	for o in dropdown["options"]:
		widest = max(widest, Layout.text_width(str(o[0])) + 4)
	return Rect2i(it["x"], it["y"] + 1, max(widest, it["w"]), dropdown["options"].size())


func _gui_input(event: InputEvent) -> void:
	if _handle(event):
		accept_event()


func _handle(event: InputEvent) -> bool:
	# what a key or the mouse does; whether it was this window's
	if event is InputEventKey and event.pressed:
		_key(event)
		return true
	elif event is InputEventMouseMotion:
		var at := _cell_at(event.position)
		pointer = at
		_tips_follow()
		var over := _item_at(at.x, at.y)
		if over != hover:
			hover = over
			# a tooltip's element takes the focus for its tip, but a click does nothing on it
			var acts := over >= 0 and str(lay.items[over]["kind"]) != "tooltip"
			mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND if acts else Control.CURSOR_ARROW
			queue_redraw()
		return true
	elif event is InputEventMouseButton and event.pressed:
		match event.button_index:
			MOUSE_BUTTON_WHEEL_DOWN:
				scroll += 3
				_clamp_scroll()
			MOUSE_BUTTON_WHEEL_UP:
				scroll -= 3
				_clamp_scroll()
			MOUSE_BUTTON_LEFT:
				var at := _cell_at(event.position)
				var i := _item_at(at.x, at.y)
				if not dropdown.is_empty():
					var r := _dropdown_rect()
					if r.has_point(at):
						_choose_option(at.y - r.position.y)
					else:
						dropdown = {}
				elif not _open_menus().is_empty() and not _in_layer(at, "menu") \
						and not (i >= 0 and str(lay.items[i]["kind"]) == "dropdown"):
					# a click away from an open dropdown's options closes them (UI-21)
					_close_menus()
					relayout()
				elif i >= 0:
					activate(i)
				pointer = at              # the mouse is where it clicked: a tooltip's tip follows it
				_tips_follow()
		queue_redraw()
		return true
	return false


# -- the frame ----------------------------------------------------------------

func _process(_delta: float) -> void:
	var moving := false
	if abs(scroll_shown - scroll) > 0.01:
		scroll_shown = lerp(scroll_shown, scroll, 0.35) if abs(scroll_shown - scroll) > 0.05 else scroll
		moving = true
	var now := Time.get_ticks_msec()
	if not running.is_empty():
		var still: Array = []
		for m in running:
			if now - int(m["start"]) < int(m["region"].get("ms", 250)):
				still.append(m)
		running = still
		moving = true
	if search_due > 0 and now >= search_due:
		_search_now()
	if not lay.toasts.is_empty() or not lay.autoplay.is_empty():
		_timers(now)
	if lay.follows_view and int(round(scroll)) != lay.view_top:
		relayout()                 # UI-21: a modal, a toast stay on the screen as the page scrolls
	if spinning and not play:
		moving = true
	if moving:
		queue_redraw()
	if play or web != null:
		_serve_play()
	elif shot != "":
		shot_frames = shot_frames + 1 if _settled() and running.is_empty() else 0
		if shot_frames == 10:
			get_viewport().get_texture().get_image().save_png(shot)
			get_tree().quit()


static func _eased(t: float) -> float:
	return 1.0 - pow(1.0 - clamp(t, 0.0, 1.0), 3.0)


func _motion_at(x: int, y: int, now: int) -> Array:
	# [alpha, offset in cells, shown]: what the motions running do to a cell (UI-19)
	var alpha := 1.0
	var offset := 0.0
	for m in running:
		var r: Dictionary = m["region"]
		if x < r["x"] or x >= r["x"] + r["w"] or y < r["y"] or y >= r["y"] + r["h"]:
			continue
		var t := _eased(float(now - int(m["start"])) / float(r.get("ms", 250)))
		match r["kind"]:
			"fade":
				alpha = min(alpha, t)
			"slide":
				alpha = min(alpha, t)
				offset += (1.0 - t) * 4.0
			"expand":
				alpha = min(alpha, t)
				if y - r["y"] >= int(ceil(r["h"] * t)):
					return [0.0, 0.0, false]
	return [alpha, offset, true]


func _style_colors(style: String) -> Array:
	# [foreground, background or null] of a cell's style
	match style:
		"muted", "placeholder":
			return [colors["muted"] if style == "muted" else colors["placeholder"], null]
		"bold":
			return [colors["bold"], null]
		"border":
			return [colors["border"], null]
		"title":
			return [colors["title"], null]
		"link":
			return [colors["link"], null]
		"accent":
			return [colors["accent"], null]
		"error":
			return [colors["error"], null]
		"unsupported":
			return [colors["unsupported"], null]
		"button":
			return [colors["fg"], colors["button"]]
		"button_primary":
			return [Color.WHITE, colors["button_primary"]]
		"button_danger":
			return [Color.WHITE, colors["button_danger"]]
		"button_disabled":
			return [colors["muted"], colors["button"]]
		"field":
			return [colors["fg"], colors["field"]]
		"field_error":
			return [colors["fg"], colors["field_error"]]
		"flash":
			return [colors["flash_fg"], colors["flash"]]
		"flash_error":
			return [colors["flash_error_fg"], colors["flash_error"]]
		"badge":
			return [Color.WHITE, colors["badge"]]
		"tab":
			return [colors["muted"], colors["tab"]]
		"tab_open":
			return [Color.WHITE, colors["tab_open"]]
		"code":
			return [colors["fg"], colors["field"]]
		"spinner":
			return [colors["accent"], null]
		"tip":
			return [colors["tip_fg"], colors["tip"]]
		"today":
			return [colors["accent"], null]
		"dim":
			return [colors["dim"], null]
	if style.begins_with("fill:"):
		# UI-21: a chart's bar, an avatar's status: a design token's colour, or the page's own
		var name := style.substr(5)
		if palette.has(name):
			return [Color(palette[name]), null]
		return [Color.from_string(name, colors["accent"]), null]
	return [colors["fg"], null]


func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), colors["bg"])
	var ascent := font.get_ascent(font_size)
	var now := Time.get_ticks_msec()
	spinning = false
	# the title bar
	draw_rect(Rect2(0, 0, size.x, cell.y), colors["bar"])
	draw_string(bold_font, Vector2(cell.x, ascent), " " + str(page.get("title", "")), HORIZONTAL_ALIGNMENT_LEFT, -1,
				font_size, colors["bold"])
	var where := path if busy == 0 else path + "  …"
	draw_string(font, Vector2(size.x - cell.x * (Layout.text_width(where) + 2), ascent), where,
				HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, colors["muted"])
	# UI-21: the boxes drawn over the page on a ground of their own; under an open modal, the page dimmed
	var content := Rect2(0, cell.y, size.x, cell.y * rows)
	var modal_at := -1
	for k in lay.layers.size():
		if str(lay.layers[k]["kind"]) == "modal":
			modal_at = k
	var lit: Array = []                           # the modal and what is drawn over it: not dimmed
	for k in range(max(0, modal_at), lay.layers.size() if modal_at >= 0 else 0):
		var m: Dictionary = lay.layers[k]
		lit.append(Rect2i(m["x"], m["y"], m["w"], m["h"]))
	for k in lay.layers.size():
		var layer: Dictionary = lay.layers[k]
		if str(layer["kind"]) == "tip":
			continue                              # its cells have a ground of their own
		var ground: Color = colors["layer"]
		if k < modal_at:
			ground = ground.lerp(colors["bg"], 0.6)
		# inside its frame, whose lines run through the middle of the border's cells
		var box := Rect2(cell.x * (layer["x"] + 0.5), cell.y * (1.5 + layer["y"]) - scroll_shown * cell.y,
						 cell.x * (layer["w"] - 1), cell.y * (layer["h"] - 1)).intersection(content)
		if box.has_area():
			draw_rect(box, ground)
	# the content, glided to where it scrolls
	var first := int(floor(scroll_shown))
	var shift := (scroll_shown - first) * cell.y
	for r in range(first, min(lay.grid.size(), first + rows + 1)):
		var row: Array = lay.grid[r]
		var top := cell.y * (1 + r - first) - shift
		if top < cell.y * 0.5 or top > cell.y * (rows + 1):
			continue
		for x in row.size():
			var c: Array = row[x]
			var m := _motion_at(x, r, now) if not running.is_empty() else [1.0, 0.0, true]
			if not m[2]:
				continue
			var alpha := float(m[0])
			if modal_at >= 0 and not _lit(lit, Vector2i(x, r)):
				alpha *= 0.4
			var styled := _style_colors(str(c[1]))
			var left: float = cell.x * (x + float(m[1]))
			if styled[1] != null:
				var bg: Color = styled[1]
				bg.a *= alpha
				draw_rect(Rect2(left, top, cell.x + 0.5, cell.y), bg)
			if str(c[0]) != " " and str(c[0]) != "":
				var fg: Color = styled[0]
				fg.a *= alpha
				var ch := str(c[0])
				if str(c[1]) == "spinner":            # UI-21: a loading mark turns
					ch = SPINNER[int(now / 100) % SPINNER.length()]
					spinning = true
				var heavy := str(c[1]) in ["bold", "title", "today"]
				draw_char(bold_font if heavy else font, Vector2(left, top + ascent), ch, font_size, fg)
	# the page's images, over their cells
	for image in lay.images:
		if textures.has(image["src"]) and not image.get("covered", false):    # UI-21: not under a layer
			var rect := Rect2(cell.x * image["x"], cell.y * (1 + image["y"]) - scroll_shown * cell.y,
							  cell.x * image["w"], cell.y * image["h"])
			var under := modal_at >= 0 and not _lit(lit, Vector2i(image["x"], image["y"]))
			draw_texture_rect(textures[image["src"]], rect, false, Color(1, 1, 1, 0.4 if under else 1.0))
	# hover and focus
	if hover >= 0 and hover < lay.items.size():
		draw_rect(_rect_of(lay.items[hover]), colors["hover"])
	if focus >= 0 and focus < lay.items.size():
		var it: Dictionary = lay.items[focus]
		draw_rect(_rect_of(it), colors["focus"], false, 1.5)
		if it["kind"] in ["input", "textarea"] and int(now / 500) % 2 == 0:
			var shown := _value(it).substr(0, caret)
			var tail := Layout.text_width(shown)
			var room: int = it["w"] - 2
			var at: int = min(tail, room)
			draw_rect(Rect2(cell.x * (it["x"] + 1 + at), cell.y * (1 + it["y"]) - scroll_shown * cell.y, 2, cell.y),
					  colors["focus"])
	# an open select's options
	if not dropdown.is_empty():
		var r := _dropdown_rect()
		var top := cell.y * (1 + r.position.y) - scroll_shown * cell.y
		draw_rect(Rect2(cell.x * r.position.x, top, cell.x * r.size.x, cell.y * r.size.y), colors["bar"])
		draw_rect(Rect2(cell.x * r.position.x, top, cell.x * r.size.x, cell.y * r.size.y), colors["border"], false, 1.0)
		for k in dropdown["options"].size():
			if k == int(dropdown["index"]):
				draw_rect(Rect2(cell.x * r.position.x, top + cell.y * k, cell.x * r.size.x, cell.y), colors["accent"])
			draw_string(font, Vector2(cell.x * (r.position.x + 1), top + cell.y * k + ascent),
						str(dropdown["options"][k][0]), HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, colors["fg"])
	# where the page is when it is longer than the screen
	if lay.height > rows:
		var track := cell.y * rows
		var knob: float = max(cell.y, track * rows / lay.height)
		var at: float = cell.y + (track - knob) * scroll_shown / max(1.0, float(lay.height - rows))
		draw_rect(Rect2(size.x - 4, at, 3, knob), colors["border"])
	# the keys that apply
	var bottom := size.y - cell.y
	draw_rect(Rect2(0, bottom, size.x, cell.y), colors["bar"])
	draw_string(font, Vector2(cell.x, bottom + ascent), status_line(), HORIZONTAL_ALIGNMENT_LEFT, -1, font_size,
				colors["muted"])


static func _lit(rects: Array, at: Vector2i) -> bool:
	for rect in rects:
		if (rect as Rect2i).has_point(at):
			return true
	return false


func _rect_of(it: Dictionary) -> Rect2:
	return Rect2(cell.x * it["x"], cell.y * (1 + it["y"]) - scroll_shown * cell.y, cell.x * max(1, it["w"]),
				 cell.y * max(1, it["h"]))


func status_line() -> String:
	if not dropdown.is_empty():
		return "↑↓ choose · Enter takes it · Esc closes"
	var kind := str(lay.items[focus]["kind"]) if focus >= 0 and focus < lay.items.size() else ""
	match kind:
		"input":
			return "type · Enter sends · Tab moves · Ctrl+U clears"
		"textarea":
			return "type · Ctrl+Enter sends · Tab moves"
		"checkbox", "switch":
			return "Space marks · Tab moves"
		"radio":
			return "←→ choose · Tab moves"
		"select":
			return "Enter opens · ↑↓ choose · Tab moves"
		"button":
			return "Enter presses · Tab moves"
		"link":
			return "Enter opens · Tab moves"
		"tab":
			return "Enter opens the tab · Tab moves"
		"file":
			return "Enter chooses a file · Tab moves"
		"fold":
			return "Enter opens or closes · Tab moves"
		"dropdown":
			return "Enter opens its options · Esc closes them · Tab moves"
		"close":
			return "Enter closes · Tab moves"
		"carousel", "stepper", "step":
			return "Enter moves to it · Tab moves"
		"month":
			return "Enter shows the month · Tab moves"
		"day":
			return "Enter picks the day · ←→↑↓ move · Tab moves"
	if not _top_modal().is_empty() and bool(_top_modal().get("closable", false)):
		return "Esc closes · Tab moves · click acts"
	return "Tab moves · click acts · wheel scrolls · F5 reloads" + ("" if web != null else " · Ctrl+Q quits")


# -- the play protocol --------------------------------------------------------

func _read_stdin() -> void:
	while true:
		var line := OS.read_string_from_stdin(1 << 20)
		inbox_lock.lock()
		inbox.append(line)
		inbox_lock.unlock()
		if line == "":
			return


func _web_inbox(line: String) -> void:
	# in a browser: a request of window.quantumTui (web.gd); an empty one is not the end of the input
	inbox_lock.lock()
	inbox.append(line if line != "" else "{}")
	inbox_lock.unlock()


func _answer(d: Dictionary) -> void:
	if web != null:
		web.answer(JSON.stringify(d))
	else:
		print("QTP " + JSON.stringify(d))


func _settled() -> bool:
	return busy == 0 and search_due < 0 and pages_loaded > 0


func _serve_play() -> void:
	if ended:
		return
	if not pending.is_empty():
		if _settled():
			settle_frames += 1
		else:
			settle_frames = 0
		var op := str(pending.get("op", ""))
		if op == "wait":
			# a text to appear, or with `gone` to go (a toast after its duration, UI-21)
			var text := "\n".join(lay.text_rows())
			var wanted := str(pending.get("text", ""))
			var gone := bool(pending.get("gone", false))
			var there := wanted in text
			if ((not there) if gone else (wanted == "" or there)) and _settled():
				pending = {}
				_answer(observation())
			elif Time.get_ticks_msec() > int(pending["deadline"]):
				var said := "%s did not %s in %ss" % [wanted, "go" if gone else "appear", str(pending.get("timeout", 15))]
				pending = {}
				_answer({"error": said})
			return
		if op == "shot":
			# the window's picture once the page has settled and nothing moves (not headless: it draws nothing)
			if settle_frames >= 10 and running.is_empty():
				var file := str(pending.get("path", ""))
				pending = {}
				if DisplayServer.get_name() == "headless":
					_answer({"error": "a shot needs a display: run the TUI with one (xvfb-run)"})
				elif web != null:
					_answer({"error": "in a browser, a shot is the page's screenshot (TuiInBrowser.shot)"})
				else:
					get_viewport().get_texture().get_image().save_png(file)
					_answer({"shot": file})
			return
		if settle_frames >= 3:
			pending = {}
			_answer(observation())
		return
	inbox_lock.lock()
	var line := ""
	var got := false
	if not inbox.is_empty():
		line = inbox.pop_front()
		got = true
	inbox_lock.unlock()
	if not got:
		return
	if line == "":
		ended = true
		get_tree().quit()
		return
	var req = JSON.parse_string(line)
	if not (req is Dictionary):
		_answer({"error": "not a request: " + line})
		return
	_serve(req)


func _push_key(name: String) -> void:
	var event := InputEventKey.new()
	var parts := name.split("+")
	var key := parts[parts.size() - 1]
	event.ctrl_pressed = "ctrl" in parts
	event.shift_pressed = "shift" in parts
	var codes := {"tab": KEY_TAB, "enter": KEY_ENTER, "space": KEY_SPACE, "up": KEY_UP, "down": KEY_DOWN,
				  "left": KEY_LEFT, "right": KEY_RIGHT, "escape": KEY_ESCAPE, "esc": KEY_ESCAPE,
				  "backspace": KEY_BACKSPACE, "delete": KEY_DELETE, "home": KEY_HOME, "end": KEY_END,
				  "pageup": KEY_PAGEUP, "pagedown": KEY_PAGEDOWN, "f5": KEY_F5}
	if codes.has(key.to_lower()):
		event.keycode = codes[key.to_lower()]
		if event.keycode == KEY_SPACE:
			event.unicode = 32
	else:
		event.keycode = OS.find_keycode_from_string(key.to_upper())
		if not event.ctrl_pressed:
			event.unicode = key.unicode_at(0)
	event.pressed = true
	_handle(event)


func _serve(req: Dictionary) -> void:
	settle_frames = 0
	match str(req.get("op", "")):
		"observe":
			_answer(observation())
			return
		"end":
			_answer({"ended": true})
			ended = true
			get_tree().quit()
			return
		"visit":
			load_page(str(req.get("path", "/")))
		"click":
			# a click of the mouse on the content's cell (x, y): scrolled into view, then clicked
			var x := int(req.get("x", 0))
			var y := int(req.get("y", 0))
			if y < scroll or y >= scroll + rows:
				scroll = float(max(0, y - rows / 2))
				_clamp_scroll()
			scroll_shown = scroll
			var event := InputEventMouseButton.new()
			event.button_index = MOUSE_BUTTON_LEFT
			event.pressed = true
			event.position = Vector2(cell.x * (x + 0.5), cell.y * (1 + y - scroll_shown + 0.5))
			_handle(event)
		"hover":
			var motion := InputEventMouseMotion.new()
			motion.position = Vector2(cell.x * (int(req.get("x", 0)) + 0.5),
									  cell.y * (1 + int(req.get("y", 0)) - scroll_shown + 0.5))
			_handle(motion)
		"wheel":
			var wheel := InputEventMouseButton.new()
			wheel.button_index = MOUSE_BUTTON_WHEEL_DOWN if int(req.get("by", 1)) > 0 else MOUSE_BUTTON_WHEEL_UP
			wheel.pressed = true
			for _k in abs(int(req.get("by", 1))):
				_handle(wheel)
		"key":
			for name in (req.get("keys", [req.get("key", "")]) as Array):
				_push_key(str(name))
		"type":
			for ch in str(req.get("text", "")):
				var event := InputEventKey.new()
				event.unicode = ch.unicode_at(0)
				event.keycode = KEY_NONE
				event.pressed = true
				_handle(event)
		"attach":
			# the file dialog of the field `bind` opened, and that file chosen in it; in a browser, its picker
			# opened, and what drives the browser chooses the file there
			for it in lay.items:
				if it["kind"] == "file" and it["bind"] == str(req.get("bind", "")):
					_choose_file(it)
					if web == null:
						dialog.file_selected.emit(str(req.get("path", "")))
		"resize":
			cols = max(20, int(req.get("cols", cols)))
			rows = max(4, int(req.get("rows", rows)))
			relayout()
		"wait":
			req["deadline"] = Time.get_ticks_msec() + int(float(req.get("timeout", 15)) * 1000)
		"shot":
			queue_redraw()
		_:
			_answer({"error": "no such request: " + str(req.get("op", ""))})
			return
	pending = req


func observation() -> Dictionary:
	var shown: Array = []
	for i in lay.items.size():
		var it: Dictionary = lay.items[i]
		var entry := {"n": i, "kind": it["kind"], "label": str(it.get("label", "")), "x": it["x"], "y": it["y"],
					  "w": it["w"], "h": it["h"], "focus": i == focus, "card": str(it.get("card", ""))}
		for k in ["bind", "to", "input_type", "search"]:
			if it.has(k):
				entry[k] = it[k]
		if it["kind"] in ["input", "textarea", "select", "radio", "calendar"]:
			entry["value"] = _value(it) if it["kind"] != "radio" else str(it.get("value", ""))
		if it["kind"] in ["checkbox", "switch", "radio"]:
			entry["checked"] = bool(it.get("checked", false))
		if it["kind"] == "select":
			var labels: Array = []
			for o in it.get("options", []):
				labels.append(str(o[0]))
			entry["options"] = labels
		if it["kind"] in ["tab", "fold", "dropdown"]:
			entry["open"] = bool(it.get("open", false))
		if it["kind"] == "calendar":           # UI-21: the month it shows; a day's date, and whether it is picked
			entry["month"] = str(it.get("month", ""))
		if it["kind"] == "day":
			entry["date"] = str(it.get("date", ""))
			entry["selected"] = bool(it.get("selected", false))
		if it["kind"] == "file":
			entry["file"] = str(state.get(it["key"], {}).get("file", ""))
		if it.has("event"):
			entry["action"] = str(it["event"].get("action", ""))
		for k in ["menu", "of"]:               # UI-21: an open dropdown's option, what a close control closes
			if it.has(k):
				entry[k] = str(it[k])
		if it.get("covered", false):           # under what is drawn over the page: it cannot be reached
			entry["covered"] = true
		shown.append(entry)
	var images: Array = []
	for image in lay.images:
		images.append({"alt": image["alt"], "src": image["src"], "loaded": textures.has(image["src"]),
					   "w": image["w"], "h": image["h"]})
	return {
		"title": str(page.get("title", "")), "path": path, "url": base_url, "pages": pages_loaded, "cols": cols,
		"rows": rows,
		"palette": palette,
		"hover": hover, "cursor": "pointing" if mouse_default_cursor_shape == Control.CURSOR_POINTING_HAND else "arrow",
		"height": lay.height, "scroll": scroll, "screen": lay.text_rows(), "items": shown, "motions": motions,
		"moving": not running.is_empty(), "progress": lay.progress, "images": images,
		"unsupported": lay.unsupported, "status": status_line(), "layers": lay.layers,
		"dropdown": [] if dropdown.is_empty() else dropdown["options"].map(func(o): return str(o[0])),
		"flash": str(page.get("flash", "")) if not bool(page.get("flashShown", false)) else "",
		"cookies": cookies.keys(),
	}
