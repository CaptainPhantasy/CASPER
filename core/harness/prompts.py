"""Validated, versioned prompt templates."""

from __future__ import annotations

import hashlib
import string
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class PromptTemplate:
    name: str
    template: str
    description: str = ""
    version: str = "1"

    @property
    def variables(self) -> tuple[str, ...]:
        names: list[str] = []
        for _, field_name, format_spec, conversion in string.Formatter().parse(self.template):
            if field_name is None:
                continue
            if not field_name.isidentifier() or format_spec or conversion:
                raise ValueError(f"unsafe prompt field: {field_name!r}")
            names.append(field_name)
        return tuple(dict.fromkeys(names))

    @property
    def checksum(self) -> str:
        content = f"{self.name}\0{self.version}\0{self.template}".encode()
        return hashlib.sha256(content).hexdigest()

    def render(self, variables: Mapping[str, object]) -> str:
        expected = set(self.variables)
        supplied = set(variables)
        missing = expected - supplied
        unknown = supplied - expected
        if missing:
            raise ValueError(f"missing prompt variables: {sorted(missing)}")
        if unknown:
            raise ValueError(f"unknown prompt variables: {sorted(unknown)}")
        return self.template.format_map(dict(variables))


class PromptLibrary:
    """Store templates by name and version without silent replacement."""

    def __init__(self, templates: tuple[PromptTemplate, ...] = ()) -> None:
        self._templates: dict[tuple[str, str], PromptTemplate] = {}
        for template in templates:
            self.register(template)

    def register(self, template: PromptTemplate, *, replace: bool = False) -> None:
        key = (template.name, template.version)
        if key in self._templates and not replace:
            raise ValueError(f"prompt already registered: {template.name}@{template.version}")
        template.variables
        self._templates[key] = template

    def get(self, name: str, version: str | None = None) -> PromptTemplate:
        if version is not None:
            try:
                return self._templates[(name, version)]
            except KeyError as exc:
                raise KeyError(f"unknown prompt: {name}@{version}") from exc
        candidates = [template for (item_name, _), template in self._templates.items() if item_name == name]
        if not candidates:
            raise KeyError(f"unknown prompt: {name}")
        return sorted(candidates, key=lambda item: item.version)[-1]

    def render(self, name: str, variables: Mapping[str, object], *, version: str | None = None) -> str:
        return self.get(name, version).render(variables)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted({name for name, _ in self._templates}))
