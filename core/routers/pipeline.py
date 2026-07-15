"""
API surface for the CASPER Prime execution pipeline.

Endpoints
---------
POST /api/pipeline/run        Start a run (intent → spec → build → verify). Returns run_id.
                              If the compiler needs clarification, returns status
                              "needs_clarification" with questions to answer and
                              resubmit (same intent + answers + run_id).
GET  /api/pipeline/run/{id}   Poll status, progress, spec, artifacts, change log.
GET  /api/pipeline/env        Environment readiness (runtimes, live key validation, ports).
POST /api/pipeline/launch     One-action launch of backend + frontend.
GET  /api/pipeline/skills     List the skills the planner can reuse.
POST /api/pipeline/undo       Undo a reversible change from a run's ledger.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.pipeline import (
    Pipeline,
    AutonomyMode,
    EnvironmentBootstrapper,
    SkillRegistry,
    ensure_seed_skills,
)

router = APIRouter()

# Repo root (this file is core/routers/pipeline.py).
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# In-memory run registry. Each entry keeps the live Pipeline (for its ledger) and
# the latest progress/result so the UI can poll.
_RUNS: Dict[str, Dict] = {}


class RunRequest(BaseModel):
    intent: str
    answers: Optional[Dict[str, str]] = None
    mode: str = "AUTO"  # STRICT | AUTO | YOLO
    project_root: Optional[str] = None
    build_cmd: Optional[List[str]] = None
    test_cmd: Optional[List[str]] = None
    budget_tokens: Optional[int] = None


class UndoRequest(BaseModel):
    run_id: str
    change_id: str


def _resolve_mode(mode: str) -> AutonomyMode:
    try:
        return AutonomyMode(mode.upper())
    except Exception:
        return AutonomyMode.AUTO


def _project_root_for(req: RunRequest, run_id: str) -> str:
    if req.project_root:
        return req.project_root
    # Default to a contained, reversible sandbox so runs never clobber the repo.
    sandbox = os.path.join(_REPO_ROOT, ".casper", "pipeline_runs", run_id)
    os.makedirs(sandbox, exist_ok=True)
    return sandbox


@router.post("/api/pipeline/run")
async def pipeline_run(req: RunRequest):
    if not req.intent or not req.intent.strip():
        raise HTTPException(status_code=400, detail="intent is required")

    # Decide the run id and sandbox up-front so the directory name and the run id
    # always match (constructed exactly once).
    run_id = "run_" + uuid.uuid4().hex[:12]
    if req.project_root:
        root = req.project_root
        os.makedirs(root, exist_ok=True)
    else:
        root = os.path.join(_REPO_ROOT, ".casper", "pipeline_runs", run_id)
        os.makedirs(root, exist_ok=True)

    pipe = Pipeline(
        project_root=root,
        autonomy_mode=_resolve_mode(req.mode),
        budget_tokens=req.budget_tokens,
    )
    # Align the Pipeline's own run id with ours for consistent reporting.
    pipe.run_id = run_id
    pipe.progress.run_id = run_id

    progress: List[Dict] = []
    pipe.progress.on_update(lambda p: progress.append(p))

    _RUNS[run_id] = {
        "status": "running",
        "pipeline": pipe,
        "progress": progress,
        "result": None,
        "project_root": root,
    }

    async def _execute():
        try:
            result = await pipe.run(
                req.intent,
                answers=req.answers,
                build_cmd=req.build_cmd,
                test_cmd=req.test_cmd,
            )
            _RUNS[run_id]["status"] = result.status
            _RUNS[run_id]["result"] = result.to_dict()
        except Exception as e:  # never let a run crash the server
            _RUNS[run_id]["status"] = "failed"
            _RUNS[run_id]["result"] = {
                "status": "failed",
                "human_summary": f"Run failed: {e}",
            }

    asyncio.create_task(_execute())
    return {"run_id": run_id, "status": "running"}


@router.get("/api/pipeline/run/{run_id}")
async def pipeline_status(run_id: str):
    entry = _RUNS.get(run_id)
    if not entry:
        raise HTTPException(status_code=404, detail="unknown run_id")
    return {
        "run_id": run_id,
        "status": entry["status"],
        "project_root": entry.get("project_root"),
        "progress": entry["progress"],
        "result": entry["result"],
    }


@router.get("/api/pipeline/env")
async def pipeline_env():
    boot = EnvironmentBootstrapper(_REPO_ROOT)
    report = await boot.check()
    return {**report.to_dict(), "launch_plan": boot.launch_plan()}


@router.post("/api/pipeline/launch")
async def pipeline_launch():
    boot = EnvironmentBootstrapper(_REPO_ROOT)
    return {"started": boot.launch()}


@router.get("/api/pipeline/skills")
async def pipeline_skills():
    reg = SkillRegistry(_REPO_ROOT)
    ensure_seed_skills(reg)
    return {"skills": [s.to_dict() for s in reg.all_skills()]}


@router.post("/api/pipeline/undo")
async def pipeline_undo(req: UndoRequest):
    entry = _RUNS.get(req.run_id)
    if not entry:
        raise HTTPException(status_code=404, detail="unknown run_id")
    pipe: Pipeline = entry["pipeline"]
    return pipe.ledger.undo(req.change_id)
