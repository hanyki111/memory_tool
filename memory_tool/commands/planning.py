"""Planning-related CLI commands (plan, summary)."""

import sys
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional

import typer

from memory_tool.commands.common import app, console, opt_str, arg_str, resolve_module_name
from memory_tool.llm.client import LLMClient
from memory_tool.summary import TimelineSummarizer, ModuleSummarizer


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


@app.command()
def summary(
    scope: str = typer.Argument("today", help="Scope: 'today', 'week', date (YYYY-MM-DD), or date range (YYYY-MM-DD:YYYY-MM-DD)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path (optional)"),
    module_name: Optional[str] = typer.Option(None, "--module", "-m", help="Summarize specific module"),
    decisions: bool = typer.Option(False, "--decisions", help="Summarize decisions.md only (requires --module)"),
    lang: Optional[str] = typer.Option(None, "--lang", "-l", help="Output language: 'ko' (Korean), 'en' (English), 'auto' (detect)"),
    force: bool = typer.Option(False, "--force", "-f", help="Force regeneration, bypassing cache"),
):
    """Summarize timeline or module using LLM (msummary command)."""
    scope = arg_str(scope)
    output = opt_str(output)
    module_name = opt_str(module_name)
    lang = opt_str(lang)

    if not LLMClient.check_availability():
        console.print("[red]ERROR[/red] LLM not configured")
        console.print("[dim]Set ANTHROPIC_API_KEY environment variable or add 'llm.api_key' to config.yaml[/dim]")
        sys.exit(1)

    if decisions and not module_name:
        console.print("[red]ERROR[/red] --decisions flag requires --module to be specified")
        console.print("[dim]Example: msummary --module project-management --decisions[/dim]")
        sys.exit(1)

    try:
        llm_client = LLMClient()

        if module_name:
            resolved_module = resolve_module_name(module_name)

            if decisions:
                if force:
                    console.print(f"[cyan]Summarizing decisions.md from '{resolved_module}' (force regeneration)...[/cyan]")
                else:
                    console.print(f"[cyan]Summarizing decisions.md from '{resolved_module}'...[/cyan]")

                module_path = Path.cwd() / ".memory" / "modules" / resolved_module
                decisions_file = module_path / "decisions.md"

                if not decisions_file.exists():
                    console.print(f"[red]ERROR[/red] decisions.md not found in module '{resolved_module}'")
                    sys.exit(1)

                decisions_content = decisions_file.read_text(encoding="utf-8")

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
                    cache_dir = Path.cwd() / ".memory" / "summaries"
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
                module_path = Path.cwd() / ".memory" / "modules" / resolved_module

                summary_text = summarizer.summarize_module(
                    module_path, force=force, output_language=lang
                )

            console.print("\n" + "="*80)
            console.print(summary_text)
            console.print("="*80)

            if output:
                output_path = Path(output)
                output_path.write_text(summary_text, encoding="utf-8")
                console.print(f"\n[green]OK[/green] Summary saved to: {output}")

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
                console.print(f"[red]ERROR[/red] Invalid date range format: {scope}")
                console.print("[dim]Use: YYYY-MM-DD:YYYY-MM-DD (e.g., 2025-11-01:2025-11-14)[/dim]")
                sys.exit(1)

        else:
            try:
                target_date = datetime.strptime(scope, "%Y-%m-%d").date()
                console.print(f"[cyan]Summarizing timeline for {target_date}{force_msg}...[/cyan]")
                summary_text = summarizer.summarize_date(target_date, output_language=lang, force=force)

            except ValueError:
                console.print(f"[red]ERROR[/red] Invalid date format: {scope}")
                console.print("[dim]Use YYYY-MM-DD format (e.g., 2025-11-14)[/dim]")
                sys.exit(1)

        console.print("\n" + "="*80)
        console.print(summary_text)
        console.print("="*80)

        if output:
            output_path = Path(output)
            output_path.write_text(summary_text, encoding="utf-8")
            console.print(f"\n[green]OK[/green] Summary saved to: {output}")

    except FileNotFoundError as e:
        console.print(f"[yellow]![/yellow] {e}")
        sys.exit(1)

    except ValueError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@app.command()
def plan(
    action: str = typer.Argument(..., help="Action: create, list, show, add, done, delete, daily, weekly, monthly, module"),
    name: str = typer.Argument(None, help="Plan name or sub-action (add/done/show)"),
    title: str = typer.Argument(None, help="Task title (for 'add' action)"),
    description: str = typer.Option("", "--desc", "-d", help="Plan description"),
    due_date: Optional[str] = typer.Option(None, "--due", help="Due date (YYYY-MM-DD)"),
    tags: List[str] = typer.Option([], "--tag", "-t", help="Tags"),
    section: str = typer.Option("sprint", "--section", "-s", help="Module plan section: sprint, backlog, debt"),
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
        module: Module plan (sprint/backlog/debt)

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
        mplan daily carryover    # Move yesterday's incomplete to today

        mplan weekly             # Show this week's plan
        mplan weekly lastweek    # Show last week's plan
        mplan weekly show W03    # Show specific week
        mplan weekly add "Goal"  # Add goal to this week
        mplan weekly carryover   # Move last week's incomplete to this week

        mplan monthly            # Show this month's plan

        mplan module core-system              # Show module plan
        mplan module core-system add "Task"   # Add to sprint (default)
        mplan module core-system add "Task" --section backlog
        mplan module core-system done "Task"
    """
    due_date = opt_str(due_date)

    try:
        from memory_tool.planner import (
            PlanManager, Task, TaskStatus,
            DailyPlan, WeeklyPlan, MonthlyPlan, ModulePlan
        )
        import subprocess
        import os

        memory_path = Path.cwd() / ".memory"

        if not memory_path.exists():
            console.print("[red]ERROR[/red] .memory/ not found. Run 'minit' first.")
            sys.exit(1)

        if action in ["daily", "weekly", "monthly", "module"]:
            if action == "daily":
                plan_mgr = DailyPlan(base_path=memory_path)

                if name is None or name == "show":
                    # mplan daily OR mplan daily show [date]
                    target_date = None
                    if title:
                        # mplan daily show 2026-01-15 OR mplan daily show yesterday
                        target_date = plan_mgr.parse_date_keyword(title)
                        if target_date is None:
                            console.print(f"[red]ERROR[/red] Invalid date: {title}")
                            console.print("[dim]Use YYYY-MM-DD or 'yesterday'[/dim]")
                            sys.exit(1)
                    content = plan_mgr.show_plan(target_date)
                    console.print(content)

                elif name == "yesterday":
                    # mplan daily yesterday
                    from datetime import timedelta
                    yesterday = date.today() - timedelta(days=1)
                    content = plan_mgr.show_plan(yesterday)
                    console.print(content)

                elif name == "add":
                    if not title:
                        console.print("[red]ERROR[/red] Task title required")
                        console.print("[dim]Usage: mplan daily add <task>[/dim]")
                        sys.exit(1)

                    plan_mgr.add_task(title)
                    console.print(f"[green]OK[/green] Task added to today's plan")
                    console.print(f"  - [ ] {title}")

                elif name == "done":
                    if not title:
                        console.print("[red]ERROR[/red] Task title required")
                        console.print("[dim]Usage: mplan daily done <task>[/dim]")
                        sys.exit(1)

                    if plan_mgr.mark_done(title):
                        console.print(f"[green]OK[/green] Task marked as completed")
                        console.print(f"  - [x] {title}")
                    else:
                        console.print(f"[red]ERROR[/red] Task not found: {title}")
                        sys.exit(1)

                elif name == "carryover":
                    # mplan daily carryover
                    from datetime import timedelta
                    yesterday = date.today() - timedelta(days=1)
                    incomplete = plan_mgr.get_incomplete_tasks(yesterday)

                    if not incomplete:
                        console.print(f"[yellow]No incomplete tasks from yesterday ({yesterday.strftime('%Y-%m-%d')})[/yellow]")
                        return

                    console.print(f"[cyan]Yesterday's incomplete tasks ({yesterday.strftime('%Y-%m-%d')}):[/cyan]")
                    selected = _interactive_carryover(incomplete, "task")

                    if not selected:
                        console.print("[dim]No tasks selected[/dim]")
                        return

                    count = plan_mgr.carryover_tasks(selected, yesterday, date.today())
                    console.print(f"\n[green]OK[/green] Carried over {count} task(s) to today's plan")
                    for task in selected:
                        console.print(f"  - {task}")

                else:
                    # Try to parse name as date keyword (mplan daily 2026-01-15)
                    target_date = plan_mgr.parse_date_keyword(name)
                    if target_date:
                        content = plan_mgr.show_plan(target_date)
                        console.print(content)
                        return

                    # Default: create plan
                    plan_path = plan_mgr.create_plan()
                    console.print(f"[green]OK[/green] Daily plan ready")
                    console.print(f"  → {plan_path.relative_to(Path.cwd())}")

                    editor = os.environ.get('EDITOR')
                    if editor:
                        subprocess.run([editor, str(plan_path)])

                    return

            elif action == "weekly":
                plan_mgr = WeeklyPlan(base_path=memory_path)

                if name is None or name == "show":
                    # mplan weekly OR mplan weekly show [W03|lastweek]
                    week_id = title if title else None
                    content = plan_mgr.show_plan(week_id)
                    console.print(content)

                elif name == "lastweek":
                    # mplan weekly lastweek
                    content = plan_mgr.show_plan("lastweek")
                    console.print(content)

                elif name == "add":
                    if not title:
                        console.print("[red]ERROR[/red] Goal required")
                        console.print("[dim]Usage: mplan weekly add <goal>[/dim]")
                        sys.exit(1)

                    plan_mgr.add_goal(title)
                    console.print(f"[green]OK[/green] Goal added to this week's plan")
                    console.print(f"  - [ ] {title}")

                elif name == "done":
                    if not title:
                        console.print("[red]ERROR[/red] Goal required")
                        console.print("[dim]Usage: mplan weekly done <goal>[/dim]")
                        sys.exit(1)

                    if plan_mgr.mark_done(title):
                        console.print(f"[green]OK[/green] Goal marked as completed")
                        console.print(f"  - [x] {title}")
                    else:
                        console.print(f"[red]ERROR[/red] Goal not found: {title}")
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
                        console.print(content)
                        return

                    plan_path = plan_mgr.create_plan()
                    console.print(f"[green]OK[/green] Weekly plan ready")
                    console.print(f"  → {plan_path.relative_to(Path.cwd())}")

                    editor = os.environ.get('EDITOR')
                    if editor:
                        subprocess.run([editor, str(plan_path)])

                    return

            elif action == "monthly":
                plan_mgr = MonthlyPlan(base_path=memory_path)

                if name is None or name == "show":
                    month_id = title if title else None
                    content = plan_mgr.show_plan(month_id)
                    console.print(content)

                elif name == "add":
                    if not title:
                        console.print("[red]ERROR[/red] Goal required")
                        console.print("[dim]Usage: mplan monthly add <goal>[/dim]")
                        sys.exit(1)

                    plan_mgr.add_goal(title)
                    console.print(f"[green]OK[/green] Goal added to this month's plan")
                    console.print(f"  - [ ] {title}")

                elif name == "done":
                    if not title:
                        console.print("[red]ERROR[/red] Goal required")
                        console.print("[dim]Usage: mplan monthly done <goal>[/dim]")
                        sys.exit(1)

                    if plan_mgr.mark_done(title):
                        console.print(f"[green]OK[/green] Goal marked as completed")
                        console.print(f"  - [x] {title}")
                    else:
                        console.print(f"[red]ERROR[/red] Goal not found: {title}")
                        sys.exit(1)

                else:
                    plan_path = plan_mgr.create_plan()
                    console.print(f"[green]OK[/green] Monthly plan ready")
                    console.print(f"  → {plan_path.relative_to(Path.cwd())}")

                    editor = os.environ.get('EDITOR')
                    if editor:
                        subprocess.run([editor, str(plan_path)])

                    return

            elif action == "module":
                if not name:
                    console.print("[red]ERROR[/red] Module name required")
                    console.print("[dim]Usage: mplan module <module-name> [add|done|show][/dim]")
                    sys.exit(1)

                plan_mgr = ModulePlan(base_path=memory_path)

                sub_action = title if title in ["add", "done", "show"] else "show"

                if sub_action == "show" or title is None:
                    content = plan_mgr.show_plan(name)
                    console.print(content)

                elif sub_action == "add":
                    if not description:
                        console.print("[red]ERROR[/red] Task required")
                        console.print("[dim]Usage: mplan module <module> add --desc <task> [--section sprint|backlog|debt][/dim]")
                        sys.exit(1)

                    if plan_mgr.add_task(name, section, description):
                        console.print(f"[green]OK[/green] Task added to {name}/{section}")
                        console.print(f"  - [ ] {description}")
                    else:
                        console.print(f"[red]ERROR[/red] Failed to add task")
                        sys.exit(1)

                elif sub_action == "done":
                    if not description:
                        console.print("[red]ERROR[/red] Task required")
                        console.print("[dim]Usage: mplan module <module> done --desc <task> [--section sprint|backlog|debt][/dim]")
                        sys.exit(1)

                    if plan_mgr.mark_done(name, section, description):
                        console.print(f"[green]OK[/green] Task marked as completed")
                        console.print(f"  - [x] {description}")
                    else:
                        console.print(f"[red]ERROR[/red] Task not found: {description}")
                        sys.exit(1)

                else:
                    plan_path = plan_mgr.create_plan(name)
                    console.print(f"[green]OK[/green] Module plan ready: {name}")
                    console.print(f"  → {plan_path.relative_to(Path.cwd())}")

                    editor = os.environ.get('EDITOR')
                    if editor:
                        subprocess.run([editor, str(plan_path)])

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
            console.print(f"  → {filepath.relative_to(Path.cwd())}")

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
            console.print(f"  - [ ] {title}")

        elif action == "done":
            if not name or not title:
                console.print("[red]ERROR[/red] Plan name and task title required")
                console.print("[dim]Usage: mplan done <plan-name> <task-title>[/dim]")
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

            task_found = False
            for task in plan_obj.tasks:
                if task.title.lower() == title.lower():
                    task.mark_completed()
                    task_found = True
                    break

            if not task_found:
                console.print(f"[red]ERROR[/red] Task not found: {title}")
                sys.exit(1)

            manager.save_plan(plan_obj, filename=plan_file)
            console.print(f"[green]OK[/green] Task completed in '{plan_obj.name}'")
            console.print(f"  - [x] {title}")

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
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)
