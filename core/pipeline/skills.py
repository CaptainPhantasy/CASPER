"""
Feature 5 — Retrievable, versioned skills registry.

A skill is a proven, reusable procedure ("scaffold a Next.js app", "wire Stripe
checkout") captured as ordered steps plus trigger keywords. Before the planner
decomposes a task it asks the registry whether a known-good skill applies, and
reuses it instead of re-deriving the approach.

Skills are JSON files. They live in the project at `.casper/skills/` and, when a
shared skills home is configured (env `CASPER_SKILLS_HOME`, default
`~/.casper/skills`), the project directory is symlinked to it so a skill that is
fine-tuned in one project propagates to all of them.

Skills improve from use: each successful run increments `success_count` and
raises confidence; repeated failure lowers it and flags the skill for review.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_SHARED_HOME = os.path.expanduser("~/.casper/skills")


@dataclass
class Skill:
    id: str
    name: str
    description: str
    triggers: List[str] = field(default_factory=list)   # keywords/phrases
    steps: List[str] = field(default_factory=list)       # ordered procedure
    version: int = 1
    success_count: int = 0
    failure_count: int = 0
    confidence: float = 0.5
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    source: str = "builtin"

    def to_dict(self) -> Dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict) -> "Skill":
        known = {f for f in Skill.__dataclass_fields__}  # type: ignore[attr-defined]
        return Skill(**{k: v for k, v in d.items() if k in known})

    def match_score(self, text: str) -> float:
        """Keyword-overlap score weighted by the skill's proven confidence."""
        if not self.triggers:
            return 0.0
        t = text.lower()
        hits = sum(1 for kw in self.triggers if kw.lower() in t)
        if hits == 0:
            return 0.0
        coverage = hits / len(self.triggers)
        return round(coverage * (0.5 + 0.5 * self.confidence), 4)


class SkillRegistry:
    """File-backed registry with a project dir symlinked to a shared home."""

    def __init__(self, project_root: str, shared_home: Optional[str] = None):
        self.project_root = Path(project_root)
        self.project_dir = self.project_root / ".casper" / "skills"
        self.shared_home = Path(shared_home or os.environ.get("CASPER_SKILLS_HOME", _DEFAULT_SHARED_HOME))
        self._skills: Dict[str, Skill] = {}
        self._ensure_layout()
        self.reload()

    # --- storage layout --------------------------------------------------
    def _ensure_layout(self) -> None:
        """Create the shared home and symlink the project skills dir to it.
        Falls back to a real directory if symlinking isn't possible."""
        try:
            self.shared_home.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create shared skills home {self.shared_home}: {e}")
        try:
            (self.project_root / ".casper").mkdir(parents=True, exist_ok=True)
            if self.project_dir.is_symlink():
                return
            if not self.project_dir.exists():
                # Symlink project → shared so skills propagate across projects.
                os.symlink(self.shared_home, self.project_dir, target_is_directory=True)
            # If it exists as a real dir already, leave it (don't clobber).
        except Exception as e:
            logger.warning(f"Skills symlink unavailable, using local dir: {e}")
            try:
                self.project_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

    def _storage_dir(self) -> Path:
        # Reads/writes go through the project dir, which is the symlink target.
        return self.project_dir if self.project_dir.exists() else self.shared_home

    # --- loading / saving ------------------------------------------------
    def reload(self) -> None:
        self._skills.clear()
        d = self._storage_dir()
        if not d.exists():
            return
        for f in d.glob("*.json"):
            try:
                self._skills[f.stem] = Skill.from_dict(json.loads(f.read_text()))
            except Exception as e:
                logger.warning(f"Skipping unreadable skill {f}: {e}")

    def _save(self, skill: Skill) -> None:
        d = self._storage_dir()
        try:
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{skill.id}.json").write_text(json.dumps(skill.to_dict(), indent=2))
        except Exception as e:
            logger.warning(f"Could not persist skill {skill.id}: {e}")

    # --- public API ------------------------------------------------------
    def add_skill(self, name: str, description: str, triggers: List[str],
                  steps: List[str], source: str = "learned") -> Skill:
        skill = Skill(
            id=f"skill_{uuid.uuid4().hex[:10]}",
            name=name, description=description,
            triggers=triggers, steps=steps, source=source,
        )
        self._skills[skill.id] = skill
        self._save(skill)
        return skill

    def find(self, query: str, min_score: float = 0.34, limit: int = 3) -> List[Skill]:
        """Return the best-matching skills for a task/spec text, best first."""
        scored = [(s.match_score(query), s) for s in self._skills.values()]
        scored = [(sc, s) for sc, s in scored if sc >= min_score]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:limit]]

    def best(self, query: str, min_score: float = 0.34) -> Optional[Skill]:
        matches = self.find(query, min_score=min_score, limit=1)
        return matches[0] if matches else None

    def record_outcome(self, skill_id: str, success: bool) -> None:
        """Update a skill's stats after a run. Skills improve (or get flagged)."""
        skill = self._skills.get(skill_id)
        if not skill:
            return
        if success:
            skill.success_count += 1
        else:
            skill.failure_count += 1
        total = skill.success_count + skill.failure_count
        # Laplace-smoothed success rate as confidence.
        skill.confidence = round((skill.success_count + 1) / (total + 2), 4)
        # Bump version when a skill crosses a meaningful confidence change.
        skill.version += 1 if success else 0
        skill.updated_at = time.time()
        self._save(skill)

    def all_skills(self) -> List[Skill]:
        return sorted(self._skills.values(), key=lambda s: s.confidence, reverse=True)


# A couple of seed skills so the registry is useful on first run. These are
# intentionally generic; real ones accumulate from successful pipeline runs.
SEED_SKILLS = [
    {
        "name": "python-module-with-tests",
        "description": "Create a Python module plus a pytest test file and run the tests.",
        "triggers": ["python", "function", "module", "script", "pytest"],
        "steps": [
            "Write the module with type hints and a docstring.",
            "Write a pytest test file covering the acceptance criteria.",
            "Run pytest and ensure it passes.",
        ],
    },
    {
        "name": "react-component",
        "description": "Scaffold a typed React function component with minimal styling.",
        "triggers": ["react", "component", "tsx", "frontend", "ui"],
        "steps": [
            "Create a .tsx function component with typed props and a default export.",
            "Add minimal Tailwind styling.",
            "Verify it type-checks with the project's build.",
        ],
    },
]


def ensure_seed_skills(registry: SkillRegistry) -> None:
    """Add seed skills if the registry is empty (first-run convenience)."""
    if registry.all_skills():
        return
    for s in SEED_SKILLS:
        registry.add_skill(s["name"], s["description"], s["triggers"], s["steps"], source="builtin")
