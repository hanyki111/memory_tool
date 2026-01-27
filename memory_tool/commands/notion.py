"""Notion integration CLI commands."""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import typer

from memory_tool.commands.common import app, console
from memory_tool.notion.client import NotionClient, NotionError
from memory_tool.notion.models import SyncDirection
from memory_tool.utils.config import Config


@app.command(name="nm")
def notion_message(
    message: str = typer.Argument(..., help="Message to append to Notion page"),
    page_id: str = typer.Option(None, "--page", "-p", help="Target page ID (optional)"),
):
    """Append text to a Notion page (nm command)."""
    try:
        client = NotionClient()
        config = Config()
        timeline_root_page_id = config.get("notion.sync.timeline.root_page_id")

        now = datetime.now()

        if page_id:
            target_id = page_id
            client.append_text(target_id, message)
            console.print(f"[green]OK[/green] Appended to Notion page")
            console.print(f"[dim]-> Page: {target_id}[/dim]")
        else:
            if not timeline_root_page_id:
                console.print("[red]ERROR[/red] Timeline root page ID not configured. Set notion.sync.timeline.root_page_id in config.yaml")
                sys.exit(1)

            console.print("[dim]Locating daily page...[/dim]")
            target_id = client.get_or_create_daily_page(now, timeline_root_page_id)

            time_str = now.strftime("%H:%M")
            client.append_timeline_entry(target_id, time_str, message, date_obj=now)

            date_str = now.strftime("%Y-%m-%d")
            console.print(f"[green]OK[/green] Recorded to Notion at {date_str} {time_str}")
            console.print(f"[dim]-> Page: {target_id} ({date_str})[/dim]")
            console.print(f"   {message}")

    except NotionError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)


@app.command(name="nadd")
def notion_add(
    title: str = typer.Argument(..., help="Title of the new page"),
    parent_id: str = typer.Option(None, "--parent", "-p", help="Parent page ID (optional)"),
):
    """Create a new Notion page (nadd command)."""
    try:
        client = NotionClient()
        new_page = client.create_page(title, parent_id)
        console.print(f"[green]OK[/green] Created page: {title}")
        console.print(f"[dim]-> {new_page.get('url')}[/dim]")

    except NotionError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)


@app.command(name="ns")
def notion_search(
    query: str = typer.Argument(..., help="Search query"),
):
    """Search Notion pages (ns command)."""
    try:
        client = NotionClient()
        results = client.search(query)

        if not results:
            console.print("[yellow]No results found[/yellow]")
            return

        console.print(f"[cyan]Notion Search Results ({len(results)}):[/cyan]\n")
        for i, res in enumerate(results, 1):
            console.print(f"{i}. {res['title']}")
            console.print(f"   [dim]ID: {res['id']}[/dim]")
            if res.get('url'):
                console.print(f"   [dim]URL: {res['url']}[/dim]")
            console.print()

    except NotionError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)


@app.command(name="nt")
def notion_today():
    """Show today's Notion timeline (nt command)."""
    try:
        client = NotionClient()
        config = Config()
        timeline_root_page_id = config.get("notion.sync.timeline.root_page_id")

        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")

        console.print(f"[cyan]{date_str} Notion Timeline:[/cyan]\n")

        target_id = client.get_or_create_daily_page(now, timeline_root_page_id)
        content = client.get_page_content(target_id)

        if content.strip():
            console.print(content)
        else:
            console.print("[dim]No entries yet.[/dim]")

        console.print(f"\n[dim]Page ID: {target_id}[/dim]")

    except NotionError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)


@app.command(name="nw")
def notion_week():
    """Show this week's Notion timeline (nw command)."""
    try:
        client = NotionClient()
        config = Config()
        timeline_root_page_id = config.get("notion.sync.timeline.root_page_id")

        today = datetime.now()

        start_of_week = today - timedelta(days=today.weekday())

        console.print(f"[cyan]Notion Timeline (Week of {start_of_week.strftime('%Y-%m-%d')}):[/cyan]\n")

        found_any = False

        for i in range((today - start_of_week).days + 1):
            current_date = start_of_week + timedelta(days=i)
            date_str = current_date.strftime("%Y-%m-%d")

            page_id = client.get_or_create_daily_page(current_date, timeline_root_page_id)
            content = client.get_page_content(page_id)

            if content.strip():
                found_any = True
                console.print(f"[bold]{date_str}[/bold]")
                console.print(content)
                console.print("")

        if not found_any:
            console.print("[dim]No entries found for this week.[/dim]")

    except NotionError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)


@app.command(name="nsi")
def notion_search_inside(
    query: str = typer.Argument(..., help="Search query inside Daily Pages"),
):
    """Search inside Notion Daily Pages (nsi command)."""
    try:
        client = NotionClient()
        console.print(f"[dim]Searching inside Daily Pages for '{query}'...[/dim]")

        results = client.search_content(query)

        if not results:
            console.print("[yellow]No matching entries found in Daily Pages.[/yellow]")
            return

        console.print(f"[cyan]Found matches in {len(results)} pages:[/cyan]\n")

        for res in results:
            console.print(f"[bold]{res['date']}[/bold] [dim]({res['id']})[/dim]")
            for line in res['matches']:
                highlighted = line.replace(query, f"[yellow]{query}[/yellow]")
                console.print(f"  {highlighted}")
            console.print()

    except NotionError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)


@app.command(name="np")
def notion_plan(
    task: str = typer.Argument(..., help="Task to add to the plan"),
    daily: bool = typer.Option(True, "--daily", "-d", help="Add to daily plan (default)"),
    weekly: bool = typer.Option(False, "--weekly", "-w", help="Add to weekly plan"),
    monthly: bool = typer.Option(False, "--monthly", "-m", help="Add to monthly plan"),
    date_str: str = typer.Option(None, "--date", help="Target date (YYYY-MM-DD for daily, W## for weekly, MM for monthly)"),
    completed: bool = typer.Option(False, "--done", "-x", help="Mark task as completed"),
):
    """Add a task to Notion plan page (np command).

    Adds a task (checkbox) to the specified plan type on Notion.
    Default is today's daily plan.

    Examples:
        np "Write documentation"              # Add to today's daily plan
        np "Review PR" --weekly               # Add to this week's weekly plan
        np "Complete project" --monthly       # Add to this month's monthly plan
        np "Fix bug" --date 2026-01-25        # Add to specific date's daily plan
        np "Deploy feature" --weekly --date W05  # Add to specific week
        np "Task done" --done                 # Add as already completed
    """
    from datetime import date
    from memory_tool.notion.plan_sync import PlanSyncer

    try:
        syncer = PlanSyncer()

        if not syncer.enabled:
            console.print("[red]ERROR[/red] Plan sync not enabled in config.yaml")
            console.print("[dim]Enable it: notion.sync.plan.enabled: true[/dim]")
            console.print("[dim]Set root_page_id: notion.sync.plan.root_page_id: <page_id>[/dim]")
            sys.exit(1)

        # Determine plan type (priority: monthly > weekly > daily)
        if monthly:
            plan_type = "monthly"
        elif weekly:
            plan_type = "weekly"
        else:
            plan_type = "daily"

        # Parse target date
        today = date.today()
        target_date = today

        if date_str:
            if plan_type == "daily":
                # Parse YYYY-MM-DD
                try:
                    from datetime import datetime as dt
                    target_date = dt.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    console.print(f"[red]ERROR[/red] Invalid date format: {date_str}")
                    console.print("[dim]Use YYYY-MM-DD format (e.g., 2026-01-25)[/dim]")
                    sys.exit(1)
            elif plan_type == "weekly":
                # Parse W## (week number)
                if date_str.upper().startswith("W"):
                    try:
                        week_num = int(date_str[1:])
                        # Get first day of that week in current year
                        year = today.year
                        target_date = date.fromisocalendar(year, week_num, 1)
                    except (ValueError, IndexError):
                        console.print(f"[red]ERROR[/red] Invalid week format: {date_str}")
                        console.print("[dim]Use W## format (e.g., W05)[/dim]")
                        sys.exit(1)
                else:
                    console.print(f"[red]ERROR[/red] Invalid week format: {date_str}")
                    console.print("[dim]Use W## format (e.g., W05)[/dim]")
                    sys.exit(1)
            elif plan_type == "monthly":
                # Parse MM or YYYY-MM
                try:
                    if "-" in date_str:
                        from datetime import datetime as dt
                        target_date = dt.strptime(date_str + "-01", "%Y-%m-%d").date()
                    else:
                        month_num = int(date_str)
                        target_date = date(today.year, month_num, 1)
                except ValueError:
                    console.print(f"[red]ERROR[/red] Invalid month format: {date_str}")
                    console.print("[dim]Use MM or YYYY-MM format (e.g., 03 or 2026-03)[/dim]")
                    sys.exit(1)

        # Get the appropriate page
        if plan_type == "daily":
            page_id = syncer._get_daily_plan_page(target_date)
            date_display = target_date.strftime("%Y-%m-%d")
        elif plan_type == "weekly":
            page_id = syncer._get_weekly_plan_page(target_date)
            iso_cal = target_date.isocalendar()
            date_display = f"{iso_cal[0]} W{iso_cal[1]:02d}"
        else:  # monthly
            page_id = syncer._get_monthly_plan_page(target_date)
            date_display = target_date.strftime("%Y-%m")

        # Add task to Notion
        syncer._append_notion_task(page_id, task, completed)

        status = "[x]" if completed else "[ ]"
        console.print(f"[green]OK[/green] Added to {plan_type} plan ({date_display})")
        console.print(f"[dim]-> {status} {task}[/dim]")

    except NotionError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)


@app.command(name="nsync")
def notion_sync(
    module_path: str = typer.Argument(None, help="Module path to sync (optional)"),
    push: bool = typer.Option(False, "--push", "-p", help="Only push local changes to Notion"),
    pull: bool = typer.Option(False, "--pull", "-l", help="Only pull Notion changes to local"),
    force: bool = typer.Option(False, "--force", "-f", help="Force sync regardless of timestamps"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would happen without syncing"),
    status: bool = typer.Option(False, "--status", "-s", help="Show sync status"),
    discover: bool = typer.Option(False, "--discover", "-d", help="Discover and download modules from Notion"),
    cleanup: bool = typer.Option(False, "--cleanup", "-c", help="Clean up orphaned pages and invalid state"),
    archive_orphans: bool = typer.Option(False, "--archive-orphans", help="Archive orphaned/duplicate pages (use with --cleanup)"),
    execute: bool = typer.Option(False, "--execute", "-x", help="Actually execute cleanup (default is dry-run for safety)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    # Type selection flags
    module_flag: bool = typer.Option(False, "--module", "-m", help="Sync modules only"),
    timeline: bool = typer.Option(False, "--timeline", "-t", help="Sync timeline only"),
    plan: bool = typer.Option(False, "--plan", help="Sync plans only"),
    # Plan-specific options
    daily: bool = typer.Option(False, "--daily", help="Sync daily plans only (requires --plan)"),
    weekly: bool = typer.Option(False, "--weekly", help="Sync weekly plans only (requires --plan)"),
    monthly: bool = typer.Option(False, "--monthly", help="Sync monthly plans only (requires --plan)"),
    # Days option
    days: int = typer.Option(7, "--days", help="Number of days to sync for timeline/daily plans (default: 7)"),
):
    """Bidirectional sync with Notion (nsync command).

    Default: Syncs all configured types (modules + timeline + plan).
    Use flags to sync specific types only.

    Examples:
        nsync                    # Sync all types (modules + timeline + plan)
        nsync --module           # Sync modules only
        nsync --timeline         # Sync timeline only
        nsync --plan             # Sync plans only
        nsync --plan --daily     # Sync daily plans only
        nsync --plan --weekly    # Sync weekly plans only
        nsync --module --timeline  # Sync modules + timeline (no plans)

        nsync projects/my-mod    # Sync specific module
        nsync --push             # Only push local to Notion
        nsync --pull             # Only pull Notion to local
        nsync --discover         # Download modules from Notion (first time)
        nsync --dry-run          # Preview changes
        nsync --status           # Show sync status
        nsync --days 7           # Sync last 7 days of timeline/daily plans

        nsync --cleanup              # Scan for orphaned pages (dry-run)
        nsync --cleanup --execute    # Actually clean up invalid states
        nsync --cleanup --archive-orphans --execute  # Also archive orphaned pages
    """
    try:
        from memory_tool.notion.sync import ModuleSyncer, NotionSyncError

        syncer = ModuleSyncer()

        # Determine which types to sync
        # If no type flags specified, sync all
        sync_modules = not (timeline or plan) or module_flag
        sync_timeline = not (module_flag or plan) or timeline
        sync_plans = not (module_flag or timeline) or plan

        # If specific type flags are given, override defaults
        if module_flag or timeline or plan:
            sync_modules = module_flag
            sync_timeline = timeline
            sync_plans = plan

        # Determine plan type if syncing plans
        plan_type = "all"
        if plan:
            if daily and not weekly and not monthly:
                plan_type = "daily"
            elif weekly and not daily and not monthly:
                plan_type = "weekly"
            elif monthly and not daily and not weekly:
                plan_type = "monthly"

        if sync_modules and not (syncer.sync_config.module and syncer.sync_config.module.enabled):
            console.print("[yellow]Notion module sync is not enabled.[/yellow]")
            console.print("[dim]Enable it in config.yaml: notion.sync.module.enabled: true[/dim]")
            if not sync_timeline and not sync_plans:
                return

        if discover:
            if dry_run:
                console.print("[cyan]Discovering modules from Notion (dry-run)...[/cyan]\n")
            else:
                console.print("[cyan]Discovering and downloading modules from Notion...[/cyan]\n")

            result = syncer.discover_from_notion(dry_run=dry_run, verbose=verbose)

            discovered = result.get("discovered", [])
            downloaded = result.get("downloaded", [])
            errors = result.get("errors", [])

            if discovered:
                console.print(f"[green]Found {len(discovered)} module(s) in Notion:[/green]")
                for page in discovered:
                    console.print(f"  - {page['path']}")
                console.print()

                if dry_run:
                    console.print("[dim]Use --discover without --dry-run to download[/dim]")
                else:
                    console.print(f"[green]Downloaded {len(downloaded)} module(s)[/green]")
                    if errors:
                        console.print(f"[red]Errors: {len(errors)}[/red]")
                        for err in errors:
                            console.print(f"  - {err['module']}: {err['error']}")
            else:
                console.print("[yellow]No modules found in Notion under root page[/yellow]")
                console.print("[dim]Make sure root_page_id points to a page with child pages[/dim]")
            return

        if cleanup:
            # Default to dry_run=True for safety unless --execute is specified
            actual_dry_run = not execute

            if actual_dry_run:
                console.print("[cyan]Cleanup scan (dry-run)...[/cyan]\n")
                console.print("[dim]Use --cleanup --execute to actually clean up[/dim]\n")
            else:
                console.print("[cyan]Running cleanup...[/cyan]\n")

            result = syncer.cleanup(
                dry_run=actual_dry_run,
                verbose=verbose,
                archive_orphans=archive_orphans,
            )

            # Display results
            invalid_states = result.get("invalid_states", [])
            orphaned_pages = result.get("orphaned_pages", [])
            duplicate_pages = result.get("duplicate_pages", [])
            cleaned_states = result.get("cleaned_states", [])
            archived_pages = result.get("archived_pages", [])
            errors = result.get("errors", [])

            if invalid_states:
                console.print(f"[yellow]Invalid states (pointing to deleted Notion pages):[/yellow]")
                for item in invalid_states:
                    console.print(f"  - {item['path']} -> {item['page_id'][:12]}...")
                console.print()

            if orphaned_pages:
                console.print(f"[yellow]Orphaned pages (in Notion but not local):[/yellow]")
                for item in orphaned_pages:
                    console.print(f"  - {item['module']}/{item['filename']}")
                console.print()

            if duplicate_pages:
                console.print(f"[yellow]Duplicate pages (same title):[/yellow]")
                for dup in duplicate_pages:
                    console.print(f"  - {dup['module']}/{dup['title']} ({len(dup['pages'])} copies)")
                console.print()

            if not invalid_states and not orphaned_pages and not duplicate_pages:
                console.print("[green]No issues found![/green]")
            else:
                total_issues = len(invalid_states) + len(orphaned_pages) + len(duplicate_pages)
                console.print(f"[bold]Total issues: {total_issues}[/bold]")

            if not actual_dry_run:
                if cleaned_states:
                    console.print(f"\n[green]Cleaned {len(cleaned_states)} invalid state(s)[/green]")
                if archived_pages:
                    console.print(f"[green]Archived {len(archived_pages)} page(s)[/green]")

            if errors:
                console.print(f"\n[red]Errors: {len(errors)}[/red]")
                for err in errors:
                    console.print(f"  - {err}")

            if actual_dry_run and (invalid_states or orphaned_pages or duplicate_pages):
                console.print("\n[dim]To fix issues:[/dim]")
                console.print("[dim]  nsync --cleanup --execute              # Clean invalid states[/dim]")
                console.print("[dim]  nsync --cleanup --archive-orphans --execute  # Also archive orphans[/dim]")

            return

        if status:
            console.print("[bold cyan]Sync Status:[/bold cyan]\n")

            # Module status
            if sync_modules:
                console.print("[cyan]Modules:[/cyan]")
                status_info = syncer.get_status(module_path)

                last_sync = status_info.get("last_full_sync")
                if last_sync:
                    console.print(f"  Last full sync: {last_sync}")
                else:
                    console.print("  [dim]No sync history yet[/dim]")

                for mod_path, mod_status in status_info.get("modules", {}).items():
                    console.print(f"  [bold]{mod_path}[/bold]")

                    if mod_status.get("last_sync"):
                        console.print(f"    Last sync: {mod_status['last_sync']}")

                    to_push = mod_status.get("to_push", [])
                    to_pull = mod_status.get("to_pull", [])
                    in_sync = mod_status.get("in_sync", [])
                    conflicts = mod_status.get("conflicts", [])

                    if to_push:
                        console.print(f"    [green]To push:[/green] {', '.join(to_push)}")
                    if to_pull:
                        console.print(f"    [blue]To pull:[/blue] {', '.join(to_pull)}")
                    if conflicts:
                        console.print(f"    [red]Conflicts:[/red] {', '.join(conflicts)}")
                    if in_sync and verbose:
                        console.print(f"    [dim]In sync:[/dim] {', '.join(in_sync)}")
                    if not to_push and not to_pull and not conflicts:
                        console.print("    [dim]All in sync[/dim]")
                console.print()

            # Plan status
            if sync_plans:
                from memory_tool.notion.plan_sync import PlanSyncer
                plan_syncer = PlanSyncer()
                plan_status = plan_syncer.get_status()

                console.print("[cyan]Plans:[/cyan]")
                console.print(f"  Enabled: {plan_status['enabled']}")
                if plan_status.get('root_page_id'):
                    console.print(f"  Root page: {plan_status['root_page_id'][:8]}...")
                console.print(f"  Daily: {plan_status['sync_daily']}, Weekly: {plan_status['sync_weekly']}, Monthly: {plan_status['sync_monthly']}")
                console.print(f"  Status: {plan_status['message']}")
                console.print()

            return

        # Sync timeline if requested
        total_pushed = 0
        total_pulled = 0
        total_updated = 0
        total_skipped = 0
        all_errors = []

        if sync_timeline:
            from memory_tool.notion.timeline_sync import TimelineSyncer

            timeline_syncer = TimelineSyncer()

            if dry_run:
                console.print(f"[cyan]Timeline sync (dry-run) - last {days} day(s):[/cyan]\n")
            else:
                console.print(f"[cyan]Syncing timeline (last {days} day(s))...[/cyan]\n")

            result = timeline_syncer.sync(
                days=days,
                push_only=push,
                pull_only=pull,
                dry_run=dry_run,
                verbose=verbose,
            )

            total_pushed += result.get("pushed", 0)
            total_pulled += result.get("pulled", 0)
            total_skipped += result.get("skipped", 0)
            all_errors.extend(result.get("errors", []))

            if verbose:
                console.print(f"[dim]Timeline: pushed={result.get('pushed', 0)}, pulled={result.get('pulled', 0)}[/dim]")
            console.print()

        # Sync plans if requested
        if sync_plans:
            from memory_tool.notion.plan_sync import PlanSyncer

            plan_syncer = PlanSyncer()

            if plan_syncer.enabled:
                if dry_run:
                    console.print(f"[cyan]Plan sync (dry-run) - {plan_type}:[/cyan]\n")
                else:
                    console.print(f"[cyan]Syncing plans ({plan_type})...[/cyan]\n")

                result = plan_syncer.sync(
                    plan_type=plan_type,
                    days=days,
                    push_only=push,
                    pull_only=pull,
                    dry_run=dry_run,
                    verbose=verbose,
                )

                total_pushed += result.get("pushed", 0)
                total_pulled += result.get("pulled", 0)
                total_updated += result.get("updated", 0)
                total_skipped += result.get("skipped", 0)
                all_errors.extend(result.get("errors", []))

                if verbose:
                    console.print(f"[dim]Plans: pushed={result.get('pushed', 0)}, pulled={result.get('pulled', 0)}, updated={result.get('updated', 0)}[/dim]")
                console.print()
            else:
                console.print("[yellow]Plan sync not enabled[/yellow]")
                console.print("[dim]Enable it in config.yaml: notion.sync.plan.enabled: true[/dim]")
                console.print()

        # Sync modules if requested
        if sync_modules and syncer.sync_config.module and syncer.sync_config.module.enabled:
            if dry_run:
                console.print("[cyan]Module sync (dry-run):[/cyan]\n")
            else:
                console.print("[cyan]Syncing modules...[/cyan]\n")

            summary = syncer.sync(
                module_path=module_path,
                push_only=push,
                pull_only=pull,
                force=force,
                dry_run=dry_run,
                verbose=verbose,
            )

            for result in summary.results:
                if result.action.direction == SyncDirection.SKIP:
                    if verbose:
                        console.print(f"[dim]SKIP[/dim]  {result.action.module_path}/{result.action.file_path}")
                    continue

                if result.success:
                    if result.action.direction == SyncDirection.PUSH:
                        console.print(f"[green]PUSH[/green] {result.action.module_path}/{result.action.file_path} -> Notion")
                    elif result.action.direction == SyncDirection.PULL:
                        console.print(f"[blue]PULL[/blue] {result.action.module_path}/{result.action.file_path} <- Notion")
                else:
                    console.print(f"[red]FAIL[/red] {result.action.module_path}/{result.action.file_path}: {result.message}")

            total_pushed += summary.pushed
            total_pulled += summary.pulled
            total_skipped += summary.skipped
            console.print()

        # Print summary
        console.print("[bold cyan]Summary:[/bold cyan]")
        if total_pushed:
            console.print(f"  [green]Pushed:[/green] {total_pushed}")
        if total_pulled:
            console.print(f"  [blue]Pulled:[/blue] {total_pulled}")
        if total_updated:
            console.print(f"  [yellow]Updated:[/yellow] {total_updated}")
        if total_skipped and verbose:
            console.print(f"  [dim]Skipped:[/dim] {total_skipped}")
        if all_errors:
            console.print(f"  [red]Errors:[/red] {len(all_errors)}")
            for err in all_errors:
                console.print(f"    - {err}")
        if not total_pushed and not total_pulled and not total_updated and not all_errors:
            console.print("  [dim]No changes to sync[/dim]")

    except NotionError as e:
        console.print(f"[red]Notion Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@app.command(name="nwatch")
def notion_watch(
    debounce: float = typer.Option(2.0, "--debounce", "-d", help="Debounce time in seconds"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would sync without syncing"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Less verbose output"),
    modules_only: bool = typer.Option(False, "--modules-only", "-m", help="Watch only modules/ directory"),
    timeline_only: bool = typer.Option(False, "--timeline-only", "-t", help="Watch only timeline/ directory"),
    plans_only: bool = typer.Option(False, "--plans-only", "-p", help="Watch only plans/ directory"),
    no_plans: bool = typer.Option(False, "--no-plans", help="Exclude plans/ from watching"),
    bidirectional: bool = typer.Option(False, "--bidirectional", "-b", help="Enable Notion -> Local sync (polling)"),
    poll_interval: int = typer.Option(120, "--poll-interval", "-i", help="Notion polling interval in seconds (default: 120)"),
):
    """Watch local modules, timeline, and plans, auto-sync with Notion on changes.

    Monitors .memory/ subdirectories for file changes:
    - modules/ changes -> triggers module sync (nsync)
    - timeline/ changes -> syncs new entries to Notion daily pages
    - plans/ changes -> syncs plans to Notion

    With --bidirectional: Also polls Notion for changes and pulls to local.

    Uses debouncing to batch rapid changes.

    Examples:
        nwatch                      # Watch all (modules + timeline + plans)
        nwatch --bidirectional      # Enable Notion -> Local sync too
        nwatch -b -i 60             # Bidirectional with 60s polling interval
        nwatch --modules-only       # Watch only modules/
        nwatch --timeline-only      # Watch only timeline/
        nwatch --plans-only         # Watch only plans/
        nwatch --no-plans           # Watch modules + timeline (exclude plans)
        nwatch --debounce 5         # Wait 5 seconds before syncing
        nwatch --dry-run            # Show what would sync (no actual sync)
        nwatch --quiet              # Less verbose output

    Requirements:
        pip install memory-tool[watch]
    """
    try:
        from memory_tool.notion.watcher import NotionWatcher, check_watchdog_available

        if not check_watchdog_available():
            console.print("[red]Error:[/red] watchdog is required for file watching.")
            console.print("[dim]Install with: pip install memory-tool[watch][/dim]")
            raise typer.Exit(1)

        verbose = not quiet

        # Determine what to watch
        if modules_only:
            watch_modules = True
            watch_timeline = False
            watch_plans = False
        elif timeline_only:
            watch_modules = False
            watch_timeline = True
            watch_plans = False
        elif plans_only:
            watch_modules = False
            watch_timeline = False
            watch_plans = True
        else:
            # Default: watch all
            watch_modules = True
            watch_timeline = True
            watch_plans = not no_plans

        watcher = NotionWatcher(
            debounce_seconds=debounce,
            verbose=verbose,
            dry_run=dry_run,
            watch_modules=watch_modules,
            watch_timeline=watch_timeline,
            watch_plans=watch_plans,
            bidirectional=bidirectional,
            poll_interval=poll_interval,
        )

        console.print("[cyan]Starting Notion sync watcher...[/cyan]\n")
        watcher.run_forever()

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except ImportError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
