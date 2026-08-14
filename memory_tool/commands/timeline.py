"""Timeline-related CLI commands."""

import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List
import re

import typer

from memory_tool.commands.common import app, console, sanitize_output, opt_str, arg_str
from memory_tool.core.timeline import (
    Timeline,
    TimelineError,
    FutureTimeError,
    DistantPastWarning,
    date_from_timeline_path,
)
from memory_tool.core.sort import TimelineSorter, SortError
from memory_tool.context.builder import ContextBuilder
from memory_tool.utils.config import Config
from memory_tool.review import ReviewManager
from memory_tool.utils.paths import display_path, get_base_path


@app.command(
    epilog="For detailed help: [bold]mhelp record[/bold]  |  Korean: [bold]mconfig set help.language ko[/bold]"
)
def record(
    message: str = typer.Argument(..., help="Message to record in timeline"),
    date: Optional[str] = typer.Option(None, "--date", help="Date (YYYY-MM-DD), defaults to today"),
    time: Optional[str] = typer.Option(None, "--time", help="Time (HH:MM), defaults to current time"),
    force: bool = typer.Option(False, "--force", "-f", help="Force recording (skip warnings for old dates)"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Comma-separated tags (e.g., bug,auth,urgent)"),
):
    """Record a message to timeline (m command).

    Records a timestamped entry to your timeline. Entries are automatically
    organized by date and can be searched later with ms command.

    Tags can be added in three ways:
        m "[버그] Fixed login issue"       (bracket at start)
        m "[버그][긴급] Multiple tags"     (consecutive brackets)
        m "Fixed bug #bug #auth"           (hashtag at end)
        m "Fixed bug" --tags bug,auth      (explicit option)

    Examples:
        m "Started working on feature X"
        m "Fixed bug" --date 2026-01-20 --time 14:30
        m "[버그] Fixed login issue"
        m "[버그][긴급] Critical auth fix #sprint-1"
        m "Fixed auth bug #bug #auth #urgent"
    """
    message = arg_str(message)
    date = opt_str(date)
    time = opt_str(time)
    tags_str = opt_str(tags)

    # 1. Parse bracket tags from start of message (e.g., "[버그][긴급] message")
    # Supports Korean, alphanumeric, hyphens, underscores
    bracket_tags: List[str] = []
    bracket_tag_pattern = re.compile(r'^(\[[\w가-힣-]+\]\s*)+')
    bracket_match = bracket_tag_pattern.match(message)
    if bracket_match:
        bracket_tags = re.findall(r'\[([\w가-힣-]+)\]', bracket_match.group(0))
        message = message[bracket_match.end():].strip()

    # 2. Parse hashtag tags from end of message (e.g., "message #tag1 #tag2")
    # Supports Korean, alphanumeric, hyphens, underscores
    inline_tags: List[str] = []
    inline_tag_pattern = re.compile(r'(\s+#[\w가-힣-]+)+$')
    match = inline_tag_pattern.search(message)
    if match:
        tag_portion = match.group(0)
        inline_tags = re.findall(r'#([\w가-힣-]+)', tag_portion)
        message = message[:match.start()].strip()

    # 3. Parse --tags option
    tag_list: List[str] = []
    if tags_str:
        tag_list = [t.strip() for t in tags_str.split(",") if t.strip()]

    # Combine all tags (bracket + inline hashtag + option), deduplicate while preserving order
    all_tags = list(dict.fromkeys(bracket_tags + inline_tags + tag_list))
    if not all_tags:
        all_tags = None

    timeline = Timeline()

    try:
        dt, file_path = timeline.record(message, date, time, force=force, tags=all_tags)

        time_str = dt.strftime("%H:%M")
        date_str = dt.strftime("%Y-%m-%d")
        rel_path = display_path(file_path)

        console.print(f"[green]OK[/green] Recorded at {date_str} {time_str}")
        console.print(f"[dim]-> {rel_path}[/dim]")

        # Auto-update context if enabled
        try:
            config = Config()
            if config.auto_update_enabled:
                console.print("[dim]Auto-updating context...[/dim]")
                builder = ContextBuilder()
                context_path = builder.write_context()
                rel_context = display_path(context_path)
                console.print(f"[dim]-> {rel_context} updated[/dim]")
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Auto-update failed: {e}")

        # Document health suggestion
        try:
            from memory_tool.utils.suggestion_helper import check_and_suggest_after_command

            memory_dir = get_base_path()
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
            file_date = date_from_timeline_path(file_path)
            date_str = file_date.strftime("%Y-%m-%d") if file_date else file_path.stem

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
            file_date = date_from_timeline_path(file_path)
            date_str = file_date.strftime("%Y-%m-%d") if file_date else file_path.stem

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
            file_date = date_from_timeline_path(file_path)
            date_str = file_date.strftime("%Y-%m-%d") if file_date else file_path.stem

            console.print(f"[bold]{date_str}[/bold]")
            console.print(sanitize_output(content))
            console.print("")

        total_days_with_entries = len(days_files)
        console.print(f"[dim]{total_days_with_entries} day(s) with entries in the last {num_days} days[/dim]")

    except Exception as e:
        console.print(f"[red]ERROR[/red] Failed to read timeline: {e}")
        sys.exit(1)


@app.command()
def day(
    date_str: str = typer.Argument(..., help="Date: YYYY-MM-DD, MM-DD, or DD"),
):
    """Show timeline for a specific date (mday command).

    Supports flexible date formats:
      - Full date: 2026-01-15
      - Month-day: 01-15 or 1-15 (current year)
      - Day only: 15 (current month/year)

    Examples:
        mday 2026-01-15      # Specific date
        mday 01-15           # January 15 (current year)
        mday 15              # 15th of current month
    """
    timeline = Timeline()

    try:
        file_path, content, parsed_date = timeline.get_date(date_str)

        if parsed_date is None:
            console.print(f"[red]ERROR[/red] Invalid date format: {date_str}")
            console.print("[dim]Use: YYYY-MM-DD, MM-DD, or DD[/dim]")
            sys.exit(1)

        date_display = parsed_date.strftime("%Y-%m-%d")

        if content is None:
            console.print(f"[yellow]![/yellow] No timeline entries for {date_display}")
            console.print(f"[dim]File would be at: {file_path}[/dim]")
            return

        console.print(f"[cyan]{date_display} Timeline:[/cyan]\n")
        console.print(sanitize_output(content))
        console.print(f"\n[dim]File: {file_path}[/dim]")

    except Exception as e:
        console.print(f"[red]ERROR[/red] Failed to read timeline: {e}")
        sys.exit(1)


@app.command()
def edit(
    date_str: str = typer.Argument(None, help="Date: YYYY-MM-DD, MM-DD, DD, or 'today'"),
):
    """Interactive editor for timeline entries (medit command).

    Edit or delete specific entries from a date's timeline.

    Commands in editor:
      <n>        - Edit entry message
      t <n>      - Change entry time
      d <n>      - Delete entry
      s          - Save and exit
      q          - Quit without saving
      ?          - Show help

    Examples:
        medit               # Edit today's timeline
        medit 2026-01-15    # Edit specific date
        medit 15            # Edit 15th of current month
    """
    from rich.prompt import Prompt
    from rich.table import Table
    from rich.panel import Panel
    from memory_tool.commands.common import get_help_language

    # Get language setting
    lang = get_help_language()
    is_ko = (lang == "ko")

    # Bilingual messages
    msg = {
        "error": "오류" if is_ko else "ERROR",
        "invalid_date": "잘못된 날짜 형식" if is_ko else "Invalid date format",
        "date_hint": "사용: YYYY-MM-DD, MM-DD, 또는 DD" if is_ko else "Use: YYYY-MM-DD, MM-DD, or DD",
        "no_entries": "타임라인 항목 없음" if is_ko else "No timeline entries for",
        "file_at": "파일 위치" if is_ko else "File would be at",
        "time_col": "시간" if is_ko else "Time",
        "message_col": "메시지" if is_ko else "Message",
        "help_title": "도움말" if is_ko else "Help",
        "help_commands": "[bold]명령어:[/bold]" if is_ko else "[bold]Commands:[/bold]",
        "help_edit": "항목 n 메시지 편집 (예: '1')" if is_ko else "Edit entry n message (e.g., '1')",
        "help_time": "항목 n 시간 변경 (예: 't 1')" if is_ko else "Change entry n time (e.g., 't 1')",
        "help_delete": "항목 n 삭제 (예: 'd 2')" if is_ko else "Delete entry n (e.g., 'd 2')",
        "help_save": "변경사항 저장 후 종료" if is_ko else "Save changes and exit",
        "help_quit": "저장 없이 종료" if is_ko else "Quit without saving",
        "help_help": "도움말 표시" if is_ko else "Show this help",
        "modified": "(수정됨)" if is_ko else "(modified)",
        "discard": "변경사항을 버리시겠습니까?" if is_ko else "Discard changes?",
        "exited": "저장 없이 종료됨" if is_ko else "Exited without saving",
        "saved": "개 항목 저장됨" if is_ko else "entries saved to",
        "no_changes": "저장할 변경사항 없음" if is_ko else "No changes to save",
        "delete_prompt": "삭제" if is_ko else "Delete",
        "confirm_delete": "삭제하시겠습니까?" if is_ko else "Confirm delete?",
        "deleted": "삭제됨" if is_ko else "Deleted",
        "cancelled": "취소됨" if is_ko else "Cancelled",
        "invalid_num": "잘못된 항목 번호. 1-{n} 사용" if is_ko else "Invalid entry number. Use 1-{n}",
        "usage_delete": "사용법: d <번호>" if is_ko else "Usage: d <number>",
        "editing": "편집 중" if is_ko else "Editing",
        "enter_message": "새 메시지 입력 (취소하려면 빈 값)" if is_ko else "Enter new message (or empty to cancel)",
        "message_prompt": "메시지" if is_ko else "Message",
        "updated": "수정됨" if is_ko else "Updated",
        "unknown_cmd": "알 수 없는 명령" if is_ko else "Unknown command",
        "hint_help": "도움말: ?" if is_ko else "type ? for help",
        "hint_quit": "'q'로 종료, 's'로 저장" if is_ko else "Use 'q' to quit, 's' to save",
        "hint_commands": "[dim]명령어: <n>=편집  t<n>=시간  d<n>=삭제  s=저장  q=종료  ?=도움말[/dim]" if is_ko else "[dim]Commands: <n>=edit  t<n>=time  d<n>=delete  s=save  q=quit  ?=help[/dim]",
        "time_change": "시간 변경" if is_ko else "Change time",
        "enter_time": "새 시간 입력 (HH:MM, 취소하려면 빈 값)" if is_ko else "Enter new time (HH:MM, or empty to cancel)",
        "time_prompt": "시간" if is_ko else "Time",
        "invalid_time": "잘못된 시간 형식. HH:MM 사용 (예: 09:30)" if is_ko else "Invalid time format. Use HH:MM (e.g., 09:30)",
        "usage_time": "사용법: t <번호>" if is_ko else "Usage: t <number>",
        "time_updated": "시간 변경됨" if is_ko else "Time changed",
    }

    timeline = Timeline()

    # Default to today if no date provided
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # Parse entries
    file_path, entries, parsed_date = timeline.parse_entries(date_str)

    if parsed_date is None:
        console.print(f"[red]{msg['error']}[/red] {msg['invalid_date']}: {date_str}")
        console.print(f"[dim]{msg['date_hint']}[/dim]")
        sys.exit(1)

    date_display = parsed_date.strftime("%Y-%m-%d")

    if not entries:
        console.print(f"[yellow]![/yellow] {msg['no_entries']} {date_display}")
        if file_path:
            console.print(f"[dim]{msg['file_at']}: {file_path}[/dim]")
        return

    # Track changes
    modified = False
    current_entries = entries.copy()

    def show_entries():
        """Display entries in a table."""
        table = Table(title=f"Timeline: {date_display}", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column(msg['time_col'], style="bold", width=6)
        table.add_column(msg['message_col'], overflow="fold")

        for i, entry in enumerate(current_entries):
            table.add_row(str(i + 1), entry['time'], entry['message'])

        console.print(table)
        console.print()

    def show_hint():
        """Display condensed command hint."""
        console.print(msg['hint_commands'])

    def show_help():
        """Display help."""
        help_text = f"""{msg['help_commands']}
  [cyan]<n>[/cyan]        {msg['help_edit']}
  [cyan]t <n>[/cyan]      {msg['help_time']}
  [cyan]d <n>[/cyan]      {msg['help_delete']}
  [cyan]s[/cyan]          {msg['help_save']}
  [cyan]q[/cyan]          {msg['help_quit']}
  [cyan]?[/cyan]          {msg['help_help']}"""
        console.print(Panel(help_text, title=msg['help_title'], border_style="blue"))

    # Main loop
    console.print()
    show_entries()
    show_help()
    console.print()

    while True:
        try:
            prompt_text = "[green]>[/green] " if not modified else f"[yellow]>[/yellow] {msg['modified']} "
            cmd = Prompt.ask(prompt_text).strip()

            if not cmd:
                continue

            # Quit without saving
            if cmd.lower() == 'q':
                if modified:
                    confirm = Prompt.ask(msg['discard'], choices=["y", "n"], default="n")
                    if confirm.lower() != 'y':
                        continue
                console.print(f"[dim]{msg['exited']}[/dim]")
                break

            # Save and exit
            if cmd.lower() == 's':
                if modified:
                    timeline.save_entries(file_path, current_entries, parsed_date)
                    if is_ko:
                        console.print(f"[green]{len(current_entries)}{msg['saved']} {file_path.name}[/green]")
                    else:
                        console.print(f"[green]{len(current_entries)} {msg['saved']} {file_path.name}[/green]")
                else:
                    console.print(f"[dim]{msg['no_changes']}[/dim]")
                break

            # Help
            if cmd == '?':
                show_help()
                continue

            # Change time: t <n>
            if cmd.lower().startswith('t '):
                try:
                    idx = int(cmd[2:].strip()) - 1
                    if 0 <= idx < len(current_entries):
                        entry = current_entries[idx]
                        console.print(f"\n{msg['time_change']}: [cyan]{entry['time']}[/cyan] | {entry['message'][:50]}")
                        console.print(f"[dim]{msg['enter_time']}:[/dim]")

                        new_time = Prompt.ask(msg['time_prompt'])
                        if new_time.strip():
                            # Validate time format
                            import re
                            time_match = re.match(r'^(\d{1,2}):(\d{2})$', new_time.strip())
                            if time_match:
                                hour = int(time_match.group(1))
                                minute = int(time_match.group(2))
                                if 0 <= hour <= 23 and 0 <= minute <= 59:
                                    # Format as HH:MM
                                    formatted_time = f"{hour:02d}:{minute:02d}"
                                    current_entries[idx]['time'] = formatted_time
                                    modified = True
                                    console.print(f"[green]{msg['time_updated']}: {formatted_time}[/green]")
                                    show_entries()
                                    show_hint()
                                else:
                                    console.print(f"[red]{msg['invalid_time']}[/red]")
                            else:
                                console.print(f"[red]{msg['invalid_time']}[/red]")
                        else:
                            console.print(f"[dim]{msg['cancelled']}[/dim]")
                    else:
                        console.print(f"[red]{msg['invalid_num'].format(n=len(current_entries))}[/red]")
                except ValueError:
                    console.print(f"[red]{msg['usage_time']}[/red]")
                continue

            # Delete entry: d <n>
            if cmd.lower().startswith('d '):
                try:
                    idx = int(cmd[2:].strip()) - 1
                    if 0 <= idx < len(current_entries):
                        entry = current_entries[idx]
                        console.print(f"{msg['delete_prompt']}: [cyan]{entry['time']}[/cyan] | {entry['message'][:50]}...")
                        confirm = Prompt.ask(msg['confirm_delete'], choices=["y", "n"], default="n")
                        if confirm.lower() == 'y':
                            current_entries.pop(idx)
                            modified = True
                            console.print(f"[green]{msg['deleted']}[/green]")
                            show_entries()
                            show_hint()
                        else:
                            console.print(f"[dim]{msg['cancelled']}[/dim]")
                    else:
                        console.print(f"[red]{msg['invalid_num'].format(n=len(current_entries))}[/red]")
                except ValueError:
                    console.print(f"[red]{msg['usage_delete']}[/red]")
                continue

            # Edit entry: <n>
            if cmd.isdigit():
                idx = int(cmd) - 1
                if 0 <= idx < len(current_entries):
                    entry = current_entries[idx]
                    console.print(f"\n{msg['editing']}: [cyan]{entry['time']}[/cyan] | {entry['message']}")
                    console.print(f"[dim]{msg['enter_message']}:[/dim]")

                    new_message = Prompt.ask(msg['message_prompt'])
                    if new_message.strip():
                        current_entries[idx]['message'] = new_message.strip()
                        modified = True
                        console.print(f"[green]{msg['updated']}[/green]")
                        show_entries()
                        show_hint()
                    else:
                        console.print(f"[dim]{msg['cancelled']}[/dim]")
                else:
                    console.print(f"[red]{msg['invalid_num'].format(n=len(current_entries))}[/red]")
                continue

            # Unknown command
            console.print(f"[red]{msg['unknown_cmd']}: {cmd}[/red] ({msg['hint_help']})")

        except KeyboardInterrupt:
            console.print(f"\n[dim]{msg['hint_quit']}[/dim]")
        except EOFError:
            break


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

            file_path = Timeline.resolve_existing_file(sorter.timeline_path, today_date)

            if file_path is None:
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

            file_path = Timeline.resolve_existing_file(sorter.timeline_path, target_date)

            if file_path is None:
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

        memory_path = get_base_path()

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
                console.print(f"  → {display_path(review_file)}")

            else:
                console.print("[cyan]Creating monthly review...[/cyan]")
                review_file = manager.create_monthly_review()

                month_name = datetime.now().strftime("%B %Y")
                console.print(f"[green]OK[/green] Monthly review created: {month_name}")
                console.print(f"  → {display_path(review_file)}")

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
