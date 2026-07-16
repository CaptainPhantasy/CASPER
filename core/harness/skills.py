"""Filesystem skill discovery with small, dependency-free metadata parsing."""

from __future__ import annotations

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
            for line in lines[1:]:
                if line.strip() == "---":
                    break
                key, separator, value = line.partition(":")
                if separator and key.strip() in {"name", "description", "version", "tags"}:
                    values[key.strip()] = value.strip().strip("\"'")
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
                    warnings.append(f"duplicate skill ignored: {skill.name} at {path}")
                    continue
                found[skill.name] = skill
        return SkillDiscoveryResult(tuple(found[name] for name in sorted(found)), tuple(warnings))
