"""
Quantum Hot Reload System

Provides file watching and WebSocket-based live reload for development.

Components:
- HotReloadWatcher: File watcher using watchdog
- HotReloadServer: WebSocket server to push updates to browsers
- HotReloadManager: Coordinates file watching and WebSocket broadcasting

Usage:
    from cli.hot_reload import HotReloadManager

    manager = HotReloadManager(
        watch_paths=[Path('./components')],
        port=35729
    )
    manager.start()
"""

import asyncio
import json
import threading
import time
import hashlib
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ReloadType(Enum):
    """Type of reload to perform."""
    FULL = "full"           # Full page reload (structure changes)
    CSS = "css"             # CSS-only reload (style changes)
    COMPONENT = "component"  # Partial component reload


@dataclass
class FileChange:
    """Represents a file change event."""
    path: Path
    change_type: str  # 'modified', 'created', 'deleted'
    timestamp: float = field(default_factory=time.time)

    @property
    def extension(self) -> str:
        return self.path.suffix.lower()

    @property
    def reload_type(self) -> ReloadType:
        """Determine reload type based on file extension."""
        if self.extension in ('.css', '.scss', '.sass', '.less'):
            return ReloadType.CSS
        return ReloadType.FULL


class HotReloadWatcher:
    """
    File watcher using watchdog library.

    Watches specified directories for changes and triggers callbacks.
    Includes debouncing to handle rapid file changes.
    """

    def __init__(
        self,
        paths: List[Path],
        extensions: List[str] = None,
        debounce_ms: int = 100,
        on_change: Callable[[List[FileChange]], None] = None
    ):
        """
        Initialize the file watcher.

        Args:
            paths: Directories or files to watch
            extensions: File extensions to watch (e.g., ['.q', '.css'])
            debounce_ms: Debounce delay in milliseconds
            on_change: Callback when files change
        """
        self.paths = [Path(p).resolve() for p in paths]
        self.extensions = extensions or ['.q', '.yaml', '.yml', '.css', '.js', '.html']
        self.debounce_ms = debounce_ms
        self.on_change = on_change

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._observer = None
        self._pending_changes: Dict[Path, FileChange] = {}
        self._debounce_timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()

        # File content hashes for detecting actual changes
        self._file_hashes: Dict[Path, str] = {}

    def start(self):
        """Start watching files."""
        if self._running:
            return

        self._running = True

        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            watcher = self

            class ChangeHandler(FileSystemEventHandler):
                def on_modified(self, event):
                    if not event.is_directory:
                        watcher._handle_change(Path(event.src_path), 'modified')

                def on_created(self, event):
                    if not event.is_directory:
                        watcher._handle_change(Path(event.src_path), 'created')

                def on_deleted(self, event):
                    if not event.is_directory:
                        watcher._handle_change(Path(event.src_path), 'deleted')

            self._observer = Observer()
            handler = ChangeHandler()

            for path in self.paths:
                if path.exists():
                    if path.is_dir():
                        self._observer.schedule(handler, str(path), recursive=True)
                    else:
                        self._observer.schedule(handler, str(path.parent), recursive=False)

            self._observer.start()

        except ImportError:
            # Fallback to polling if watchdog not available
            self._thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._thread.start()

    def stop(self):
        """Stop watching files."""
        self._running = False

        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._observer = None

        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

        if self._debounce_timer:
            self._debounce_timer.cancel()
            self._debounce_timer = None

    def _handle_change(self, path: Path, change_type: str):
        """Handle a file change event."""
        path = path.resolve()

        # Check extension filter
        if self.extensions and path.suffix.lower() not in self.extensions:
            return

        # Check if content actually changed (for modified events)
        if change_type == 'modified':
            try:
                current_hash = self._compute_hash(path)
                if path in self._file_hashes and self._file_hashes[path] == current_hash:
                    return  # Content unchanged, skip
                self._file_hashes[path] = current_hash
            except (IOError, OSError):
                pass  # File might be locked or deleted

        # Add to pending changes
        with self._lock:
            self._pending_changes[path] = FileChange(path, change_type)

            # Reset debounce timer
            if self._debounce_timer:
                self._debounce_timer.cancel()

            self._debounce_timer = threading.Timer(
                self.debounce_ms / 1000.0,
                self._flush_changes
            )
            self._debounce_timer.start()

    def _flush_changes(self):
        """Flush pending changes to callback."""
        with self._lock:
            if not self._pending_changes:
                return

            changes = list(self._pending_changes.values())
            self._pending_changes.clear()

        if self.on_change and changes:
            try:
                self.on_change(changes)
            except Exception as e:
                print(f"[Hot Reload] Error in change callback: {e}")

    def _compute_hash(self, path: Path) -> str:
        """Compute MD5 hash of file content."""
        try:
            content = path.read_bytes()
            return hashlib.md5(content).hexdigest()
        except (IOError, OSError):
            return ""

    def _poll_loop(self):
        """Polling fallback when watchdog is not available."""
        last_mtimes: Dict[Path, float] = {}

        while self._running:
            try:
                current_files: Set[Path] = set()

                for base_path in self.paths:
                    if not base_path.exists():
                        continue

                    if base_path.is_file():
                        files = [base_path]
                    else:
                        files = []
                        for ext in self.extensions:
                            files.extend(base_path.rglob(f'*{ext}'))

                    for file_path in files:
                        file_path = file_path.resolve()
                        current_files.add(file_path)

                        try:
                            mtime = file_path.stat().st_mtime

                            if file_path in last_mtimes:
                                if mtime > last_mtimes[file_path]:
                                    self._handle_change(file_path, 'modified')

                            last_mtimes[file_path] = mtime
                        except (IOError, OSError):
                            pass

                # Check for deleted files
                for old_file in list(last_mtimes.keys()):
                    if old_file not in current_files:
                        self._handle_change(old_file, 'deleted')
                        del last_mtimes[old_file]

            except Exception:
                pass

            time.sleep(0.5)


class HotReloadServer:
    """
    WebSocket server for pushing reload events to browsers.

    Uses asyncio and the websockets library.
    """

    def __init__(self, host: str = 'localhost', port: int = 35729):
        """
        Initialize the WebSocket server.

        Args:
            host: Host to bind to
            port: Port for WebSocket server
        """
        self.host = host
        self.port = port
        self._clients: Set = set()
        self._server = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self):
        """Start the WebSocket server in a background thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()

        # Wait a bit for server to start
        time.sleep(0.2)

    def stop(self):
        """Stop the WebSocket server."""
        self._running = False

        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def _run_server(self):
        """Run the WebSocket server (in background thread)."""
        try:
            import websockets
            import websockets.server
        except ImportError:
            print("[Hot Reload] websockets library not found. Using fallback polling.")
            print("[Hot Reload] Install with: pip install websockets")
            return

        async def handler(websocket):
            """Handle WebSocket connections."""
            self._clients.add(websocket)
            try:
                # Send initial connection message
                await websocket.send(json.dumps({
                    'type': 'connected',
                    'timestamp': time.time()
                }))

                # Keep connection alive
                async for message in websocket:
                    # Handle ping/pong or other messages
                    try:
                        data = json.loads(message)
                        if data.get('type') == 'ping':
                            await websocket.send(json.dumps({'type': 'pong'}))
                    except json.JSONDecodeError:
                        pass

            except websockets.exceptions.ConnectionClosed:
                pass
            finally:
                self._clients.discard(websocket)

        async def main():
            async with websockets.server.serve(handler, self.host, self.port):
                while self._running:
                    await asyncio.sleep(0.1)

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_until_complete(main())
        except Exception:
            pass
        finally:
            self._loop.close()

    def broadcast(self, message: dict):
        """
        Broadcast a message to all connected clients.

        Args:
            message: Message dict to send as JSON
        """
        if not self._clients or not self._loop:
            return

        async def send_to_all():
            json_msg = json.dumps(message)
            disconnected = set()

            for client in self._clients.copy():
                try:
                    await client.send(json_msg)
                except Exception:
                    disconnected.add(client)

            self._clients -= disconnected

        try:
            asyncio.run_coroutine_threadsafe(send_to_all(), self._loop)
        except Exception:
            pass

    @property
    def client_count(self) -> int:
        """Number of connected clients."""
        return len(self._clients)


class HotReloadManager:
    """
    Coordinates file watching and WebSocket broadcasting.

    Main interface for the hot reload system.
    """

    def __init__(
        self,
        watch_paths: List[Path] = None,
        extensions: List[str] = None,
        ws_host: str = 'localhost',
        ws_port: int = 35729,
        debounce_ms: int = 100,
        on_reload: Callable[[List[FileChange], ReloadType], None] = None,
        console = None
    ):
        """
        Initialize the hot reload manager.

        Args:
            watch_paths: Paths to watch for changes
            extensions: File extensions to watch
            ws_host: WebSocket server host
            ws_port: WebSocket server port
            debounce_ms: Debounce delay in milliseconds
            on_reload: Optional callback when reload is triggered
            console: Optional console for logging (from cli.utils)
        """
        self.watch_paths = watch_paths or [Path('.')]
        self.extensions = extensions or ['.q', '.yaml', '.yml', '.css', '.js', '.html']
        self.ws_host = ws_host
        self.ws_port = ws_port
        self.debounce_ms = debounce_ms
        self.on_reload = on_reload
        self.console = console

        self._watcher: Optional[HotReloadWatcher] = None
        self._server: Optional[HotReloadServer] = None
        self._running = False
        self._reload_count = 0

        # Error tracking for overlay
        self._last_error: Optional[dict] = None

    def start(self):
        """Start the hot reload system."""
        if self._running:
            return

        self._running = True

        # Start WebSocket server
        self._server = HotReloadServer(self.ws_host, self.ws_port)
        self._server.start()

        # Start file watcher
        self._watcher = HotReloadWatcher(
            paths=self.watch_paths,
            extensions=self.extensions,
            debounce_ms=self.debounce_ms,
            on_change=self._handle_changes
        )
        self._watcher.start()

        self._log(f"Hot reload started on ws://{self.ws_host}:{self.ws_port}")

    def stop(self):
        """Stop the hot reload system."""
        self._running = False

        if self._watcher:
            self._watcher.stop()
            self._watcher = None

        if self._server:
            self._server.stop()
            self._server = None

        self._log("Hot reload stopped")

    def _handle_changes(self, changes: List[FileChange]):
        """Handle file changes from watcher."""
        if not changes:
            return

        self._reload_count += 1

        # Determine reload type
        reload_type = ReloadType.FULL
        css_only = all(c.reload_type == ReloadType.CSS for c in changes)
        if css_only:
            reload_type = ReloadType.CSS

        # Log changes
        for change in changes:
            rel_path = change.path
            try:
                rel_path = change.path.relative_to(Path.cwd())
            except ValueError:
                pass
            self._log(f"[{datetime.now().strftime('%H:%M:%S')}] {change.change_type}: {rel_path}")

        # Clear any previous error
        self._last_error = None

        # Try to parse changed .q files to detect errors
        parse_error = None
        for change in changes:
            if change.extension == '.q' and change.change_type != 'deleted':
                error = self._check_parse_error(change.path)
                if error:
                    parse_error = error
                    break

        if parse_error:
            self._last_error = parse_error
            self._broadcast_error(parse_error)
            return

        # Broadcast reload to clients
        self._broadcast_reload(changes, reload_type)

        # Call optional callback
        if self.on_reload:
            try:
                self.on_reload(changes, reload_type)
            except Exception as e:
                self._log(f"Error in reload callback: {e}")

    def _check_parse_error(self, path: Path) -> Optional[dict]:
        """Check if a .q file has parse errors."""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from core.parser import QuantumParser, QuantumParseError

            parser = QuantumParser()
            parser.parse_file(str(path))
            return None

        except QuantumParseError as e:
            return {
                'type': 'parse_error',
                'file': str(path),
                'message': str(e),
                'line': getattr(e, 'line', None),
                'column': getattr(e, 'column', None)
            }
        except Exception as e:
            return {
                'type': 'error',
                'file': str(path),
                'message': str(e)
            }

    def _broadcast_reload(self, changes: List[FileChange], reload_type: ReloadType):
        """Broadcast reload event to connected browsers."""
        if not self._server:
            return

        message = {
            'type': 'reload',
            'reloadType': reload_type.value,
            'files': [
                {
                    'path': str(c.path),
                    'changeType': c.change_type,
                    'extension': c.extension
                }
                for c in changes
            ],
            'timestamp': time.time(),
            'reloadCount': self._reload_count
        }

        self._server.broadcast(message)
        self._log(f"Reloading... ({reload_type.value})")

    def _broadcast_error(self, error: dict):
        """Broadcast error event to connected browsers."""
        if not self._server:
            return

        message = {
            'type': 'error',
            'error': error,
            'timestamp': time.time()
        }

        self._server.broadcast(message)
        self._log(f"Parse error in {error.get('file', 'unknown')}: {error.get('message', 'Unknown error')}")

    def clear_error(self):
        """Clear the current error and notify clients."""
        self._last_error = None
        if self._server:
            self._server.broadcast({
                'type': 'clear_error',
                'timestamp': time.time()
            })

    def force_reload(self):
        """Force a full page reload on all clients."""
        if self._server:
            self._reload_count += 1
            self._server.broadcast({
                'type': 'reload',
                'reloadType': 'full',
                'files': [],
                'timestamp': time.time(),
                'reloadCount': self._reload_count,
                'forced': True
            })
            self._log("Forced reload")

    def _log(self, message: str):
        """Log a message."""
        if self.console:
            self.console.info(message)
        else:
            print(f"[Hot Reload] {message}")

    @property
    def ws_url(self) -> str:
        """WebSocket URL for client connection."""
        return f"ws://{self.ws_host}:{self.ws_port}"

    @property
    def client_count(self) -> int:
        """Number of connected browser clients."""
        return self._server.client_count if self._server else 0


def get_hot_reload_client_script(ws_port: int = 35729, ws_host: str = 'localhost') -> str:
    """
    Get the hot reload client JavaScript code.

    Args:
        ws_port: WebSocket server port
        ws_host: WebSocket server host

    Returns:
        JavaScript code to inject into HTML pages
    """
    return f"""
<!-- Quantum Hot Reload Client -->
<script>
(function() {{
    'use strict';

    var WS_URL = 'ws://{ws_host}:{ws_port}';
    var RECONNECT_INTERVAL = 1000;
    var MAX_RECONNECT_ATTEMPTS = 30;

    var socket = null;
    var reconnectAttempts = 0;
    var overlay = null;
    var isConnected = false;

    // State preservation
    var preservedState = {{}};

    function log(msg) {{
        console.log('[Hot Reload] ' + msg);
    }}

    function connect() {{
        if (socket && socket.readyState === WebSocket.OPEN) {{
            return;
        }}

        try {{
            socket = new WebSocket(WS_URL);

            socket.onopen = function() {{
                log('Connected to dev server');
                reconnectAttempts = 0;
                isConnected = true;
                hideOverlay();
                showToast('Hot reload connected', 'success');
            }};

            socket.onclose = function() {{
                isConnected = false;
                log('Disconnected from dev server');
                scheduleReconnect();
            }};

            socket.onerror = function(err) {{
                log('WebSocket error');
            }};

            socket.onmessage = function(event) {{
                try {{
                    var data = JSON.parse(event.data);
                    handleMessage(data);
                }} catch (e) {{
                    log('Error parsing message: ' + e);
                }}
            }};

        }} catch (e) {{
            log('Failed to connect: ' + e);
            scheduleReconnect();
        }}
    }}

    function scheduleReconnect() {{
        if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {{
            log('Max reconnect attempts reached');
            showOverlay({{
                type: 'connection_lost',
                message: 'Lost connection to dev server. Please restart the server.'
            }});
            return;
        }}

        reconnectAttempts++;
        setTimeout(connect, RECONNECT_INTERVAL);
    }}

    function handleMessage(data) {{
        switch (data.type) {{
            case 'connected':
                log('Server acknowledged connection');
                break;

            case 'reload':
                handleReload(data);
                break;

            case 'error':
                handleError(data.error);
                break;

            case 'clear_error':
                hideOverlay();
                break;

            case 'pong':
                // Heartbeat response
                break;
        }}
    }}

    function handleReload(data) {{
        log('Reload triggered: ' + data.reloadType);

        if (data.reloadType === 'css') {{
            reloadCSS();
            showToast('Styles updated', 'info');
        }} else {{
            // Preserve state before reload
            preserveState();

            // Full page reload
            showToast('Reloading...', 'info');
            setTimeout(function() {{
                location.reload();
            }}, 100);
        }}
    }}

    function handleError(error) {{
        log('Error received: ' + error.message);
        showOverlay(error);
    }}

    function reloadCSS() {{
        var links = document.querySelectorAll('link[rel="stylesheet"]');
        var timestamp = Date.now();

        links.forEach(function(link) {{
            var href = link.href.split('?')[0];
            link.href = href + '?_hr=' + timestamp;
        }});

        log('CSS reloaded');
    }}

    function preserveState() {{
        // Save form values
        var forms = document.querySelectorAll('form');
        forms.forEach(function(form, i) {{
            var formId = form.id || 'form_' + i;
            preservedState[formId] = {{}};

            var inputs = form.querySelectorAll('input, textarea, select');
            inputs.forEach(function(input) {{
                if (input.name) {{
                    if (input.type === 'checkbox' || input.type === 'radio') {{
                        preservedState[formId][input.name] = input.checked;
                    }} else {{
                        preservedState[formId][input.name] = input.value;
                    }}
                }}
            }});
        }});

        // Save scroll position
        preservedState._scroll = {{
            x: window.scrollX,
            y: window.scrollY
        }};

        // Store in sessionStorage for restoration after reload
        try {{
            sessionStorage.setItem('__quantum_hr_state', JSON.stringify(preservedState));
        }} catch (e) {{
            // Storage might be full or unavailable
        }}
    }}

    function restoreState() {{
        try {{
            var saved = sessionStorage.getItem('__quantum_hr_state');
            if (!saved) return;

            var state = JSON.parse(saved);
            sessionStorage.removeItem('__quantum_hr_state');

            // Restore form values
            Object.keys(state).forEach(function(formId) {{
                if (formId.startsWith('_')) return;

                var form = document.getElementById(formId) || document.forms[formId.replace('form_', '')];
                if (!form) return;

                var formState = state[formId];
                Object.keys(formState).forEach(function(name) {{
                    var input = form.querySelector('[name="' + name + '"]');
                    if (input) {{
                        if (input.type === 'checkbox' || input.type === 'radio') {{
                            input.checked = formState[name];
                        }} else {{
                            input.value = formState[name];
                        }}
                    }}
                }});
            }});

            // Restore scroll position
            if (state._scroll) {{
                setTimeout(function() {{
                    window.scrollTo(state._scroll.x, state._scroll.y);
                }}, 100);
            }}

            log('State restored');

        }} catch (e) {{
            log('Error restoring state: ' + e);
        }}
    }}

    function showOverlay(error) {{
        hideOverlay();

        overlay = document.createElement('div');
        overlay.id = '__quantum_hr_overlay';
        overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.9);z-index:999999;display:flex;align-items:center;justify-content:center;font-family:-apple-system,BlinkMacSystemFont,sans-serif;';

        var content = document.createElement('div');
        content.style.cssText = 'max-width:800px;padding:40px;background:#1e1e1e;border-radius:8px;color:#fff;box-shadow:0 4px 24px rgba(0,0,0,0.5);';

        var title = error.type === 'connection_lost' ? 'Connection Lost' : 'Parse Error';
        var titleColor = error.type === 'connection_lost' ? '#ffc107' : '#f44336';

        content.innerHTML = '<h2 style="color:' + titleColor + ';margin:0 0 16px 0;display:flex;align-items:center;gap:8px;">' +
            '<span style="font-size:24px;">' + (error.type === 'connection_lost' ? '&#x26A0;' : '&#x2717;') + '</span>' +
            title +
            '</h2>' +
            (error.file ? '<p style="color:#888;margin:0 0 12px 0;font-size:14px;">File: ' + error.file + '</p>' : '') +
            '<pre style="background:#2d2d2d;padding:16px;border-radius:4px;overflow:auto;max-height:400px;margin:0;font-size:14px;line-height:1.5;color:#ff6b6b;">' +
            escapeHtml(error.message) +
            '</pre>' +
            '<p style="color:#888;margin:16px 0 0 0;font-size:13px;">Fix the error and save the file to reload automatically.</p>';

        overlay.appendChild(content);
        document.body.appendChild(overlay);

        // Click outside to dismiss (but error will reappear on next change)
        overlay.addEventListener('click', function(e) {{
            if (e.target === overlay) {{
                hideOverlay();
            }}
        }});
    }}

    function hideOverlay() {{
        if (overlay && overlay.parentNode) {{
            overlay.parentNode.removeChild(overlay);
        }}
        overlay = null;
    }}

    function showToast(message, type) {{
        var existing = document.getElementById('__quantum_hr_toast');
        if (existing) {{
            existing.parentNode.removeChild(existing);
        }}

        var toast = document.createElement('div');
        toast.id = '__quantum_hr_toast';

        var bgColor = type === 'success' ? '#4caf50' : type === 'error' ? '#f44336' : '#2196f3';

        toast.style.cssText = 'position:fixed;bottom:20px;right:20px;padding:12px 20px;background:' + bgColor + ';color:#fff;border-radius:4px;font-family:-apple-system,BlinkMacSystemFont,sans-serif;font-size:14px;z-index:999998;box-shadow:0 2px 8px rgba(0,0,0,0.2);animation:__qhr_fadein 0.3s ease;';
        toast.textContent = message;

        // Add animation keyframes if not present
        if (!document.getElementById('__quantum_hr_styles')) {{
            var style = document.createElement('style');
            style.id = '__quantum_hr_styles';
            style.textContent = '@keyframes __qhr_fadein {{ from {{ opacity:0;transform:translateY(10px); }} to {{ opacity:1;transform:translateY(0); }} }}';
            document.head.appendChild(style);
        }}

        document.body.appendChild(toast);

        setTimeout(function() {{
            if (toast.parentNode) {{
                toast.style.opacity = '0';
                toast.style.transition = 'opacity 0.3s ease';
                setTimeout(function() {{
                    if (toast.parentNode) {{
                        toast.parentNode.removeChild(toast);
                    }}
                }}, 300);
            }}
        }}, 2000);
    }}

    function escapeHtml(text) {{
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }}

    // Heartbeat to keep connection alive
    setInterval(function() {{
        if (socket && socket.readyState === WebSocket.OPEN) {{
            socket.send(JSON.stringify({{ type: 'ping' }}));
        }}
    }}, 30000);

    // Initialize
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', function() {{
            restoreState();
            connect();
        }});
    }} else {{
        restoreState();
        connect();
    }}

}})();
</script>
"""


# Export client script as a constant for easy access
HOT_RELOAD_CLIENT_SCRIPT = get_hot_reload_client_script()
