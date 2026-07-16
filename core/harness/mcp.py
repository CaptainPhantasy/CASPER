"""Declarative MCP server configuration registry."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum


class MCPTransport(str, Enum):
    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"


@dataclass(frozen=True)
class MCPServerConfig:
    name: str
    transport: MCPTransport
    command: tuple[str, ...] = ()
    url: str = ""
    environment: dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    timeout_seconds: float = 30.0

    def redacted(self) -> dict[str, object]:
        return {
            "name": self.name,
            "transport": self.transport.value,
            "command": list(self.command),
            "url": self.url,
            "environment_keys": sorted(self.environment),
            "enabled": self.enabled,
            "timeout_seconds": self.timeout_seconds,
        }


class MCPServerRegistry:
    def __init__(self) -> None:
        self._servers: dict[str, MCPServerConfig] = {}

    @staticmethod
    def _validate(config: MCPServerConfig) -> None:
        if not config.name or not config.name.replace("_", "").replace("-", "").isalnum():
            raise ValueError("MCP server name may contain letters, numbers, _ and -")
        if config.transport == MCPTransport.STDIO and not config.command:
            raise ValueError("stdio MCP servers require a command")
        if config.transport != MCPTransport.STDIO and not config.url.startswith(("http://", "https://")):
            raise ValueError("HTTP and SSE MCP servers require an http(s) URL")
        if config.timeout_seconds <= 0:
            raise ValueError("MCP timeout must be positive")

    def register(self, config: MCPServerConfig) -> None:
        self._validate(config)
        if config.name in self._servers:
            raise ValueError(f"MCP server already registered: {config.name}")
        self._servers[config.name] = config

    def get(self, name: str) -> MCPServerConfig | None:
        return self._servers.get(name)

    def require(self, name: str) -> MCPServerConfig:
        config = self.get(name)
        if config is None:
            raise KeyError(f"unknown MCP server: {name}")
        return config

    def set_enabled(self, name: str, enabled: bool) -> MCPServerConfig:
        updated = replace(self.require(name), enabled=enabled)
        self._servers[name] = updated
        return updated

    def list(self, *, enabled_only: bool = False) -> tuple[MCPServerConfig, ...]:
        names = sorted(self._servers)
        return tuple(
            self._servers[name] for name in names
            if not enabled_only or self._servers[name].enabled
        )

    def unregister(self, name: str) -> MCPServerConfig | None:
        return self._servers.pop(name, None)
