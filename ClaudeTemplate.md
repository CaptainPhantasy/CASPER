# CLAUDE.md Template

## ⚡ **CRITICAL: BUILD CHEATSHEET FIRST**

**🎯 IMMEDIATELY create `CheatSheet.md` with exact file:line locations as you explore code.**

**❌ DO NOT:** Explore without documenting, read files without indexing locations
**✅ DO:** Build CheatSheet.md in real-time with precise file:line references

## CheatSheet Requirements

**Create `CheatSheet.md` with these sections:**
```markdown
# [PROJECT] Codebase CheatSheet

## 📍 CRITICAL CODE LOCATIONS
- **Main Entry**: `file.ext:XX-YY` - description
- **Core Logic**: `file.ext:XX-YY` - description
- **Configuration**: `file.ext:XX-YY` - description

## 🚀 QUICK DEVELOPMENT TASKS
### Adding [Feature Type]
```language
# 1. Modify: file.ext:XX-YY
code_template_here

# 2. Test: file.ext:XX-YY
test_template_here
```

## 🚨 EMERGENCY FIXES
- **[Issue Type]**: `file.ext:XX-YY` - fix location
```

## Project Template

**[PROJECT_NAME]**: [Brief description]
- **[Stack A]**: [Technology] ([Port]) - [Purpose]
- **[Stack B]**: [Technology] ([Port]) - [Purpose]
- **Architecture**: [Pattern description]

## Quick Commands

```bash
[start_command]          # [Description]
[test_command]           # [Description]
[lint_command]           # [Description]
```

## Configuration

**Required environment:**
```bash
[KEY_1]=[value]
[KEY_2]=[value]
```

## Agent Standards

1. Check `conflicts.md` before starting
2. Log with ISO 8601 timestamps (UTC)
3. Update CheatSheet.md as you discover code locations
4. Include verification commands

**Progress Format:**
```markdown
### ✅ [Task] - [STATUS]
- **Timestamp:** YYYY-MM-DDTHH:MM:SS UTC
- **Fix:** [Actions taken]
- **CheatSheet Updated:** [Locations added]
- **Verification:** [Test command]
```

## 🏗️ **HIRE/FIRE FLEET METHOD**

**For complex tasks: Hire specialists → Build shared CheatSheet → Fire when done**

### Fleet Template
```markdown
**Task**: [Objective]
**Fleet**: [agent-role] → [agent-role] → [agent-role]
**Shared CheatSheet**: `CheatSheet_YYYYMMDD.md`
**Coordination**: `fleet_task_YYYYMMDD.md`
```

### Protocol
- **Hire**: Narrow context, CheatSheet contribution required
- **Build**: Each agent adds precise file:line locations to shared CheatSheet
- **Coordinate**: Shared markdown files + CheatSheet updates
- **Fire**: Delete after CheatSheet contribution verified

### R&D Alignment
**"Reduce & Delegate"** with real-time documentation:
- **Reduce**: Break tasks → specialized roles
- **Document**: Build CheatSheet as you explore
- **Delegate**: Narrow context + CheatSheet updates
- **Parallel**: Simultaneous exploration + documentation

---
**Instructions**: Copy this template to `CLAUDE.md` in new projects, customize bracketed sections