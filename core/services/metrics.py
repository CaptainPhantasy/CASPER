"""
Prometheus metrics collection for CASPER Prime.

Tracks:
- HTTP request count, latency, and errors
- Task submissions and completion
- LLM API calls by provider and status
- Agent pool utilization
- Approval queue depth
- WebSocket connection count
- System resource usage (CPU, memory)

Exposes metrics via the /metrics endpoint in FastAPI.
"""

import time
import psutil
from typing import Optional
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    REGISTRY,
)

# ---------------------------------------------------------------------------
# Metrics definitions
# ---------------------------------------------------------------------------

# HTTP request metrics
http_requests_total = Counter(
    "casper_http_requests_total",
    "Total HTTP requests by method, path, and status",
    ["method", "path", "status"],
)

http_request_duration_seconds = Histogram(
    "casper_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Task metrics
tasks_submitted_total = Counter(
    "casper_tasks_submitted_total",
    "Total tasks submitted by priority",
    ["priority"],
)

tasks_completed_total = Counter(
    "casper_tasks_completed_total",
    "Total tasks completed by status",
    ["status"],
)

tasks_active = Gauge(
    "casper_tasks_active",
    "Currently active (in-progress) tasks",
)

# LLM metrics
llm_calls_total = Counter(
    "casper_llm_calls_total",
    "Total LLM API calls by provider and outcome",
    ["provider", "outcome"],
)

llm_call_duration_seconds = Histogram(
    "casper_llm_call_duration_seconds",
    "LLM API call latency in seconds",
    ["provider"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)

llm_circuit_breaker_state = Gauge(
    "casper_llm_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["provider"],
)

# Agent metrics
agents_active = Gauge(
    "casper_agents_active",
    "Active agents by role",
    ["role"],
)

agents_busy = Gauge(
    "casper_agents_busy",
    "Busy (working) agents by role",
    ["role"],
)

# Approval metrics
approval_requests_total = Counter(
    "casper_approval_requests_total",
    "Total approval requests by risk level",
    ["risk_level"],
)

approval_queue_depth = Gauge(
    "casper_approval_queue_depth",
    "Pending approval requests awaiting decision",
)

approval_decisions_total = Counter(
    "casper_approval_decisions_total",
    "Total approval decisions by type",
    ["decision"],
)

# WebSocket metrics
websocket_connections_active = Gauge(
    "casper_websocket_connections_active",
    "Active WebSocket connections",
)

# System metrics
system_cpu_percent = Gauge(
    "casper_system_cpu_percent",
    "System CPU usage percentage",
)

system_memory_percent = Gauge(
    "casper_system_memory_percent",
    "System memory usage percentage",
)

system_memory_available_bytes = Gauge(
    "casper_system_memory_available_bytes",
    "Available system memory in bytes",
)

# Build info
casper_info = Info(
    "casper",
    "CASPER Prime build and version information",
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def record_http_request(method: str, path: str, status: int, duration: float):
    """Record an HTTP request."""
    http_requests_total.labels(method=method, path=path, status=str(status)).inc()
    http_request_duration_seconds.labels(method=method, path=path).observe(duration)


def record_task_submitted(priority: str = "normal"):
    """Record a task submission."""
    tasks_submitted_total.labels(priority=priority).inc()
    tasks_active.inc()


def record_task_completed(status: str = "success"):
    """Record a task completion."""
    tasks_completed_total.labels(status=status).inc()
    tasks_active.dec()


def record_llm_call(provider: str, outcome: str, duration: float = 0.0):
    """Record an LLM API call."""
    llm_calls_total.labels(provider=provider, outcome=outcome).inc()
    if duration > 0:
        llm_call_duration_seconds.labels(provider=provider).observe(duration)


def record_approval_request(risk_level: str = "low"):
    """Record an approval request."""
    approval_requests_total.labels(risk_level=risk_level).inc()
    approval_queue_depth.inc()


def record_approval_decision(decision: str = "approved"):
    """Record an approval decision."""
    approval_decisions_total.labels(decision=decision).inc()
    approval_queue_depth.dec()


def update_agent_metrics(active: dict, busy: dict):
    """Update agent pool metrics.

    Args:
        active: Dict mapping role -> count of active agents
        busy: Dict mapping role -> count of busy agents
    """
    for role, count in active.items():
        agents_active.labels(role=role).set(count)
    for role, count in busy.items():
        agents_busy.labels(role=role).set(count)


def update_system_metrics():
    """Update system resource metrics from psutil."""
    try:
        system_cpu_percent.set(psutil.cpu_percent(interval=0.1))
        mem = psutil.virtual_memory()
        system_memory_percent.set(mem.percent)
        system_memory_available_bytes.set(mem.available)
    except Exception:
        pass  # psutil may not be available in all environments


def set_build_info(version: str = "0.1.0-beta.1", commit: str = "unknown"):
    """Set build information."""
    casper_info.info({"version": version, "commit": commit})


def get_metrics() -> bytes:
    """Generate Prometheus metrics in text format."""
    update_system_metrics()
    return generate_latest()


def get_metrics_content_type() -> str:
    """Return the content type for Prometheus metrics."""
    return CONTENT_TYPE_LATEST
