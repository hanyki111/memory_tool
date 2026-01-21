"""Timeline-related CLI commands."""

import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

import typer

from memory_tool.commands.common import app, console, sanitize_output, opt_str, arg_str
from memory_tool.core.timeline import (
    Timeline,
    TimelineError,
    FutureTimeError,
    DistantPastWarning,
)
from memory_tool.core.sort import TimelineSorter, SortError
from memory_tool.context.builder import ContextBuilder
from memory_tool.utils.config import Config
from memory_tool.review import ReviewManager


@app.command(
    epilog="For detailed help: [bold]mhelp record[/bold]  |  Korean: [bold]mconfig set help.language ko[/bold]"
)
def record(
    message: str = typer.Argument(..., help="Message to record in timeline"),
    date: Optional[str] = typer.Option(None, "--date", help="Date (YYYY-MM-DD), defaults to today"),
    time: Optional[str] = typer.Option(None, "--time", help="Time (HH:MM), defaults to current time"),
    force: bool = typer.Option(False, "--force", "-f", help="Force recording (skip warnings for old dates)"),
):
    """Record a message to timeline (m command).

    Records a timestamped entry to your timeline. Entries are automatically
    organized by date and can be searched later with ms command.

    Examples:
        m "Started working on feature X"
        m "Fixed bug" --date 2026-01-20 --time 14:30
    """
    message = arg_str(message)
    date = opt_str(date)
    time = opt_str(time)

    timeline = Timeline()

    try:
        dt, file_path = timeline.record(message, date, time, force=force)

        time_str = dt.strftime("%H:%M")
        date_str = dt.strftime("%Y-%m-%d")
        rel_path = file_path.relative_to(Path.cwd())

        console.print(f"[green]OK[/green] Recorded at {date_str} {time_str}")
        console.print(f"[dim]-> {rel_path}[/dim]")

        # Auto-update context if enabled
        try:
            config = Config()
            if config.auto_update_enabled:
                console.print("[dim]Auto-updating context...[/dim]")
                builder = ContextBuilder()
                context_path = builder.write_context()
                rel_context = context_path.relative_to(Path.cwd())
                console.print(f"[dim]-> {rel_context} updated[/dim]")
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Auto-update failed: {e}")

        # Document health suggestion
        try:
            from memory_tool.utils.suggestion_helper import check_and_suggest_after_command

            memory_dir = Path.cwd() / ".memory"
            check_and_suggest_after_command(memory_dir, "m", force=False)
        except Exception:
            pass

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


@app.command(
    epilog="For detailed help: [bold]mhelp today[/bold]"
)
def today():
    """Show today's timeline (mtoday command).

    Displays all timeline entries recorded today, sorted by time.

    Examples:
        mtoday               # Show today's entries
    """
    timeline = Timeline()

    try:
        file_path, content = timeline.get_today()

        if file_path is None:
            console.print("[yellow]![/yellow] No timeline entries for today yet")
            console.print(f"[dim]Use: m \"your message\" to start recording[/dim]")
            return

        today_str = datetime.now().strftime("%Y-%m-%d")
        console.print(f"[cyan]{today_str} Timeline:[/cyan]\n")
        console.print(sanitize_output(content))
        console.print(f"\n[dim]File: {file_path}[/dim]")

    except Exception as e:
        console.print(f"[red]ERROR[/red] Failed to read today's timeline: {e}")
        sys.exit(1)


@app.command(
    epilog="For detailed help: [bold]mhelp week[/bold]"
)
def week():
    """Show this week's timeline (mweek command).

    Displays timeline entries from Monday to today, grouped by date.

    Examples:
        mweek                # Show this week's entries
    """
    timeline = Timeline()

    try:
        week_files = timeline.get_week()

        if not week_files:
            console.print("[yellow]![/yellow] No timeline entries for this week yet")
            console.print(f"[dim]Use: m \"your message\" to start recording[/dim]")
            return

        today_dt = datetime.now()
        days_since_monday = today_dt.weekday()
        monday = today_dt - timedelta(days=days_since_monday)

        console.print(f"[cyan]Week of {monday.strftime('%Y-%m-%d')} Timeline:[/cyan]\n")

        for file_path, content in week_files:
            year_month = file_path.parent.name
            day = file_path.stem
            date_str = f"{year_month}-{day}"

            console.print(f"[bold]{date_str}[/bold]")
            console.print(sanitize_output(content))
            console.print("")

        total_days = len(week_files)
        console.print(f"[dim]{total_days} day(s) with entries this week[/dim]")

    except Exception as e:
        console.print(f"[red]ERROR[/red] Failed to read week's timeline: {e}")
        sys.exit(1)


@app.command()
def month():
    """Show this month's timeline (mmonth command)."""
    timeline = Timeline()

    try:
        month_files = timeline.get_month()

        if not month_files:
            console.print("[yellow]![/yellow] No timeline entries for this month yet")
            console.print(f"[dim]Use: m \"your message\" to start recording[/dim]")
            return

        today_dt = datetime.now()
        month_name = today_dt.strftime('%Y-%m')

        console.print(f"[cyan]{month_name} Timeline:[/cyan]\n")

        for file_path, content in month_files:
            year_month = file_path.parent.name
            day = file_path.stem
            date_str = f"{year_month}-{day}"

            console.print(f"[bold]{date_str}[/bold]")
            console.print(sanitize_output(content))
            console.print("")

        total_days = len(month_files)
        console.print(f"[dim]{total_days} day(s) with entries this month[/dim]")

    except Exception as e:
        console.print(f"[red]ERROR[/red] Failed to read month's timeline: {e}")
        sys.exit(1)


@app.command()
def days(
    num_days: int = typer.Argument(14, help="Number of days to show (default: 14)"),
):
    """Show timeline for the last N days (mdays command).

    Examples:
        mdays        # Show last 14 days (default)
        mdays 7      # Show last 7 days
        mdays 30     # Show last 30 days
    """
    timeline = Timeline()

    try:
        days_files = timeline.get_days(num_days)

        if not days_files:
            console.print(f"[yellow]![/yellow] No timeline entries for the last {num_days} days")
            console.print(f"[dim]Use: m \"your message\" to start recording[/dim]")
            return

        today_dt = datetime.now()
        start_date = today_dt - timedelta(days=num_days - 1)

        console.print(f"[cyan]Timeline: Last {num_days} days ({start_date.strftime('%Y-%m-%d')} ~ {today_dt.strftime('%Y-%m-%d')}):[/cyan]\n")

        for file_path, content in days_files:
            year_month = file_path.parent.name
            day = file_path.stem
            date_str = f"{year_month}-{day}"

            console.print(f"[bold]{date_str}[/bold]")
            console.print(sanitize_output(content))
            console.print("")

        total_days_with_entries = len(days_files)
        console.print(f"[dim]{total_days_with_entries} day(s) with entries in the last {num_days} days[/dim]")

    except Exception as e:
        console.print(f"[red]ERROR[/red] Failed to read timeline: {e}")
        sys.exit(1)


@app.command()
def sort(
    date_or_all: str = typer.Argument("today", help="Date (YYYY-MM-DD), 'today', or 'all'"),
    no_backup: bool = typer.Option(False, "--no-backup", help="Skip backup creation"),
):
    """Sort timeline entries by time (msort command)."""
    sorter = TimelineSorter()

    if not sorter.is_initialized():
        console.print(f"[red]ERROR[/red] Timeline not found at {sorter.timeline_path}")
        console.print("[dim]Run 'minit' to initialize[/dim]")
        sys.exit(1)

    try:
        if date_or_all.lower() == "all":
            console.print("[cyan]Sorting all timeline files...[/cyan]")
            results = sorter.sort_all(create_backup=not no_backup)

            if not results:
                console.print("[yellow]No timeline files found[/yellow]")
                sys.exit(0)

            total_files = len(results)
            total_entries = sum(r[1] for r in results)
            total_sorted = sum(r[2] for r in results)

            console.print(f"\n[green]OK[/green] Sorted {total_files} file(s)")
            console.print(f"  Total entries: {total_entries}")
            console.print(f"  Sorted entries: {total_sorted}")
            console.print(f"  Unsorted entries: {total_entries - total_sorted}")

            if not no_backup:
                console.print(f"\n[dim]Backups created with .bak extension[/dim]")

        elif date_or_all.lower() == "today":
            today_date = date.today()
            year_month = today_date.strftime("%Y-%m")
            day = today_date.strftime("%d")

            file_path = sorter.timeline_path / year_month / f"{day}.md"

            if not file_path.exists():
                console.print(f"[yellow]No timeline file for today ({today_date.strftime('%Y-%m-%d')})[/yellow]")
                sys.exit(0)

            console.print(f"[cyan]Sorting {today_date.strftime('%Y-%m-%d')}...[/cyan]")
            total, sorted_count = sorter.sort_file(file_path, create_backup=not no_backup)

            console.print(f"\n[green]OK[/green] Sorted {file_path.name}")
            console.print(f"  Total entries: {total}")
            console.print(f"  Sorted entries: {sorted_count}")
            console.print(f"  Unsorted entries: {total - sorted_count}")

            if not no_backup:
                backup_path = file_path.with_suffix(file_path.suffix + ".bak")
                console.print(f"\n[dim]Backup: {backup_path.name}[/dim]")

        else:
            try:
                target_date = datetime.strptime(date_or_all, "%Y-%m-%d").date()
            except ValueError:
                console.print(f"[red]ERROR[/red] Invalid date format: {date_or_all}")
                console.print("[dim]Use YYYY-MM-DD format (e.g., 2025-11-14)[/dim]")
                sys.exit(1)

            year_month = target_date.strftime("%Y-%m")
            day = target_date.strftime("%d")

            file_path = sorter.timeline_path / year_month / f"{day}.md"

            if not file_path.exists():
                console.print(f"[yellow]No timeline file for {date_or_all}[/yellow]")
                sys.exit(0)

            console.print(f"[cyan]Sorting {date_or_all}...[/cyan]")
            total, sorted_count = sorter.sort_file(file_path, create_backup=not no_backup)

            console.print(f"\n[green]OK[/green] Sorted {file_path.name}")
            console.print(f"  Total entries: {total}")
            console.print(f"  Sorted entries: {sorted_count}")
            console.print(f"  Unsorted entries: {total - sorted_count}")

            if not no_backup:
                backup_path = file_path.with_suffix(file_path.suffix + ".bak")
                console.print(f"\n[dim]Backup: {backup_path.name}[/dim]")

    except SortError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        sys.exit(1)


@app.command()
def review(
    period: str = typer.Argument(..., help="Period: 'weekly' or 'monthly'"),
    action: str = typer.Argument("create", help="Action: 'create' or 'show'"),
    identifier: str = typer.Argument(None, help="Week ID (W##) or Month (MM) for 'show' action"),
    editor: bool = typer.Option(True, "--editor/--no-editor", help="Open in editor after creation"),
):
    """Manage weekly and monthly reviews (mreview command).

    Examples:
        mreview weekly                  # Create/edit this week's review
        mreview weekly show             # Show this week's review
        mreview weekly show W47         # Show specific week review
        mreview monthly                 # Create/edit this month's review
        mreview monthly show            # Show this month's review
        mreview monthly show 11         # Show specific month review
    """
    try:
        import os
        import subprocess

        memory_path = Path.cwd() / ".memory"

        if not memory_path.exists():
            console.print("[red]ERROR[/red] .memory/ not found. Run 'minit' first.")
            sys.exit(1)

        manager = ReviewManager()

        if period.lower() not in ["weekly", "monthly"]:
            console.print(f"[red]ERROR[/red] Invalid period: {period}")
            console.print("[dim]Valid periods: weekly, monthly[/dim]")
            sys.exit(1)

        if action.lower() == "show":
            if period.lower() == "weekly":
                review_file = manager.get_weekly_review(week_id=identifier) if identifier else manager.get_weekly_review()

                if not review_file:
                    if identifier:
                        console.print(f"[yellow]![/yellow] Weekly review not found: {identifier}")
                    else:
                        console.print("[yellow]![/yellow] No review for this week yet")
                        console.print("[dim]Create one with: mreview weekly[/dim]")
                    sys.exit(1)

                content = review_file.read_text(encoding="utf-8")
                console.print(content)

            else:
                month_num = None
                year = None
                if identifier:
                    try:
                        month_num = int(identifier)
                        if month_num < 1 or month_num > 12:
                            console.print(f"[red]ERROR[/red] Invalid month: {month_num}")
                            console.print("[dim]Month must be between 1 and 12[/dim]")
                            sys.exit(1)
                    except ValueError:
                        console.print(f"[red]ERROR[/red] Invalid month format: {identifier}")
                        console.print("[dim]Use numeric month (1-12)[/dim]")
                        sys.exit(1)

                review_file = manager.get_monthly_review(month=month_num, year=year)

                if not review_file:
                    if identifier:
                        console.print(f"[yellow]![/yellow] Monthly review not found: {identifier}")
                    else:
                        console.print("[yellow]![/yellow] No review for this month yet")
                        console.print("[dim]Create one with: mreview monthly[/dim]")
                    sys.exit(1)

                content = review_file.read_text(encoding="utf-8")
                console.print(content)

        else:
            if period.lower() == "weekly":
                console.print("[cyan]Creating weekly review...[/cyan]")
                review_file = manager.create_weekly_review()

                week_id = manager.weekly.get_week_id()
                console.print(f"[green]OK[/green] Weekly review created: {week_id}")
                console.print(f"  → {review_file.relative_to(Path.cwd())}")

            else:
                console.print("[cyan]Creating monthly review...[/cyan]")
                review_file = manager.create_monthly_review()

                month_name = datetime.now().strftime("%B %Y")
                console.print(f"[green]OK[/green] Monthly review created: {month_name}")
                console.print(f"  → {review_file.relative_to(Path.cwd())}")

            if editor:
                editor_cmd = os.environ.get("EDITOR", "notepad" if sys.platform == "win32" else "vi")

                try:
                    console.print(f"\n[cyan]Opening in editor: {editor_cmd}[/cyan]")
                    subprocess.run([editor_cmd, str(review_file)], check=True)
                except subprocess.CalledProcessError:
                    console.print(f"[yellow]![/yellow] Failed to open editor")
                    console.print(f"[dim]Edit manually: {review_file}[/dim]")
                except FileNotFoundError:
                    console.print(f"[yellow]![/yellow] Editor not found: {editor_cmd}")
                    console.print(f"[dim]Set EDITOR environment variable or edit manually: {review_file}[/dim]")

    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)
