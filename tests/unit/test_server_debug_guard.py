"""
The Werkzeug debugger must never be exposed on a network interface.

Debug mode includes an interactive console that evaluates arbitrary Python, so
`debug: true` on host 0.0.0.0 is unauthenticated RCE for anyone who can reach
the port. The shipped defaults used to be exactly that combination — host
0.0.0.0, debug true — active on the first `quantum start`. Reported by two
audit dimensions.
"""

from quantum.runtime.web_server import QuantumWebServer


class TestSafeDefaults:
    def test_default_host_is_loopback(self):
        assert QuantumWebServer().config["server"]["host"] == "127.0.0.1"

    def test_default_debug_is_off(self):
        assert QuantumWebServer().config["server"]["debug"] is False


class TestStartDropsDebuggerOffLoopback:
    """start() forces debug off when the host is not loopback, and passes the
    real value to app.run so the effect is observable without a live server."""

    def _run_captured(self, host, debug):
        s = QuantumWebServer()
        s.config["server"].update(host=host, port=0, debug=debug, reload=False)
        captured = {}
        s.app.run = lambda **kw: captured.update(kw)  # type: ignore
        s._register_signal_handlers = lambda: None      # avoid main-thread req
        s._write_pid_file = lambda *a: None
        s._print_banner = lambda: None
        s._check_port_available = lambda h, p: True
        s.start()
        return captured

    def test_debug_dropped_on_all_interfaces(self):
        assert self._run_captured("0.0.0.0", True).get("debug") is False

    def test_debug_dropped_on_a_lan_ip(self):
        assert self._run_captured("192.168.1.10", True).get("debug") is False

    def test_debug_allowed_on_loopback(self):
        assert self._run_captured("127.0.0.1", True).get("debug") is True

    def test_debug_off_stays_off_everywhere(self):
        assert self._run_captured("0.0.0.0", False).get("debug") is False
