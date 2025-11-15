# Module Organization Principles

> Principles and guidelines for organizing modules in memory_tool

**Version:** 1.0
**Created:** 2025-11-15
**Status:** Active

---

## Core Principles

### 1. Single Responsibility Principle (SRP)

Each module should have one, and only one, reason to change.

**Good:**
```
projects/memory-tool/search-engine/
projects/memory-tool/tui-browser/
```

**Bad:**
```
projects/memory-tool/search-and-ui-and-llm/  # Too many responsibilities
```

### 2. Cohesion Over Size

Module boundaries should be drawn by **topic cohesion**, not arbitrary size limits.

- High cohesion: All parts strongly related
- Low coupling: Minimal dependencies on other modules

### 3. Lifecycle Alignment

Parts that change together should stay together.

- If Feature A and B always update together → Same module
- If Feature A updates weekly, B monthly → Separate modules

---

## When to Split a Module

### Quantitative Triggers

Split when ANY of these conditions are met:

1. **Size Threshold**
   - `current.md` > 300 lines
   - Total module files > 3000 lines
   - More than 20 decisions

2. **Complexity Threshold**
   - More than 5 distinct topics
   - More than 10 outgoing [[connections]]
   - Archive size > 5MB

3. **Activity Threshold**
   - 3+ sections updated 3+ times per week
   - More than 50 timeline entries per month referencing this module

### Qualitative Indicators

Consider splitting when:

1. **Cognitive Load Test**
   - New person needs >20 minutes to understand module
   - Module description requires >3 sentences

2. **Change Impact Test**
   - Changes frequently affect multiple unrelated parts
   - Hard to isolate changes to one area

3. **Reusability Test**
   - Need to reference only part of module frequently
   - Other projects could use subset independently

4. **Team Boundary Test**
   - Different people/teams own different parts
   - Merge conflicts common in same module

---

## When to Use Hierarchical Modules

### Use Parent/Child Structure When:

✅ **Clear containment relationship**
```
projects/memory-tool/
├── core-system/           # Parent
│   ├── timeline/         # Child
│   └── search/           # Child
```

✅ **Shared context**
- All children relate to same project/area
- Common lifecycle (start/end together)
- Natural navigation path

✅ **Progressive disclosure**
- High-level understanding at parent
- Drill down for details in children

### Use Flat Structure When:

✅ **Independent concerns**
```
projects/
├── memory-tool/
├── personal-website/
└── blog/
```

✅ **Cross-cutting relationships**
- Modules connect in graph, not tree
- Multiple parents possible

✅ **Different lifecycles**
- Modules start/end independently

---

## Module Size Guidelines

### Small Module (Recommended)
- **Size:** 100-500 lines
- **Decisions:** 1-5
- **Topics:** Single concern
- **Example:** `projects/memory-tool/cli-commands/`

### Medium Module
- **Size:** 500-1500 lines
- **Decisions:** 5-15
- **Topics:** 2-3 related concerns
- **Example:** `projects/memory-tool/search-engine/`

### Large Module (Consider Splitting)
- **Size:** 1500-3000 lines
- **Decisions:** 15-30
- **Topics:** Multiple concerns
- **Warning:** May become hard to maintain

### Too Large (Must Split)
- **Size:** >3000 lines
- **Decisions:** >30
- **Topics:** Many unrelated concerns
- **Action Required:** Break into smaller modules

---

## Naming Conventions

### Project Modules
```
projects/[project-name]/[feature-or-subsystem]/
```
Examples:
- `projects/memory-tool/core-system/`
- `projects/memory-tool/module-system/`
- `projects/website/frontend/`

### Area Modules
```
areas/[domain-or-discipline]/
```
Examples:
- `areas/python-development/`
- `areas/ai-machine-learning/`
- `areas/productivity/`

### Resource Modules
```
resources/[resource-type]/
```
Examples:
- `resources/templates/`
- `resources/tools/`
- `resources/references/`

### Archive Modules
```
archive/[YYYY-MM]/[completed-project]/
```
Examples:
- `archive/2025-11/phase-1-implementation/`

---

## Cohesion Checklist

Before finalizing module boundaries, verify:

- [ ] Can describe module purpose in 1-2 sentences
- [ ] All content relates to single theme
- [ ] Changes to one file often require changing related files (high cohesion)
- [ ] Changes rarely require modifying other modules (low coupling)
- [ ] Someone can understand module independently
- [ ] Module has clear interfaces (well-defined [[connections]])
- [ ] No "god module" containing everything

---

## Migration Strategy

When splitting an existing module:

### Step 1: Analyze
```bash
# Identify distinct topics
ms "module-name" --semantic

# Check size and complexity
wc -l .memory/modules/module-name/*.md

# Review decisions
cat .memory/modules/module-name/decisions.md
```

### Step 2: Design
1. Identify natural boundaries (topics, lifecycle, team)
2. Sketch new structure
3. Map [[connections]] between new modules
4. Verify no circular dependencies

### Step 3: Execute
```bash
# Create new module structure
mmodule create projects/parent/child1
mmodule create projects/parent/child2

# Migrate content incrementally
# Move related decisions together
# Update [[links]] to new module names

# Archive old module
mmodule archive old-module-name
```

### Step 4: Validate
- [ ] All content migrated
- [ ] [[Links]] updated
- [ ] No broken connections (`mmodule check-links`)
- [ ] Timeline entries reference new modules
- [ ] Context regenerated (`mcontext`)

---

## Anti-Patterns to Avoid

### ❌ God Module
One module containing everything
```
memory-system/  # Contains: CLI, search, TUI, LLM, modules, decisions...
```

### ❌ Premature Splitting
Creating modules before understanding boundaries
```
projects/memory-tool/feature-a/
projects/memory-tool/feature-b/
# Later: A and B always change together → Should be one module
```

### ❌ Deep Nesting
More than 3 levels of hierarchy
```
projects/memory-tool/system/subsystem/component/subcomponent/  # Too deep!
```

### ❌ Artificial Boundaries
Splitting by arbitrary criteria (file type, date)
```
modules-created-in-november/  # Bad: Not cohesive
typescript-modules/           # Bad: Technology not topic
```

---

## Decision Framework

When deciding module structure, ask:

1. **Purpose:** What is this module's single responsibility?
2. **Scope:** What's included? What's explicitly excluded?
3. **Lifecycle:** When does it start? When is it complete?
4. **Owners:** Who maintains this? (can be same person/team)
5. **Dependencies:** What does it depend on? What depends on it?
6. **Size:** Is it the right size for its purpose?
7. **Navigation:** Can users easily find and understand it?

---

## Examples

### Good: Clear Separation
```
projects/memory-tool/
├── core-system/              # Data structures and storage
├── search-engine/            # Search algorithms and indexing
└── tui-browser/              # Terminal UI
```

Each has clear purpose, different lifecycle, minimal overlap.

### Good: Hierarchical When Appropriate
```
projects/memory-tool/llm-integration/
├── summarization/
├── embeddings/
└── providers/
```

All children relate to LLM integration parent.

### Bad: Mixed Concerns
```
projects/memory-tool/features-and-fixes/
├── search-improvements/
├── bug-fixes/
└── documentation/
```

No clear principle for what belongs here.

---

## References

Related decisions:
- [[memory-system/decisions#24]]: MCP deprioritization
- [[memory-system/decisions#25]]: Module system design

Related modules:
- [[projects/memory-tool/module-system]]: Implementation
- [[resources/module-templates]]: Templates

---

**Last Updated:** 2025-11-15
