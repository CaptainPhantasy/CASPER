#!/usr/bin/env python3
"""Project hook that supplies verification context and protects system paths."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _resolved(raw: str, cwd: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path(cwd) / path
    return path.resolve(strict=False)


def _deny(reason: str) -> None:
    print(reason, file=sys.stderr)
    raise SystemExit(2)


def main() -> int:
    payload = json.load(sys.stdin)
    event = str(payload.get("hook_event_name", ""))
    if event == "session_start":
        print(json.dumps({
            "hookSpecificOutput": {
                "additionalContext": (
                    "CASPER project hooks are active. Verify filesystem and command side effects "
                    "before reporting completion."
                )
            }
        }))
        return 0

    if event != "before_tool":
        return 0

    tool_name = str(payload.get("tool_name", ""))
    tool_input = payload.get("tool_input", {})
    if not isinstance(tool_input, dict):
        _deny("Tool input must be a JSON object.")

    protected = {Path("/"), Path("/System"), Path("/bin"), Path("/sbin"), Path("/usr")}
    cwd = str(payload.get("cwd", "."))
    if tool_name == "make_directory":
        target = _resolved(str(tool_input.get("path", "")), cwd)
        if target in protected:
            _deny(f"Project hook blocked protected system path: {target}")

    if tool_name == "run_command":
        argv = tool_input.get("argv", [])
        if not isinstance(argv, list):
            _deny("run_command argv must be a list.")
        command = [str(item) for item in argv]
        if command and command[0] == "sudo":
            _deny("Project hook requires elevated commands to stay operator-owned.")
        for item in command[1:]:
            if not item.startswith("-") and _resolved(item, cwd) in protected:
                _deny(f"Project hook blocked command targeting protected system path: {item}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
