"""Single source of truth for CASPER's verified harness feature catalog."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureGroup:
    cycle: int
    name: str
    features: tuple[str, ...]


FEATURE_GROUPS: tuple[FeatureGroup, ...] = (
    FeatureGroup(1, "Canonical harness", (
        "bounded runtime", "native provider failover", "typed tool kernel", "permission policy",
        "transactional workspace", "repository context", "durable runs", "event/headless protocol",
        "evidence evaluation", "modern terminal client",
    )),
    FeatureGroup(2, "Extensions and orchestration", (
        "lifecycle hooks", "extension registry", "skill discovery", "MCP registry", "agent profiles",
        "task DAG scheduler", "cancellation", "background jobs", "health diagnostics", "worktree leases",
    )),
    FeatureGroup(3, "Developer intelligence", (
        "symbol index", "dependency graph", "ranked search", "diagnostic parser", "test selector",
        "change impact", "plan tracker", "JSON Schema validation", "prompt library", "file watcher",
    )),
    FeatureGroup(4, "Safety and operations", (
        "secret redaction", "command risk", "resource budgets", "circuit breaker", "retry policy",
        "audit chain", "artifact registry", "telemetry", "layered configuration", "workspace trust",
    )),
    FeatureGroup(5, "Interaction and portability", (
        "slash commands", "natural-language routing", "command palette", "session branching", "diff preview",
        "conflict detection", "model routing", "content cache", "session bundles", "onboarding doctor",
    )),
)


def feature_count() -> int:
    return sum(len(group.features) for group in FEATURE_GROUPS)


def render_feature_catalog() -> str:
    lines = [f"CASPER verified engine catalog ({feature_count()} total)"]
    number = 1
    for group in FEATURE_GROUPS:
        lines.append(f"\nCycle {group.cycle} - {group.name}")
        for feature in group.features:
            lines.append(f"  {number:02d}. {feature}")
            number += 1
    return "\n".join(lines)
