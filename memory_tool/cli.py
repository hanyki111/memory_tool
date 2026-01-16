"""CLI interface for Memory Tool."""

import sys
from datetime import timedelta
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel

from memory_tool.core.timeline import (
    Timeline,
    TimelineError,
    FutureTimeError,
    DistantPastWarning,
)
from memory_tool.core.init import (
    MemoryInitializer,
    InitializationError,
    AlreadyInitializedError,
)
from memory_tool.core.search import (
    MemorySearcher,
    SearchError,
)
from memory_tool.core.sort import (
    TimelineSorter,
    SortError,
)
from memory_tool.core.module import (
    ModuleManager,
    ModuleError,
)
from memory_tool.context.builder import (
    ContextBuilder,
    ContextError,
)
from memory_tool.utils.path_checker import (
    PathChecker,
    format_check_result,
)
from memory_tool.utils.alias import (
    AliasManager,
    AliasError,
)
from memory_tool.utils.config import Config
from memory_tool.llm.client import LLMClient
from memory_tool.summary import (
    TimelineSummarizer,
    ConversationSummarizer,
    ModuleSummarizer,
)
from memory_tool.review import ReviewManager
from memory_tool.notion.client import NotionClient, NotionError
from memory_tool.notion.models import SyncDirection

app = typer.Typer(
    name="memory-tool",
    help="Time-Space Integrated Knowledge System",
    add_completion=False,
)
console = Console()


def sanitize_output(text: str) -> str:
    """Remove characters that cause issues with Windows console.

    Args:
        text: Input text

    Returns:
        Sanitized text
    """
    # Replace common problematic characters
    replacements = {
        '⭐': '*',
        '✅': '[OK]',
        '❌': '[X]',
        '⚠️': '[!]',
        '⚠': '[!]',
        '🎯': '[TARGET]',
        '🔄': '[REFRESH]',
        '📝': '[NOTE]',
        '💡': '[IDEA]',
        '🚀': '[LAUNCH]',
        '✨': '[NEW]',
        '🔍': '[SEARCH]',
        '📌': '[PIN]',
        '🎉': '[DONE]',
        '💪': '[STRONG]',
        '🤔': '[THINK]',
        '📋': '[LIST]',
        '🔗': '[LINK]',
    }

    for emoji, replacement in replacements.items():
        text = text.replace(emoji, replacement)

    return text


def _opt_str(value) -> Optional[str]:
    """Safely convert Typer option value to str or None.

    Typer 0.12.0+ may return OptionInfo objects instead of None
    when optional parameters are not provided. This function handles that.

    Args:
        value: Value from typer.Option (could be str, None, or OptionInfo)

    Returns:
        str if value is a string, None otherwise
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value
    # OptionInfo or other objects become None
    return None


def _arg_str(value) -> str:
    """Safely convert Typer argument value to str.

    Typer 0.12.0+ may return ArgumentInfo objects instead of actual values
    in some edge cases. This function handles that.

    Args:
        value: Value from typer.Argument (could be str or ArgumentInfo)

    Returns:
        str value

    Raises:
        typer.BadParameter: If value is not a valid string
    """
    if isinstance(value, str):
        return value
    # ArgumentInfo or other objects - this shouldn't happen for required args
    # but if it does, raise an error
    raise typer.BadParameter(f"Invalid argument value: {type(value).__name__}")


def _resolve_module_name(module_name: str) -> str:
    """Resolve module name to full path by searching all modules.

    Args:
        module_name: Module name or path (e.g., 'website' or 'projects/website')

    Returns:
        Full module path (e.g., 'projects/website')

    Raises:
        typer.Exit: If module not found or multiple matches require selection
    """
    if not module_name:
        return None

    # Try exact match first
    manager = ModuleManager()
    matches = manager.find_module_by_name(module_name, exact=True)

    if len(matches) == 1:
        return matches[0]

    # Try flexible match (by last component)
    if len(matches) == 0:
        matches = manager.find_module_by_name(module_name, exact=False)

    # Handle results
    if len(matches) == 0:
        console.print(f"[red]ERROR[/red] Module not found: {module_name}")
        console.print("[dim]Use 'python -m memory_tool module list' to see all modules[/dim]")
        raise typer.Exit(1)
    elif len(matches) == 1:
        resolved = matches[0]
        if resolved != module_name:
            console.print(f"[dim]Resolved '{module_name}' -> '{resolved}'[/dim]")
        return resolved
    else:
        # Multiple matches - ask user to select
        console.print(f"[yellow]Multiple modules match '{module_name}':[/yellow]")
        for i, match in enumerate(matches, 1):
            console.print(f"  {i}. {match}")
        console.print("\n[dim]Please specify the full path (e.g., --module projects/website)[/dim]")
        raise typer.Exit(1)


@app.command()
def record(
    message: str = typer.Argument(..., help="Message to record in timeline"),
    date: Optional[str] = typer.Option(None, "--date", help="Date (YYYY-MM-DD)"),
    time: Optional[str] = typer.Option(None, "--time", help="Time (HH:MM)"),
    force: bool = typer.Option(False, "--force", "-f", help="Force recording (skip warnings)"),
):
    """Record a message to timeline (m command)."""
    # Safely convert Typer ArgumentInfo/OptionInfo to str/None
    message = _arg_str(message)
    date = _opt_str(date)
    time = _opt_str(time)

    timeline = Timeline()

    try:
        dt, file_path = timeline.record(message, date, time, force=force)

        # Success message
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
            # Don't fail the record if auto-update fails
            console.print(f"[yellow]Warning:[/yellow] Auto-update failed: {e}")

        # Document health suggestion (NEW - Phase 5b)
        try:
            from memory_tool.utils.suggestion_helper import check_and_suggest_after_command

            memory_dir = Path.cwd() / ".memory"
            check_and_suggest_after_command(memory_dir, "m", force=False)
        except Exception:
            # Don't fail the record if suggestion fails
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
def search(
    query: str = typer.Argument(..., help="Search query (regex pattern or semantic)"),
    with_kb: bool = typer.Option(False, "--with-kb", help="Include personal KB"),
    all: bool = typer.Option(False, "--all", help="Search all projects"),
    case_sensitive: bool = typer.Option(False, "--case", "-c", help="Case sensitive search"),
    no_context: bool = typer.Option(False, "--no-context", help="Hide context lines"),
    max_results: int = typer.Option(None, "--max", "-n", help="Maximum results"),
    from_date: Optional[str] = typer.Option(None, "--from", help="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = typer.Option(None, "--to", help="End date (YYYY-MM-DD)"),
    semantic: bool = typer.Option(False, "--semantic", "-s", help="Semantic search using embeddings"),
    threshold: float = typer.Option(0.3, "--threshold", "-t", help="Similarity threshold (0-1, semantic only)"),
    no_index: bool = typer.Option(False, "--no-index", help="Force file-based search (skip SQLite index)"),
    # New ranking options
    rank: Optional[str] = typer.Option(None, "--rank", help="Ranking algorithm: bm25 (default: none)"),
    boost_recent: bool = typer.Option(False, "--boost-recent", help="Boost recent results"),
    decay_days: int = typer.Option(30, "--decay-days", help="Date decay days (for --boost-recent)"),
    # New filter options
    date: Optional[str] = typer.Option(None, "--date", help="Date expression: today, yesterday, this-week, last-N-days, YYYY-MM-DD"),
    file_type: Optional[str] = typer.Option(None, "--type", help="File type: timeline, modules, decisions, plans, archive"),
    module_filter: Optional[str] = typer.Option(None, "--module", help="Filter by module path (e.g., 'projects' or 'projects/website')"),
    tag: List[str] = typer.Option(None, "--tag", help="Filter by tags (can use multiple times)"),
    # New formatting options
    show_score: bool = typer.Option(False, "--show-score", help="Show relevance scores"),
    summary: bool = typer.Option(False, "--summary", help="Show summary statistics"),
    # Phase 2 & 3 options
    hybrid: bool = typer.Option(False, "--hybrid", help="Hybrid search (text + semantic)"),
    text_weight: float = typer.Option(0.7, "--text-weight", help="Text weight for hybrid search (default: 0.7)"),
    semantic_weight: float = typer.Option(0.3, "--semantic-weight", help="Semantic weight for hybrid search (default: 0.3)"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable result caching"),
    cache_ttl: int = typer.Option(3600, "--cache-ttl", help="Cache TTL in seconds (default: 3600 / 1 hour)"),
):
    """Search timeline and modules (ms command).

    Examples:
        ms "bug fix" --rank bm25 --boost-recent
        ms "feature" --date this-week --type timeline
        ms "decision" --show-score --summary
        ms "implementation" --hybrid --text-weight 0.5 --semantic-weight 0.5
        ms "query" --no-cache
    """
    # Safely convert Typer ArgumentInfo/OptionInfo to str/None
    query = _arg_str(query)
    from_date = _opt_str(from_date)
    to_date = _opt_str(to_date)
    rank = _opt_str(rank)
    date = _opt_str(date)
    file_type = _opt_str(file_type)
    module_filter = _opt_str(module_filter)

    # Initialize cache if enabled
    search_cache = None
    cache_key_params = {
        "with_kb": with_kb,
        "all": all,
        "case_sensitive": case_sensitive,
        "max_results": max_results,
        "from_date": from_date,
        "to_date": to_date,
        "rank": rank,
        "boost_recent": boost_recent,
        "date": date,
        "file_type": file_type,
        "module_filter": module_filter,
        "tag": tuple(tag) if tag else None,
        "hybrid": hybrid,
        "text_weight": text_weight if hybrid else None,
        "semantic_weight": semantic_weight if hybrid else None,
    }

    if not no_cache:
        from memory_tool.search import SearchCache
        from pathlib import Path
        cache_dir = Path.home() / ".memory" / ".cache" / "search"
        search_cache = SearchCache(cache_dir, ttl_seconds=cache_ttl)

        # Try to get cached results
        cached_results = search_cache.get(query, **cache_key_params)
        if cached_results:
            console.print("[dim]Using cached results...[/dim]\n")
            # Display cached results using formatter
            if show_score or summary or not no_context:
                from memory_tool.search import ResultFormatter
                formatter = ResultFormatter(Path.cwd())
                formatter.print_results(
                    cached_results,
                    query=query,
                    show_score=show_score,
                    show_context=not no_context,
                    context_lines=1,
                    highlight=True,
                    show_summary=summary,
                )
            else:
                # Simple display
                for i, result in enumerate(cached_results, 1):
                    console.print(f"{i}. {result.file_path}:{result.line_number}")
            return

    # Hybrid search mode: combine text + semantic
    if hybrid:
        try:
            from memory_tool.core.vector_search import VectorSearcher, VectorSearchNotAvailableError
            from memory_tool.search import HybridSearcher
            from memory_tool.core.search import SearchResult

            # Perform text search
            searcher = MemorySearcher()
            scope = "all" if all else "local"

            from datetime import datetime
            parsed_from = None
            parsed_to = None

            try:
                if from_date:
                    parsed_from = datetime.strptime(from_date, "%Y-%m-%d").date()
                if to_date:
                    parsed_to = datetime.strptime(to_date, "%Y-%m-%d").date()
            except ValueError as e:
                console.print(f"[red]ERROR[/red] Invalid date format: {e}")
                sys.exit(1)

            # Text search
            text_results_dict = searcher.search(
                query,
                scope=scope,
                with_kb=with_kb,
                case_sensitive=case_sensitive,
                context_lines=1,
                max_results=max_results or 50,
                from_date=parsed_from,
                to_date=parsed_to,
                use_index=not no_index,
            )

            text_results = []
            for source_results in text_results_dict.values():
                text_results.extend(source_results)

            # Extract dates
            for result in text_results:
                date_from_path = searcher._extract_date_from_path(result.file_path)
                if date_from_path:
                    result.date = datetime.combine(date_from_path, datetime.min.time())

            # Semantic search
            try:
                vector_searcher = VectorSearcher()
                semantic_results_list = vector_searcher.semantic_search(
                    query,
                    top_k=max_results or 50,
                    threshold=threshold
                )

                # Convert to SearchResult format
                semantic_results = []
                for r in semantic_results_list:
                    semantic_results.append(SearchResult(
                        file_path=Path(r['file']),
                        line_number=r['line'],
                        line_content=r['content'],
                        match_context=r['content'],
                        score=r['similarity'],
                        date=datetime.fromisoformat(r['date']) if r.get('date') else None,
                    ))

                # Combine with HybridSearcher
                hybrid_searcher = HybridSearcher()
                all_results = hybrid_searcher.combine_results(
                    text_results,
                    semantic_results,
                    text_weight,
                    semantic_weight,
                )

                console.print(f"[cyan]Hybrid Search Results[/cyan] (text: {text_weight:.1f}, semantic: {semantic_weight:.1f})\n")

                # Apply filters and ranking
                if date or file_type or tag:
                    from memory_tool.search import FilterChain
                    filter_chain = FilterChain(searcher.base_path)
                    all_results = filter_chain.apply_filters(
                        all_results,
                        date_expr=date,
                        file_type=file_type,
                        tags=tag if tag else None,
                    )

                if rank or boost_recent:
                    from memory_tool.search import SearchRanker
                    use_bm25 = (rank == "bm25")
                    ranker = SearchRanker(
                        use_bm25=use_bm25,
                        use_date_weight=boost_recent,
                        date_decay_days=decay_days,
                    )
                    all_results = ranker.rank(query, all_results)

                # Cache results
                if search_cache:
                    search_cache.set(query, all_results, **cache_key_params)

                # Display results
                if all_results:
                    if show_score or summary or not no_context:
                        from memory_tool.search import ResultFormatter
                        formatter = ResultFormatter(searcher.base_path)
                        formatter.print_results(
                            all_results,
                            query=query,
                            show_score=show_score,
                            show_context=not no_context,
                            context_lines=1,
                            highlight=True,
                            show_summary=summary,
                        )
                    else:
                        for i, result in enumerate(all_results[:max_results] if max_results else all_results, 1):
                            console.print(f"{i}. {result.file_path}:{result.line_number}")
                else:
                    console.print("[yellow]No results found[/yellow]")

                return

            except VectorSearchNotAvailableError as e:
                console.print(f"[red]ERROR[/red] {e}")
                console.print("[dim]Install with: pip install memory-tool[vector][/dim]")
                sys.exit(1)

        except ImportError:
            console.print("[red]ERROR[/red] Vector search not available for hybrid mode")
            console.print("[dim]Install with: pip install memory-tool[vector][/dim]")
            sys.exit(1)

    # Use vector search if --semantic flag is set (semantic only)
    if semantic:
        try:
            from memory_tool.core.vector_search import VectorSearcher, VectorSearchNotAvailableError

            try:
                vector_searcher = VectorSearcher()
                results_list = vector_searcher.semantic_search(
                    query,
                    top_k=max_results or 10,
                    threshold=threshold
                )

                # Format results
                if not results_list:
                    console.print("[yellow]No results found[/yellow]")
                    return

                console.print(f"[cyan]Semantic Search Results[/cyan] (similarity >= {threshold})\n")
                for i, result in enumerate(results_list, 1):
                    similarity_color = "green" if result['similarity'] > 0.7 else "yellow" if result['similarity'] > 0.5 else "dim"
                    sanitized_content = sanitize_output(result['content'])
                    console.print(f"[{similarity_color}]{i}. [{result['similarity']:.2f}][/{similarity_color}] {result['file']}:{result['line']}")
                    console.print(f"   [dim]{result['date']}[/dim] | {sanitized_content}")
                    console.print()

                return

            except VectorSearchNotAvailableError as e:
                console.print(f"[red]ERROR[/red] {e}")
                console.print("[dim]Install with: pip install memory-tool[vector][/dim]")
                sys.exit(1)

        except ImportError:
            console.print("[red]ERROR[/red] Vector search not available")
            console.print("[dim]Install with: pip install memory-tool[vector][/dim]")
            sys.exit(1)

    # Regular search
    searcher = MemorySearcher()

    # Determine scope
    if all:
        scope = "all"
    else:
        scope = "local"

    # Parse dates (legacy --from/--to support)
    from datetime import datetime
    parsed_from = None
    parsed_to = None

    try:
        if from_date:
            parsed_from = datetime.strptime(from_date, "%Y-%m-%d").date()
        if to_date:
            parsed_to = datetime.strptime(to_date, "%Y-%m-%d").date()

        # Validate date range
        if parsed_from and parsed_to and parsed_from > parsed_to:
            console.print("[red]ERROR[/red] --from date must be before --to date")
            sys.exit(1)

    except ValueError as e:
        console.print(f"[red]ERROR[/red] Invalid date format: {e}")
        console.print("[dim]Use YYYY-MM-DD format (e.g., 2025-11-14)[/dim]")
        sys.exit(1)

    try:
        results_dict = searcher.search(
            query,
            scope=scope,
            with_kb=with_kb,
            case_sensitive=case_sensitive,
            context_lines=1 if not no_context else 0,
            max_results=max_results,
            from_date=parsed_from,
            to_date=parsed_to,
            use_index=not no_index,
        )

        # Convert dict results to flat list of SearchResults
        from memory_tool.core.search import SearchResult
        all_results = []
        for source_path, source_results in results_dict.items():
            all_results.extend(source_results)

        # Extract dates for results from file paths
        for result in all_results:
            date_from_path = searcher._extract_date_from_path(result.file_path)
            if date_from_path:
                result.date = datetime.combine(date_from_path, datetime.min.time())

        # Apply enhanced filters
        if date or file_type or tag or module_filter:
            from memory_tool.search import FilterChain
            filter_chain = FilterChain(searcher.base_path)
            all_results = filter_chain.apply_filters(
                all_results,
                date_expr=date,
                file_type=file_type,
                tags=tag if tag else None,
            )

            # Apply module filter separately
            if module_filter:
                # Filter results by module path
                modules_path = searcher.base_path / ".memory" / "modules"
                module_filter_path = modules_path / module_filter

                filtered_results = []
                for result in all_results:
                    # Check if result file is under the module path
                    try:
                        result_path = Path(result.file_path)
                        if result_path.is_relative_to(module_filter_path):
                            filtered_results.append(result)
                    except (ValueError, AttributeError):
                        # is_relative_to not available in older Python, fallback
                        result_str = str(result.file_path)
                        filter_str = str(module_filter_path)
                        if result_str.startswith(filter_str):
                            filtered_results.append(result)

                all_results = filtered_results

        # Apply ranking
        if rank or boost_recent:
            from memory_tool.search import SearchRanker

            use_bm25 = (rank == "bm25")
            ranker = SearchRanker(
                use_bm25=use_bm25,
                use_date_weight=boost_recent,
                date_decay_days=decay_days,
            )

            all_results = ranker.rank(query, all_results)

        # Limit results if needed
        if max_results and len(all_results) > max_results:
            all_results = all_results[:max_results]

        # Cache results
        if search_cache:
            search_cache.set(query, all_results, **cache_key_params)

        # Format and display
        if show_score or summary or not no_context:
            # Use enhanced formatter
            from memory_tool.search import ResultFormatter
            formatter = ResultFormatter(searcher.base_path)

            formatter.print_results(
                all_results,
                query=query,
                show_score=show_score,
                show_context=not no_context,
                context_lines=1,
                highlight=True,
                show_summary=summary,
            )
        else:
            # Use simple formatter
            formatted = searcher.format_results(
                {str(searcher.memory_path): all_results},
                show_context=not no_context
            )
            console.print(formatted)

        # Document health suggestion (NEW - Phase 5b)
        try:
            from memory_tool.utils.suggestion_helper import check_and_suggest_after_command

            memory_dir = Path.cwd() / ".memory"
            check_and_suggest_after_command(memory_dir, "search", force=False)
        except Exception:
            # Don't fail if suggestion fails
            pass

    except SearchError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@app.command()
def context(
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (default: .claude/memory-context.md)",
    ),
    structure: bool = typer.Option(
        False,
        "--structure",
        "-s",
        help="Include module-source mapping in context",
    ),
    with_map: bool = typer.Option(
        False,
        "--with-map",
        "-m",
        help="Generate code-context.md with Python code structure",
    ),
    map_depth: str = typer.Option(
        "structure",
        "--map-depth",
        help="Code map depth: overview, structure (default), api, docs",
    ),
    map_path: str = typer.Option(
        None,
        "--map-path",
        help="Path to analyze for code map (default: current directory)",
    ),
    check_health_only: bool = typer.Option(
        False,
        "--check-health-only",
        help="Only check document health and exit (for git hooks)",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Quiet mode (minimal output)",
    ),
    update_interfaces: bool = typer.Option(
        False,
        "--update-interfaces",
        "-i",
        help="Update interface.md for all modules based on Related Files",
    ),
    include_archived: bool = typer.Option(
        False,
        "--include-archived",
        help="Include archived modules when updating interfaces",
    ),
):
    """Build context for Claude Code (mcontext command).

    With --with-map, also generates code-context.md containing Python code
    structure (classes, methods, signatures) for AI-assisted development.

    With --update-interfaces, updates interface.md for all modules by analyzing
    the Python source files listed in each module's Related Files section.
    Archive modules are excluded by default (use --include-archived to include).
    """
    # Health check only mode (for git hooks)
    if check_health_only:
        from memory_tool.utils.health_checker import DocumentHealthChecker

        memory_dir = Path.cwd() / ".memory"
        checker = DocumentHealthChecker(memory_dir)

        critical_issues = checker.get_critical_issues()
        warning_issues = checker.get_warning_issues()

        if critical_issues:
            if not quiet:
                console.print("\n[red]CRITICAL[/red] Document Health Issues:\n")
                for issue in critical_issues[:5]:
                    console.print(f"  - {issue.module_name}/{issue.file_type}.md: [yellow]{issue.line_count}[/yellow] lines")
                console.print()
                console.print("  [dim]Recommend archiving before commit:[/dim]")
                console.print(f"  [cyan]marchive decisions --suggest[/cyan]")
            sys.exit(2)  # Exit code 2 for critical
        elif warning_issues:
            if not quiet:
                console.print("\n[yellow]WARNING[/yellow] Document Health Issues:\n")
                for issue in warning_issues[:5]:
                    console.print(f"  - {issue.module_name}/{issue.file_type}.md: [yellow]{issue.line_count}[/yellow] lines")
                console.print()
                console.print("  [dim]Consider archiving:[/dim]")
                console.print(f"  [cyan]marchive decisions --suggest[/cyan]")
            sys.exit(1)  # Exit code 1 for warning
        else:
            if not quiet:
                console.print("[green]OK[/green] Document health OK")
            sys.exit(0)  # Exit code 0 for OK

    # Normal context building
    builder = ContextBuilder()

    # Parse output path
    output_path = Path(output) if output else None

    try:
        result_path = builder.write_context(output_path, include_structure=structure)

        # Success message
        if not quiet:
            try:
                rel_path = result_path.relative_to(Path.cwd())
            except ValueError:
                rel_path = result_path
            console.print(f"[green]OK[/green] Context built successfully")
            console.print(f"[dim]-> {rel_path}[/dim]")

            # Show what was included
            config = builder.load_config()
            recent_days = config.get("context", {}).get("recent_days", 3)
            timeline_count = len(builder.get_recent_timeline_paths(recent_days))
            module_count = len(builder.get_module_statuses())

            console.print(f"[dim]Included: {timeline_count} timeline(s), {module_count} module(s)[/dim]")

            if structure:
                console.print(f"[dim]Module-source mapping: included[/dim]")

            # Show cached path check warning if any
            path_checker = PathChecker()
            cached_warning = path_checker.get_cached_summary()
            if cached_warning:
                console.print(f"[yellow]Path issues:[/yellow] {cached_warning}")
                console.print(f"[dim]Run 'mcheck' for details[/dim]")

        # Generate code map if requested
        if with_map:
            from memory_tool.codemap import PythonParser, CodeMapFormatter, DepthLevel

            # Validate depth
            valid_depths = ["overview", "structure", "api", "docs"]
            if map_depth not in valid_depths:
                console.print(f"[yellow]![/yellow] Invalid map depth: {map_depth}, using 'structure'")
                map_depth = "structure"

            # Determine path to analyze
            analysis_path = Path(map_path) if map_path else Path.cwd()
            if not analysis_path.exists():
                console.print(f"[yellow]![/yellow] Map path not found: {map_path}")
            else:
                # Check for Python files
                py_files = list(analysis_path.rglob("*.py")) if analysis_path.is_dir() else []
                if analysis_path.is_dir() and not py_files:
                    console.print(f"[yellow]![/yellow] No Python files found for code map")
                else:
                    # Parse and format
                    parser = PythonParser()
                    if analysis_path.is_dir():
                        codemap = parser.parse_directory(analysis_path, relative_to=Path.cwd())
                    else:
                        module = parser.parse_file(analysis_path)
                        from memory_tool.codemap.models import CodeMap
                        codemap = CodeMap(root_path=Path.cwd(), modules=[module] if module else [])

                    if codemap.modules:
                        formatter = CodeMapFormatter(depth=DepthLevel(map_depth))
                        map_content = formatter.format(codemap)

                        # Write to code-context.md
                        claude_dir = Path.cwd() / ".claude"
                        claude_dir.mkdir(exist_ok=True)
                        code_context_path = claude_dir / "code-context.md"

                        header = f"# Code Structure Map\n\nGenerated by `mcontext --with-map`\nDepth: {map_depth}\n\n"
                        code_context_path.write_text(header + map_content, encoding="utf-8")

                        if not quiet:
                            stats = codemap.get_stats()
                            console.print(f"[green]OK[/green] Code map generated")
                            console.print(f"[dim]-> .claude/code-context.md ({stats['classes']} classes, {stats['methods']} methods)[/dim]")

        # Update interface.md for all modules
        if update_interfaces:
            from memory_tool.codemap import PythonParser, CodeMapFormatter, DepthLevel
            from memory_tool.context.related_files import get_module_related_files
            from memory_tool.core.module import ModuleManager

            memory_path = Path.cwd() / ".memory"
            if not memory_path.exists():
                console.print("[yellow]![/yellow] .memory/ not found, skipping interface update")
            else:
                module_manager = ModuleManager()
                modules = module_manager.list_modules(include_archived=include_archived)

                updated_count = 0
                skipped_count = 0

                all_modules = modules.get("active", []) + modules.get("root", [])

                for module_name in all_modules:
                    module_path = memory_path / "modules" / module_name
                    current_md = module_path / "current.md"

                    if not current_md.exists():
                        continue

                    # Get Related Files from current.md
                    related_files = get_module_related_files(module_path)

                    if related_files.is_empty():
                        skipped_count += 1
                        continue

                    # Filter for Python source files
                    py_files = []
                    project_root = Path.cwd()

                    for path_str in related_files.source:
                        # Try to resolve the path
                        full_path = project_root / path_str
                        if full_path.exists() and full_path.suffix == ".py":
                            py_files.append(full_path)
                        else:
                            # Try relative to module directory
                            module_relative = module_path / path_str
                            if module_relative.exists() and module_relative.suffix == ".py":
                                py_files.append(module_relative)

                    if not py_files:
                        skipped_count += 1
                        continue

                    # Parse Python files
                    parser = PythonParser(include_private=False)
                    from memory_tool.codemap.models import CodeMap

                    parsed_modules = []
                    for py_file in py_files:
                        module_info = parser.parse_file(py_file)
                        if module_info:
                            # Adjust path to be relative to project root
                            try:
                                module_info.path = py_file.relative_to(project_root)
                            except ValueError:
                                module_info.path = py_file
                            parsed_modules.append(module_info)

                    if not parsed_modules:
                        skipped_count += 1
                        continue

                    codemap = CodeMap(root_path=project_root, modules=parsed_modules)

                    # Generate interface.md
                    formatter = CodeMapFormatter(depth=DepthLevel.API, include_private=False)
                    interface_content = formatter.format_for_interface(codemap)

                    # Write to interface.md
                    interface_file = module_path / "interface.md"
                    interface_file.write_text(interface_content, encoding="utf-8")
                    updated_count += 1

                if not quiet:
                    console.print(f"[green]OK[/green] Interface files updated: {updated_count} module(s)")
                    if skipped_count > 0:
                        console.print(f"[dim]Skipped {skipped_count} module(s) (no Python source files)[/dim]")

    except ContextError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        sys.exit(1)


@app.command()
def check(
    module: str = typer.Option(
        None,
        "--module",
        "-m",
        help="Check specific module only",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show all paths, not just issues",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Quiet mode (exit code only)",
    ),
    legacy: bool = typer.Option(
        False,
        "--legacy",
        "-l",
        help="Use legacy grouped output format instead of standard error format",
    ),
    include_archived: bool = typer.Option(
        False,
        "--include-archived",
        help="Include archived modules in check",
    ),
):
    """Check validity of Related Files paths in modules (mcheck command).

    Validates that all paths specified in module Related Files sections
    actually exist in the project.

    Features:
    - Smart path resolution (module dir -> project root -> .memory)
    - Standard compiler-style error format (file:line: error: message)
    - IDE-friendly output (VSCode terminal links)
    - Archive modules excluded by default (use --include-archived to include)
    """
    checker = PathChecker()

    try:
        if module:
            # Check specific module
            module_name = _resolve_module_name(module)
            result = checker.check_module(module_name)

            if not quiet:
                if legacy:
                    # Legacy format
                    if not result.has_related_files:
                        console.print(f"[yellow]![/yellow] {module_name}")
                        console.print("  No Related Files section found")
                        if result.related_files.format_type == "legacy":
                            console.print("  [dim](using legacy Key Files format)[/dim]")
                    else:
                        console.print(f"{result.status_icon} {module_name}")
                        for path_result in result.path_results:
                            if verbose or not path_result.exists:
                                type_ind = ""
                                if path_result.exists:
                                    type_ind = " (dir)" if path_result.is_directory else " (file)"
                                console.print(f"  {path_result.status_icon} {path_result.path}{type_ind}")
                    console.print()
                    console.print(f"[dim]Valid: {result.valid_count}, Missing: {result.missing_count}[/dim]")
                else:
                    # Standard error format
                    for path_result in result.path_results:
                        if not path_result.exists:
                            console.print(f"[red]{path_result.format_error()}[/red]")
                    if not result.has_related_files:
                        source_file = f".memory/modules/{module_name}/current.md"
                        console.print(f"[yellow]{source_file}:1: warning: No Related Files section found[/yellow]")
                    console.print(f"\n[dim]Checked: {result.valid_count} valid, {result.missing_count} missing[/dim]")

            # Exit with error if issues found
            if result.has_issues:
                sys.exit(1)

        else:
            # Check all modules
            summary = checker.check_all_modules(include_archived=include_archived)

            # Save to cache
            checker.save_cache(summary)

            if not quiet:
                output = format_check_result(
                    summary,
                    verbose=verbose,
                    standard_format=not legacy,
                )
                console.print(output)

            # Exit with error if issues found
            if summary.has_issues:
                sys.exit(1)
            else:
                if not quiet:
                    console.print("\n[green]All paths valid![/green]")

    except Exception as e:
        if not quiet:
            console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)


@app.command()
def today():
    """Show today's timeline (mtoday command)."""
    timeline = Timeline()

    try:
        file_path, content = timeline.get_today()

        if file_path is None:
            console.print("[yellow]![/yellow] No timeline entries for today yet")
            console.print(f"[dim]Use: m \"your message\" to start recording[/dim]")
            return

        # Display today's timeline
        from datetime import datetime
        today_str = datetime.now().strftime("%Y-%m-%d")
        console.print(f"[cyan]{today_str} Timeline:[/cyan]\n")
        console.print(sanitize_output(content))
        console.print(f"\n[dim]File: {file_path}[/dim]")

    except Exception as e:
        console.print(f"[red]ERROR[/red] Failed to read today's timeline: {e}")
        sys.exit(1)


@app.command()
def week():
    """Show this week's timeline (mweek command)."""
    timeline = Timeline()

    try:
        week_files = timeline.get_week()

        if not week_files:
            console.print("[yellow]![/yellow] No timeline entries for this week yet")
            console.print(f"[dim]Use: m \"your message\" to start recording[/dim]")
            return

        # Display week's timeline
        from datetime import datetime
        today = datetime.now()
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)

        console.print(f"[cyan]Week of {monday.strftime('%Y-%m-%d')} Timeline:[/cyan]\n")

        for file_path, content in week_files:
            # Extract date from path (YYYY-MM/DD.md)
            year_month = file_path.parent.name
            day = file_path.stem
            date_str = f"{year_month}-{day}"

            console.print(f"[bold]{date_str}[/bold]")
            console.print(sanitize_output(content))
            console.print("")  # Blank line between days

        total_days = len(week_files)
        console.print(f"[dim]{total_days} day(s) with entries this week[/dim]")

    except Exception as e:
        console.print(f"[red]ERROR[/red] Failed to read week's timeline: {e}")
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
                today = date.today()
                today_plan = daily_path / today.strftime("%Y-%m") / f"{today.strftime('%d')}.md"
                if today_plan.exists():
                    import re
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
                today = date.today()
                iso_cal = today.isocalendar()
                week_num = iso_cal[1]
                week_plan = weekly_path / str(today.year) / f"W{week_num:02d}.md"
                if week_plan.exists():
                    import re
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
    # Safely convert Typer OptionInfo to str/None
    directory = _opt_str(directory)

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
def sort(
    date_or_all: str = typer.Argument("today", help="Date (YYYY-MM-DD), 'today', or 'all'"),
    no_backup: bool = typer.Option(False, "--no-backup", help="Skip backup creation"),
):
    """Sort timeline entries by time (msort command)."""
    sorter = TimelineSorter()

    # Check if initialized
    if not sorter.is_initialized():
        console.print(f"[red]ERROR[/red] Timeline not found at {sorter.timeline_path}")
        console.print("[dim]Run 'minit' to initialize[/dim]")
        sys.exit(1)

    try:
        # Parse date argument
        from datetime import datetime, date

        if date_or_all.lower() == "all":
            # Sort all timeline files
            console.print("[cyan]Sorting all timeline files...[/cyan]")
            results = sorter.sort_all(create_backup=not no_backup)

            if not results:
                console.print("[yellow]No timeline files found[/yellow]")
                sys.exit(0)

            # Display results
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
            # Sort today's file
            today = date.today()
            year_month = today.strftime("%Y-%m")
            day = today.strftime("%d")

            file_path = sorter.timeline_path / year_month / f"{day}.md"

            if not file_path.exists():
                console.print(f"[yellow]No timeline file for today ({today.strftime('%Y-%m-%d')})[/yellow]")
                sys.exit(0)

            console.print(f"[cyan]Sorting {today.strftime('%Y-%m-%d')}...[/cyan]")
            total, sorted_count = sorter.sort_file(file_path, create_backup=not no_backup)

            console.print(f"\n[green]OK[/green] Sorted {file_path.name}")
            console.print(f"  Total entries: {total}")
            console.print(f"  Sorted entries: {sorted_count}")
            console.print(f"  Unsorted entries: {total - sorted_count}")

            if not no_backup:
                backup_path = file_path.with_suffix(file_path.suffix + ".bak")
                console.print(f"\n[dim]Backup: {backup_path.name}[/dim]")

        else:
            # Parse specific date
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
def module(
    action: str = typer.Argument(..., help="Action: create, list, tree, archive, unarchive, connections, graph, rebuild-graph, check-links, suggest-links, suggest-ai, ai-organize, auto-tag, graph-history, graph-diff, graph-snapshot, from-text"),
    name: str = typer.Argument(None, help="Module name or path (e.g., 'projects/website')"),
    description: str = typer.Option("", "--desc", "-d", help="Module description"),
    reason: str = typer.Option("", "--reason", "-r", help="Reason for archiving"),
    tags: str = typer.Option("", "--tags", "-t", help="Module tags (comma-separated)"),
    archived: bool = typer.Option(False, "--archived", "-a", help="Include archived modules in list"),
    format: Optional[str] = typer.Option(None, "--format", "-f", help="Export format: mermaid, graphviz, json (for graph action)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path (for graph action)"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output (for rebuild-graph in hooks)"),
    version1: int = typer.Option(None, "--v1", help="First version ID (for graph-diff)"),
    version2: int = typer.Option(None, "--v2", help="Second version ID (for graph-diff)"),
    notes: str = typer.Option("", "--notes", "-n", help="Notes for graph snapshot"),
    limit: int = typer.Option(10, "--limit", "-l", help="Limit number of results"),
    text: Optional[str] = typer.Option(None, "--text", help="Input text for from-text action"),
    text_file: Optional[str] = typer.Option(None, "--text-file", help="File path containing input text for from-text action"),
    preview: bool = typer.Option(False, "--preview", "-p", help="Preview generated module without saving (for from-text action)"),
    lang: Optional[str] = typer.Option(None, "--lang", help="Output language for from-text: 'ko', 'en', 'auto'"),
    structure: Optional[str] = typer.Option(None, "--structure", "-s", help="Module structure type for from-text: 'feature' (software), 'topic' (learning/KB), 'auto'"),
):
    """Manage modules (supports hierarchical paths, wiki-style [[connections]], and AI suggestions)."""
    # Safely convert Typer ArgumentInfo/OptionInfo to str/None
    action = _arg_str(action)
    name = _opt_str(name)
    format = _opt_str(format)
    output = _opt_str(output)

    manager = ModuleManager()

    try:
        if action.lower() == "create":
            # Create new module
            if not name:
                console.print("[red]ERROR[/red] Module name is required for create")
                console.print("[dim]Usage: module create <name> [--desc \"description\"][/dim]")
                sys.exit(1)

            # Parse tags
            tag_list = [t.strip() for t in tags.split(",")] if tags else []

            console.print(f"[cyan]Creating module '{name}'...[/cyan]")
            module_path = manager.create(name, description, tag_list)

            # Success
            rel_path = module_path.relative_to(Path.cwd())
            console.print(f"\n[green]OK[/green] Module created: {name}")
            console.print(f"[dim]Location: {rel_path}[/dim]")
            console.print(f"\n[dim]Files created:[/dim]")
            console.print(f"  - module.md      (module definition)")
            console.print(f"  - current.md     (current status)")
            console.print(f"  - decisions.md   (decisions)")
            console.print(f"  - dependencies.md (dependencies)")
            console.print(f"  - interface.md   (interface/API)")

            # Document health suggestion (NEW - Phase 5b)
            try:
                from memory_tool.utils.suggestion_helper import check_and_suggest_after_command

                memory_dir = Path.cwd() / ".memory"
                check_and_suggest_after_command(memory_dir, "module", force=False)
            except Exception:
                # Don't fail if suggestion fails
                pass

        elif action.lower() == "list":
            # List modules
            modules = manager.list_modules(include_archived=archived)

            # Display active modules
            active = modules.get("active", [])
            console.print(f"[cyan]Active Modules:[/cyan] {len(active)}\n")

            if active:
                for mod_name in active:
                    console.print(f"  - {mod_name}")
            else:
                console.print("  [dim]No active modules[/dim]")

            # Display archived modules
            if archived and "archived" in modules:
                arch = modules["archived"]
                console.print(f"\n[cyan]Archived Modules:[/cyan] {len(arch)}\n")

                if arch:
                    for mod_name in arch:
                        console.print(f"  - {mod_name}")
                else:
                    console.print("  [dim]No archived modules[/dim]")

        elif action.lower() == "archive":
            # Archive module
            if not name:
                console.print("[red]ERROR[/red] Module name is required for archive")
                console.print("[dim]Usage: module archive <name> [--reason \"reason\"][/dim]")
                sys.exit(1)

            # Resolve module name
            resolved_name = _resolve_module_name(name)

            console.print(f"[cyan]Archiving module '{resolved_name}'...[/cyan]")
            archive_path = manager.archive(resolved_name, reason)

            # Success
            rel_path = archive_path.relative_to(Path.cwd())
            console.print(f"\n[green]OK[/green] Module archived: {resolved_name}")
            console.print(f"[dim]Location: {rel_path}[/dim]")

            if reason:
                console.print(f"[dim]Reason: {reason}[/dim]")

        elif action.lower() == "tree":
            # Display module hierarchy as tree
            tree = manager.build_module_tree()

            if not tree:
                console.print("[dim]No modules found[/dim]")
                return

            console.print("[cyan]Module Hierarchy:[/cyan]\n")

            def print_tree(node_dict, prefix="", is_last=True):
                """Recursively print tree structure."""
                items = list(node_dict.items())
                for i, (name, children) in enumerate(items):
                    is_last_item = (i == len(items) - 1)

                    # Print current node
                    connector = "└── " if is_last_item else "├── "
                    console.print(f"{prefix}{connector}{name}")

                    # Print children
                    if children:
                        extension = "    " if is_last_item else "│   "
                        print_tree(children, prefix + extension, is_last_item)

            print_tree(tree)

        elif action.lower() == "connections":
            # Show connections for a module
            if not name:
                console.print("[red]ERROR[/red] Module name is required for connections")
                console.print("[dim]Usage: module connections <name>[/dim]")
                sys.exit(1)

            from memory_tool.core.connections import ConnectionGraph

            graph = ConnectionGraph()

            # Get outgoing and incoming connections
            outgoing = graph.get_outgoing_connections(name)
            incoming = graph.get_incoming_connections(name)

            console.print(f"[cyan]Connections for module:[/cyan] {name}\n")

            # Display outgoing connections
            if outgoing:
                console.print(f"[green]Outgoing ({len(outgoing)}):[/green]")
                for conn in outgoing:
                    console.print(f"  → {conn.target}")
                    console.print(f"    [dim]{conn.source_file}:{conn.line_number}[/dim]")
            else:
                console.print("[dim]No outgoing connections[/dim]")

            console.print()

            # Display incoming connections
            if incoming:
                console.print(f"[green]Incoming ({len(incoming)}):[/green]")
                for conn in incoming:
                    console.print(f"  ← {conn.source}")
                    console.print(f"    [dim]{conn.source_file}:{conn.line_number}[/dim]")
            else:
                console.print("[dim]No incoming connections[/dim]")

        elif action.lower() == "graph":
            # Display connection graph overview or export
            from memory_tool.core.connections import ConnectionGraph

            graph = ConnectionGraph()

            # Handle export formats
            if format:
                if format.lower() == "mermaid":
                    diagram = graph.export_mermaid()

                    if output:
                        # Save to file
                        output_path = Path(output)
                        output_path.write_text(diagram, encoding="utf-8")
                        console.print(f"[green]OK[/green] Mermaid diagram saved to: {output}")
                    else:
                        # Print to console
                        console.print("[cyan]Mermaid Diagram:[/cyan]\n")
                        console.print(diagram)

                elif format.lower() == "graphviz":
                    dot = graph.export_graphviz()

                    if output:
                        # Save to file
                        output_path = Path(output)
                        output_path.write_text(dot, encoding="utf-8")
                        console.print(f"[green]OK[/green] Graphviz DOT saved to: {output}")
                    else:
                        # Print to console
                        console.print("[cyan]Graphviz DOT:[/cyan]\n")
                        console.print(dot)

                elif format.lower() == "json":
                    import json

                    graph_data = graph.to_json()
                    json_output = json.dumps(graph_data, indent=2, ensure_ascii=False)

                    if output:
                        # Save to file
                        output_path = Path(output)
                        output_path.write_text(json_output, encoding="utf-8")
                        console.print(f"[green]OK[/green] JSON saved to: {output}")
                    else:
                        # Print to console (for piping)
                        print(json_output)

                else:
                    console.print(f"[red]ERROR[/red] Unknown format: {format}")
                    console.print("Valid formats: mermaid, graphviz, json")
                    sys.exit(1)

                return

            # Default: show stats and overview
            stats = graph.get_graph_stats()

            console.print("[cyan]Module Connection Graph[/cyan]\n")

            console.print(f"Total connections: {stats['total_connections']}")
            console.print(f"Connected modules: {stats['connected_modules']}")
            console.print(f"Orphaned modules: {stats['orphaned_modules']}")

            # Show all modules with their connection counts
            all_modules = graph.get_all_modules()

            if all_modules:
                console.print(f"\n[cyan]Module Connections:[/cyan]\n")

                for module in sorted(all_modules):
                    outgoing = graph.get_outgoing_connections(module)
                    incoming = graph.get_incoming_connections(module)

                    out_count = len(outgoing)
                    in_count = len(incoming)

                    console.print(f"  {module}")
                    console.print(f"    [dim]→ {out_count} outgoing, ← {in_count} incoming[/dim]")
            else:
                console.print("\n[dim]No connections found. Run 'module rebuild-graph' to build the graph.[/dim]")

        elif action.lower() == "check-links":
            # Check for broken links
            from memory_tool.core.connections import ConnectionGraph

            graph = ConnectionGraph()

            console.print("[cyan]Checking module links...[/cyan]\n")

            # Check broken links
            broken = graph.check_broken_links()

            if broken:
                console.print(f"[yellow]Found {len(broken)} module(s) with broken links:[/yellow]\n")

                for source, targets in sorted(broken.items()):
                    console.print(f"  {source}:")
                    for target in targets:
                        console.print(f"    [red]x[/red] [[{target}]] -> module not found")

                console.print()
            else:
                console.print("[green]OK[/green] No broken links found\n")

            # Check orphaned modules
            orphaned = graph.get_orphaned_modules()

            if orphaned:
                console.print(f"[yellow]Found {len(orphaned)} orphaned module(s) (no connections):[/yellow]\n")

                for module in sorted(orphaned):
                    console.print(f"  [dim]{module}[/dim]")

                console.print()
            else:
                console.print("[green]OK[/green] No orphaned modules")

        elif action.lower() == "suggest-links":
            # Suggest backlinks for a module
            if not name:
                console.print("[red]ERROR[/red] Module name is required for suggest-links")
                console.print("[dim]Usage: module suggest-links <name>[/dim]")
                sys.exit(1)

            from memory_tool.core.connections import ConnectionGraph

            graph = ConnectionGraph()

            console.print(f"[cyan]Suggesting links for:[/cyan] {name}\n")

            suggestions = graph.suggest_backlinks(name, max_suggestions=10)

            if suggestions:
                console.print(f"[green]Suggested connections ({len(suggestions)}):[/green]\n")

                for module, reason in suggestions:
                    console.print(f"  → [[{module}]]")
                    console.print(f"    [dim]{reason}[/dim]")
                    console.print()

                console.print("[dim]Add these links to your module's .md files to create connections.[/dim]")
            else:
                console.print("[dim]No suggestions found.[/dim]")
                console.print("[dim]This module may already be well-connected, or there are no related modules.[/dim]")

        elif action.lower() == "rebuild-graph":
            # Rebuild connection graph from all modules
            from memory_tool.core.connections import ConnectionGraph
            from memory_tool.core.graph_versions import GraphVersionManager

            if not quiet:
                console.print("[cyan]Rebuilding connection graph...[/cyan]")

            graph = ConnectionGraph()

            try:
                total = graph.rebuild_from_modules()

                if not quiet:
                    console.print(f"\n[green]OK[/green] Connection graph rebuilt")
                    console.print(f"Found {total} connections")

                    # Show stats
                    stats = graph.get_graph_stats()
                    console.print(f"Connected modules: {stats['connected_modules']}")
                    console.print(f"Orphaned modules: {stats['orphaned_modules']}")

                # Auto-versioning: Create snapshot after rebuild
                try:
                    version_manager = GraphVersionManager()
                    version_id = version_manager.create_snapshot(notes="Auto-snapshot after rebuild-graph")

                    if not quiet:
                        console.print(f"\n[dim]Auto-snapshot created (version {version_id})[/dim]")
                except Exception:
                    # Don't fail rebuild if snapshot fails
                    pass

            except Exception as e:
                if not quiet:
                    console.print(f"[red]ERROR[/red] Failed to rebuild graph: {e}")
                sys.exit(1)

        elif action.lower() == "suggest-ai":
            # AI-based connection suggestions
            if not name:
                console.print("[red]ERROR[/red] Module name is required for suggest-ai")
                console.print("[dim]Usage: module suggest-ai <name>[/dim]")
                sys.exit(1)

            # Check if LLM is available
            if not LLMClient.check_availability():
                console.print("[red]ERROR[/red] LLM not configured")
                console.print("[dim]Set ANTHROPIC_API_KEY environment variable or configure Ollama[/dim]")
                console.print("[dim]See config.yaml for LLM configuration[/dim]")
                sys.exit(1)

            from memory_tool.core.ai_suggester import AIConnectionSuggester

            console.print(f"[cyan]Analyzing module content for AI suggestions:[/cyan] {name}\n")
            console.print("[dim]Using LLM to analyze content similarity...[/dim]\n")

            # Get module path
            mod_manager = ModuleManager()
            module_path = mod_manager.modules_path / name

            if not module_path.exists():
                console.print(f"[red]ERROR[/red] Module not found: {name}")
                sys.exit(1)

            # Get all candidate modules
            all_modules = mod_manager.discover_all_modules()
            candidates = [
                (str(mod), mod_manager.modules_path / mod)
                for mod in all_modules
                if str(mod) != name
            ]

            # Get AI suggestions
            suggester = AIConnectionSuggester()
            try:
                suggestions = suggester.suggest_connections(
                    module_path,
                    candidates,
                    max_suggestions=5
                )

                if suggestions:
                    console.print(f"[green]AI-suggested connections ({len(suggestions)}):[/green]\n")

                    for module_name, reason, confidence in suggestions:
                        confidence_pct = int(confidence * 100)
                        color = "green" if confidence >= 0.7 else "yellow" if confidence >= 0.5 else "dim"

                        # Normalize path separators for display
                        display_name = module_name.replace('\\', '/')
                        console.print(f"  → \\[\\[{display_name}]] [{color}]({confidence_pct}%)[/{color}]")
                        console.print(f"    [dim]{reason}[/dim]")
                        console.print()

                    console.print("[dim]Add these links to your module's .md files to create connections.[/dim]")
                else:
                    console.print("[dim]No strong connections suggested by AI.[/dim]")
                    console.print("[dim]The module content may be too unique or general.[/dim]")

            except Exception as e:
                console.print(f"[red]ERROR[/red] AI suggestion failed: {e}")
                sys.exit(1)

        elif action.lower() == "ai-organize":
            # AI-based module organization suggestions
            from memory_tool.core.ai_organizer import ModuleOrganizer

            console.print("[cyan]Analyzing module structure...[/cyan]\n")

            mod_manager = ModuleManager()
            organizer = ModuleOrganizer(mod_manager.modules_path)

            try:
                # Use name as scope if provided
                scope = name if name else None
                include_merges = True  # Could add --no-merges flag later

                with console.status("[dim]Analyzing modules (this may take a moment)...[/dim]"):
                    suggestions = organizer.analyze_and_suggest(
                        scope=scope,
                        include_merges=include_merges
                    )

                if suggestions:
                    # Format and display suggestions
                    output_text = organizer.format_suggestions(suggestions)
                    console.print(output_text)

                    # Summary
                    console.print(f"\n[dim]Total suggestions: {len(suggestions)}[/dim]")
                    console.print("[dim]Use these suggestions to improve your module organization.[/dim]")
                else:
                    console.print("[green]✓ Module structure looks good![/green]")
                    console.print("[dim]No organization suggestions at this time.[/dim]")

            except Exception as e:
                console.print(f"[red]ERROR[/red] Analysis failed: {e}")
                sys.exit(1)

        elif action.lower() == "auto-tag":
            # AI-based tag suggestions
            if not name:
                console.print("[red]ERROR[/red] Module name is required for auto-tag")
                console.print("[dim]Usage: module auto-tag <name>[/dim]")
                sys.exit(1)

            # Check if LLM is available
            if not LLMClient.check_availability():
                console.print("[red]ERROR[/red] LLM not configured")
                console.print("[dim]Set ANTHROPIC_API_KEY environment variable or configure Ollama[/dim]")
                console.print("[dim]See config.yaml for LLM configuration[/dim]")
                sys.exit(1)

            from memory_tool.core.ai_suggester import AIConnectionSuggester

            console.print(f"[cyan]Analyzing module content for tags:[/cyan] {name}\n")
            console.print("[dim]Using LLM to generate relevant tags...[/dim]\n")

            # Get module path
            mod_manager = ModuleManager()
            module_path = mod_manager.modules_path / name

            if not module_path.exists():
                console.print(f"[red]ERROR[/red] Module not found: {name}")
                sys.exit(1)

            # Get AI tag suggestions
            suggester = AIConnectionSuggester()
            try:
                tags = suggester.suggest_tags(module_path, max_tags=5)

                if tags:
                    console.print(f"[green]Suggested tags ({len(tags)}):[/green]\n")

                    for tag in tags:
                        console.print(f"  • {tag}")

                    console.print(f"\n[dim]Add these tags to your module's metadata or use them for organization.[/dim]")
                else:
                    console.print("[dim]No tags suggested by AI.[/dim]")
                    console.print("[dim]The module may need more content for tag generation.[/dim]")

            except Exception as e:
                console.print(f"[red]ERROR[/red] Tag generation failed: {e}")
                sys.exit(1)

        elif action.lower() == "graph-snapshot":
            # Create a snapshot of current graph state
            from memory_tool.core.graph_versions import GraphVersionManager

            console.print("[cyan]Creating graph snapshot...[/cyan]")

            manager_ver = GraphVersionManager()

            try:
                version_id = manager_ver.create_snapshot(notes=notes or "")

                console.print(f"\n[green]OK[/green] Snapshot created")
                console.print(f"Version ID: {version_id}")
                if notes:
                    console.print(f"Notes: {notes}")

                # Show current stats
                version = manager_ver.get_version(version_id)
                if version:
                    console.print(f"Connections: {version.total_connections}")
                    console.print(f"Modules: {version.total_modules}")
                    console.print(f"Timestamp: {version.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

            except Exception as e:
                console.print(f"[red]ERROR[/red] Failed to create snapshot: {e}")
                sys.exit(1)

        elif action.lower() == "graph-history":
            # List graph version history
            from memory_tool.core.graph_versions import GraphVersionManager

            console.print("[cyan]Graph Version History[/cyan]\n")

            manager_ver = GraphVersionManager()

            try:
                versions = manager_ver.list_versions(limit=limit or 10)

                if versions:
                    console.print(f"[green]Recent versions ({len(versions)}):[/green]\n")

                    for ver in versions:
                        timestamp_str = ver.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                        console.print(f"  Version {ver.version_id} - {timestamp_str}")
                        console.print(f"    Connections: {ver.total_connections}, Modules: {ver.total_modules}")
                        if ver.notes:
                            console.print(f"    Notes: [dim]{ver.notes}[/dim]")
                        console.print()

                    total_count = manager_ver.get_version_count()
                    if total_count > len(versions):
                        console.print(f"[dim]Showing {len(versions)} of {total_count} total versions[/dim]")
                        console.print(f"[dim]Use --limit to see more versions[/dim]")
                else:
                    console.print("[dim]No versions found.[/dim]")
                    console.print("[dim]Create a snapshot with: module graph-snapshot[/dim]")

            except Exception as e:
                console.print(f"[red]ERROR[/red] Failed to list versions: {e}")
                sys.exit(1)

        elif action.lower() == "graph-diff":
            # Compare two graph versions
            if not version1 or not version2:
                console.print("[red]ERROR[/red] Two version IDs required for graph-diff")
                console.print("[dim]Usage: module graph-diff --version1 <id> --version2 <id>[/dim]")
                sys.exit(1)

            from memory_tool.core.graph_versions import GraphVersionManager

            console.print(f"[cyan]Comparing graph versions {version1} → {version2}[/cyan]\n")

            manager_ver = GraphVersionManager()

            try:
                # Get version info
                v1 = manager_ver.get_version(version1)
                v2 = manager_ver.get_version(version2)

                if not v1:
                    console.print(f"[red]ERROR[/red] Version {version1} not found")
                    sys.exit(1)
                if not v2:
                    console.print(f"[red]ERROR[/red] Version {version2} not found")
                    sys.exit(1)

                # Show version details
                console.print(f"[dim]Version {version1}:[/dim] {v1.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                console.print(f"  Connections: {v1.total_connections}, Modules: {v1.total_modules}")
                console.print()
                console.print(f"[dim]Version {version2}:[/dim] {v2.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                console.print(f"  Connections: {v2.total_connections}, Modules: {v2.total_modules}")
                console.print()

                # Get diff
                diff = manager_ver.diff_versions(version1, version2)

                # Show changes
                if diff["added"]:
                    console.print(f"[green]Added connections ({len(diff['added'])}):[/green]")
                    for source, target in diff["added"][:10]:
                        console.print(f"  + {source} → {target}")
                    if len(diff["added"]) > 10:
                        console.print(f"  [dim]... and {len(diff['added']) - 10} more[/dim]")
                    console.print()

                if diff["removed"]:
                    console.print(f"[red]Removed connections ({len(diff['removed'])}):[/red]")
                    for source, target in diff["removed"][:10]:
                        console.print(f"  - {source} → {target}")
                    if len(diff["removed"]) > 10:
                        console.print(f"  [dim]... and {len(diff['removed']) - 10} more[/dim]")
                    console.print()

                if not diff["added"] and not diff["removed"]:
                    console.print("[dim]No changes between versions[/dim]")

                # Summary
                console.print(f"[dim]Summary: +{len(diff['added'])} -{len(diff['removed'])} ={len(diff['unchanged'])}[/dim]")

            except Exception as e:
                console.print(f"[red]ERROR[/red] Failed to compare versions: {e}")
                sys.exit(1)

        elif action.lower() == "unarchive":
            # Restore module from archive
            if not name:
                console.print("[red]ERROR[/red] Module name is required for unarchive")
                console.print("[dim]Usage: module unarchive <name>[/dim]")
                sys.exit(1)

            console.print(f"[cyan]Restoring module '{name}' from archive...[/cyan]")
            module_path = manager.unarchive(name)

            # Success
            rel_path = module_path.relative_to(Path.cwd())
            console.print(f"\n[green]OK[/green] Module restored: {name}")
            console.print(f"[dim]Location: {rel_path}[/dim]")

        elif action.lower() == "from-text":
            # AI-based module generation from text
            from memory_tool.core.ai_module_generator import AIModuleGenerator

            # Get input text
            input_text = None

            if text:
                input_text = text
            elif text_file:
                text_path = Path(text_file)
                if not text_path.exists():
                    console.print(f"[red]ERROR[/red] Text file not found: {text_file}")
                    sys.exit(1)
                input_text = text_path.read_text(encoding="utf-8")
            else:
                console.print("[red]ERROR[/red] Either --text or --text-file is required")
                console.print("[dim]Usage: module from-text --text \"Your text here\"[/dim]")
                console.print("[dim]   or: module from-text --text-file input.txt[/dim]")
                sys.exit(1)

            if not input_text.strip():
                console.print("[red]ERROR[/red] Input text is empty")
                sys.exit(1)

            # Check LLM availability
            if not LLMClient.check_availability():
                console.print("[red]ERROR[/red] LLM not configured")
                console.print("[dim]Set ANTHROPIC_API_KEY environment variable or configure Ollama[/dim]")
                sys.exit(1)

            # Validate structure type if provided
            structure_type = structure if structure else "auto"
            if structure_type not in ["feature", "topic", "auto"]:
                console.print(f"[red]ERROR[/red] Invalid structure type: {structure_type}")
                console.print("[dim]Valid values: 'feature', 'topic', 'auto'[/dim]")
                sys.exit(1)

            console.print("[cyan]Analyzing text and generating module structure...[/cyan]")
            if structure_type != "auto":
                structure_label = "Feature-based" if structure_type == "feature" else "Topic-based"
                console.print(f"[dim]Structure type: {structure_label} (forced)[/dim]")

            try:
                generator = AIModuleGenerator()
                output_lang = lang if lang else "auto"

                with console.status("[dim]Generating module (this may take a moment)...[/dim]"):
                    generated = generator.generate(input_text, language=output_lang, structure_type=structure_type)

                # Preview mode: show generated content
                if preview:
                    console.print()
                    preview_output = generator.format_preview(generated)
                    console.print(preview_output)
                    console.print()
                    console.print("[yellow]Preview mode:[/yellow] Module not saved")
                    console.print(f"[dim]To save, run without --preview flag[/dim]")
                else:
                    # Save mode: create module
                    module_path = generator.save_module(generated)
                    rel_path = module_path.relative_to(Path.cwd())

                    structure_label = "Feature-based" if generated.structure_type == "feature" else "Topic-based"
                    console.print(f"\n[green]OK[/green] Module created: {generated.name}")
                    console.print(f"[dim]Location: {rel_path}[/dim]")
                    console.print(f"[dim]Structure: {structure_label}[/dim]")
                    console.print(f"[dim]Type: {generated.module_type}[/dim]")

                    if generated.suggested_connections:
                        console.print(f"\n[cyan]Suggested connections:[/cyan]")
                        for conn in generated.suggested_connections:
                            console.print(f"  - [[{conn}]]")

                    console.print(f"\n[dim]Files created:[/dim]")
                    console.print(f"  - module.md      (module definition)")
                    console.print(f"  - current.md     (current status)")
                    console.print(f"  - decisions.md   (decisions)")
                    if generated.suggested_connections:
                        console.print(f"  - dependencies.md (dependencies)")

            except ValueError as e:
                console.print(f"[red]ERROR[/red] {e}")
                sys.exit(1)
            except Exception as e:
                console.print(f"[red]ERROR[/red] Module generation failed: {e}")
                sys.exit(1)

        else:
            console.print(f"[red]ERROR[/red] Unknown action: {action}")
            console.print("Valid actions: create, list, tree, archive, unarchive, connections, graph, rebuild-graph,")
            console.print("  check-links, suggest-links, suggest-ai, ai-organize, auto-tag, graph-snapshot,")
            console.print("  graph-history, graph-diff, from-text")
            sys.exit(1)

    except ModuleError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        sys.exit(1)


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
    # Safely convert Typer ArgumentInfo/OptionInfo to str/None
    scope = _arg_str(scope)
    output = _opt_str(output)
    module_name = _opt_str(module_name)
    lang = _opt_str(lang)

    # Check if LLM is available
    if not LLMClient.check_availability():
        console.print("[red]ERROR[/red] LLM not configured")
        console.print("[dim]Set ANTHROPIC_API_KEY environment variable or add 'llm.api_key' to config.yaml[/dim]")
        sys.exit(1)

    # Validation: --decisions requires --module
    if decisions and not module_name:
        console.print("[red]ERROR[/red] --decisions flag requires --module to be specified")
        console.print("[dim]Example: msummary --module project-management --decisions[/dim]")
        sys.exit(1)

    try:
        llm_client = LLMClient()

        # Module summarization
        if module_name:
            # Resolve module name
            resolved_module = _resolve_module_name(module_name)

            if decisions:
                # Decisions-only summarization
                if force:
                    console.print(f"[cyan]Summarizing decisions.md from '{resolved_module}' (force regeneration)...[/cyan]")
                else:
                    console.print(f"[cyan]Summarizing decisions.md from '{resolved_module}'...[/cyan]")

                module_path = Path.cwd() / ".memory" / "modules" / resolved_module
                decisions_file = module_path / "decisions.md"

                if not decisions_file.exists():
                    console.print(f"[red]ERROR[/red] decisions.md not found in module '{resolved_module}'")
                    sys.exit(1)

                # Read decisions content
                decisions_content = decisions_file.read_text(encoding="utf-8")

                # Create prompt for decisions summarization
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

                # Call LLM with smart caching
                import hashlib
                content_hash = hashlib.sha256(decisions_content.encode('utf-8')).hexdigest()[:16]
                # Replace slashes in module name for safe filename
                safe_module_name = resolved_module.replace('/', '_').replace('\\', '_')
                cache_key = f"decisions_{safe_module_name}_{content_hash}"

                if force:
                    # Force regeneration - skip cache
                    summary_text = llm_client.summarize(
                        content=prompt,
                        system_prompt="You are a technical analyst specializing in software project documentation."
                    )
                else:
                    # Check cache first
                    from pathlib import Path as PathlibPath
                    cache_dir = PathlibPath.cwd() / ".memory" / "summaries"
                    cache_file = cache_dir / f"{cache_key}.md"

                    if cache_file.exists():
                        console.print("[dim]Using cached summary (content unchanged)[/dim]")
                        summary_text = cache_file.read_text(encoding="utf-8")
                    else:
                        # Generate new summary
                        summary_text = llm_client.summarize(
                            content=prompt,
                            system_prompt="You are a technical analyst specializing in software project documentation."
                        )

                        # Save to cache
                        cache_dir.mkdir(parents=True, exist_ok=True)
                        cache_file.write_text(summary_text, encoding="utf-8")

            else:
                # Full module summarization
                if force:
                    console.print(f"[cyan]Summarizing module '{resolved_module}' (force regeneration)...[/cyan]")
                else:
                    console.print(f"[cyan]Summarizing module '{resolved_module}'...[/cyan]")

                summarizer = ModuleSummarizer(llm_client)
                module_path = Path.cwd() / ".memory" / "modules" / resolved_module

                summary_text = summarizer.summarize_module(
                    module_path, force=force, output_language=lang
                )

            # Display summary
            console.print("\n" + "="*80)
            console.print(summary_text)
            console.print("="*80)

            # Save to file if requested
            if output:
                output_path = Path(output)
                output_path.write_text(summary_text, encoding="utf-8")
                console.print(f"\n[green]OK[/green] Summary saved to: {output}")

            return

        # Timeline summarization
        from datetime import datetime

        summarizer = TimelineSummarizer(llm_client)

        # Parse scope
        force_msg = " (force regeneration)" if force else ""
        if scope.lower() == "today":
            console.print(f"[cyan]Summarizing today's timeline{force_msg}...[/cyan]")
            summary_text = summarizer.summarize_today(output_language=lang, force=force)

        elif scope.lower() == "week":
            console.print(f"[cyan]Summarizing this week's timeline{force_msg}...[/cyan]")
            summary_text = summarizer.summarize_week(output_language=lang, force=force)

        elif ":" in scope:
            # Date range: YYYY-MM-DD:YYYY-MM-DD
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
            # Specific date: YYYY-MM-DD
            try:
                target_date = datetime.strptime(scope, "%Y-%m-%d").date()
                console.print(f"[cyan]Summarizing timeline for {target_date}{force_msg}...[/cyan]")
                summary_text = summarizer.summarize_date(target_date, output_language=lang, force=force)

            except ValueError:
                console.print(f"[red]ERROR[/red] Invalid date format: {scope}")
                console.print("[dim]Use YYYY-MM-DD format (e.g., 2025-11-14)[/dim]")
                sys.exit(1)

        # Display summary
        console.print("\n" + "="*80)
        console.print(summary_text)
        console.print("="*80)

        # Save to file if requested
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
def index(
    check: bool = typer.Option(False, "--check", help="Check index status"),
    stats: bool = typer.Option(False, "--stats", help="Show index statistics"),
    force: bool = typer.Option(False, "--force", "-f", help="Force full reindex"),
    optimize: bool = typer.Option(False, "--optimize", help="Optimize index for better performance"),
    vacuum: bool = typer.Option(False, "--vacuum", help="Vacuum database to reclaim space"),
):
    """Manage SQLite search index."""
    try:
        from memory_tool.db import IndexManager

        memory_path = Path.cwd() / ".memory"

        if not memory_path.exists():
            console.print("[red]ERROR[/red] .memory/ not found. Run 'minit' first.")
            sys.exit(1)

        # Check SQLite availability
        if not IndexManager.available():
            console.print("[red]ERROR[/red] SQLite with FTS5 not available")
            console.print("Indexing requires SQLite 3.9.0+ with FTS5 support")
            sys.exit(1)

        indexer = IndexManager(memory_path)

        # Check mode
        if check:
            is_fresh = indexer.is_index_fresh()
            if is_fresh:
                console.print("[green]Index is up to date[/green]")
            else:
                console.print("[yellow]Index is stale or missing[/yellow]")
                console.print("Run 'mindex' to rebuild")
            return

        # Stats mode
        if stats:
            stats_data = indexer.get_stats()
            if stats_data["status"] == "not_created":
                console.print("[yellow]Index not created yet[/yellow]")
                console.print("Run 'mindex' to create index")
            else:
                console.print(f"[green]Index Status: OK[/green]")
                console.print(f"Total entries: {stats_data['total_entries']}")
                console.print(f"Size: {stats_data['size_mb']} MB")
                console.print("\nEntries by type:")
                for entry_type, count in stats_data['by_type'].items():
                    console.print(f"  {entry_type}: {count}")
            return

        # Optimize mode
        if optimize or vacuum:
            from memory_tool.search import IndexOptimizer

            db_path = memory_path / ".index" / "search.db"
            if not db_path.exists():
                console.print("[red]ERROR[/red] Index database not found")
                console.print("Run 'mindex' to create index first")
                sys.exit(1)

            optimizer = IndexOptimizer(db_path)

            if optimize and vacuum:
                # Full optimization
                console.print("Running full optimization...")
                result = optimizer.full_optimize()

                if result.get("overall_success"):
                    console.print("[green]Optimization complete![/green]")

                    # Show FTS5 results
                    fts_result = result.get("fts5_optimize", {})
                    if fts_result.get("success"):
                        console.print(f"  FTS5: {fts_result.get('entries_indexed', 0)} entries optimized")

                    # Show vacuum results
                    vacuum_result = result.get("vacuum", {})
                    if vacuum_result.get("success"):
                        reduced_mb = vacuum_result.get("size_reduced_mb", 0)
                        percent = vacuum_result.get("percent_reduced", 0)
                        console.print(f"  Vacuum: {reduced_mb:.2f} MB reclaimed ({percent:.1f}%)")
                else:
                    console.print("[yellow]Optimization completed with errors[/yellow]")
                    for key, res in result.items():
                        if res.get("error"):
                            console.print(f"  {key}: {res['error']}")

            elif optimize:
                # FTS5 optimize only
                console.print("Optimizing FTS5 index...")
                result = optimizer.optimize_fts5()

                if result.get("success"):
                    console.print(f"[green]OK[/green] {result.get('message')}")
                    console.print(f"  Entries: {result.get('entries_indexed', 0)}")
                else:
                    console.print(f"[red]ERROR[/red] {result.get('error')}")
                    sys.exit(1)

            elif vacuum:
                # Vacuum only
                console.print("Vacuuming database...")
                result = optimizer.vacuum_database()

                if result.get("success"):
                    reduced_mb = result.get("size_reduced_mb", 0)
                    percent = result.get("percent_reduced", 0)
                    console.print(f"[green]OK[/green] {reduced_mb:.2f} MB reclaimed ({percent:.1f}%)")
                    console.print(f"  Before: {result.get('size_before_mb', 0):.2f} MB")
                    console.print(f"  After: {result.get('size_after_mb', 0):.2f} MB")
                else:
                    console.print(f"[red]ERROR[/red] {result.get('error')}")
                    sys.exit(1)

            return

        # Reindex mode
        console.print("Indexing .memory/ content...")

        # Always ensure database exists
        if not indexer.index_path.exists():
            console.print("Creating database...")
            indexer.create_database()
        elif force:
            console.print("Force rebuilding database...")
            indexer.create_database()

        with console.status("[bold green]Indexing files..."):
            total_entries = indexer.index_all(exclude_archive=True)

        console.print(f"[green]Indexed {total_entries} entries[/green]")
        console.print(f"Index location: {indexer.index_path}")

    except ImportError:
        console.print("[red]ERROR[/red] SQLite indexing module not available")
        console.print("This feature requires the db module")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]ERROR[/red] Indexing failed: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@app.command()
def archive(
    target: str = typer.Argument(..., help="Target: 'decisions', 'current', 'plans'"),
    phase: int = typer.Option(None, "--phase", help="Phase number to archive (backwards compat)"),
    up_to: int = typer.Option(None, "--up-to", help="Archive decisions up to this number (e.g., 25 = #1-#25)"),
    keep_recent: int = typer.Option(None, "--keep-recent", help="Keep only N most recent decisions"),
    older_than: Optional[str] = typer.Option(None, "--older-than", help="Archive decisions older than duration (e.g., 6m, 1y, 180d)"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactively select decisions to archive"),
    suggest: bool = typer.Option(False, "--suggest", help="Suggest what to archive (does not archive)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be archived without doing it"),
    module_name: Optional[str] = typer.Option(None, "--module", "-m", help="Module name or path (default: memory-system)"),
):
    """Archive completed documentation (marchive command).

    Examples:
        marchive decisions                              # Keep recent 10 (default)
        marchive decisions --keep-recent 15             # Keep recent 15
        marchive decisions --up-to 25                   # Archive #1-25
        marchive decisions --older-than 6m              # Archive older than 6 months
        marchive decisions --older-than 1y              # Archive older than 1 year
        marchive decisions --interactive                # Interactively select decisions
        marchive decisions --suggest                    # Show suggestions (no archive)
        marchive decisions --phase 5                    # Archive Phase 1-5 (old style)
        marchive current --phase 5                      # Archive Phase 5 current.md
        marchive plans                                  # Move PLAN-*.md to archive
        marchive decisions --dry-run                    # Preview
        marchive decisions --module projects/website    # Archive for specific module
    """
    # Safely convert Typer OptionInfo to str/None
    older_than = _opt_str(older_than)
    module_name = _opt_str(module_name)

    try:
        from memory_tool.core.archiver import Archiver, ArchiverError
        from memory_tool.utils.config import Config

        # Resolve module name if provided
        resolved_module = _resolve_module_name(module_name)

        archiver = Archiver(module_name=resolved_module)

        if target == "decisions":
            # Special case: --suggest mode
            if suggest:
                try:
                    result = archiver.suggest_archive()
                    console.print(result['summary'])

                    if result['archive_count'] > 0:
                        console.print("\n[dim]To archive these decisions:[/dim]")
                        console.print(f"[dim]  marchive decisions --older-than 6m[/dim]")
                        console.print(f"[dim]  marchive decisions --interactive[/dim]")
                except ArchiverError as e:
                    console.print(f"[red]ERROR[/red] {e}")
                    sys.exit(1)
                return

            # Special case: --interactive mode
            if interactive:
                try:
                    archive_path, num_archived = archiver.archive_decisions_interactive(
                        age_threshold_months=6,
                        dry_run=dry_run
                    )
                    if not dry_run:
                        console.print(f"\n[dim]Backup: decisions.md.bak[/dim]")
                except ArchiverError as e:
                    console.print(f"[red]ERROR[/red] {e}")
                    sys.exit(1)
                return

            # Validate mutually exclusive options
            options_provided = sum([
                phase is not None,
                up_to is not None,
                keep_recent is not None,
                older_than is not None
            ])

            if options_provided > 1:
                console.print("[red]ERROR[/red] Only one of --phase, --up-to, --keep-recent, or --older-than can be specified")
                sys.exit(1)

            # Determine which mode to use
            if phase is not None:
                # Mode: Phase-based (backwards compat)
                mode = "phase"
                value = phase
            elif up_to is not None:
                # Mode: Decision number-based
                mode = "up-to"
                value = up_to
            elif older_than is not None:
                # Mode: Date-based (NEW)
                mode = "older-than"
                value = older_than
            else:
                # Mode: Keep recent (default or explicit)
                mode = "keep-recent"
                if keep_recent is None:
                    # Use default from config
                    config = Config()
                    value = config.get("modules.archive_keep_recent", 10)
                else:
                    value = keep_recent

            try:
                # Call appropriate archiver method
                if mode == "phase":
                    archive_path, num_archived = archiver.archive_decisions(value, dry_run)
                elif mode == "up-to":
                    archive_path, num_archived = archiver.archive_decisions_by_number(value, dry_run)
                elif mode == "older-than":
                    archive_path, num_archived = archiver.archive_decisions_by_date(value, dry_run)
                else:  # keep-recent
                    archive_path, num_archived = archiver.archive_decisions_by_count(value, dry_run)

                if dry_run:
                    console.print(f"[cyan]Would archive {num_archived} decisions to:[/cyan]")
                    console.print(f"  {archive_path.relative_to(Path.cwd())}")
                    console.print(f"\n[dim]Mode: {mode}={value}[/dim]")
                else:
                    console.print(f"[green]OK[/green] Archived {num_archived} decisions")
                    console.print(f"  → {archive_path.relative_to(Path.cwd())}")
                    console.print(f"\n[dim]Backup: decisions.md.bak[/dim]")

            except ArchiverError as e:
                console.print(f"[red]ERROR[/red] {e}")
                sys.exit(1)

        elif target == "current":
            # Archive current.md
            if not phase:
                console.print("[red]ERROR[/red] --phase required for current")
                console.print("[dim]Example: marchive current --phase 5[/dim]")
                sys.exit(1)

            try:
                archive_path = archiver.archive_current(phase, dry_run)

                if dry_run:
                    console.print(f"[cyan]Would archive current.md to:[/cyan]")
                    console.print(f"  {archive_path.relative_to(Path.cwd())}")
                else:
                    console.print(f"[green]OK[/green] Archived current.md")
                    console.print(f"  → {archive_path.relative_to(Path.cwd())}")
                    console.print(f"\n[dim]Backup: current.md.bak[/dim]")

            except ArchiverError as e:
                console.print(f"[red]ERROR[/red] {e}")
                sys.exit(1)

        elif target == "plans":
            # Archive PLAN files
            try:
                archived_files = archiver.archive_plans(dry_run)

                if not archived_files:
                    console.print("[yellow]No PLAN-*.md files found to archive[/yellow]")
                    return

                if dry_run:
                    console.print(f"[cyan]Would move {len(archived_files)} PLAN file(s) to archive/plans/:[/cyan]")
                    for f in archived_files:
                        console.print(f"  - {f.name}")
                else:
                    console.print(f"[green]OK[/green] Moved {len(archived_files)} PLAN file(s) to archive/plans/")
                    for f in archived_files:
                        console.print(f"  - {f.name}")

            except ArchiverError as e:
                console.print(f"[red]ERROR[/red] {e}")
                sys.exit(1)

        else:
            console.print(f"[red]ERROR[/red] Unknown target: {target}")
            console.print("[dim]Valid targets: decisions, current, plans[/dim]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]ERROR[/red] Unexpected error: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
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
                console.print(f"  → {installed_path}")

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
def browse(
    query: str = typer.Argument(None, help="Initial search query"),
    mode: str = typer.Option("search", "--mode", "-m", help="Initial mode: search, timeline, modules, graph"),
):
    """Interactive TUI browser (mbrowse command).

    Launch an enhanced terminal interface with multiple modes:
    - Search: Interactive search with filters
    - Timeline: Date-based timeline explorer
    - Modules: Hierarchical module browser
    - Graph: Module connection graph viewer

    Keybindings:
        Tab: Switch between modes
        /: Focus search (in search mode)
        Enter: Show details
        Esc: Close details
        q: Quit application
        j/k: Navigate (Vim-style)
        n/p: Next/Previous (in timeline)
        r: Refresh
        ?: Help

    Examples:
        mbrowse                       # Launch browser (search mode)
        mbrowse "search query"        # Launch with query
        mbrowse --mode timeline       # Launch in timeline mode
        mbrowse --mode graph          # Launch in graph mode
    """
    try:
        # Check if textual is available
        try:
            from memory_tool.tui import run_browser
        except ImportError:
            console.print("[red]ERROR[/red] TUI feature not available")
            console.print("Install with: pip install memory-tool[tui]")
            console.print("Or: pip install textual>=0.47.0")
            sys.exit(1)

        memory_path = Path.cwd() / ".memory"

        if not memory_path.exists():
            console.print("[red]ERROR[/red] .memory/ not found. Run 'minit' first.")
            sys.exit(1)

        # Validate mode
        valid_modes = ["search", "timeline", "modules", "graph"]
        if mode not in valid_modes:
            console.print(f"[red]ERROR[/red] Invalid mode: {mode}")
            console.print(f"Valid modes: {', '.join(valid_modes)}")
            sys.exit(1)

        # Launch enhanced TUI browser
        run_browser(base_path=Path.cwd(), mode=mode, query=query)

    except KeyboardInterrupt:
        console.print("\n[yellow]Browser closed[/yellow]")
    except Exception as e:
        console.print(f"[red]ERROR[/red] Browser failed: {e}")
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
        mplan daily add "Task"   # Add task to today
        mplan daily done "Task"  # Mark task as done

        mplan weekly             # Show this week's plan
        mplan weekly add "Goal"  # Add goal to this week

        mplan monthly            # Show this month's plan

        mplan module core-system              # Show module plan
        mplan module core-system add "Task"   # Add to sprint (default)
        mplan module core-system add "Task" --section backlog
        mplan module core-system done "Task"
    """
    # Safely convert Typer OptionInfo to str/None
    due_date = _opt_str(due_date)

    try:
        from memory_tool.planner import (
            PlanManager, Task, TaskStatus,
            DailyPlan, WeeklyPlan, MonthlyPlan, ModulePlan
        )
        from datetime import datetime
        import subprocess
        import os

        memory_path = Path.cwd() / ".memory"

        if not memory_path.exists():
            console.print("[red]ERROR[/red] .memory/ not found. Run 'minit' first.")
            sys.exit(1)

        # Handle time-based plans (daily/weekly/monthly/module)
        if action in ["daily", "weekly", "monthly", "module"]:
            if action == "daily":
                plan_mgr = DailyPlan(base_path=memory_path)

                if name is None or name == "show":
                    # Show today's plan
                    content = plan_mgr.show_plan()
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

                else:
                    # Try to create plan and open editor
                    plan_path = plan_mgr.create_plan()
                    console.print(f"[green]OK[/green] Daily plan ready")
                    console.print(f"  → {plan_path.relative_to(Path.cwd())}")

                    # Open in editor if name is not a command
                    editor = os.environ.get('EDITOR')
                    if editor:
                        subprocess.run([editor, str(plan_path)])

                    return

            elif action == "weekly":
                plan_mgr = WeeklyPlan(base_path=memory_path)

                if name is None or name == "show":
                    # Show this week's plan or specific week
                    week_id = title if title else None
                    content = plan_mgr.show_plan(week_id)
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

                else:
                    # Create plan and open editor
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
                    # Show this month's plan or specific month
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
                    # Create plan and open editor
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

                # Check if title is a sub-command
                sub_action = title if title in ["add", "done", "show"] else "show"

                if sub_action == "show" or title is None:
                    # Show module plan
                    content = plan_mgr.show_plan(name)
                    console.print(content)

                elif sub_action == "add":
                    # For add, we need another argument (the actual task)
                    # This is a limitation - we'll use description option instead
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
                    # Create/show plan
                    plan_path = plan_mgr.create_plan(name)
                    console.print(f"[green]OK[/green] Module plan ready: {name}")
                    console.print(f"  → {plan_path.relative_to(Path.cwd())}")

                    editor = os.environ.get('EDITOR')
                    if editor:
                        subprocess.run([editor, str(plan_path)])

            return

        # Handle project plans (original functionality)
        manager = PlanManager(base_path=memory_path)

        # Action: create
        if action == "create":
            if not name:
                console.print("[red]ERROR[/red] Plan name required")
                console.print("[dim]Usage: mplan create <name> [options][/dim]")
                sys.exit(1)

            # Parse due date
            due = None
            if due_date:
                try:
                    due = datetime.strptime(due_date, "%Y-%m-%d").date()
                except ValueError:
                    console.print(f"[red]ERROR[/red] Invalid date format: {due_date}")
                    console.print("[dim]Use YYYY-MM-DD format[/dim]")
                    sys.exit(1)

            # Create plan
            plan_obj = manager.create_plan(
                name=name,
                description=description,
                due_date=due,
                tags=tags
            )

            # Save plan
            filepath = manager.save_plan(plan_obj)
            console.print(f"[green]OK[/green] Plan created:")
            console.print(f"  → {filepath.relative_to(Path.cwd())}")

        # Action: list
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

        # Action: show
        elif action == "show":
            if not name:
                console.print("[red]ERROR[/red] Plan name required")
                console.print("[dim]Usage: mplan show <name>[/dim]")
                sys.exit(1)

            # Find plan file
            plans = manager.list_plans()
            plan_file = None
            for plan_info in plans:
                if plan_info['name'].lower() == name.lower():
                    plan_file = plan_info['filename']
                    break

            if not plan_file:
                console.print(f"[red]ERROR[/red] Plan not found: {name}")
                sys.exit(1)

            # Load and display plan
            plan_obj = manager.load_plan(plan_file)
            console.print(plan_obj.to_markdown())

        # Action: add
        elif action == "add":
            if not name or not title:
                console.print("[red]ERROR[/red] Plan name and task title required")
                console.print("[dim]Usage: mplan add <plan-name> <task-title>[/dim]")
                sys.exit(1)

            # Find plan file
            plans = manager.list_plans()
            plan_file = None
            for plan_info in plans:
                if plan_info['name'].lower() == name.lower():
                    plan_file = plan_info['filename']
                    break

            if not plan_file:
                console.print(f"[red]ERROR[/red] Plan not found: {name}")
                sys.exit(1)

            # Load plan
            plan_obj = manager.load_plan(plan_file)

            # Add task
            task = Task(title=title, tags=tags)
            plan_obj.add_task(task)

            # Save plan
            manager.save_plan(plan_obj, filename=plan_file)
            console.print(f"[green]OK[/green] Task added to '{plan_obj.name}'")
            console.print(f"  - [ ] {title}")

        # Action: done
        elif action == "done":
            if not name or not title:
                console.print("[red]ERROR[/red] Plan name and task title required")
                console.print("[dim]Usage: mplan done <plan-name> <task-title>[/dim]")
                sys.exit(1)

            # Find plan file
            plans = manager.list_plans()
            plan_file = None
            for plan_info in plans:
                if plan_info['name'].lower() == name.lower():
                    plan_file = plan_info['filename']
                    break

            if not plan_file:
                console.print(f"[red]ERROR[/red] Plan not found: {name}")
                sys.exit(1)

            # Load plan
            plan_obj = manager.load_plan(plan_file)

            # Find and mark task as done
            task_found = False
            for task in plan_obj.tasks:
                if task.title.lower() == title.lower():
                    task.mark_completed()
                    task_found = True
                    break

            if not task_found:
                console.print(f"[red]ERROR[/red] Task not found: {title}")
                sys.exit(1)

            # Save plan
            manager.save_plan(plan_obj, filename=plan_file)
            console.print(f"[green]OK[/green] Task completed in '{plan_obj.name}'")
            console.print(f"  - [x] {title}")

        # Action: delete
        elif action == "delete":
            if not name:
                console.print("[red]ERROR[/red] Plan name required")
                console.print("[dim]Usage: mplan delete <name>[/dim]")
                sys.exit(1)

            # Find plan file
            plans = manager.list_plans()
            plan_file = None
            for plan_info in plans:
                if plan_info['name'].lower() == name.lower():
                    plan_file = plan_info['filename']
                    break

            if not plan_file:
                console.print(f"[red]ERROR[/red] Plan not found: {name}")
                sys.exit(1)

            # Delete plan
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
        mhooks install document-health  # Install document health check hook ⭐
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
            console.print(f"  [cyan]→[/cyan] [dim]{dest.relative_to(migrator.timeline_path)}[/dim]\n")

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

        # Validate period
        if period.lower() not in ["weekly", "monthly"]:
            console.print(f"[red]ERROR[/red] Invalid period: {period}")
            console.print("[dim]Valid periods: weekly, monthly[/dim]")
            sys.exit(1)

        # Action: show
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

                # Display review content
                content = review_file.read_text(encoding="utf-8")
                console.print(content)

            else:  # monthly
                # Parse month/year if provided
                month = None
                year = None
                if identifier:
                    try:
                        month = int(identifier)
                        if month < 1 or month > 12:
                            console.print(f"[red]ERROR[/red] Invalid month: {month}")
                            console.print("[dim]Month must be between 1 and 12[/dim]")
                            sys.exit(1)
                    except ValueError:
                        console.print(f"[red]ERROR[/red] Invalid month format: {identifier}")
                        console.print("[dim]Use numeric month (1-12)[/dim]")
                        sys.exit(1)

                review_file = manager.get_monthly_review(month=month, year=year)

                if not review_file:
                    if identifier:
                        console.print(f"[yellow]![/yellow] Monthly review not found: {identifier}")
                    else:
                        console.print("[yellow]![/yellow] No review for this month yet")
                        console.print("[dim]Create one with: mreview monthly[/dim]")
                    sys.exit(1)

                # Display review content
                content = review_file.read_text(encoding="utf-8")
                console.print(content)

        # Action: create (default)
        else:
            if period.lower() == "weekly":
                console.print("[cyan]Creating weekly review...[/cyan]")
                review_file = manager.create_weekly_review()

                week_id = manager.weekly.get_week_id()
                console.print(f"[green]OK[/green] Weekly review created: {week_id}")
                console.print(f"  → {review_file.relative_to(Path.cwd())}")

            else:  # monthly
                console.print("[cyan]Creating monthly review...[/cyan]")
                review_file = manager.create_monthly_review()

                from datetime import datetime
                month_name = datetime.now().strftime("%B %Y")
                console.print(f"[green]OK[/green] Monthly review created: {month_name}")
                console.print(f"  → {review_file.relative_to(Path.cwd())}")

            # Open in editor if requested
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


@app.command()
def map(
    path: str = typer.Argument(
        ".",
        help="Path to analyze (file or directory)",
    ),
    depth: str = typer.Option(
        "structure",
        "--depth",
        "-d",
        help="Output depth: overview, structure (default), api, docs",
    ),
    private: bool = typer.Option(
        False,
        "--private",
        "-p",
        help="Include private symbols (_name)",
    ),
    tests: bool = typer.Option(
        False,
        "--tests",
        "-t",
        help="Include test files",
    ),
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Write output to file instead of stdout",
    ),
    interface: str = typer.Option(
        None,
        "--interface",
        "-i",
        help="Generate interface.md for specified module",
    ),
):
    """Generate code map from Python source files (mmap command).

    Analyzes Python source code using AST and outputs structure information.

    Depth levels:
    - overview:  Class names with docstrings
    - structure: + Method names (default)
    - api:       + Full type signatures
    - docs:      + Method docstrings

    Examples:
        mmap                           # Current directory, structure depth
        mmap src/                      # Specific directory
        mmap --depth=api               # Full signatures
        mmap --private                 # Include private symbols
        mmap -o code-map.md            # Write to file
        mmap --interface=core-engine   # Generate interface.md for module
    """
    from memory_tool.codemap import (
        PythonParser,
        CodeMapFormatter,
        DepthLevel,
    )

    try:
        target_path = Path(path).resolve()

        if not target_path.exists():
            console.print(f"[red]ERROR[/red] Path not found: {path}")
            sys.exit(1)

        # Validate depth
        valid_depths = ["overview", "structure", "api", "docs"]
        if depth not in valid_depths:
            console.print(f"[red]ERROR[/red] Invalid depth: {depth}")
            console.print(f"[dim]Valid depths: {', '.join(valid_depths)}[/dim]")
            sys.exit(1)

        # Check for Python files
        if target_path.is_file():
            if not target_path.suffix == ".py":
                console.print(f"[yellow]![/yellow] Not a Python file: {path}")
                console.print("[dim]mmap currently supports Python only.[/dim]")
                sys.exit(1)
        else:
            # Check if directory has Python files
            py_files = list(target_path.rglob("*.py"))
            if not py_files:
                # Check what file types exist
                all_files = list(target_path.rglob("*"))
                # Filter to valid extensions (alphanumeric only, max 10 chars)
                extensions = set(
                    f.suffix for f in all_files
                    if f.is_file() and f.suffix
                    and len(f.suffix) <= 10
                    and f.suffix[1:].replace("_", "").isalnum()
                )
                console.print(f"[yellow]![/yellow] No Python files found in: {path}")
                if extensions:
                    console.print(f"[dim]Found file types: {', '.join(sorted(extensions))}[/dim]")
                console.print("[dim]mmap currently supports Python only.[/dim]")
                console.print("[dim]Alternatives: Use 'ctags' for multi-language support[/dim]")
                sys.exit(1)

        # Parse
        parser = PythonParser(
            include_tests=tests,
            include_private=private,
        )

        base_path = Path.cwd()

        if target_path.is_file():
            module = parser.parse_file(target_path)
            if module:
                try:
                    module.path = target_path.relative_to(base_path)
                except ValueError:
                    module.path = target_path

                from memory_tool.codemap.models import CodeMap
                codemap = CodeMap(root_path=base_path, modules=[module])
            else:
                console.print(f"[red]ERROR[/red] Failed to parse: {path}")
                sys.exit(1)
        else:
            codemap = parser.parse_directory(target_path, relative_to=base_path)

        if not codemap.modules:
            console.print("[yellow]![/yellow] No public symbols found.")
            sys.exit(0)

        # Generate interface.md for module
        if interface:
            memory_path = Path.cwd() / ".memory"
            if not memory_path.exists():
                console.print("[red]ERROR[/red] .memory/ not found. Run 'minit' first.")
                sys.exit(1)

            module_name = _resolve_module_name(interface)
            module_path = memory_path / "modules" / module_name

            if not module_path.exists():
                console.print(f"[red]ERROR[/red] Module not found: {module_name}")
                sys.exit(1)

            # Generate interface content
            formatter = CodeMapFormatter(
                depth=DepthLevel.API,
                include_private=private,
            )
            interface_content = formatter.format_for_interface(codemap)

            # Write to interface.md
            interface_file = module_path / "interface.md"
            interface_file.write_text(interface_content, encoding="utf-8")

            console.print(f"[green]OK[/green] Generated interface.md for {module_name}")
            console.print(f"  → {interface_file.relative_to(Path.cwd())}")
            return

        # Format output
        formatter = CodeMapFormatter(
            depth=DepthLevel(depth),
            include_private=private,
        )
        result = formatter.format(codemap)

        # Output
        if output:
            output_path = Path(output)
            output_path.write_text(result, encoding="utf-8")
            console.print(f"[green]OK[/green] Code map written to: {output}")
        else:
            console.print(result)

    except Exception as e:
        console.print(f"[red]ERROR[/red] {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


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

    if ctx.invoked_subcommand is None:
        console.print(
            Panel.fit(
                "[bold cyan]Memory Tool[/bold cyan]\n\n"
                "Time-Space Integrated Knowledge System\n"
                "For Claude Code integration\n\n"
                "[dim]Use --help to see available commands[/dim]",
                border_style="cyan",
            )
        )


@app.command(name="nm")
def notion_message(
    message: str = typer.Argument(..., help="Message to append to Notion page"),
    page_id: str = typer.Option(None, "--page", "-p", help="Target page ID (optional)"),
):
    """Append text to a Notion page (nm command)."""
    try:
        from datetime import datetime
        client = NotionClient()
        now = datetime.now()
        
        if page_id:
            # Direct append to specific page
            target_id = page_id
            client.append_text(target_id, message)
            console.print(f"[green]OK[/green] Appended to Notion page")
            console.print(f"[dim]-> Page: {target_id}[/dim]")
        else:
            # Auto-daily mode (Root -> Month -> Day)
            if not client.default_page_id:
                console.print("[red]ERROR[/red] Default page ID not configured in config.yaml")
                sys.exit(1)
                
            console.print("[dim]Locating daily page...[/dim]")
            target_id = client.get_or_create_daily_page(now)
            
            time_str = now.strftime("%H:%M")
            client.append_timeline_entry(target_id, time_str, message)
            
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
        from datetime import datetime
        client = NotionClient()
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        
        console.print(f"[cyan]{date_str} Notion Timeline:[/cyan]\n")
        
        # We reuse get_or_create to find the ID easily (it caches too)
        # If it creates an empty page, that's fine/expected behavior for 'today'
        target_id = client.get_or_create_daily_page(now)
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
        from datetime import datetime, timedelta
        client = NotionClient()
        today = datetime.now()
        
        # Calculate Monday
        start_of_week = today - timedelta(days=today.weekday())
        
        console.print(f"[cyan]Notion Timeline (Week of {start_of_week.strftime('%Y-%m-%d')}):[/cyan]\n")
        
        found_any = False
        
        # Loop from Monday to Today
        for i in range((today - start_of_week).days + 1):
            current_date = start_of_week + timedelta(days=i)
            date_str = current_date.strftime("%Y-%m-%d")
            
            # Using cache to find ID without API call if possible
            # Note: get_or_create_daily_page might do API calls if not cached.
            # For 'week' view, maybe we should only check cache or use search?
            # But consistent structure suggests we check existence.
            # To be safe/fast, we rely on cache primarily.
            
            # We use get_or_create because if we are checking the week,
            # ensuring the pages exist is consistent with 'mweek' behavior logic
            # (though mweek reads files).
            # Limitation: This might take a few seconds for 5-7 days if not cached.
            page_id = client.get_or_create_daily_page(current_date)
            content = client.get_page_content(page_id)
            
            if content.strip():
                found_any = True
                console.print(f"[bold]{date_str}[/bold]")
                console.print(content)
                console.print("") # Separator
        
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
                # Highlight the query
                highlighted = line.replace(query, f"[yellow]{query}[/yellow]")
                console.print(f"  {highlighted}")
            console.print()
            
    except NotionError as e:
        console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)


@app.command(name="nsync")
def notion_sync(
    module: str = typer.Argument(None, help="Module path to sync (optional)"),
    push: bool = typer.Option(False, "--push", "-p", help="Only push local changes to Notion"),
    pull: bool = typer.Option(False, "--pull", "-l", help="Only pull Notion changes to local"),
    force: bool = typer.Option(False, "--force", "-f", help="Force sync regardless of timestamps"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would happen without syncing"),
    status: bool = typer.Option(False, "--status", "-s", help="Show sync status"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Bidirectional sync with Notion (nsync command).

    Syncs local modules with Notion pages. Configure targets in config.yaml.

    Examples:
        nsync                    # Sync all configured targets
        nsync projects/my-mod    # Sync specific module
        nsync --push             # Only push local to Notion
        nsync --pull             # Only pull Notion to local
        nsync --dry-run          # Preview changes
        nsync --status           # Show sync status
    """
    try:
        from memory_tool.notion.sync import ModuleSyncer, NotionSyncError

        syncer = ModuleSyncer()

        # Check if sync is enabled
        if not syncer.sync_config.enabled:
            console.print("[yellow]Notion sync is not enabled.[/yellow]")
            console.print("[dim]Enable it in config.yaml: notion.sync.enabled: true[/dim]")
            return

        # Status mode
        if status:
            status_info = syncer.get_status(module)

            last_sync = status_info.get("last_full_sync")
            if last_sync:
                console.print(f"[cyan]Last full sync:[/cyan] {last_sync}")
            else:
                console.print("[dim]No sync history yet[/dim]")
            console.print()

            for mod_path, mod_status in status_info.get("modules", {}).items():
                console.print(f"[bold]{mod_path}[/bold]")

                if mod_status.get("last_sync"):
                    console.print(f"  Last sync: {mod_status['last_sync']}")

                to_push = mod_status.get("to_push", [])
                to_pull = mod_status.get("to_pull", [])
                in_sync = mod_status.get("in_sync", [])
                conflicts = mod_status.get("conflicts", [])

                if to_push:
                    console.print(f"  [green]To push:[/green] {', '.join(to_push)}")
                if to_pull:
                    console.print(f"  [blue]To pull:[/blue] {', '.join(to_pull)}")
                if conflicts:
                    console.print(f"  [red]Conflicts:[/red] {', '.join(conflicts)}")
                if in_sync and verbose:
                    console.print(f"  [dim]In sync:[/dim] {', '.join(in_sync)}")
                if not to_push and not to_pull and not conflicts:
                    console.print("  [dim]All in sync[/dim]")
                console.print()
            return

        # Sync mode
        if dry_run:
            console.print("[cyan]Dry run - showing what would happen:[/cyan]\n")
        else:
            console.print("[cyan]Syncing with Notion...[/cyan]\n")

        summary = syncer.sync(
            module_path=module,
            push_only=push,
            pull_only=pull,
            force=force,
            dry_run=dry_run,
        )

        # Display results
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

        console.print()
        console.print(f"[cyan]{summary}[/cyan]")

    except NotionSyncError as e:
        console.print(f"[red]Sync Error:[/red] {e}")
        sys.exit(1)
    except NotionError as e:
        console.print(f"[red]Notion Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


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

