"""CLI interface for Memory Tool."""

import sys
from datetime import timedelta
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from memory_tool.core.timeline import (
    Timeline,
    TimelineError,
    FutureTimeError,
    DistantPastWarning,
)
from memory_tool.core.init import (
    MemoryInitializer,
    InitializationError,
    AlreadyInitializedError,
)
from memory_tool.core.search import (
    MemorySearcher,
    SearchError,
)
from memory_tool.context.builder import (
    ContextBuilder,
    ContextError,
)
from memory_tool.utils.alias import (
    AliasManager,
    AliasError,
)

app = typer.Typer(
    name="memory-tool",
    help="Time-Space Integrated Knowledge System",
    add_completion=False,
)
console = Console()


def sanitize_output(text: str) -> str:
    """Remove characters that cause issues with Windows console.

    Args:
        text: Input text

    Returns:
        Sanitized text
    """
    # Replace common problematic characters
    replacements = {
        '⭐': '*',
        '✅': '[OK]',
        '❌': '[X]',
        '⚠️': '[!]',
        '⚠': '[!]',
        '🎯': '[TARGET]',
        '🔄': '[REFRESH]',
        '📝': '[NOTE]',
        '💡': '[IDEA]',
        '🚀': '[LAUNCH]',
        '✨': '[NEW]',
        '🔍': '[SEARCH]',
        '📌': '[PIN]',
        '🎉': '[DONE]',
        '💪': '[STRONG]',
        '🤔': '[THINK]',
        '📋': '[LIST]',
        '🔗': '[LINK]',
    }

    for emoji, replacement in replacements.items():
        text = text.replace(emoji, replacement)

    return text


@app.command()
def record(
    message: str = typer.Argument(..., help="Message to record in timeline"),
    date: str = typer.Option(None, "--date", help="Date (YYYY-MM-DD)"),
    time: str = typer.Option(None, "--time", help="Time (HH:MM)"),
    force: bool = typer.Option(False, "--force", "-f", help="Force recording (skip warnings)"),
):
    """Record a message to timeline (m command)."""
    timeline = Timeline()

    try:
        dt, file_path = timeline.record(message, date, time, force=force)

        # Success message
        time_str = dt.strftime("%H:%M")
        date_str = dt.strftime("%Y-%m-%d")
        rel_path = file_path.relative_to(Path.cwd())

        console.print(f"[green]OK[/green] Recorded at {date_str} {time_str}")
        console.print(f"[dim]-> {rel_path}[/dim]")

    except FutureTimeError as e:
        console.print(f"[red]ERROR[/red] {e}", style="bold")
        sys.exit(1)

    except DistantPastWarning as e:
        console.print(f"[yellow]WARNING[/yellow] {e}")
        console.print("[dim]Use --force to record anyway[/dim]")
        sys.exit(1)

    except ValueError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)

    except TimelineError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)


@app.command()
def init(
    path: str = typer.Argument(".", help="Path to initialize .memory/ structure"),
    force: bool = typer.Option(False, "--force", "-f", help="Force reinitialize"),
    kb: str = typer.Option(None, "--kb", help="Path to knowledge base"),
):
    """Initialize .memory/ structure (minit command)."""
    target_path = Path(path).resolve()

    if not target_path.exists():
        console.print(f"[red]ERROR[/red] Path does not exist: {target_path}")
        sys.exit(1)

    if not target_path.is_dir():
        console.print(f"[red]ERROR[/red] Path is not a directory: {target_path}")
        sys.exit(1)

    initializer = MemoryInitializer(target_path)

    try:
        created = initializer.initialize(force=force, kb_path=kb)

        # Success message
        console.print(f"[green]OK[/green] Initialized .memory/ at: {target_path}")
        console.print(f"[dim]Created {len(created['directories'])} directories, {len(created['files'])} files[/dim]")

        if kb:
            console.print(f"[dim]Knowledge base: {kb}[/dim]")

        # Claude Code integration info
        template_path = target_path / ".memory" / "templates" / "CLAUDE.md.template"
        console.print(f"\n[cyan]Claude Code Integration:[/cyan]")
        console.print(f"[dim]Template: {template_path}[/dim]")
        console.print(f"[dim]Copy sections to your CLAUDE.md to integrate with Claude Code[/dim]")

    except AlreadyInitializedError as e:
        console.print(f"[yellow]WARNING[/yellow] {e}")
        console.print("[dim]Use --force to reinitialize[/dim]")
        sys.exit(1)

    except InitializationError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        sys.exit(1)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query (regex pattern)"),
    with_kb: bool = typer.Option(False, "--with-kb", help="Include personal KB"),
    all: bool = typer.Option(False, "--all", help="Search all projects"),
    case_sensitive: bool = typer.Option(False, "--case", "-c", help="Case sensitive search"),
    no_context: bool = typer.Option(False, "--no-context", help="Hide context lines"),
    max_results: int = typer.Option(None, "--max", "-n", help="Maximum results"),
):
    """Search timeline and modules (ms command)."""
    searcher = MemorySearcher()

    # Determine scope
    if all:
        scope = "all"
    else:
        scope = "local"

    try:
        results = searcher.search(
            query,
            scope=scope,
            with_kb=with_kb,
            case_sensitive=case_sensitive,
            context_lines=1 if not no_context else 0,
            max_results=max_results,
        )

        # Format and display
        formatted = searcher.format_results(results, show_context=not no_context)
        console.print(formatted)

    except SearchError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        sys.exit(1)


@app.command()
def context(
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (default: .claude/memory-context.md)",
    ),
):
    """Build context for Claude Code (mcontext command)."""
    builder = ContextBuilder()

    # Parse output path
    output_path = Path(output) if output else None

    try:
        result_path = builder.write_context(output_path)

        # Success message
        try:
            rel_path = result_path.relative_to(Path.cwd())
        except ValueError:
            rel_path = result_path
        console.print(f"[green]OK[/green] Context built successfully")
        console.print(f"[dim]-> {rel_path}[/dim]")

        # Show what was included
        config = builder.load_config()
        recent_days = config.get("context", {}).get("recent_days", 3)
        timeline_count = len(builder.get_recent_timeline_paths(recent_days))
        module_count = len(builder.get_module_statuses())

        console.print(f"[dim]Included: {timeline_count} timeline(s), {module_count} module(s)[/dim]")

    except ContextError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        sys.exit(1)


@app.command()
def today():
    """Show today's timeline (mtoday command)."""
    timeline = Timeline()

    try:
        file_path, content = timeline.get_today()

        if file_path is None:
            console.print("[yellow]![/yellow] No timeline entries for today yet")
            console.print(f"[dim]Use: m \"your message\" to start recording[/dim]")
            return

        # Display today's timeline
        from datetime import datetime
        today_str = datetime.now().strftime("%Y-%m-%d")
        console.print(f"[cyan]{today_str} Timeline:[/cyan]\n")
        console.print(sanitize_output(content))
        console.print(f"\n[dim]File: {file_path}[/dim]")

    except Exception as e:
        console.print(f"[red]ERROR[/red] Failed to read today's timeline: {e}")
        sys.exit(1)


@app.command()
def week():
    """Show this week's timeline (mweek command)."""
    timeline = Timeline()

    try:
        week_files = timeline.get_week()

        if not week_files:
            console.print("[yellow]![/yellow] No timeline entries for this week yet")
            console.print(f"[dim]Use: m \"your message\" to start recording[/dim]")
            return

        # Display week's timeline
        from datetime import datetime
        today = datetime.now()
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)

        console.print(f"[cyan]Week of {monday.strftime('%Y-%m-%d')} Timeline:[/cyan]\n")

        for file_path, content in week_files:
            # Extract date from path (YYYY-MM/DD.md)
            year_month = file_path.parent.name
            day = file_path.stem
            date_str = f"{year_month}-{day}"

            console.print(f"[bold]{date_str}[/bold]")
            console.print(sanitize_output(content))
            console.print("")  # Blank line between days

        total_days = len(week_files)
        console.print(f"[dim]{total_days} day(s) with entries this week[/dim]")

    except Exception as e:
        console.print(f"[red]ERROR[/red] Failed to read week's timeline: {e}")
        sys.exit(1)


@app.command()
def status():
    """Show statistics (mstatus command)."""
    base_path = Path.cwd()
    memory_path = base_path / ".memory"

    if not memory_path.exists():
        console.print("[red]ERROR[/red] .memory/ not found in current directory")
        console.print("[dim]Run 'minit' to initialize[/dim]")
        sys.exit(1)

    try:
        # Count timeline files
        timeline_path = memory_path / "timeline"
        timeline_files = list(timeline_path.rglob("*.md")) if timeline_path.exists() else []
        timeline_count = len(timeline_files)

        # Count entries in timeline files
        total_entries = 0
        latest_date = None
        for tf in timeline_files:
            content = tf.read_text(encoding="utf-8")
            lines = content.splitlines()
            # Count lines starting with "-" (entries)
            entries = [line for line in lines if line.strip().startswith("-")]
            total_entries += len(entries)

            # Track latest date
            year_month = tf.parent.name
            day = tf.stem
            try:
                from datetime import datetime
                file_date = datetime.strptime(f"{year_month}-{day}", "%Y-%m-%d")
                if latest_date is None or file_date > latest_date:
                    latest_date = file_date
            except:
                pass

        # Count modules
        modules_path = memory_path / "modules"
        module_dirs = []
        if modules_path.exists():
            module_dirs = [d for d in modules_path.iterdir() if d.is_dir() and not d.name.startswith(".")]
        modules_count = len(module_dirs)

        # Count concepts
        concepts_path = memory_path / "concepts"
        concept_files = list(concepts_path.glob("*.md")) if concepts_path.exists() else []
        concepts_count = len(concept_files)

        # Calculate .memory size
        total_size = 0
        for item in memory_path.rglob("*"):
            if item.is_file():
                total_size += item.stat().st_size

        size_mb = total_size / (1024 * 1024)

        # Display statistics
        console.print("[cyan]Memory Tool Statistics:[/cyan]\n")

        console.print(f"[bold]Timeline:[/bold]")
        console.print(f"  Days recorded: {timeline_count}")
        console.print(f"  Total entries: {total_entries}")
        if latest_date:
            console.print(f"  Latest: {latest_date.strftime('%Y-%m-%d')}")
        console.print()

        console.print(f"[bold]Organization:[/bold]")
        console.print(f"  Modules: {modules_count}")
        console.print(f"  Concepts: {concepts_count}")
        console.print()

        console.print(f"[bold]Storage:[/bold]")
        console.print(f"  Size: {size_mb:.2f} MB")
        console.print(f"  Location: {memory_path}")

    except Exception as e:
        console.print(f"[red]ERROR[/red] Failed to collect statistics: {e}")
        sys.exit(1)


@app.command()
def alias(
    action: str = typer.Argument(..., help="Action: install, uninstall, list"),
    name: str = typer.Argument(None, help="Alias name (optional, default: all)"),
    directory: str = typer.Option(None, "--dir", "-d", help="Installation directory (for batch files)"),
    powershell: bool = typer.Option(False, "--powershell", "--ps", help="Use PowerShell profile (works in all terminals)"),
):
    """Manage command aliases (malias command)."""
    manager = AliasManager()

    # Parse directory
    install_dir = Path(directory) if directory else None

    try:
        if action == "install":
            if powershell:
                # Install to PowerShell profile
                if name:
                    # Install single alias
                    profile_path, was_added = manager.install_powershell_alias(name)
                    if was_added:
                        console.print(f"[green]OK[/green] Installed alias to PowerShell profile: {name}")
                    else:
                        console.print(f"[yellow]![/yellow] Alias already exists: {name}")
                    console.print(f"[dim]-> {profile_path}[/dim]")
                else:
                    # Install all aliases
                    installed = manager.install_all_powershell()
                    added_count = sum(1 for was_added in installed.values() if was_added)
                    console.print(f"[green]OK[/green] Installed {added_count} aliases to PowerShell profile")

                    profile_path = manager.get_powershell_profile_path()
                    console.print(f"[dim]Profile: {profile_path}[/dim]\n")

                    for alias_name, was_added in installed.items():
                        command, description = manager.ALIASES[alias_name]
                        if was_added:
                            console.print(f"[green]  + {alias_name:10}[/green] -> {command:10} ({description})")
                        else:
                            console.print(f"[dim]  = {alias_name:10} -> {command:10} (already exists)[/dim]")

                # Show reload instructions
                console.print("\n[cyan]To use aliases, reload your PowerShell profile:[/cyan]")
                console.print("[dim]  . $PROFILE[/dim]")
                console.print("[dim]Or restart your terminal[/dim]")
            else:
                # Install batch files (original behavior)
                if name:
                    # Install single alias
                    batch_file = manager.install_alias(name, install_dir)
                    console.print(f"[green]OK[/green] Installed alias: {name}")
                    console.print(f"[dim]-> {batch_file}[/dim]")
                else:
                    # Install all aliases
                    installed = manager.install_all(install_dir)
                    console.print(f"[green]OK[/green] Installed {len(installed)} aliases")
                    for alias_name, batch_file in installed.items():
                        console.print(f"[dim]  {alias_name} -> {batch_file}[/dim]")

                # Show PATH instructions
                target_dir = install_dir or manager.get_default_install_dir()
                instructions = manager.get_path_instructions(target_dir)
                console.print(instructions)

        elif action == "uninstall":
            if powershell:
                # Uninstall from PowerShell profile
                if name:
                    # Uninstall single alias
                    profile_path, was_removed = manager.uninstall_powershell_alias(name)
                    if was_removed:
                        console.print(f"[green]OK[/green] Uninstalled alias from PowerShell profile: {name}")
                        if profile_path:
                            console.print(f"[dim]-> {profile_path}[/dim]")
                    else:
                        console.print(f"[yellow]![/yellow] Alias not found: {name}")
                else:
                    # Uninstall all aliases
                    removed = manager.uninstall_all_powershell()
                    if removed:
                        console.print(f"[green]OK[/green] Uninstalled {len(removed)} aliases from PowerShell profile")
                        for alias_name in removed:
                            console.print(f"[dim]  {alias_name}[/dim]")
                    else:
                        console.print("[yellow]![/yellow] No aliases found to uninstall")

                # Show reload instructions
                console.print("\n[cyan]To apply changes, reload your PowerShell profile:[/cyan]")
                console.print("[dim]  . $PROFILE[/dim]")
                console.print("[dim]Or restart your terminal[/dim]")
            else:
                # Uninstall batch files (original behavior)
                if name:
                    # Uninstall single alias
                    removed = manager.uninstall_alias(name, install_dir)
                    if removed:
                        console.print(f"[green]OK[/green] Uninstalled alias: {name}")
                    else:
                        console.print(f"[yellow]![/yellow] Alias not found: {name}")
                else:
                    # Uninstall all aliases
                    removed = manager.uninstall_all(install_dir)
                    if removed:
                        console.print(f"[green]OK[/green] Uninstalled {len(removed)} aliases")
                        for alias_name in removed:
                            console.print(f"[dim]  {alias_name}[/dim]")
                    else:
                        console.print("[yellow]![/yellow] No aliases found to uninstall")

        elif action == "list":
            if powershell:
                # List PowerShell profile aliases
                ps_status_map = manager.list_powershell_installed()
                ps_profile = manager.get_powershell_profile_path()

                if ps_profile:
                    console.print(f"[cyan]PowerShell Profile:[/cyan] {ps_profile}\n")

                    for alias_name, installed in ps_status_map.items():
                        command, description = manager.ALIASES[alias_name]
                        status_icon = "[green]OK[/green]" if installed else "[dim]--[/dim]"
                        console.print(f"  {status_icon} {alias_name:10} -> {command:10} ({description})")

                    console.print("")
                    if any(ps_status_map.values()):
                        console.print("[green]OK[/green] Aliases are configured in PowerShell profile")
                        console.print("[dim]Works in: PowerShell, VSCode, Windows Terminal, etc.[/dim]")
                    else:
                        console.print("[yellow]![/yellow] No aliases found in PowerShell profile")
                        console.print("[dim]Run 'malias install --powershell' to install[/dim]")
                else:
                    console.print("[red]ERROR[/red] PowerShell not available")
            else:
                # List batch file aliases (original behavior) and PowerShell status
                # Show batch files
                status_map = manager.list_installed(install_dir)
                target_dir = install_dir or manager.get_default_install_dir()

                console.print(f"[cyan]Batch Files:[/cyan] {target_dir}\n")

                for alias_name, installed in status_map.items():
                    command, description = manager.ALIASES[alias_name]
                    status_icon = "[green]OK[/green]" if installed else "[dim]--[/dim]"
                    console.print(f"  {status_icon} {alias_name:10} -> {command:10} ({description})")

                console.print("")
                in_path = manager.is_in_path(target_dir)
                if in_path:
                    console.print("[green]OK[/green] Directory is in PATH")
                else:
                    console.print("[yellow]![/yellow] Directory is NOT in PATH (aliases won't work)")
                    console.print("[dim]Run 'malias install' to see PATH setup instructions[/dim]")

                # Also show PowerShell profile status
                ps_profile = manager.get_powershell_profile_path()
                if ps_profile:
                    ps_status_map = manager.list_powershell_installed()
                    console.print(f"\n[cyan]PowerShell Profile:[/cyan] {ps_profile}")

                    ps_installed_count = sum(1 for v in ps_status_map.values() if v)
                    if ps_installed_count > 0:
                        console.print(f"[green]OK[/green] {ps_installed_count} aliases configured in PowerShell profile")
                    else:
                        console.print("[dim]No PowerShell aliases (use --powershell to install)[/dim]")

        else:
            console.print(f"[red]ERROR[/red] Unknown action: {action}")
            console.print("Valid actions: install, uninstall, list")
            sys.exit(1)

    except AliasError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        sys.exit(1)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version"),
):
    """Memory Tool - Time-Space Integrated Knowledge System."""
    if version:
        from memory_tool import __version__
        console.print(f"Memory Tool v{__version__}")
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        console.print(
            Panel.fit(
                "[bold cyan]Memory Tool[/bold cyan]\n\n"
                "Time-Space Integrated Knowledge System\n"
                "For Claude Code integration\n\n"
                "[dim]Use --help to see available commands[/dim]",
                border_style="cyan",
            )
        )


if __name__ == "__main__":
    app()
