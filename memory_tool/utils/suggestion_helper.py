"""Helper functions for showing document health suggestions."""

from pathlib import Path
from typing import Optional

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
    # Check if we should show suggestion (cooldown)
    tracker = SuggestionTracker(memory_dir)
    if not tracker.should_show_suggestion(f"document-health-{suggestion_type}", cooldown_hours, force):
        return False

    # Check for health issues
    checker = DocumentHealthChecker(memory_dir)
    critical_issues = checker.get_critical_issues()
    warning_issues = checker.get_warning_issues()

    # Critical issues always show (ignoring cooldown for critical)
    if critical_issues:
        _show_critical_suggestion(critical_issues, context)
        tracker.mark_suggestion_shown(f"document-health-{suggestion_type}")
        return True

    # Warning issues respect cooldown
    if warning_issues:
        _show_warning_suggestion(warning_issues, context)
        tracker.mark_suggestion_shown(f"document-health-{suggestion_type}")
        return True

    return False


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
