"""Starting and stopping the server: banner, port check, PID file, signals.

Part of QuantumWebServer (web_server.py), as a mixin."""

import os
import signal
import socket
import sys
import time
from pathlib import Path


class ServerLifecycle:
    def _count_component_files(self) -> int:
        """Count .q files in the components directory."""
        components_dir = Path(self.config['paths']['components'])
        if not components_dir.is_dir():
            return 0
        # a *.test.q next to the pages is a test suite, not a page (ROUTE-4)
        return sum(1 for p in components_dir.rglob('*.q') if not p.name.endswith('.test.q'))

    def _count_routes(self):
        """Return (static_count, dynamic_count) of registered routes."""
        static_count = len([r for r in self.app.url_map.iter_rules()
                           if '<' not in str(r)])
        dynamic_count = len(self._dynamic_routes)
        return static_count, dynamic_count

    def _print_banner(self):
        """Print startup banner with server information."""
        port = self.config['server']['port']
        components_dir = self.config['paths']['components']
        log_config = self.config.get('logging', {})
        startup_ms = (time.monotonic() - self._start_time) * 1000
        file_count = self._count_component_files()
        static_routes, dynamic_routes = self._count_routes()

        print()
        print("=" * 60)
        print("  QUANTUM WEB SERVER")
        print("=" * 60)
        print(f"  URL:             http://localhost:{port}")
        print(f"  Components:      {components_dir} ({file_count} files)")
        print(f"  Routes:          {static_routes} static + {dynamic_routes} dynamic")
        print(f"  Log level:       {log_config.get('level', 'INFO')}")
        if log_config.get('file', True):
            print(f"  Log file:        {log_config.get('filename', 'quantum.log')}")
        print(f"  Auto-reload:     {self.config['server'].get('reload', False)}")
        print(f"  Debug mode:      {self.config['server'].get('debug', False)}")
        if self.dev_panel is not None:
            print(f"  Dev panel:       http://localhost:{port}/_dev")
        if self.hot_reload_enabled:
            print(f"  Hot Reload:      ws://localhost:{self.hot_reload_port}")
        print(f"  Startup time:    {startup_ms:.0f}ms")
        print("=" * 60)
        print("  Press Ctrl+C to stop")
        print("=" * 60)
        print()

    def _check_port_available(self, host: str, port: int) -> bool:
        """Check if a port is available for binding."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('127.0.0.1' if host == '0.0.0.0' else host, port))
                return result != 0  # 0 means connection succeeded → port in use
        except OSError:
            return True  # If we can't connect, assume port is free

    def _write_pid_file(self, is_reloader_child: bool = False):
        """Write .quantum.pid: this process, plus the parent under the reloader.

        With `reload: true` Werkzeug serves from a CHILD process. Recording
        only the parent meant `quantum stop` killed the parent and left the
        child listening on the port. `quantum stop` reads every line.

        Each line is the PID and the process's start time (RUN-3): a PID
        alone is reused by the next process that starts, and a stale file
        made `quantum stop` kill that one.
        """
        from quantum.runtime.process_identity import pid_file_line
        pids = [os.getppid(), os.getpid()] if is_reloader_child else [os.getpid()]
        try:
            Path(self.PID_FILE).write_text(
                '\n'.join(pid_file_line(p) for p in pids) + '\n', encoding='utf-8')
        except OSError as e:
            self.logger.warning(f"Could not write PID file: {e}")

    def _remove_pid_file(self):
        """Remove .quantum.pid if it exists.

        Only the process that started the server owns the file. The reloader
        child exits with code 3 on EVERY code change to be restarted, and its
        cleanup used to delete the file — so after the first hot reload
        `quantum stop` reported "No running server found" while it was up.
        """
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            return
        try:
            Path(self.PID_FILE).unlink(missing_ok=True)
        except OSError:
            pass

    def _cleanup(self):
        """Cleanup on shutdown: remove PID file, log shutdown."""
        self._remove_pid_file()
        self.logger.info("Server stopped")

    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown."""
        def _handler(signum, frame):
            self._cleanup()
            sys.exit(0)

        signal.signal(signal.SIGINT, _handler)
        signal.signal(signal.SIGTERM, _handler)
        # Windows-specific: CTRL_BREAK_EVENT
        if hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, _handler)

    def start(self):
        """Start the Quantum web server."""
        host = self.config['server']['host']
        port = self.config['server']['port']
        debug = self.config['server'].get('debug', False)
        reload = self.config['server'].get('reload', False)

        # The Werkzeug debugger is an eval console. Never expose it on a
        # non-loopback interface, even if the config asks for it — that is
        # unauthenticated RCE over the network. Drop the debugger rather than
        # refusing to start, so a misconfiguration degrades safely.
        if debug and host not in ('127.0.0.1', 'localhost', '::1'):
            self.logger.error(
                f"Refusing to run the debugger (debug: true) on {host}: the "
                f"Werkzeug console would be an eval prompt open to the network. "
                f"Serving with the debugger OFF. Use host 127.0.0.1 for a local "
                f"debug session."
            )
            debug = False

        # Werkzeug's reloader re-executes this whole program in a child
        # process and sets WERKZEUG_RUN_MAIN in it. Without this guard the
        # child ran the port check, found the PARENT's own socket bound,
        # reported "port already in use" and returned — so `quantum start`
        # printed its success banner and then died, with nothing listening.
        # `reload: true` is the shipped default in quantum.config.yaml, which
        # means the documented way to start the server could not start it.
        is_reloader_child = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'

        if not is_reloader_child and not self._check_port_available(host, port):
            self.logger.error(
                f"Port {port} already in use. Stop the other process, or set "
                f"server.port in quantum.config.yaml."
            )
            # Non-zero: a supervisor, container healthcheck or CI step must be
            # able to tell a dead server from a live one. This used to return
            # None, so the CLI exited 0 while nothing was listening.
            return 1

        self._write_pid_file(is_reloader_child)
        self._register_signal_handlers()
        self._print_banner()

        # DEV-4: with --hot-reload, the process that serves (the reloader's
        # child, or the only process) also watches the project and tells the
        # browsers to reload. The page script alone connected to nothing.
        hot_reload = None
        if getattr(self, 'hot_reload_enabled', False) and (is_reloader_child or not reload):
            hot_reload = self._start_hot_reload()

        try:
            self.app.run(
                host=host,
                port=port,
                debug=debug,
                use_reloader=reload
            )
        except KeyboardInterrupt:
            self.logger.info("Stopped by user")
        except OSError as e:
            # Losing the bind after the banner printed is the case most likely
            # to be mistaken for success.
            self.logger.error(f"Could not bind {host}:{port} — {e}")
            return 1
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            return 1
        finally:
            if hot_reload is not None:
                hot_reload.stop()
            self._cleanup()
        return 0

    def _start_hot_reload(self):
        """Watch the components and static folders; reload the browsers on a change."""
        from quantum.cli.hot_reload import HotReloadManager
        paths = self.config.get('paths', {})
        folders = [Path(paths[key]).resolve() for key in ('components', 'static')
                   if paths.get(key) and Path(paths[key]).is_dir()]
        manager = HotReloadManager(
            watch_paths=folders or [Path.cwd()],
            ws_host='localhost',
            ws_port=self.hot_reload_port,
            # performance.cache_templates keeps each page's AST forever; a
            # reload must see the new file.
            on_reload=lambda changes, reload_type: self.template_cache.clear(),
        )
        manager.start()
        return manager
