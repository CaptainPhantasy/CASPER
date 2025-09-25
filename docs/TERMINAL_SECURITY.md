# CASPER Terminal Security Implementation

## Overview

The CASPER Terminal Security system provides comprehensive protection for terminal operations through multiple layers of security controls. This document outlines the security architecture, components, and usage guidelines.

## Security Architecture

### Core Components

1. **SecurityMiddleware** - Central command validation and filtering
2. **WebSocket Security Handler** - Secure WebSocket communication with authentication
3. **Command Proxy** - Secure CASPER CLI command execution with rate limiting
4. **Process Sandboxing** - Isolated execution environments
5. **Audit Logging** - Comprehensive security event tracking

## Security Features

### 1. Command Validation and Filtering

**Multi-level Security Classification:**
- **SAFE** - Commands with no security risk (ls, cat, pwd, git status)
- **RESTRICTED** - Commands requiring validation (mkdir, chmod, git add)
- **DANGEROUS** - Commands requiring explicit approval (sudo, ssh, curl)
- **BLOCKED** - Commands never allowed (rm, dd, reboot, shutdown)

**Pattern-based Detection:**
- Recursive delete operations (`rm -rf`)
- Command injection patterns (`;`, `&&`, `|`)
- Device file access (`> /dev/`)
- Command substitution (`` `command` ``, `$(command)`)

### 2. Process Sandboxing

**Sandbox Features:**
- Isolated temporary directories per session
- Restricted environment variables
- Limited PATH access
- Process group isolation
- Automatic cleanup on session termination

**Implementation:**
```python
# Create sandbox for session
sandbox_context = await security.create_sandbox(session_id)

# PTY runs in sandbox environment
pty_session_id = await pty_manager.create_session(
    working_dir=sandbox_context["sandbox_dir"],
    env=sandbox_context["env_vars"]
)
```

### 3. Authentication and Authorization

**JWT Token Authentication:**
- Optional JWT token validation for WebSocket connections
- User identification for audit logging
- Session-based access control

**Rate Limiting:**
- Per-command rate limits (configurable)
- Concurrent task execution limits
- User-based quota enforcement

### 4. Comprehensive Audit Logging

**Event Types:**
- `COMMAND_VALIDATION` - Command security validation
- `SECURITY_VIOLATION` - Blocked command attempts
- `SANDBOX_CREATED` - Sandbox environment creation
- `CASPER_COMMAND_EXECUTION` - CASPER CLI command execution
- `AUTHENTICATION` - User authentication events

**Risk Levels:**
- `LOW` - Normal operations
- `MEDIUM` - Potentially risky operations
- `HIGH` - Dangerous operations blocked
- `CRITICAL` - Severe security violations

## API Endpoints

### Security Management

#### Get Security Statistics
```
GET /api/terminal/security/stats
```
Returns overall security statistics and audit summary.

#### Get Security Audit Log
```
GET /api/terminal/security/audit?hours=24&risk_level=high
```
Returns filtered audit events with optional risk level filtering.

#### Validate Command Security
```
POST /api/terminal/security/validate
{
  "command": "rm -rf /",
  "session_id": "optional",
  "user_id": "optional"
}
```
Validates command against security policies without execution.

### Session Management

#### Get Active Sessions
```
GET /api/terminal/sessions/active
```
Returns information about all active terminal sessions.

#### Execute Command in Session
```
POST /api/terminal/sessions/{session_id}/command
{
  "command": "ls -la"
}
```
Executes command in specific terminal session with security validation.

## Configuration

### Security Configuration

```python
class SecurityConfig:
    def __init__(self):
        # Safe commands (no restrictions)
        self.safe_commands = {
            "ls", "cat", "head", "tail", "pwd", "date",
            "casper", "poetry", "pytest", "git status"
        }

        # Restricted commands (require validation)
        self.restricted_commands = {
            "mkdir", "chmod", "git add", "git commit",
            "npm install", "pip install"
        }

        # Dangerous commands (require approval)
        self.dangerous_commands = {
            "sudo", "ssh", "curl", "wget", "kill"
        }

        # Blocked commands (never allowed)
        self.blocked_commands = {
            "rm", "dd", "mkfs", "reboot", "shutdown"
        }
```

### Rate Limiting Configuration

```python
command_rate_limits = {
    "task": {"max_per_minute": 10, "requests": []},
    "status": {"max_per_minute": 60, "requests": []},
    "analyze": {"max_per_minute": 30, "requests": []},
}
```

## Usage Examples

### WebSocket Terminal Connection

```javascript
// Connect to secure terminal
const ws = new WebSocket('ws://localhost:8742/ws/terminal');

// Send authentication token (optional)
ws.send(JSON.stringify({
    type: 'auth',
    token: 'your-jwt-token'
}));

// Execute command with security validation
ws.send(JSON.stringify({
    type: 'command',
    command: 'ls -la'
}));

// Handle security violations
ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.type === 'security_violation') {
        console.error('Command blocked:', message.reason);
    }
};
```

### Python Security Validation

```python
from core.terminal.security import SecurityMiddleware

security = SecurityMiddleware()

# Validate command
try:
    await security.validate_command(
        command="ls -la",
        session_id="session_123",
        user_id="user_456"
    )
    print("Command allowed")
except SecurityViolation as e:
    print(f"Command blocked: {e}")
    print(f"Risk level: {e.risk_level}")
```

## Security Best Practices

### For Development

1. **Always validate commands** before execution
2. **Use sandbox environments** for untrusted code
3. **Monitor audit logs** regularly for security events
4. **Implement proper authentication** for production deployments
5. **Configure rate limits** appropriate for your use case

### For Production

1. **Enable JWT authentication** for all connections
2. **Use HTTPS/WSS** for all communications
3. **Implement log rotation** to prevent disk space issues
4. **Monitor security metrics** and set up alerts
5. **Regular security audits** of command classifications
6. **Network isolation** for terminal processes

## Testing

### Running Security Tests

```bash
# Run all security tests
pytest tests/test_terminal_security.py -v

# Run specific test categories
pytest tests/test_terminal_security.py::TestSecurityMiddleware -v
pytest tests/test_terminal_security.py::TestSecurityPerformance -v

# Run security-only tests
python tests/test_terminal_security.py --security-only
```

### Test Coverage

The security test suite covers:
- Command validation and filtering
- Sandbox creation and cleanup
- Authentication and authorization
- Audit logging functionality
- Rate limiting mechanisms
- WebSocket security handling
- Integration testing across all components
- Performance testing under load

## Monitoring and Alerting

### Key Metrics to Monitor

1. **Security Violations per Hour** - Monitor for unusual spikes
2. **Blocked Commands by Type** - Identify attack patterns
3. **Authentication Failures** - Detect brute force attempts
4. **Sandbox Creation/Cleanup** - Monitor resource usage
5. **Command Execution Latency** - Performance monitoring

### Recommended Alerts

```python
# Example alert conditions
alerts = {
    "high_security_violations": "violations > 10 per minute",
    "authentication_failures": "failures > 5 per minute from same IP",
    "resource_exhaustion": "active_sandboxes > 100",
    "performance_degradation": "command_latency > 1000ms"
}
```

## Troubleshooting

### Common Issues

1. **Command Blocked Unexpectedly**
   - Check audit log for specific reason
   - Verify command classification
   - Review dangerous patterns matching

2. **Sandbox Creation Failure**
   - Check disk space availability
   - Verify temporary directory permissions
   - Review system limits (ulimit)

3. **Authentication Issues**
   - Verify JWT token format and signature
   - Check token expiration
   - Validate user_id in token payload

4. **Performance Issues**
   - Monitor audit log size
   - Check sandbox cleanup frequency
   - Review rate limiting settings

### Debug Mode

```python
# Enable detailed security logging
import logging
logging.getLogger('core.terminal.security').setLevel(logging.DEBUG)

# Get detailed audit summary
summary = security.get_audit_summary(hours=1)
print(json.dumps(summary, indent=2))
```

## Security Compliance

This security implementation addresses common compliance requirements:

- **Command Injection Prevention** - Pattern-based detection and blocking
- **Process Isolation** - Sandbox environments for untrusted code
- **Audit Trail** - Comprehensive logging of all security events
- **Access Control** - Authentication and authorization mechanisms
- **Rate Limiting** - Protection against abuse and resource exhaustion

## Future Enhancements

Planned security improvements:

1. **Machine Learning** - Anomaly detection for command patterns
2. **Network Isolation** - Container-based process isolation
3. **Encryption** - End-to-end encryption for command transmission
4. **RBAC** - Role-based access control for command categories
5. **Security Policies** - User-defined security policy engine

## Support

For security-related issues or questions:

1. Check the audit logs for detailed information
2. Review this documentation for configuration options
3. Run the security test suite to verify functionality
4. Contact the CASPER development team for assistance

## License

This security implementation is part of the CASPER Prime project and follows the same license terms.