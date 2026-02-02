"""File watcher for automatic Notion sync.

Watches local .memory/ directory for changes and triggers sync:
- modules/ changes -> nsync (module sync)
- timeline/ changes -> nm (timeline mirror to Notion)
- plans/ changes -> plan sync to Notion
"""

import time
import threading
import re
from pathlib import Path
from typing import Optional, Callable, Set
from datetime import datetime

try:
    from watchdog.observers.polling import PollingObserver as Observer
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
        on_module_change: Callable[[str, Set[str]], None],
        on_timeline_change: Callable[[str, str], None],
        on_plan_change: Optional[Callable[[str, str, str], None]] = None,
        on_module_move: Optional[Callable[[str, str], None]] = None,
        on_module_delete: Optional[Callable[[str], None]] = None,
        debounce_seconds: float = 2.0,
        verbose: bool = False,
        modules_dir: Optional[Path] = None,
        plans_dir: Optional[Path] = None,
    ):
        """Initialize handler.

        Args:
            on_module_change: Callback for module changes (event_type, module_paths)
            on_timeline_change: Callback for timeline changes
            on_plan_change: Callback for plan changes (event_type, plan_type, file_path)
            on_module_move: Callback for module file moves (src_path, dest_path)
            on_module_delete: Callback for module file deletes (file_path)
            debounce_seconds: Wait time before triggering sync
            verbose: Print verbose output
            modules_dir: Path to modules directory for extracting module paths
            plans_dir: Path to plans directory for extracting plan paths
        """
        super().__init__()
        self.on_module_change = on_module_change
        self.on_timeline_change = on_timeline_change
        self.on_plan_change = on_plan_change
        self.on_module_move = on_module_move
        self.on_module_delete = on_module_delete
        self.debounce_seconds = debounce_seconds
        self.verbose = verbose
        self.modules_dir = modules_dir
        self.plans_dir = plans_dir
        self._lock = threading.Lock()

        # Separate debounce timers for modules, timeline, and plans
        self._module_timer: Optional[threading.Timer] = None
        self._timeline_timer: Optional[threading.Timer] = None
        self._plan_timer: Optional[threading.Timer] = None
        self._module_pending_paths: Set[str] = set()  # Track changed module paths
        self._timeline_pending_files: Set[str] = set()
        self._plan_pending_files: Set[tuple] = set()  # (plan_type, file_path)

        # Track pending moves and deletes for debouncing
        self._module_pending_moves: list = []  # [(src_path, dest_path), ...]
        self._module_pending_deletes: Set[str] = set()  # {file_path, ...}

    def _get_change_type(self, path: str) -> Optional[str]:
        """Determine if path is module, timeline, or plan change."""
        path_str = str(path).replace("\\", "/")

        if "/modules/" in path_str and path_str.endswith(".md"):
            return "module"
        elif "/timeline/" in path_str and path_str.endswith(".md"):
            return "timeline"
        elif "/plans/daily/" in path_str and path_str.endswith(".md"):
            return "plan_daily"
        elif "/plans/weekly/" in path_str and path_str.endswith(".md"):
            return "plan_weekly"
        elif "/plans/monthly/" in path_str and path_str.endswith(".md"):
            return "plan_monthly"
        return None

    def _extract_module_path(self, file_path: str) -> Optional[str]:
        """Extract module path from file path.

        Args:
            file_path: Full path to the changed file

        Returns:
            Module path relative to modules directory (e.g., "게임 분석/니케")
        """
        if not self.modules_dir:
            return None

        try:
            file_path_obj = Path(file_path)
            # Get parent directory (the module directory containing the .md file)
            module_dir = file_path_obj.parent
            # Get relative path from modules_dir
            rel_path = module_dir.relative_to(self.modules_dir)
            return str(rel_path).replace("\\", "/")
        except (ValueError, Exception):
            return None

    def _schedule_module_sync(self, event_type: str, path: str):
        """Schedule module sync with debouncing.

        Uses unified _trigger_module_changes to handle all module events together.
        """
        with self._lock:
            if self._module_timer:
                self._module_timer.cancel()

            # Track the module path
            module_path = self._extract_module_path(path)
            if module_path:
                self._module_pending_paths.add(module_path)

            self._module_timer = threading.Timer(
                self.debounce_seconds,
                self._trigger_module_changes,
            )
            self._module_timer.start()

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

    def _schedule_plan_sync(self, event_type: str, plan_type: str, path: str):
        """Schedule plan sync with debouncing."""
        if not self.on_plan_change:
            return

        with self._lock:
            if self._plan_timer:
                self._plan_timer.cancel()

            self._plan_pending_files.add((plan_type, path))

            self._plan_timer = threading.Timer(
                self.debounce_seconds,
                self._trigger_plan_sync,
                args=[event_type]
            )
            self._plan_timer.start()

    def _trigger_plan_sync(self, event_type: str):
        """Trigger plan sync callback."""
        with self._lock:
            self._plan_timer = None
            pending = list(self._plan_pending_files)
            self._plan_pending_files.clear()

        # Call callback for each pending plan file
        if pending and self.on_plan_change:
            for plan_type, file_path in pending:
                self.on_plan_change(event_type, plan_type, file_path)

    def on_any_event(self, event):
        """Debug: Log all events."""
        if self.verbose and not event.is_directory:
            print(f"[watch:debug] Event: {event.event_type} -> {event.src_path}")

    def on_modified(self, event):
        """Handle file modification."""
        if event.is_directory:
            return

        change_type = self._get_change_type(event.src_path)
        if self.verbose:
            print(f"[watch:debug] Modified change_type={change_type} path={event.src_path}")

        if change_type == "module":
            print(f"[watch] Module modified: {Path(event.src_path).name}")
            self._schedule_module_sync("modified", event.src_path)
        elif change_type == "timeline":
            print(f"[watch] Timeline modified: {Path(event.src_path).name}")
            self._schedule_timeline_sync("modified", event.src_path)
        elif change_type and change_type.startswith("plan_"):
            plan_type = change_type.replace("plan_", "")
            print(f"[watch] Plan ({plan_type}) modified: {Path(event.src_path).name}")
            self._schedule_plan_sync("modified", plan_type, event.src_path)

    def on_created(self, event):
        """Handle file creation."""
        if event.is_directory:
            return

        change_type = self._get_change_type(event.src_path)
        if self.verbose:
            print(f"[watch:debug] Created change_type={change_type} path={event.src_path}")

        if change_type == "module":
            print(f"[watch] Module created: {Path(event.src_path).name}")
            self._schedule_module_sync("created", event.src_path)
        elif change_type == "timeline":
            print(f"[watch] Timeline created: {Path(event.src_path).name}")
            self._schedule_timeline_sync("created", event.src_path)
        elif change_type and change_type.startswith("plan_"):
            plan_type = change_type.replace("plan_", "")
            print(f"[watch] Plan ({plan_type}) created: {Path(event.src_path).name}")
            self._schedule_plan_sync("created", plan_type, event.src_path)

    def on_deleted(self, event):
        """Handle file deletion."""
        if event.is_directory:
            return

        change_type = self._get_change_type(event.src_path)
        if self.verbose:
            print(f"[watch:debug] Deleted change_type={change_type} path={event.src_path}")

        if change_type == "module":
            print(f"[watch] Module deleted: {Path(event.src_path).name}")
            self._schedule_module_delete(event.src_path)

    def on_moved(self, event):
        """Handle file move/rename.

        This is crucial for preventing duplicate Notion pages when files are moved.
        Instead of treating moves as delete+create, we track the src->dest mapping
        and transfer the Notion page ID to the new location.
        """
        if event.is_directory:
            return

        src_change_type = self._get_change_type(event.src_path)
        dest_change_type = self._get_change_type(event.dest_path)

        if self.verbose:
            print(f"[watch:debug] Moved src_type={src_change_type} dest_type={dest_change_type}")
            print(f"[watch:debug]   src={event.src_path}")
            print(f"[watch:debug]   dest={event.dest_path}")

        # Handle module file moves
        if src_change_type == "module" or dest_change_type == "module":
            src_name = Path(event.src_path).name
            dest_name = Path(event.dest_path).name
            print(f"[watch] Module moved: {src_name} -> {dest_name}")
            self._schedule_module_move(event.src_path, event.dest_path)

    def _schedule_module_delete(self, path: str):
        """Schedule module delete handling with debouncing."""
        if not self.on_module_delete:
            return

        with self._lock:
            if self._module_timer:
                self._module_timer.cancel()

            self._module_pending_deletes.add(path)

            self._module_timer = threading.Timer(
                self.debounce_seconds,
                self._trigger_module_changes,
            )
            self._module_timer.start()

    def _schedule_module_move(self, src_path: str, dest_path: str):
        """Schedule module move handling with debouncing."""
        if not self.on_module_move:
            # Fallback: treat as delete + create
            self._schedule_module_delete(src_path)
            self._schedule_module_sync("created", dest_path)
            return

        with self._lock:
            if self._module_timer:
                self._module_timer.cancel()

            self._module_pending_moves.append((src_path, dest_path))

            self._module_timer = threading.Timer(
                self.debounce_seconds,
                self._trigger_module_changes,
            )
            self._module_timer.start()

    def _trigger_module_changes(self):
        """Trigger all pending module changes (moves, deletes, syncs)."""
        with self._lock:
            self._module_timer = None
            pending_moves = self._module_pending_moves.copy()
            pending_deletes = self._module_pending_deletes.copy()
            pending_paths = self._module_pending_paths.copy()
            self._module_pending_moves.clear()
            self._module_pending_deletes.clear()
            self._module_pending_paths.clear()

        # Process moves first (transfer state before creating new pages)
        for src_path, dest_path in pending_moves:
            if self.on_module_move:
                self.on_module_move(src_path, dest_path)

        # Process deletes (archive old Notion pages)
        for path in pending_deletes:
            if self.on_module_delete:
                self.on_module_delete(path)

        # Process regular syncs
        if pending_paths:
            self.on_module_change("modified", pending_paths)


class NotionWatcher:
    """Watch local modules, timeline, and plans, sync with Notion on changes."""

    def __init__(
        self,
        memory_root: Optional[Path] = None,
        debounce_seconds: float = 2.0,
        verbose: bool = True,
        dry_run: bool = False,
        watch_modules: bool = True,
        watch_timeline: bool = True,
        watch_plans: bool = True,
        bidirectional: bool = False,
        poll_interval: int = 120,
    ):
        """Initialize watcher.

        Args:
            memory_root: Path to .memory directory (auto-detected if None)
            debounce_seconds: Wait time before triggering sync
            verbose: Print verbose output
            dry_run: Only show what would sync, don't actually sync
            watch_modules: Watch modules directory
            watch_timeline: Watch timeline directory
            watch_plans: Watch plans directory
            bidirectional: Enable Notion -> Local sync via polling
            poll_interval: Seconds between Notion polling (default: 120)
        """
        if not WATCHDOG_AVAILABLE:
            raise ImportError(
                "watchdog is required for file watching. "
                "Install with: pip install memory-tool[watch]"
            )

        self.memory_root = memory_root or self._find_memory_root()
        self.modules_dir = self.memory_root / "modules"
        self.timeline_dir = self.memory_root / "timeline"
        self.plans_dir = self.memory_root / "plans"
        self.debounce_seconds = debounce_seconds
        self.verbose = verbose
        self.dry_run = dry_run
        self.watch_modules = watch_modules
        self.watch_timeline = watch_timeline
        self.watch_plans = watch_plans
        self.bidirectional = bidirectional
        self.poll_interval = poll_interval
        self._observer: Optional[Observer] = None
        self._poll_thread: Optional[threading.Thread] = None
        self._running = False
        self._module_sync_count = 0
        self._module_pull_count = 0
        self._timeline_sync_count = 0
        self._timeline_pull_count = 0
        self._plan_sync_count = 0
        self._plan_pull_count = 0
        self._last_timeline_content: dict = {}  # Track timeline content to find new entries

        # Sync lock to prevent race conditions (duplicate page creation)
        self._sync_lock = threading.Lock()
        self._sync_in_progress = False
        self._pending_modules: Set[str] = set()  # Modules waiting to sync

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

    def _on_module_change(self, event_type: str, module_paths: Set[str]):
        """Handle module change by syncing specific modules only.

        Uses a lock to prevent race conditions where multiple syncs run
        concurrently and create duplicate Notion pages.

        Args:
            event_type: Type of change (created, modified)
            module_paths: Set of module paths that changed
        """
        self._module_sync_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S")

        if not module_paths:
            if self.verbose:
                print(f"[{timestamp}] No module paths to sync")
            return

        if self.dry_run:
            print(f"\n[{timestamp}] Module change detected ({event_type})")
            for mp in module_paths:
                print(f"[{timestamp}] Would sync module: {mp}")
            return

        # Check if sync is already in progress
        with self._sync_lock:
            if self._sync_in_progress:
                # Add to pending and return - will be processed after current sync
                self._pending_modules.update(module_paths)
                print(f"[{timestamp}] Sync in progress, queued {len(module_paths)} module(s)")
                return
            self._sync_in_progress = True

        print(f"\n[{timestamp}] Module change detected: {len(module_paths)} module(s)")

        try:
            self._do_module_sync(module_paths, timestamp)
        finally:
            # Process any pending modules that accumulated during sync
            self._process_pending_modules()

    def _do_module_sync(self, module_paths: Set[str], timestamp: str):
        """Execute the actual module sync.

        Args:
            module_paths: Set of module paths to sync
            timestamp: Timestamp string for logging
        """
        try:
            from memory_tool.notion.sync import ModuleSyncer

            syncer = ModuleSyncer()
            total_pushed = 0
            total_pulled = 0
            total_errors = []

            for module_path in module_paths:
                if self.verbose:
                    print(f"[{timestamp}] Syncing module: {module_path}")

                result = syncer.sync(module_path=module_path, verbose=self.verbose)

                total_pushed += result.pushed
                total_pulled += result.pulled
                if result.failed > 0:
                    total_errors.extend([r.message for r in result.results if not r.success])

            if total_errors:
                print(f"[{timestamp}] Module sync: {total_pushed} pushed, {total_pulled} pulled, {len(total_errors)} errors")
            elif total_pushed or total_pulled:
                print(f"[{timestamp}] Module sync: {total_pushed} pushed, {total_pulled} pulled")
            else:
                print(f"[{timestamp}] No module changes to sync")

        except Exception as e:
            print(f"[{timestamp}] Module sync failed: {e}")

    def _on_module_move(self, src_path: str, dest_path: str):
        """Handle module file move by transferring sync state.

        When a file is moved, we:
        1. Transfer the Notion page ID from old location to new location
        2. Update the Notion page's parent if the module changed
        3. Archive the old state to prevent orphaned pages

        Args:
            src_path: Original file path
            dest_path: New file path
        """
        timestamp = datetime.now().strftime("%H:%M:%S")

        if self.dry_run:
            print(f"[{timestamp}] Would handle move: {Path(src_path).name} -> {Path(dest_path).name}")
            return

        try:
            from memory_tool.notion.state import SyncStateManager
            from memory_tool.notion.sync import ModuleSyncer

            state_manager = SyncStateManager(self.memory_root)

            # Extract module paths and file names
            src_module_path = self._extract_module_path_from_file(src_path)
            dest_module_path = self._extract_module_path_from_file(dest_path)
            src_file_name = Path(src_path).name
            dest_file_name = Path(dest_path).name

            if not src_module_path or not dest_module_path:
                print(f"[{timestamp}] Could not extract module paths for move")
                return

            # Get the old file's sync state (contains Notion page ID)
            old_state = state_manager.get_file_state(src_module_path, src_file_name)

            if old_state.notion_page_id:
                print(f"[{timestamp}] Transferring Notion page ID: {old_state.notion_page_id[:8]}...")

                # Transfer state to new location
                state_manager.set_file_state(dest_module_path, dest_file_name, old_state)

                # Clear old state to prevent duplicate references
                state_manager.clear_file_state(src_module_path, src_file_name)

                # If module changed, we need to move the Notion page too
                if src_module_path != dest_module_path:
                    print(f"[{timestamp}] Module changed: {src_module_path} -> {dest_module_path}")
                    # The actual Notion page move will happen during next sync
                    # For now, just sync the destination module
                    syncer = ModuleSyncer()
                    syncer.sync(module_path=dest_module_path, verbose=self.verbose)
                else:
                    # Same module, just file renamed - sync to update
                    syncer = ModuleSyncer()
                    syncer.sync(module_path=dest_module_path, verbose=self.verbose)

                print(f"[{timestamp}] Move handled successfully")
            else:
                # No existing Notion page, just sync the new location
                print(f"[{timestamp}] No existing Notion page for moved file")
                syncer = ModuleSyncer()
                syncer.sync(module_path=dest_module_path, verbose=self.verbose)

        except Exception as e:
            print(f"[{timestamp}] Move handling failed: {e}")
            # Fallback: just sync destination
            try:
                from memory_tool.notion.sync import ModuleSyncer
                dest_module_path = self._extract_module_path_from_file(dest_path)
                if dest_module_path:
                    syncer = ModuleSyncer()
                    syncer.sync(module_path=dest_module_path, verbose=self.verbose)
            except Exception:
                pass

    def _on_module_delete(self, file_path: str):
        """Handle module file deletion by archiving Notion page.

        Args:
            file_path: Deleted file path
        """
        timestamp = datetime.now().strftime("%H:%M:%S")

        if self.dry_run:
            print(f"[{timestamp}] Would handle delete: {Path(file_path).name}")
            return

        try:
            from memory_tool.notion.state import SyncStateManager
            from memory_tool.notion.client import NotionClient

            state_manager = SyncStateManager(self.memory_root)

            module_path = self._extract_module_path_from_file(file_path)
            file_name = Path(file_path).name

            if not module_path:
                return

            # Get the file's sync state
            file_state = state_manager.get_file_state(module_path, file_name)

            if file_state.notion_page_id:
                print(f"[{timestamp}] Archiving Notion page for deleted file: {file_name}")

                try:
                    client = NotionClient()
                    # Archive (soft delete) the Notion page
                    client.archive_page(file_state.notion_page_id)
                    print(f"[{timestamp}] Archived Notion page: {file_state.notion_page_id[:8]}...")
                except Exception as e:
                    print(f"[{timestamp}] Failed to archive Notion page: {e}")

                # Clear the sync state
                state_manager.clear_file_state(module_path, file_name)
            else:
                if self.verbose:
                    print(f"[{timestamp}] No Notion page to archive for: {file_name}")

        except Exception as e:
            print(f"[{timestamp}] Delete handling failed: {e}")

    def _extract_module_path_from_file(self, file_path: str) -> Optional[str]:
        """Extract module path from a full file path.

        Args:
            file_path: Full path to file

        Returns:
            Module path relative to modules directory
        """
        if not self.modules_dir:
            return None

        try:
            file_path_obj = Path(file_path)
            module_dir = file_path_obj.parent
            rel_path = module_dir.relative_to(self.modules_dir)
            return str(rel_path).replace("\\", "/")
        except (ValueError, Exception):
            return None

    def _process_pending_modules(self):
        """Process any modules that were queued during an active sync."""
        while True:
            with self._sync_lock:
                if not self._pending_modules:
                    self._sync_in_progress = False
                    return
                # Take all pending modules and clear the set
                modules_to_sync = self._pending_modules.copy()
                self._pending_modules.clear()

            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{timestamp}] Processing {len(modules_to_sync)} queued module(s)")
            self._do_module_sync(modules_to_sync, timestamp)

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
            new_entries = self._find_new_entries(file_path, content, event_type)

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
            from memory_tool.utils.config import Config

            try:
                client = NotionClient()

                # Get timeline root_page_id from config
                config = Config()
                timeline_root_page_id = config.get("notion.sync.timeline.root_page_id")

                # Get the date from file path (e.g., .../2026-01/16.md)
                date_str = self._extract_date_from_path(file_path)
                if date_str:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                else:
                    date_obj = datetime.now()

                # Get or create daily page (pass timeline-specific root_page_id)
                page_id = client.get_or_create_daily_page(date_obj, timeline_root_page_id)

                for entry in new_entries:
                    try:
                        # Create full datetime by combining date and time
                        try:
                            time_parts = entry['time'].split(':')
                            entry_datetime = date_obj.replace(
                                hour=int(time_parts[0]),
                                minute=int(time_parts[1]),
                                second=0,
                                microsecond=0
                            )
                        except (ValueError, IndexError):
                            entry_datetime = date_obj

                        client.append_timeline_entry(
                            page_id, entry['time'], entry['message'],
                            date_obj=entry_datetime
                        )
                        print(f"[{timestamp}] Synced: {entry['time']} | {entry['message'][:40]}...")
                    except NotionError as e:
                        print(f"[{timestamp}] Failed to sync entry: {e}")

            except NotionError as e:
                print(f"[{timestamp}] Timeline sync failed: {e}")

        except Exception as e:
            print(f"[{timestamp}] Timeline sync error: {e}")

    def _strip_tags_for_key(self, message: str) -> str:
        """Remove hashtags and bracket tags from message for comparison.

        This ensures tag changes don't create duplicate entries.
        """
        # Remove #hashtags (including Korean)
        stripped = re.sub(r'#[\w가-힣-]+', '', message)
        # Remove [bracket tags] (including Korean and spaces)
        stripped = re.sub(r'\[[\w가-힣\s-]+\]', '', stripped)
        # Clean up extra spaces
        stripped = re.sub(r'\s+', ' ', stripped).strip()
        return stripped

    def _entry_key(self, time_str: str, message: str) -> str:
        """Create a stable key for an entry (tags stripped)."""
        # Normalize time
        if ":" in time_str:
            parts = time_str.split(":")
            normalized_time = f"{int(parts[0]):02d}:{parts[1]}"
        else:
            normalized_time = time_str
        # Strip tags for stable comparison
        clean_message = self._strip_tags_for_key(message)
        return f"{normalized_time}|{clean_message[:50].lower()}"

    def _find_new_entries(self, file_path: str, content: str, event_type: str = "modified") -> list:
        """Find new timeline entries that haven't been synced yet.

        Args:
            file_path: Path to the timeline file
            content: Current file content
            event_type: "created" or "modified" - created files sync all entries
        """
        # Parse all entries from content
        entry_pattern = re.compile(r"^- (\d{1,2}:\d{2})\s*\|\s*(.+)$", re.MULTILINE)
        current_entries = []

        for match in entry_pattern.finditer(content):
            entry = {
                'time': match.group(1),
                'message': match.group(2).strip(),
                'raw': match.group(0)
            }
            entry['key'] = self._entry_key(entry['time'], entry['message'])
            current_entries.append(entry)

        # Get previously seen content
        prev_content = self._last_timeline_content.get(file_path, "")

        # Update cached content
        self._last_timeline_content[file_path] = content

        # For newly created files (not preloaded), sync all entries
        # This ensures the first entry of a new day's timeline is synced
        if not prev_content:
            if event_type == "created":
                # New file created during watch - sync all entries
                return current_entries
            else:
                # File existed before watch started (preloaded) - skip to avoid re-sync
                return []

        # Find entries that are new (not in previous content by key, not raw)
        prev_entries_keys = set()
        for match in entry_pattern.finditer(prev_content):
            key = self._entry_key(match.group(1), match.group(2).strip())
            prev_entries_keys.add(key)

        # Only sync entries with new keys (tag changes won't trigger re-sync)
        new_entries = [e for e in current_entries if e['key'] not in prev_entries_keys]

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

    def _on_plan_change(self, event_type: str, plan_type: str, file_path: str):
        """Handle plan change by syncing to Notion."""
        self._plan_sync_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S")

        if self.dry_run:
            print(f"\n[{timestamp}] Plan ({plan_type}) change detected ({event_type})")
            print(f"[{timestamp}] Would sync: {Path(file_path).name}")
            return

        print(f"\n[{timestamp}] Plan ({plan_type}) change detected: {Path(file_path).name}")

        try:
            from memory_tool.notion.plan_sync import PlanSyncer

            plan_syncer = PlanSyncer()

            if not plan_syncer.enabled:
                if self.verbose:
                    print(f"[{timestamp}] Plan sync not enabled, skipping")
                return

            # Extract date from file path and sync that specific plan
            result = plan_syncer.sync(
                plan_type=plan_type,
                days=1,  # Only sync today's changes
                push_only=True,  # Only push local changes
                dry_run=self.dry_run,
                verbose=self.verbose,
            )

            pushed = result.get("pushed", 0)
            updated = result.get("updated", 0)
            errors = result.get("errors", [])

            if pushed or updated:
                print(f"[{timestamp}] Plan sync: {pushed} pushed, {updated} updated")
            elif errors:
                print(f"[{timestamp}] Plan sync errors: {len(errors)}")
                for err in errors:
                    print(f"  - {err}")
            else:
                print(f"[{timestamp}] No plan changes to sync")

        except Exception as e:
            print(f"[{timestamp}] Plan sync failed: {e}")

    def start(self):
        """Start watching for file changes."""
        self._observer = Observer()
        handler = ChangeHandler(
            on_module_change=self._on_module_change,
            on_timeline_change=self._on_timeline_change,
            on_plan_change=self._on_plan_change if self.watch_plans else None,
            on_module_move=self._on_module_move if self.watch_modules else None,
            on_module_delete=self._on_module_delete if self.watch_modules else None,
            debounce_seconds=self.debounce_seconds,
            verbose=self.verbose,
            modules_dir=self.modules_dir,
            plans_dir=self.plans_dir,
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

        if self.watch_plans and self.plans_dir.exists():
            self._observer.schedule(handler, str(self.plans_dir), recursive=True)
            watched_dirs.append(f"plans/")

        if not watched_dirs:
            raise FileNotFoundError(
                "No directories to watch. Ensure modules/, timeline/, or plans/ exist in .memory/"
            )

        self._observer.start()
        self._running = True

        # Start polling thread if bidirectional
        if self.bidirectional:
            self._poll_thread = threading.Thread(target=self._poll_notion_loop, daemon=True)
            self._poll_thread.start()

        mode = "(dry-run)" if self.dry_run else ""
        bidir_mode = "(bidirectional)" if self.bidirectional else "(Local -> Notion)"
        print(f"Watching: {', '.join(watched_dirs)} {mode} {bidir_mode}")
        print(f"Debounce: {self.debounce_seconds}s")
        if self.bidirectional:
            print(f"Notion poll interval: {self.poll_interval}s")
        if self.verbose:
            print(f"[debug] Memory root: {self.memory_root}")
            print(f"[debug] Modules dir: {self.modules_dir} (exists: {self.modules_dir.exists()})")
            print(f"[debug] Timeline dir: {self.timeline_dir} (exists: {self.timeline_dir.exists()})")
        print("Press Ctrl+C to stop\n")

    def _preload_timeline_content(self):
        """Pre-load existing timeline content to track new entries only."""
        for md_file in self.timeline_dir.glob("**/*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                self._last_timeline_content[str(md_file)] = content
            except Exception:
                pass

    def _poll_notion_loop(self):
        """Polling loop to check Notion for changes."""
        while self._running:
            try:
                self._poll_notion()
            except Exception as e:
                if self.verbose:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[{timestamp}] Notion poll error: {e}")

            # Sleep in small increments to allow quick shutdown
            for _ in range(self.poll_interval):
                if not self._running:
                    break
                time.sleep(1)

    def _poll_notion(self):
        """Poll Notion for changes and pull to local (modules + timeline)."""
        timestamp = datetime.now().strftime("%H:%M:%S")

        if self.verbose:
            print(f"[{timestamp}] Polling Notion for changes...")

        total_pulled = 0
        all_errors = []

        # 1. Pull modules from Notion
        if self.watch_modules:
            try:
                from memory_tool.notion.sync import ModuleSyncer

                module_syncer = ModuleSyncer(base_path=self.memory_root.parent)
                result = module_syncer.sync(
                    pull_only=True,
                    dry_run=self.dry_run,
                    verbose=False,
                )

                if result.pulled > 0:
                    self._module_pull_count += result.pulled
                    total_pulled += result.pulled
                    print(f"[{timestamp}] Pulled {result.pulled} module file(s) from Notion")

                if result.failed > 0:
                    all_errors.extend([r.message for r in result.results if not r.success])

            except Exception as e:
                if self.verbose:
                    print(f"[{timestamp}] Module poll failed: {e}")

        # 2. Pull timeline from Notion
        if self.watch_timeline:
            try:
                from memory_tool.notion.timeline_sync import TimelineSyncer

                timeline_syncer = TimelineSyncer(memory_root=self.memory_root)

                # Only sync today's timeline for polling (to minimize API calls)
                result = timeline_syncer.sync(
                    days=1,
                    pull_only=True,
                    dry_run=self.dry_run,
                    verbose=False,
                )

                pulled = result.get("pulled", 0)
                errors = result.get("errors", [])

                if pulled > 0:
                    self._timeline_pull_count += pulled
                    total_pulled += pulled
                    print(f"[{timestamp}] Pulled {pulled} timeline entry(ies) from Notion")
                    # Reload timeline content to avoid pushing back what we just pulled
                    self._preload_timeline_content()

                if errors:
                    all_errors.extend(errors)

            except Exception as e:
                if self.verbose:
                    print(f"[{timestamp}] Timeline poll failed: {e}")

        # 3. Pull plans from Notion
        if self.watch_plans:
            try:
                from memory_tool.notion.plan_sync import PlanSyncer

                plan_syncer = PlanSyncer(memory_root=self.memory_root)

                if plan_syncer.enabled:
                    result = plan_syncer.sync(
                        plan_type="all",
                        days=1,  # Only today's plan for polling
                        pull_only=True,
                        dry_run=self.dry_run,
                        verbose=False,
                    )

                    pulled = result.get("pulled", 0)
                    errors = result.get("errors", [])

                    if pulled > 0:
                        self._plan_pull_count += pulled
                        total_pulled += pulled
                        print(f"[{timestamp}] Pulled {pulled} plan task(s) from Notion")

                    if errors:
                        all_errors.extend(errors)

            except Exception as e:
                if self.verbose:
                    print(f"[{timestamp}] Plan poll failed: {e}")

        # Summary
        if total_pulled == 0 and self.verbose:
            print(f"[{timestamp}] No changes from Notion")

        if all_errors and self.verbose:
            for err in all_errors:
                print(f"[{timestamp}] Poll error: {err}")

    def stop(self):
        """Stop watching."""
        self._running = False
        if self._observer:
            self._observer.stop()
            self._observer.join()

        stats = f"Module syncs: {self._module_sync_count}, Timeline syncs: {self._timeline_sync_count}"
        if self._plan_sync_count:
            stats += f", Plan syncs: {self._plan_sync_count}"
        if self.bidirectional:
            pulls = []
            if self._module_pull_count:
                pulls.append(f"Module pulls: {self._module_pull_count}")
            if self._timeline_pull_count:
                pulls.append(f"Timeline pulls: {self._timeline_pull_count}")
            if self._plan_pull_count:
                pulls.append(f"Plan pulls: {self._plan_pull_count}")
            if pulls:
                stats += ", " + ", ".join(pulls)
        print(f"\nStopped. {stats}")

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
