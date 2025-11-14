# SQLite Indexing Implementation Plan

**Feature Branch:** `feature/sqlite-indexing`
**Phase:** 5 Revised (Practical Improvements)
**Priority:** #2 (High)
**Estimated Time:** 4-6 hours

---

## 🎯 Goal

Improve search performance by 10-100x through SQLite full-text search indexing.

**Current State:**
- File-based search using ripgrep
- Every search reads all .md files
- Slow for large timelines (1000+ entries)
- No caching

**Target State:**
- SQLite FTS5 index
- Sub-second search on 10,000+ entries
- Incremental index updates
- Backward compatible (files still work)

---

## 📐 Design Decisions

### 1. Index Location
```
.memory/
  ├── timeline/
  ├── modules/
  ├── concepts/
  └── .index.db  ← SQLite database (hidden, gitignored)
```

**Why hidden:**
- Index is derived data (can be regenerated)
- Should not be committed to Git
- Users shouldn't modify directly

### 2. Schema Design

```sql
-- Main FTS5 table
CREATE VIRTUAL TABLE entries_fts USING fts5(
    content,        -- Full text content
    file_path,      -- Relative path from .memory/
    entry_date,     -- YYYY-MM-DD for timeline
    entry_time,     -- HH:MM for timeline
    entry_type,     -- 'timeline', 'decision', 'module', 'concept'
    tokenize='porter unicode61'
);

-- Metadata table
CREATE TABLE index_meta (
    file_path TEXT PRIMARY KEY,
    last_modified INTEGER,  -- Unix timestamp
    file_hash TEXT          -- SHA256 for change detection
);
```

### 3. Indexing Strategy

**On Command:**
- `m` command: Index new timeline entry immediately
- `ms` command: Check index freshness, rebuild if needed
- `mindex` command: Force full reindex (new command)

**What to Index:**
- Timeline entries (.memory/timeline/**/*.md)
- Decisions (.memory/modules/*/decisions.md)
- Current state (.memory/modules/*/current.md)
- Concepts (.memory/concepts/*.md)

**What NOT to Index:**
- Archive files (read-only, infrequent access)
- Templates
- README files

### 4. Search Integration

**ms command behavior:**
```python
# Before
results = ripgrep_search(pattern)

# After (with fallback)
if index_exists() and index_fresh():
    results = sqlite_search(pattern)
else:
    results = ripgrep_search(pattern)  # Fallback
```

**Backward compatibility:**
- If SQLite fails, fallback to ripgrep
- If .index.db deleted, regenerate on next search
- No breaking changes to existing commands

---

## 🏗️ Implementation Steps

### Phase 1: Core Infrastructure (2 hours)

1. **db/indexer.py** (New module)
   - `IndexManager` class
   - `create_database()` - Initialize schema
   - `index_file(file_path)` - Index single file
   - `index_all()` - Full reindex
   - `is_index_fresh()` - Check if rebuild needed

2. **db/search.py** (New module)
   - `SQLiteSearcher` class
   - `search(pattern, filters)` - FTS5 query
   - `get_context(file, line)` - Extract context lines
   - Convert SQLite results to existing format

3. **.gitignore update**
   ```
   .memory/.index.db
   .memory/.index.db-shm
   .memory/.index.db-wal
   ```

### Phase 2: Timeline Integration (1 hour)

4. **Modify core/timeline.py**
   ```python
   def add_entry(self, message):
       # Existing file write
       self._write_to_file(message)

       # New: Index immediately
       if IndexManager.available():
           IndexManager.index_entry(file, line, message)
   ```

5. **Modify core/search.py**
   ```python
   def search(self, pattern):
       # Try SQLite first
       if SQLiteSearcher.available():
           return SQLiteSearcher.search(pattern)

       # Fallback to file search
       return self._file_search(pattern)
   ```

### Phase 3: CLI Commands (1 hour)

6. **Add mindex command** (cli.py)
   ```bash
   mindex              # Full reindex
   mindex --check      # Check index status
   mindex --stats      # Show index statistics
   ```

7. **Update ms command** (cli.py)
   - Add `--no-index` flag (force file search)
   - Show "Using index" vs "Using file search" in output
   - Performance metrics (optional)

### Phase 4: Testing & Validation (1-2 hours)

8. **Create test timeline**
   - Generate 1000+ entries
   - Various patterns (dates, times, keywords)

9. **Performance benchmarks**
   - Measure: File search vs SQLite search
   - Target: 10x improvement minimum
   - Document results

10. **Edge case testing**
    - Empty timeline
    - Concurrent writes (multiple m commands)
    - Corrupted index (should rebuild)
    - Missing .index.db (should create)

---

## 🧪 Test Plan

### Unit Tests (Future - Phase 6)
- `test_indexer.py` - Index creation, updates
- `test_sqlite_search.py` - Query accuracy
- `test_integration.py` - End-to-end

### Manual Tests (This Phase)
1. Fresh project: `minit` → `mindex` → verify
2. Add entries: `m "test"` × 100 → `ms "test"` → verify speed
3. Index rebuild: Delete `.index.db` → `ms` → verify rebuild
4. Fallback: Corrupt index → `ms` → verify fallback
5. Large dataset: 1000 entries → `ms` → sub-second?

---

## 🚨 Risks & Mitigations

### Risk 1: SQLite dependency
**Impact:** Users without SQLite can't search
**Mitigation:** Graceful fallback to ripgrep (existing method)

### Risk 2: Index corruption
**Impact:** Search returns wrong results
**Mitigation:**
- Hash-based integrity check
- Auto-rebuild on corruption
- Clear error messages

### Risk 3: Concurrent writes
**Impact:** Index out of sync with files
**Mitigation:**
- SQLite handles concurrent reads well
- Write lock for index updates
- Timestamp-based freshness check

### Risk 4: Disk space
**Impact:** .index.db grows large
**Mitigation:**
- FTS5 is space-efficient (~2x text size)
- VACUUM command to reclaim space
- Exclude archives from index

---

## 📊 Success Criteria

**Must Have:**
- ✅ Search speed 10x faster on 1000+ entries
- ✅ Backward compatible (fallback works)
- ✅ Auto-rebuild on index corruption
- ✅ No breaking changes to existing commands

**Nice to Have:**
- 📊 `mindex --stats` shows index info
- 🔍 Ranking/relevance scoring
- 📈 Performance metrics in output

**Non-Goals (Future Phases):**
- ❌ Vector search integration (separate)
- ❌ Multi-project indexing
- ❌ Real-time index updates (current: on-command)

---

## 🔄 Rollback Plan

If critical issues found:
1. Keep feature branch unmerged
2. SQLite search fails → ripgrep fallback (already built-in)
3. Remove `mindex` command from CLI
4. No data loss (files are source of truth)

---

## 📝 Documentation Updates

After completion:
- Update README.md (SQLite optional dependency)
- Add "Performance" section to docs
- Update CLAUDE.md (mindex command)
- Record decision in decisions.md (#26)

---

## 🎯 Next Steps After This

Phase 5 Roadmap continues:
1. ✅ Document management
2. 🔄 **SQLite indexing** (this)
3. ⏳ Search improvements (hybrid, ranking)
4. ⏳ Auto-summary enhancements
5. ⏳ Performance optimization
6. ⏳ Test coverage
7. ⏳ Usability (GUI/TUI)

---

**Created:** 2025-11-14 23:05
**Branch:** feature/sqlite-indexing
**Estimated Start:** After user approval
