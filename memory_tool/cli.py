"""CLI interface for Memory Tool.

This module serves as the entry point for the CLI. All commands are organized
in the memory_tool.commands package:
- timeline: record, today, week, month, days, sort, review
- modules: module, archive, browse
- search: search, check, index
- planning: plan, summary
- context: context, map (code_map)
- notion: nm, nadd, ns, nt, nw, nsi, nsync, nwatch
- system: init, status, alias, completion, tutorial, hooks, migrate_timeline, update
"""

import typer
from rich.panel import Panel

# Import app and console from commands package
# This also imports all command modules which register their commands with app
from memory_tool.commands import app, console


def _notify_update() -> None:
    """Show a one-line update notice if a newer version is available."""
    try:
        from memory_tool.core.updater import auto_check_update
        latest = auto_check_update()
        if latest:
            console.print(f"[dim]새 버전 v{latest} 사용 가능 — mupdate 로 업데이트[/dim]")
    except Exception:
        pass  # Never break the user's command


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

    # Auto update check (throttled, silent on failure)
    if ctx.invoked_subcommand not in (None, "update"):
        _notify_update()

    if ctx.invoked_subcommand is None:
        _notify_update()
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


# ============================================================================
# CLI Entry Points
# ============================================================================
# These wrapper functions are needed because pyproject.toml entry points
# call functions directly, bypassing Typer's CLI argument parsing.
# Without these wrappers, typer.Argument(...) returns ArgumentInfo objects
# instead of actual command-line arguments on Typer 0.12+.
# ============================================================================


def record_cli():
    """Entry point for 'm' command."""
    import sys
    sys.argv = ['memory_tool', 'record'] + sys.argv[1:]
    app()


def init_cli():
    """Entry point for 'minit' command."""
    import sys
    sys.argv = ['memory_tool', 'init'] + sys.argv[1:]
    app()


def search_cli():
    """Entry point for 'ms' command."""
    import sys
    sys.argv = ['memory_tool', 'search'] + sys.argv[1:]
    app()


def context_cli():
    """Entry point for 'mcontext' command."""
    import sys
    sys.argv = ['memory_tool', 'context'] + sys.argv[1:]
    app()


def check_cli():
    """Entry point for 'mcheck' command."""
    import sys
    sys.argv = ['memory_tool', 'check'] + sys.argv[1:]
    app()


def today_cli():
    """Entry point for 'mtoday' command."""
    import sys
    sys.argv = ['memory_tool', 'today'] + sys.argv[1:]
    app()


def week_cli():
    """Entry point for 'mweek' command."""
    import sys
    sys.argv = ['memory_tool', 'week'] + sys.argv[1:]
    app()


def month_cli():
    """Entry point for 'mmonth' command."""
    import sys
    sys.argv = ['memory_tool', 'month'] + sys.argv[1:]
    app()


def days_cli():
    """Entry point for 'mdays' command."""
    import sys
    sys.argv = ['memory_tool', 'days'] + sys.argv[1:]
    app()


def status_cli():
    """Entry point for 'mstatus' command."""
    import sys
    sys.argv = ['memory_tool', 'status'] + sys.argv[1:]
    app()


def alias_cli():
    """Entry point for 'malias' command."""
    import sys
    sys.argv = ['memory_tool', 'alias'] + sys.argv[1:]
    app()


def summary_cli():
    """Entry point for 'msummary' command."""
    import sys
    sys.argv = ['memory_tool', 'summary'] + sys.argv[1:]
    app()


def browse_cli():
    """Entry point for 'mbrowse' command."""
    import sys
    sys.argv = ['memory_tool', 'browse'] + sys.argv[1:]
    app()


def completion_cli():
    """Entry point for 'mcompletion' command."""
    import sys
    sys.argv = ['memory_tool', 'completion'] + sys.argv[1:]
    app()


def plan_cli():
    """Entry point for 'mplan' command."""
    import sys
    sys.argv = ['memory_tool', 'plan'] + sys.argv[1:]
    app()


def tutorial_cli():
    """Entry point for 'mtutorial' command."""
    import sys
    sys.argv = ['memory_tool', 'tutorial'] + sys.argv[1:]
    app()


def map_cli():
    """Entry point for 'mmap' command."""
    import sys
    sys.argv = ['memory_tool', 'map'] + sys.argv[1:]
    app()


def sort_cli():
    """Entry point for 'msort' command."""
    import sys
    sys.argv = ['memory_tool', 'sort'] + sys.argv[1:]
    app()


def archive_cli():
    """Entry point for 'marchive' command."""
    import sys
    sys.argv = ['memory_tool', 'archive'] + sys.argv[1:]
    app()


def index_cli():
    """Entry point for 'mindex' command."""
    import sys
    sys.argv = ['memory_tool', 'index'] + sys.argv[1:]
    app()


def module_cli():
    """Entry point for 'mmodule' command."""
    import sys
    sys.argv = ['memory_tool', 'module'] + sys.argv[1:]
    app()


def review_cli():
    """Entry point for 'mreview' command."""
    import sys
    sys.argv = ['memory_tool', 'review'] + sys.argv[1:]
    app()


def hooks_cli():
    """Entry point for 'mhooks' command."""
    import sys
    sys.argv = ['memory_tool', 'hooks'] + sys.argv[1:]
    app()


def migrate_timeline_cli():
    """Entry point for 'mmigrate-timeline' command."""
    import sys
    sys.argv = ['memory_tool', 'migrate-timeline'] + sys.argv[1:]
    app()


def notion_message_cli():
    """Entry point for 'nm' command."""
    import sys
    sys.argv = ['memory_tool', 'nm'] + sys.argv[1:]
    app()


def notion_add_cli():
    """Entry point for 'nadd' command."""
    import sys
    sys.argv = ['memory_tool', 'nadd'] + sys.argv[1:]
    app()


def notion_search_cli():
    """Entry point for 'ns' command."""
    import sys
    sys.argv = ['memory_tool', 'ns'] + sys.argv[1:]
    app()


def notion_today_cli():
    """Entry point for 'nt' command."""
    import sys
    sys.argv = ['memory_tool', 'nt'] + sys.argv[1:]
    app()


def notion_week_cli():
    """Entry point for 'nw' command."""
    import sys
    sys.argv = ['memory_tool', 'nw'] + sys.argv[1:]
    app()


def notion_search_inside_cli():
    """Entry point for 'nsi' command."""
    import sys
    sys.argv = ['memory_tool', 'nsi'] + sys.argv[1:]
    app()


def notion_sync_cli():
    """Entry point for 'nsync' command."""
    import sys
    sys.argv = ['memory_tool', 'nsync'] + sys.argv[1:]
    app()


def notion_watch_cli():
    """Entry point for 'nwatch' command."""
    import sys
    sys.argv = ['memory_tool', 'nwatch'] + sys.argv[1:]
    app()


def ask_cli():
    """Entry point for 'mask' command."""
    import sys
    sys.argv = ['memory_tool', 'ask'] + sys.argv[1:]
    app()


def providers_cli():
    """Entry point for 'mproviders' command."""
    import sys
    sys.argv = ['memory_tool', 'providers'] + sys.argv[1:]
    app()


def help_cli():
    """Entry point for 'mhelp' command."""
    import sys
    sys.argv = ['memory_tool', 'help'] + sys.argv[1:]
    app()


def config_cli():
    """Entry point for 'mconfig' command."""
    import sys
    sys.argv = ['memory_tool', 'config'] + sys.argv[1:]
    app()


def publish_cli():
    """Entry point for 'mpublish' command."""
    import sys
    sys.argv = ['memory_tool', 'publish'] + sys.argv[1:]
    app()


def import_cli():
    """Entry point for 'mimport' command."""
    import sys
    sys.argv = ['memory_tool', 'import-kb'] + sys.argv[1:]
    app()


def update_cli():
    """Entry point for 'mupdate' command."""
    import sys
    sys.argv = ['memory_tool', 'update'] + sys.argv[1:]
    app()
