"""Search-related CLI commands."""

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import typer

from memory_tool.commands.common import (
    app, console, sanitize_output, opt_str, arg_str, resolve_module_name
)
from memory_tool.core.search import MemorySearcher, SearchError
from memory_tool.utils.path_checker import PathChecker, format_check_result
from memory_tool.utils.config import Config
from memory_tool.search.filters import TagCollector
from memory_tool.search.formatter import deduplicate_results


@app.command(
    epilog="For detailed help: [bold]mhelp search[/bold]"
)
def search(
    query: str = typer.Argument(..., help="Search query (keyword, regex, or semantic)"),
    with_kb: bool = typer.Option(False, "--with-kb", help="Include personal KB"),
    all: bool = typer.Option(False, "--all", help="Search all projects"),
    case_sensitive: bool = typer.Option(False, "--case", "-c", help="Case sensitive search"),
    no_context: bool = typer.Option(False, "--no-context", help="Hide context lines"),
    max_results: int = typer.Option(None, "--max", "-n", help="Maximum results"),
    from_date: Optional[str] = typer.Option(None, "--from", help="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = typer.Option(None, "--to", help="End date (YYYY-MM-DD)"),
    semantic: bool = typer.Option(False, "--semantic", "-s", help="Semantic search using embeddings"),
    threshold: Optional[float] = typer.Option(None, "--threshold", "-t", help="Similarity threshold (0-1, default from config: 0.5)"),
    no_index: bool = typer.Option(False, "--no-index", help="Force file-based search (skip SQLite index)"),
    rank: Optional[str] = typer.Option(None, "--rank", help="Ranking algorithm: bm25 (default: none)"),
    boost_recent: bool = typer.Option(False, "--boost-recent", help="Boost recent results"),
    decay_days: int = typer.Option(30, "--decay-days", help="Date decay days (for --boost-recent)"),
    date: Optional[str] = typer.Option(None, "--date", help="Date expression: today, yesterday, this-week, last-N-days, YYYY-MM-DD"),
    file_type: Optional[str] = typer.Option(None, "--type", help="File type: timeline, modules, decisions, plans, archive"),
    module_filter: Optional[str] = typer.Option(None, "--module", help="Filter by module path (e.g., 'projects' or 'projects/website')"),
    tag: List[str] = typer.Option(None, "--tag", help="Filter by tags (can use multiple times)"),
    tag_only: Optional[str] = typer.Option(None, "--tag-only", help="Search by tag only (no keyword matching)"),
    show_score: bool = typer.Option(False, "--show-score", help="Show relevance scores"),
    summary: bool = typer.Option(False, "--summary", help="Show summary statistics"),
    hybrid: Optional[bool] = typer.Option(None, "--hybrid/--no-hybrid", help="Hybrid search (keyword + semantic combined). Default from config."),
    text_weight: Optional[float] = typer.Option(None, "--text-weight", help="Keyword weight for hybrid (default from config: 0.7)"),
    semantic_weight: Optional[float] = typer.Option(None, "--semantic-weight", help="Semantic weight for hybrid (default from config: 0.3)"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable result caching"),
    cache_ttl: int = typer.Option(3600, "--cache-ttl", help="Cache TTL in seconds (default: 3600)"),
):
    """Search timeline and modules (ms command).

    Supports keyword search (default), semantic search (--semantic),
    and hybrid search (--hybrid) combining both approaches.

    Tag search methods:
        ms "#버그"                   # Search by hashtag
        ms "#버그 #긴급"             # Multiple tags
        ms --tag-only 버그           # Tag-only search
        ms "login" --tag 버그        # Keyword + tag filter

    Examples:
        ms "bug fix"                        # Keyword search
        ms "authentication" --semantic      # Semantic search
        ms "login" --hybrid                 # Hybrid search
        ms "feature" --date this-week       # Filter by date
        ms "refactor" --type timeline       # Filter by file type
    """
    query = arg_str(query)
    from_date = opt_str(from_date)
    to_date = opt_str(to_date)
    rank = opt_str(rank)
    date = opt_str(date)
    file_type = opt_str(file_type)
    module_filter = opt_str(module_filter)
    tag_only = opt_str(tag_only)

    # Initialize tag list if None
    if tag is None:
        tag = []
    else:
        tag = list(tag)

    # Parse #hashtags from query (supports Korean)
    # e.g., "#버그 #긴급" -> tags: ["버그", "긴급"], query: ""
    # e.g., "login #버그" -> tags: ["버그"], query: "login"
    if query.startswith('#'):
        # Query starts with hashtag - likely tag-only search
        query_tags = re.findall(r'#([\w가-힣-]+)', query)
        if query_tags:
            tag.extend(query_tags)
            # Remove hashtags from query
            remaining = re.sub(r'#[\w가-힣-]+\s*', '', query).strip()
            query = remaining if remaining else ""
    else:
        # Check for hashtags at the end of query
        hashtag_pattern = re.compile(r'(\s+#[\w가-힣-]+)+$')
        match = hashtag_pattern.search(query)
        if match:
            query_tags = re.findall(r'#([\w가-힣-]+)', match.group(0))
            tag.extend(query_tags)
            query = query[:match.start()].strip()

    # Handle --tag-only option
    if tag_only:
        tag.append(tag_only)
        if not query:
            query = ""  # Will search all content, filtered by tag

    # Load search defaults from config
    config = Config()
    if hybrid is None:
        hybrid = config.get("search.hybrid", False)
    if text_weight is None:
        text_weight = config.get("search.text_weight", 0.7)
    if semantic_weight is None:
        semantic_weight = config.get("search.semantic_weight", 0.3)
    if threshold is None:
        threshold = config.get("search.semantic_threshold", 0.5)

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
        cache_dir = Path.home() / ".memory" / ".cache" / "search"
        search_cache = SearchCache(cache_dir, ttl_seconds=cache_ttl)

        cached_results = search_cache.get(query, **cache_key_params)
        if cached_results:
            console.print("[dim]Using cached results...[/dim]\n")
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
                for i, result in enumerate(cached_results, 1):
                    console.print(f"{i}. {result.file_path}:{result.line_number}")
            return

    if hybrid:
        try:
            from memory_tool.core.vector_search import VectorSearcher, VectorSearchNotAvailableError
            from memory_tool.search import HybridSearcher
            from memory_tool.core.search import SearchResult

            searcher = MemorySearcher()
            scope = "all" if all else "local"

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

            for result in text_results:
                date_from_path = searcher._extract_date_from_path(result.file_path)
                if date_from_path:
                    result.date = datetime.combine(date_from_path, datetime.min.time())

            try:
                vector_searcher = VectorSearcher()
                semantic_results_list = vector_searcher.semantic_search(
                    query,
                    top_k=max_results or 50,
                    threshold=threshold
                )

                semantic_results = []
                for r in semantic_results_list:
                    result_date = None
                    if r.get('date'):
                        try:
                            result_date = datetime.fromisoformat(r['date'])
                        except ValueError:
                            pass  # Skip invalid date formats
                    semantic_results.append(SearchResult(
                        file_path=Path(r['file']),
                        line_number=r['line'],
                        line_content=r['content'],
                        match_context=r['content'],
                        score=r['similarity'],
                        date=result_date,
                    ))

                hybrid_searcher = HybridSearcher()
                all_results = hybrid_searcher.combine_results(
                    text_results,
                    semantic_results,
                    text_weight,
                    semantic_weight,
                )

                console.print(f"[cyan]Hybrid Search Results[/cyan] (text: {text_weight:.1f}, semantic: {semantic_weight:.1f})\n")

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

                # Deduplicate overlapping results
                all_results = deduplicate_results(all_results, context_lines=1)

                if search_cache:
                    search_cache.set(query, all_results, **cache_key_params)

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

    searcher = MemorySearcher()
    scope = "all" if all else "local"

    parsed_from = None
    parsed_to = None

    try:
        if from_date:
            parsed_from = datetime.strptime(from_date, "%Y-%m-%d").date()
        if to_date:
            parsed_to = datetime.strptime(to_date, "%Y-%m-%d").date()

        if parsed_from and parsed_to and parsed_from > parsed_to:
            console.print("[red]ERROR[/red] --from date must be before --to date")
            sys.exit(1)

    except ValueError as e:
        console.print(f"[red]ERROR[/red] Invalid date format: {e}")
        console.print("[dim]Use YYYY-MM-DD format (e.g., 2025-11-14)[/dim]")
        sys.exit(1)

    # If query is empty but tags are specified, use wildcard pattern
    search_query = query if query else "."
    tag_only_mode = not query and tag

    try:
        results_dict = searcher.search(
            search_query,
            scope=scope,
            with_kb=with_kb,
            case_sensitive=case_sensitive,
            context_lines=1 if not no_context else 0,
            max_results=None if tag_only_mode else max_results,  # Get all results for tag filtering
            from_date=parsed_from,
            to_date=parsed_to,
            use_index=not no_index if not tag_only_mode else False,  # Skip index for tag-only mode
        )

        from memory_tool.core.search import SearchResult
        all_results = []
        for source_path, source_results in results_dict.items():
            all_results.extend(source_results)

        for result in all_results:
            date_from_path = searcher._extract_date_from_path(result.file_path)
            if date_from_path:
                result.date = datetime.combine(date_from_path, datetime.min.time())

        if date or file_type or tag or module_filter:
            from memory_tool.search import FilterChain
            filter_chain = FilterChain(searcher.base_path)
            all_results = filter_chain.apply_filters(
                all_results,
                date_expr=date,
                file_type=file_type,
                tags=tag if tag else None,
            )

            if module_filter:
                modules_path = searcher.base_path / ".memory" / "modules"
                module_filter_path = modules_path / module_filter

                filtered_results = []
                for result in all_results:
                    try:
                        result_path = Path(result.file_path)
                        if result_path.is_relative_to(module_filter_path):
                            filtered_results.append(result)
                    except (ValueError, AttributeError):
                        result_str = str(result.file_path)
                        filter_str = str(module_filter_path)
                        if result_str.startswith(filter_str):
                            filtered_results.append(result)

                all_results = filtered_results

        if rank or boost_recent:
            from memory_tool.search import SearchRanker

            use_bm25 = (rank == "bm25")
            ranker = SearchRanker(
                use_bm25=use_bm25,
                use_date_weight=boost_recent,
                date_decay_days=decay_days,
            )

            all_results = ranker.rank(query, all_results)

        # Deduplicate overlapping results (from context lines)
        all_results = deduplicate_results(all_results, context_lines=1)

        if max_results and len(all_results) > max_results:
            all_results = all_results[:max_results]

        if search_cache:
            search_cache.set(query, all_results, **cache_key_params)

        # Show tag search header if tag-only mode
        if tag_only_mode:
            tag_str = ", ".join(f"#{t}" for t in tag)
            console.print(f"[cyan]Tag Search Results[/cyan] ({tag_str})\n")

        if show_score or summary or not no_context:
            from memory_tool.search import ResultFormatter
            formatter = ResultFormatter(searcher.base_path)

            formatter.print_results(
                all_results,
                query=query if query else None,
                show_score=show_score,
                show_context=not no_context,
                context_lines=1,
                highlight=bool(query),
                show_summary=summary,
            )
        else:
            formatted = searcher.format_results(
                {str(searcher.memory_path): all_results},
                show_context=not no_context
            )
            console.print(formatted)

        try:
            from memory_tool.utils.suggestion_helper import check_and_suggest_after_command
            memory_dir = Path.cwd() / ".memory"
            check_and_suggest_after_command(memory_dir, "search", force=False)
        except Exception:
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
def check(
    module: str = typer.Option(None, "--module", "-m", help="Check specific module only"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show all paths, not just issues"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Quiet mode (exit code only)"),
    legacy: bool = typer.Option(False, "--legacy", "-l", help="Use legacy grouped output format instead of standard error format"),
    include_archived: bool = typer.Option(False, "--include-archived", help="Include archived modules in check"),
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
            module_name = resolve_module_name(module)
            result = checker.check_module(module_name)

            if not quiet:
                if legacy:
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
                    for path_result in result.path_results:
                        if not path_result.exists:
                            console.print(f"[red]{path_result.format_error()}[/red]")
                    if not result.has_related_files:
                        source_file = f".memory/modules/{module_name}/current.md"
                        console.print(f"[yellow]{source_file}:1: warning: No Related Files section found[/yellow]")
                    console.print(f"\n[dim]Checked: {result.valid_count} valid, {result.missing_count} missing[/dim]")

            if result.has_issues:
                sys.exit(1)

        else:
            summary_result = checker.check_all_modules(include_archived=include_archived)
            checker.save_cache(summary_result)

            if not quiet:
                output_text = format_check_result(
                    summary_result,
                    verbose=verbose,
                    standard_format=not legacy,
                )
                console.print(output_text)

            if summary_result.has_issues:
                sys.exit(1)
            else:
                if not quiet:
                    console.print("\n[green]All paths valid![/green]")

    except Exception as e:
        if not quiet:
            console.print(f"[red]ERROR[/red] {e}")
        sys.exit(1)


@app.command()
def index(
    check_flag: bool = typer.Option(False, "--check", help="Check index status"),
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

        if not IndexManager.available():
            console.print("[red]ERROR[/red] SQLite with FTS5 not available")
            console.print("Indexing requires SQLite 3.9.0+ with FTS5 support")
            sys.exit(1)

        indexer = IndexManager(memory_path)

        if check_flag:
            is_fresh = indexer.is_index_fresh()
            if is_fresh:
                console.print("[green]Index is up to date[/green]")
            else:
                console.print("[yellow]Index is stale or missing[/yellow]")
                console.print("Run 'mindex' to rebuild")
            return

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

        if optimize or vacuum:
            from memory_tool.search import IndexOptimizer

            db_path = memory_path / ".index" / "search.db"
            if not db_path.exists():
                console.print("[red]ERROR[/red] Index database not found")
                console.print("Run 'mindex' to create index first")
                sys.exit(1)

            optimizer = IndexOptimizer(db_path)

            if optimize and vacuum:
                console.print("Running full optimization...")
                result = optimizer.full_optimize()

                if result.get("overall_success"):
                    console.print("[green]Optimization complete![/green]")

                    fts_result = result.get("fts5_optimize", {})
                    if fts_result.get("success"):
                        console.print(f"  FTS5: {fts_result.get('entries_indexed', 0)} entries optimized")

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
                console.print("Optimizing FTS5 index...")
                result = optimizer.optimize_fts5()

                if result.get("success"):
                    console.print(f"[green]OK[/green] {result.get('message')}")
                    console.print(f"  Entries: {result.get('entries_indexed', 0)}")
                else:
                    console.print(f"[red]ERROR[/red] {result.get('error')}")
                    sys.exit(1)

            elif vacuum:
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

        console.print("Indexing .memory/ content...")

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
def tags(
    file_type: List[str] = typer.Option(
        None, "--type", "-t",
        help="File types: timeline, modules, plans (can use multiple)"
    ),
    all_types: bool = typer.Option(
        False, "--all", "-a",
        help="Search all file types"
    ),
    sort: Optional[str] = typer.Option(
        None, "--sort", "-s",
        help="Sort by: count (default), alpha"
    ),
    min_count: Optional[int] = typer.Option(
        None, "--min-count", "-m",
        help="Minimum usage count to display"
    ),
):
    """List tags used in .memory (mtags command).

    By default, shows tags from timeline only.

    Examples:
        mtags                              # Timeline tags (default)
        mtags --all                        # All file types
        mtags --type timeline --type modules  # Multiple types
        mtags --sort alpha                 # Sort alphabetically
        mtags --min-count 3                # Tags used 3+ times
    """
    # Load defaults from config
    config = Config()

    # Determine file types to search
    if file_type:
        selected_types = list(file_type)
    elif all_types:
        selected_types = ["timeline", "modules", "plans"]
    else:
        selected_types = config.get("tags.default_types", ["timeline"])

    # Load sort and min_count from config if not provided
    if sort is None:
        sort = config.get("tags.sort", "count")
    if min_count is None:
        min_count = config.get("tags.min_count", 1)

    # Validate sort option
    if sort not in ("count", "alpha"):
        console.print(f"[red]ERROR[/red] Invalid sort option: {sort}")
        console.print("[dim]Valid options: count, alpha[/dim]")
        sys.exit(1)

    # Find .memory directory
    memory_path = Path.cwd() / ".memory"
    if not memory_path.exists():
        console.print("[red]ERROR[/red] .memory/ not found. Run 'minit' first.")
        sys.exit(1)

    # Collect tags
    collector = TagCollector(memory_path)
    tag_counts = collector.collect(selected_types)

    # Filter by min_count
    if min_count > 1:
        tag_counts = {k: v for k, v in tag_counts.items() if v >= min_count}

    if not tag_counts:
        type_str = ", ".join(selected_types)
        console.print(f"[yellow]No tags found in {type_str}[/yellow]")
        if min_count > 1:
            console.print(f"[dim](minimum count filter: {min_count})[/dim]")
        return

    # Sort tags
    if sort == "alpha":
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[0].lower())
    else:  # count (default)
        sorted_tags = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0].lower()))

    # Calculate max values for bar chart
    max_count = max(tag_counts.values())
    max_tag_len = max(len(tag) for tag in tag_counts.keys())
    bar_width = 20  # Maximum bar width

    # Print header
    type_str = ", ".join(selected_types)
    unique_count = len(tag_counts)
    console.print(f"\n[bold cyan]Tags in {type_str}[/bold cyan] ({unique_count} unique tags)\n")

    # Print tags with bar chart
    # Use ASCII-safe character for Windows compatibility
    bar_char = "#"

    for tag, count in sorted_tags:
        # Calculate bar length
        bar_len = int((count / max_count) * bar_width) if max_count > 0 else 0
        bar = bar_char * bar_len

        # Color based on count
        if count >= max_count * 0.7:
            bar_color = "green"
        elif count >= max_count * 0.3:
            bar_color = "yellow"
        else:
            bar_color = "dim"

        # Print formatted line
        console.print(
            f"  {tag:<{max_tag_len}}  [{bar_color}]{bar:<{bar_width}}[/{bar_color}]  {count}"
        )
