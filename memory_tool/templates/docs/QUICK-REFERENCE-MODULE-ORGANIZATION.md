# Quick Reference: Module Organization

> Quick decision guide for module organization

---

## When to Create a New Module?

### ✅ Create New Module When:

1. **Starting a new project**
   ```bash
   mmodule create projects/new-project
   ```

2. **New major feature (>500 lines expected)**
   ```bash
   mmodule create projects/main-project/new-feature
   ```

3. **Independent concern** (different topic, lifecycle, or team)

4. **Reusable component**
   ```bash
   mmodule create resources/templates/api-design
   ```

### ❌ Don't Create New Module When:

1. **Small enhancement (<100 lines)**
   → Add to existing module

2. **Tightly coupled** to existing module
   → Extend existing module

3. **Temporary experiment**
   → Use timeline or scratch space

4. **Just organizing files**
   → Use subdirectories within module

---

## When to Split an Existing Module?

### 🔴 Must Split (High Priority):
- [ ] current.md > 300 lines
- [ ] Total files > 3000 lines
- [ ] >30 decisions
- [ ] >5 unrelated topics
- [ ] Multiple people frequently conflict

### 🟡 Consider Splitting (Medium Priority):
- [ ] current.md > 200 lines
- [ ] Total files > 2000 lines
- [ ] >20 decisions
- [ ] >3 topics
- [ ] Takes >20min to understand

### 🟢 Keep As-Is (Low Priority):
- [ ] current.md < 200 lines
- [ ] Total files < 2000 lines
- [ ] <20 decisions
- [ ] Single topic
- [ ] Clear and focused

---

## Module Hierarchy vs Flat?

### Use Hierarchy (projects/parent/child) When:
```
✅ Clear containment (child IS-PART-OF parent)
✅ Shared context/project
✅ Same lifecycle
✅ Progressive disclosure needed
```

**Example:**
```
projects/memory-tool/
├── core-system/
├── search-system/
└── ui-system/
```

### Use Flat (projects/module-a, projects/module-b) When:
```
✅ Independent concerns
✅ Different lifecycles
✅ Cross-cutting relationships
✅ Multiple potential parents
```

**Example:**
```
projects/
├── memory-tool/
├── personal-blog/
└── portfolio-site/
```

---

## Naming Quick Guide

| Type | Pattern | Example |
|------|---------|---------|
| Project feature | `projects/[project]/[feature]` | `projects/memory-tool/search-system` |
| Area of interest | `areas/[domain]` | `areas/python-development` |
| Reusable resource | `resources/[type]` | `resources/api-templates` |
| Completed project | `archive/[YYYY-MM]/[name]` | `archive/2025-11/phase-1` |

---

## Quick Checklist Before Creating Module

- [ ] Can describe purpose in 1-2 sentences?
- [ ] Does it have single responsibility?
- [ ] Is it the right size (not too small, not too large)?
- [ ] Does it have clear boundaries?
- [ ] Will it have >100 lines of content?
- [ ] Is it independent enough?
- [ ] Does hierarchy make sense (if nested)?

If all ✅ → Create module
If mostly ❌ → Add to existing module or reconsider

---

## Quick Commands

```bash
# Create flat module
mmodule create projects/my-project

# Create hierarchical module
mmodule create projects/my-project/feature-a

# Check if module should split (manual check)
wc -l .memory/modules/my-module/*.md

# View module tree
mmodule tree

# View connections
mmodule graph

# Check for issues
mmodule check-links
```

---

## Common Patterns

### Pattern 1: Feature System
```
projects/app-name/
├── auth-system/
├── data-layer/
└── ui-layer/
```

### Pattern 2: Component Library
```
resources/
├── ui-components/
├── api-patterns/
└── deployment-configs/
```

### Pattern 3: Learning Area
```
areas/
├── machine-learning/
│   ├── neural-networks/
│   └── nlp/
└── web-development/
```

### Pattern 4: Timeboxed Projects
```
projects/
└── 2025-goals/
    ├── q1-objectives/
    ├── q2-objectives/
    └── review/
```

---

## Red Flags

### 🚩 Module Too Large
```
Symptoms:
- Hard to navigate
- Many unrelated topics
- Frequent conflicts
- Long current.md

Action: Split by topic/feature
```

### 🚩 Too Many Small Modules
```
Symptoms:
- Lots of <50 line modules
- Frequent cross-module references
- Unclear boundaries

Action: Merge related modules
```

### 🚩 Deep Nesting (>3 levels)
```
Symptoms:
- projects/a/b/c/d/e/
- Hard to navigate
- Unclear relationships

Action: Flatten or reorganize
```

### 🚩 Unclear Purpose
```
Symptoms:
- Can't explain in 1 sentence
- "Miscellaneous" in name
- Everything goes here

Action: Split by clear criteria
```

---

## Decision Tree

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

## Example: Deciding on memory-system Split

**Question:** Should I split memory-system?

**Analysis:**
- [x] Size: 2000 lines ✓ (approaching 3000)
- [x] Decisions: 29 ✓ (approaching 30)
- [x] Topics: 7 distinct ✓ (>5)
- [x] Cognitive load: 25+ min ✓ (>20)
- [x] Update freq: Daily across multiple topics ✓

**Answer:** ✅ YES, split recommended

**Approach:** Feature-based split into 6 modules:
- core-system
- search-system
- module-system
- ui-system
- llm-integration
- project-management

---

## Resources

- Full principles: `.memory/modules/MODULE-ORGANIZATION-PRINCIPLES.md`
- Migration plan: `.memory/modules/memory-system/MIGRATION-PLAN.md`
- Module commands: `mmodule --help`

---

**Last Updated:** 2025-11-15
