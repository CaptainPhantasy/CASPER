"""
Feature 6 — Environment bootstrapping (guided setup for non-developers).

A non-dev has no idea what Node, a venv, PYTHONPATH, or a port is. This module
turns "get it running" into a few guided, validated steps:

- Detect required runtimes (python, node, npm) and the project's venv.
- Validate API keys *live* (catching the stale/rotated-key problem) and store
  validated keys securely.
- Detect missing/broken environment variables.
- Produce a one-action launch plan (and optionally run it) so backend + frontend
  start together without manual terminal gymnastics.

Everything is reported in plain language with a clear "what to do next".
"""

from __future__ import annotations

import asyncio
import os
import shutil
import socket
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class RuntimeStatus:
    name: str
    present: bool
    version: str = ""
    advice: str = ""


@dataclass
class KeyStatus:
    provider: str
    state: str  # "valid" | "invalid" | "missing"
    advice: str = ""


@dataclass
class EnvReport:
    runtimes: List[RuntimeStatus] = field(default_factory=list)
    keys: List[KeyStatus] = field(default_factory=list)
    ports: Dict[int, bool] = field(default_factory=dict)  # port -> free?
    ready: bool = False
    summary: str = ""

    def to_dict(self) -> Dict:
        return {
            "runtimes": [r.__dict__ for r in self.runtimes],
            "keys": [k.__dict__ for k in self.keys],
            "ports": self.ports,
            "ready": self.ready,
            "summary": self.summary,
        }


class EnvironmentBootstrapper:
    def __init__(
        self, project_root: str, backend_port: int = 8742, frontend_port: int = 4188
    ):
        self.project_root = Path(project_root)
        self.backend_port = backend_port
        self.frontend_port = frontend_port
        self.venv_python = self._find_venv_python()

    # --- detection -------------------------------------------------------
    def _find_venv_python(self) -> Optional[str]:
        for name in (".casper-venv", "venv", ".venv"):
            cand = self.project_root / name / "bin" / "python"
            if cand.exists():
                return str(cand)
        return None

    def _runtime(
        self, name: str, version_args: List[str], advice: str
    ) -> RuntimeStatus:
        path = shutil.which(name)
        if not path:
            return RuntimeStatus(name=name, present=False, advice=advice)
        try:
            r = subprocess.run(
                [path] + version_args, capture_output=True, text=True, timeout=8
            )
            ver = (
                (r.stdout or r.stderr).strip().splitlines()[0]
                if (r.stdout or r.stderr)
                else ""
            )
        except Exception:
            ver = ""
        return RuntimeStatus(name=name, present=True, version=ver)

    def _port_free(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(("127.0.0.1", port)) != 0

    async def validate_key(self, provider: str, key: str) -> bool:
        """Validate a key live against the provider. Returns True if usable."""
        if not key:
            return False
        try:
            if provider == "anthropic":
                from anthropic import AsyncAnthropic

                client = AsyncAnthropic(api_key=key)
                await client.models.list()
                return True
            if provider == "openai":
                from openai import AsyncOpenAI

                client = AsyncOpenAI(api_key=key)
                await client.models.list()
                return True
        except Exception:
            return False
        return False

    # --- full report -----------------------------------------------------
    async def check(self) -> EnvReport:
        report = EnvReport()
        report.runtimes = [
            self._runtime(
                "python3", ["--version"], "Install Python 3.11+ from python.org."
            ),
            self._runtime(
                "node", ["--version"], "Install Node.js LTS from nodejs.org."
            ),
            self._runtime("npm", ["--version"], "npm ships with Node.js."),
        ]
        if self.venv_python:
            report.runtimes.append(
                RuntimeStatus(
                    name="project venv", present=True, version=self.venv_python
                )
            )
        else:
            report.runtimes.append(
                RuntimeStatus(
                    name="project venv",
                    present=False,
                    advice="Run setup to create a virtual environment with the backend dependencies.",
                )
            )

        # Keys (validate whatever is in the environment live).
        for provider, env in (
            ("anthropic", "ANTHROPIC_API_KEY"),
            ("openai", "OPENAI_API_KEY"),
        ):
            key = os.environ.get(env)
            if not key:
                report.keys.append(
                    KeyStatus(
                        provider=provider,
                        state="missing",
                        advice=f"Add your {provider} API key in Settings.",
                    )
                )
            else:
                ok = await self.validate_key(provider, key)
                report.keys.append(
                    KeyStatus(
                        provider=provider,
                        state="valid" if ok else "invalid",
                        advice=(
                            ""
                            if ok
                            else f"Your {provider} key was rejected — it may be rotated/expired. Paste a fresh one."
                        ),
                    )
                )

        report.ports = {
            self.backend_port: self._port_free(self.backend_port),
            self.frontend_port: self._port_free(self.frontend_port),
        }

        # Readiness: at least one valid key + python present.
        has_valid_key = any(k.state == "valid" for k in report.keys)
        py_ok = any(r.name == "python3" and r.present for r in report.runtimes)
        report.ready = has_valid_key and py_ok
        report.summary = self._summarize(report)
        return report

    def _summarize(self, r: EnvReport) -> str:
        if r.ready:
            return "Everything needed is set up. You can start building."
        missing = [rt.name for rt in r.runtimes if not rt.present]
        bad_keys = [k.provider for k in r.keys if k.state != "valid"]
        bits = []
        if missing:
            bits.append("missing: " + ", ".join(missing))
        if bad_keys:
            bits.append("needs a working API key for: " + ", ".join(bad_keys))
        return (
            "Not ready yet — "
            + ("; ".join(bits) if bits else "see details above")
            + "."
        )

    # --- one-action launch ----------------------------------------------
    def launch_plan(self) -> Dict[str, List[str]]:
        """The exact commands the one-button launch runs (also shown to the user)."""
        py = self.venv_python or "python3"
        return {
            "backend": [py, "-m", "core.server"],
            "frontend": [
                "npm",
                "run",
                "preview",
                "--",
                "--port",
                str(self.frontend_port),
                "--strictPort",
            ],
        }

    def launch(self) -> Dict[str, str]:
        """Start backend + frontend detached. Returns a status per service."""
        plan = self.launch_plan()
        result: Dict[str, str] = {}
        env = {
            **os.environ,
            "PYTHONPATH": str(self.project_root),
            "PORT": str(self.backend_port),
        }

        if self._port_free(self.backend_port):
            try:
                subprocess.Popen(
                    plan["backend"],
                    cwd=str(self.project_root),
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                result["backend"] = f"starting on :{self.backend_port}"
            except Exception as e:
                result["backend"] = f"failed: {e}"
        else:
            result["backend"] = f"already running on :{self.backend_port}"

        dash = self.project_root / "dashboard"
        if dash.exists():
            if self._port_free(self.frontend_port):
                try:
                    subprocess.Popen(
                        plan["frontend"],
                        cwd=str(dash),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    result["frontend"] = f"starting on :{self.frontend_port}"
                except Exception as e:
                    result["frontend"] = f"failed: {e}"
            else:
                result["frontend"] = f"already running on :{self.frontend_port}"
        return result
