"""
Build-system detection and real verification commands.

The platform is stack-agnostic: it inspects a generated project, figures out what
kind of project it is, and returns the actual commands to build and test it. The
Verifier runs these for real and reads the exit code — no guessing whether the
work "looks done".
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class BuildSystem:
    kind: str  # swiftpm | node | python | go | rust | unknown
    build_cmd: Optional[List[str]] = None
    test_cmd: Optional[List[str]] = None
    setup_cmd: Optional[List[str]] = None  # e.g. npm install
    available: bool = True  # is the toolchain installed?
    toolchain: str = ""  # the binary it needs
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "build_cmd": self.build_cmd,
            "test_cmd": self.test_cmd,
            "setup_cmd": self.setup_cmd,
            "available": self.available,
            "toolchain": self.toolchain,
            "notes": self.notes,
        }


def _has(tool: str) -> bool:
    return shutil.which(tool) is not None


def detect_build_system(project_root: str) -> BuildSystem:
    """Inspect a project directory and return how to build/test it for real."""
    root = Path(project_root)

    if (root / "Package.swift").exists():
        return BuildSystem(
            kind="swiftpm",
            build_cmd=["swift", "build"],
            test_cmd=["swift", "test"],
            available=_has("swift"),
            toolchain="swift",
            notes="Swift Package Manager project.",
        )

    if (root / "package.json").exists():
        # Prefer a build script if present; always able to at least install.
        return BuildSystem(
            kind="node",
            setup_cmd=["npm", "install", "--no-audit", "--no-fund"],
            build_cmd=["npm", "run", "build", "--if-present"],
            test_cmd=["npm", "test", "--if-present"],
            available=_has("npm"),
            toolchain="npm",
            notes="Node/JavaScript project.",
        )

    if (root / "go.mod").exists():
        return BuildSystem(
            kind="go",
            build_cmd=["go", "build", "./..."],
            test_cmd=["go", "test", "./..."],
            available=_has("go"),
            toolchain="go",
            notes="Go module.",
        )

    if (root / "Cargo.toml").exists():
        return BuildSystem(
            kind="rust",
            build_cmd=["cargo", "build"],
            test_cmd=["cargo", "test"],
            available=_has("cargo"),
            toolchain="cargo",
            notes="Rust crate.",
        )

    if (
        (root / "pyproject.toml").exists()
        or (root / "requirements.txt").exists()
        or _any_py(root)
    ):
        py = "python3" if _has("python3") else "python"
        # Compile-check all .py files; run pytest if tests exist.
        return BuildSystem(
            kind="python",
            build_cmd=[py, "-m", "compileall", "-q", "."],
            test_cmd=[py, "-m", "pytest", "-q"] if _has_pytest(root) else None,
            available=_has(py),
            toolchain=py,
            notes="Python project.",
        )

    return BuildSystem(
        kind="unknown", available=False, notes="No recognized build system."
    )


def _any_py(root: Path) -> bool:
    try:
        return any(p.suffix == ".py" for p in root.rglob("*.py"))
    except Exception:
        return False


def _has_pytest(root: Path) -> bool:
    try:
        return any("test" in p.name.lower() for p in root.rglob("*.py"))
    except Exception:
        return False
