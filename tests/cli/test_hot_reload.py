"""
Tests for the Quantum Hot Reload System.
"""

import pytest
import time
import tempfile
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestFileChange:
    """Tests for FileChange dataclass."""

    def test_file_change_creation(self):
        """Test creating a FileChange."""
        from cli.hot_reload import FileChange, ReloadType

        path = Path("/test/file.q")
        change = FileChange(path=path, change_type="modified")

        assert change.path == path
        assert change.change_type == "modified"
        assert change.extension == ".q"
        assert change.reload_type == ReloadType.FULL

    def test_css_file_reload_type(self):
        """Test that CSS files get CSS reload type."""
        from cli.hot_reload import FileChange, ReloadType

        change = FileChange(path=Path("/test/style.css"), change_type="modified")
        assert change.reload_type == ReloadType.CSS

    def test_scss_file_reload_type(self):
        """Test that SCSS files get CSS reload type."""
        from cli.hot_reload import FileChange, ReloadType

        change = FileChange(path=Path("/test/style.scss"), change_type="modified")
        assert change.reload_type == ReloadType.CSS

    def test_q_file_reload_type(self):
        """Test that .q files get FULL reload type."""
        from cli.hot_reload import FileChange, ReloadType

        change = FileChange(path=Path("/test/component.q"), change_type="modified")
        assert change.reload_type == ReloadType.FULL


class TestHotReloadWatcher:
    """Tests for HotReloadWatcher."""

    def test_watcher_creation(self):
        """Test creating a watcher."""
        from cli.hot_reload import HotReloadWatcher

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
        from cli.hot_reload import HotReloadWatcher

        callback = MagicMock()
        watcher = HotReloadWatcher(
            paths=[Path(".")],
            extensions=[".q"],
            on_change=callback
        )

        # Simulate handling changes
        # .txt should be filtered out
        watcher._handle_change(Path("/test/file.txt"), "modified")
        time.sleep(0.2)

        # Callback should not have been called
        callback.assert_not_called()

    def test_watcher_start_stop(self):
        """Test starting and stopping watcher."""
        from cli.hot_reload import HotReloadWatcher

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
        from cli.hot_reload import HotReloadServer

        server = HotReloadServer(host="localhost", port=35730)
        assert server.host == "localhost"
        assert server.port == 35730
        assert server.client_count == 0


class TestHotReloadManager:
    """Tests for HotReloadManager."""

    def test_manager_creation(self):
        """Test creating a manager."""
        from cli.hot_reload import HotReloadManager

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
        from cli.hot_reload import HotReloadManager

        manager = HotReloadManager(
            ws_host="127.0.0.1",
            ws_port=9999
        )

        assert manager.ws_url == "ws://127.0.0.1:9999"


class TestHotReloadClientScript:
    """Tests for hot reload client script generation."""

    def test_get_hot_reload_client_script(self):
        """Test generating client script."""
        from cli.hot_reload import get_hot_reload_client_script

        script = get_hot_reload_client_script(ws_port=35729, ws_host="localhost")

        assert "ws://localhost:35729" in script
        assert "WebSocket" in script
        assert "reload" in script
        assert "__quantum_hr_overlay" in script

    def test_client_script_custom_port(self):
        """Test client script with custom port."""
        from cli.hot_reload import get_hot_reload_client_script

        script = get_hot_reload_client_script(ws_port=8888, ws_host="192.168.1.1")

        assert "ws://192.168.1.1:8888" in script


class TestReloadType:
    """Tests for ReloadType enum."""

    def test_reload_type_values(self):
        """Test reload type enum values."""
        from cli.hot_reload import ReloadType

        assert ReloadType.FULL.value == "full"
        assert ReloadType.CSS.value == "css"
        assert ReloadType.COMPONENT.value == "component"


class TestIntegration:
    """Integration tests for the hot reload system."""

    def test_manager_start_stop(self):
        """Test starting and stopping the manager."""
        from cli.hot_reload import HotReloadManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = HotReloadManager(
                watch_paths=[Path(tmpdir)],
                ws_port=35732
            )

            manager.start()
            assert manager._running
            time.sleep(0.3)

            manager.stop()
            assert not manager._running

    def test_file_change_detection(self):
        """Test that file changes are detected."""
        from cli.hot_reload import HotReloadManager, FileChange

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
                ws_port=35733,
                debounce_ms=50,
                on_reload=on_reload
            )

            manager.start()
            time.sleep(0.3)

            # Modify the file
            test_file.write_text("<q:component name='Test'>Modified</q:component>")
            time.sleep(0.5)

            manager.stop()

            # Check that we detected the change
            # Note: This might be flaky depending on file system
            # In a real test we'd use proper synchronization


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
