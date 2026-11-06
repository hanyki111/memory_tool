"""Helper functions for showing document health suggestions."""

from pathlib import Path
from typing import Optional, Tuple

from rich.console import Console

from memory_tool.utils.health_checker import DocumentHealthChecker
from memory_tool.utils.suggestion_tracker import SuggestionTracker


console = Console()


def show_document_health_suggestion(
    memory_dir: Path,
    suggestion_type: str,
    context: str = "general",
    force: bool = False,
    cooldown_hours: int = 24
) -> bool:
    """Show document health suggestion if needed.

    Args:
        memory_dir: Path to .memory directory
        suggestion_type: Type of suggestion (e.g., "m-command", "module-command")
        context: Context for the suggestion (affects message)
        force: If True, always show suggestion
        cooldown_hours: Hours to wait between suggestions

    Returns:
        True if suggestion was shown
    """
    found = _pending_health_issues(memory_dir, suggestion_type, cooldown_hours, force)
    if found is None:
        return False

    level, issues = found
    if level == "critical":
        _show_critical_suggestion(issues, context)
    else:
        _show_warning_suggestion(issues, context)
    return True


def _pending_health_issues(
    memory_dir: Path, suggestion_type: str, cooldown_hours: int, force: bool
) -> Optional[Tuple[str, list]]:
    """Find the issues to suggest about now, and mark the suggestion as shown.

    Returns:
        ("critical" or "warning", issues), or None when there is nothing to say
        or the cooldown has not passed.
    """
    tracker = SuggestionTracker(memory_dir)
    key = f"document-health-{suggestion_type}"
    if not tracker.should_show_suggestion(key, cooldown_hours, force):
        return None

    checker = DocumentHealthChecker(memory_dir)
    for level, issues in (("critical", checker.get_critical_issues()), ("warning", checker.get_warning_issues())):
        if issues:
            tracker.mark_suggestion_shown(key)
            return level, issues

    return None


def document_health_notice(memory_dir: Path, command_name: str, force: bool = False) -> Optional[str]:
    """The same suggestion as plain text, for --json results.

    It follows the same cooldown as the printed suggestion and counts as shown.
    """
    found = _pending_health_issues(memory_dir, f"{command_name}-command", 24, force)
    if found is None:
        return None

    level, issues = found
    if level == "critical":
        listed = ", ".join(f"{i.module_name}/{i.file_type}.md ({i.line_count} lines)" for i in issues[:3])
        return f"Some documents are very large: {listed}. Run mcontext to see all issues."

    if len(issues) == 1:
        issue = issues[0]
        return (
            f"{issue.module_name}/{issue.file_type}.md is getting large ({issue.line_count} lines). "
            f"Consider: marchive {issue.file_type} --module {issue.module_name} --suggest"
        )
    return f"{len(issues)} documents are getting large. Run mcontext to see them."


def _show_critical_suggestion(issues, context: str):
    """Show critical issue suggestion.

    Args:
        issues: List of HealthIssue objects
        context: Context for the suggestion
    """
    console.print()
    console.print("🔴 [bold red]CRITICAL[/bold red] Document Health Alert")

    for issue in issues[:3]:  # Show top 3 critical issues
        console.print(f"   └─ [yellow]{issue.module_name}/{issue.file_type}.md[/yellow]: {issue.line_count} lines")

    console.print()
    console.print("   [dim]Immediate action recommended:[/dim]")

    if len(issues) == 1:
        issue = issues[0]
        console.print(f"   [cyan]marchive {issue.file_type} --module {issue.module_name} --interactive[/cyan]")
    else:
        console.print(f"   [cyan]mcontext[/cyan]  [dim]# View all issues[/dim]")
        console.print(f"   [cyan]marchive decisions --suggest[/cyan]  [dim]# Get recommendations[/dim]")


def _show_warning_suggestion(issues, context: str):
    """Show warning level suggestion.

    Args:
        issues: List of HealthIssue objects
        context: Context for the suggestion
    """
    console.print()
    console.print("💡 [bold yellow]Tip[/bold yellow]: ", end="")

    if len(issues) == 1:
        issue = issues[0]
        console.print(f"{issue.module_name}/{issue.file_type}.md is getting large ({issue.line_count} lines).")
        console.print(f"   [dim]Consider:[/dim] [cyan]marchive {issue.file_type} --module {issue.module_name} --suggest[/cyan]")
    else:
        console.print(f"{len(issues)} documents are getting large.")
        console.print(f"   [dim]Quick check:[/dim] [cyan]mcontext[/cyan] [dim]or[/dim] [cyan]marchive decisions --suggest[/cyan]")


def check_and_suggest_after_command(
    memory_dir: Path,
    command_name: str,
    force: bool = False
):
    """Convenience function to check and suggest after a command.

    Args:
        memory_dir: Path to .memory directory
        command_name: Name of command that was run (e.g., "m", "module")
        force: If True, always show suggestion
    """
    show_document_health_suggestion(
        memory_dir=memory_dir,
        suggestion_type=f"{command_name}-command",
        context=command_name,
        force=force,
        cooldown_hours=24
    )
