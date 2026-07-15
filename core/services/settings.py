"""Utility helpers for reading and writing CASPER configuration settings.

This module centralises persistence of user-tunable preferences that power the
dashboard "Settings" dialog. Settings are stored alongside the active project
under ``.casper/config/settings.json`` so they travel with the workspace and can
be versioned when desired.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

DEFAULT_SETTINGS = {
    "general": {
        "auto_launch_dashboard": False,
        "confirm_destructive_actions": True,
        "telemetry_opt_in": False,
    },
    "agents": {
        "max_parallel_agents": 4,
        "default_priority": "medium",
        "allow_devops_operations": True,
    },
    "repository": {
        "ignored_patterns": ["node_modules", ".git", "__pycache__"],
        "auto_format_on_apply": True,
        "require_human_approval": True,
    },
}


@dataclass
class SettingsStore:
    """Provide typed access to the settings JSON file."""

    project_root: Path
    file_name: str = "settings.json"
    _cache: Dict[str, Any] = field(default_factory=dict, init=False)

    @property
    def settings_path(self) -> Path:
        return self.project_root / ".casper" / "config" / self.file_name

    def load(self, refresh: bool = False) -> Dict[str, Any]:
        """Load settings from disk, falling back to defaults."""

        if not refresh and self._cache:
            return self._cache

        path = self.settings_path
        if not path.exists():
            self._cache = json.loads(json.dumps(DEFAULT_SETTINGS))
            return self._cache

        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except json.JSONDecodeError:
            data = {}

        merged = self._merge_defaults(data)
        self._cache = merged
        return merged

    def save(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Persist new settings to disk and return the stored snapshot."""

        merged = self._merge_defaults(data)

        path = self.settings_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(merged, handle, indent=2)

        self._cache = merged
        return merged

    def _merge_defaults(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Merge provided values with defaults, ensuring shape compatibility."""

        merged: Dict[str, Any] = json.loads(json.dumps(DEFAULT_SETTINGS))
        if not isinstance(data, dict):
            return merged

        for section, defaults in DEFAULT_SETTINGS.items():
            user_section = data.get(section, {}) if isinstance(data, dict) else {}
            if not isinstance(user_section, dict):
                merged[section] = defaults
                continue

            merged_section = defaults.copy()
            for key, value in user_section.items():
                merged_section[key] = value
            merged[section] = merged_section

        return merged


def get_settings_store(project_root: Path) -> SettingsStore:
    """Factory helper for convenience."""

    return SettingsStore(project_root=project_root)
