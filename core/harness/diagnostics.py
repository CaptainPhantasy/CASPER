"""Normalize compiler, linter, type-checker, and test diagnostics."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Diagnostic:
    path: str
    line: int
    column: int | None
    severity: str
    code: str | None
    message: str
    source: str


class DiagnosticParser:
    """Parse common single-line diagnostic formats into one typed model."""

    _TSC = re.compile(
        r"^(?P<path>.+?)\((?P<line>\d+),(?P<col>\d+)\):\s*"
        r"(?P<severity>error|warning)\s+(?P<code>TS\d+):\s*(?P<message>.+)$",
        re.IGNORECASE,
    )
    _POSITIONAL = re.compile(
        r"^(?P<path>.+?):(?P<line>\d+)(?::(?P<col>\d+))?:\s*"
        r"(?:(?P<severity>error|warning|info|note|fatal)\s*:?\s*)?"
        r"(?:(?P<code>[A-Z][A-Z0-9_-]*\d{2,}|[A-Z]\d{3,})\s+)?(?P<message>.+)$",
        re.IGNORECASE,
    )
    _BRACKET_CODE = re.compile(r"\s+\[(?P<code>[\w-]+)]$")

    @classmethod
    def parse(cls, text: str, *, source: str = "auto", cwd: Path | str | None = None) -> tuple[Diagnostic, ...]:
        diagnostics: list[Diagnostic] = []
        for raw_line in text.splitlines():
            line_text = raw_line.strip()
            match = cls._TSC.match(line_text)
            detected_source = source
            if match:
                detected_source = "typescript" if source == "auto" else source
            else:
                match = cls._POSITIONAL.match(line_text)
            if not match:
                continue
            fields = match.groupdict()
            message = fields["message"].strip()
            code = fields.get("code")
            bracket = cls._BRACKET_CODE.search(message)
            if bracket and code is None:
                code = bracket.group("code")
                message = message[: bracket.start()].rstrip()
                if detected_source == "auto":
                    detected_source = "mypy"
            if detected_source == "auto":
                detected_source = "ruff" if code and re.fullmatch(r"[A-Z]+\d+", code) else "generic"
            severity = (fields.get("severity") or cls._infer_severity(message, code)).casefold()
            path = cls._normalize_path(fields["path"], cwd)
            diagnostics.append(Diagnostic(
                path=path,
                line=int(fields["line"]),
                column=int(fields["col"]) if fields.get("col") else None,
                severity=severity,
                code=code,
                message=message,
                source=detected_source,
            ))
        return tuple(diagnostics)

    @staticmethod
    def _infer_severity(message: str, code: str | None) -> str:
        folded = message.casefold()
        if "warning" in folded:
            return "warning"
        if code and code.upper().startswith("W"):
            return "warning"
        return "error"

    @staticmethod
    def _normalize_path(path: str, cwd: Path | str | None) -> str:
        value = Path(path)
        if cwd is None or not value.is_absolute():
            return value.as_posix()
        try:
            return value.resolve().relative_to(Path(cwd).resolve()).as_posix()
        except ValueError:
            return value.as_posix()
