# COMMAND IMPLEMENTATION - CHAIN OF THOUGHT METHODOLOGY

## SYSTEMATIC COMMAND IMPLEMENTATION PROTOCOL

### CORE PRINCIPLE: One Command, Full Verification, Then Next

Each command follows this exact COT sequence:
1. **THINK** - Analyze command requirements
2. **PLAN** - Design implementation approach
3. **BUILD** - Implement the command
4. **TEST** - Verify functionality
5. **VALIDATE** - Confirm success criteria met
6. **DOCUMENT** - Record completion
7. **PROCEED** - Move to next command only after validation

---

## IMPLEMENTATION ORDER (Priority-Based)

### TIER 1: CORE COMMANDS (Must Work First)
These enable basic functionality and testing of other commands.

```
1. help       - Shows available commands
2. task       - Execute development tasks
3. analyze    - Analyze task complexity
4. status     - Show system status
5. exit/quit  - Clean shutdown
```

### TIER 2: ESSENTIAL WORKFLOW COMMANDS
Enable core development workflows.

```
6. /task      - Slash version of task
7. /analyze   - Slash version of analyze
8. /status    - Slash version of status
9. /help      - Slash version of help
10. list      - List available agents/tasks
```

### TIER 3: DEVELOPMENT COMMANDS
Common development operations.

```
11. /create   - Create new components
12. /test     - Run tests
13. /debug    - Debug code
14. /review   - Code review
15. /refactor - Refactor code
```

### TIER 4: SPECIALIZED COMMANDS
Advanced features and utilities.

```
16-49. Remaining slash commands by category
```

---

## COT TEMPLATE FOR EACH COMMAND

### Command: `{command_name}`

#### 1. THINK - Requirements Analysis
```markdown
- [ ] Command purpose defined
- [ ] Input parameters identified
- [ ] Expected output specified
- [ ] Error cases enumerated
- [ ] Dependencies checked
```

#### 2. PLAN - Implementation Design
```markdown
- [ ] Handler function signature
- [ ] Validation logic planned
- [ ] Agent delegation mapped
- [ ] Response format designed
- [ ] Error handling strategy
```

#### 3. BUILD - Implementation
```python
# Location: core/services/slash_commands.py or casper_terminal_simple.py

async def handle_{command_name}(self, args: str) -> str:
    """
    Purpose: {purpose}
    Input: {input_spec}
    Output: {output_spec}
    """
    # Validation
    if not self._validate_{command_name}_args(args):
        return self._error_response("Invalid arguments")

    # Execution
    try:
        result = await self._execute_{command_name}(args)
        return self._format_{command_name}_response(result)
    except Exception as e:
        return self._error_response(f"Command failed: {e}")
```

#### 4. TEST - Verification Script
```python
# Test file: tests/test_command_{command_name}.py

async def test_{command_name}_basic():
    """Test basic functionality"""
    result = await execute_command("{command_name} test_arg")
    assert result.success == True
    assert "expected_output" in result.output

async def test_{command_name}_edge_cases():
    """Test edge cases and errors"""
    # Empty input
    result = await execute_command("{command_name}")
    assert result.success == False

    # Invalid input
    result = await execute_command("{command_name} invalid!!!")
    assert "error" in result.output.lower()

async def test_{command_name}_integration():
    """Test with real agent system"""
    # Test actual agent delegation
    # Test response formatting
    # Test error recovery
```

#### 5. VALIDATE - Success Criteria
```markdown
- [ ] Command appears in help menu
- [ ] Command executes without errors
- [ ] Output matches expected format
- [ ] Error cases handled gracefully
- [ ] Integration with agents works
- [ ] Performance < 2 seconds
- [ ] Memory usage acceptable
```

#### 6. DOCUMENT - Completion Record
```markdown
Command: {command_name}
Status: ✅ COMPLETE
Date: {date}
Tests: {test_count} passed
Notes: {any_special_notes}
```

#### 7. PROCEED - Gateway Check
```markdown
BEFORE MOVING TO NEXT COMMAND:
- [ ] All tests passing
- [ ] No console errors
- [ ] Help text updated
- [ ] Command documented
- [ ] Git commit created
```

---

## PRACTICAL EXAMPLE: Implementing `help` Command

### 1. THINK
- Purpose: Display available commands with descriptions
- Input: Optional category filter (e.g., "help dev")
- Output: Formatted command list
- Errors: Unknown category
- Dependencies: Command registry

### 2. PLAN
```python
Handler: handle_help(category: Optional[str])
Validation: Check category exists
Agent: No agent needed (local operation)
Response: Rich-formatted panel
Errors: "Unknown category: {cat}"
```

### 3. BUILD
```python
async def handle_help(self, args: str = "") -> None:
    """Display help for commands"""
    console = Console()

    if not args:
        # Show all commands
        help_panel = Panel.fit(
            self._format_all_commands(),
            title="📖 CASPER2 Commands",
            border_style="cyan"
        )
    else:
        # Show category
        if args not in self.command_categories:
            console.print(f"[red]Unknown category: {args}[/red]")
            return
        help_panel = Panel.fit(
            self._format_category_commands(args),
            title=f"📖 {args.title()} Commands",
            border_style="cyan"
        )

    console.print(help_panel)
```

### 4. TEST
```python
async def test_help_command():
    terminal = CasperTerminal()

    # Test basic help
    await terminal.handle_command("help")
    # Verify output contains expected sections

    # Test category help
    await terminal.handle_command("help dev")
    # Verify only dev commands shown

    # Test invalid category
    await terminal.handle_command("help invalid")
    # Verify error message shown
```

### 5. VALIDATE
✅ Command in help menu
✅ Executes without errors
✅ Shows formatted command list
✅ Handles unknown categories
✅ No agent delegation needed
✅ Response time < 100ms
✅ Minimal memory usage

### 6. DOCUMENT
```
Command: help
Status: ✅ COMPLETE
Date: 2024-01-25
Tests: 3 passed
Notes: Base command for discovering others
```

### 7. PROCEED
✅ All tests passing
✅ No console errors
✅ Help includes itself
✅ README updated
✅ Committed: "feat: implement help command with COT verification"

**NEXT**: Move to `task` command

---

## TESTING HARNESS

### Automated Test Runner
```bash
#!/bin/bash
# test_command.sh

COMMAND=$1

echo "🔍 Testing command: $COMMAND"

# 1. Unit tests
echo "Running unit tests..."
pytest tests/test_command_${COMMAND}.py -xvs

# 2. Integration test
echo "Running integration test..."
python3 -c "
import asyncio
from casper_terminal_simple import test_command
asyncio.run(test_command('$COMMAND'))
"

# 3. Manual verification
echo "Manual verification..."
casper2 <<EOF
$COMMAND test_input
exit
EOF

# 4. Performance test
echo "Performance test..."
time casper2 -c "$COMMAND benchmark"

echo "✅ Command $COMMAND verified"
```

### Progress Tracking
```markdown
## COMMAND IMPLEMENTATION STATUS

### TIER 1: CORE COMMANDS
- [ ] help       - 0% - Not started
- [ ] task       - 0% - Not started
- [ ] analyze    - 0% - Not started
- [ ] status     - 0% - Not started
- [ ] exit/quit  - 0% - Not started

### TIER 2: ESSENTIAL WORKFLOW
- [ ] /task      - 0% - Not started
- [ ] /analyze   - 0% - Not started
- [ ] /status    - 0% - Not started
- [ ] /help      - 0% - Not started
- [ ] list       - 0% - Not started

[Continue for all 49 commands...]
```

---

## SUCCESS METRICS

### Per-Command Metrics
- Implementation time: < 30 minutes
- Test coverage: > 80%
- Performance: < 2 seconds
- Error rate: < 1%

### Overall Progress Metrics
- Commands implemented: X/49
- Tests passing: Y/Z
- Average implementation time: XX minutes
- Total defects found: N

---

## ANTI-PATTERNS TO AVOID

❌ **Moving to next command before current is verified**
❌ **Implementing multiple commands simultaneously**
❌ **Skipping test creation**
❌ **Not updating help text**
❌ **Forgetting error handling**
❌ **Not testing edge cases**
❌ **Skipping documentation**

---

## VERIFICATION CHECKLIST

Before marking ANY command as complete:

```markdown
## Command: {command_name}

### Implementation
- [ ] Handler function implemented
- [ ] Validation logic complete
- [ ] Error handling added
- [ ] Response formatting done

### Testing
- [ ] Unit tests written
- [ ] Unit tests passing
- [ ] Integration test written
- [ ] Integration test passing
- [ ] Edge cases tested
- [ ] Performance tested

### Documentation
- [ ] Help text added
- [ ] Command in registry
- [ ] README updated
- [ ] Examples provided

### Quality
- [ ] Code reviewed
- [ ] No console errors
- [ ] Memory leaks checked
- [ ] Performance acceptable

### Sign-off
- [ ] Developer tested
- [ ] Automated tests pass
- [ ] Documentation complete
- [ ] Ready for next command

Signed: _______________
Date: _________________
```

---

## IMPLEMENTATION SCHEDULE

### Day 1: Foundation (5 commands)
- Morning: help, exit/quit
- Afternoon: task, analyze, status

### Day 2: Workflow (5 commands)
- Morning: /task, /analyze, /status
- Afternoon: /help, list

### Day 3: Development (5 commands)
- Morning: /create, /test
- Afternoon: /debug, /review, /refactor

### Days 4-7: Remaining Commands
- 8-10 commands per day
- Category by category
- Full verification each

---

## NOTES

1. **No Parallel Work**: One command at a time
2. **Full Verification**: Each command must be 100% working
3. **Clear Documentation**: Every step documented
4. **Test First**: Write tests before implementation when possible
5. **Incremental Progress**: Small, verified steps
6. **No Assumptions**: Test everything, assume nothing

This COT methodology ensures quality over speed, with each command fully operational before proceeding.