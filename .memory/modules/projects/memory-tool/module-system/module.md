# Module: projects/memory-tool/module-system

**Created:** 2025-11-15
**Tags:** modules, hierarchy, connections, graph, wiki

## Purpose

Hierarchical module management with wiki-style connections: Organize knowledge into structured modules, track relationships with [[links]], visualize knowledge graph, and suggest connections using AI.

## Scope

**Included:**
- **Hierarchical Modules**: Directory-based structure (`projects/parent/child`)
- **Module Discovery**: Recursive scanning, tree building
- **Wiki Connections**: `[[module-name]]` syntax, bidirectional links
- **Connection Graph**: SQLite-based graph database (`.memory/.connections.db`)
- **Graph Visualization**: Mermaid diagrams, Graphviz exports
- **Link Validation**: Broken link detection, orphaned module finding
- **AI Suggestions**: LLM-based connection recommendations, auto-tagging
- **Graph Versioning**: Snapshot system, diff/history tracking
- **Git Hooks**: Auto-rebuild on commit/checkout
- **CLI**: `module` command with 14+ actions

**Excluded:**
- Timeline management → [[projects/memory-tool/core-system]]
- Search within modules → [[projects/memory-tool/search-system]]
- UI for module browsing → [[projects/memory-tool/ui-system]]

## Architecture

**Module Structure:**
```
.memory/modules/
├── projects/parent/
│   ├── child1/
│   │   └── current.md  # Module marker
│   └── child2/
│       └── current.md
```

**Connection Graph:**
- SQLite database for fast lookups
- Nodes: Module paths
- Edges: [[link]] references
- Attributes: Context, line numbers

**Graph Versioning:**
- Snapshot on every rebuild
- Diff algorithm for changes
- History with timestamps
- Rollback capability

**AI Suggestions:**
- Path similarity (Levenshtein distance)
- Category matching (tag-based)
- Common target patterns
- LLM-based content analysis

**Related Decisions:**
- Decision #13: Directory-based hierarchy
- Decision #14: current.md as module marker
- Decision #15: Wiki-style [[links]]
- Decision #16: SQLite for connections
- Decision #17: Visualization formats
- Decision #18: Git hooks integration
- Decision #19: AI suggestions
- Decision #20: Graph versioning

## Related Modules

- [[projects/memory-tool/llm-integration]] - Provides AI suggestions
- [[projects/memory-tool/ui-system]] - Displays module tree/graph
- [[projects/memory-tool/core-system]] - Module file management
- [[projects/memory-tool/search-system]] - Searches module content
