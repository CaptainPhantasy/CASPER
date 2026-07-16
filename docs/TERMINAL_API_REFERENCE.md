# CASPER Prime Terminal API Reference

## Overview

The CASPER Prime Terminal API provides programmatic access to terminal functionality, including session management, command execution, and real-time communication via WebSocket connections. This API is designed for integration with the dashboard frontend and external tools.

## Base URL

```
Production: https://your-domain.com/api
Development: http://localhost:8742/api
```

## Authentication

All API requests require authentication via JWT tokens obtained through the authentication system.

```http
Authorization: Bearer <jwt_token>
```

## WebSocket Connection

Terminal functionality primarily operates through WebSocket connections for real-time communication.

### WebSocket Endpoint

```
ws://localhost:8742/ws/terminal/{session_id}
```

### Connection Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| session_id | UUID | Yes | Unique terminal session identifier |
| token | string | Yes | JWT authentication token |

### Connection Example

```javascript
const ws = new WebSocket(`ws://localhost:8742/ws/terminal/${sessionId}?token=${authToken}`);

ws.onopen = (event) => {
    console.log('Terminal connected');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};
```

## REST API Endpoints

### Terminal Sessions

#### Create Terminal Session

Creates a new terminal session.

```http
POST /api/terminal/sessions
```

**Request Body:**
```json
{
    "name": "My Terminal Session",
    "working_directory": "/app",
    "environment_variables": {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "TERM": "xterm-256color"
    }
}
```

**Response:**
```json
{
    "session_id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "My Terminal Session",
    "working_directory": "/app",
    "status": "active",
    "created_at": "2024-09-24T10:00:00Z",
    "websocket_url": "ws://localhost:8742/ws/terminal/123e4567-e89b-12d3-a456-426614174000"
}
```

#### List Terminal Sessions

Retrieves all terminal sessions for the authenticated user.

```http
GET /api/terminal/sessions
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| status | string | all | Filter by session status: `active`, `inactive`, `all` |
| limit | integer | 50 | Maximum number of sessions to return |
| offset | integer | 0 | Offset for pagination |

**Response:**
```json
{
    "sessions": [
        {
            "session_id": "123e4567-e89b-12d3-a456-426614174000",
            "name": "My Terminal Session",
            "working_directory": "/app",
            "status": "active",
            "created_at": "2024-09-24T10:00:00Z",
            "last_activity": "2024-09-24T10:30:00Z"
        }
    ],
    "total": 1,
    "limit": 50,
    "offset": 0
}
```

#### Get Terminal Session

Retrieves details for a specific terminal session.

```http
GET /api/terminal/sessions/{session_id}
```

**Response:**
```json
{
    "session_id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "My Terminal Session",
    "working_directory": "/app",
    "environment_variables": {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "TERM": "xterm-256color"
    },
    "status": "active",
    "created_at": "2024-09-24T10:00:00Z",
    "last_activity": "2024-09-24T10:30:00Z",
    "command_count": 15,
    "websocket_url": "ws://localhost:8742/ws/terminal/123e4567-e89b-12d3-a456-426614174000"
}
```

#### Update Terminal Session

Updates terminal session properties.

```http
PATCH /api/terminal/sessions/{session_id}
```

**Request Body:**
```json
{
    "name": "Updated Terminal Session",
    "working_directory": "/new/path"
}
```

**Response:**
```json
{
    "session_id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Updated Terminal Session",
    "working_directory": "/new/path",
    "status": "active",
    "updated_at": "2024-09-24T10:45:00Z"
}
```

#### Delete Terminal Session

Terminates and removes a terminal session.

```http
DELETE /api/terminal/sessions/{session_id}
```

**Response:**
```json
{
    "message": "Terminal session terminated successfully",
    "session_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

### Command History

#### Get Command History

Retrieves command history for a terminal session.

```http
GET /api/terminal/sessions/{session_id}/history
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | integer | 100 | Maximum number of commands to return |
| offset | integer | 0 | Offset for pagination |
| search | string | - | Search term to filter commands |

**Response:**
```json
{
    "commands": [
        {
            "command_id": "456e7890-e89b-12d3-a456-426614174001",
            "command": "ls -la",
            "exit_code": 0,
            "output": "total 48\ndrwxr-xr-x  12 user user  4096 Sep 24 10:30 .\n...",
            "execution_time_ms": 25,
            "executed_at": "2024-09-24T10:30:15Z"
        }
    ],
    "total": 15,
    "limit": 100,
    "offset": 0
}
```

#### Execute Command

Executes a command in a terminal session (alternative to WebSocket).

```http
POST /api/terminal/sessions/{session_id}/execute
```

**Request Body:**
```json
{
    "command": "echo 'Hello World'",
    "timeout": 30000
}
```

**Response:**
```json
{
    "command_id": "456e7890-e89b-12d3-a456-426614174001",
    "command": "echo 'Hello World'",
    "exit_code": 0,
    "output": "Hello World\n",
    "execution_time_ms": 15,
    "executed_at": "2024-09-24T10:35:00Z"
}
```

### Terminal Metrics

#### Get Session Metrics

Retrieves performance metrics for a terminal session.

```http
GET /api/terminal/sessions/{session_id}/metrics
```

**Response:**
```json
{
    "session_id": "123e4567-e89b-12d3-a456-426614174000",
    "metrics": {
        "command_count": 15,
        "average_execution_time_ms": 45.3,
        "memory_usage_mb": 25.6,
        "cpu_usage_percent": 2.1,
        "session_duration_seconds": 1800,
        "last_activity": "2024-09-24T10:35:00Z"
    }
}
```

#### Get System Metrics

Retrieves overall terminal system metrics.

```http
GET /api/terminal/metrics
```

**Response:**
```json
{
    "system_metrics": {
        "active_sessions": 5,
        "total_commands_today": 1250,
        "average_response_time_ms": 38.7,
        "websocket_connections": 8,
        "memory_usage_mb": 128.5,
        "cpu_usage_percent": 5.2
    },
    "timestamp": "2024-09-24T10:40:00Z"
}
```

## WebSocket Message Types

### Client to Server Messages

#### Execute Command

```json
{
    "type": "execute",
    "data": {
        "command": "ls -la",
        "request_id": "unique-request-id"
    }
}
```

#### Resize Terminal

```json
{
    "type": "resize",
    "data": {
        "rows": 24,
        "cols": 80
    }
}
```

#### Send Input

```json
{
    "type": "input",
    "data": {
        "input": "user input text\n"
    }
}
```

#### Change Directory

```json
{
    "type": "chdir",
    "data": {
        "path": "/new/working/directory"
    }
}
```

### Server to Client Messages

#### Command Output

```json
{
    "type": "output",
    "data": {
        "request_id": "unique-request-id",
        "output": "command output text",
        "stream": "stdout"
    }
}
```

#### Command Completion

```json
{
    "type": "command_complete",
    "data": {
        "request_id": "unique-request-id",
        "exit_code": 0,
        "execution_time_ms": 125
    }
}
```

#### Error Message

```json
{
    "type": "error",
    "data": {
        "request_id": "unique-request-id",
        "error": "Command execution failed",
        "error_code": "EXEC_FAILED"
    }
}
```

#### Session Status

```json
{
    "type": "status",
    "data": {
        "status": "active",
        "working_directory": "/current/path",
        "pid": 1234
    }
}
```

## Error Handling

### HTTP Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid request parameters |
| 401 | Unauthorized - Invalid or missing authentication |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Session or resource not found |
| 409 | Conflict - Resource already exists |
| 422 | Unprocessable Entity - Validation errors |
| 500 | Internal Server Error - Server-side error |
| 503 | Service Unavailable - System temporarily unavailable |

### Error Response Format

```json
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid session parameters",
        "details": {
            "field": "working_directory",
            "reason": "Path does not exist"
        },
        "timestamp": "2024-09-24T10:40:00Z",
        "request_id": "req_123456789"
    }
}
```

### WebSocket Error Codes

| Code | Description |
|------|-------------|
| 4000 | Invalid message format |
| 4001 | Authentication failed |
| 4002 | Session not found |
| 4003 | Command execution failed |
| 4004 | Permission denied |
| 4005 | Session terminated |

### WebSocket Error Message

```json
{
    "type": "error",
    "data": {
        "code": 4003,
        "message": "Command execution failed",
        "details": "Permission denied: /protected/file",
        "timestamp": "2024-09-24T10:40:00Z"
    }
}
```

## Rate Limiting

API endpoints are rate-limited to prevent abuse:

- **Terminal Sessions**: 10 requests per minute per user
- **Command Execution**: 60 commands per minute per session
- **WebSocket Messages**: 100 messages per minute per connection
- **Metrics**: 30 requests per minute per user

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1632472800
```

## Security Considerations

### Command Validation

All commands are validated against a whitelist of allowed commands and patterns. Dangerous commands are blocked by default.

### Session Isolation

Each terminal session runs in an isolated environment with restricted access to the system.

### Audit Logging

All terminal activities are logged for security and compliance purposes.

### Input Sanitization

All user input is sanitized to prevent injection attacks.

## SDK Examples

### Python SDK

```python
import asyncio
import websockets
import json

class CasperTerminal:
    def __init__(self, base_url, auth_token):
        self.base_url = base_url
        self.auth_token = auth_token
        self.ws = None

    async def connect(self, session_id):
        uri = f"ws://{self.base_url}/ws/terminal/{session_id}?token={self.auth_token}"
        self.ws = await websockets.connect(uri)

    async def execute_command(self, command):
        message = {
            "type": "execute",
            "data": {
                "command": command,
                "request_id": f"req_{int(time.time())}"
            }
        }
        await self.ws.send(json.dumps(message))

    async def listen(self):
        async for message in self.ws:
            data = json.loads(message)
            print(f"Received: {data}")

# Usage
terminal = CasperTerminal("localhost:8742", "your-jwt-token")
await terminal.connect("session-id")
await terminal.execute_command("ls -la")
```

### JavaScript SDK

```javascript
class CasperTerminal {
    constructor(baseUrl, authToken) {
        this.baseUrl = baseUrl;
        this.authToken = authToken;
        this.ws = null;
    }

    async connect(sessionId) {
        const wsUrl = `ws://${this.baseUrl}/ws/terminal/${sessionId}?token=${this.authToken}`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => console.log('Connected to terminal');
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        this.ws.onerror = (error) => console.error('WebSocket error:', error);
    }

    executeCommand(command) {
        const message = {
            type: 'execute',
            data: {
                command: command,
                request_id: `req_${Date.now()}`
            }
        };
        this.ws.send(JSON.stringify(message));
    }

    handleMessage(data) {
        switch (data.type) {
            case 'output':
                console.log('Output:', data.data.output);
                break;
            case 'command_complete':
                console.log('Command completed with exit code:', data.data.exit_code);
                break;
            case 'error':
                console.error('Error:', data.data.error);
                break;
        }
    }
}

// Usage
const terminal = new CasperTerminal('localhost:8742', 'your-jwt-token');
await terminal.connect('session-id');
terminal.executeCommand('echo "Hello World"');
```

## Changelog

### Version 1.0.0 (2024-09-24)
- Initial API release
- WebSocket terminal communication
- Session management endpoints
- Command history tracking
- Metrics and monitoring
- Rate limiting implementation
- Security features and validation

---

*Last Updated: September 2024*
*For API support, contact: api-support@casper-prime.ai*