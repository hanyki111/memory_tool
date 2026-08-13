"""Tag management CLI commands."""

import sys
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Set
from datetime import date

import typer

from memory_tool.commands.common import app, console
from memory_tool.utils.config import Config
from memory_tool.utils.paths import get_base_path


def get_display_width(text: str) -> int:
    """
    Calculate the display width of text in a terminal.

    Wide characters (CJK, Korean, etc.) take 2 columns,
    while ASCII and other narrow characters take 1 column.

    Args:
        text: Text to measure

    Returns:
        Display width in terminal columns
    """
    width = 0
    for char in text:
        # Get East Asian Width property
        ea_width = unicodedata.east_asian_width(char)
        # Wide (W) and Fullwidth (F) characters take 2 columns
        if ea_width in ('W', 'F'):
            width += 2
        else:
            width += 1
    return width

# Create tag subcommand app
tag_app = typer.Typer(
    name="tag",
    help="Tag management commands (mtag)",
    rich_markup_mode="rich",
    invoke_without_command=True,
)


@tag_app.callback()
def tag_callback(
    ctx: typer.Context,
    file_type: List[str] = typer.Option(
        None, "--type", "-t",
        help="File types: timeline, modules, plans (can use multiple)"
    ),
    all_types: bool = typer.Option(
        False, "--all", "-a",
        help="Search all file types"
    ),
    sort: Optional[str] = typer.Option(
        None, "--sort", "-s",
        help="Sort by: count (default), alpha"
    ),
    min_count: Optional[int] = typer.Option(
        None, "--min-count", "-m",
        help="Minimum usage count to display"
    ),
):
    """Tag management commands (mtag).

    Without subcommand, lists tags with usage counts (default behavior).

    Examples:
        mtag                    # List timeline tags (default)
        mtag --all              # All file types
        mtag --sort alpha       # Alphabetical order
        mtag replace OLD NEW    # Replace tag
        mtag delete TAG         # Delete tag
        mtag find TAG           # Find tag occurrences
    """
    # If a subcommand is invoked, don't run list
    if ctx.invoked_subcommand is not None:
        return

    # Default behavior: run tag list
    _run_tag_list(file_type, all_types, sort, min_count)


def _build_activity_string(dates: Set[date], days: int = 31) -> str:
    """
    Build activity string showing which days a tag was used.

    Args:
        dates: Set of dates when the tag was used
        days: Number of days to show (default: 31)

    Returns:
        String of length `days` with '#' for active days, '·' for inactive
    """
    today = datetime.now().date()
    result = []

    for i in range(days - 1, -1, -1):  # From oldest to today
        check_date = today - timedelta(days=i)
        if check_date in dates:
            result.append("#")
        else:
            result.append("·")

    return "".join(result)


def _build_date_header(days: int = 31) -> str:
    """
    Build date header showing day numbers.

    Shows day numbers at regular intervals to help orientation.

    Args:
        days: Number of days to show

    Returns:
        Header string with day markers
    """
    today = datetime.now().date()
    result = []

    for i in range(days - 1, -1, -1):
        check_date = today - timedelta(days=i)
        day = check_date.day

        # Show day number at start of each month or at regular intervals
        if day == 1 or i == days - 1 or i == 0:
            result.append(str(day).rjust(2)[-1])  # Last digit only
        else:
            result.append(" ")

    return "".join(result)


def _run_tag_list(
    file_type: List[str],
    all_types: bool,
    sort: Optional[str],
    min_count: Optional[int],
):
    """Internal function to run tag list logic."""
    from memory_tool.search.filters import TagCollector

    memory_path = get_base_path()
    if not memory_path.exists():
        console.print("[red]ERROR[/red] .memory/ not found. Run 'minit' first.")
        raise typer.Exit(1)

    # Load defaults from config
    config = Config()
    if not file_type and not all_types:
        file_type = config.get("tags.default_types", ["timeline"])
    if all_types:
        file_type = ["timeline", "modules", "plans"]
    if sort is None:
        sort = config.get("tags.sort", "count")
    if min_count is None:
        min_count = config.get("tags.min_count", 1)

    selected_types = list(file_type) if file_type else ["timeline"]

    # Collect tags with date information
    collector = TagCollector(memory_path)
    days = 31
    tag_data = collector.collect_with_dates(selected_types, days=days)

    # Filter by min_count
    if min_count > 1:
        tag_data = {k: v for k, v in tag_data.items() if v['count'] >= min_count}

    if not tag_data:
        type_str = ", ".join(selected_types)
        console.print(f"[yellow]No tags found in {type_str}[/yellow]")
        if min_count > 1:
            console.print(f"[dim](minimum count filter: {min_count})[/dim]")
        return

    # Sort tags
    if sort == "alpha":
        sorted_tags = sorted(tag_data.items(), key=lambda x: x[0].lower())
    else:  # count (default)
        sorted_tags = sorted(tag_data.items(), key=lambda x: (-x[1]['count'], x[0].lower()))

    # Calculate display widths
    max_tag_display_width = max(get_display_width(tag) for tag in tag_data.keys())
    max_count = max(v['count'] for v in tag_data.values())
    count_width = len(str(max_count))

    # Print title
    type_str = ", ".join(selected_types)
    unique_count = len(tag_data)
    today = datetime.now().date()
    console.print(f"\n[bold cyan]Tags in {type_str}[/bold cyan] ({unique_count} unique tags)")
    console.print()

    # Build header
    tag_header = "Tag"
    tag_header_padding = max_tag_display_width - get_display_width(tag_header)
    count_header = "Count"

    # Calculate positions
    # Format: "  Tag      Count  Activity (31 days)"
    activity_label = f"Activity ({days} days)"

    # Print header
    console.print(
        f"  [bold]{tag_header}{' ' * tag_header_padding}  "
        f"{count_header:>{count_width + 1}}  "
        f"{activity_label}[/bold]"
    )

    # Print separator
    separator_len = 2 + max_tag_display_width + 2 + max(count_width + 1, len(count_header)) + 2 + days
    console.print(f"  [dim]{'─' * (separator_len - 2)}[/dim]")

    # Print each tag row
    for tag, data in sorted_tags:
        count = data['count']
        dates = data['dates']

        # Build activity string
        activity = _build_activity_string(dates, days)

        # Calculate padding for proper alignment
        tag_display_width = get_display_width(tag)
        padding = max_tag_display_width - tag_display_width

        # Color activity based on recent usage
        recent_days = sum(1 for d in dates if (today - d).days < 7)
        if recent_days >= 3:
            activity_color = "green"
        elif recent_days >= 1:
            activity_color = "yellow"
        else:
            activity_color = "dim"

        # Print formatted line
        console.print(
            f"  {tag}{' ' * padding}  "
            f"{count:>{max(count_width + 1, len(count_header))}}  "
            f"[{activity_color}]{activity}[/{activity_color}]"
        )


@tag_app.command("list")
def tag_list(
    file_type: List[str] = typer.Option(
        None, "--type", "-t",
        help="File types: timeline, modules, plans (can use multiple)"
    ),
    all_types: bool = typer.Option(
        False, "--all", "-a",
        help="Search all file types"
    ),
    sort: Optional[str] = typer.Option(
        None, "--sort", "-s",
        help="Sort by: count (default), alpha"
    ),
    min_count: Optional[int] = typer.Option(
        None, "--min-count", "-m",
        help="Minimum usage count to display"
    ),
):
    """List tags with usage counts.

    By default, shows tags from timeline only.

    Examples:
        mtag list                              # Timeline tags (default)
        mtag list --all                        # All file types
        mtag list --type timeline --type modules  # Multiple types
        mtag list --sort alpha                 # Sort alphabetically
        mtag list --min-count 3                # Tags used 3+ times
    """
    _run_tag_list(file_type, all_types, sort, min_count)


@tag_app.command("replace")
def tag_replace(
    old_tag: str = typer.Argument(..., help="Tag to replace"),
    new_tag: str = typer.Argument(..., help="New tag value"),
    file_type: List[str] = typer.Option(
        None, "--type", "-t",
        help="File types: timeline, modules, plans (can use multiple)"
    ),
    all_types: bool = typer.Option(
        False, "--all", "-a",
        help="Search all file types"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n",
        help="Preview changes without modifying files"
    ),
):
    """Replace a tag with another.

    Replaces all occurrences of a tag in .memory files.
    Matching is case-insensitive.

    Examples:
        mtag replace endfield 엔드필드              # Replace tag
        mtag replace "old tag" "new tag" --all     # All file types
        mtag replace bug BUG --type timeline       # Timeline only
        mtag replace test TEST --dry-run           # Preview only
    """
    from memory_tool.search.filters import TagManager

    memory_path = get_base_path()
    if not memory_path.exists():
        console.print("[red]ERROR[/red] .memory/ not found. Run 'minit' first.")
        raise typer.Exit(1)

    # Determine file types
    if all_types:
        selected_types = ["timeline", "modules", "plans"]
    elif file_type:
        selected_types = list(file_type)
    else:
        selected_types = ["timeline", "modules", "plans"]  # Default: all

    manager = TagManager(memory_path)

    # Show what we're doing
    if dry_run:
        console.print("[yellow]DRY RUN[/yellow] - No files will be modified\n")

    console.print(f"Replacing [cyan]{old_tag}[/cyan] -> [green]{new_tag}[/green]")
    console.print(f"Searching in: {', '.join(selected_types)}\n")

    # Perform replacement
    result = manager.replace_tag(old_tag, new_tag, selected_types, dry_run=dry_run)

    if result["files_modified"] == 0:
        console.print(f"[yellow]No occurrences of '{old_tag}' found[/yellow]")
        return

    # Show results
    console.print(f"[bold]Files modified:[/bold] {result['files_modified']}")
    console.print(f"[bold]Total replacements:[/bold] {result['total_replacements']}\n")

    for detail in result["details"]:
        if "error" in detail:
            console.print(f"  [red]ERROR[/red] {detail['file']}: {detail['error']}")
        else:
            console.print(f"  [green]OK[/green] {detail['file']} ({detail['count']} replacements)")

    if dry_run:
        console.print("\n[yellow]Run without --dry-run to apply changes[/yellow]")


@tag_app.command("delete")
def tag_delete(
    tag: str = typer.Argument(..., help="Tag to delete"),
    file_type: List[str] = typer.Option(
        None, "--type", "-t",
        help="File types: timeline, modules, plans (can use multiple)"
    ),
    all_types: bool = typer.Option(
        False, "--all", "-a",
        help="Search all file types"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n",
        help="Preview changes without modifying files"
    ),
    force: bool = typer.Option(
        False, "--force", "-f",
        help="Skip confirmation prompt"
    ),
):
    """Delete a tag from all files.

    Removes all occurrences of a tag from .memory files.
    Matching is case-insensitive.

    Examples:
        mtag delete TAG                    # Delete tag (with confirmation)
        mtag delete "test tag" --all       # All file types
        mtag delete tmp --dry-run          # Preview only
        mtag delete old --force            # Skip confirmation
    """
    from memory_tool.search.filters import TagManager

    memory_path = get_base_path()
    if not memory_path.exists():
        console.print("[red]ERROR[/red] .memory/ not found. Run 'minit' first.")
        raise typer.Exit(1)

    # Determine file types
    if all_types:
        selected_types = ["timeline", "modules", "plans"]
    elif file_type:
        selected_types = list(file_type)
    else:
        selected_types = ["timeline", "modules", "plans"]  # Default: all

    manager = TagManager(memory_path)

    # First, find occurrences
    occurrences = manager.find_tag(tag, selected_types)

    if not occurrences:
        console.print(f"[yellow]No occurrences of '{tag}' found[/yellow]")
        return

    # Show what will be deleted
    total_count = sum(o["count"] for o in occurrences)
    console.print(f"Found [cyan]{tag}[/cyan] in {len(occurrences)} file(s) ({total_count} occurrences)\n")

    for occ in occurrences:
        console.print(f"  {occ['file']} ({occ['count']})")

    console.print()

    # Confirm unless --force or --dry-run
    if not force and not dry_run:
        confirm = typer.confirm("Delete all occurrences?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            return

    if dry_run:
        console.print("[yellow]DRY RUN[/yellow] - No files will be modified")
        return

    # Perform deletion
    result = manager.delete_tag(tag, selected_types, dry_run=False)

    console.print(f"\n[green]Deleted {result['total_deletions']} occurrences from {result['files_modified']} file(s)[/green]")


@tag_app.command("find")
def tag_find(
    tag: str = typer.Argument(..., help="Tag to find"),
    file_type: List[str] = typer.Option(
        None, "--type", "-t",
        help="File types: timeline, modules, plans (can use multiple)"
    ),
    all_types: bool = typer.Option(
        False, "--all", "-a",
        help="Search all file types"
    ),
):
    """Find all occurrences of a tag.

    Shows which files contain a specific tag.
    Matching is case-insensitive.

    Examples:
        mtag find bug                      # Find in all file types
        mtag find "memory tool" --type timeline
    """
    from memory_tool.search.filters import TagManager

    memory_path = get_base_path()
    if not memory_path.exists():
        console.print("[red]ERROR[/red] .memory/ not found. Run 'minit' first.")
        raise typer.Exit(1)

    # Determine file types
    if all_types:
        selected_types = ["timeline", "modules", "plans"]
    elif file_type:
        selected_types = list(file_type)
    else:
        selected_types = ["timeline", "modules", "plans"]  # Default: all

    manager = TagManager(memory_path)
    occurrences = manager.find_tag(tag, selected_types)

    if not occurrences:
        console.print(f"[yellow]No occurrences of '{tag}' found[/yellow]")
        return

    total_count = sum(o["count"] for o in occurrences)
    console.print(f"\n[bold cyan]Tag: {tag}[/bold cyan]")
    console.print(f"Found in {len(occurrences)} file(s), {total_count} total occurrences\n")

    # Sort by count descending
    occurrences.sort(key=lambda x: -x["count"])

    for occ in occurrences:
        console.print(f"  {occ['file']:<50} {occ['count']}")


# Register tag_app with main app
app.add_typer(tag_app, name="tag")
