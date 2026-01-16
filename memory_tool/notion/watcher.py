"""File watcher for automatic Notion sync.

Watches local .memory/modules/ directory for changes and triggers sync.
"""

import time
import threading
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object


class ModuleChangeHandler(FileSystemEventHandler):
    """Handle file system events for .memory/modules/ directory."""

    def __init__(
        self,
        on_change: Callable[[str, str], None],
        debounce_seconds: float = 2.0,
        verbose: bool = False
    ):
        """Initialize handler.

        Args:
            on_change: Callback function(event_type, file_path) when change detected
            debounce_seconds: Wait time before triggering sync (to batch rapid changes)
            verbose: Print verbose output
        """
        super().__init__()
        self.on_change = on_change
        self.debounce_seconds = debounce_seconds
        self.verbose = verbose
        self._pending_sync = False
        self._last_event_time = 0
        self._lock = threading.Lock()
        self._debounce_timer: Optional[threading.Timer] = None

    def _should_process(self, path: str) -> bool:
        """Check if file should trigger sync."""
        path_obj = Path(path)

        # Only process .md files
        if path_obj.suffix.lower() != '.md':
            return False

        # Skip hidden files and directories
        for part in path_obj.parts:
            if part.startswith('.') and part not in ['.memory']:
                return False

        return True

    def _schedule_sync(self, event_type: str, path: str):
        """Schedule sync with debouncing."""
        with self._lock:
            # Cancel previous timer if exists
            if self._debounce_timer:
                self._debounce_timer.cancel()

            self._pending_sync = True
            self._last_event_time = time.time()

            # Schedule new sync after debounce period
            self._debounce_timer = threading.Timer(
                self.debounce_seconds,
                self._trigger_sync,
                args=[event_type, path]
            )
            self._debounce_timer.start()

    def _trigger_sync(self, event_type: str, path: str):
        """Trigger the sync callback."""
        with self._lock:
            self._pending_sync = False
            self._debounce_timer = None

        self.on_change(event_type, path)

    def on_modified(self, event):
        """Handle file modification."""
        if event.is_directory:
            return

        if self._should_process(event.src_path):
            if self.verbose:
                print(f"[watch] Modified: {event.src_path}")
            self._schedule_sync("modified", event.src_path)

    def on_created(self, event):
        """Handle file creation."""
        if event.is_directory:
            return

        if self._should_process(event.src_path):
            if self.verbose:
                print(f"[watch] Created: {event.src_path}")
            self._schedule_sync("created", event.src_path)

    def on_deleted(self, event):
        """Handle file deletion."""
        if event.is_directory:
            return

        if self._should_process(event.src_path):
            if self.verbose:
                print(f"[watch] Deleted: {event.src_path}")
            self._schedule_sync("deleted", event.src_path)

    def on_moved(self, event):
        """Handle file move/rename."""
        if event.is_directory:
            return

        if self._should_process(event.dest_path):
            if self.verbose:
                print(f"[watch] Moved: {event.src_path} -> {event.dest_path}")
            self._schedule_sync("moved", event.dest_path)


class NotionWatcher:
    """Watch local modules and sync with Notion on changes."""

    def __init__(
        self,
        memory_root: Optional[Path] = None,
        debounce_seconds: float = 2.0,
        verbose: bool = True,
        dry_run: bool = False
    ):
        """Initialize watcher.

        Args:
            memory_root: Path to .memory directory (auto-detected if None)
            debounce_seconds: Wait time before triggering sync
            verbose: Print verbose output
            dry_run: Only show what would sync, don't actually sync
        """
        if not WATCHDOG_AVAILABLE:
            raise ImportError(
                "watchdog is required for file watching. "
                "Install with: pip install memory-tool[watch]"
            )

        self.memory_root = memory_root or self._find_memory_root()
        self.modules_dir = self.memory_root / "modules"
        self.debounce_seconds = debounce_seconds
        self.verbose = verbose
        self.dry_run = dry_run
        self._observer: Optional[Observer] = None
        self._running = False
        self._sync_count = 0

    def _find_memory_root(self) -> Path:
        """Find .memory directory from current working directory."""
        current = Path.cwd()

        # Check current directory
        if (current / ".memory").exists():
            return current / ".memory"

        # Check parent directories
        for parent in current.parents:
            if (parent / ".memory").exists():
                return parent / ".memory"

        raise FileNotFoundError(
            "Could not find .memory directory. "
            "Run 'minit' to initialize or navigate to a project with .memory/"
        )

    def _on_change(self, event_type: str, file_path: str):
        """Handle file change by triggering sync."""
        self._sync_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S")

        if self.dry_run:
            print(f"\n[{timestamp}] Change detected ({event_type}): {file_path}")
            print(f"[{timestamp}] Would run: nsync --verbose")
            return

        print(f"\n[{timestamp}] Change detected ({event_type})")
        print(f"[{timestamp}] Running sync...")

        try:
            from memory_tool.notion.sync import ModuleSyncer

            syncer = ModuleSyncer()
            result = syncer.sync(verbose=self.verbose)

            pushed = result.get("pushed", 0)
            pulled = result.get("pulled", 0)
            errors = result.get("errors", [])

            if errors:
                print(f"[{timestamp}] Sync completed with errors: {pushed} pushed, {pulled} pulled, {len(errors)} errors")
            elif pushed or pulled:
                print(f"[{timestamp}] Sync completed: {pushed} pushed, {pulled} pulled")
            else:
                print(f"[{timestamp}] No changes to sync")

        except Exception as e:
            print(f"[{timestamp}] Sync failed: {e}")

    def start(self):
        """Start watching for file changes."""
        if not self.modules_dir.exists():
            raise FileNotFoundError(
                f"Modules directory not found: {self.modules_dir}\n"
                "Run 'minit' to initialize or create modules first."
            )

        self._observer = Observer()
        handler = ModuleChangeHandler(
            on_change=self._on_change,
            debounce_seconds=self.debounce_seconds,
            verbose=self.verbose
        )

        self._observer.schedule(handler, str(self.modules_dir), recursive=True)
        self._observer.start()
        self._running = True

        mode = "(dry-run)" if self.dry_run else ""
        print(f"Watching for changes in: {self.modules_dir} {mode}")
        print(f"Debounce: {self.debounce_seconds}s")
        print("Press Ctrl+C to stop\n")

    def stop(self):
        """Stop watching."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._running = False
            print(f"\nStopped watching. Total syncs triggered: {self._sync_count}")

    def run_forever(self):
        """Run watcher until interrupted."""
        self.start()
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()


def check_watchdog_available() -> bool:
    """Check if watchdog is installed."""
    return WATCHDOG_AVAILABLE
