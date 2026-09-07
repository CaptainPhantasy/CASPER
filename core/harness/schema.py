"""Dependency-free JSON Schema validation for structured model output."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    keyword: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    issues: tuple[ValidationIssue, ...]
    value: Any = None


class JSONSchemaValidator:
    """Validate the practical JSON Schema subset used by tool responses."""

    def __init__(self, schema: dict[str, Any]) -> None:
        self.schema = schema

    def validate_json(self, text: str) -> ValidationResult:
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            return ValidationResult(False, (ValidationIssue("$", "json", f"invalid JSON at line {exc.lineno}: {exc.msg}"),))
        return self.validate(value)

    def validate(self, value: Any) -> ValidationResult:
        issues: list[ValidationIssue] = []
        self._check(self.schema, value, "$", issues)
        return ValidationResult(not issues, tuple(issues), value)

    def _check(self, schema: dict[str, Any], value: Any, path: str, issues: list[ValidationIssue]) -> None:
        if "const" in schema and value != schema["const"]:
            issues.append(ValidationIssue(path, "const", f"must equal {schema['const']!r}"))
        if "enum" in schema and value not in schema["enum"]:
            issues.append(ValidationIssue(path, "enum", f"must be one of {schema['enum']!r}"))
        expected = schema.get("type")
        if expected is not None and not self._matches_type(value, expected):
            issues.append(ValidationIssue(path, "type", f"expected {expected}, got {type(value).__name__}"))
            return
        if isinstance(value, dict):
            required = schema.get("required", ())
            for name in required:
                if name not in value:
                    issues.append(ValidationIssue(f"{path}.{name}", "required", "property is required"))
            properties = schema.get("properties", {})
            for name, item in value.items():
                item_path = f"{path}.{name}"
                if name in properties:
                    self._check(properties[name], item, item_path, issues)
                elif schema.get("additionalProperties") is False:
                    issues.append(ValidationIssue(item_path, "additionalProperties", "unexpected property"))
                elif isinstance(schema.get("additionalProperties"), dict):
                    self._check(schema["additionalProperties"], item, item_path, issues)
        if isinstance(value, list):
            if "minItems" in schema and len(value) < schema["minItems"]:
                issues.append(ValidationIssue(path, "minItems", f"requires at least {schema['minItems']} items"))
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                issues.append(ValidationIssue(path, "maxItems", f"allows at most {schema['maxItems']} items"))
            item_schema = schema.get("items")
            if isinstance(item_schema, dict):
                for index, item in enumerate(value):
                    self._check(item_schema, item, f"{path}[{index}]", issues)
        if isinstance(value, str):
            if "minLength" in schema and len(value) < schema["minLength"]:
                issues.append(ValidationIssue(path, "minLength", f"requires at least {schema['minLength']} characters"))
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                issues.append(ValidationIssue(path, "maxLength", f"allows at most {schema['maxLength']} characters"))
            if "pattern" in schema and re.search(schema["pattern"], value) is None:
                issues.append(ValidationIssue(path, "pattern", f"does not match {schema['pattern']!r}"))
        if self._is_number(value):
            if "minimum" in schema and value < schema["minimum"]:
                issues.append(ValidationIssue(path, "minimum", f"must be at least {schema['minimum']}"))
            if "maximum" in schema and value > schema["maximum"]:
                issues.append(ValidationIssue(path, "maximum", f"must be at most {schema['maximum']}"))
        self._check_composition(schema, value, path, issues)

    def _check_composition(self, schema: dict[str, Any], value: Any, path: str, issues: list[ValidationIssue]) -> None:
        for keyword in ("anyOf", "oneOf"):
            choices = schema.get(keyword)
            if not choices:
                continue
            matches = 0
            for choice in choices:
                nested: list[ValidationIssue] = []
                self._check(choice, value, path, nested)
                matches += not nested
            valid = matches >= 1 if keyword == "anyOf" else matches == 1
            if not valid:
                issues.append(ValidationIssue(path, keyword, f"matched {matches} alternatives"))

    @staticmethod
    def _is_number(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    @classmethod
    def _matches_type(cls, value: Any, expected: str | list[str]) -> bool:
        if isinstance(expected, list):
            return any(cls._matches_type(value, item) for item in expected)
        return {
            "null": value is None,
            "boolean": isinstance(value, bool),
            "integer": isinstance(value, int) and not isinstance(value, bool),
            "number": cls._is_number(value),
            "string": isinstance(value, str),
            "array": isinstance(value, list),
            "object": isinstance(value, dict),
        }.get(expected, False)
