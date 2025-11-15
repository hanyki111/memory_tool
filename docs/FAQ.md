# Frequently Asked Questions (FAQ)

> Common questions about memory_tool

---

## Table of Contents

### General
- [What is memory_tool?](#what-is-memory_tool)
- [Do I need Claude Code?](#do-i-need-claude-code)
- [Can I use it for personal projects?](#can-i-use-it-for-personal-projects)
- [Is it free?](#is-it-free)
- [Where is my data stored?](#where-is-my-data-stored)

### Installation
- [What are the system requirements?](#what-are-the-system-requirements)
- [Do I need to install from PyPI?](#do-i-need-to-install-from-pypi)
- [Can I install without git?](#can-i-install-without-git)
- [How do I uninstall?](#how-do-i-uninstall)

### Usage
- [What's the difference between timeline and modules?](#whats-the-difference-between-timeline-and-modules)
- [When should I create a module?](#when-should-i-create-a-module)
- [How do I search effectively?](#how-do-i-search-effectively)
- [Can I edit timeline files manually?](#can-i-edit-timeline-files-manually)

### Claude Code Integration
- [How does Claude Code integration work?](#how-does-claude-code-integration-work)
- [Do I need to run mcontext every time?](#do-i-need-to-run-mcontext-every-time)
- [What if Claude doesn't see my context?](#what-if-claude-doesnt-see-my-context)

### Advanced Features
- [Should I use vector search?](#should-i-use-vector-search)
- [Which LLM provider should I choose?](#which-llm-provider-should-i-choose)
- [How do [[wiki links]] work?](#how-do-wiki-links-work)

### Multiple Projects
- [Can I use memory_tool for multiple projects?](#can-i-use-memory_tool-for-multiple-projects)
- [How do I share knowledge between projects?](#how-do-i-share-knowledge-between-projects)
- [Can I have a global knowledge base?](#can-i-have-a-global-knowledge-base)

### Data Management
- [How do I backup my data?](#how-do-i-backup-my-data)
- [Can I sync across machines?](#can-i-sync-across-machines)
- [How much disk space does it use?](#how-much-disk-space-does-it-use)
- [How do I clean up old data?](#how-do-i-clean-up-old-data)

### Performance
- [Why is search slow?](#why-is-search-slow)
- [Why is vector search very slow?](#why-is-vector-search-very-slow)
- [How do I optimize performance?](#how-do-i-optimize-performance)

### Troubleshooting
- [Command not found](#command-not-found)
- [Encoding errors on Windows](#encoding-errors-on-windows)
- [Graph rebuild fails](#graph-rebuild-fails)
- [Search returns no results](#search-returns-no-results)

---

## General

### What is memory_tool?

memory_tool is a **Time-Space Integrated Knowledge System** that helps you:
1. **Capture** knowledge in 0.5 seconds (timeline)
2. **Organize** when you have time (modules)
3. **Retrieve** with powerful search
4. **Integrate** with Claude Code automatically

It separates **capture** (fast, during work) from **organization** (slow, during reviews).

**Philosophy:** "0.5초로 포착하고, 주말에 정리하며, 평생 활용한다."

---

### Do I need Claude Code?

**No!** memory_tool works standalone.

**Without Claude Code:**
- ✅ Record timeline (`m` command)
- ✅ Search (`ms` command)
- ✅ Organize modules
- ✅ All features work

**With Claude Code:**
- ✅ All of the above
- ✅ **Plus:** Automatic context generation
- ✅ Claude knows your recent work
- ✅ No manual context explanation

**Bottom line:** Useful without Claude, powerful with Claude.

---

### Can I use it for personal projects?

**Absolutely!** memory_tool is designed for:
- ✅ Personal coding projects
- ✅ Learning and research
- ✅ Side projects
- ✅ Work projects
- ✅ Multiple projects simultaneously

Each project gets its own `.memory/` directory, completely isolated.

---

### Is it free?

**Yes, core features are free!**

**Free:**
- ✅ Timeline recording
- ✅ Text search
- ✅ Module organization
- ✅ Claude Code integration
- ✅ All CLI commands

**Optional costs:**
- Vector search: Free (local processing)
- LLM features:
  - Ollama: **Free** (local)
  - Anthropic: **Paid** (~$1-5/month typical)

**Recommendation:** Start with free features, add paid if needed.

---

### Where is my data stored?

**Locally on your machine** in `.memory/` directory.

```
your-project/
└── .memory/
    ├── timeline/       # Your timeline entries
    ├── modules/        # Your modules
    ├── concepts/       # Your concepts
    └── config.yaml     # Your settings
```

**Privacy:**
- ✅ No cloud (unless you choose)
- ✅ No accounts
- ✅ No data collection
- ✅ You own the files

**Syncing:** Optional via Git, Dropbox, etc. (your choice)

---

## Installation

### What are the system requirements?

**Minimum:**
- Python 3.10+
- ~100MB disk space
- Git (for GitHub installation)

**Recommended:**
- Python 3.11 or 3.12
- 2GB+ RAM (for vector search)
- SSD (faster search)

**Operating systems:**
- ✅ Windows 10/11
- ✅ macOS 10.15+
- ✅ Linux (any modern distro)

---

### Do I need to install from PyPI?

**No!** You can install from GitHub:

```bash
pip install git+https://github.com/hanyki111/memory_tool.git
```

**PyPI release:** Coming after alpha testing period.

**Why GitHub first:**
- Faster iteration
- Community feedback
- Bug fixes without PyPI delays

---

### Can I install without git?

**No for now.** GitHub installation requires git.

**Workarounds:**
1. **Install git:** https://git-scm.com/downloads (recommended)
2. **Wait for PyPI:** Coming after alpha testing

**Why git required:**
- `pip install git+https://...` uses git internally
- Clones repository and installs

---

### How do I uninstall?

**Uninstall package:**
```bash
pip uninstall memory-tool
```

**Remove aliases (optional):**
```bash
malias uninstall
```

**Remove data (optional - WARNING: deletes everything!):**
```bash
# Windows
rmdir /s .memory

# Unix
rm -rf .memory
```

**Note:** Uninstalling the package does NOT delete your `.memory/` data unless you explicitly delete it.

---

## Usage

### What's the difference between timeline and modules?

**Timeline** = TIME dimension (when)
```
Work happens in time:
├── 09:00 - Started project
├── 10:30 - Made decision
└── 14:15 - Fixed bug

"I fixed that bug yesterday afternoon"
```

**Modules** = SPACE dimension (what)
```
Knowledge organizes by topic:
├── auth-system/
├── database/
└── api/

"What did I decide about authentication?"
```

**When to use each:**
- **Timeline:** Capture as you work (fast)
- **Modules:** Organize during reviews (slow)

**Analogy:**
- Timeline = Camera (capture everything)
- Modules = Photo album (organize later)

---

### When should I create a module?

**Create a module when:**
1. **Size:** Content > 100 lines
2. **Boundary:** Clear, focused topic
3. **Reusable:** Will reference again
4. **Complex:** Multiple decisions/concepts

**DON'T create for:**
- ❌ <100 lines of content
- ❌ One-time notes
- ❌ Unclear purpose
- ❌ "Just in case"

**Guidelines:**
- current.md > 300 lines → Consider split
- >20 decisions → Consider split
- >3 distinct topics → Consider split

**Full guide:** `.memory/docs/MODULE-ORGANIZATION-PRINCIPLES.md`

---

### How do I search effectively?

**Strategy:**

1. **Start with text search** (fastest)
   ```bash
   ms "keyword"
   ```

2. **Add filters if needed**
   ```bash
   ms "keyword" --after 2025-11-01
   ms "keyword" --timeline-only
   ```

3. **Try semantic if no results** (slower, smarter)
   ```bash
   ms --semantic "concept or question"
   ```

4. **Use hybrid for best results**
   ```bash
   ms --hybrid "query"
   ```

**Tips:**
- **Exact terms:** Text search
- **Concepts/questions:** Semantic search
- **Don't know:** Hybrid search
- **File names, errors:** Text search
- **"How to" questions:** Semantic search

---

### Can I edit timeline files manually?

**Yes!** Timeline files are plain markdown.

**Safe edits:**
```markdown
# Add missing entry
- 14:00 | Forgot to record this

# Fix typo
- 15:00 | Impelemented → Implemented feature

# Add context
- 16:00 | Fixed bug (in auth.py line 42)
```

**After editing:**
```bash
# Re-sort if needed
msort

# Rebuild search index
python -m memory_tool index optimize
```

**Best practice:**
- Use `m` command when possible
- Manual edits for corrections only
- Always run `msort` after time edits

---

## Claude Code Integration

### How does Claude Code integration work?

**Automatic:**
1. You run: `mcontext`
2. Creates: `.claude/memory-context.md`
3. Claude Code automatically reads this file
4. Claude knows your context!

**What's included:**
- Recent timeline (last 3 days)
- Active modules (current work)
- Key decisions (important choices)
- Connections (relationships)

**No manual work:**
- No copying
- No pasting
- No explaining

---

### Do I need to run mcontext every time?

**No!** Enable auto-update:

```yaml
# .memory/config.yaml
context:
  auto_update: true
```

**With auto-update:**
- Context regenerates after each `m` command
- Always up-to-date
- Never manual

**Without auto-update:**
- Run `mcontext` before Claude sessions
- More control
- Slightly faster `m` command

**Recommendation:** Enable auto-update (set it and forget it)

---

### What if Claude doesn't see my context?

**Checklist:**

1. **File exists?**
   ```bash
   ls .claude/memory-context.md
   ```

2. **Recently generated?**
   ```bash
   mcontext --force
   ```

3. **Claude Code reading .claude/ folder?**
   - Check Claude Code settings
   - Ensure project root is correct

4. **Context not empty?**
   ```bash
   cat .claude/memory-context.md
   # Should have content, not empty
   ```

**Fix:**
```bash
# Regenerate
mcontext --force

# Check
cat .claude/memory-context.md

# Restart Claude Code
```

---

## Advanced Features

### Should I use vector search?

**Consider vector search if:**
- ✅ Searching concepts, not keywords
- ✅ Asking questions ("how to authenticate users")
- ✅ Different terminology across timeline
- ✅ Large knowledge base (1000+ entries)

**Skip if:**
- ❌ Small project (<100 entries)
- ❌ Searching exact terms
- ❌ Limited resources (slow machine)
- ❌ Don't want 500MB dependency

**Installation:**
```bash
pip install git+https://github.com/hanyki111/memory_tool.git#egg=memory-tool[vector]
```

**Try before committing:**
- Start without vector search
- Add later if needed
- Not required for core functionality

---

### Which LLM provider should I choose?

**Anthropic (Claude):**
- ✅ Best quality
- ✅ Fast
- ✅ No local resources
- ❌ Costs money (~$1-5/month)
- ❌ Requires internet
- ❌ Data sent to cloud

**Ollama (Local):**
- ✅ Free
- ✅ Private (local)
- ✅ Offline
- ❌ Uses local resources
- ❌ Slower (unless GPU)
- ❌ Lower quality

**Recommendation:**
- **Start with Ollama** (free, try it out)
- **Upgrade to Anthropic** if quality matters
- **Cost-conscious:** Stick with Ollama

**Installation:**
```bash
# Both
pip install git+https://github.com/hanyki111/memory_tool.git#egg=memory-tool[llm]

# Ollama: Download from ollama.ai
# Anthropic: Get API key from console.anthropic.com
```

---

### How do [[wiki links]] work?

**Syntax:**
```markdown
We're using [[auth-system]] for authentication.
```

**Result:**
- Creates connection: current_file → auth-system
- Shows in graph visualization
- Navigable in TUI browser

**After adding links:**
```bash
python -m memory_tool module rebuild-graph
```

**Auto-rebuild:**
```bash
# Install git hooks
python -m memory_tool hooks install

# Now rebuilds automatically on git commit/merge
```

**Best practices:**
- Link generously
- Link as you write
- Use display text: `[[module|Display Name]]`
- Review graph periodically

**See also:** [USER_GUIDE.md - Wiki-style Connections](USER_GUIDE.md#wiki-style-connections)

---

## Multiple Projects

### Can I use memory_tool for multiple projects?

**Yes! Each project is independent.**

**Setup:**
```bash
# Project 1
cd ~/projects/todo-app
minit
m "Working on todo app"

# Project 2
cd ~/projects/blog
minit
m "Working on blog"
```

**Result:**
```
~/projects/
├── todo-app/
│   └── .memory/      # Independent
└── blog/
    └── .memory/      # Independent
```

**Searching:**
```bash
# Current project only (default)
ms "query"

# All projects
ms --all "query"
```

---

### How do I share knowledge between projects?

**Option 1: Wiki Links (Recommended)**
```markdown
# In project-a/.memory/modules/auth/current.md
Similar to [[../../project-b/modules/auth]]
```

**Option 2: Shared Knowledge Base**
```bash
# Create ~/kb/.memory/ as knowledge base
cd ~/kb
minit

# Link from projects
cd ~/projects/todo-app
# Use [[kb/concept]] in files
```

**Option 3: Git Submodules**
```bash
# Shared concepts as submodule
git submodule add ~/kb/.memory/modules/concepts .memory/modules/kb-concepts
```

**Recommendation:**
- **Small sharing:** Wiki links
- **Heavy sharing:** Shared KB
- **Team sharing:** Git submodules

---

### Can I have a global knowledge base?

**Yes!**

**Setup:**
```bash
# Create global KB
mkdir ~/knowledge-base
cd ~/knowledge-base
minit

# Add concepts
python -m memory_tool module create concepts/jwt-auth
python -m memory_tool module create concepts/rest-api
```

**Usage from projects:**
```bash
# Option A: Search with --with-kb
cd ~/projects/my-project
ms --with-kb "JWT"

# Option B: Link in files
# [[kb/concepts/jwt-auth]]
```

**Configuration:**
```yaml
# .memory/config.yaml
search:
  knowledge_base_path: ~/knowledge-base/.memory
```

**Recommendation:**
- Start without global KB
- Add when patterns emerge
- Don't over-organize upfront

---

## Data Management

### How do I backup my data?

**Method 1: Git (Recommended)**
```bash
# Initialize git
git init
echo ".DS_Store" >> .gitignore
echo "*.pyc" >> .gitignore

# Commit
git add .memory/
git commit -m "Backup knowledge base"

# Push to GitHub (optional, private repo)
git remote add origin https://github.com/you/your-project.git
git push -u origin main
```

**Method 2: Manual Copy**
```bash
# Compress
tar -czf memory-backup-$(date +%Y%m%d).tar.gz .memory/

# Or zip
zip -r memory-backup-$(date +%Y%m%d).zip .memory/
```

**Method 3: Cloud Sync**
- Put project in Dropbox/OneDrive/Google Drive
- .memory/ syncs automatically

**Recommendation:** Git (best for developers)

---

### Can I sync across machines?

**Yes! Multiple methods:**

**Method 1: Git (Best)**
```bash
# Machine 1
git push

# Machine 2
git pull
```

**Method 2: Cloud Storage**
- Put project in Dropbox/OneDrive
- Opens same project on multiple machines

**Method 3: Manual Rsync**
```bash
rsync -av --delete .memory/ user@remote:~/project/.memory/
```

**Conflicts:**
- Timeline rarely conflicts (time-ordered)
- Modules may conflict (resolve manually)
- Git handles conflicts well

---

### How much disk space does it use?

**Typical sizes:**
- 1 year timeline: **~1-5 MB**
- Search index: **~2-10 MB**
- Embeddings cache: **~10-100 MB** (if vector search used)
- Modules: **Varies** (depends on content)

**Total typical:** 15-115 MB per year

**Large projects (10,000+ entries):**
- Timeline: ~50-100 MB
- Search index: ~50-200 MB
- Embeddings: ~500-1000 MB

**Optimization:**
```bash
# Compress old timelines
find .memory/timeline -name "*.md" -mtime +365 -exec gzip {} \;

# Vacuum index
python -m memory_tool index vacuum

# Clear embedding cache (if needed)
rm -rf .memory/.embeddings-cache
```

---

### How do I clean up old data?

**Archive decisions:**
```bash
# Keep recent 10 decisions
python -m memory_tool archive decisions --keep-recent 10

# Archive by number
python -m memory_tool archive decisions --up-to 20
```

**Archive completed plans:**
```bash
python -m memory_tool archive plans PLAN-completed-feature
```

**Archive old modules:**
```bash
python -m memory_tool module archive old-module \
  --reason "No longer active"
```

**Compress old timelines:**
```bash
# Compress timelines older than 1 year
find .memory/timeline -name "*.md" -mtime +365 -exec gzip {} \;
```

**Delete (caution!):**
```bash
# Delete specific timeline
rm .memory/timeline/2024-01/15.md

# Delete old timelines (caution!)
rm -rf .memory/timeline/2024-01/
```

**Recommendation:**
- Archive, don't delete
- Storage is cheap
- Might need old data later

---

## Performance

### Why is search slow?

**Possible causes:**

1. **Large dataset** (10,000+ entries)
   ```bash
   # Optimize index
   python -m memory_tool index optimize
   ```

2. **First search after boot**
   - Loading index into memory
   - Subsequent searches faster

3. **No index optimization**
   ```bash
   # Check stats
   python -m memory_tool index stats

   # Optimize
   python -m memory_tool index optimize
   ```

4. **Slow disk** (HDD vs SSD)
   - SSD: ~0.05s
   - HDD: ~0.5-1s

**Solutions:**
```bash
# Weekly optimization
python -m memory_tool index optimize

# Enable result caching
# .memory/config.yaml
search:
  cache_results: true
  cache_ttl: 3600
```

---

### Why is vector search very slow?

**Possible causes:**

1. **First run** (loading model)
   - First: 2-3 seconds (loading model)
   - After: 0.1-0.5 seconds (cached)

2. **CPU-only processing**
   ```bash
   # Check GPU
   python -c "import torch; print(torch.cuda.is_available())"

   # If True, install GPU version
   pip uninstall sentence-transformers
   pip install sentence-transformers[gpu]

   # Result: ~10x faster
   ```

3. **Large dataset** (1000+ files)
   - Pre-index embeddings:
   ```bash
   python -c "
   from memory_tool.search.vector import VectorSearch
   vs = VectorSearch()
   vs.preindex_timeline()
   "
   ```

4. **Embedding cache disabled**
   ```yaml
   # .memory/config.yaml
   search:
     cache_embeddings: true  # Enable!
   ```

**Solutions:**
```bash
# Best: GPU + caching
pip install sentence-transformers[gpu]

# .memory/config.yaml
search:
  cache_embeddings: true
  device: cuda
```

---

### How do I optimize performance?

**Regular maintenance:**
```bash
# Weekly
python -m memory_tool index optimize

# Monthly
python -m memory_tool index vacuum
```

**Enable caching:**
```yaml
# .memory/config.yaml
search:
  cache_results: true
  cache_embeddings: true
performance:
  batch_embeddings: true
  incremental_index: true
```

**Hardware:**
- **SSD** vs HDD: ~10x faster
- **GPU** for vector search: ~10x faster
- **More RAM:** Helps with large datasets

**Minimize index rebuilds:**
```bash
# Don't run unnecessarily
python -m memory_tool module rebuild-graph  # Only when needed
```

---

## Troubleshooting

### Command not found

**Symptom:**
```bash
$ m "test"
bash: m: command not found
```

**Cause:** Aliases not installed or PATH not set

**Solution:**

**Option 1: Install aliases**
```bash
malias install --powershell  # Windows
malias install --shell bash  # Unix
```

**Option 2: Use full command**
```bash
python -m memory_tool record "test"
```

**Option 3: Check PATH (Windows batch)**
```powershell
$env:Path -split ';' | Select-String ".memory"
# Should show: C:\Users\You\.memory\bin
```

**Option 4: Reinstall**
```bash
malias uninstall
malias install --powershell
# Restart terminal
```

---

### Encoding errors on Windows

**Symptom:**
```
UnicodeDecodeError: 'charmap' codec can't decode byte...
```

**Cause:** Windows console encoding (not UTF-8)

**Solution:**

**Option 1: PowerShell encoding**
```powershell
# Add to $PROFILE
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
```

**Option 2: Use Windows Terminal**
- Download: Microsoft Store
- UTF-8 by default
- Better terminal overall

**Option 3: Python encoding**
```bash
# Set environment variable
$env:PYTHONIOENCODING = "utf-8"
```

**Option 4: Output to file**
```bash
ms "query" > results.txt
# Then open results.txt (UTF-8)
```

---

### Graph rebuild fails

**Symptom:**
```
Error rebuilding graph
Database is locked
```

**Cause:** Another process accessing database

**Solution:**

**Option 1: Close other terminals**
- Close other terminals running memory_tool
- Try again

**Option 2: Kill lock**
```bash
# Close all memory_tool processes
# Windows
taskkill /F /IM python.exe /FI "WINDOWTITLE eq memory_tool*"

# Unix
pkill -f memory_tool
```

**Option 3: Rebuild database**
```bash
# Backup first!
cp .memory/.connections.db .memory/.connections.db.backup

# Delete and rebuild
rm .memory/.connections.db
python -m memory_tool module rebuild-graph
```

---

### Search returns no results

**Symptom:**
```bash
ms "keyword"
# Found 0 results
```

**But you know the keyword exists.**

**Possible causes:**

1. **Case sensitive**
   ```bash
   # Try case-insensitive
   ms -i "keyword"
   ```

2. **Index not built**
   ```bash
   python -m memory_tool index rebuild
   ```

3. **Wrong directory**
   ```bash
   pwd
   # Make sure you're in project root (where .memory/ is)
   ```

4. **Typo in keyword**
   ```bash
   # Try partial match
   ms "keywor"

   # Try regex
   ms "ke.*word"
   ```

5. **File not indexed**
   ```bash
   # Optimize index
   python -m memory_tool index optimize
   ```

**Solution:**
```bash
# Full reset
python -m memory_tool index rebuild
python -m memory_tool module rebuild-graph

# Try again
ms "keyword"
```

---

## Still Need Help?

**Resources:**
- 📚 [USER_GUIDE.md](USER_GUIDE.md) - Complete guide
- 🚀 [QUICKSTART.md](QUICKSTART.md) - 5-minute start
- 💾 [INSTALLATION.md](INSTALLATION.md) - Installation guide
- 🐛 [GitHub Issues](https://github.com/hanyki111/memory_tool/issues) - Report bugs

**Before posting an issue:**
1. Check this FAQ
2. Check USER_GUIDE.md
3. Try with `--help` flag
4. Include:
   - OS and Python version
   - Command you ran
   - Full error message
   - Steps to reproduce

---

**Happy knowledge capturing!** 🚀

> "0.5초로 포착하고, 주말에 정리하며, 평생 활용한다."
