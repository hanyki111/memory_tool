# Search Improvements Plan

**Created:** 2025-11-15
**Status:** Planning
**Priority:** High

---

## 📋 Overview

Comprehensive search system improvements covering 5 major areas:
- A. Hybrid Search (텍스트 + 벡터)
- B. Ranking Algorithm (BM25, TF-IDF, 날짜 가중치)
- C. Search Filters (날짜, 파일 타입, 태그)
- D. Result Formatting (하이라이트, 컨텍스트, 스코어)
- E. Performance Optimization (캐싱, 병렬 처리)

**Goal:** Make search more accurate, flexible, and performant

---

## 🎯 Current State Analysis

### Existing Search Capabilities:

**1. Text Search (ripgrep-based):**
- Fast full-text search
- Regex support
- File filtering (glob, type)
- Output modes: content, files, count

**2. Vector Search (semantic):**
- sentence-transformers embeddings
- Cosine similarity ranking
- `--semantic` flag
- Embeddings cache

**3. SQLite FTS5 Index:**
- Fast indexed search
- `mindex` to build index
- `ms --no-index` to disable
- 10-100x speed improvement

### Current Limitations:

**Accuracy:**
- No hybrid scoring (text + semantic separate)
- Simple relevance ranking
- No date-based weighting

**Flexibility:**
- Limited filter options
- No tag/category filtering
- Basic date filtering

**UX:**
- Minimal context display
- No relevance scores shown
- Basic highlighting

**Performance:**
- No result caching
- Sequential processing
- Full scan for some queries

---

## 🔧 Detailed Design

### A. Hybrid Search (텍스트 + 벡터 결합)

**Goal:** Combine text matching and semantic similarity for better results

**Implementation:**

```python
class HybridSearcher:
    """Combine text and semantic search with configurable weights."""

    def search(
        self,
        query: str,
        text_weight: float = 0.7,
        semantic_weight: float = 0.3,
    ) -> List[SearchResult]:
        """
        Perform hybrid search.

        1. Run text search (SQLite FTS5 or ripgrep)
        2. Run semantic search (embeddings)
        3. Merge results with weighted scoring
        4. Return top-k by combined score
        """
        text_results = self._text_search(query)
        semantic_results = self._semantic_search(query)

        # Merge and score
        combined = self._merge_results(
            text_results,
            semantic_results,
            text_weight,
            semantic_weight,
        )

        return sorted(combined, key=lambda x: x.score, reverse=True)
```

**CLI Integration:**
```bash
ms "query" --hybrid              # Default weights (0.7, 0.3)
ms "query" --hybrid --text-weight 0.5 --semantic-weight 0.5
ms "query" --text-only           # Text only (existing)
ms "query" --semantic            # Semantic only (existing)
```

**Files to Change:**
- `memory_tool/search/hybrid.py` (new)
- `memory_tool/cli.py` (add --hybrid option)
- `memory_tool/search/searcher.py` (integrate hybrid)

---

### B. Ranking Algorithm (BM25, TF-IDF, 날짜 가중치)

**Goal:** Improve relevance scoring with established algorithms

**Implementation:**

**1. BM25 Scoring (for text search):**
```python
class BM25Ranker:
    """BM25 ranking for text search results."""

    def __init__(self, k1=1.5, b=0.75):
        self.k1 = k1  # Term frequency saturation
        self.b = b    # Length normalization

    def score(self, query_terms, document, corpus_stats):
        """
        Calculate BM25 score.

        Score = Σ IDF(qi) * (f(qi,D) * (k1+1)) / (f(qi,D) + k1*(1-b+b*|D|/avgdl))

        Where:
        - IDF(qi) = inverse document frequency
        - f(qi,D) = term frequency in document
        - |D| = document length
        - avgdl = average document length
        """
        score = 0.0
        for term in query_terms:
            idf = corpus_stats.get_idf(term)
            tf = document.count(term)
            doc_len = len(document)
            avg_len = corpus_stats.avg_doc_length

            score += idf * (tf * (self.k1 + 1)) / (
                tf + self.k1 * (1 - self.b + self.b * doc_len / avg_len)
            )

        return score
```

**2. Date-based Weighting:**
```python
class DateWeightRanker:
    """Apply date-based weighting to search results."""

    def apply_date_weight(
        self,
        results: List[SearchResult],
        decay_days: int = 30,
        boost_factor: float = 2.0,
    ):
        """
        Boost recent results, decay old ones.

        Weight = base_score * (1 + boost_factor * e^(-days_ago / decay_days))
        """
        now = datetime.now()

        for result in results:
            days_ago = (now - result.date).days
            date_weight = 1 + boost_factor * math.exp(-days_ago / decay_days)
            result.score *= date_weight

        return sorted(results, key=lambda x: x.score, reverse=True)
```

**CLI Integration:**
```bash
ms "query" --rank bm25              # Use BM25 ranking
ms "query" --boost-recent           # Boost recent results (default 30 days)
ms "query" --boost-recent --decay-days 7  # Custom decay
```

**Files to Change:**
- `memory_tool/search/ranking.py` (new)
- `memory_tool/search/bm25.py` (new)
- `memory_tool/cli.py` (add ranking options)

---

### C. Search Filters (날짜, 파일 타입, 태그)

**Goal:** More flexible filtering for precise searches

**Implementation:**

**1. Enhanced Date Filtering:**
```python
class DateFilter:
    """Advanced date filtering."""

    @staticmethod
    def parse_date_expression(expr: str) -> Tuple[datetime, datetime]:
        """
        Parse date expressions:
        - "today", "yesterday", "this-week", "this-month"
        - "2025-11-15" (specific date)
        - "2025-11" (month)
        - "last-7-days", "last-30-days"
        - "2025-11-01..2025-11-15" (range)
        """
        # Implementation here
        pass
```

**2. File Type Filtering:**
```python
class FileTypeFilter:
    """Filter by file type."""

    TYPES = {
        "timeline": ["timeline/**/*.md"],
        "modules": ["modules/**/*.md"],
        "concepts": ["concepts/**/*.md"],
        "decisions": ["**/decisions*.md"],
        "plans": ["**/PLAN-*.md"],
    }

    def filter(self, results: List[SearchResult], file_type: str):
        """Filter results by file type."""
        patterns = self.TYPES.get(file_type, [])
        # Match against patterns
```

**3. Tag/Category Filtering:**
```python
class TagFilter:
    """Filter by tags or categories."""

    def extract_tags(self, content: str) -> Set[str]:
        """
        Extract tags from content:
        - #tag format
        - **Category:** format
        - YAML frontmatter tags
        """
        tags = set()

        # #hashtag
        tags.update(re.findall(r'#(\w+)', content))

        # **Category:** pattern
        category_matches = re.findall(r'\*\*([^:]+):\*\*', content)
        tags.update(category_matches)

        return tags

    def filter(self, results: List[SearchResult], tags: List[str]):
        """Filter results by tags."""
        # Implementation
```

**CLI Integration:**
```bash
ms "query" --date today
ms "query" --date this-week
ms "query" --date last-7-days
ms "query" --date 2025-11-01..2025-11-15
ms "query" --type timeline
ms "query" --type decisions
ms "query" --tag feature --tag bugfix
ms "query" --category "Phase Implementation"
```

**Files to Change:**
- `memory_tool/search/filters.py` (new)
- `memory_tool/cli.py` (add filter options)

---

### D. Result Formatting (하이라이트, 컨텍스트, 스코어)

**Goal:** Better visualization of search results

**Implementation:**

**1. Enhanced Highlighting:**
```python
class ResultFormatter:
    """Format search results with rich output."""

    def format_result(
        self,
        result: SearchResult,
        show_score: bool = True,
        show_context: bool = True,
        context_lines: int = 2,
    ) -> str:
        """
        Format result with:
        - File path with relative display
        - Match highlighting (bold, color)
        - Context lines (before/after)
        - Relevance score
        - Date/metadata
        """
        output = []

        # Header with score
        if show_score:
            output.append(f"[cyan]Score: {result.score:.2f}[/cyan]")

        # File path
        output.append(f"[bold]{result.file_path}[/bold]:{result.line_number}")

        # Date
        output.append(f"[dim]{result.date.strftime('%Y-%m-%d %H:%M')}[/dim]")

        # Context with highlighting
        if show_context:
            context = self._get_context(result, context_lines)
            highlighted = self._highlight_matches(context, result.matches)
            output.append(highlighted)

        return "\n".join(output)

    def _highlight_matches(self, text: str, matches: List[str]) -> str:
        """Highlight matched terms in text."""
        for match in matches:
            # Use rich markup for highlighting
            text = text.replace(match, f"[bold yellow]{match}[/bold yellow]")
        return text
```

**2. Summary Statistics:**
```python
def print_search_summary(results: List[SearchResult]):
    """Print search summary statistics."""
    console.print(f"\n[bold]Found {len(results)} results[/bold]")
    console.print(f"Files: {len(set(r.file_path for r in results))}")
    console.print(f"Date range: {min(r.date for r in results)} to {max(r.date for r in results)}")
    console.print(f"Avg score: {sum(r.score for r in results) / len(results):.2f}\n")
```

**CLI Integration:**
```bash
ms "query" --show-score           # Show relevance scores
ms "query" --context 3            # 3 lines of context
ms "query" --no-highlight         # Disable highlighting
ms "query" --summary              # Show summary statistics
```

**Files to Change:**
- `memory_tool/search/formatter.py` (new)
- `memory_tool/cli.py` (add formatting options)

---

### E. Performance Optimization (캐싱, 병렬 처리)

**Goal:** Faster search with caching and parallelization

**Implementation:**

**1. Result Caching:**
```python
class SearchCache:
    """Cache search results for faster repeated queries."""

    def __init__(self, cache_dir: Path, ttl_seconds: int = 3600):
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds

    def get(self, query_key: str) -> Optional[List[SearchResult]]:
        """Get cached results if valid."""
        cache_file = self.cache_dir / f"{hash(query_key)}.json"

        if not cache_file.exists():
            return None

        # Check TTL
        mtime = cache_file.stat().st_mtime
        if time.time() - mtime > self.ttl_seconds:
            cache_file.unlink()
            return None

        # Load from cache
        data = json.loads(cache_file.read_text())
        return [SearchResult.from_dict(d) for d in data]

    def set(self, query_key: str, results: List[SearchResult]):
        """Cache search results."""
        cache_file = self.cache_dir / f"{hash(query_key)}.json"
        data = [r.to_dict() for r in results]
        cache_file.write_text(json.dumps(data))
```

**2. Parallel Processing:**
```python
class ParallelSearcher:
    """Search multiple sources in parallel."""

    def search_parallel(
        self,
        query: str,
        sources: List[SearchSource],
        max_workers: int = 4,
    ) -> List[SearchResult]:
        """
        Search multiple sources concurrently.

        Example:
        - Timeline files
        - Module files
        - Concept files
        All searched in parallel, results merged
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(source.search, query)
                for source in sources
            ]

            results = []
            for future in concurrent.futures.as_completed(futures):
                results.extend(future.result())

        return results
```

**3. Index Optimization:**
```python
class IndexOptimizer:
    """Optimize SQLite FTS5 index."""

    def optimize(self, db_path: Path):
        """
        Optimize FTS5 index:
        - VACUUM
        - OPTIMIZE
        - REBUILD if needed
        """
        conn = sqlite3.connect(db_path)

        # Optimize FTS5
        conn.execute("INSERT INTO search_fts(search_fts) VALUES('optimize')")

        # Vacuum
        conn.execute("VACUUM")

        conn.commit()
        conn.close()
```

**CLI Integration:**
```bash
ms "query" --no-cache             # Disable cache
ms "query" --cache-ttl 7200       # Custom TTL (2 hours)
mindex --optimize                 # Optimize index
```

**Config Settings:**
```yaml
search:
  cache_enabled: true
  cache_ttl_seconds: 3600  # 1 hour
  parallel_workers: 4
  index_auto_optimize: true
```

**Files to Change:**
- `memory_tool/search/cache.py` (new)
- `memory_tool/search/parallel.py` (new)
- `memory_tool/cli.py` (add cache options)
- `.memory/config.yaml` (add settings)

---

## 📁 File Structure

```
memory_tool/
├── search/
│   ├── __init__.py
│   ├── searcher.py          # Main search interface (existing)
│   ├── hybrid.py            # NEW: Hybrid search
│   ├── ranking.py           # NEW: Ranking algorithms
│   ├── bm25.py              # NEW: BM25 implementation
│   ├── filters.py           # NEW: Advanced filters
│   ├── formatter.py         # NEW: Result formatting
│   ├── cache.py             # NEW: Result caching
│   └── parallel.py          # NEW: Parallel search
├── cli.py                   # Updated: New options
└── utils/
    └── config.py            # Updated: New config options
```

---

## 🧪 Testing Plan

### Unit Tests:

**1. Hybrid Search:**
```python
def test_hybrid_search_weights():
    """Test hybrid search with different weights."""
    searcher = HybridSearcher()
    results = searcher.search("test query", text_weight=0.8, semantic_weight=0.2)
    assert len(results) > 0
    assert all(hasattr(r, 'score') for r in results)
```

**2. BM25 Ranking:**
```python
def test_bm25_scoring():
    """Test BM25 score calculation."""
    ranker = BM25Ranker()
    score = ranker.score(["test"], document, corpus_stats)
    assert score > 0
```

**3. Date Filtering:**
```python
def test_date_filter_today():
    """Test 'today' date filter."""
    filter = DateFilter()
    start, end = filter.parse_date_expression("today")
    assert start.date() == datetime.now().date()
```

**4. Result Caching:**
```python
def test_search_cache():
    """Test result caching."""
    cache = SearchCache(cache_dir)
    cache.set("query", results)
    cached = cache.get("query")
    assert cached == results
```

### Integration Tests:

```bash
# Test hybrid search
ms "feature implementation" --hybrid

# Test ranking
ms "bug fix" --rank bm25 --boost-recent

# Test filters
ms "decision" --date this-week --type decisions

# Test formatting
ms "phase" --show-score --context 3

# Test caching
ms "query" --no-cache
ms "query"  # Should use cache
```

---

## 🚀 Implementation Priority

**Phase 1: Core Improvements (High Priority)**
1. B. Ranking Algorithm (BM25, date weighting)
2. C. Search Filters (date, file type)
3. D. Result Formatting (score, context, highlighting)

**Phase 2: Advanced Features (Medium Priority)**
4. A. Hybrid Search (text + semantic)
5. E. Performance - Caching

**Phase 3: Optimization (Low Priority)**
6. E. Performance - Parallel processing
7. E. Performance - Index optimization

---

## 📊 Expected Impact

**Accuracy:**
- Hybrid search: +30% relevant results
- BM25 ranking: +20% better ordering
- Date weighting: Recent results prioritized

**Flexibility:**
- 5+ new filter options
- Natural date expressions
- Tag/category filtering

**UX:**
- Clear relevance scores
- Rich context display
- Better highlighting

**Performance:**
- Caching: 10-100x for repeated queries
- Parallel: 2-4x for multi-source searches
- Index optimization: Sustained fast performance

---

## ⚠️ Risks & Mitigations

**Risk 1: Complexity**
- Mitigation: Phased implementation, one feature at a time
- Keep existing search working throughout

**Risk 2: Performance Regression**
- Mitigation: Benchmark before/after
- Make advanced features opt-in (--hybrid, etc.)

**Risk 3: Breaking Changes**
- Mitigation: Maintain backward compatibility
- Existing commands work as before
- New features are additive (new flags)

---

## 🔄 Backward Compatibility

**All existing commands continue to work:**
```bash
ms "query"                    # Works as before
ms "query" --semantic         # Works as before
ms "query" --date 2025-11     # Works as before
```

**New features are opt-in:**
```bash
ms "query" --hybrid           # NEW
ms "query" --rank bm25        # NEW
ms "query" --show-score       # NEW
```

---

## 📝 Documentation Updates

**README.md:**
- Add "Search Improvements" section
- Document new flags and options
- Show examples

**CLAUDE.md:**
- Update command reference
- Add search best practices

**decisions.md:**
- Add Decision #30: Search improvements implementation

---

## ✅ Acceptance Criteria

**Phase 1 Complete When:**
- [ ] BM25 ranking implemented and tested
- [ ] Date weighting functional
- [ ] Enhanced date filters work (today, this-week, etc.)
- [ ] File type filtering works
- [ ] Result formatting improved (scores, context)
- [ ] All existing tests pass
- [ ] New tests added and passing

**Phase 2 Complete When:**
- [ ] Hybrid search functional
- [ ] Result caching working
- [ ] Performance benchmarks show improvement

**Phase 3 Complete When:**
- [ ] Parallel search implemented
- [ ] Index optimization working
- [ ] All documentation updated

---

**Total Estimated Lines:** ~2000 new/modified lines
**Estimated Time:** 3-4 hours (phased implementation)
**Branch:** feature/search-improvements
