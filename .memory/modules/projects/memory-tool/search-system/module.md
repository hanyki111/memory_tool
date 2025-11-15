# Module: projects/memory-tool/search-system

**Created:** 2025-11-15
**Tags:** search, indexing, semantic, full-text, vector

## Purpose

Advanced search functionality with multiple backends: full-text search (SQLite FTS5), semantic search (vector embeddings), and hybrid ranking. Provides fast, relevant results across timeline and modules.

## Scope

**Included:**
- **Text Search**: SQLite FTS5 indexing, BM25 ranking, porter stemming
- **Vector Search**: sentence-transformers embeddings, cosine similarity
- **Hybrid Search**: Combined text + vector with configurable weights
- **Advanced Filters**: Date ranges, file types, tags, exclude patterns
- **Performance**: Result caching (TTL-based), parallel processing, batch indexing
- **Index Management**: Incremental updates, optimization, vacuum
- **CLI**: `ms` command with 15+ options

**Excluded:**
- Timeline data storage → [[projects/memory-tool/core-system]]
- UI presentation → [[projects/memory-tool/ui-system]]
- LLM-based summarization → [[projects/memory-tool/llm-integration]]

## Architecture

**Three-Tier Search Strategy:**
1. **Fast Path**: SQLite FTS5 for quick text matches
2. **Semantic Path**: Vector embeddings for conceptual similarity
3. **Hybrid Path**: Combined ranking for best results

**Performance Optimization:**
- Incremental indexing (only changed files)
- Batch embeddings (10-50x speedup)
- Result caching with TTL
- Parallel search processing
- Memory-efficient streaming

**Fallback Strategy:**
- SQLite unavailable → ripgrep fallback
- Index corrupted → auto-rebuild
- Embeddings missing → text-only search

**Related Decisions:**
- Decision #6: Multiple search backends
- Decision #7: SQLite FTS5 for full-text
- Decision #8: sentence-transformers for vectors
- Decision #9: BM25 ranking algorithm
- Decision #10: Hybrid search strategy
- Decision #11: Result caching
- Decision #12: Incremental indexing

## Related Modules

- [[projects/memory-tool/core-system]] - Provides timeline data
- [[projects/memory-tool/llm-integration]] - Generates embeddings
- [[projects/memory-tool/ui-system]] - Displays results
- [[projects/memory-tool/module-system]] - Searches module content
