"""System-related CLI commands (init, status, alias, completion, tutorial, hooks, migrate)."""

import sys
from pathlib import Path
from typing import Optional

import typer

from memory_tool.commands.common import app, console, opt_str, resolve_module_name


@app.command()
def init(
    path: str = typer.Argument(".", help="Path to initialize .memory/ structure"),
    force: bool = typer.Option(False, "--force", "-f", help="Force reinitialize"),
    kb: Optional[str] = typer.Option(None, "--kb", help="Path to knowledge base"),
    update_docs: bool = typer.Option(False, "--update-docs", help="Update documentation templates in existing project"),
    update_all: bool = typer.Option(False, "--update-all", help="Update all templates including guidelines (backs up existing)"),
):
    """Initialize .memory/ structure (minit command).

    Use --update-docs to update documentation templates in an existing project.
    Use --update-all to also update .claude/guidelines.md (creates backup).
    """
    from memory_tool.core.init import (
        MemoryInitializer,
        InitializationError,
        AlreadyInitializedError,
    )

    target_path = Path(path).resolve()

    if not target_path.exists():
        console.print(f"[red]ERROR[/red] Path does not exist: {target_path}")
        sys.exit(1)

    if not target_path.is_dir():
        console.print(f"[red]ERROR[/red] Path is not a directory: {target_path}")
        sys.exit(1)

    initializer = MemoryInitializer(target_path)

    try:
        # Handle --update-docs or --update-all mode
        if update_docs or update_all:
            result = initializer.update_docs(include_guidelines=update_all)

            if result["files"]:
                console.print(f"[green]OK[/green] Updated documentation templates")
                for f in result["files"]:
                    console.print(f"  [dim]Updated: {f.relative_to(target_path)}[/dim]")

            if result.get("backed_up"):
                for f in result["backed_up"]:
                    console.print(f"  [yellow]Backup: {f.relative_to(target_path)}[/yellow]")

            return

        # Normal initialization
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

        # Count plans and get progress
        plans_path = memory_path / "plans"
        daily_plans = 0
        weekly_plans = 0
        monthly_plans = 0
        today_progress = None
        week_progress = None

        if plans_path.exists():
            # Count daily plans
            daily_path = plans_path / "daily"
            if daily_path.exists():
                daily_plans = len(list(daily_path.rglob("*.md")))
                # Get today's progress
                from datetime import date
                import re
                today = date.today()
                today_plan = daily_path / today.strftime("%Y-%m") / f"{today.strftime('%d')}.md"
                if today_plan.exists():
                    content = today_plan.read_text(encoding='utf-8')
                    total = len(re.findall(r'- \[[ x]\]', content))
                    completed = len(re.findall(r'- \[x\]', content))
                    if total > 0:
                        today_progress = (completed, total)

            # Count weekly plans
            weekly_path = plans_path / "weekly"
            if weekly_path.exists():
                weekly_plans = len(list(weekly_path.rglob("*.md")))
                # Get this week's progress
                from datetime import date
                import re
                today = date.today()
                iso_cal = today.isocalendar()
                week_num = iso_cal[1]
                week_plan = weekly_path / str(today.year) / f"W{week_num:02d}.md"
                if week_plan.exists():
                    content = week_plan.read_text(encoding='utf-8')
                    total = len(re.findall(r'- \[[ x]\]', content))
                    completed = len(re.findall(r'- \[x\]', content))
                    if total > 0:
                        week_progress = (completed, total)

            # Count monthly plans
            monthly_path = plans_path / "monthly"
            if monthly_path.exists():
                monthly_plans = len(list(monthly_path.rglob("*.md")))

        console.print(f"[bold]Plans:[/bold]")
        console.print(f"  Daily plans: {daily_plans}")
        if today_progress:
            completed, total = today_progress
            percentage = (completed / total * 100)
            console.print(f"  Today's progress: {completed}/{total} ({percentage:.0f}%)")
        console.print(f"  Weekly plans: {weekly_plans}")
        if week_progress:
            completed, total = week_progress
            percentage = (completed / total * 100)
            console.print(f"  This week's progress: {completed}/{total} ({percentage:.0f}%)")
        console.print(f"  Monthly plans: {monthly_plans}")
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
    directory: Optional[str] = typer.Option(None, "--dir", "-d", help="Installation directory (for script files)"),
    powershell: bool = typer.Option(False, "--powershell", "--ps", help="Use PowerShell profile (Windows)"),
    bash: bool = typer.Option(False, "--bash", help="Use Bash profile (~/.bashrc)"),
    zsh: bool = typer.Option(False, "--zsh", help="Use Zsh profile (~/.zshrc)"),
):
    """Manage command aliases (malias command).

    Examples:
        malias install --powershell    # Windows PowerShell
        malias install --bash          # Linux/macOS Bash
        malias install --zsh           # Linux/macOS Zsh
        malias list                    # Show all aliases
    """
    from memory_tool.utils.alias import AliasManager, AliasError

    # Safely convert Typer OptionInfo to str/None
    directory = opt_str(directory)

    manager = AliasManager()

    # Parse directory
    install_dir = Path(directory) if directory else None

    # Determine shell type
    shell_type = None
    if bash:
        shell_type = "bash"
    elif zsh:
        shell_type = "zsh"

    try:
        if action == "install":
            if bash or zsh:
                # Install to Unix shell profile (Bash/Zsh)
                shell_name = "Bash" if bash else "Zsh"
                if name:
                    profile_path, was_added = manager.install_shell_alias(name, shell=shell_type)
                    if was_added:
                        console.print(f"[green]OK[/green] Installed alias to {shell_name} profile: {name}")
                    else:
                        console.print(f"[yellow]![/yellow] Alias already exists: {name}")
                    console.print(f"[dim]-> {profile_path}[/dim]")
                else:
                    installed = manager.install_all_shell(shell=shell_type)
                    added_count = sum(1 for was_added in installed.values() if was_added)
                    console.print(f"[green]OK[/green] Installed {added_count} aliases to {shell_name} profile")

                    profile_path = manager.get_shell_profile_path(shell_type)
                    console.print(f"[dim]Profile: {profile_path}[/dim]\n")

                    for alias_name, was_added in installed.items():
                        command, description = manager.ALIASES[alias_name]
                        if was_added:
                            console.print(f"[green]  + {alias_name:10}[/green] -> {command:10} ({description})")
                        else:
                            console.print(f"[dim]  = {alias_name:10} -> {command:10} (already exists)[/dim]")

                # Show reload instructions
                profile_file = "~/.bashrc" if bash else "~/.zshrc"
                console.print(f"\n[cyan]To use aliases, reload your shell profile:[/cyan]")
                console.print(f"[dim]  source {profile_file}[/dim]")
                console.print("[dim]Or restart your terminal[/dim]")

            elif powershell:
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
            elif bash or zsh:
                # Uninstall from Unix shell profile (Bash/Zsh)
                shell_name = "Bash" if bash else "Zsh"
                if name:
                    profile_path, was_removed = manager.uninstall_shell_alias(name, shell=shell_type)
                    if was_removed:
                        console.print(f"[green]OK[/green] Uninstalled alias from {shell_name} profile: {name}")
                        if profile_path:
                            console.print(f"[dim]-> {profile_path}[/dim]")
                    else:
                        console.print(f"[yellow]![/yellow] Alias not found: {name}")
                else:
                    removed = manager.uninstall_all_shell(shell=shell_type)
                    if removed:
                        console.print(f"[green]OK[/green] Uninstalled {len(removed)} aliases from {shell_name} profile")
                        for alias_name in removed:
                            console.print(f"[dim]  {alias_name}[/dim]")
                    else:
                        console.print("[yellow]![/yellow] No aliases found to uninstall")

                # Show reload instructions
                profile_file = "~/.bashrc" if bash else "~/.zshrc"
                console.print(f"\n[cyan]To apply changes, reload your shell profile:[/cyan]")
                console.print(f"[dim]  source {profile_file}[/dim]")
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
            elif bash or zsh:
                # List Unix shell profile aliases (Bash/Zsh)
                shell_name = "Bash" if bash else "Zsh"
                shell_status_map = manager.list_shell_installed(shell=shell_type)
                shell_profile = manager.get_shell_profile_path(shell_type)

                if shell_profile:
                    console.print(f"[cyan]{shell_name} Profile:[/cyan] {shell_profile}\n")

                    for alias_name, installed in shell_status_map.items():
                        command, description = manager.ALIASES[alias_name]
                        status_icon = "[green]OK[/green]" if installed else "[dim]--[/dim]"
                        console.print(f"  {status_icon} {alias_name:10} -> {command:10} ({description})")

                    console.print("")
                    if any(shell_status_map.values()):
                        console.print(f"[green]OK[/green] Aliases are configured in {shell_name} profile")
                    else:
                        console.print(f"[yellow]![/yellow] No aliases found in {shell_name} profile")
                        console.print(f"[dim]Run 'malias install --{shell_type}' to install[/dim]")
                else:
                    console.print(f"[red]ERROR[/red] {shell_name} profile not found (not on Unix?)")
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


@app.command()
def completion(
    action: str = typer.Argument(..., help="Action: generate, install, uninstall, status"),
    shell: str = typer.Argument(None, help="Shell: bash, zsh, powershell"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    to_profile: bool = typer.Option(False, "--profile", help="Append to shell profile"),
):
    """Manage shell completion scripts (mcompletion command).

    Actions:
        generate: Generate completion script for shell
        install: Install completion script to default location
        uninstall: Remove completion script
        status: Check installation status

    Examples:
        mcompletion generate bash          # Print bash completion
        mcompletion install bash           # Install bash completion
        mcompletion install zsh --profile  # Add to .zshrc
        mcompletion status bash            # Check if installed
        mcompletion uninstall bash         # Remove completion
    """
    try:
        from memory_tool.utils.completion import CompletionManager

        manager = CompletionManager()

        # Action: generate
        if action == "generate":
            if not shell:
                console.print("[red]ERROR[/red] Shell type required")
                console.print("[dim]Usage: mcompletion generate <shell>[/dim]")
                sys.exit(1)

            try:
                script = manager.generate_completion(shell)
                console.print(script)
            except Exception as e:
                console.print(f"[red]ERROR[/red] {e}")
                sys.exit(1)

        # Action: install
        elif action == "install":
            if not shell:
                console.print("[red]ERROR[/red] Shell type required")
                console.print("[dim]Usage: mcompletion install <shell>[/dim]")
                sys.exit(1)

            try:
                output_path = Path(output) if output else None
                installed_path = manager.install_completion(
                    shell,
                    output_file=output_path,
                    append_to_profile=to_profile
                )

                console.print(f"[green]OK[/green] Completion installed:")
                console.print(f"  -> {installed_path}")

                if to_profile:
                    console.print("\n[cyan]Reload your shell or run:[/cyan]")
                    console.print(f"  source {installed_path}")
                else:
                    console.print("\n[cyan]Reload your shell for changes to take effect[/cyan]")

            except Exception as e:
                console.print(f"[red]ERROR[/red] {e}")
                sys.exit(1)

        # Action: uninstall
        elif action == "uninstall":
            if not shell:
                console.print("[red]ERROR[/red] Shell type required")
                console.print("[dim]Usage: mcompletion uninstall <shell>[/dim]")
                sys.exit(1)

            try:
                removed = manager.uninstall_completion(shell)

                if removed:
                    console.print(f"[green]OK[/green] Completion removed for {shell}")
                    console.print("[cyan]Reload your shell for changes to take effect[/cyan]")
                else:
                    console.print(f"[yellow]No completion found for {shell}[/yellow]")

            except Exception as e:
                console.print(f"[red]ERROR[/red] {e}")
                sys.exit(1)

        # Action: status
        elif action == "status":
            if not shell:
                # Check all shells
                shells = ["bash", "zsh", "powershell"]
                console.print("[bold cyan]Completion Status:[/bold cyan]\n")

                for sh in shells:
                    installed = manager.check_installation(sh)
                    status_icon = "[green]OK[/green]" if installed else "[dim]--[/dim]"
                    status_text = "Installed" if installed else "Not installed"
                    console.print(f"  {status_icon} {sh:12} {status_text}")

            else:
                # Check specific shell
                installed = manager.check_installation(shell)

                if installed:
                    console.print(f"[green]OK[/green] Completion installed for {shell}")
                else:
                    console.print(f"[yellow]Completion not installed for {shell}[/yellow]")
                    console.print("\n[cyan]To install:[/cyan]")
                    console.print(f"  mcompletion install {shell}")

        else:
            console.print(f"[red]ERROR[/red] Unknown action: {action}")
            console.print("[dim]Valid actions: generate, install, uninstall, status[/dim]")
            sys.exit(1)

    except ImportError:
        console.print("[red]ERROR[/red] Completion module not available")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@app.command()
def tutorial(
    lesson: str = typer.Argument(None, help="Lesson ID to show (optional)"),
    list_lessons: bool = typer.Option(False, "--list", "-l", help="List available lessons"),
):
    """Interactive tutorial for memory_tool (mtutorial command).

    Learn how to use memory_tool commands with step-by-step tutorials.

    Examples:
        mtutorial                  # Show interactive menu
        mtutorial basics           # Show basics lesson
        mtutorial --list           # List all lessons
    """
    try:
        from memory_tool.utils.tutorial import Tutorial

        tut = Tutorial()

        if list_lessons:
            tut.list_lessons()
        else:
            tut.run(lesson_id=lesson)

    except KeyboardInterrupt:
        console.print("\n[yellow]Tutorial closed[/yellow]")
    except Exception as e:
        console.print(f"[red]ERROR[/red] Tutorial failed: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@app.command()
def hooks(
    action: str = typer.Argument(..., help="Action: install, uninstall, list"),
    hook_type: str = typer.Argument(None, help="Hook type: pre-commit, post-checkout, document-health"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing hook"),
):
    """Manage git hooks for memory_tool.

    Examples:
        mhooks install document-health  # Install document health check hook
        mhooks install pre-commit       # Install graph rebuild hook
        mhooks install post-checkout    # Install post-checkout hook
        mhooks list                     # List installed hooks
        mhooks uninstall pre-commit     # Remove hook
    """
    try:
        from memory_tool.utils.git_hooks import GitHookManager, GitHookError

        manager = GitHookManager()

        if action.lower() == "install":
            if not hook_type:
                console.print("[red]ERROR[/red] Hook type required for install")
                console.print("[dim]Usage: hooks install <document-health|pre-commit|post-checkout>[/dim]")
                sys.exit(1)

            # Check if git repo
            if not manager.is_git_repo():
                console.print("[red]ERROR[/red] Not a git repository")
                console.print("[dim]Run 'git init' first or navigate to a git repository[/dim]")
                sys.exit(1)

            console.print(f"[cyan]Installing {hook_type} hook...[/cyan]")

            try:
                if hook_type == "document-health":
                    hook_path = manager.install_document_health_hook(force=force)
                    hook_description = "check document health before commits"
                elif hook_type == "pre-commit":
                    hook_path = manager.install_pre_commit_hook(force=force)
                    hook_description = "rebuild connection graph before commits"
                elif hook_type == "post-checkout":
                    hook_path = manager.install_post_checkout_hook(force=force)
                    hook_description = "rebuild connection graph after checkout"
                else:
                    console.print(f"[red]ERROR[/red] Unknown hook type: {hook_type}")
                    console.print("Valid types: document-health, pre-commit, post-checkout")
                    sys.exit(1)

                console.print(f"\n[green]OK[/green] Hook installed: {hook_path.relative_to(Path.cwd())}")
                console.print(f"\n[dim]This hook will automatically {hook_description}.")
                console.print("You can disable it by removing the hook file.[/dim]")

            except GitHookError as e:
                console.print(f"[red]ERROR[/red] {e}")
                sys.exit(1)

        elif action.lower() == "uninstall":
            if not hook_type:
                console.print("[red]ERROR[/red] Hook type required for uninstall")
                console.print("[dim]Usage: hooks uninstall <pre-commit|post-checkout>[/dim]")
                sys.exit(1)

            if not manager.is_git_repo():
                console.print("[red]ERROR[/red] Not a git repository")
                sys.exit(1)

            console.print(f"[cyan]Uninstalling {hook_type} hook...[/cyan]")

            try:
                removed = manager.uninstall_hook(hook_type)

                if removed:
                    console.print(f"\n[green]OK[/green] Hook removed")
                else:
                    console.print(f"\n[yellow]![/yellow] Hook not found: {hook_type}")

            except GitHookError as e:
                console.print(f"[red]ERROR[/red] {e}")
                sys.exit(1)

        elif action.lower() == "list":
            if not manager.is_git_repo():
                console.print("[yellow]![/yellow] Not a git repository")
                return

            hooks_status = manager.list_installed_hooks()

            console.print("[cyan]Git Hooks Status:[/cyan]\n")

            for hook_name, hook_type_status in hooks_status.items():
                if hook_type_status == "not installed":
                    console.print(f"  [dim]-- {hook_name} (not installed)[/dim]")
                elif hook_type_status == "document-health":
                    console.print(f"  [green]OK[/green] {hook_name}: [yellow]document-health[/yellow]")
                elif hook_type_status == "graph-rebuild":
                    console.print(f"  [green]OK[/green] {hook_name}: [cyan]graph-rebuild[/cyan]")
                else:
                    console.print(f"  [green]OK[/green] {hook_name}: {hook_type_status}")

            console.print()
            console.print("[dim]Use 'mhooks install <document-health|pre-commit|post-checkout>' to install[/dim]")

        else:
            console.print(f"[red]ERROR[/red] Unknown action: {action}")
            console.print("Valid actions: install, uninstall, list")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@app.command()
def migrate_timeline(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be migrated without actually moving files"),
):
    """Migrate timeline files from legacy structure to new daily/ structure.

    This command migrates timeline files from:
      timeline/YYYY-MM/DD.md (legacy)
    To:
      timeline/daily/YYYY-MM/DD.md (new structure)

    Use --dry-run to preview what would be migrated.

    Examples:
        mmigrate-timeline              # Perform migration
        mmigrate-timeline --dry-run    # Preview migration
    """
    try:
        from memory_tool.utils.migrate_timeline import TimelineMigrator

        console.print("[cyan]Timeline Migration[/cyan]\n")

        # Initialize migrator
        migrator = TimelineMigrator()

        # Find files to migrate
        migrations = migrator.find_legacy_files()

        if not migrations:
            console.print("[green]No legacy timeline files found.[/green]")
            console.print("[dim]All timeline files are already in the new structure.[/dim]")
            return

        # Show what will be migrated
        console.print(f"[yellow]Found {len(migrations)} file(s) to migrate:[/yellow]\n")

        for source, dest in migrations[:10]:  # Show first 10
            console.print(f"  [dim]{source.relative_to(migrator.timeline_path)}[/dim]")
            console.print(f"  [cyan]->[/cyan] [dim]{dest.relative_to(migrator.timeline_path)}[/dim]\n")

        if len(migrations) > 10:
            console.print(f"  [dim]... and {len(migrations) - 10} more files[/dim]\n")

        if dry_run:
            console.print("[yellow]DRY RUN:[/yellow] No files were moved.")
            console.print("[dim]Run without --dry-run to perform migration[/dim]")
            return

        # Confirm migration
        if not typer.confirm("\nProceed with migration?"):
            console.print("[yellow]Migration cancelled[/yellow]")
            return

        # Perform migration
        console.print("\n[cyan]Migrating files...[/cyan]")
        success_count, error_count = migrator.migrate(dry_run=False)

        # Report results
        console.print()
        if success_count > 0:
            console.print(f"[green]SUCCESS[/green] Migrated {success_count} file(s)")

        if error_count > 0:
            console.print(f"[red]ERROR[/red] Failed to migrate {error_count} file(s)")

        if success_count > 0:
            console.print("\n[dim]Empty legacy directories have been removed.[/dim]")
            console.print("[green]Migration complete![/green]")

    except Exception as e:
        console.print(f"[red]ERROR[/red] Migration failed: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)
