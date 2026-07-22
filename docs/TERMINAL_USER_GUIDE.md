# CASPER Prime Terminal User Guide

## Overview

The CASPER Prime Terminal provides integrated terminal access directly within the dashboard, enabling seamless command execution and monitoring without leaving the application interface. This terminal system is designed specifically for AI-assisted development workflows and includes specialized features for CASPER CLI integration.

## Getting Started

### Accessing the Terminal

1. **Open Terminal Panel**: Click the terminal icon in the dashboard sidebar or use the keyboard shortcut `Ctrl+`` (backtick)
2. **Panel Management**: The terminal opens as a resizable panel that can be positioned alongside other dashboard components
3. **Multiple Sessions**: Create new terminal sessions using the "+" button in the terminal tab bar

### Basic Terminal Features

#### Terminal Tabs and Sessions
- **New Session**: Click the "+" button to create a new terminal session
- **Session Management**: Each session maintains its own command history and working directory
- **Tab Switching**: Use `Ctrl+Tab` to switch between terminal sessions
- **Close Session**: Click the "×" on any terminal tab or use `Ctrl+Shift+W`

#### Panel Resizing
- **Drag to Resize**: Use the drag handle between panels to adjust terminal size
- **Maximize/Minimize**: Double-click the terminal header to toggle maximized view
- **Layout Presets**: Use predefined layouts from the Layout menu:
  - **Developer Layout**: Large terminal with code editor
  - **Analyst Layout**: Terminal alongside data visualization panels
  - **Compact Layout**: Minimized terminal for quick commands

## CASPER CLI Integration

### Available Commands

The terminal provides direct access to all CASPER CLI commands:

#### Task Management
```bash
# Execute a development task
casper task "Add user authentication to the login page"

# Run with dry-run mode (analyze without execution)
casper task "Refactor database schema" --dry-run

# Execute with approval mode
casper task "Deploy to production" --approve
```

#### Project Management
```bash
# Initialize CASPER in a new project
casper init

# Check project status
casper status

# View agent activity
casper agents

# Show configuration
casper config
```

#### Agent Operations
```bash
# List available agents
casper agents list

# Start specific agent
casper agents start backend-prime

# Monitor agent activity
casper agents monitor

# Stop all agents
casper agents stop
```

### Command Features

#### Auto-completion
- Press `Tab` to auto-complete CASPER commands
- Use `Tab Tab` to show all available options
- Context-aware completion based on current project state

#### Command History
- Use `↑` and `↓` arrow keys to navigate command history
- Search history with `Ctrl+R`
- History persists across terminal sessions

#### Real-time Output
- Live streaming of command output
- Progress indicators for long-running tasks
- Color-coded output (errors in red, success in green)

## Advanced Features

### Terminal Customization

#### Appearance Settings
Access terminal settings via the gear icon in the terminal header:
- **Font Size**: Adjust terminal font size (12-24px)
- **Color Scheme**: Choose from multiple themes (Dark, Light, Solarized)
- **Transparency**: Adjust background transparency (0-50%)
- **Line Height**: Modify line spacing for readability

#### Keyboard Shortcuts
- `Ctrl+C`: Interrupt current command
- `Ctrl+Z`: Suspend current process
- `Ctrl+L`: Clear terminal screen
- `Ctrl+A`: Move cursor to beginning of line
- `Ctrl+E`: Move cursor to end of line
- `Ctrl+K`: Kill text from cursor to end of line
- `Ctrl+U`: Kill text from cursor to beginning of line

### Search and Navigation
- `Ctrl+F`: Open search bar in terminal
- `F3` / `Shift+F3`: Find next/previous search result
- `Ctrl+Shift+F`: Search across all terminal sessions

### Copy and Paste
- `Ctrl+C`: Copy selected text (when text is selected)
- `Ctrl+V`: Paste from clipboard
- `Ctrl+Shift+C`: Copy selected text (alternative)
- `Ctrl+Shift+V`: Paste from clipboard (alternative)

## Workflow Integration

### Development Workflows

#### Code Development
1. Open terminal alongside code editor
2. Use `casper task` to generate or modify code
3. Monitor real-time progress and agent communications
4. Test changes directly in terminal
5. Commit changes when satisfied

#### Testing and Deployment
1. Run tests using standard commands (`pytest`, `npm test`)
2. Use CASPER agents for automated testing workflows
3. Deploy using `casper deploy` or standard deployment commands
4. Monitor deployment status in real-time

### Project Analysis
1. Use `casper analyze` for codebase analysis
2. View results in terminal and dashboard simultaneously
3. Execute recommended improvements via terminal commands
4. Track progress across multiple terminal sessions

## Performance and Limits

### Performance Characteristics
- **Command Latency**: < 100ms for standard CASPER commands
- **Terminal Rendering**: 60 FPS during active output
- **Memory Usage**: < 50MB per terminal session
- **Session Limit**: Up to 10 concurrent terminal sessions

### Resource Management
- Terminal sessions automatically manage memory usage
- Long-running processes are handled efficiently
- Background tasks don't block terminal interaction
- Automatic cleanup of completed processes

## Security Features

### Command Validation
- All commands are validated before execution
- Dangerous commands require confirmation
- System commands are sandboxed for security
- Audit trail maintained for all executed commands

### Access Control
- Terminal access respects dashboard authentication
- Commands run with appropriate user permissions
- No elevation of privileges without explicit approval
- Session isolation prevents cross-contamination

## Troubleshooting

### Common Issues

#### Terminal Won't Connect
1. Check WebSocket connection status in browser dev tools
2. Verify CASPER backend is running on port 8742
3. Refresh the dashboard page
4. Check network connectivity

#### Commands Not Executing
1. Verify CASPER CLI is properly installed
2. Check if command syntax is correct
3. Ensure you're in the correct directory
4. Review error messages for specific issues

#### Performance Issues
1. Close unused terminal sessions
2. Clear terminal history if very long
3. Check system resource usage
4. Restart terminal session if unresponsive

#### Display Issues
1. Adjust terminal font size if text appears garbled
2. Try different color schemes for better visibility
3. Check browser zoom level (100% recommended)
4. Clear browser cache and refresh

### Getting Help

#### In-Terminal Help
```bash
# Show CASPER CLI help
casper --help

# Get help for specific command
casper task --help

# Show version information
casper --version
```

#### Dashboard Help
- Click the "?" icon in terminal header for context help
- Access full documentation via Help menu
- Use keyboard shortcut `F1` for quick help

#### Support Resources
- Online documentation: [CASPER Prime Docs]
- Community forum: [CASPER Community]
- Issue tracker: [GitHub Issues]
- Email support: support@casper-prime.ai

## Tips and Best Practices

### Efficiency Tips
1. **Use Multiple Sessions**: Keep different sessions for different tasks (dev, test, deploy)
2. **Leverage Presets**: Use layout presets for different work modes
3. **Command Aliases**: Set up aliases for frequently used CASPER commands
4. **History Search**: Use `Ctrl+R` to quickly find and re-run previous commands

### Workflow Optimization
1. **Start with Analysis**: Begin tasks with `casper analyze` to understand context
2. **Use Dry-Run Mode**: Test complex tasks with `--dry-run` before execution
3. **Monitor Progress**: Keep terminal visible during long-running tasks
4. **Save Work Frequently**: Use terminal to commit changes regularly

### Layout Management
1. **Customize for Task**: Adjust panel sizes based on current work
2. **Save Layouts**: Create custom layouts for different project types
3. **Use Keyboard Shortcuts**: Learn shortcuts for faster panel management
4. **Mobile Considerations**: Use compact layout on smaller screens

## Version Information

- **Terminal Version**: 1.0.0
- **XTerm.js Version**: 5.5.0
- **Compatible Browsers**: Chrome 90+, Firefox 88+, Safari 14+
- **Node.js Requirement**: 18.0+
- **Python Requirement**: 3.11+

---

*Last Updated: September 2024*
*For technical support, contact: support@casper-prime.ai*