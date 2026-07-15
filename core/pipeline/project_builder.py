"""
Generic, knowledge-informed multi-file project builder.

This is the platform capability that lets CASPER build real applications — any
stack — rather than emit a single orphan file:

1. Research: fetch current docs/examples (WebKnowledge + GitHubKnowledge) for the
   spec so generation is grounded in real, current APIs.
2. Scaffold: the model emits a complete multi-file project as a file manifest.
3. Build: detect the build system and run the REAL build/test, capturing exit codes.
4. Self-heal: on a real build error, feed the compiler output back and rewrite the
   offending files; rebuild. Loop until green or out of attempts.

The file-manifest format is delimiter-based (not JSON) so code with quotes,
newlines, and braces round-trips reliably:

    <<<FILE relative/path.ext>>>
    ...file content...
    <<<ENDFILE>>>
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.pipeline.buildsystems import BuildSystem, detect_build_system
from core.pipeline.models import FrozenSpec
from core.services.llm import llm_service
from core.services.web_knowledge import WebKnowledge, GitHubKnowledge

logger = logging.getLogger(__name__)

_FILE_RE = re.compile(r"<<<FILE\s+(.+?)>>>\n(.*?)\n<<<ENDFILE>>>", re.DOTALL)

_SCAFFOLD_SYSTEM = (
    "You are CASPER's senior engineer. You produce COMPLETE, COMPILABLE multi-file "
    "projects. Use the provided reference docs for correct, current APIs. Output ONLY "
    "the file manifest in the exact delimiter format requested — no prose."
)


@dataclass
class BuildAttempt:
    stage: str  # setup | build | test
    cmd: List[str]
    exit_code: int
    ok: bool
    output_tail: str

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "cmd": self.cmd,
            "exit_code": self.exit_code,
            "ok": self.ok,
            "output_tail": self.output_tail,
        }


@dataclass
class ProjectBuildResult:
    success: bool
    project_root: str
    files: List[str] = field(default_factory=list)
    build_system: Optional[dict] = None
    attempts: List[BuildAttempt] = field(default_factory=list)
    repair_rounds: int = 0
    human_summary: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "project_root": self.project_root,
            "files": self.files,
            "build_system": self.build_system,
            "repair_rounds": self.repair_rounds,
            "attempts": [a.to_dict() for a in self.attempts],
            "human_summary": self.human_summary,
        }


def parse_manifest(text: str) -> Dict[str, str]:
    """Parse a <<<FILE>>> manifest into {path: content}."""
    out: Dict[str, str] = {}
    for m in _FILE_RE.finditer(text or ""):
        path = m.group(1).strip().strip("`").strip()
        content = m.group(2)
        if path:
            out[path] = content
    return out


class ProjectBuilder:
    def __init__(self, project_root: str, timeout: int = 600):
        self.project_root = project_root
        self.timeout = timeout
        self.web = WebKnowledge(project_root)
        self.gh = GitHubKnowledge(project_root)

    # --- knowledge -------------------------------------------------------
    def gather_knowledge(
        self, spec: FrozenSpec, github_repos: Optional[List[str]] = None
    ) -> str:
        """Build a reference brief from web docs + (optional) GitHub example files."""
        query = spec.summary + " " + " ".join(r.text for r in spec.requirements)
        brief = self.web.research_brief(query, max_chars=7000)
        gh_parts: List[str] = []
        for repo in (github_repos or [])[:2]:
            readme = self.gh.get_readme(repo, max_chars=4000)
            if readme:
                gh_parts.append(f"### GitHub {repo} README\n{readme}")
        if gh_parts:
            brief = (brief + "\n\n" + "\n\n".join(gh_parts))[:11000]
        return brief

    # --- scaffold --------------------------------------------------------
    async def scaffold(
        self, spec: FrozenSpec, knowledge: str, model: Optional[str] = None
    ) -> List[str]:
        reqs = "\n".join(
            f"- {r.text} (acceptance: {'; '.join(r.acceptance_criteria) or 'n/a'})"
            for r in spec.requirements
        )
        constraints = "\n".join(f"- {c}" for c in spec.constraints) or "- (none)"
        prompt = (
            f"Build this project so it COMPILES and runs.\n\n"
            f"GOAL: {spec.summary}\n\nREQUIREMENTS:\n{reqs}\n\nCONSTRAINTS:\n{constraints}\n\n"
            + (
                f"REFERENCE DOCS (use these for correct, current APIs):\n{knowledge}\n\n"
                if knowledge
                else ""
            )
            + "Output the COMPLETE project as a file manifest, each file as:\n"
            "<<<FILE relative/path>>>\n<file content>\n<<<ENDFILE>>>\n\n"
            "Include every file needed to build (manifests, sources, config). Make it compile."
        )
        raw = await llm_service.complete(
            prompt=prompt,
            system=_SCAFFOLD_SYSTEM,
            model=model,
            tier="frontier",
            max_tokens=8000,
        )
        files = parse_manifest(raw)
        return self._write_files(files)

    def _write_files(self, files: Dict[str, str]) -> List[str]:
        written: List[str] = []
        for rel, content in files.items():
            # Stay inside the project root.
            safe = os.path.normpath(rel).lstrip("/")
            if safe.startswith(".."):
                continue
            full = os.path.join(self.project_root, safe)
            try:
                Path(full).parent.mkdir(parents=True, exist_ok=True)
                Path(full).write_text(content, encoding="utf-8")
                written.append(safe)
            except Exception as e:
                logger.warning(f"Could not write {full}: {e}")
        return written

    # --- build -----------------------------------------------------------
    def _run(self, stage: str, cmd: List[str]) -> BuildAttempt:
        try:
            r = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            tail = ((r.stdout or "")[-1500:] + "\n" + (r.stderr or "")[-2500:]).strip()
            return BuildAttempt(
                stage=stage,
                cmd=cmd,
                exit_code=r.returncode,
                ok=(r.returncode == 0),
                output_tail=tail,
            )
        except subprocess.TimeoutExpired:
            return BuildAttempt(
                stage=stage, cmd=cmd, exit_code=124, ok=False, output_tail="timed out"
            )
        except Exception as e:
            return BuildAttempt(
                stage=stage, cmd=cmd, exit_code=1, ok=False, output_tail=str(e)
            )

    def build(self, bs: BuildSystem) -> List[BuildAttempt]:
        attempts: List[BuildAttempt] = []
        if bs.setup_cmd:
            attempts.append(self._run("setup", bs.setup_cmd))
        if bs.build_cmd:
            attempts.append(self._run("build", bs.build_cmd))
        # Only test if build passed.
        if bs.test_cmd and attempts and attempts[-1].ok:
            attempts.append(self._run("test", bs.test_cmd))
        return attempts

    # --- repair ----------------------------------------------------------
    async def repair(
        self, spec: FrozenSpec, error_log: str, model: Optional[str] = None
    ) -> List[str]:
        existing = self._list_project_files()
        listing = "\n".join(existing[:60])
        prompt = (
            f"The project failed to build. Fix it.\n\nGOAL: {spec.summary}\n\n"
            f"BUILD ERROR:\n{error_log[-3000:]}\n\n"
            f"PROJECT FILES:\n{listing}\n\n"
            "Output ONLY the files that must change, in manifest format:\n"
            "<<<FILE relative/path>>>\n<complete new content>\n<<<ENDFILE>>>\n"
            "Return complete file contents (not diffs). Fix the actual cause of the error."
        )
        raw = await llm_service.complete(
            prompt=prompt,
            system=_SCAFFOLD_SYSTEM,
            model=model,
            tier="frontier",
            max_tokens=6000,
        )
        files = parse_manifest(raw)
        return self._write_files(files)

    def _list_project_files(self) -> List[str]:
        out: List[str] = []
        for p in Path(self.project_root).rglob("*"):
            if (
                p.is_file()
                and ".build" not in p.parts
                and "node_modules" not in p.parts
                and ".git" not in p.parts
            ):
                out.append(str(p.relative_to(self.project_root)))
        return out

    # --- orchestration ---------------------------------------------------
    async def build_project(
        self,
        spec: FrozenSpec,
        model: Optional[str] = None,
        github_repos: Optional[List[str]] = None,
        max_repair: int = 3,
        on_progress=None,
    ) -> ProjectBuildResult:
        def progress(stage: str, detail: str = ""):
            if on_progress:
                try:
                    on_progress(stage, detail)
                except Exception:
                    pass

        progress("researching", "Reading current docs")
        knowledge = self.gather_knowledge(spec, github_repos)

        progress("scaffolding", "Writing the project files")
        files = await self.scaffold(spec, knowledge, model=model)

        bs = detect_build_system(self.project_root)
        if not bs.available:
            return ProjectBuildResult(
                success=False,
                project_root=self.project_root,
                files=files,
                build_system=bs.to_dict(),
                human_summary=f"Generated the project, but the '{bs.toolchain or bs.kind}' toolchain isn't installed to build it.",
            )

        all_attempts: List[BuildAttempt] = []
        repair_rounds = 0
        progress("building", f"Building ({bs.kind})")
        attempts = self.build(bs)
        all_attempts += attempts

        while not _attempts_ok(attempts) and repair_rounds < max_repair:
            repair_rounds += 1
            err = _first_failure_log(attempts)
            progress("repairing", f"Fixing build error (round {repair_rounds})")
            await self.repair(spec, err, model=model)
            bs = detect_build_system(
                self.project_root
            )  # files may have changed manifest
            attempts = self.build(bs)
            all_attempts += attempts

        ok = _attempts_ok(attempts)
        return ProjectBuildResult(
            success=ok,
            project_root=self.project_root,
            files=self._list_project_files(),
            build_system=bs.to_dict(),
            attempts=all_attempts,
            repair_rounds=repair_rounds,
            human_summary=(
                f"Built and verified ✓ ({bs.kind}) after {repair_rounds} self-repair round(s)."
                if ok
                else f"Couldn't get a clean build after {repair_rounds} repair attempt(s). Last error preserved."
            ),
        )


def _attempts_ok(attempts: List[BuildAttempt]) -> bool:
    return bool(attempts) and all(a.ok for a in attempts)


def _first_failure_log(attempts: List[BuildAttempt]) -> str:
    for a in attempts:
        if not a.ok:
            return f"[{a.stage}] exit {a.exit_code}\n{a.output_tail}"
    return ""
