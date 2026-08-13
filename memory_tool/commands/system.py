"""System-related CLI commands (init, status, alias, completion, tutorial, hooks, migrate, update)."""

import sys
from pathlib import Path
from typing import Optional

import typer

from memory_tool.commands.common import app, console, opt_str, resolve_module_name
from memory_tool.utils.paths import base_dir_for_root, display_path, get_project_root


@app.command(
    epilog="For detailed help: [bold]mhelp init[/bold]"
)
def init(
    path: str = typer.Argument(".", help="Path to initialize .memory/ structure"),
    force: bool = typer.Option(False, "--force", "-f", help="Force reinitialize (overwrites existing)"),
    kb: Optional[str] = typer.Option(None, "--kb", help="Path to knowledge base directory"),
    update_docs: bool = typer.Option(False, "--update-docs", help="Update documentation templates only"),
    update_all: bool = typer.Option(False, "--update-all", help="Update all templates (creates backups)"),
    base: Optional[str] = typer.Option(
        None,
        "--base",
        help="Knowledge base folder name (default: .memory). Use '.' for the project root.",
    ),
):
    """Initialize the knowledge base structure (minit command).

    Creates the knowledge base folder with timeline, modules, plans and
    configuration files, plus .claude/ for Claude Code integration.

    The folder name is recorded in a .memory-tool.yml pointer file, so it can be
    changed later with 'mbase set'. Because Obsidian hides dot-prefixed folders,
    use a visible name (or the vault root) when working inside a vault.

    Examples:
        minit                      # Initialize .memory/ in current directory
        minit --base memory        # Use a visible memory/ folder
        minit --base .             # Use the current directory as the base
        minit --force              # Reinitialize (overwrites)
        minit --update-docs        # Update documentation templates
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

    try:
        initializer = MemoryInitializer(target_path, base_name=base)
    except InitializationError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)

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
        base_label = (
            "the project root" if initializer.is_root_base else f"{initializer.base_name}/"
        )
        console.print(f"[green]OK[/green] Initialized knowledge base at: {initializer.memory_path}")
        console.print(f"[dim]Base folder: {base_label}[/dim]")
        console.print(f"[dim]Created {len(created['directories'])} directories, {len(created['files'])} files[/dim]")

        if kb:
            console.print(f"[dim]Knowledge base: {kb}[/dim]")

        if initializer.is_root_base:
            from memory_tool.utils.paths import CONTENT_SUBDIRS

            console.print(
                f"\n[dim]Records go straight to timeline/, modules/, ... "
                f"Only these folders are searched: {', '.join(CONTENT_SUBDIRS)}[/dim]"
            )
        elif initializer.base_name.startswith("."):
            console.print(
                f"\n[yellow]NOTE[/yellow] '{initializer.base_name}' is hidden in Obsidian."
            )
            console.print(
                "[dim]For vault use: minit --base memory, or change later with "
                "'mbase set memory'.[/dim]"
            )

        # Claude Code integration info
        template_path = initializer.memory_path / "templates" / "CLAUDE.md.template"
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
    base_path = get_project_root()
    memory_path = base_dir_for_root(base_path)

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

        # Calculate knowledge base size. When the base folder is the project
        # root, only the content subfolders count -- otherwise this would report
        # the size of venv/, .git/ and the rest of the project.
        from memory_tool.utils.paths import CONTENT_SUBDIRS

        if base_dir_for_root(base_path) == base_path:
            size_roots = [
                memory_path / name
                for name in CONTENT_SUBDIRS
                if (memory_path / name).is_dir()
            ]
        else:
            size_roots = [memory_path]

        total_size = 0
        for root in size_roots:
            for item in root.rglob("*"):
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


def _display_aliases_grouped(manager, status_map, lang=None):
    """Display aliases grouped by category."""
    from collections import defaultdict

    # Group aliases by category
    groups = defaultdict(list)
    for alias_name, alias_info in manager.ALIASES_EXT.items():
        command, desc_en, desc_ko, category = alias_info
        groups[category].append((alias_name, command, desc_en, desc_ko))

    # Display order
    group_order = ["core", "timeline", "search", "module", "federation", "plan", "llm", "notion", "system"]

    for group_key in group_order:
        if group_key not in groups:
            continue

        group_title = manager.ALIAS_GROUPS.get(group_key, group_key)
        console.print(f"[bold yellow]{group_title}[/bold yellow]")

        # Separate English and Korean aliases
        english_aliases = []
        korean_aliases = []

        for alias_name, command, desc_en, desc_ko in groups[group_key]:
            # Check if Korean (contains Hangul)
            is_korean = any('\uac00' <= c <= '\ud7a3' for c in alias_name)
            if is_korean:
                korean_aliases.append((alias_name, command, desc_en, desc_ko))
            else:
                english_aliases.append((alias_name, command, desc_en, desc_ko))

        # Display English aliases first
        for alias_name, command, desc_en, desc_ko in sorted(english_aliases, key=lambda x: x[0]):
            installed = status_map.get(alias_name, False)
            status_icon = "[green]OK[/green]" if installed else "[dim]--[/dim]"

            # Choose description based on language
            if lang == "ko":
                desc = desc_ko
            elif lang == "en":
                desc = desc_en
            else:
                desc = f"{desc_en} / {desc_ko}"

            console.print(f"  {status_icon} {alias_name:12} -> {command:12} {desc}")

        # Display Korean aliases
        if korean_aliases:
            for alias_name, command, desc_en, desc_ko in sorted(korean_aliases, key=lambda x: x[0]):
                installed = status_map.get(alias_name, False)
                status_icon = "[green]OK[/green]" if installed else "[dim]--[/dim]"

                if lang == "ko":
                    desc = desc_ko
                elif lang == "en":
                    desc = desc_en
                else:
                    desc = desc_ko  # Korean aliases show Korean description by default

                console.print(f"  {status_icon} [dim]{alias_name:12}[/dim] -> {command:12} [dim]{desc}[/dim]")

        console.print("")  # Empty line between groups


def _display_aliases_flat(manager, status_map, lang=None):
    """Display aliases in flat list (legacy format)."""
    for alias_name, installed in status_map.items():
        if hasattr(manager, 'ALIASES_EXT') and alias_name in manager.ALIASES_EXT:
            command, desc_en, desc_ko, _ = manager.ALIASES_EXT[alias_name]
            if lang == "ko":
                desc = desc_ko
            elif lang == "en":
                desc = desc_en
            else:
                desc = desc_en
        else:
            command, desc = manager.ALIASES.get(alias_name, ("?", "?"))

        status_icon = "[green]OK[/green]" if installed else "[dim]--[/dim]"
        console.print(f"  {status_icon} {alias_name:12} -> {command:12} ({desc})")


@app.command()
def alias(
    action: str = typer.Argument(..., help="Action: install, uninstall, list"),
    name: str = typer.Argument(None, help="Alias name (optional, default: all)"),
    directory: Optional[str] = typer.Option(None, "--dir", "-d", help="Installation directory (for script files)"),
    powershell: bool = typer.Option(False, "--powershell", "--ps", help="Use PowerShell profile (Windows)"),
    bash: bool = typer.Option(False, "--bash", help="Use Bash profile (~/.bashrc)"),
    zsh: bool = typer.Option(False, "--zsh", help="Use Zsh profile (~/.zshrc)"),
    lang: Optional[str] = typer.Option(None, "--lang", "-l", help="Language for descriptions: en, ko (default: both)"),
    flat: bool = typer.Option(False, "--flat", help="Show flat list instead of grouped"),
):
    """Manage command aliases (malias command).

    Examples:
        malias list                    # Show all aliases (grouped)
        malias list --lang ko          # Show with Korean descriptions
        malias list --flat             # Show flat list (not grouped)
        malias install --powershell    # Windows PowerShell
        malias install --bash          # Linux/macOS Bash
        malias install --zsh           # Linux/macOS Zsh
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
            # Get status map based on platform
            if powershell:
                status_map = manager.list_powershell_installed()
                profile_path = manager.get_powershell_profile_path()
                platform_name = "PowerShell Profile"
            elif bash or zsh:
                shell_name = "Bash" if bash else "Zsh"
                status_map = manager.list_shell_installed(shell=shell_type)
                profile_path = manager.get_shell_profile_path(shell_type)
                platform_name = f"{shell_name} Profile"
            else:
                status_map = manager.list_installed(install_dir)
                target_dir = install_dir or manager.get_default_install_dir()
                profile_path = target_dir
                platform_name = "Batch Files"

            # Display header
            console.print(f"[bold cyan]{platform_name}:[/bold cyan] {profile_path}\n")

            # Get language preference
            lang_pref = opt_str(lang)

            if not flat and hasattr(manager, 'ALIASES_EXT') and hasattr(manager, 'ALIAS_GROUPS'):
                # Grouped display
                _display_aliases_grouped(manager, status_map, lang_pref)
            else:
                # Flat display (legacy)
                _display_aliases_flat(manager, status_map, lang_pref)

            # Show status summary
            console.print("")
            installed_count = sum(1 for v in status_map.values() if v)
            total_count = len(status_map)
            console.print(f"[dim]Installed: {installed_count}/{total_count}[/dim]")

            if powershell:
                if any(status_map.values()):
                    console.print("[green]OK[/green] Aliases configured in PowerShell profile")
                else:
                    console.print("[dim]Run 'malias install --powershell' to install[/dim]")
            elif bash or zsh:
                if any(status_map.values()):
                    console.print(f"[green]OK[/green] Aliases configured in {shell_name} profile")
                else:
                    console.print(f"[dim]Run 'malias install --{shell_type}' to install[/dim]")
            else:
                in_path = manager.is_in_path(target_dir)
                if in_path:
                    console.print("[green]OK[/green] Directory is in PATH")
                else:
                    console.print("[yellow]![/yellow] Directory NOT in PATH")
                    console.print("[dim]Run 'malias install' for setup instructions[/dim]")

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
    lang: str = typer.Option("en", "--lang", help="Language: en (English), ko (Korean)"),
):
    """Interactive tutorial for memory_tool (mtutorial command).

    Learn how to use memory_tool commands with step-by-step tutorials.
    Available in English and Korean.

    Lessons:
        installation   - Install and set up memory_tool
        setup          - Configure CLAUDE.md for AI integration
        daily          - Daily workflow guide
        ai-integration - Claude Code, Gemini CLI integration
        recording      - Recording best practices
        search         - Search and retrieval
        modules        - Module organization
        korean         - Korean commands (한글 명령어)
        quickref       - Quick reference card

    Examples:
        mtutorial                      # Interactive menu (English)
        mtutorial --lang ko            # Interactive menu (Korean)
        mtutorial setup                # CLAUDE.md setup guide
        mtutorial ai-integration       # AI integration guide
        mtutorial daily --lang ko      # Daily workflow (Korean)
        mtutorial --list               # List all lessons
        mtutorial --list --lang ko     # List lessons (Korean)
    """
    try:
        from memory_tool.utils.tutorial import Tutorial

        # Validate language
        if lang not in ["en", "ko"]:
            console.print(f"[yellow]Warning:[/yellow] Unknown language '{lang}', using 'en'")
            lang = "en"

        tut = Tutorial(lang=lang)

        if list_lessons:
            tut.list_lessons()
        else:
            tut.run(lesson_id=lesson)

    except KeyboardInterrupt:
        msg = "\n[yellow]튜토리얼 종료[/yellow]" if lang == "ko" else "\n[yellow]Tutorial closed[/yellow]"
        console.print(msg)
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

                console.print(f"\n[green]OK[/green] Hook installed: {display_path(hook_path)}")
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


@app.command(
    epilog="For detailed help: [bold]mhelp config[/bold]"
)
def config(
    action: str = typer.Argument(..., help="Action: list, get, set, guide"),
    key: str = typer.Argument(None, help="Config key path (e.g., help.language)"),
    value: str = typer.Argument(None, help="Value to set (for 'set' action)"),
):
    """Manage config.yaml settings (mconfig command).

    View and modify configuration settings including timeline, search,
    LLM, Notion integration, and help language preferences.

    Examples:
        mconfig list                      # Show all settings
        mconfig get help.language         # Get help language
        mconfig set help.language ko      # Set to Korean
        mconfig set llm.provider ollama   # Set LLM provider
        mconfig guide                     # Interactive setup guide
    """
    import yaml
    from memory_tool.utils.config import Config

    base_path = get_project_root()
    memory_path = base_dir_for_root(base_path)
    config_path = memory_path / "config.yaml"

    if not memory_path.exists():
        console.print("[red]ERROR[/red] .memory/ not found in current directory")
        console.print("[dim]Run 'minit' to initialize[/dim]")
        sys.exit(1)

    try:
        if action == "list":
            # List all config values
            cfg = Config(memory_path)
            config_data = cfg.load()

            console.print("[bold cyan]Configuration:[/bold cyan]\n")

            def print_config(data, prefix=""):
                for k, v in data.items():
                    full_key = f"{prefix}.{k}" if prefix else k
                    if isinstance(v, dict):
                        console.print(f"[yellow]{full_key}:[/yellow]")
                        print_config(v, full_key)
                    else:
                        console.print(f"  {full_key}: [green]{v}[/green]")

            print_config(config_data)
            console.print(f"\n[dim]Config file: {config_path}[/dim]")

        elif action == "get":
            if not key:
                console.print("[red]ERROR[/red] Key path required for 'get' action")
                console.print("[dim]Example: mconfig get help.language[/dim]")
                sys.exit(1)

            cfg = Config(memory_path)
            result = cfg.get(key)

            if result is None:
                console.print(f"[yellow]Key not found:[/yellow] {key}")
            else:
                console.print(f"{key}: [green]{result}[/green]")

        elif action == "set":
            if not key:
                console.print("[red]ERROR[/red] Key path required for 'set' action")
                console.print("[dim]Example: mconfig set help.language ko[/dim]")
                sys.exit(1)

            if value is None:
                console.print("[red]ERROR[/red] Value required for 'set' action")
                console.print(f"[dim]Example: mconfig set {key} <value>[/dim]")
                sys.exit(1)

            # Load existing config or start fresh
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f) or {}
            else:
                config_data = {}

            # Parse value (convert to appropriate type)
            parsed_value = value
            if value.lower() == "true":
                parsed_value = True
            elif value.lower() == "false":
                parsed_value = False
            elif value.isdigit():
                parsed_value = int(value)
            elif value.replace(".", "", 1).isdigit():
                parsed_value = float(value)

            # Set nested key
            keys = key.split(".")
            current = config_data
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                elif not isinstance(current[k], dict):
                    current[k] = {}
                current = current[k]

            old_value = current.get(keys[-1])
            current[keys[-1]] = parsed_value

            # Write back to config file
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

            if old_value is not None:
                console.print(f"[green]OK[/green] {key}: [dim]{old_value}[/dim] -> [green]{parsed_value}[/green]")
            else:
                console.print(f"[green]OK[/green] {key}: [green]{parsed_value}[/green]")

        elif action == "guide":
            # Interactive setup guide
            from rich.prompt import Prompt
            from rich.panel import Panel
            from memory_tool.commands.common import get_help_language

            lang = get_help_language()
            is_ko = (lang == "ko")

            # Bilingual messages
            msg = {
                "title": "설정 가이드" if is_ko else "Configuration Guide",
                "welcome": "memory_tool 설정을 도와드립니다." if is_ko else "Let me help you configure memory_tool.",
                "select_category": "설정할 카테고리를 선택하세요:" if is_ko else "Select a category to configure:",
                "categories": {
                    "1": ("언어 설정", "Language settings") if is_ko else ("Language settings", "언어 설정"),
                    "2": ("태그 형식", "Tag format") if is_ko else ("Tag format", "태그 형식"),
                    "3": ("Notion 연동", "Notion integration") if is_ko else ("Notion integration", "Notion 연동"),
                    "4": ("LLM 설정", "LLM settings") if is_ko else ("LLM settings", "LLM 설정"),
                    "q": ("종료", "Exit") if is_ko else ("Exit", "종료"),
                },
                "current": "현재 값" if is_ko else "Current",
                "choose": "선택" if is_ko else "Choice",
                "saved": "저장됨" if is_ko else "Saved",
                "cancelled": "취소됨" if is_ko else "Cancelled",
                "back": "뒤로 가려면 빈 값 입력" if is_ko else "Press Enter to go back",
            }

            def save_config(key_path: str, new_value):
                """Save a config value."""
                if config_path.exists():
                    with open(config_path, "r", encoding="utf-8") as f:
                        config_data = yaml.safe_load(f) or {}
                else:
                    config_data = {}

                keys = key_path.split(".")
                current = config_data
                for k in keys[:-1]:
                    if k not in current:
                        current[k] = {}
                    current = current[k]
                current[keys[-1]] = new_value

                with open(config_path, "w", encoding="utf-8") as f:
                    yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

            def get_current(key_path: str):
                """Get current config value."""
                cfg = Config(memory_path)
                return cfg.get(key_path)

            console.print(Panel(f"[bold]{msg['title']}[/bold]\n\n{msg['welcome']}", border_style="cyan"))

            while True:
                console.print(f"\n[bold]{msg['select_category']}[/bold]")
                for num, (primary, secondary) in msg["categories"].items():
                    console.print(f"  [cyan]{num}[/cyan]. {primary} [dim]({secondary})[/dim]")

                choice = Prompt.ask(f"\n{msg['choose']}", default="q")

                if choice == "q":
                    break

                elif choice == "1":
                    # Language settings
                    console.print(Panel(
                        "[bold]help.language[/bold]\n\n"
                        + ("도움말 및 출력 언어를 설정합니다.\n\n" if is_ko else "Set the language for help and output.\n\n")
                        + "  [cyan]en[/cyan] - English\n"
                        + "  [cyan]ko[/cyan] - 한국어\n",
                        title="언어 설정" if is_ko else "Language Settings",
                        border_style="blue"
                    ))
                    current = get_current("help.language") or "en"
                    console.print(f"{msg['current']}: [green]{current}[/green]")
                    new_val = Prompt.ask(
                        "help.language",
                        choices=["en", "ko", ""],
                        default=""
                    )
                    if new_val:
                        save_config("help.language", new_val)
                        console.print(f"[green]{msg['saved']}[/green]: help.language = {new_val}")

                elif choice == "2":
                    # Tag format settings
                    console.print(Panel(
                        "[bold]tag.storage_format[/bold]\n"
                        + ("태그가 파일에 저장되는 형식입니다.\n\n" if is_ko else "How tags are stored in files.\n\n")
                        + "  [cyan]bracket[/cyan]  - [태그] 형식 (메시지 앞)\n"
                        + ("                 예: - 14:30 | [버그] [긴급] 메시지\n\n" if is_ko else "                 ex: - 14:30 | [bug] [urgent] message\n\n")
                        + "  [cyan]hashtag[/cyan] - #태그 형식 (메시지 뒤)\n"
                        + ("                 예: - 14:30 | 메시지 #버그 #긴급\n\n" if is_ko else "                 ex: - 14:30 | message #bug #urgent\n\n")
                        + "[bold]tag.display_format[/bold]\n"
                        + ("검색 결과 등에서 태그가 표시되는 형식입니다.\n" if is_ko else "How tags are displayed in search results.\n")
                        + ("(storage_format과 동일하게 설정하는 것을 권장)\n" if is_ko else "(Recommend setting same as storage_format)\n"),
                        title="태그 형식" if is_ko else "Tag Format",
                        border_style="blue"
                    ))

                    # storage_format
                    current_storage = get_current("tag.storage_format") or "bracket"
                    console.print(f"\n{msg['current']} tag.storage_format: [green]{current_storage}[/green]")
                    new_storage = Prompt.ask(
                        "tag.storage_format",
                        choices=["bracket", "hashtag", ""],
                        default=""
                    )
                    if new_storage:
                        save_config("tag.storage_format", new_storage)
                        console.print(f"[green]{msg['saved']}[/green]: tag.storage_format = {new_storage}")

                    # display_format
                    current_display = get_current("tag.display_format") or "bracket"
                    console.print(f"\n{msg['current']} tag.display_format: [green]{current_display}[/green]")
                    new_display = Prompt.ask(
                        "tag.display_format",
                        choices=["bracket", "hashtag", ""],
                        default=""
                    )
                    if new_display:
                        save_config("tag.display_format", new_display)
                        console.print(f"[green]{msg['saved']}[/green]: tag.display_format = {new_display}")

                elif choice == "3":
                    # Notion integration
                    console.print(Panel(
                        "[bold]notion.api_key[/bold]\n"
                        + ("Notion API 통합 토큰입니다.\n" if is_ko else "Notion API integration token.\n")
                        + ("https://www.notion.so/my-integrations 에서 생성\n\n" if is_ko else "Create at https://www.notion.so/my-integrations\n\n")
                        + "[bold]notion.default_page_id[/bold]\n"
                        + ("동기화할 기본 Notion 페이지 ID입니다.\n" if is_ko else "Default Notion page ID for sync.\n")
                        + ("페이지 URL에서 마지막 32자리 (하이픈 제외)\n\n" if is_ko else "Last 32 characters from page URL (without hyphens)\n\n")
                        + "[bold]notion.sync.timeline.root_page_id[/bold]\n"
                        + ("타임라인 동기화용 페이지 ID (선택사항)\n" if is_ko else "Page ID for timeline sync (optional)\n"),
                        title="Notion 연동" if is_ko else "Notion Integration",
                        border_style="blue"
                    ))

                    # api_key
                    current_key = get_current("notion.api_key")
                    if current_key:
                        masked = current_key[:10] + "..." + current_key[-4:] if len(current_key) > 14 else "***"
                        console.print(f"\n{msg['current']} notion.api_key: [green]{masked}[/green]")
                    else:
                        console.print(f"\n{msg['current']} notion.api_key: [dim](not set)[/dim]")

                    new_key = Prompt.ask("notion.api_key", default="", password=False)
                    if new_key:
                        save_config("notion.api_key", new_key)
                        console.print(f"[green]{msg['saved']}[/green]: notion.api_key")

                    # default_page_id
                    current_page = get_current("notion.default_page_id")
                    console.print(f"\n{msg['current']} notion.default_page_id: [green]{current_page or '(not set)'}[/green]")
                    new_page = Prompt.ask("notion.default_page_id", default="")
                    if new_page:
                        save_config("notion.default_page_id", new_page)
                        console.print(f"[green]{msg['saved']}[/green]: notion.default_page_id = {new_page}")

                elif choice == "4":
                    # LLM settings
                    console.print(Panel(
                        "[bold]llm.provider[/bold]\n"
                        + ("LLM 제공자를 선택합니다.\n\n" if is_ko else "Select LLM provider.\n\n")
                        + "  [cyan]anthropic[/cyan] - Claude API (Anthropic)\n"
                        + "  [cyan]openai[/cyan]    - OpenAI API\n"
                        + "  [cyan]ollama[/cyan]    - Local Ollama\n\n"
                        + "[bold]llm.model[/bold]\n"
                        + ("사용할 모델 이름입니다.\n" if is_ko else "Model name to use.\n")
                        + ("예: claude-3-5-sonnet-20241022, gpt-4o, llama3.2\n\n" if is_ko else "ex: claude-3-5-sonnet-20241022, gpt-4o, llama3.2\n\n")
                        + "[bold]llm.api_key[/bold]\n"
                        + ("API 키 (Anthropic/OpenAI용)\n" if is_ko else "API key (for Anthropic/OpenAI)\n"),
                        title="LLM 설정" if is_ko else "LLM Settings",
                        border_style="blue"
                    ))

                    # provider
                    current_provider = get_current("llm.provider") or "anthropic"
                    console.print(f"\n{msg['current']} llm.provider: [green]{current_provider}[/green]")
                    new_provider = Prompt.ask(
                        "llm.provider",
                        choices=["anthropic", "openai", "ollama", ""],
                        default=""
                    )
                    if new_provider:
                        save_config("llm.provider", new_provider)
                        console.print(f"[green]{msg['saved']}[/green]: llm.provider = {new_provider}")

                    # model
                    current_model = get_current("llm.model")
                    console.print(f"\n{msg['current']} llm.model: [green]{current_model or '(not set)'}[/green]")
                    new_model = Prompt.ask("llm.model", default="")
                    if new_model:
                        save_config("llm.model", new_model)
                        console.print(f"[green]{msg['saved']}[/green]: llm.model = {new_model}")

                    # api_key
                    current_llm_key = get_current("llm.api_key")
                    if current_llm_key:
                        masked = current_llm_key[:10] + "..." if len(current_llm_key) > 10 else "***"
                        console.print(f"\n{msg['current']} llm.api_key: [green]{masked}[/green]")
                    else:
                        console.print(f"\n{msg['current']} llm.api_key: [dim](not set)[/dim]")

                    new_llm_key = Prompt.ask("llm.api_key", default="")
                    if new_llm_key:
                        save_config("llm.api_key", new_llm_key)
                        console.print(f"[green]{msg['saved']}[/green]: llm.api_key")

                else:
                    console.print(f"[yellow]Unknown choice: {choice}[/yellow]")

            console.print(f"\n[dim]{'설정 가이드 종료' if is_ko else 'Configuration guide finished'}[/dim]")

        else:
            console.print(f"[red]ERROR[/red] Unknown action: {action}")
            console.print("[dim]Valid actions: list, get, set, guide[/dim]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR[/red] Config operation failed: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@app.command()
def update(
    check: bool = typer.Option(False, "--check", "-c", help="Check only, don't install"),
    auto: bool = typer.Option(False, "--auto", help="Enable automatic update check"),
    no_auto: bool = typer.Option(False, "--no-auto", help="Disable automatic update check"),
):
    """Check for updates and install latest version (mupdate command).

    Checks GitHub for the latest release tag and compares with the
    currently installed version. If a newer version is available,
    installs it via pip.

    Examples:
        mupdate              # Check and install updates
        mupdate --check      # Check only (no install)
        mupdate --auto       # Enable auto update check
        mupdate --no-auto    # Disable auto update check
    """
    from memory_tool.core.updater import (
        get_current_version,
        check_latest_version,
        compare_versions,
        do_update,
        get_auto_check_enabled,
        set_auto_check_enabled,
    )

    # Handle --auto / --no-auto toggle
    if auto or no_auto:
        enabled = auto and not no_auto
        set_auto_check_enabled(enabled)
        state = "[green]ON[/green]" if enabled else "[yellow]OFF[/yellow]"
        console.print(f"자동 업데이트 확인: {state}")
        if not check and not (auto and no_auto):
            return

    current = get_current_version()
    console.print(f"[cyan]Memory Tool[/cyan] v{current}")

    # Show auto-check status
    auto_status = get_auto_check_enabled()
    auto_label = "[green]ON[/green]" if auto_status else "[yellow]OFF[/yellow]"
    console.print(f"[dim]자동 확인: {auto_label}[/dim]\n")

    # Check latest version
    console.print("[dim]GitHub에서 최신 버전 확인 중...[/dim]")
    latest = check_latest_version()

    if latest is None:
        console.print("[yellow]WARNING[/yellow] 최신 버전을 확인할 수 없습니다")
        console.print("[dim]네트워크 연결을 확인하거나, GitHub에 태그가 있는지 확인하세요[/dim]")
        sys.exit(1)

    cmp = compare_versions(current, latest)

    if cmp == 0:
        console.print(f"[green]OK[/green] 이미 최신 버전입니다 (v{latest})")
        return
    elif cmp > 0:
        console.print(f"[green]OK[/green] 현재 버전(v{current})이 최신 릴리즈(v{latest})보다 앞서 있습니다")
        return

    # Update available
    console.print(f"[yellow]업데이트 가능:[/yellow] v{current} → v{latest}")

    if check:
        console.print("\n[dim]업데이트하려면: mupdate[/dim]")
        return

    # Do update
    console.print(f"\n[cyan]v{latest} 설치 중...[/cyan]")
    success, message = do_update(latest)

    if success:
        console.print(f"[green]OK[/green] {message}")
        console.print("[dim]새 버전을 사용하려면 터미널을 재시작하세요[/dim]")
    else:
        console.print(f"[red]ERROR[/red] {message}")
        sys.exit(1)
