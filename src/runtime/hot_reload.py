"""
Hot Reload - File watcher for auto-refresh during development

Watches .q component files and triggers browser refresh on changes.
"""

import time
import threading
from pathlib import Path
from typing import Set, Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent


class ComponentFileHandler(FileSystemEventHandler):
    """Handles file system events for .q component files"""

    def __init__(self, callback: Callable[[str], None]):
        self.callback = callback
        self.last_modified = {}
        self.debounce_seconds = 0.5  # Prevent multiple triggers

    def on_modified(self, event: FileSystemEvent):
        """Called when a file is modified"""
        if event.is_directory:
            return

        file_path = event.src_path

        # Only watch .q files
        if not file_path.endswith('.q'):
            return

        # Debounce: ignore if modified too recently
        current_time = time.time()
        last_mod_time = self.last_modified.get(file_path, 0)

        if current_time - last_mod_time < self.debounce_seconds:
            return

        self.last_modified[file_path] = current_time

        # Trigger callback
        print(f"🔄 File changed: {Path(file_path).name}")
        self.callback(file_path)

    def on_created(self, event: FileSystemEvent):
        """Called when a new file is created"""
        if event.is_directory:
            return

        file_path = event.src_path

        if file_path.endswith('.q'):
            print(f"✨ New file: {Path(file_path).name}")
            self.callback(file_path)


class HotReloadWatcher:
    """Watches component files and triggers callbacks on changes"""

    def __init__(self, watch_dirs: list[str], callback: Callable[[str], None]):
        """
        Initialize hot reload watcher

        Args:
            watch_dirs: List of directories to watch
            callback: Function to call when files change (receives file path)
        """
        self.watch_dirs = [Path(d) for d in watch_dirs]
        self.callback = callback
        self.observer = Observer()
        self.handler = ComponentFileHandler(callback)
        self.is_running = False

    def start(self):
        """Start watching for file changes"""
        if self.is_running:
            return

        print("🔄 Hot reload enabled")
        print(f"📁 Watching: {', '.join(str(d) for d in self.watch_dirs)}")

        # Schedule observers for each directory
        for watch_dir in self.watch_dirs:
            if watch_dir.exists():
                self.observer.schedule(
                    self.handler,
                    str(watch_dir),
                    recursive=True
                )
            else:
                print(f"⚠️  Warning: {watch_dir} does not exist")

        self.observer.start()
        self.is_running = True

    def stop(self):
        """Stop watching for file changes"""
        if not self.is_running:
            return

        print("\n🛑 Stopping hot reload...")
        self.observer.stop()
        self.observer.join()
        self.is_running = False

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()


class ServerSentEvents:
    """Server-Sent Events (SSE) for pushing reload notifications to browser"""

    def __init__(self):
        self.listeners: Set[Callable] = set()

    def add_listener(self, listener: Callable):
        """Add a listener that will be called with SSE data"""
        self.listeners.add(listener)

    def remove_listener(self, listener: Callable):
        """Remove a listener"""
        self.listeners.discard(listener)

    def notify_reload(self, file_path: str):
        """Notify all listeners that a file changed"""
        message = f"data: {{'type': 'reload', 'file': '{file_path}'}}\n\n"

        for listener in self.listeners:
            try:
                listener(message)
            except Exception as e:
                print(f"Error notifying listener: {e}")


# Global SSE manager
_sse_manager = ServerSentEvents()


def get_sse_manager() -> ServerSentEvents:
    """Get global SSE manager"""
    return _sse_manager


def create_hot_reload_watcher(
    components_dir: str = "components",
    examples_dir: Optional[str] = "examples"
) -> HotReloadWatcher:
    """
    Create a hot reload watcher for component directories

    Args:
        components_dir: Main components directory
        examples_dir: Examples directory (optional)

    Returns:
        Configured HotReloadWatcher instance
    """
    watch_dirs = [components_dir]
    if examples_dir and Path(examples_dir).exists():
        watch_dirs.append(examples_dir)

    def on_file_change(file_path: str):
        """Called when a file changes"""
        # Notify SSE clients
        get_sse_manager().notify_reload(file_path)

    return HotReloadWatcher(watch_dirs, on_file_change)


# Hot reload HTML snippet to inject into pages
HOT_RELOAD_SCRIPT = """
<script>
// Hot Reload Client
(function() {
    const eventSource = new EventSource('/__hot_reload__');

    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);

        if (data.type === 'reload') {
            console.log('🔄 Hot reload: ' + data.file);
            // Wait a bit for file to be written
            setTimeout(() => {
                window.location.reload();
            }, 300);
        }
    };

    eventSource.onerror = function() {
        console.log('❌ Hot reload connection lost');
        // Try to reconnect after a delay
        setTimeout(() => {
            window.location.reload();
        }, 5000);
    };

    console.log('🔥 Hot reload connected');
})();
</script>
"""
