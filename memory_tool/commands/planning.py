"""Planning-related CLI commands (plan, summary)."""

import io
import sys
from datetime import datetime, date
from pathlib import Path
from typing import List, NoReturn, Optional

import typer
from rich.console import Console
from rich.markup import escape

from memory_tool.commands import json_output
from memory_tool.commands.common import app, console, opt_str, arg_str, resolve_module_name, print_llm_unavailable
from memory_tool.commands.common import console as shared_console
from memory_tool.core.doc_sections import SectionError, read_decisions_text
from memory_tool.llm.client import LLMClient
from memory_tool.summary import TimelineSummarizer, ModuleSummarizer
from memory_tool.utils.paths import display_path, get_base_path


def _interactive_carryover(tasks: List[str], task_type: str = "task") -> List[str]:
    """Interactive selection of tasks/goals to carry over.

    Args:
        tasks: List of task/goal texts
        task_type: "task" or "goal" for display purposes

    Returns:
        List of selected task/goal texts
    """
    if not tasks:
        return []

    console.print(f"\nIncomplete {task_type}s:")
    for i, task in enumerate(tasks, 1):
        console.print(f"  [{i}] 📋 {task}")

    console.print(f"\n[dim]Select {task_type}s to carry over (e.g., 1,2,3 or 'all' or 'none'):[/dim]")

    try:
        selection = input("> ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return []

    if selection == "none" or selection == "":
        return []

    if selection == "all":
        return tasks

    # Parse comma-separated numbers
    selected = []
    try:
        indices = [int(x.strip()) for x in selection.split(",")]
        for idx in indices:
            if 1 <= idx <= len(tasks):
                selected.append(tasks[idx - 1])
    except ValueError:
        console.print("[red]Invalid selection[/red]")
        return []

    return selected


class _CountingClient:
    """Count the LLM calls a summary makes, to tell whether it came from the cache."""

    def __init__(self, client):
        self._client = client
        self.calls = 0

    def summarize(self, *args, **kwargs):
        self.calls += 1
        return self._client.summarize(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._client, name)


@app.command()
def summary(
    scope: str = typer.Argument("today", help="Scope: 'today', 'week', date (YYYY-MM-DD), or date range (YYYY-MM-DD:YYYY-MM-DD)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path (optional)"),
    module_name: Optional[str] = typer.Option(None, "--module", "-m", help="Summarize specific module"),
    decisions: bool = typer.Option(False, "--decisions", help="Summarize decisions.md only (requires --module)"),
    lang: Optional[str] = typer.Option(None, "--lang", "-l", help="Output language: 'ko' (Korean), 'en' (English), 'auto' (detect)"),
    force: bool = typer.Option(False, "--force", "-f", help="Force regeneration, bypassing cache"),
    as_json: bool = typer.Option(False, "--json", help="Print the summary as one line of JSON (for editors and scripts)"),
):
    """Summarize timeline or module using LLM (msummary command)."""
    # Everything below prints through `console`. In JSON mode only the result
    # line may reach standard output.
    console = Console(file=io.StringIO()) if as_json else shared_console

    scope = arg_str(scope)
    output = opt_str(output)
    module_name = opt_str(module_name)
    lang = opt_str(lang)

    def failed(code: str, message: str, hint: Optional[str] = None, style: str = "[red]ERROR[/red]") -> NoReturn:
        if as_json:
            json_output.fail(code, message)
        shared_console.print(f"{style} {message}")
        if hint:
            shared_console.print(f"[dim]{hint}[/dim]")
        sys.exit(1)

    def finished(summary_text: str, kind: str, target: str) -> None:
        saved = None
        if output:
            Path(output).write_text(summary_text, encoding="utf-8")
            saved = json_output.path_text(Path(output))

        if as_json:
            json_output.succeed(
                kind=kind, scope=target, summary=summary_text,
                cached=llm_client.calls == 0, saved_to=saved,
            )
            return

        console.print("\n" + "="*80)
        console.print(summary_text)
        console.print("="*80)
        if saved:
            console.print(f"\n[green]OK[/green] Summary saved to: {output}")

    if not LLMClient.check_availability():
        if as_json:
            json_output.fail(json_output.LLM_UNAVAILABLE, json_output.llm_unavailable_message())
        print_llm_unavailable(console)
        sys.exit(1)

    if decisions and not module_name:
        failed(
            json_output.INVALID_ARGUMENT, "--decisions flag requires --module to be specified",
            "Example: msummary --module project-management --decisions",
        )

    try:
        llm_client = _CountingClient(LLMClient())

        if module_name:
            resolved_module = resolve_module_name(module_name)

            if decisions:
                if force:
                    console.print(f"[cyan]Summarizing decisions.md from '{resolved_module}' (force regeneration)...[/cyan]")
                else:
                    console.print(f"[cyan]Summarizing decisions.md from '{resolved_module}'...[/cyan]")

                module_path = get_base_path() / "modules" / resolved_module
                try:
                    decisions_content = read_decisions_text(module_path)
                except SectionError as e:
                    failed(json_output.FAILED, str(e))

                if decisions_content is None:
                    failed(json_output.NOT_FOUND, f"No decisions found in module '{resolved_module}'")

                prompt = f"""Analyze and summarize the following decisions.md content from a software project module.

Provide:
1. Overview: Total number of decisions and time span
2. Key Categories: Group decisions by theme/topic
3. Major Decisions: Highlight the most important 3-5 decisions
4. Patterns: Any trends or patterns in decision-making
5. Archive Suggestions: Which decisions are outdated and could be archived (if any)

Decisions Content:
```markdown
{decisions_content}
```

Provide a clear, structured summary in markdown format."""

                import hashlib
                content_hash = hashlib.sha256(decisions_content.encode('utf-8')).hexdigest()[:16]
                safe_module_name = resolved_module.replace('/', '_').replace('\\', '_')
                cache_key = f"decisions_{safe_module_name}_{content_hash}"

                if force:
                    summary_text = llm_client.summarize(
                        content=prompt,
                        system_prompt="You are a technical analyst specializing in software project documentation."
                    )
                else:
                    cache_dir = get_base_path() / "summaries"
                    cache_file = cache_dir / f"{cache_key}.md"

                    if cache_file.exists():
                        console.print("[dim]Using cached summary (content unchanged)[/dim]")
                        summary_text = cache_file.read_text(encoding="utf-8")
                    else:
                        summary_text = llm_client.summarize(
                            content=prompt,
                            system_prompt="You are a technical analyst specializing in software project documentation."
                        )

                        cache_dir.mkdir(parents=True, exist_ok=True)
                        cache_file.write_text(summary_text, encoding="utf-8")

            else:
                if force:
                    console.print(f"[cyan]Summarizing module '{resolved_module}' (force regeneration)...[/cyan]")
                else:
                    console.print(f"[cyan]Summarizing module '{resolved_module}'...[/cyan]")

                summarizer = ModuleSummarizer(llm_client)
                module_path = get_base_path() / "modules" / resolved_module

                summary_text = summarizer.summarize_module(
                    module_path, force=force, output_language=lang
                )

            finished(summary_text, "decisions" if decisions else "module", resolved_module)
            return

        summarizer = TimelineSummarizer(llm_client)

        force_msg = " (force regeneration)" if force else ""
        if scope.lower() == "today":
            console.print(f"[cyan]Summarizing today's timeline{force_msg}...[/cyan]")
            summary_text = summarizer.summarize_today(output_language=lang, force=force)

        elif scope.lower() == "week":
            console.print(f"[cyan]Summarizing this week's timeline{force_msg}...[/cyan]")
            summary_text = summarizer.summarize_week(output_language=lang, force=force)

        elif ":" in scope:
            try:
                start_str, end_str = scope.split(":")
                start_date = datetime.strptime(start_str.strip(), "%Y-%m-%d").date()
                end_date = datetime.strptime(end_str.strip(), "%Y-%m-%d").date()

                console.print(f"[cyan]Summarizing timeline from {start_date} to {end_date}{force_msg}...[/cyan]")
                summary_text = summarizer.summarize_range(start_date, end_date, output_language=lang, force=force)

            except ValueError as e:
                failed(
                    json_output.INVALID_ARGUMENT, f"Invalid date range format: {scope}",
                    "Use: YYYY-MM-DD:YYYY-MM-DD (e.g., 2025-11-01:2025-11-14)",
                )

        else:
            try:
                target_date = datetime.strptime(scope, "%Y-%m-%d").date()
                console.print(f"[cyan]Summarizing timeline for {target_date}{force_msg}...[/cyan]")
                summary_text = summarizer.summarize_date(target_date, output_language=lang, force=force)

            except ValueError:
                failed(
                    json_output.INVALID_ARGUMENT, f"Invalid date format: {scope}",
                    "Use YYYY-MM-DD format (e.g., 2025-11-14)",
                )

        finished(summary_text, "timeline", scope.lower())

    except FileNotFoundError as e:
        failed(json_output.NOT_FOUND, str(e), style="[yellow]![/yellow]")

    except ValueError as e:
        failed(json_output.FAILED, str(e))

    except Exception as e:
        if as_json:
            json_output.fail(json_output.LLM_FAILED, f"Unexpected error: {e}")
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


# ---------------------------------------------------------------------------
# mplan daily
# ---------------------------------------------------------------------------


def _daily_task_dict(task: dict) -> dict:
    """One task for --json. ``line`` is 1-based, as --line takes it."""
    return {
        "line": task["line_num"] + 1,
        "text": task["text"],
        "done": task["completed"],
        "time": task["time"],
    }


def _daily_plan_dict(plan_mgr, target_date: date) -> dict:
    """A day's plan for --json, read without changing anything."""
    plan_path = plan_mgr.get_plan_path(target_date)
    tasks = plan_mgr.get_tasks(target_date)
    return {
        "date": target_date.strftime("%Y-%m-%d"),
        "path": json_output.path_text(plan_path),
        "exists": plan_path.exists(),
        "tasks": [_daily_task_dict(task) for task in tasks],
        "progress": {"done": sum(1 for t in tasks if t["completed"]), "total": len(tasks)},
        "recurring": plan_mgr._get_recurring_content(),
    }


def _daily_task_at(plan_mgr, text: str, target_date: date, completed: bool) -> Optional[dict]:
    """The first task with this exact text, done or not."""
    for task in plan_mgr.get_tasks(target_date):
        if task["text"] == text and task["completed"] == completed:
            return task
    return None


def _daily_plan(
    plan_mgr,
    name: Optional[str],
    title: Optional[str],
    as_json: bool,
    line: Optional[int],
    carry: List[str],
) -> None:
    """mplan daily [show|add|done|undo|carryover|<date>] for people and, with --json, programs."""
    from datetime import timedelta
    import os
    import subprocess
    from rich.markup import escape

    today = date.today()
    yesterday = today - timedelta(days=1)

    def failed(code: str, message: str, hint: Optional[str] = None, **fields) -> NoReturn:
        if as_json:
            json_output.fail(code, message, **fields)
        console.print(f"[red]ERROR[/red] {escape(message)}")
        if hint:
            console.print(f"[dim]{escape(hint)}[/dim]")
        sys.exit(1)

    def show(target_date: date) -> None:
        if as_json:
            json_output.succeed(**_daily_plan_dict(plan_mgr, target_date))
        else:
            console.print(plan_mgr.show_plan(target_date), markup=False)

    def list_choices(completed: bool) -> None:
        choices = [t for t in plan_mgr.get_tasks() if t["completed"] == completed]
        if choices and not as_json:
            console.print("\n[dim]Available tasks:[/dim]")
            for t in choices:
                console.print(f"  {t['index']}. {escape(t['text'])}")

    if name is None or name == "show":
        target_date = today
        if title:
            target_date = plan_mgr.parse_date_keyword(title)
            if target_date is None:
                failed(json_output.INVALID_ARGUMENT, f"Invalid date: {title}", "Use YYYY-MM-DD, 'today' or 'yesterday'")
        show(target_date)
        return

    if name == "yesterday":
        show(yesterday)
        return

    if name == "add":
        if not title or not title.strip():
            failed(json_output.INVALID_ARGUMENT, "Task title required", "Usage: mplan daily add <task>")
        plan_mgr.add_task(title)
        text = " ".join(title.split())
        if as_json:
            task = _daily_task_at(plan_mgr, text, today, completed=False)
            json_output.succeed(task=_daily_task_dict(task), plan=_daily_plan_dict(plan_mgr, today))
            return
        console.print("[green]OK[/green] Task added to today's plan")
        console.print(escape(f"  - [ ] {text}"))
        return

    if name in ("done", "undo"):
        completing = name == "done"
        if not title:
            failed(
                json_output.INVALID_ARGUMENT,
                "Task title or index required",
                f"Usage: mplan daily {name} <task|index>   e.g. mplan daily {name} 1, mplan daily {name} \"Write\"",
            )

        if completing:
            success, result = plan_mgr.mark_done(title, line=line)
            removed = None
        else:
            success, result, removed = plan_mgr.mark_undone(title, line=line)

        if not success:
            if result == "ambiguous":
                if not as_json:
                    console.print(f"[yellow]Multiple tasks match '{escape(title)}':[/yellow]")
                    for t in plan_mgr.get_tasks():
                        if t["completed"] != completing and title.lower() in t["text"].lower():
                            console.print(f"  {t['index']}. {escape(t['text'])}")
                    console.print(f"\n[dim]Use index number: mplan daily {name} <number>[/dim]")
                    sys.exit(1)
                failed(json_output.INVALID_ARGUMENT, f"Several tasks match: {title}")
            where = f" on line {line}" if line is not None else ""
            state = "incomplete" if completing else "completed"
            if not as_json:
                console.print(f"[red]ERROR[/red] No {state} task{escape(where)}: {escape(title)}")
                list_choices(completed=not completing)
                sys.exit(1)
            failed(
                json_output.NOT_FOUND,
                f"No {state} task{where}: {title}. The plan may have been changed since.",
            )

        task = _daily_task_at(plan_mgr, result, today, completed=completing)

        if completing:
            entry = None
            if task and task["time"]:
                from memory_tool.planner.integration import PlanTimelineIntegration

                integration = PlanTimelineIntegration(plan_mgr.base_path)
                message = integration.completion_message(result, "daily", today)
                _, _, position = integration.timeline().find_entry(today.strftime("%Y-%m-%d"), task["time"], message)
                if position is not None:
                    entry = {"date": today.strftime("%Y-%m-%d"), "time": task["time"], "text": message}
            if as_json:
                json_output.succeed(
                    task=_daily_task_dict(task) if task else None,
                    timeline=entry,
                    plan=_daily_plan_dict(plan_mgr, today),
                )
                return
            console.print("[green]OK[/green] Task marked as completed")
            console.print(escape(f"  - [x] {result}"))
            return

        notices = []
        if not removed:
            notices.append(json_output.notice(
                "plan",
                "The task's timeline entry was not found (changed or deleted since), so it was left as it is.",
            ))
        if as_json:
            json_output.succeed(
                task=_daily_task_dict(task) if task else None,
                timeline_removed=bool(removed),
                plan=_daily_plan_dict(plan_mgr, today),
                notices=notices,
            )
            return
        console.print("[green]OK[/green] Task marked as not done")
        console.print(escape(f"  - [ ] {result}"))
        if removed:
            console.print("[dim]Its timeline entry was deleted.[/dim]")
        else:
            console.print("[yellow]Its timeline entry was not found and was left as it is.[/yellow]")
        return

    if name == "carryover":
        incomplete = plan_mgr.get_incomplete_tasks(yesterday)

        if carry:
            # Without asking: only the tasks named, and only if yesterday left them undone.
            missing = [t for t in carry if t not in incomplete]
            wanted = [t for t in carry if t in incomplete]
            present = {t["text"] for t in plan_mgr.get_tasks(today)}
            skipped = [t for t in dict.fromkeys(wanted) if t in present]
            carried = [t for t in dict.fromkeys(wanted) if t not in present]
            plan_mgr.carryover_tasks(carried, yesterday, today)
            if as_json:
                json_output.succeed(
                    **{"from": yesterday.strftime("%Y-%m-%d")},
                    carried=carried,
                    skipped=skipped,
                    missing=missing,
                    plan=_daily_plan_dict(plan_mgr, today),
                )
                return
            console.print(f"[green]OK[/green] Carried over {len(carried)} task(s) to today's plan")
            for task in carried:
                console.print(f"  - {escape(task)}")
            for task in skipped:
                console.print(f"  [dim]already in today's plan: {escape(task)}[/dim]")
            for task in missing:
                console.print(f"  [yellow]not an incomplete task yesterday: {escape(task)}[/yellow]")
            return

        if as_json:
            failed(
                json_output.INVALID_ARGUMENT,
                "Name the tasks to carry over with --task; mplan daily show yesterday --json lists them.",
            )

        if not incomplete:
            console.print(f"[yellow]No incomplete tasks from yesterday ({yesterday.strftime('%Y-%m-%d')})[/yellow]")
            return

        console.print(f"[cyan]Yesterday's incomplete tasks ({yesterday.strftime('%Y-%m-%d')}):[/cyan]")
        selected = _interactive_carryover(incomplete, "task")

        if not selected:
            console.print("[dim]No tasks selected[/dim]")
            return

        count = plan_mgr.carryover_tasks(selected, yesterday, today)
        console.print(f"\n[green]OK[/green] Carried over {count} task(s) to today's plan")
        for task in selected:
            console.print(f"  - {escape(task)}")
        return

    # mplan daily 2026-01-15
    target_date = plan_mgr.parse_date_keyword(name)
    if target_date:
        show(target_date)
        return

    if as_json:
        failed(json_output.INVALID_ARGUMENT, f"Unknown daily action: {name}")

    # Default: create plan
    plan_path = plan_mgr.create_plan()
    console.print("[green]OK[/green] Daily plan ready")
    console.print(f"  → {display_path(plan_path)}")

    editor = os.environ.get('EDITOR')
    if editor:
        subprocess.run([editor, str(plan_path)])


@app.command()
def plan(
    action: str = typer.Argument(..., help="Action: create, list, show, add, done, delete, daily, weekly, monthly"),
    name: str = typer.Argument(None, help="Plan name or sub-action (add/done/show)"),
    title: str = typer.Argument(None, help="Task title (for 'add' action)"),
    description: str = typer.Option("", "--desc", "-d", help="Plan description"),
    due_date: Optional[str] = typer.Option(None, "--due", help="Due date (YYYY-MM-DD)"),
    tags: List[str] = typer.Option([], "--tag", "-t", help="Tags"),
    as_json: bool = typer.Option(False, "--json", help="mplan daily only: print the result as one line of JSON"),
    line: Optional[int] = typer.Option(None, "--line", help="mplan daily done/undo: the task's line (from --json); the text must match it"),
    carry: List[str] = typer.Option([], "--task", help="mplan daily carryover: a task to carry over, without asking (repeatable)"),
):
    """Manage plans and tasks (mplan command).

    Actions (Project Plans):
        create: Create a new project plan
        list: List all project plans
        show: Show plan details
        add: Add task to plan
        done: Mark task as completed
        delete: Delete a plan

    Actions (Time-based Plans):
        daily: Daily plan (today)
        weekly: Weekly plan (this week)
        monthly: Monthly plan (this month)

    Examples (Project Plans):
        mplan create "Project Alpha" --desc "Main project plan"
        mplan list
        mplan show "Project Alpha"
        mplan add "Project Alpha" "Implement feature X"
        mplan done "Project Alpha" "Implement feature X"
        mplan delete "Project Alpha"

    Examples (Time-based Plans):
        mplan daily              # Show today's plan
        mplan daily yesterday    # Show yesterday's plan
        mplan daily show 2026-01-15  # Show specific date
        mplan daily add "Task"   # Add task to today
        mplan daily done "Task"  # Mark task as done
        mplan daily undo "Task"  # Mark a done task as not done (deletes its timeline entry)
        mplan daily carryover    # Move yesterday's incomplete to today
        mplan daily carryover --task "Task"   # ... without asking
        mplan daily show --json  # For programs: tasks with their lines

        mplan weekly             # Show this week's plan
        mplan weekly lastweek    # Show last week's plan
        mplan weekly show W03    # Show specific week
        mplan weekly add "Goal"  # Add goal to this week
        mplan weekly carryover   # Move last week's incomplete to this week

        mplan monthly            # Show this month's plan

    """
    due_date = opt_str(due_date)

    try:
        from memory_tool.planner import (
            PlanManager, Task, TaskStatus,
            DailyPlan, WeeklyPlan, MonthlyPlan
        )
        import subprocess
        import os

        memory_path = get_base_path()

        if as_json and action != "daily":
            json_output.fail(json_output.INVALID_ARGUMENT, "--json is supported by mplan daily only")

        if not memory_path.exists():
            if as_json:
                json_output.fail(json_output.NOT_INITIALIZED, "No knowledge base. Run 'minit' first.")
            console.print("[red]ERROR[/red] .memory/ not found. Run 'minit' first.")
            sys.exit(1)

        if action in ["daily", "weekly", "monthly"]:
            if action == "daily":
                _daily_plan(DailyPlan(base_path=memory_path), name, title, as_json, line, carry)
                return

            elif action == "weekly":
                plan_mgr = WeeklyPlan(base_path=memory_path)

                if name is None or name == "show":
                    # mplan weekly OR mplan weekly show [W03|lastweek]
                    week_id = title if title else None
                    content = plan_mgr.show_plan(week_id)
                    console.print(content, markup=False)

                elif name == "lastweek":
                    # mplan weekly lastweek
                    content = plan_mgr.show_plan("lastweek")
                    console.print(content, markup=False)

                elif name == "add":
                    if not title:
                        console.print("[red]ERROR[/red] Goal required")
                        console.print("[dim]Usage: mplan weekly add <goal>[/dim]")
                        sys.exit(1)

                    plan_mgr.add_goal(title)
                    console.print(f"[green]OK[/green] Goal added to this week's plan")
                    console.print(escape(f"  - [ ] {title}"))

                elif name == "done":
                    if not title:
                        console.print("[red]ERROR[/red] Goal title or index required")
                        console.print("[dim]Usage: mplan weekly done <goal|index>[/dim]")
                        console.print("[dim]Examples:[/dim]")
                        console.print("[dim]  mplan weekly done 1          # Complete 1st goal[/dim]")
                        console.print("[dim]  mplan weekly done \"Review\"   # Prefix match[/dim]")
                        sys.exit(1)

                    success, result = plan_mgr.mark_done(title)
                    if success:
                        console.print(f"[green]OK[/green] Goal marked as completed")
                        console.print(escape(f"  - [x] {result}"))
                    elif result == "ambiguous":
                        # Show matching goals for user to choose
                        console.print(f"[yellow]Multiple goals match '{title}':[/yellow]")
                        goals = plan_mgr.get_goals(incomplete_only=True)
                        for g in goals:
                            if title.lower() in g['text'].lower():
                                console.print(f"  {g['index']}. {g['text']}")
                        console.print(f"\n[dim]Use index number: mplan weekly done <number>[/dim]")
                        sys.exit(1)
                    else:
                        console.print(f"[red]ERROR[/red] Goal not found: {title}")
                        # Show available goals
                        goals = plan_mgr.get_goals(incomplete_only=True)
                        if goals:
                            console.print(f"\n[dim]Available goals:[/dim]")
                            for g in goals:
                                console.print(f"  {g['index']}. {g['text']}")
                        sys.exit(1)

                elif name == "carryover":
                    # mplan weekly carryover
                    from datetime import timedelta
                    last_week_date = date.today() - timedelta(weeks=1)
                    incomplete = plan_mgr.get_incomplete_goals(last_week_date)
                    _, week_num, _, _ = plan_mgr.get_week_info(last_week_date)

                    if not incomplete:
                        console.print(f"[yellow]No incomplete goals from last week (W{week_num:02d})[/yellow]")
                        return

                    console.print(f"[cyan]Last week's incomplete goals (W{week_num:02d}):[/cyan]")
                    selected = _interactive_carryover(incomplete, "goal")

                    if not selected:
                        console.print("[dim]No goals selected[/dim]")
                        return

                    count = plan_mgr.carryover_goals(selected, last_week_date, date.today())
                    _, this_week_num, _, _ = plan_mgr.get_week_info()
                    console.print(f"\n[green]OK[/green] Carried over {count} goal(s) to this week (W{this_week_num:02d})")
                    for goal in selected:
                        console.print(f"  - {goal}")

                else:
                    # Try as week ID (W03, lastweek, etc.)
                    if name.lower().startswith("w") or name.lower() == "lastweek":
                        content = plan_mgr.show_plan(name)
                        console.print(content, markup=False)
                        return

                    plan_path = plan_mgr.create_plan()
                    console.print(f"[green]OK[/green] Weekly plan ready")
                    console.print(f"  → {display_path(plan_path)}")

                    editor = os.environ.get('EDITOR')
                    if editor:
                        subprocess.run([editor, str(plan_path)])

                    return

            elif action == "monthly":
                plan_mgr = MonthlyPlan(base_path=memory_path)

                if name is None or name == "show":
                    month_id = title if title else None
                    content = plan_mgr.show_plan(month_id)
                    console.print(content, markup=False)

                elif name == "add":
                    if not title:
                        console.print("[red]ERROR[/red] Goal required")
                        console.print("[dim]Usage: mplan monthly add <goal>[/dim]")
                        sys.exit(1)

                    plan_mgr.add_goal(title)
                    console.print(f"[green]OK[/green] Goal added to this month's plan")
                    console.print(escape(f"  - [ ] {title}"))

                elif name == "done":
                    if not title:
                        console.print("[red]ERROR[/red] Goal required")
                        console.print("[dim]Usage: mplan monthly done <goal>[/dim]")
                        sys.exit(1)

                    if plan_mgr.mark_done(title):
                        console.print(f"[green]OK[/green] Goal marked as completed")
                        console.print(escape(f"  - [x] {title}"))
                    else:
                        console.print(f"[red]ERROR[/red] Goal not found: {title}")
                        sys.exit(1)

                else:
                    plan_path = plan_mgr.create_plan()
                    console.print(f"[green]OK[/green] Monthly plan ready")
                    console.print(f"  → {display_path(plan_path)}")

                    editor = os.environ.get('EDITOR')
                    if editor:
                        subprocess.run([editor, str(plan_path)])

                    return

            return

        manager = PlanManager(base_path=memory_path)

        if action == "create":
            if not name:
                console.print("[red]ERROR[/red] Plan name required")
                console.print("[dim]Usage: mplan create <name> [options][/dim]")
                sys.exit(1)

            due = None
            if due_date:
                try:
                    due = datetime.strptime(due_date, "%Y-%m-%d").date()
                except ValueError:
                    console.print(f"[red]ERROR[/red] Invalid date format: {due_date}")
                    console.print("[dim]Use YYYY-MM-DD format[/dim]")
                    sys.exit(1)

            plan_obj = manager.create_plan(
                name=name,
                description=description,
                due_date=due,
                tags=tags
            )

            filepath = manager.save_plan(plan_obj)
            console.print(f"[green]OK[/green] Plan created:")
            console.print(f"  → {display_path(filepath)}")

        elif action == "list":
            plans = manager.list_plans()

            if not plans:
                console.print("[yellow]No plans found[/yellow]")
                console.print("[dim]Create a plan with: mplan create <name>[/dim]")
                return

            console.print("[bold cyan]Plans:[/bold cyan]\n")
            for plan_info in plans:
                completion = plan_info['completion']
                status_color = "green" if completion >= 100 else "yellow" if completion >= 50 else "red"
                console.print(f"  [{status_color}]{completion:5.1f}%[/{status_color}] {plan_info['name']}")
                console.print(f"         {plan_info['tasks']} tasks | Modified: {plan_info['modified'].strftime('%Y-%m-%d %H:%M')}")

        elif action == "show":
            if not name:
                console.print("[red]ERROR[/red] Plan name required")
                console.print("[dim]Usage: mplan show <name>[/dim]")
                sys.exit(1)

            plans = manager.list_plans()
            plan_file = None
            for plan_info in plans:
                if plan_info['name'].lower() == name.lower():
                    plan_file = plan_info['filename']
                    break

            if not plan_file:
                console.print(f"[red]ERROR[/red] Plan not found: {name}")
                sys.exit(1)

            plan_obj = manager.load_plan(plan_file)
            console.print(plan_obj.to_markdown())

        elif action == "add":
            if not name or not title:
                console.print("[red]ERROR[/red] Plan name and task title required")
                console.print("[dim]Usage: mplan add <plan-name> <task-title>[/dim]")
                sys.exit(1)

            plans = manager.list_plans()
            plan_file = None
            for plan_info in plans:
                if plan_info['name'].lower() == name.lower():
                    plan_file = plan_info['filename']
                    break

            if not plan_file:
                console.print(f"[red]ERROR[/red] Plan not found: {name}")
                sys.exit(1)

            plan_obj = manager.load_plan(plan_file)

            task = Task(title=title, tags=tags)
            plan_obj.add_task(task)

            manager.save_plan(plan_obj, filename=plan_file)
            console.print(f"[green]OK[/green] Task added to '{plan_obj.name}'")
            console.print(escape(f"  - [ ] {title}"))

        elif action == "done":
            if not name or not title:
                console.print("[red]ERROR[/red] Plan name and task title/index required")
                console.print("[dim]Usage: mplan done <plan-name> <task|index>[/dim]")
                console.print("[dim]Examples:[/dim]")
                console.print("[dim]  mplan done myplan 1          # Complete 1st task[/dim]")
                console.print("[dim]  mplan done myplan \"Write\"    # Prefix match[/dim]")
                sys.exit(1)

            plans = manager.list_plans()
            plan_file = None
            for plan_info in plans:
                if plan_info['name'].lower() == name.lower():
                    plan_file = plan_info['filename']
                    break

            if not plan_file:
                console.print(f"[red]ERROR[/red] Plan not found: {name}")
                sys.exit(1)

            plan_obj = manager.load_plan(plan_file)

            # Get incomplete tasks
            incomplete_tasks = [t for t in plan_obj.tasks if not t.completed]

            if not incomplete_tasks:
                console.print(f"[yellow]No incomplete tasks in '{plan_obj.name}'[/yellow]")
                sys.exit(1)

            # Find matching task
            target_task = None
            matched_text = None

            # Check if title is a numeric index
            if title.isdigit():
                index = int(title)
                if 1 <= index <= len(incomplete_tasks):
                    target_task = incomplete_tasks[index - 1]
                    matched_text = target_task.title
            else:
                title_lower = title.lower()

                # 1. Exact match
                for task in incomplete_tasks:
                    if task.title.lower() == title_lower:
                        target_task = task
                        matched_text = task.title
                        break

                # 2. Prefix match (if unique)
                if target_task is None:
                    prefix_matches = [t for t in incomplete_tasks if t.title.lower().startswith(title_lower)]
                    if len(prefix_matches) == 1:
                        target_task = prefix_matches[0]
                        matched_text = target_task.title

                # 3. Contains match (if unique)
                if target_task is None:
                    contains_matches = [t for t in incomplete_tasks if title_lower in t.title.lower()]
                    if len(contains_matches) == 1:
                        target_task = contains_matches[0]
                        matched_text = target_task.title
                    elif len(contains_matches) > 1:
                        # Ambiguous match
                        console.print(f"[yellow]Multiple tasks match '{title}':[/yellow]")
                        for i, t in enumerate(incomplete_tasks, 1):
                            if title_lower in t.title.lower():
                                console.print(f"  {i}. {t.title}")
                        console.print(f"\n[dim]Use index number: mplan done {name} <number>[/dim]")
                        sys.exit(1)

            if target_task is None:
                console.print(f"[red]ERROR[/red] Task not found: {title}")
                # Show available tasks
                if incomplete_tasks:
                    console.print(f"\n[dim]Available tasks:[/dim]")
                    for i, t in enumerate(incomplete_tasks, 1):
                        console.print(f"  {i}. {t.title}")
                sys.exit(1)

            target_task.mark_completed()
            manager.save_plan(plan_obj, filename=plan_file)
            console.print(f"[green]OK[/green] Task completed in '{plan_obj.name}'")
            console.print(escape(f"  - [x] {matched_text}"))

        elif action == "delete":
            if not name:
                console.print("[red]ERROR[/red] Plan name required")
                console.print("[dim]Usage: mplan delete <name>[/dim]")
                sys.exit(1)

            plans = manager.list_plans()
            plan_file = None
            for plan_info in plans:
                if plan_info['name'].lower() == name.lower():
                    plan_file = plan_info['filename']
                    break

            if not plan_file:
                console.print(f"[red]ERROR[/red] Plan not found: {name}")
                sys.exit(1)

            manager.delete_plan(plan_file)
            console.print(f"[green]OK[/green] Plan deleted: {name}")

        else:
            console.print(f"[red]ERROR[/red] Unknown action: {action}")
            console.print("[dim]Valid actions: create, list, show, add, done, delete[/dim]")
            sys.exit(1)

    except Exception as e:
        if as_json:
            json_output.fail(json_output.FAILED, f"Unexpected error: {e}")
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)
