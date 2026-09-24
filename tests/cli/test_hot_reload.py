"""
Tests for the Quantum Hot Reload System.
"""

import pytest
import socket
import time
import tempfile
from pathlib import Path
from unittest.mock import MagicMock


def wait_until(condition, timeout=15.0, interval=0.05):
    """Poll until `condition()` is true; False if it never is within `timeout`.

    The tests used fixed sleeps, which are either too short on a loaded CI
    machine (a flake) or wasted time everywhere else.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(interval)
    return condition()


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def accepts_connections(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


class TestFileChange:
    """Tests for FileChange dataclass."""

    def test_file_change_creation(self):
        """Test creating a FileChange."""
        from quantum.cli.hot_reload import FileChange, ReloadType

        path = Path("/test/file.q")
        change = FileChange(path=path, change_type="modified")

        assert change.path == path
        assert change.change_type == "modified"
        assert change.extension == ".q"
        assert change.reload_type == ReloadType.FULL

    def test_css_file_reload_type(self):
        """Test that CSS files get CSS reload type."""
        from quantum.cli.hot_reload import FileChange, ReloadType

        change = FileChange(path=Path("/test/style.css"), change_type="modified")
        assert change.reload_type == ReloadType.CSS

    def test_scss_file_reload_type(self):
        """Test that SCSS files get CSS reload type."""
        from quantum.cli.hot_reload import FileChange, ReloadType

        change = FileChange(path=Path("/test/style.scss"), change_type="modified")
        assert change.reload_type == ReloadType.CSS

    def test_q_file_reload_type(self):
        """Test that .q files get FULL reload type."""
        from quantum.cli.hot_reload import FileChange, ReloadType

        change = FileChange(path=Path("/test/component.q"), change_type="modified")
        assert change.reload_type == ReloadType.FULL


class TestHotReloadWatcher:
    """Tests for HotReloadWatcher."""

    def test_watcher_creation(self):
        """Test creating a watcher."""
        from quantum.cli.hot_reload import HotReloadWatcher

        callback = MagicMock()
        watcher = HotReloadWatcher(
            paths=[Path(".")],
            extensions=[".q", ".css"],
            debounce_ms=100,
            on_change=callback
        )

        assert watcher.debounce_ms == 100
        assert ".q" in watcher.extensions
        assert ".css" in watcher.extensions
        assert watcher.on_change == callback

    def test_watcher_extension_filter(self):
        """Test that watcher filters by extension."""
        from quantum.cli.hot_reload import HotReloadWatcher

        callback = MagicMock()
        watcher = HotReloadWatcher(
            paths=[Path(".")],
            extensions=[".q"],
            on_change=callback
        )

        # A .txt is filtered out at once: nothing pending, no timer armed, so
        # the callback can never fire for it (no need to wait and see).
        watcher._handle_change(Path("/test/file.txt"), "modified")
        assert not watcher._pending_changes
        assert watcher._debounce_timer is None
        callback.assert_not_called()

        # A .q goes through the same path and is queued (the positive control).
        watcher._handle_change(Path("/test/file.q"), "created")
        assert list(watcher._pending_changes) == [Path("/test/file.q").resolve()]
        watcher._debounce_timer.cancel()

    def test_watcher_start_stop(self):
        """Test starting and stopping watcher."""
        from quantum.cli.hot_reload import HotReloadWatcher

        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = HotReloadWatcher(
                paths=[Path(tmpdir)],
                extensions=[".q"],
                on_change=lambda x: None
            )

            watcher.start()
            assert watcher._running

            watcher.stop()
            assert not watcher._running


class TestHotReloadServer:
    """Tests for HotReloadServer."""

    def test_server_creation(self):
        """Test creating a WebSocket server."""
        from quantum.cli.hot_reload import HotReloadServer

        server = HotReloadServer(host="localhost", port=35730)
        assert server.host == "localhost"
        assert server.port == 35730
        assert server.client_count == 0


class TestHotReloadManager:
    """Tests for HotReloadManager."""

    def test_manager_creation(self):
        """Test creating a manager."""
        from quantum.cli.hot_reload import HotReloadManager

        manager = HotReloadManager(
            watch_paths=[Path(".")],
            ws_port=35731,
            debounce_ms=50
        )

        assert manager.ws_port == 35731
        assert manager.debounce_ms == 50
        assert manager.ws_url == "ws://localhost:35731"

    def test_manager_ws_url(self):
        """Test WebSocket URL generation."""
        from quantum.cli.hot_reload import HotReloadManager

        manager = HotReloadManager(
            ws_host="127.0.0.1",
            ws_port=9999
        )

        assert manager.ws_url == "ws://127.0.0.1:9999"


class TestHotReloadClientScript:
    """Tests for hot reload client script generation."""

    def test_get_hot_reload_client_script(self):
        """Test generating client script."""
        from quantum.cli.hot_reload import get_hot_reload_client_script

        script = get_hot_reload_client_script(ws_port=35729, ws_host="localhost")

        assert "ws://localhost:35729" in script
        assert "WebSocket" in script
        assert "reload" in script
        assert "__quantum_hr_overlay" in script

    def test_client_script_custom_port(self):
        """Test client script with custom port."""
        from quantum.cli.hot_reload import get_hot_reload_client_script

        script = get_hot_reload_client_script(ws_port=8888, ws_host="192.168.1.1")

        assert "ws://192.168.1.1:8888" in script


class TestReloadType:
    """Tests for ReloadType enum."""

    def test_reload_type_values(self):
        """Test reload type enum values."""
        from quantum.cli.hot_reload import ReloadType

        assert ReloadType.FULL.value == "full"
        assert ReloadType.CSS.value == "css"
        assert ReloadType.COMPONENT.value == "component"


class TestIntegration:
    """Integration tests for the hot reload system."""

    def test_manager_start_stop(self):
        """Test starting and stopping the manager."""
        from quantum.cli.hot_reload import HotReloadManager

        with tempfile.TemporaryDirectory() as tmpdir:
            port = free_port()
            manager = HotReloadManager(
                watch_paths=[Path(tmpdir)],
                ws_host="127.0.0.1",
                ws_port=port
            )

            manager.start()
            assert manager._running
            assert wait_until(lambda: accepts_connections(port)), "the WebSocket server never listened"

            manager.stop()
            assert not manager._running
            assert wait_until(lambda: not accepts_connections(port)), "the WebSocket server kept listening"

    def test_file_change_detection(self):
        """Test that file changes are detected."""
        from quantum.cli.hot_reload import HotReloadManager

        changes_received = []

        def on_reload(changes, reload_type):
            changes_received.extend(changes)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            test_file = tmpdir / "test.q"
            test_file.write_text("<q:component name='Test'></q:component>")

            manager = HotReloadManager(
                watch_paths=[tmpdir],
                extensions=[".q"],
                ws_host="127.0.0.1",
                ws_port=free_port(),
                debounce_ms=50,
                on_reload=on_reload
            )

            manager.start()
            try:
                # A write made before the watcher has taken its first look is
                # invisible to it, and nothing says when that look happened.
                # So write a new version each round until one is seen, instead
                # of one write and a sleep. (This test used to assert nothing.)
                version = [0]

                def modify_and_check():
                    version[0] += 1
                    test_file.write_text(
                        f"<q:component name='Test'>Modified {version[0]}</q:component>")
                    return wait_until(lambda: changes_received, timeout=1.0)

                assert wait_until(modify_and_check, timeout=30, interval=0),                     "the change to test.q was never reported"
            finally:
                manager.stop()

            assert any(c.path == test_file.resolve() for c in changes_received)
            assert all(c.extension == ".q" for c in changes_received)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
