"""Tag management CLI commands."""

import sys
from pathlib import Path
from typing import List, Optional

import typer

from memory_tool.commands.common import app, console
from memory_tool.utils.config import Config

# Create tag subcommand app
tag_app = typer.Typer(
    name="tag",
    help="Tag management commands (mtag)",
    rich_markup_mode="rich",
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
    from memory_tool.search.filters import TagCollector

    memory_path = Path.cwd() / ".memory"
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

    # Collect tags
    collector = TagCollector(memory_path)
    tag_counts = collector.collect(selected_types)

    # Filter by min_count
    if min_count > 1:
        tag_counts = {k: v for k, v in tag_counts.items() if v >= min_count}

    if not tag_counts:
        type_str = ", ".join(selected_types)
        console.print(f"[yellow]No tags found in {type_str}[/yellow]")
        if min_count > 1:
            console.print(f"[dim](minimum count filter: {min_count})[/dim]")
        return

    # Sort tags
    if sort == "alpha":
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[0].lower())
    else:  # count (default)
        sorted_tags = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0].lower()))

    # Calculate max values for bar chart
    max_count = max(tag_counts.values())
    max_tag_len = max(len(tag) for tag in tag_counts.keys())
    bar_width = 20  # Maximum bar width

    # Print header
    type_str = ", ".join(selected_types)
    unique_count = len(tag_counts)
    console.print(f"\n[bold cyan]Tags in {type_str}[/bold cyan] ({unique_count} unique tags)\n")

    # Print tags with bar chart
    # Use ASCII-safe character for Windows compatibility
    bar_char = "#"

    for tag, count in sorted_tags:
        # Calculate bar length
        bar_len = int((count / max_count) * bar_width) if max_count > 0 else 0
        bar = bar_char * bar_len

        # Color based on count
        if count >= max_count * 0.7:
            bar_color = "green"
        elif count >= max_count * 0.3:
            bar_color = "yellow"
        else:
            bar_color = "dim"

        # Print formatted line
        console.print(
            f"  {tag:<{max_tag_len}}  [{bar_color}]{bar:<{bar_width}}[/{bar_color}]  {count}"
        )


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

    memory_path = Path.cwd() / ".memory"
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

    memory_path = Path.cwd() / ".memory"
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

    memory_path = Path.cwd() / ".memory"
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
