"""Timeline mode for TUI browser."""

from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timedelta

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.widgets import (
    Static,
    Label,
    ListItem,
    ListView,
)
from textual.reactive import reactive
from rich.text import Text
from rich.panel import Panel


class TimelineList(ListView):
    """ListView for displaying timeline dates."""

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]


class TimelineMode(Static):
    """Timeline mode widget for TUI browser.

    Features:
    - Date list (recent dates)
    - Entry view for selected date
    - Navigation (prev/next day, week)
    - Summary statistics
    """

    CSS = """
    TimelineMode {
        layout: horizontal;
        height: 1fr;
    }

    #date-list-container {
        width: 30;
        border-right: solid $primary;
    }

    #entry-view-container {
        width: 1fr;
        padding: 1 2;
    }

    TimelineList {
        height: 1fr;
    }

    #entry-content {
        height: 1fr;
        overflow-y: auto;
    }

    #stats-panel {
        height: auto;
        padding: 1;
        background: $boost;
    }
    """

    BINDINGS = [
        Binding("n", "next_day", "Next Day", show=True),
        Binding("p", "prev_day", "Prev Day", show=True),
        Binding("t", "today", "Today", show=True),
    ]

    def __init__(self, base_path: Path, **kwargs):
        super().__init__(**kwargs)
        self.base_path = base_path
        self.timeline_path = base_path / ".memory" / "timeline"
        self.dates: List[datetime] = []
        self.selected_date: Optional[datetime] = None
        self.entries: Dict[str, List[str]] = {}

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Container(id="date-list-container"):
            yield Label("Recent Dates", id="date-list-header")
            yield TimelineList(id="date-list")

        with Container(id="entry-view-container"):
            with Container(id="stats-panel"):
                yield Label("", id="stats-label")

            with VerticalScroll(id="entry-content"):
                yield Static("Select a date to view entries", id="entry-text")

    def on_mount(self) -> None:
        """Handle widget mount."""
        self.load_dates()
        self.populate_date_list()

    def load_dates(self) -> None:
        """Load available timeline dates."""
        if not self.timeline_path.exists():
            return

        # Find all timeline markdown files
        date_files = []
        for year_dir in self.timeline_path.iterdir():
            if not year_dir.is_dir():
                continue

            for month_dir in year_dir.iterdir():
                if not month_dir.is_dir():
                    continue

                for day_file in month_dir.glob("*.md"):
                    # Parse date from filename (DD.md)
                    try:
                        day = int(day_file.stem)
                        month = int(month_dir.name)
                        year = int(year_dir.name)
                        date = datetime(year, month, day)
                        date_files.append((date, day_file))
                    except ValueError:
                        continue

        # Sort by date descending (most recent first)
        date_files.sort(reverse=True, key=lambda x: x[0])

        # Store dates
        self.dates = [date for date, _ in date_files]

        # Load entries for each date
        for date, file_path in date_files:
            date_key = date.strftime("%Y-%m-%d")
            self.entries[date_key] = self._parse_timeline_file(file_path)

    def _parse_timeline_file(self, file_path: Path) -> List[str]:
        """Parse timeline file and extract entries."""
        try:
            content = file_path.read_text(encoding="utf-8")
            entries = []

            # Split by lines and find entries (format: HH:MM | content)
            for line in content.split("\n"):
                line = line.strip()
                if "|" in line and line[0].isdigit():
                    entries.append(line)

            return entries
        except Exception:
            return []

    def populate_date_list(self) -> None:
        """Populate the date list."""
        date_list = self.query_one("#date-list", TimelineList)

        for date in self.dates:
            # Get entry count
            date_key = date.strftime("%Y-%m-%d")
            entry_count = len(self.entries.get(date_key, []))

            # Format label
            if date.date() == datetime.now().date():
                label = f"[bold cyan]Today ({entry_count})[/]"
            elif date.date() == (datetime.now() - timedelta(days=1)).date():
                label = f"[cyan]Yesterday ({entry_count})[/]"
            else:
                label = f"{date.strftime('%Y-%m-%d')} ({entry_count})"

            date_list.append(ListItem(Label(label)))

        # Select today by default
        if self.dates:
            self.selected_date = self.dates[0]
            self.show_date_entries(self.selected_date)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle date selection."""
        if event.list_view.id == "date-list":
            index = event.list_view.index
            if 0 <= index < len(self.dates):
                self.selected_date = self.dates[index]
                self.show_date_entries(self.selected_date)

    def show_date_entries(self, date: datetime) -> None:
        """Show entries for selected date."""
        date_key = date.strftime("%Y-%m-%d")
        entries = self.entries.get(date_key, [])

        # Build display text
        content = Text()

        # Header
        content.append(f"Timeline for ", style="bold")
        content.append(f"{date.strftime('%Y-%m-%d (%A)')}\n\n", style="bold cyan")

        if not entries:
            content.append("No entries for this date.", style="dim")
        else:
            for entry in entries:
                # Parse time and content
                if "|" in entry:
                    time_part, content_part = entry.split("|", 1)
                    content.append(f"{time_part.strip()}", style="bold yellow")
                    content.append(" | ", style="dim")
                    content.append(f"{content_part.strip()}\n\n", style="white")
                else:
                    content.append(f"{entry}\n\n", style="white")

        # Update entry view
        entry_text = self.query_one("#entry-text", Static)
        entry_text.update(content)

        # Update stats
        stats_label = self.query_one("#stats-label", Label)
        stats_label.update(f"Entries: {len(entries)} | Date: {date.strftime('%Y-%m-%d')}")

    def action_next_day(self) -> None:
        """Navigate to next day."""
        if not self.selected_date or not self.dates:
            return

        # Find current index
        try:
            current_index = self.dates.index(self.selected_date)
            if current_index > 0:  # Can go forward (dates are sorted descending)
                self.selected_date = self.dates[current_index - 1]
                self.show_date_entries(self.selected_date)

                # Update list selection
                date_list = self.query_one("#date-list", TimelineList)
                date_list.index = current_index - 1
        except ValueError:
            pass

    def action_prev_day(self) -> None:
        """Navigate to previous day."""
        if not self.selected_date or not self.dates:
            return

        # Find current index
        try:
            current_index = self.dates.index(self.selected_date)
            if current_index < len(self.dates) - 1:  # Can go back
                self.selected_date = self.dates[current_index + 1]
                self.show_date_entries(self.selected_date)

                # Update list selection
                date_list = self.query_one("#date-list", TimelineList)
                date_list.index = current_index + 1
        except ValueError:
            pass

    def action_today(self) -> None:
        """Navigate to today."""
        if not self.dates:
            return

        today = datetime.now().date()

        # Find today in dates
        for i, date in enumerate(self.dates):
            if date.date() == today:
                self.selected_date = date
                self.show_date_entries(self.selected_date)

                # Update list selection
                date_list = self.query_one("#date-list", TimelineList)
                date_list.index = i
                return

        # If today not found, select most recent
        self.selected_date = self.dates[0]
        self.show_date_entries(self.selected_date)
        date_list = self.query_one("#date-list", TimelineList)
        date_list.index = 0
