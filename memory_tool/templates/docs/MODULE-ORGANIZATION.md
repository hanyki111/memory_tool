# Module Organization

> Complete guide for organizing modules in memory_tool

**Version:** 2.0
**Status:** Active

---

## Part 1: Quick Reference

### When to Create a New Module?

**Create When:**
- Starting a new project: `mmodule create projects/new-project`
- New major feature (>500 lines expected)
- Independent concern (different topic, lifecycle)
- Reusable component

**Don't Create When:**
- Small enhancement (<100 lines) → Add to existing module
- Tightly coupled to existing module → Extend it
- Temporary experiment → Use timeline

### When to Split an Existing Module?

| Priority | Criteria |
|----------|----------|
| 🔴 Must Split | current.md > 300 lines, >30 decisions, >5 topics |
| 🟡 Consider | current.md > 200 lines, >20 decisions, >3 topics |
| 🟢 Keep As-Is | current.md < 200 lines, <20 decisions, single topic |

### Hierarchy vs Flat?

**Use Hierarchy** (`projects/parent/child`):
- Clear containment (child IS-PART-OF parent)
- Shared context/project
- Same lifecycle

**Use Flat** (`projects/module-a`):
- Independent concerns
- Different lifecycles
- Cross-cutting relationships

### Quick Commands

```bash
mmodule create projects/my-project     # Create module
mmodule tree                           # View hierarchy
mmodule graph                          # View connections
mmodule check-links                    # Find broken links
mcheck                                 # Validate Related Files
```

### Related Files Section

Add to top of `current.md`:

```markdown
## Related Files

- **Source:** `src/my-feature/`
- **Tests:** `tests/my-feature/`
- **Docs:** `docs/my-feature.md`
```

Validate with: `mcheck`

---

## Part 2: Core Principles

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

## Part 3: Detailed Guidelines

### Module Size Guidelines

| Size | Lines | Decisions | Topics | Action |
|------|-------|-----------|--------|--------|
| Small (Recommended) | 100-500 | 1-5 | Single | Maintain |
| Medium | 500-1500 | 5-15 | 2-3 related | Monitor |
| Large | 1500-3000 | 15-30 | Multiple | Consider splitting |
| Too Large | >3000 | >30 | Many unrelated | Must split |

### Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Project feature | `projects/[project]/[feature]` | `projects/memory-tool/search-system` |
| Area of interest | `areas/[domain]` | `areas/python-development` |
| Reusable resource | `resources/[type]` | `resources/api-templates` |
| Completed project | `archive/[YYYY-MM]/[name]` | `archive/2025-11/phase-1` |

### Hierarchical Modules (Parent/Child)

Use when:
- Clear containment relationship
- All children relate to same project/area
- Common lifecycle (start/end together)

Example:
```
projects/memory-tool/              # Root module (parent)
├── module.md                      # Project overview
├── current.md                     # Project status
├── core-system/                   # Sub-module (child)
├── module-system/                 # Sub-module (child)
└── search-system/                 # Sub-module (child)
```

### Root Module Files

**module.md should contain:**
- Project purpose and goals
- High-level architecture
- List of sub-modules with links
- Key architectural decisions

**current.md should contain:**
- Overall project status (phase, progress)
- Recent major updates
- Status of each sub-module (1-2 lines)
- Next steps and priorities

---

## Part 4: Anti-Patterns

### God Module
One module containing everything.
```
memory-system/  # Contains: CLI, search, TUI, LLM, modules...
```
**Fix:** Split by feature/responsibility.

### Premature Splitting
Creating modules before understanding boundaries.
```
projects/memory-tool/feature-a/
projects/memory-tool/feature-b/
# Later: A and B always change together
```
**Fix:** Wait until natural boundaries emerge.

### Deep Nesting
More than 3 levels of hierarchy.
```
projects/a/b/c/d/e/  # Too deep!
```
**Fix:** Flatten or reorganize.

### Artificial Boundaries
Splitting by arbitrary criteria.
```
modules-created-in-november/  # Bad: Not cohesive
typescript-modules/           # Bad: Technology not topic
```
**Fix:** Split by topic/responsibility.

---

## Part 5: Decision Framework

When deciding module structure, ask:

1. **Purpose:** What is this module's single responsibility?
2. **Scope:** What's included? What's explicitly excluded?
3. **Lifecycle:** When does it start? When is it complete?
4. **Dependencies:** What does it depend on? What depends on it?
5. **Size:** Is it the right size for its purpose?
6. **Navigation:** Can users easily find and understand it?

### Decision Tree

```
Need to track something?
│
├─ Is it part of existing module?
│  ├─ Yes → Add to existing
│  └─ No ↓
│
├─ Is it >100 lines?
│  ├─ No → Use timeline
│  └─ Yes ↓
│
├─ Single topic?
│  ├─ No → Split into multiple
│  └─ Yes ↓
│
├─ Part of existing project?
│  ├─ Yes → Create child module (projects/parent/child)
│  └─ No → Create new project (projects/new-project)
│
└─ Create module!
```

---

## Part 6: Migration Strategy

When splitting an existing module:

### Step 1: Analyze
```bash
ms "module-name" --semantic     # Identify topics
wc -l .memory/modules/module-name/*.md  # Check size
```

### Step 2: Design
1. Identify natural boundaries (topics, lifecycle)
2. Sketch new structure
3. Map [[connections]] between new modules
4. Verify no circular dependencies

### Step 3: Execute
```bash
mmodule create projects/parent/child1
mmodule create projects/parent/child2
# Migrate content incrementally
# Update [[links]] to new module names
mmodule archive old-module-name
```

### Step 4: Validate
- All content migrated
- [[Links]] updated
- No broken connections (`mmodule check-links`)
- Context regenerated (`mcontext`)

---

## Part 7: Checklist

### Before Creating Module
- [ ] Can describe purpose in 1-2 sentences?
- [ ] Does it have single responsibility?
- [ ] Will it have >100 lines of content?
- [ ] Does it have clear boundaries?
- [ ] Is it independent enough?

### Before Splitting Module
- [ ] current.md > 300 lines?
- [ ] >20 decisions?
- [ ] >3 distinct topics?
- [ ] Takes >20min to understand?
- [ ] Natural boundaries identified?

### Cohesion Check
- [ ] All content relates to single theme
- [ ] Changes rarely require modifying other modules
- [ ] Someone can understand module independently
- [ ] No "god module" containing everything

---

**Generated by Memory Tool**
