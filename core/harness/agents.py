"""Named custom-agent profiles with explicit model and tool boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field

from .policy import PermissionMode


@dataclass(frozen=True)
class AgentProfile:
    name: str
    description: str
    system_prompt: str
    model: str = ""
    allowed_tools: tuple[str, ...] = ()
    permission_mode: PermissionMode = PermissionMode.DEFAULT
    max_steps: int = 24
    metadata: dict[str, str] = field(default_factory=dict)


class AgentProfileRegistry:
    def __init__(self) -> None:
        self._profiles: dict[str, AgentProfile] = {}

    def register(self, profile: AgentProfile) -> None:
        if not profile.name or not profile.name.replace("_", "").replace("-", "").isalnum():
            raise ValueError("profile name may contain letters, numbers, _ and -")
        if not profile.system_prompt.strip():
            raise ValueError("profile system_prompt is required")
        if profile.max_steps < 1:
            raise ValueError("profile max_steps must be positive")
        if profile.name in self._profiles:
            raise ValueError(f"agent profile already registered: {profile.name}")
        self._profiles[profile.name] = profile

    def get(self, name: str) -> AgentProfile | None:
        return self._profiles.get(name)

    def require(self, name: str) -> AgentProfile:
        profile = self.get(name)
        if profile is None:
            raise KeyError(f"unknown agent profile: {name}")
        return profile

    def list(self) -> tuple[AgentProfile, ...]:
        return tuple(self._profiles[name] for name in sorted(self._profiles))

    def unregister(self, name: str) -> AgentProfile | None:
        return self._profiles.pop(name, None)
