"""Compatibility proof for CASPER's terminal identity."""

from __future__ import annotations

import hashlib
import io

from rich.console import Console

import core.cli


def test_casper_ascii_identity_is_preserved(monkeypatch) -> None:
    output = io.StringIO()
    monkeypatch.setattr(
        core.cli,
        "console",
        Console(file=output, force_terminal=False, color_system=None, width=200),
    )

    core.cli.print_modern_banner()

    rendered = output.getvalue()
    assert len(rendered) == 1037
    assert hashlib.sha256(rendered.encode()).hexdigest() == (
        "b9995c987598cff903fd32a2c3bc8d18a1569bb2a8fd14187df5cec7e91a70b8"
    )
    assert [len(line) for line in rendered.strip().splitlines()] == [
        109,
        111,
        113,
        113,
        114,
        115,
        116,
        117,
        118,
    ]
