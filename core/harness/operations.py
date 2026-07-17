"""Operational state engines for CASPER artifacts, telemetry, config, and trust."""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Optional


# Engine 37: artifact registry ------------------------------------------------


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_id: str
    path: str
    kind: str
    size: int
    sha256: str
    created_at: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArtifactVerification:
    valid: bool
    artifact_id: str
    reason: str
    current_sha256: str = ""


class ArtifactRegistry:
    """Register immutable artifact identities and detect later file changes."""

    def __init__(self, workspace_root: Path | str) -> None:
        self.workspace_root = Path(workspace_root).expanduser().resolve()
        self._records: dict[str, ArtifactRecord] = {}

    @staticmethod
    def _digest(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _resolve(self, path: Path | str) -> Path:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = self.workspace_root / candidate
        resolved = candidate.resolve()
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError as exc:
            raise ValueError("artifact must be inside the workspace") from exc
        return resolved

    def register(
        self, path: Path | str, *, kind: str = "file", metadata: Optional[Mapping[str, Any]] = None
    ) -> ArtifactRecord:
        resolved = self._resolve(path)
        if not resolved.is_file():
            raise FileNotFoundError(f"artifact is not a file: {resolved}")
        digest = self._digest(resolved)
        relative = resolved.relative_to(self.workspace_root).as_posix()
        artifact_id = f"artifact_{digest[:16]}"
        record = ArtifactRecord(
            artifact_id,
            relative,
            kind,
            resolved.stat().st_size,
            digest,
            time.time(),
            dict(metadata or {}),
        )
        self._records[artifact_id] = record
        return record

    def get(self, artifact_id: str) -> Optional[ArtifactRecord]:
        return self._records.get(artifact_id)

    def list(self, *, kind: Optional[str] = None) -> tuple[ArtifactRecord, ...]:
        records = tuple(self._records.values())
        if kind is not None:
            records = tuple(record for record in records if record.kind == kind)
        return tuple(sorted(records, key=lambda item: (item.created_at, item.artifact_id)))

    def verify(self, artifact_id: str) -> ArtifactVerification:
        record = self.get(artifact_id)
        if record is None:
            return ArtifactVerification(False, artifact_id, "Artifact id is not registered.")
        path = self.workspace_root / record.path
        if not path.is_file():
            return ArtifactVerification(False, artifact_id, "Artifact file no longer exists.")
        digest = self._digest(path)
        if digest != record.sha256:
            return ArtifactVerification(False, artifact_id, "Artifact content hash changed.", digest)
        if path.stat().st_size != record.size:
            return ArtifactVerification(False, artifact_id, "Artifact size changed.", digest)
        return ArtifactVerification(True, artifact_id, "Artifact matches its registered digest.", digest)


# Engine 38: telemetry spans and metrics -------------------------------------


class SpanStatus(str, Enum):
    OK = "ok"
    ERROR = "error"


@dataclass(frozen=True)
class SpanRecord:
    span_id: str
    name: str
    started_at: float
    duration_ms: float
    status: SpanStatus
    attributes: dict[str, Any]
    error_type: str = ""
    error_message: str = ""


@dataclass(frozen=True)
class MetricSnapshot:
    counters: dict[str, float]
    observations: dict[str, tuple[float, ...]]
    spans: tuple[SpanRecord, ...]


@dataclass
class _ActiveSpan:
    span_id: str
    name: str
    started_at: float
    attributes: dict[str, Any]


class TelemetryCollector:
    """Collect dependency-free spans, counters, and numeric observations."""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._counters: dict[str, float] = {}
        self._observations: dict[str, list[float]] = {}
        self._spans: list[SpanRecord] = []

    def increment(self, name: str, value: float = 1.0) -> None:
        if not name.strip():
            raise ValueError("metric name cannot be empty")
        self._counters[name] = self._counters.get(name, 0.0) + float(value)

    def observe(self, name: str, value: float) -> None:
        if not name.strip():
            raise ValueError("metric name cannot be empty")
        self._observations.setdefault(name, []).append(float(value))

    @contextmanager
    def span(self, name: str, attributes: Optional[Mapping[str, Any]] = None) -> Iterator[_ActiveSpan]:
        if not name.strip():
            raise ValueError("span name cannot be empty")
        active = _ActiveSpan(f"span_{uuid.uuid4().hex[:16]}", name, self._clock(), dict(attributes or {}))
        try:
            yield active
        except BaseException as exc:
            duration = max(0.0, (self._clock() - active.started_at) * 1000.0)
            self._spans.append(SpanRecord(
                active.span_id, active.name, active.started_at, duration, SpanStatus.ERROR,
                dict(active.attributes), type(exc).__name__, str(exc),
            ))
            self.increment("span.errors")
            raise
        else:
            duration = max(0.0, (self._clock() - active.started_at) * 1000.0)
            self._spans.append(SpanRecord(
                active.span_id, active.name, active.started_at, duration, SpanStatus.OK,
                dict(active.attributes),
            ))
            self.increment("span.completed")
            self.observe(f"span.duration_ms.{name}", duration)

    def snapshot(self) -> MetricSnapshot:
        return MetricSnapshot(
            dict(self._counters),
            {name: tuple(values) for name, values in self._observations.items()},
            tuple(self._spans),
        )


# Engine 39: layered configuration -------------------------------------------


@dataclass(frozen=True)
class ConfigLayer:
    name: str
    values: Mapping[str, Any]


@dataclass(frozen=True)
class ConfigResolution:
    values: dict[str, Any]
    provenance: dict[str, str]


class LayeredConfiguration:
    """Resolve deterministic deep configuration with field provenance."""

    PRECEDENCE = ("defaults", "user", "project", "environment", "cli")

    def __init__(self, layers: tuple[ConfigLayer, ...] = ()) -> None:
        self._layers: dict[str, ConfigLayer] = {}
        for layer in layers:
            self.set_layer(layer.name, layer.values)

    def set_layer(self, name: str, values: Mapping[str, Any]) -> None:
        if name not in self.PRECEDENCE:
            raise ValueError(f"unknown configuration layer: {name}")
        self._layers[name] = ConfigLayer(name, dict(values))

    @staticmethod
    def environment_layer(
        environ: Mapping[str, str] = os.environ, *, prefix: str = "CASPER_"
    ) -> ConfigLayer:
        values: dict[str, Any] = {}
        for key, raw in environ.items():
            if not key.startswith(prefix):
                continue
            path = key[len(prefix):].casefold().split("__")
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = raw
            cursor = values
            for component in path[:-1]:
                cursor = cursor.setdefault(component, {})
            cursor[path[-1]] = parsed
        return ConfigLayer("environment", values)

    @staticmethod
    def _merge(
        target: dict[str, Any], source: Mapping[str, Any], layer: str,
        provenance: dict[str, str], prefix: str = "",
    ) -> None:
        for key, value in source.items():
            dotted = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, Mapping) and isinstance(target.get(key), Mapping):
                merged_child = dict(target[key])
                LayeredConfiguration._merge(merged_child, value, layer, provenance, dotted)
                target[key] = merged_child
            elif isinstance(value, Mapping):
                new_child: dict[str, Any] = {}
                LayeredConfiguration._merge(new_child, value, layer, provenance, dotted)
                target[key] = new_child
            else:
                target[key] = value
                provenance[dotted] = layer

    def resolve(self) -> ConfigResolution:
        values: dict[str, Any] = {}
        provenance: dict[str, str] = {}
        for name in self.PRECEDENCE:
            layer = self._layers.get(name)
            if layer is not None:
                self._merge(values, layer.values, name, provenance)
        return ConfigResolution(values, provenance)

    def get(self, dotted_path: str, default: Any = None) -> Any:
        cursor: Any = self.resolve().values
        for component in dotted_path.split("."):
            if not isinstance(cursor, Mapping) or component not in cursor:
                return default
            cursor = cursor[component]
        return cursor


# Engine 40: workspace trust profiles ----------------------------------------


class WorkspaceTrustLevel(str, Enum):
    UNTRUSTED = "untrusted"
    RESTRICTED = "restricted"
    TRUSTED = "trusted"


@dataclass(frozen=True)
class WorkspaceTrustProfile:
    level: WorkspaceTrustLevel
    load_project_config: bool
    allow_network: bool
    auto_approve_read_only: bool
    writable: bool


@dataclass(frozen=True)
class WorkspaceTrustDecision:
    root: str
    profile: WorkspaceTrustProfile
    source: str
    reason: str


class WorkspaceTrustManager:
    """Persist trust per workspace and inherit only from explicit parent rules."""

    PROFILES = {
        WorkspaceTrustLevel.UNTRUSTED: WorkspaceTrustProfile(
            WorkspaceTrustLevel.UNTRUSTED, False, False, False, False
        ),
        WorkspaceTrustLevel.RESTRICTED: WorkspaceTrustProfile(
            WorkspaceTrustLevel.RESTRICTED, True, False, True, True
        ),
        WorkspaceTrustLevel.TRUSTED: WorkspaceTrustProfile(
            WorkspaceTrustLevel.TRUSTED, True, True, True, True
        ),
    }

    def __init__(self, store_path: Optional[Path | str] = None) -> None:
        self.store_path = Path(store_path).expanduser().resolve() if store_path else None
        self._rules: dict[str, dict[str, Any]] = {}
        if self.store_path and self.store_path.is_file():
            raw = json.loads(self.store_path.read_text(encoding="utf-8"))
            for root, value in raw.items():
                self._rules[str(Path(root).expanduser().resolve())] = {
                    "level": WorkspaceTrustLevel(value["level"]).value,
                    "inherit": bool(value.get("inherit", False)),
                }

    def _save(self) -> None:
        if self.store_path is None:
            return
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.store_path.with_suffix(self.store_path.suffix + ".tmp")
        temporary.write_text(json.dumps(self._rules, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self.store_path)

    def set_trust(
        self, root: Path | str, level: WorkspaceTrustLevel | str, *, inherit: bool = False
    ) -> WorkspaceTrustDecision:
        resolved = str(Path(root).expanduser().resolve())
        selected = WorkspaceTrustLevel(level)
        self._rules[resolved] = {"level": selected.value, "inherit": bool(inherit)}
        self._save()
        return WorkspaceTrustDecision(
            resolved, self.PROFILES[selected], "exact",
            f"Workspace trust set to {selected.value}.",
        )

    def revoke(self, root: Path | str) -> None:
        self._rules.pop(str(Path(root).expanduser().resolve()), None)
        self._save()

    def decide(self, workspace: Path | str) -> WorkspaceTrustDecision:
        resolved_path = Path(workspace).expanduser().resolve()
        resolved = str(resolved_path)
        exact = self._rules.get(resolved)
        if exact is not None:
            level = WorkspaceTrustLevel(exact["level"])
            return WorkspaceTrustDecision(
                resolved, self.PROFILES[level], "exact", "An exact workspace trust rule matched."
            )
        candidates: list[tuple[int, str, dict[str, Any]]] = []
        for root, rule in self._rules.items():
            if not rule.get("inherit"):
                continue
            try:
                resolved_path.relative_to(Path(root))
            except ValueError:
                continue
            candidates.append((len(Path(root).parts), root, rule))
        if candidates:
            _, root, rule = max(candidates, key=lambda item: item[0])
            level = WorkspaceTrustLevel(rule["level"])
            return WorkspaceTrustDecision(
                resolved, self.PROFILES[level], f"inherited:{root}",
                "The most specific inheritable parent trust rule matched.",
            )
        return WorkspaceTrustDecision(
            resolved, self.PROFILES[WorkspaceTrustLevel.UNTRUSTED], "default",
            "No trust rule matched; fail closed as untrusted.",
        )
