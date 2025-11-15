# Quick Start Guide

> Get started with memory_tool in 5 minutes

---

## ⚡ 30-Second Start

```bash
# 1. Install
pip install git+https://github.com/hanyki111/memory_tool.git

# 2. Initialize
cd your-project
minit

# 3. Start recording
m "프로젝트 시작!"
```

**Done!** You're now capturing knowledge. 🎉

---

## 🎯 5-Minute Complete Guide

### Step 1: Install (1 minute)

```bash
# Install from GitHub
pip install git+https://github.com/hanyki111/memory_tool.git

# Verify
python -m memory_tool --version
# Output: memory-tool 1.0.0-alpha
```

**Trouble?** See [INSTALLATION.md](INSTALLATION.md)

---

### Step 2: Initialize Your Project (30 seconds)

```bash
# Go to your project directory
cd /path/to/your/project

# Initialize .memory/ structure
minit
```

**What happened?**
```
.memory/
├── timeline/     # Your time-based records
├── modules/      # Organized knowledge
├── concepts/     # Conceptual knowledge
└── config.yaml   # Settings
```

---

### Step 3: Record Your First Entry (30 seconds)

```bash
# Record what you're doing right now
m "Started using memory_tool"

# Record a decision
m "Decision: Using PostgreSQL instead of MySQL"

# Record with context
m "Fixed bug in auth.py line 45 - was checking wrong condition"
```

**Tip:** Think of `m` as your "external brain capture button". Hit it whenever:
- You start something new
- You make a decision
- You solve a problem
- You learn something

**The 0.5-second principle:** Recording should be so fast you do it without thinking.

---

### Step 4: Search Your Knowledge (30 seconds)

```bash
# Find entries
ms "auth"

# Case-insensitive search
ms -i "postgresql"

# Search with regex
ms "bug.*fix"
```

**Output example:**
```
.memory\timeline\2025-11\15.md:3
  - 17:45 | Fixed bug in auth.py line 45 - was checking wrong condition

Found 1 result(s)
```

---

### Step 5: View Your Timeline (30 seconds)

```bash
# Today's timeline
mtoday

# This week
mweek

# Check statistics
mstatus
```

**Example output:**
```
=== Today's Timeline ===
2025-11-15

- 17:30 | Started using memory_tool
- 17:35 | Decision: Using PostgreSQL instead of MySQL
- 17:45 | Fixed bug in auth.py line 45 - was checking wrong condition
```

---

### Step 6: Create Context for Claude Code (1 minute)

If you're using Claude Code, this is the killer feature:

```bash
# Generate context from your timeline
mcontext
```

**What happened?**
- Created `.claude/memory-context.md`
- Includes recent timeline entries
- Includes active modules
- Includes key decisions

**Result:** Next time you open Claude Code, it automatically knows what you've been working on! 🤖

---

## 🎓 3-Minute Concept Tutorial

### Understanding Time + Space

memory_tool combines two dimensions:

#### 📅 Time (Timeline)
```bash
m "Fixed login bug"     # Captured at 17:45
m "Added new feature"   # Captured at 18:20
```

**Why?** You work in time order. Your brain remembers "I fixed that bug yesterday afternoon".

#### 📦 Space (Modules)
```bash
# Create a module for a feature
python -m memory_tool module create auth-system

# Organize knowledge by topic
# .memory/modules/auth-system/current.md
```

**Why?** You organize by topics. Your brain thinks "What did I decide about authentication?"

#### 🔗 Connections (Links)
```markdown
# In any file, use [[wiki links]]
We're using [[auth-system]] with [[database/postgres]]
```

**Why?** Knowledge is connected. Your brain links "auth uses database".

---

## 📚 Core Commands (2-Minute Reference)

### Recording
```bash
m "message"              # Record now
m --time "14:30" "msg"   # Specific time
m --yesterday "msg"      # Yesterday
```

### Searching
```bash
ms "query"               # Text search
ms -i "Query"            # Case-insensitive
ms --semantic "concept"  # Semantic search (if installed)
```

### Viewing
```bash
mtoday                   # Today's timeline
mweek                    # This week
mstatus                  # Statistics
```

### Organizing
```bash
python -m memory_tool module create my-module    # Create module
python -m memory_tool module list                # List modules
python -m memory_tool module tree                # Tree view
```

### Claude Code
```bash
mcontext                 # Generate context
```

### Advanced
```bash
msummary                 # Summarize with AI (if llm installed)
mbrowse                  # Interactive TUI (if tui installed)
```

---

## 🚀 Quick Workflows

### Daily Work Flow

```bash
# Morning: Review yesterday
mweek

# During work: Capture everything
m "Starting feature X"
m "Found issue with Y"
m "Decision: Choosing approach Z"

# Evening: Context for tomorrow
mcontext
```

### Project Start

```bash
# 1. Initialize
minit

# 2. Document initial state
m "Project: Building todo app with React + FastAPI"
m "Tech stack decided: React, FastAPI, PostgreSQL, Docker"

# 3. Create project module
python -m memory_tool module create projects/todo-app

# 4. Start working
m "Created initial project structure"
```

### Research Session

```bash
# While reading/learning
m "Learned: JWT tokens expire after 24h by default"
m "Resource: https://jwt.io/introduction"
m "Note: Consider refresh tokens for better UX"

# Search later
ms "JWT"
```

### Bug Fixing

```bash
# When you encounter a bug
m "Bug: Users can't login after password reset"

# As you investigate
m "Found: Password hash not updating in DB"
m "Root cause: Missing commit() in reset_password()"

# After fixing
m "Fixed: Added db.commit() in user_service.py line 142"
m "Tested: Password reset now works correctly"
```

---

## ⚙️ Optional Setup (5 minutes)

### Install Aliases (Recommended)

**Windows PowerShell:**
```bash
malias install --powershell
# Restart terminal
```

**Unix (Bash/Zsh):**
```bash
malias install --shell bash
echo 'source ~/.memory/aliases.sh' >> ~/.bashrc
source ~/.bashrc
```

**Result:** Type `m` instead of `python -m memory_tool record`

### Enable AI Features (Optional)

```bash
# Install LLM support
pip install git+https://github.com/hanyki111/memory_tool.git#egg=memory-tool[llm]

# Option A: Use Ollama (free, local)
# 1. Install Ollama: https://ollama.ai
# 2. Pull model: ollama pull llama2
# 3. Configure:
cat > .memory/config.yaml << EOF
llm:
  provider: ollama
  model: llama2
EOF

# Option B: Use Claude (paid, best quality)
export ANTHROPIC_API_KEY=sk-ant-...
cat > .memory/config.yaml << EOF
llm:
  provider: anthropic
  model: claude-3-haiku-20240307
EOF

# Try it
msummary
```

---

## 🎯 Success Checklist

After 5 minutes, you should be able to:

- [ ] Record entries with `m "message"`
- [ ] Search with `ms "query"`
- [ ] View timeline with `mtoday`
- [ ] Generate context with `mcontext`
- [ ] Understand time + space organization

**If any fail,** see [Troubleshooting](INSTALLATION.md#troubleshooting)

---

## 🔥 Pro Tips

1. **Capture More Than You Think**
   - Too much is better than too little
   - You can always ignore, but can't recover lost thoughts

2. **Use Natural Language**
   - Not formal documentation
   - Write how you think
   - "Fixed that annoying bug" is fine

3. **Record Decisions Explicitly**
   - Start with "Decision:"
   - Future you will thank you
   - Example: "Decision: Not using microservices - team too small"

4. **Search is Your Friend**
   - Forgot something? Search it
   - `ms "pattern"` is faster than scrolling

5. **Context is Magic**
   - Run `mcontext` before Claude Code sessions
   - It remembers what you forget

---

## 📖 What's Next?

You now know enough to be productive!

**Learn more:**
- 📚 [USER_GUIDE.md](USER_GUIDE.md) - Complete guide with all features
- ❓ [FAQ.md](FAQ.md) - Common questions
- 🎯 [Real-world workflows](USER_GUIDE.md#part-3-real-world-workflows)

**Get advanced:**
- 🔍 [Vector search](USER_GUIDE.md#vector-search--semantic)
- 🤖 [LLM features](USER_GUIDE.md#llm-integration)
- 🌐 [Module organization](USER_GUIDE.md#module-system)
- 📊 [TUI browser](USER_GUIDE.md#interactive-tui-browser)

---

## 💡 Philosophy Reminder

> **"0.5초로 포착하고, 주말에 정리하며, 평생 활용한다."**

- ⚡ **Capture First** - Don't organize while working
- 📅 **Organize Later** - Weekend review sessions
- 🎯 **Use Forever** - Your external brain, for life

---

**Questions?** Check [FAQ.md](FAQ.md) or open an issue: https://github.com/hanyki111/memory_tool/issues

**Happy capturing!** 🚀
