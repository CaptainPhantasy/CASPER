"""Filesystem skill discovery with small, dependency-free metadata parsing."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkillMetadata:
    name: str
    description: str
    path: Path
    version: str = ""
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class SkillDiscoveryResult:
    skills: tuple[SkillMetadata, ...]
    warnings: tuple[str, ...] = ()


class SkillDiscovery:
    """Discover SKILL.md files beneath ordered roots; first duplicate wins."""

    def __init__(self, roots: tuple[Path | str, ...], *, max_files: int = 2_000) -> None:
        self.roots = tuple(Path(root).expanduser().resolve() for root in roots)
        self.max_files = max(1, max_files)

    @staticmethod
    def _metadata(path: Path) -> SkillMetadata:
        text = path.read_text(encoding="utf-8", errors="replace")[:32_768]
        values: dict[str, str] = {}
        lines = text.splitlines()
        if lines and lines[0].strip() == "---":
            for index, line in enumerate(lines[1:], start=1):
                if line.strip() == "---":
                    break
                key, separator, value = line.partition(":")
                if separator and key.strip() in {"name", "description", "version", "tags"}:
                    field = key.strip()
                    parsed = value.strip().strip("\"'")
                    if field == "description" and parsed in {">", ">-", "|", "|-"}:
                        continuation: list[str] = []
                        for extra in lines[index + 1:]:
                            if extra.strip() == "---" or extra and not extra[0].isspace():
                                break
                            if extra.strip():
                                continuation.append(extra.strip())
                        parsed = " ".join(continuation)
                    values[field] = parsed
        if "name" not in values:
            values["name"] = path.parent.name
        if "description" not in values:
            for line in lines:
                stripped = line.strip().lstrip("#").strip()
                if stripped and stripped != "---" and not stripped.startswith(("name:", "version:", "tags:")):
                    values["description"] = stripped
                    break
        raw_tags = values.get("tags", "").strip("[]")
        tags = tuple(part.strip().strip("\"'") for part in raw_tags.split(",") if part.strip())
        return SkillMetadata(
            values["name"], values.get("description", ""), path,
            values.get("version", ""), tags,
        )

    def discover(self) -> SkillDiscoveryResult:
        found: dict[str, SkillMetadata] = {}
        warnings: list[str] = []
        visited = 0
        for root in self.roots:
            if not root.is_dir():
                warnings.append(f"skill root does not exist: {root}")
                continue
            for path in sorted(root.rglob("SKILL.md")):
                visited += 1
                if visited > self.max_files:
                    warnings.append(f"skill scan stopped at bounded limit {self.max_files}")
                    return SkillDiscoveryResult(tuple(found.values()), tuple(warnings))
                try:
                    skill = self._metadata(path)
                except OSError as exc:
                    warnings.append(f"cannot read {path}: {exc}")
                    continue
                if skill.name in found:
                    continue
                found[skill.name] = skill
        return SkillDiscoveryResult(tuple(found[name] for name in sorted(found)), tuple(warnings))


def default_skill_roots(project_root: Path | str) -> tuple[Path, ...]:
    """Return existing project and shared skill roots in deterministic priority order."""
    project = Path(project_root).expanduser().resolve()
    candidates: list[Path] = [
        project / ".casper" / "skills",
        project / ".claude" / "skills",
    ]
    configured = os.environ.get("CASPER_SKILLS_HOME", "")
    candidates.extend(Path(item).expanduser() for item in configured.split(os.pathsep) if item)
    candidates.extend([
        Path.home() / ".codex" / "skills",
        Path.home() / ".agents" / "skills",
        Path.home() / ".claude" / "skills",
    ])
    roots: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.is_dir() and resolved not in seen:
            roots.append(resolved)
            seen.add(resolved)
    return tuple(roots)
