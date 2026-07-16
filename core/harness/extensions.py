"""Namespaced registry for independently installed harness extensions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass(frozen=True)
class ExtensionSpec:
    namespace: str
    name: str
    version: str
    instance: Any = None
    capabilities: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def qualified_name(self) -> str:
        return f"{self.namespace}:{self.name}"


class ExtensionRegistry:
    def __init__(self) -> None:
        self._extensions: dict[str, ExtensionSpec] = {}

    @staticmethod
    def _valid_part(value: str) -> bool:
        return bool(value) and all(character.isalnum() or character in "_-" for character in value)

    def register(self, extension: ExtensionSpec) -> None:
        if not self._valid_part(extension.namespace) or not self._valid_part(extension.name):
            raise ValueError("extension namespace and name may contain letters, numbers, _ and -")
        if not extension.version.strip():
            raise ValueError("extension version is required")
        if extension.qualified_name in self._extensions:
            raise ValueError(f"extension already registered: {extension.qualified_name}")
        self._extensions[extension.qualified_name] = extension

    def get(self, qualified_name: str) -> ExtensionSpec | None:
        return self._extensions.get(qualified_name)

    def require(self, qualified_name: str) -> ExtensionSpec:
        extension = self.get(qualified_name)
        if extension is None:
            raise KeyError(f"unknown extension: {qualified_name}")
        return extension

    def list(self, namespace: str | None = None) -> tuple[ExtensionSpec, ...]:
        values: Iterable[ExtensionSpec] = self._extensions.values()
        if namespace is not None:
            values = (item for item in values if item.namespace == namespace)
        return tuple(sorted(values, key=lambda item: item.qualified_name))

    def unregister(self, qualified_name: str) -> ExtensionSpec | None:
        return self._extensions.pop(qualified_name, None)
