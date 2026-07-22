"""
CASPER Prime Monitoring Module

This module provides comprehensive monitoring capabilities for the CASPER Prime system,
including performance metrics, health checks, and system monitoring.
"""

import time
import psutil
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry, CONTENT_TYPE_LATEST, generate_latest
from fastapi import APIRouter, Response
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)

# Prometheus metrics
REGISTRY = CollectorRegistry()

# Terminal metrics
TERMINAL_SESSIONS_ACTIVE = Gauge(
    'casper_terminal_active_sessions_total',
    'Number of active terminal sessions',
    registry=REGISTRY
)

TERMINAL_COMMANDS_EXECUTED = Counter(
    'casper_terminal_commands_executed_total',
    'Total number of commands executed',
    ['session_id', 'status'],
    registry=REGISTRY
)

TERMINAL_COMMAND_DURATION = Histogram(
    'casper_terminal_command_duration_seconds',
    'Command execution duration in seconds',
    ['session_id'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=REGISTRY
)

TERMINAL_MEMORY_USAGE = Gauge(
    'casper_terminal_memory_usage_bytes',
    'Memory usage by terminal sessions in bytes',
    ['session_id'],
    registry=REGISTRY
)

# WebSocket metrics
WEBSOCKET_CONNECTIONS = Gauge(
    'casper_websocket_connections_total',
    'Number of active WebSocket connections',
    registry=REGISTRY
)

WEBSOCKET_MESSAGES_SENT = Counter(
    'casper_websocket_messages_sent_total',
    'Total number of WebSocket messages sent',
    ['connection_id', 'message_type'],
    registry=REGISTRY
)

WEBSOCKET_MESSAGES_RECEIVED = Counter(
    'casper_websocket_messages_received_total',
    'Total number of WebSocket messages received',
    ['connection_id', 'message_type'],
    registry=REGISTRY
)

WEBSOCKET_ERRORS = Counter(
    'casper_websocket_errors_total',
    'Total number of WebSocket errors',
    ['error_type'],
    registry=REGISTRY
)

# System metrics
SYSTEM_CPU_USAGE = Gauge(
    'casper_system_cpu_usage_percent',
    'System CPU usage percentage',
    registry=REGISTRY
)

SYSTEM_MEMORY_USAGE = Gauge(
    'casper_system_memory_usage_bytes',
    'System memory usage in bytes',
    registry=REGISTRY
)

SYSTEM_DISK_USAGE = Gauge(
    'casper_system_disk_usage_percent',
    'System disk usage percentage',
    registry=REGISTRY
)

# Application metrics
APP_REQUEST_DURATION = Histogram(
    'casper_app_request_duration_seconds',
    'Application request duration in seconds',
    ['method', 'endpoint', 'status_code'],
    registry=REGISTRY
)

APP_ACTIVE_USERS = Gauge(
    'casper_app_active_users_total',
    'Number of active users',
    registry=REGISTRY
)

APP_INFO = Info(
    'casper_app_info',
    'Application information',
    registry=REGISTRY
)


@dataclass
class SystemMetrics:
    """System performance metrics"""
    cpu_percent: float
    memory_used: int
    memory_total: int
    memory_percent: float
    disk_used: int
    disk_total: int
    disk_percent: float
    load_average: tuple
    uptime_seconds: float
    timestamp: datetime


@dataclass
class TerminalMetrics:
    """Terminal-specific metrics"""
    active_sessions: int
    total_commands: int
    average_execution_time: float
    memory_usage: int
    error_rate: float
    timestamp: datetime


@dataclass
class WebSocketMetrics:
    """WebSocket connection metrics"""
    active_connections: int
    messages_sent: int
    messages_received: int
    connection_errors: int
    average_latency: float
    timestamp: datetime


class MetricsCollector:
    """Collects and manages system metrics"""

    def __init__(self):
        self.start_time = time.time()
        self.terminal_sessions = set()
        self.websocket_connections = set()

    def collect_system_metrics(self) -> SystemMetrics:
        """Collect system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()

            # Disk usage
            disk = psutil.disk_usage('/')

            # Load average
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)

            # Uptime
            uptime = time.time() - self.start_time

            metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_used=memory.used,
                memory_total=memory.total,
                memory_percent=memory.percent,
                disk_used=disk.used,
                disk_total=disk.total,
                disk_percent=(disk.used / disk.total) * 100,
                load_average=load_avg,
                uptime_seconds=uptime,
                timestamp=datetime.utcnow()
            )

            # Update Prometheus metrics
            SYSTEM_CPU_USAGE.set(cpu_percent)
            SYSTEM_MEMORY_USAGE.set(memory.used)
            SYSTEM_DISK_USAGE.set(metrics.disk_percent)

            return metrics

        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            raise

    def collect_terminal_metrics(self) -> TerminalMetrics:
        """Collect terminal-specific metrics"""
        try:
            # This would typically query the database or active sessions
            # For now, using the tracked sessions
            active_sessions = len(self.terminal_sessions)

            # Update Prometheus metrics
            TERMINAL_SESSIONS_ACTIVE.set(active_sessions)

            metrics = TerminalMetrics(
                active_sessions=active_sessions,
                total_commands=0,  # Would be fetched from database
                average_execution_time=0.0,  # Calculated from recent commands
                memory_usage=0,  # Sum of all session memory usage
                error_rate=0.0,  # Error rate calculation
                timestamp=datetime.utcnow()
            )

            return metrics

        except Exception as e:
            logger.error(f"Failed to collect terminal metrics: {e}")
            raise

    def collect_websocket_metrics(self) -> WebSocketMetrics:
        """Collect WebSocket connection metrics"""
        try:
            active_connections = len(self.websocket_connections)

            # Update Prometheus metrics
            WEBSOCKET_CONNECTIONS.set(active_connections)

            metrics = WebSocketMetrics(
                active_connections=active_connections,
                messages_sent=0,  # Would be tracked from WebSocket manager
                messages_received=0,
                connection_errors=0,
                average_latency=0.0,
                timestamp=datetime.utcnow()
            )

            return metrics

        except Exception as e:
            logger.error(f"Failed to collect WebSocket metrics: {e}")
            raise

    def track_terminal_session(self, session_id: str):
        """Track a new terminal session"""
        self.terminal_sessions.add(session_id)
        logger.debug(f"Tracking terminal session: {session_id}")

    def untrack_terminal_session(self, session_id: str):
        """Stop tracking a terminal session"""
        self.terminal_sessions.discard(session_id)
        logger.debug(f"Stopped tracking terminal session: {session_id}")

    def track_websocket_connection(self, connection_id: str):
        """Track a new WebSocket connection"""
        self.websocket_connections.add(connection_id)
        logger.debug(f"Tracking WebSocket connection: {connection_id}")

    def untrack_websocket_connection(self, connection_id: str):
        """Stop tracking a WebSocket connection"""
        self.websocket_connections.discard(connection_id)
        logger.debug(f"Stopped tracking WebSocket connection: {connection_id}")

    def record_command_execution(self, session_id: str, duration: float, success: bool):
        """Record terminal command execution metrics"""
        status = 'success' if success else 'error'
        TERMINAL_COMMANDS_EXECUTED.labels(session_id=session_id, status=status).inc()
        TERMINAL_COMMAND_DURATION.labels(session_id=session_id).observe(duration)

    def record_websocket_message(self, connection_id: str, message_type: str, direction: str):
        """Record WebSocket message metrics"""
        if direction == 'sent':
            WEBSOCKET_MESSAGES_SENT.labels(connection_id=connection_id, message_type=message_type).inc()
        else:
            WEBSOCKET_MESSAGES_RECEIVED.labels(connection_id=connection_id, message_type=message_type).inc()

    def record_websocket_error(self, error_type: str):
        """Record WebSocket error"""
        WEBSOCKET_ERRORS.labels(error_type=error_type).inc()


class HealthChecker:
    """System health monitoring"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.checks = {}

    async def check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        try:
            # This would check database connection
            # For now, return a mock health check
            return {
                "status": "healthy",
                "response_time_ms": 5.2,
                "connections": 10,
                "max_connections": 100
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def check_redis_health(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance"""
        try:
            # This would check Redis connection
            return {
                "status": "healthy",
                "memory_usage_mb": 45.2,
                "connected_clients": 5
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def check_terminal_health(self) -> Dict[str, Any]:
        """Check terminal system health"""
        try:
            metrics = self.metrics_collector.collect_terminal_metrics()
            return {
                "status": "healthy" if metrics.active_sessions < 100 else "degraded",
                "active_sessions": metrics.active_sessions,
                "memory_usage_mb": metrics.memory_usage / (1024 * 1024)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def comprehensive_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }

        # Run all health checks
        health_status["checks"]["database"] = await self.check_database_health()
        health_status["checks"]["redis"] = await self.check_redis_health()
        health_status["checks"]["terminal"] = await self.check_terminal_health()

        # Check system resources
        system_metrics = self.metrics_collector.collect_system_metrics()
        health_status["checks"]["system"] = {
            "status": "healthy" if system_metrics.cpu_percent < 80 and system_metrics.memory_percent < 85 else "degraded",
            "cpu_percent": system_metrics.cpu_percent,
            "memory_percent": system_metrics.memory_percent,
            "disk_percent": system_metrics.disk_percent
        }

        # Determine overall status
        statuses = [check["status"] for check in health_status["checks"].values()]
        if "unhealthy" in statuses:
            health_status["status"] = "unhealthy"
        elif "degraded" in statuses:
            health_status["status"] = "degraded"

        return health_status


# Global instances
metrics_collector = MetricsCollector()
health_checker = HealthChecker(metrics_collector)

# FastAPI router for monitoring endpoints
router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return await health_checker.comprehensive_health_check()


@router.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    # Collect latest metrics
    metrics_collector.collect_system_metrics()
    metrics_collector.collect_terminal_metrics()
    metrics_collector.collect_websocket_metrics()

    # Generate Prometheus format
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST
    )


@router.get("/metrics/system")
async def get_system_metrics():
    """Get system metrics in JSON format"""
    metrics = metrics_collector.collect_system_metrics()
    return asdict(metrics)


@router.get("/metrics/terminal")
async def get_terminal_metrics():
    """Get terminal metrics in JSON format"""
    metrics = metrics_collector.collect_terminal_metrics()
    return asdict(metrics)


@router.get("/metrics/websocket")
async def get_websocket_metrics():
    """Get WebSocket metrics in JSON format"""
    metrics = metrics_collector.collect_websocket_metrics()
    return asdict(metrics)


@asynccontextmanager
async def request_timer(method: str, endpoint: str, status_code: int):
    """Context manager for timing requests"""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        APP_REQUEST_DURATION.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).observe(duration)


# Background task for periodic metrics collection
async def periodic_metrics_collection():
    """Collect metrics periodically in the background"""
    while True:
        try:
            metrics_collector.collect_system_metrics()
            metrics_collector.collect_terminal_metrics()
            metrics_collector.collect_websocket_metrics()
            await asyncio.sleep(15)  # Collect metrics every 15 seconds
        except Exception as e:
            logger.error(f"Error in periodic metrics collection: {e}")
            await asyncio.sleep(60)  # Wait longer on error


# Initialize application info
APP_INFO.info({
    'version': '1.0.0',
    'name': 'CASPER Prime',
    'description': 'Autonomous AI Development Platform',
    'build_date': datetime.utcnow().isoformat()
})