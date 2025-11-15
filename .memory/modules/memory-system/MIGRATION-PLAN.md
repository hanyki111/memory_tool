# memory-system Migration Plan

> Plan to restructure memory-system into hierarchical modules

**Created:** 2025-11-15
**Status:** Proposed
**Target Date:** TBD

---

## Current State Analysis

### Module Size
```
current.md:            234 lines
decisions.md:          536 lines
PLAN-*.md:            694 lines
Other files:          ~500 lines
Total:               ~2000 lines
```

### Phase Coverage
- Phase 1: CLI commands + Skill
- Phase 2: Advanced search + module management
- Phase 3: Vector search
- Phase 4: LLM integration
- Phase 5: Search improvements + optimization
- Phase 6: Hierarchical modules + wiki connections
- Phase 7: Enhanced TUI

### Problem Indicators
✅ Size: ~2000 lines (approaching 3000 limit)
✅ Topics: 7+ distinct areas (CLI, search, TUI, LLM, modules, etc.)
✅ Decisions: 29 decisions (approaching 30 limit)
✅ Cognitive Load: Takes >20min to understand full scope
✅ Update Frequency: Multiple areas updated daily

**Conclusion:** Module split is justified and necessary.

---

## Proposed Structure

### Option A: Feature-Based Split (RECOMMENDED)

```
projects/
└── memory-tool/
    ├── core-system/                    # Core data and infrastructure
    │   ├── module.md                   # "Core data structures for memory_tool"
    │   ├── current.md                  # Timeline, init, basic CLI
    │   ├── decisions.md                # Decisions #1-5
    │   ├── timeline/                   # Timeline implementation details
    │   └── initialization/             # Init system details
    │
    ├── search-system/                  # Search engine
    │   ├── module.md                   # "Advanced search with multiple backends"
    │   ├── current.md                  # Text, vector, SQLite FTS5
    │   ├── decisions.md                # Decisions #6-12
    │   ├── text-search/                # BM25, ranking
    │   ├── vector-search/              # Embeddings, semantic
    │   └── indexing/                   # SQLite FTS5, optimization
    │
    ├── module-system/                  # Module management & connections
    │   ├── module.md                   # "Hierarchical modules with wiki-style connections"
    │   ├── current.md                  # Module management, graph, AI
    │   ├── decisions.md                # Decisions #13-20
    │   ├── hierarchy/                  # Tree structure, discovery
    │   ├── connections/                # Wiki links, graph database
    │   ├── graph/                      # Visualization, versioning
    │   └── ai-suggestions/             # LLM-based recommendations
    │
    ├── ui-system/                      # User interfaces
    │   ├── module.md                   # "Command-line and terminal interfaces"
    │   ├── current.md                  # CLI, TUI, aliases
    │   ├── decisions.md                # Decisions #21-25
    │   ├── cli/                        # Command implementations
    │   ├── tui/                        # Terminal UI browser
    │   └── aliases/                    # Alias management
    │
    ├── llm-integration/                # LLM features
    │   ├── module.md                   # "AI-powered features using LLMs"
    │   ├── current.md                  # Summarization, embeddings
    │   ├── decisions.md                # Decisions #26-29
    │   ├── summarization/              # Timeline/module summaries
    │   ├── embeddings/                 # Vector generation
    │   └── providers/                  # Anthropic, Ollama
    │
    └── project-management/             # Meta: project decisions
        ├── module.md                   # "Architecture and cross-cutting decisions"
        ├── current.md                  # Overall status
        ├── decisions.md                # Architecture decisions
        ├── principles.md               # Design principles
        └── roadmap.md                  # Future plans
```

### Rationale

**core-system:**
- Single responsibility: Basic data structures (timeline, entries)
- Stable, changes infrequently
- Other systems depend on this

**search-system:**
- Single responsibility: Finding information
- 3 related subsystems (text, vector, index)
- High cohesion within, low coupling with others

**module-system:**
- Single responsibility: Module organization & knowledge graph
- Natural grouping: hierarchy + connections + graph
- Phase 6 work stays together

**ui-system:**
- Single responsibility: User interaction
- CLI and TUI are presentation layers
- Changes together (new commands → new UI)

**llm-integration:**
- Single responsibility: AI-powered features
- Provider-agnostic
- Can add new LLM features independently

**project-management:**
- Single responsibility: Project governance
- Cross-cutting decisions
- Minimal code, mostly documentation

---

## Migration Steps

### Phase 1: Preparation (Est: 2 hours)

1. **Backup current state**
   ```bash
   cp -r .memory/modules/memory-system .memory/modules/memory-system.backup
   ```

2. **Create new module structure**
   ```bash
   mmodule create projects/memory-tool/core-system
   mmodule create projects/memory-tool/search-system
   mmodule create projects/memory-tool/module-system
   mmodule create projects/memory-tool/ui-system
   mmodule create projects/memory-tool/llm-integration
   mmodule create projects/memory-tool/project-management
   ```

3. **Create module.md for each**
   - Write clear single-sentence purpose
   - List scope and boundaries
   - Note dependencies

### Phase 2: Content Migration (Est: 4 hours)

#### 2.1 Migrate Decisions

**mapping.csv:**
```csv
Decision,Target Module,Reason
#1-5,core-system,"Timeline, init, basic structure"
#6-12,search-system,"Text, vector, SQLite search"
#13-20,module-system,"Hierarchical modules, connections, graph"
#21-25,ui-system,"CLI, TUI, aliases"
#26-29,llm-integration,"Anthropic, Ollama, summarization"
#24,project-management,"MCP deprioritization (architecture)"
```

#### 2.2 Migrate Current.md Content

Split `current.md` sections:
- Phase 1 core features → core-system
- Phase 2-3 search features → search-system
- Phase 6 module features → module-system
- Phase 7 TUI features → ui-system
- Phase 4 LLM features → llm-integration
- Overall roadmap → project-management

#### 2.3 Migrate Plans

- `PLAN-search-improvements.md` → search-system/
- Keep general plans in project-management/

### Phase 3: Update [[Links]] (Est: 2 hours)

1. **Find all references to memory-system**
   ```bash
   ms "\\[\\[memory-system" --output-mode content
   ```

2. **Update to new module names**
   - `[[memory-system/timeline]]` → `[[projects/memory-tool/core-system/timeline]]`
   - `[[memory-system/search]]` → `[[projects/memory-tool/search-system]]`
   - etc.

3. **Rebuild connection graph**
   ```bash
   mmodule rebuild-graph
   ```

4. **Check for broken links**
   ```bash
   mmodule check-links
   ```

### Phase 4: Create Inter-Module Connections (Est: 1 hour)

Add [[links]] between new modules:

**core-system** connections:
- → search-system (provides data to search)
- → ui-system (provides data to display)

**search-system** connections:
- ← core-system (depends on timeline data)
- → llm-integration (uses embeddings)
- → ui-system (provides results)

**module-system** connections:
- → llm-integration (uses AI suggestions)
- → ui-system (provides module browser)

**ui-system** connections:
- ← All systems (displays all features)

**llm-integration** connections:
- → search-system (provides embeddings)
- → module-system (provides suggestions)

### Phase 5: Archive Old Module (Est: 30 min)

```bash
# Archive the old memory-system
mmodule archive memory-system --reason "Split into feature-specific modules"

# Verify archive
ls .memory/modules/memory-system/archive/
```

### Phase 6: Update Documentation (Est: 1 hour)

1. **Update CLAUDE.md**
   - Point to new module structure
   - Update references

2. **Update README.md**
   - Mention modular architecture

3. **Regenerate context**
   ```bash
   mcontext
   ```

4. **Record to timeline**
   ```bash
   m "Restructured memory-system into 6 feature-based modules: core, search, modules, ui, llm, project-management. Improved cohesion and maintainability."
   ```

### Phase 7: Validation (Est: 1 hour)

Verify:
- [ ] All content migrated
- [ ] No broken [[links]]
- [ ] Connection graph accurate
- [ ] Context generation works
- [ ] All commands still function
- [ ] Module tree displays correctly
- [ ] Graph view shows connections

---

## Decision Mapping Detail

### Core System (Decisions #1-5)
- #1: Timeline-first architecture
- #2: 0.5-second capture principle
- #3: Markdown file format
- #4: ISO date structure (YYYY-MM/DD.md)
- #5: Auto-context generation

### Search System (Decisions #6-12)
- #6: Multiple search backends
- #7: SQLite FTS5 for full-text
- #8: sentence-transformers for vectors
- #9: BM25 ranking algorithm
- #10: Hybrid search combining text + vector
- #11: Result caching strategy
- #12: Incremental indexing

### Module System (Decisions #13-20)
- #13: Directory-based hierarchy
- #14: current.md as module marker
- #15: Wiki-style [[links]] for connections
- #16: SQLite for connection graph
- #17: Mermaid + Graphviz exports
- #18: Git hooks for auto-sync
- #19: AI-based connection suggestions
- #20: Graph versioning system

### UI System (Decisions #21-25)
- #21: Typer for CLI framework
- #22: Rich for terminal formatting
- #23: Textual for TUI
- #24: (moved to project-management)
- #25: Alias system for convenience

### LLM Integration (Decisions #26-29)
- #26: Dual provider support (Anthropic + Ollama)
- #27: Local-first with Ollama
- #28: Timeline summarization strategy
- #29: Archive automation

### Project Management
- #24: MCP deprioritization → Practical improvements
- Architecture principles
- Phase planning
- Roadmap

---

## Risk Assessment

### Low Risk
✅ Content is well-documented
✅ Clear natural boundaries exist
✅ Module system supports this operation
✅ Can test incrementally

### Medium Risk
⚠️ Many [[links]] need updating
⚠️ Timeline references may need updates
⚠️ Testing all functionality takes time

### Mitigation
- Keep backup of original
- Migrate incrementally (one module at a time)
- Test after each migration step
- Can rollback if issues found

---

## Timeline Estimate

**Total:** ~11 hours (can spread over multiple days)

- Preparation: 2h
- Migration: 4h
- Link updates: 2h
- Connections: 1h
- Archive: 0.5h
- Documentation: 1h
- Validation: 1h

**Recommended:** Split into 3 sessions:
- Session 1 (4h): Prep + Create structure + Migrate content
- Session 2 (4h): Update links + Create connections
- Session 3 (3h): Archive old + Update docs + Validate

---

## Success Criteria

Migration is successful when:
- [ ] All 6 new modules created with clear purposes
- [ ] All content migrated from old memory-system
- [ ] All [[links]] updated and validated
- [ ] Connection graph shows proper relationships
- [ ] No broken links (`mmodule check-links` passes)
- [ ] Module tree displays hierarchy correctly
- [ ] Graph view shows all connections
- [ ] Context generation includes new modules
- [ ] All CLI commands work
- [ ] Timeline entries reference new modules
- [ ] Documentation updated

---

## Rollback Plan

If migration fails:

```bash
# Remove new modules
rm -rf .memory/modules/projects/memory-tool/

# Restore backup
cp -r .memory/modules/memory-system.backup .memory/modules/memory-system

# Rebuild graph
mmodule rebuild-graph

# Regenerate context
mcontext
```

---

## Post-Migration Benefits

### Immediate
✅ Clearer separation of concerns
✅ Easier to find specific information
✅ Reduced cognitive load per module
✅ Better visualization in graph view

### Long-term
✅ Independent evolution of subsystems
✅ Easier onboarding (can learn one system at a time)
✅ Better reusability (can reference specific systems)
✅ Clearer dependencies and architecture

---

## Alternative: Gradual Migration

If full migration seems too risky, can do gradual approach:

1. **Week 1:** Extract llm-integration (least coupled)
2. **Week 2:** Extract ui-system (clear boundary)
3. **Week 3:** Extract search-system
4. **Week 4:** Extract module-system
5. **Week 5:** Rename remaining to core-system

This allows testing and validation between each step.

---

**Status:** Proposed, awaiting approval
**Next Step:** Review and decide on migration approach
