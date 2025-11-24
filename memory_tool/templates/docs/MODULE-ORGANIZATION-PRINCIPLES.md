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

## Project Root Modules

### What is a Project Root Module?

A **project root module** serves as the parent container and overview for a collection of related sub-modules.

**Example:**
```
projects/memory-tool/              # Root module (parent)
├── module.md                      # Project overview
├── current.md                     # Project status
├── core-system/                   # Sub-module (child)
├── module-system/                 # Sub-module (child)
├── search-system/                 # Sub-module (child)
└── ui-system/                     # Sub-module (child)
```

### When to Create a Project Root Module

✅ **Create when:**

1. **Multiple sub-modules exist** (3+ sub-modules)
   - `projects/memory-tool/core-system`, `module-system`, `search-system`
   - Parent `projects/memory-tool` provides overview

2. **Need project-wide overview**
   - Architecture decisions affecting all sub-modules
   - Shared dependencies and relationships
   - Overall project status and roadmap

3. **Sub-modules share lifecycle**
   - All start/end together as a project
   - Common milestones and phases
   - Coordinated releases

4. **External users need context**
   - Onboarding new contributors
   - Understanding project structure
   - Navigating to relevant sub-modules

❌ **Don't create when:**

1. **Only 1-2 sub-modules** (not enough to warrant root)
2. **Sub-modules are independent** (different projects)
3. **No shared context** (unrelated concerns)

### Root Module Structure

**Essential files:**
```
projects/my-project/
├── module.md                     # REQUIRED: Project definition
│   ├── Purpose
│   ├── Scope
│   ├── Architecture
│   ├── Sub-modules (list + links)
│   └── Key decisions
│
└── current.md                    # REQUIRED: Project status
    ├── Phase progress
    ├── Recent updates
    ├── Sub-module status
    └── Next steps
```

**Optional files:**
```
projects/my-project/
├── decisions.md                  # Project-wide decisions
├── dependencies.md               # External dependencies
└── PLAN-*.md                     # Project plans
```

### Content Guidelines

**module.md should contain:**
- ✅ Project purpose and goals
- ✅ High-level architecture
- ✅ List of sub-modules with brief descriptions
- ✅ Links to sub-modules: `[[projects/my-project/sub-module]]`
- ✅ Key architectural decisions
- ✅ Technology stack overview

**module.md should NOT contain:**
- ❌ Detailed implementation (belongs in sub-modules)
- ❌ Duplicate content from sub-modules
- ❌ Low-level technical details

**current.md should contain:**
- ✅ Overall project status (phase, progress)
- ✅ Recent major updates
- ✅ Status of each sub-module (1-2 lines each)
- ✅ Next steps and priorities
- ✅ Key metrics (optional)

**current.md should NOT contain:**
- ❌ Detailed sub-module status (belongs in sub-module/current.md)
- ❌ Daily updates (use timeline instead)
- ❌ Low-priority details

### Hierarchy Detection

With project root modules, the module system automatically detects parent-child relationships:

**Directory structure:**
```
.memory/modules/
└── projects/
    └── memory-tool/              # Parent (has current.md)
        ├── core-system/          # Child (has current.md)
        └── search-system/        # Child (has current.md)
```

**Automatic behavior:**
1. **Module graph** shows parent-child edges
2. **JSON export** includes `type: "parent-child"` edges
3. **No orphaned modules** (all connected via hierarchy)
4. **Visual navigation** (tree view enabled)

### Best Practices

**DO:**
- ✅ Keep root module high-level (overview only)
- ✅ Update `current.md` when project phase changes
- ✅ Link to sub-modules for details
- ✅ Record project-wide decisions in root `decisions.md`
- ✅ Use root module as entry point for new users

**DON'T:**
- ❌ Duplicate sub-module content in root
- ❌ Make root module too detailed (defeats purpose)
- ❌ Skip creating root when 3+ sub-modules exist
- ❌ Mix project overview with implementation details

### Examples

**Good: Clear Hierarchy**
```
projects/memory-tool/
├── module.md                     # 300 lines: Overview, architecture, sub-modules
├── current.md                    # 150 lines: Phase status, recent updates
├── core-system/                  # 500 lines total: Implementation details
├── module-system/                # 600 lines total: Implementation details
└── search-system/                # 400 lines total: Implementation details
```

**Bad: Flat Structure (Missing Root)**
```
projects/memory-tool-core/        # Independent, no hierarchy
projects/memory-tool-search/      # Independent, no hierarchy
projects/memory-tool-ui/          # Independent, no hierarchy
# Problem: No overview, unclear relationships
```

**Bad: Root Too Detailed**
```
projects/memory-tool/
└── module.md                     # 3000 lines: Contains all implementation
    # Problem: Defeats purpose, should be in sub-modules
```

### Migration: Adding Root to Existing Sub-modules

If you have sub-modules without a root:

**Step 1: Check if root is needed**
```bash
# Count sub-modules
mmodule list | grep "projects/my-project/" | wc -l
# If 3+, create root
```

**Step 2: Create root module files**
```bash
# Create module.md (project overview)
# Create current.md (project status)
# Place in .memory/modules/projects/my-project/
```

**Step 3: Verify hierarchy**
```bash
# Check parent-child edges
python -m memory_tool module graph --format json
# Should see "type": "parent-child" edges
```

**Step 4: Update references**
- Update sub-module `module.md` files to reference parent (optional)
- Update documentation to use root as entry point
- Regenerate context: `mcontext`

### Detection Logic

The module system treats a directory as a root module if:
1. Contains `current.md` (module marker)
2. Has sub-directories that are also modules
3. Sub-modules have parent path as prefix

Example:
- `projects/memory-tool/` is root if:
  - `projects/memory-tool/current.md` exists ✓
  - `projects/memory-tool/core-system/current.md` exists ✓
  - Path relationship: child starts with parent path ✓

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

**Last Updated:** 2025-11-24
