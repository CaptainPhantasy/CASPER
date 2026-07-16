# CASPER CLI Commands - Logic Chain & User Process Documentation

## Overview

This document explains the complete logic chain and user process for every command in the CASPER CLI system. Each command follows a specific flow from user input to final output.

---

## 🎯 Core System Commands

### `/help` - Command Documentation System

**User Process:**
1. User types `/help` or `/help <category>`
2. System displays available commands

**Logic Chain:**
```
User Input → Parse Category (optional)
    ↓
Category Filter Check
    ├─ No Category → Show all commands grouped by category
    └─ Category → Filter commands for that category
    ↓
Format Output with Rich Tables
    ↓
Display to Console
```

**Key Features:**
- Categories: System, CASPER, Git, Testing, etc.
- Aliases support (h, ?)
- Smart grouping for readability

---

### `/status` - System Health Monitor

**User Process:**
1. User types `/status`
2. System shows agent pool, tasks, and resources

**Logic Chain:**
```
User Input → Gather System Metrics
    ↓
Query Components:
    ├─ Active Tasks Count
    ├─ Queued Tasks Count
    ├─ Agent Pool Status (per role)
    ├─ Context Sessions
    └─ Resource Usage
    ↓
Format into Rich Tables
    ↓
Display Real-time Status
```

**Data Sources:**
- AgentCoordinator for task metrics
- AgentPool for agent availability
- ContextManager for session data

---

### `/config` - Configuration Management

**User Process:**
1. User types `/config` (show) or `/config set <key> <value>`
2. System displays or modifies configuration

**Logic Chain:**
```
User Input → Parse Action (show/set)
    ↓
Branch on Action:
    ├─ Show → Load .casper/config/casper.json
    │         Format as table
    │         Display current settings
    │
    └─ Set → Validate key/value pair
             Update configuration
             Write to casper.json
             Confirm change
```

**Configuration Scope:**
- Agent settings (max parallel, priorities)
- Repository settings (approval, formatting)
- User preferences

---

## 🤖 CASPER Core Commands

### `/task` - Multi-Agent Task Execution

**User Process:**
1. User types `/task "build user authentication"`
2. System analyzes, decomposes, and executes via agents

**Logic Chain:**
```
User Input → Task Complexity Analysis
    ↓
Complexity Assessment (LOW/MEDIUM/HIGH)
    ↓
Agent Selection Based on Keywords:
    ├─ Frontend keywords → Frontend Prime
    ├─ Backend keywords → Backend Prime
    ├─ Testing keywords → Testing Prime
    └─ DevOps keywords → DevOps Prime
    ↓
Task Decomposition into Subtasks
    ↓
Execution Strategy (Sequential/Parallel)
    ↓
Agent Pool Allocation
    ↓
Context Bundle Creation & Passing
    ↓
Progress Monitoring via WebSocket
    ↓
Result Aggregation
    ↓
Final Output to User
```

**Agent Coordination:**
- Master Prime orchestrates
- Specialized agents execute
- Context bundles maintain state
- Real-time progress updates

---

### `/analyze` - Task Complexity Assessment

**User Process:**
1. User types `/analyze "refactor authentication module"`
2. System provides complexity analysis without execution

**Logic Chain:**
```
User Input → Task Parser
    ↓
Pattern Matching Against Indicators:
    ├─ HIGH: "entire system", "integrate", "full-stack"
    ├─ MEDIUM: "api", "component", "refactor"
    └─ LOW: "fix", "update", "simple"
    ↓
Agent Requirement Analysis
    ↓
Token Estimation
    ↓
Risk Factor Identification
    ↓
Generate Analysis Report:
    ├─ Lines of Code Estimate
    ├─ Files Affected
    ├─ Required Agents
    ├─ Priority Level
    └─ Estimated Duration
```

---

## 💻 Development Commands

### `/todo` - Task Management System

**User Process:**
1. `/todo "Fix login bug"` - Add task
2. `/todo list` - View all tasks
3. `/todo done 1` - Mark complete
4. `/todo remove 1` - Delete task

**Logic Chain:**
```
User Input → Parse Action
    ↓
Action Router:
    ├─ ADD → Generate UUID
    │        Create task object
    │        Append to .casper/todos.json
    │
    ├─ LIST → Load todos.json
    │         Format as Rich table
    │         Show with status indicators
    │
    ├─ DONE → Find task by ID
    │         Update status & timestamp
    │         Save to todos.json
    │
    └─ REMOVE → Filter out task
                Save updated list
```

**Data Structure:**
```json
{
  "id": "uuid",
  "task": "description",
  "status": "pending|completed",
  "created_at": "ISO-8601",
  "completed_at": "ISO-8601"
}
```

---

### `/explain` - AI-Powered Code/Error Explanation

**User Process:**
1. User types `/explain "TypeError: undefined is not a function"`
2. System provides detailed explanation and solutions

**Logic Chain:**
```
User Input → Content Classification
    ↓
Branch on Type:
    ├─ Error Message → Extract error type
    │                  Query LLM for explanation
    │                  Generate solutions
    │
    ├─ File Path → Read file content
    │              Analyze code structure
    │              Explain functionality
    │
    └─ Concept → Generate educational content
    ↓
LLM Service Available?
    ├─ Yes → AI-powered analysis
    └─ No → Fallback pattern matching
    ↓
Format Response with:
    ├─ Problem explanation
    ├─ Common causes
    ├─ Solution steps
    └─ Prevention tips
```

---

### `/newcomponent` - Component Generator

**User Process:**
1. User types `/newcomponent UserProfile --type react`
2. System creates component with boilerplate

**Logic Chain:**
```
User Input → Parse Component Name & Options
    ↓
Detect Project Type:
    ├─ React (package.json check)
    ├─ Vue (vue.config.js check)
    └─ Python (pyproject.toml check)
    ↓
Generate Component Code:
    ├─ Import statements
    ├─ Component structure
    ├─ Props/State definitions
    ├─ Render method/template
    └─ Export statement
    ↓
Determine File Path:
    └─ src/components/{ComponentName}.{ext}
    ↓
Write File with Boilerplate
    ↓
Optional Test File Generation (--with-test)
    ↓
Optional Storybook Story (--stories)
```

---

### `/addroute` - Route Creation

**User Process:**
1. User types `/addroute /dashboard DashboardComponent`
2. System creates route and component

**Logic Chain:**
```
User Input → Parse Path & Component
    ↓
Framework Detection:
    ├─ React Router → Check App.tsx
    ├─ Vue Router → Check router/index.js
    └─ Generic → Provide instructions
    ↓
Component Generation:
    ├─ Create component file
    ├─ Add boilerplate code
    └─ Set up basic structure
    ↓
Router Integration:
    ├─ Generate import statement
    ├─ Create route object
    └─ Provide integration instructions
```

---

### `/gen` - Full Feature Scaffolding

**User Process:**
1. User types `/gen user --full`
2. System generates complete CRUD feature

**Logic Chain:**
```
User Input → Parse Feature Name & Options
    ↓
Option Processing:
    ├─ --full → All components
    ├─ --api → Backend only
    ├─ --frontend → UI only
    └─ --backend → Server only
    ↓
Project Type Detection
    ↓
Generation Pipeline:
    ├─ Backend Generation:
    │   ├─ Model (User.py)
    │   ├─ Schema (UserSchema.py)
    │   ├─ API Routes (user_routes.py)
    │   └─ Service Layer (user_service.py)
    │
    └─ Frontend Generation:
        ├─ List Component
        ├─ Form Component
        ├─ Detail View
        └─ API Service
    ↓
Test File Generation
    ↓
Documentation Updates
```

---

### `/refactor` - Code Improvement Analysis

**User Process:**
1. User types `/refactor src/utils.py calculate_total`
2. System analyzes and suggests improvements

**Logic Chain:**
```
User Input → Parse File & Function
    ↓
File Reading & Validation
    ↓
Code Extraction:
    ├─ Specific function (if named)
    └─ First 2000 chars (if not)
    ↓
Analysis Method:
    ├─ LLM Available → AI analysis
    │   ├─ Code smell detection
    │   ├─ Performance issues
    │   ├─ Best practices
    │   └─ Refactored code
    │
    └─ Static Analysis → Pattern matching
        ├─ Complexity checks
        ├─ TODO/FIXME detection
        ├─ Exception handling
        └─ File size warnings
    ↓
Generate Recommendations
```

---

## 🔧 Git Commands

### `/commit` - Smart Commit Messages

**User Process:**
1. User types `/commit` or `/commit --message="custom"`
2. System generates or uses commit message

**Logic Chain:**
```
User Input → Check Git Repository
    ↓
Get Changes:
    ├─ git status --porcelain
    └─ git diff HEAD
    ↓
Message Generation:
    ├─ Custom Message → Use provided
    └─ AI Generation → Analyze changes
                       Generate conventional commit
    ↓
Commit Creation:
    ├─ Stage changes (if needed)
    ├─ Create commit
    └─ Add co-author attribution
    ↓
Handle Pre-commit Hooks
    ↓
Verify Success
```

**Commit Format:**
- Conventional commits (feat:, fix:, docs:)
- AI-generated descriptions
- Co-author attribution

---

### `/pr` - Pull Request Creation

**User Process:**
1. User types `/pr` or `/pr "Custom title"`
2. System creates GitHub pull request

**Logic Chain:**
```
User Input → Check gh CLI Installation
    ↓
Validate Branch:
    ├─ Not on main/master
    └─ Has commits to push
    ↓
Gather PR Content:
    ├─ Branch diff (git diff main...HEAD)
    ├─ Commit list (git log main..HEAD)
    └─ Changes summary (--stat)
    ↓
Title/Description Generation:
    ├─ LLM Available → AI generation
    └─ Fallback → Branch name formatting
    ↓
Execute gh pr create:
    ├─ With generated title
    ├─ With commit body
    └─ Interactive mode fallback
```

---

### `/review` - Code Review

**User Process:**
1. User types `/review` (current changes) or `/review file.py`
2. System performs code review

**Logic Chain:**
```
User Input → Determine Target
    ↓
Content Acquisition:
    ├─ No Args → git diff (unstaged)
    └─ File Path → Read file content
    ↓
Review Process:
    ├─ LLM Available → AI review
    │   ├─ Security vulnerabilities
    │   ├─ Performance issues
    │   ├─ Code quality
    │   ├─ Best practices
    │   └─ Bug detection
    │
    └─ Static Analysis → Pattern checks
        ├─ Hardcoded secrets
        ├─ Dynamic execution
        ├─ TODO comments
        └─ Function complexity
    ↓
Format Findings with Severity
```

---

### `/fixbug` - Bug Fix Workflow

**User Process:**
1. User types `/fixbug 123` or `/fixbug "login error"`
2. System creates bug fix branch and workflow

**Logic Chain:**
```
User Input → Parse Issue Reference
    ↓
Branch Creation:
    ├─ Issue Number → fix/issue-123
    └─ Description → fix/login-error
    ↓
Git Operations:
    └─ git checkout -b {branch_name}
    ↓
Workflow Setup:
    ├─ Create bug checklist
    ├─ Generate debug suggestions
    └─ Create tracking file
    ↓
AI Assistance (if available):
    ├─ Likely causes
    ├─ Files to check
    ├─ Debug steps
    └─ Common fixes
    ↓
Bug Tracking File:
    └─ .casper/bugs/{branch_name}.md
```

---

## 🧪 Testing Commands

### `/test` - Test Execution

**User Process:**
1. User types `/test` or `/test specific_file.py`
2. System runs appropriate tests

**Logic Chain:**
```
User Input → Parse Test Target
    ↓
Framework Detection:
    ├─ Python → pytest.ini check
    ├─ JavaScript → jest.config.js check
    └─ Generic → package.json scripts
    ↓
Command Construction:
    ├─ pytest with coverage flags
    ├─ jest with watch mode
    └─ npm test fallback
    ↓
Execution & Monitoring:
    ├─ Run subprocess
    ├─ Stream output
    └─ Capture exit code
    ↓
Failure Handling:
    └─ Offer to run only failed tests
```

---

### `/testfail` - Rerun Failed Tests

**User Process:**
1. User types `/testfail`
2. System reruns only previously failed tests

**Logic Chain:**
```
User Input → Detect Test Framework
    ↓
Framework-Specific Command:
    ├─ pytest → --lf (last failed)
    ├─ Jest → --onlyFailures
    └─ npm test → standard rerun
    ↓
Execute with Verbose Option
    ↓
Display Results
    ↓
Suggest /explain for Errors
```

---

### `/lint` - Code Quality Check

**User Process:**
1. User types `/lint` or `/lint src/`
2. System runs appropriate linters

**Logic Chain:**
```
User Input → Parse Target Path
    ↓
Linter Detection:
    ├─ Python → flake8/pylint/black
    ├─ JavaScript → eslint
    ├─ TypeScript → tslint/eslint
    └─ Generic → file extension based
    ↓
Auto-fix Option:
    ├─ --fix flag support
    └─ Format on save
    ↓
Execute Linting:
    ├─ Run linter command
    ├─ Parse output
    └─ Format issues
    ↓
Summary Generation:
    ├─ Issue count by severity
    └─ Suggested fixes
```

---

### `/debug` - Debug Session Setup

**User Process:**
1. User types `/debug file.py` or `/debug "error message"`
2. System provides debugging strategy

**Logic Chain:**
```
User Input → Parse Debug Target
    ↓
Target Analysis:
    ├─ File → Language detection
    │         Function analysis
    │         Breakpoint suggestions
    │
    └─ Issue → Error classification
               Common causes
               Debug approach
    ↓
Strategy Generation:
    ├─ Language-Specific:
    │   ├─ Python → pdb/debugpy setup
    │   ├─ JavaScript → node --inspect
    │   └─ Java → jdb configuration
    │
    └─ Issue-Specific:
        ├─ Auth → Token/session checks
        ├─ Database → Query logging
        └─ API → Request/response capture
    ↓
IDE Integration Instructions
    ↓
Monitoring Setup
```

---

## 🚀 Workflow Commands

### `/sync` - Repository Synchronization

**User Process:**
1. User types `/sync`
2. System updates repository and dependencies

**Logic Chain:**
```
User Input → Git Repository Check
    ↓
Git Operations:
    ├─ Fetch latest changes
    ├─ Check for conflicts
    ├─ Pull with rebase/merge
    └─ Update submodules
    ↓
Dependency Updates:
    ├─ Python → pip/poetry install
    ├─ Node.js → npm/yarn install
    └─ Other → Detect and run
    ↓
Post-Sync Tasks:
    ├─ Database migrations
    ├─ Asset compilation
    └─ Cache clearing
    ↓
Status Report
```

---

### `/deploy` - Deployment Automation

**User Process:**
1. User types `/deploy staging`
2. System handles deployment process

**Logic Chain:**
```
User Input → Parse Environment
    ↓
Pre-deployment Checks:
    ├─ Git status (clean?)
    ├─ Branch check (correct?)
    ├─ Test execution
    └─ Build validation
    ↓
Platform Detection:
    ├─ Docker → Dockerfile present
    ├─ Heroku → Procfile present
    ├─ Vercel → vercel.json
    └─ Generic → Manual steps
    ↓
Deployment Process:
    ├─ Build application
    ├─ Run integration tests
    ├─ Push to registry
    └─ Trigger deployment
    ↓
Deployment Log:
    └─ .casper/deployments/{env}-{timestamp}.log
    ↓
Monitoring Instructions
```

---

### `/standup` - Daily Status Report

**User Process:**
1. User types `/standup`
2. System generates activity summary

**Logic Chain:**
```
User Input → Time Range (default: yesterday)
    ↓
Data Collection:
    ├─ Git commits (git log --since)
    ├─ Current branch
    ├─ Modified files count
    ├─ Todo status
    └─ Merge conflicts
    ↓
Report Sections:
    ├─ Yesterday/Recently
    ├─ Today's Focus
    ├─ Blockers
    └─ Quick Stats
    ↓
Format with Rich Console
    ↓
Display Summary
```

---

## 🔐 Environment & Security

### `/env` - Environment Variable Management

**User Process:**
1. `/env list` - Show variables
2. `/env set KEY value` - Set variable
3. `/env get KEY` - Get value

**Logic Chain:**
```
User Input → Parse Action
    ↓
Action Handler:
    ├─ LIST → Read .env file
    │         Mask sensitive values
    │         Display table
    │
    ├─ SET → Validate key/value
    │        Update .env file
    │        Reload environment
    │
    ├─ GET → Retrieve value
    │        Mask if sensitive
    │
    └─ ENCRYPT → Encode values
                 Store securely
```

---

### `/scan` - Security Vulnerability Scanning

**User Process:**
1. User types `/scan`
2. System checks for vulnerabilities

**Logic Chain:**
```
User Input → Scanner Detection
    ↓
Security Checks:
    ├─ Dependency vulnerabilities
    ├─ Hardcoded secrets
    ├─ Insecure patterns
    └─ Outdated packages
    ↓
Tool Execution:
    ├─ Python → safety/bandit
    ├─ Node.js → npm audit
    └─ Generic → pattern matching
    ↓
Report Generation:
    ├─ Critical issues
    ├─ Warnings
    └─ Recommendations
```

---

## 📊 Business Commands

### `/estimate` - Project Estimation

**User Process:**
1. User types `/estimate "e-commerce platform"`
2. System provides time/effort estimates

**Logic Chain:**
```
User Input → Project Analysis
    ↓
Scope Decomposition:
    ├─ Feature identification
    ├─ Complexity assessment
    └─ Dependency mapping
    ↓
Estimation Methods:
    ├─ Story points
    ├─ Hours/days
    └─ Risk factors
    ↓
Report Generation:
    ├─ Timeline
    ├─ Resource needs
    └─ Cost projection
```

---

### `/invoice` - Invoice Generation

**User Process:**
1. User types `/invoice --client "ACME Corp"`
2. System generates invoice

**Logic Chain:**
```
User Input → Parse Parameters
    ↓
Time Tracking Integration:
    ├─ Collect logged hours
    ├─ Apply rates
    └─ Calculate totals
    ↓
Invoice Creation:
    ├─ Header information
    ├─ Line items
    ├─ Taxes/discounts
    └─ Payment terms
    ↓
Output Format:
    ├─ PDF generation
    └─ Email template
```

---

### `/proposal` - Proposal Generation

**User Process:**
1. User types `/proposal "mobile app development"`
2. System creates project proposal

**Logic Chain:**
```
User Input → Project Requirements
    ↓
AI-Powered Generation:
    ├─ Executive summary
    ├─ Technical approach
    ├─ Timeline
    ├─ Budget
    └─ Terms
    ↓
Document Formatting:
    ├─ Professional template
    └─ Export options
```

---

## 🎯 Session Management

### `/save` - Save Session

**User Process:**
1. User types `/save` or `/save "feature-dev"`
2. System saves current session

**Logic Chain:**
```
User Input → Session Name (optional)
    ↓
State Collection:
    ├─ Open files
    ├─ Terminal history
    ├─ Git branch
    ├─ Environment
    └─ Todo status
    ↓
Serialization:
    └─ .casper/sessions/{name}.session
    ↓
Confirmation
```

---

### `/resume` - Resume Session

**User Process:**
1. User types `/resume feature-dev`
2. System restores saved session

**Logic Chain:**
```
User Input → Load Session File
    ↓
State Restoration:
    ├─ Checkout git branch
    ├─ Open files
    ├─ Restore environment
    └─ Load todos
    ↓
Verification
```

---

## 🎨 Personalization

### `/theme` - Theme Management

**User Process:**
1. `/theme list` - Show themes
2. `/theme set dark` - Apply theme

**Logic Chain:**
```
User Input → Parse Action
    ↓
Theme Operations:
    ├─ List available
    ├─ Preview theme
    └─ Apply theme
    ↓
Update Configuration:
    ├─ Terminal colors
    └─ UI preferences
```

---

### `/custom` - Custom Commands

**User Process:**
1. `/custom add "deploy-prod" "npm run build && deploy"`
2. `/custom run deploy-prod`

**Logic Chain:**
```
User Input → Parse Custom Command
    ↓
Command Management:
    ├─ Add new command
    ├─ List customs
    ├─ Edit existing
    └─ Delete command
    ↓
Execution:
    ├─ Variable substitution
    ├─ Command chaining
    └─ Error handling
```

---

### `/favorite` - Favorite Commands

**User Process:**
1. `/favorite add commit`
2. `/favorite list`

**Logic Chain:**
```
User Input → Favorite Management
    ↓
Operations:
    ├─ Add to favorites
    ├─ Remove favorite
    └─ List favorites
    ↓
Quick Access:
    └─ Shortened aliases
```

---

## System Architecture Summary

### Command Processing Pipeline

```
User Input → Slash Command Router
    ↓
Command Validation & Parsing
    ↓
Permission & Context Check
    ↓
Service Layer Integration:
    ├─ LLM Service (AI features)
    ├─ Git Service (version control)
    ├─ File System (I/O operations)
    ├─ Agent System (complex tasks)
    └─ External Tools (linters, testers)
    ↓
Execution & Error Handling
    ↓
Response Formatting (Rich Console)
    ↓
User Output
```

### Error Handling Strategy

All commands follow this pattern:
1. **Input Validation** - Check arguments before processing
2. **Graceful Degradation** - Fallback when services unavailable
3. **Helpful Messages** - Guide users to solutions
4. **Recovery Options** - Suggest alternatives or fixes

### State Management

- **Session State**: .casper/sessions/
- **Configuration**: .casper/config/
- **Task State**: .casper/todos.json
- **Context Bundles**: .casper/context/
- **Deployment Logs**: .casper/deployments/

---

## Best Practices for Command Usage

### Command Chaining
Commands can be used in sequence for complex workflows:
```bash
/fixbug 123        # Create bug branch
/debug auth.py     # Set up debugging
/test auth         # Run specific tests
/commit           # Commit fixes
/pr               # Create pull request
```

### Efficient Workflows

**Feature Development:**
```
/task "implement user profiles" → /gen user --full → /test → /commit → /pr
```

**Daily Routine:**
```
/standup → /todo list → /sync → [work] → /commit → /todo done 1
```

**Code Quality:**
```
/lint → /refactor complex.py → /review → /test → /commit
```

---

This documentation represents the complete logic chain and user process for all CASPER CLI commands as of 2025-09-25.