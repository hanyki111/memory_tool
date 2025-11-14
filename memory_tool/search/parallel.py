"""Parallel search processing for improved performance."""

import concurrent.futures
from typing import List, Callable, Any
from pathlib import Path
from ..core.search import SearchResult


class ParallelSearcher:
    """Execute search operations in parallel across multiple sources."""

    def __init__(self, max_workers: int = 4):
        """
        Initialize parallel searcher.

        Args:
            max_workers: Maximum number of parallel workers (default: 4)
        """
        self.max_workers = max_workers

    def search_parallel(
        self,
        query: str,
        search_functions: List[Callable[[str], List[SearchResult]]],
    ) -> List[SearchResult]:
        """
        Execute multiple search functions in parallel.

        Args:
            query: Search query
            search_functions: List of search functions to execute

        Returns:
            Combined list of all search results
        """
        all_results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all search tasks
            futures = [
                executor.submit(search_func, query)
                for search_func in search_functions
            ]

            # Collect results as they complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    results = future.result()
                    if results:
                        all_results.extend(results)
                except Exception as e:
                    # Log error but continue with other results
                    print(f"Search error: {e}")

        return all_results

    def search_directories_parallel(
        self,
        query: str,
        directories: List[Path],
        search_func: Callable[[str, Path], List[SearchResult]],
    ) -> List[SearchResult]:
        """
        Search multiple directories in parallel.

        Args:
            query: Search query
            directories: List of directories to search
            search_func: Search function that takes (query, directory)

        Returns:
            Combined list of search results from all directories
        """
        all_results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit search task for each directory
            futures = {
                executor.submit(search_func, query, directory): directory
                for directory in directories
            }

            # Collect results
            for future in concurrent.futures.as_completed(futures):
                directory = futures[future]
                try:
                    results = future.result()
                    if results:
                        all_results.extend(results)
                except Exception as e:
                    print(f"Error searching {directory}: {e}")

        return all_results

    def batch_process(
        self,
        items: List[Any],
        process_func: Callable[[Any], Any],
    ) -> List[Any]:
        """
        Process items in parallel batches.

        Args:
            items: List of items to process
            process_func: Function to apply to each item

        Returns:
            List of processed results
        """
        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = [executor.submit(process_func, item) for item in items]

            # Collect results in order
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"Processing error: {e}")

        return results
