"""File watcher for automatic Notion sync.

Watches local .memory/ directory for changes and triggers sync:
- modules/ changes -> nsync (module sync)
- timeline/ changes -> nm (timeline mirror to Notion)
"""

import time
import threading
import re
from pathlib import Path
from typing import Optional, Callable, Set
from datetime import datetime

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object


class ChangeHandler(FileSystemEventHandler):
    """Handle file system events for .memory/ directory."""

    def __init__(
        self,
        on_module_change: Callable[[str, str], None],
        on_timeline_change: Callable[[str, str], None],
        debounce_seconds: float = 2.0,
        verbose: bool = False
    ):
        """Initialize handler.

        Args:
            on_module_change: Callback for module changes
            on_timeline_change: Callback for timeline changes
            debounce_seconds: Wait time before triggering sync
            verbose: Print verbose output
        """
        super().__init__()
        self.on_module_change = on_module_change
        self.on_timeline_change = on_timeline_change
        self.debounce_seconds = debounce_seconds
        self.verbose = verbose
        self._lock = threading.Lock()

        # Separate debounce timers for modules and timeline
        self._module_timer: Optional[threading.Timer] = None
        self._timeline_timer: Optional[threading.Timer] = None
        self._timeline_pending_files: Set[str] = set()

    def _get_change_type(self, path: str) -> Optional[str]:
        """Determine if path is module or timeline change."""
        path_str = str(path).replace("\\", "/")

        if "/modules/" in path_str and path_str.endswith(".md"):
            return "module"
        elif "/timeline/" in path_str and path_str.endswith(".md"):
            return "timeline"
        return None

    def _schedule_module_sync(self, event_type: str, path: str):
        """Schedule module sync with debouncing."""
        with self._lock:
            if self._module_timer:
                self._module_timer.cancel()

            self._module_timer = threading.Timer(
                self.debounce_seconds,
                self._trigger_module_sync,
                args=[event_type, path]
            )
            self._module_timer.start()

    def _trigger_module_sync(self, event_type: str, path: str):
        """Trigger module sync callback."""
        with self._lock:
            self._module_timer = None
        self.on_module_change(event_type, path)

    def _schedule_timeline_sync(self, event_type: str, path: str):
        """Schedule timeline sync with debouncing."""
        with self._lock:
            if self._timeline_timer:
                self._timeline_timer.cancel()

            self._timeline_pending_files.add(path)

            self._timeline_timer = threading.Timer(
                self.debounce_seconds,
                self._trigger_timeline_sync,
                args=[event_type]
            )
            self._timeline_timer.start()

    def _trigger_timeline_sync(self, event_type: str):
        """Trigger timeline sync callback."""
        with self._lock:
            self._timeline_timer = None
            files = list(self._timeline_pending_files)
            self._timeline_pending_files.clear()

        # Call callback with the most recent file
        if files:
            self.on_timeline_change(event_type, files[-1])

    def on_modified(self, event):
        """Handle file modification."""
        if event.is_directory:
            return

        change_type = self._get_change_type(event.src_path)
        if change_type == "module":
            if self.verbose:
                print(f"[watch] Module modified: {Path(event.src_path).name}")
            self._schedule_module_sync("modified", event.src_path)
        elif change_type == "timeline":
            if self.verbose:
                print(f"[watch] Timeline modified: {Path(event.src_path).name}")
            self._schedule_timeline_sync("modified", event.src_path)

    def on_created(self, event):
        """Handle file creation."""
        if event.is_directory:
            return

        change_type = self._get_change_type(event.src_path)
        if change_type == "module":
            if self.verbose:
                print(f"[watch] Module created: {Path(event.src_path).name}")
            self._schedule_module_sync("created", event.src_path)
        elif change_type == "timeline":
            if self.verbose:
                print(f"[watch] Timeline created: {Path(event.src_path).name}")
            self._schedule_timeline_sync("created", event.src_path)


class NotionWatcher:
    """Watch local modules and timeline, sync with Notion on changes."""

    def __init__(
        self,
        memory_root: Optional[Path] = None,
        debounce_seconds: float = 2.0,
        verbose: bool = True,
        dry_run: bool = False,
        watch_modules: bool = True,
        watch_timeline: bool = True,
    ):
        """Initialize watcher.

        Args:
            memory_root: Path to .memory directory (auto-detected if None)
            debounce_seconds: Wait time before triggering sync
            verbose: Print verbose output
            dry_run: Only show what would sync, don't actually sync
            watch_modules: Watch modules directory
            watch_timeline: Watch timeline directory
        """
        if not WATCHDOG_AVAILABLE:
            raise ImportError(
                "watchdog is required for file watching. "
                "Install with: pip install memory-tool[watch]"
            )

        self.memory_root = memory_root or self._find_memory_root()
        self.modules_dir = self.memory_root / "modules"
        self.timeline_dir = self.memory_root / "timeline"
        self.debounce_seconds = debounce_seconds
        self.verbose = verbose
        self.dry_run = dry_run
        self.watch_modules = watch_modules
        self.watch_timeline = watch_timeline
        self._observer: Optional[Observer] = None
        self._running = False
        self._module_sync_count = 0
        self._timeline_sync_count = 0
        self._last_timeline_content: dict = {}  # Track timeline content to find new entries

    def _find_memory_root(self) -> Path:
        """Find .memory directory from current working directory."""
        current = Path.cwd()

        if (current / ".memory").exists():
            return current / ".memory"

        for parent in current.parents:
            if (parent / ".memory").exists():
                return parent / ".memory"

        raise FileNotFoundError(
            "Could not find .memory directory. "
            "Run 'minit' to initialize or navigate to a project with .memory/"
        )

    def _on_module_change(self, event_type: str, file_path: str):
        """Handle module change by triggering nsync."""
        self._module_sync_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S")

        if self.dry_run:
            print(f"\n[{timestamp}] Module change detected ({event_type})")
            print(f"[{timestamp}] Would run: nsync")
            return

        print(f"\n[{timestamp}] Module change detected")
        print(f"[{timestamp}] Running module sync...")

        try:
            from memory_tool.notion.sync import ModuleSyncer

            syncer = ModuleSyncer()
            result = syncer.sync(verbose=self.verbose)

            pushed = result.get("pushed", 0)
            pulled = result.get("pulled", 0)
            errors = result.get("errors", [])

            if errors:
                print(f"[{timestamp}] Module sync: {pushed} pushed, {pulled} pulled, {len(errors)} errors")
            elif pushed or pulled:
                print(f"[{timestamp}] Module sync: {pushed} pushed, {pulled} pulled")
            else:
                print(f"[{timestamp}] No module changes to sync")

        except Exception as e:
            print(f"[{timestamp}] Module sync failed: {e}")

    def _on_timeline_change(self, event_type: str, file_path: str):
        """Handle timeline change by syncing new entries to Notion."""
        self._timeline_sync_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S")

        try:
            # Read the timeline file
            timeline_path = Path(file_path)
            if not timeline_path.exists():
                return

            content = timeline_path.read_text(encoding="utf-8")

            # Parse timeline entries (format: "- HH:MM | message")
            new_entries = self._find_new_entries(file_path, content)

            if not new_entries:
                if self.verbose:
                    print(f"[{timestamp}] No new timeline entries to sync")
                return

            if self.dry_run:
                print(f"\n[{timestamp}] Timeline change detected: {len(new_entries)} new entries")
                for entry in new_entries:
                    print(f"[{timestamp}] Would sync: {entry['time']} | {entry['message'][:50]}...")
                return

            print(f"\n[{timestamp}] Timeline change detected: {len(new_entries)} new entries")

            # Sync each new entry to Notion
            from memory_tool.notion.client import NotionClient, NotionError

            try:
                client = NotionClient()

                # Get the date from file path (e.g., .../2026-01/16.md)
                date_str = self._extract_date_from_path(file_path)
                if date_str:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                else:
                    date_obj = datetime.now()

                # Get or create daily page
                page_id = client.get_or_create_daily_page(date_obj)

                for entry in new_entries:
                    try:
                        client.append_timeline_entry(page_id, entry['time'], entry['message'])
                        print(f"[{timestamp}] Synced: {entry['time']} | {entry['message'][:40]}...")
                    except NotionError as e:
                        print(f"[{timestamp}] Failed to sync entry: {e}")

            except NotionError as e:
                print(f"[{timestamp}] Timeline sync failed: {e}")

        except Exception as e:
            print(f"[{timestamp}] Timeline sync error: {e}")

    def _find_new_entries(self, file_path: str, content: str) -> list:
        """Find new timeline entries that haven't been synced yet."""
        # Parse all entries from content
        entry_pattern = re.compile(r"^- (\d{1,2}:\d{2})\s*\|\s*(.+)$", re.MULTILINE)
        current_entries = []

        for match in entry_pattern.finditer(content):
            current_entries.append({
                'time': match.group(1),
                'message': match.group(2).strip(),
                'raw': match.group(0)
            })

        # Get previously seen content
        prev_content = self._last_timeline_content.get(file_path, "")

        # Update cached content
        self._last_timeline_content[file_path] = content

        # If first time seeing this file, don't sync (avoid re-syncing existing entries)
        if not prev_content:
            return []

        # Find entries that are new (not in previous content)
        prev_entries_raw = set()
        for match in entry_pattern.finditer(prev_content):
            prev_entries_raw.add(match.group(0))

        new_entries = [e for e in current_entries if e['raw'] not in prev_entries_raw]

        return new_entries

    def _extract_date_from_path(self, file_path: str) -> Optional[str]:
        """Extract date from timeline file path."""
        # Pattern: .../YYYY-MM/DD.md
        match = re.search(r"(\d{4}-\d{2})[/\\](\d{1,2})\.md$", file_path)
        if match:
            year_month = match.group(1)
            day = match.group(2).zfill(2)
            return f"{year_month}-{day}"
        return None

    def start(self):
        """Start watching for file changes."""
        self._observer = Observer()
        handler = ChangeHandler(
            on_module_change=self._on_module_change,
            on_timeline_change=self._on_timeline_change,
            debounce_seconds=self.debounce_seconds,
            verbose=self.verbose
        )

        watched_dirs = []

        if self.watch_modules and self.modules_dir.exists():
            self._observer.schedule(handler, str(self.modules_dir), recursive=True)
            watched_dirs.append(f"modules/")

        if self.watch_timeline and self.timeline_dir.exists():
            self._observer.schedule(handler, str(self.timeline_dir), recursive=True)
            watched_dirs.append(f"timeline/")
            # Pre-load existing timeline content to avoid re-syncing
            self._preload_timeline_content()

        if not watched_dirs:
            raise FileNotFoundError(
                "No directories to watch. Ensure modules/ or timeline/ exist in .memory/"
            )

        self._observer.start()
        self._running = True

        mode = "(dry-run)" if self.dry_run else ""
        print(f"Watching: {', '.join(watched_dirs)} {mode}")
        print(f"Debounce: {self.debounce_seconds}s")
        print("Press Ctrl+C to stop\n")

    def _preload_timeline_content(self):
        """Pre-load existing timeline content to track new entries only."""
        for md_file in self.timeline_dir.glob("**/*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                self._last_timeline_content[str(md_file)] = content
            except Exception:
                pass

    def stop(self):
        """Stop watching."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._running = False
            print(f"\nStopped. Module syncs: {self._module_sync_count}, Timeline syncs: {self._timeline_sync_count}")

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
