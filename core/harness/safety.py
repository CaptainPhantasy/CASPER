"""Safety and resilience engines for the CASPER coding harness.

The classes in this module are dependency-free and intentionally independent of
the model provider.  They can therefore protect interactive, headless, and test
runs through the same deterministic contracts.
"""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Callable, Mapping, Optional, TypeVar


# Engine 31: secret redaction -------------------------------------------------


@dataclass(frozen=True)
class RedactionResult:
    value: Any
    redactions: int
    categories: tuple[str, ...]


class SecretRedactor:
    """Redact common credentials from strings and nested observation payloads."""

    _SENSITIVE_KEY = re.compile(
        r"(?:api[_-]?key|access[_-]?token|auth(?:orization)?|bearer|client[_-]?secret|"
        r"password|passwd|private[_-]?key|refresh[_-]?token|secret)$",
        re.IGNORECASE,
    )
    _PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
        (
            "credential_assignment",
            re.compile(
                r"(?i)\b(api[_-]?key|access[_-]?token|client[_-]?secret|password|passwd|"
                r"refresh[_-]?token|secret)\s*([=:])\s*([^\s,;]+)"
            ),
        ),
        ("bearer", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{8,}={0,2}")),
        ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")),
        ("github_token", re.compile(r"\bgh[opusr]_[A-Za-z0-9]{20,}\b")),
        ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    )

    @staticmethod
    def _replacement(category: str) -> str:
        return f"<redacted:{category}>"

    def redact_text(self, text: str) -> RedactionResult:
        redacted = text
        count = 0
        categories: list[str] = []
        for category, pattern in self._PATTERNS:
            if category == "credential_assignment":
                def replace_assignment(match: re.Match[str]) -> str:
                    return f"{match.group(1)}{match.group(2)}{self._replacement(category)}"

                redacted, changes = pattern.subn(replace_assignment, redacted)
            else:
                redacted, changes = pattern.subn(self._replacement(category), redacted)
            if changes:
                count += changes
                categories.append(category)
        return RedactionResult(redacted, count, tuple(categories))

    def redact(self, value: Any) -> RedactionResult:
        categories: set[str] = set()
        count = 0

        def visit(item: Any, key: str = "") -> Any:
            nonlocal count
            if key and self._SENSITIVE_KEY.search(key):
                count += 1
                categories.add("sensitive_field")
                return self._replacement("sensitive_field")
            if isinstance(item, str):
                result = self.redact_text(item)
                count += result.redactions
                categories.update(result.categories)
                return result.value
            if isinstance(item, Mapping):
                return {str(k): visit(v, str(k)) for k, v in item.items()}
            if isinstance(item, list):
                return [visit(child) for child in item]
            if isinstance(item, tuple):
                return tuple(visit(child) for child in item)
            return item

        return RedactionResult(visit(value), count, tuple(sorted(categories)))


# Engine 32: advanced command risk analysis ----------------------------------


class CommandRisk(str, Enum):
    SAFE = "safe"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class CommandRiskFinding:
    code: str
    risk: CommandRisk
    summary: str
    evidence: str


@dataclass(frozen=True)
class CommandRiskAssessment:
    risk: CommandRisk
    score: int
    findings: tuple[CommandRiskFinding, ...]
    parsed_commands: tuple[tuple[str, ...], ...]
    recommendation: str

    @property
    def requires_approval(self) -> bool:
        return self.risk in {CommandRisk.MODERATE, CommandRisk.HIGH, CommandRisk.CRITICAL}


class CommandRiskAnalyzer:
    """Analyze shell text without executing it, including chained operations."""

    _ORDER = {
        CommandRisk.SAFE: 0,
        CommandRisk.LOW: 1,
        CommandRisk.MODERATE: 2,
        CommandRisk.HIGH: 3,
        CommandRisk.CRITICAL: 4,
    }
    _SCORES = {
        CommandRisk.SAFE: 0,
        CommandRisk.LOW: 10,
        CommandRisk.MODERATE: 35,
        CommandRisk.HIGH: 70,
        CommandRisk.CRITICAL: 100,
    }

    @staticmethod
    def _split(command: str) -> tuple[tuple[str, ...], ...]:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True
        tokens = list(lexer)
        groups: list[list[str]] = [[]]
        for token in tokens:
            if token in {";", "&&", "||", "|", "&"}:
                if groups[-1]:
                    groups.append([])
            else:
                groups[-1].append(token)
        return tuple(tuple(group) for group in groups if group)

    def analyze(self, command: str) -> CommandRiskAssessment:
        command = command.strip()
        if not command:
            finding = CommandRiskFinding("empty", CommandRisk.MODERATE, "Empty command.", "")
            return self._assessment((finding,), ())
        try:
            groups = self._split(command)
        except ValueError as exc:
            finding = CommandRiskFinding(
                "parse_error", CommandRisk.HIGH, "Shell syntax could not be parsed safely.", str(exc)
            )
            return self._assessment((finding,), ())

        lower = command.casefold()
        findings: list[CommandRiskFinding] = []
        if re.search(r"\brm\s+(?:-[a-z]*r[a-z]*f|-rf|-fr)\s+(?:/|~|\$home)(?:\s|$)", lower):
            findings.append(CommandRiskFinding(
                "destructive_root_delete", CommandRisk.CRITICAL,
                "Recursive deletion targets a root or home boundary.", command,
            ))
        if re.search(r"(?:curl|wget)\b[^|]*\|\s*(?:ba)?sh\b", lower):
            findings.append(CommandRiskFinding(
                "remote_code_pipe", CommandRisk.CRITICAL,
                "Remote content is piped directly to a shell.", command,
            ))
        if re.search(r"\bgit\s+(?:push\b.*(?:--force|-f)\b|reset\s+--hard\b|clean\s+-[a-z]*f)", lower):
            findings.append(CommandRiskFinding(
                "destructive_git", CommandRisk.HIGH,
                "The Git operation can discard or rewrite shared work.", command,
            ))
        if re.search(r"\b(?:sudo|su)\b", lower):
            findings.append(CommandRiskFinding(
                "privilege_escalation", CommandRisk.HIGH,
                "The command requests elevated privileges.", command,
            ))
        if re.search(r"\bchmod\s+(?:-r\s+)?777\b", lower):
            findings.append(CommandRiskFinding(
                "world_writable", CommandRisk.HIGH,
                "The command makes content world-writable.", command,
            ))
        if re.search(r"(?:^|\s)(?:>|>>)\s*(?:/etc/|/usr/|/bin/|/sbin/)", lower):
            findings.append(CommandRiskFinding(
                "system_redirect", CommandRisk.HIGH,
                "Shell output targets a protected system directory.", command,
            ))
        if re.search(r"\b(?:npm|pip|gem|cargo)\s+(?:install|add|uninstall|remove)\b", lower):
            findings.append(CommandRiskFinding(
                "dependency_mutation", CommandRisk.MODERATE,
                "The command changes installed dependencies.", command,
            ))
        if re.search(r"\b(?:mv|cp|rm|sed\s+-i|truncate|dd)\b", lower):
            findings.append(CommandRiskFinding(
                "filesystem_mutation", CommandRisk.MODERATE,
                "The command may modify or remove files.", command,
            ))
        if not findings:
            executables = {group[0].casefold() for group in groups if group}
            read_only = {"ls", "pwd", "cat", "head", "tail", "rg", "grep", "find", "git", "pytest"}
            risk = CommandRisk.SAFE if executables and executables <= read_only else CommandRisk.LOW
            findings.append(CommandRiskFinding(
                "bounded_command", risk, "No elevated-risk shell pattern was detected.", command,
            ))
        return self._assessment(tuple(findings), groups)

    def _assessment(
        self, findings: tuple[CommandRiskFinding, ...], groups: tuple[tuple[str, ...], ...]
    ) -> CommandRiskAssessment:
        highest = max((item.risk for item in findings), key=self._ORDER.__getitem__)
        score = max(self._SCORES[item.risk] for item in findings)
        recommendation = {
            CommandRisk.SAFE: "Proceed within the workspace boundary.",
            CommandRisk.LOW: "Proceed and capture the command output.",
            CommandRisk.MODERATE: "Review exact arguments and create a checkpoint before approval.",
            CommandRisk.HIGH: "Require explicit approval and a recovery plan.",
            CommandRisk.CRITICAL: "Deny by default; require an intentional operator override.",
        }[highest]
        return CommandRiskAssessment(highest, score, findings, groups, recommendation)


# Engine 33: resource budget enforcement -------------------------------------


@dataclass(frozen=True)
class BudgetLimits:
    max_steps: int = 24
    max_tool_calls: int = 100
    max_tokens: int = 200_000
    max_cost_usd: float = 25.0
    max_elapsed_seconds: float = 3_600.0


@dataclass(frozen=True)
class BudgetUsage:
    steps: int = 0
    tool_calls: int = 0
    tokens: int = 0
    cost_usd: float = 0.0

    def plus(self, other: "BudgetUsage") -> "BudgetUsage":
        return BudgetUsage(
            self.steps + other.steps,
            self.tool_calls + other.tool_calls,
            self.tokens + other.tokens,
            self.cost_usd + other.cost_usd,
        )


@dataclass(frozen=True)
class BudgetDecision:
    allowed: bool
    reason: str
    exceeded: tuple[str, ...]
    remaining: dict[str, float]
    stop_condition: str


class ResourceBudgetEnforcer:
    """Atomically reserve bounded run resources before work is performed."""

    def __init__(self, limits: BudgetLimits, *, clock: Callable[[], float] = time.monotonic) -> None:
        if min(limits.max_steps, limits.max_tool_calls, limits.max_tokens) < 0:
            raise ValueError("integer budget limits cannot be negative")
        if min(limits.max_cost_usd, limits.max_elapsed_seconds) < 0:
            raise ValueError("numeric budget limits cannot be negative")
        self.limits = limits
        self.usage = BudgetUsage()
        self._clock = clock
        self._started = clock()

    def check(self, requested: BudgetUsage = BudgetUsage()) -> BudgetDecision:
        candidate = self.usage.plus(requested)
        elapsed = max(0.0, self._clock() - self._started)
        values = {
            "steps": (candidate.steps, self.limits.max_steps),
            "tool_calls": (candidate.tool_calls, self.limits.max_tool_calls),
            "tokens": (candidate.tokens, self.limits.max_tokens),
            "cost_usd": (candidate.cost_usd, self.limits.max_cost_usd),
            "elapsed_seconds": (elapsed, self.limits.max_elapsed_seconds),
        }
        exceeded = tuple(name for name, (used, limit) in values.items() if used > limit)
        remaining = {name: max(0.0, float(limit) - float(used)) for name, (used, limit) in values.items()}
        if exceeded:
            return BudgetDecision(
                False,
                f"Resource budget would exceed: {', '.join(exceeded)}.",
                exceeded,
                remaining,
                "Stop this run or explicitly create a new budget before retrying.",
            )
        return BudgetDecision(True, "Resource reservation is within budget.", (), remaining, "")

    def reserve(self, requested: BudgetUsage) -> BudgetDecision:
        decision = self.check(requested)
        if decision.allowed:
            self.usage = self.usage.plus(requested)
        return decision


# Engine 34: circuit breaker --------------------------------------------------


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True)
class CircuitDecision:
    allowed: bool
    state: CircuitState
    reason: str
    retry_after_seconds: float


class CircuitBreaker:
    """Stop repeated provider/tool failures and probe recovery safely."""

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        half_open_successes: int = 1,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if failure_threshold < 1 or recovery_timeout < 0 or half_open_successes < 1:
            raise ValueError("circuit breaker limits must be positive")
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_successes = half_open_successes
        self._clock = clock
        self.state = CircuitState.CLOSED
        self.failures = 0
        self._successes = 0
        self._opened_at: Optional[float] = None
        self._probe_in_flight = False

    def allow(self) -> CircuitDecision:
        if self.state == CircuitState.OPEN:
            opened_at = self._opened_at if self._opened_at is not None else self._clock()
            elapsed = self._clock() - opened_at
            remaining = max(0.0, self.recovery_timeout - elapsed)
            if remaining > 0:
                return CircuitDecision(False, self.state, "Circuit is cooling down after failures.", remaining)
            self.state = CircuitState.HALF_OPEN
            self._probe_in_flight = False
        if self.state == CircuitState.HALF_OPEN:
            if self._probe_in_flight:
                return CircuitDecision(False, self.state, "A recovery probe is already running.", 0.0)
            self._probe_in_flight = True
            return CircuitDecision(True, self.state, "Allow one bounded recovery probe.", 0.0)
        return CircuitDecision(True, self.state, "Circuit is closed.", 0.0)

    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self._successes += 1
            self._probe_in_flight = False
            if self._successes >= self.half_open_successes:
                self.reset()
        else:
            self.failures = 0

    def record_failure(self) -> None:
        self._probe_in_flight = False
        self._successes = 0
        self.failures += 1
        if self.state == CircuitState.HALF_OPEN or self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self._opened_at = self._clock()

    def reset(self) -> None:
        self.state = CircuitState.CLOSED
        self.failures = 0
        self._successes = 0
        self._opened_at = None
        self._probe_in_flight = False


# Engine 35: retry policy -----------------------------------------------------


@dataclass(frozen=True)
class RetryDecision:
    retry: bool
    attempt: int
    delay_seconds: float
    reason: str
    stop_condition: str


T = TypeVar("T")


class RetryPolicy:
    """Bound transient retries with deterministic exponential backoff."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 0.25,
        max_delay: float = 5.0,
        retryable: tuple[type[BaseException], ...] = (TimeoutError, ConnectionError),
    ) -> None:
        if max_attempts < 1 or base_delay < 0 or max_delay < 0:
            raise ValueError("retry limits are invalid")
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.retryable = retryable

    def decide(self, attempt: int, error: BaseException) -> RetryDecision:
        if attempt < 1:
            raise ValueError("attempt numbering starts at one")
        if not isinstance(error, self.retryable):
            return RetryDecision(
                False, attempt, 0.0, f"{type(error).__name__} is not classified as transient.",
                "Stop and address the root cause before retrying.",
            )
        if attempt >= self.max_attempts:
            return RetryDecision(
                False, attempt, 0.0, "Retry attempt budget is exhausted.",
                f"Stop after {self.max_attempts} attempts and surface the last error.",
            )
        delay = min(self.max_delay, self.base_delay * (2 ** (attempt - 1)))
        return RetryDecision(True, attempt, delay, "Transient failure is eligible for retry.", "")

    def run(self, operation: Callable[[], T], *, sleep: Callable[[float], None] = time.sleep) -> T:
        attempt = 1
        while True:
            try:
                return operation()
            except BaseException as exc:
                decision = self.decide(attempt, exc)
                if not decision.retry:
                    raise
                sleep(decision.delay_seconds)
                attempt += 1


# Engine 36: tamper-evident audit chain --------------------------------------


@dataclass(frozen=True)
class AuditEntry:
    index: int
    timestamp: float
    event_type: str
    payload: dict[str, Any]
    previous_hash: str
    hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AuditVerification:
    valid: bool
    checked: int
    failure_index: Optional[int]
    reason: str


class TamperEvidentAuditChain:
    """Append canonical events whose hashes commit to the complete prior chain."""

    GENESIS_HASH = "0" * 64

    def __init__(self, entries: tuple[AuditEntry, ...] = ()) -> None:
        self._entries = list(entries)

    @staticmethod
    def _hash(index: int, timestamp: float, event_type: str, payload: Mapping[str, Any], previous: str) -> str:
        body = json.dumps(
            {
                "index": index,
                "timestamp": timestamp,
                "event_type": event_type,
                "payload": payload,
                "previous_hash": previous,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    @property
    def entries(self) -> tuple[AuditEntry, ...]:
        return tuple(self._entries)

    def append(self, event_type: str, payload: Mapping[str, Any], *, timestamp: Optional[float] = None) -> AuditEntry:
        if not event_type.strip():
            raise ValueError("audit event type cannot be empty")
        index = len(self._entries)
        previous = self._entries[-1].hash if self._entries else self.GENESIS_HASH
        created = time.time() if timestamp is None else float(timestamp)
        copied_payload = json.loads(json.dumps(dict(payload), default=str))
        digest = self._hash(index, created, event_type, copied_payload, previous)
        entry = AuditEntry(index, created, event_type, copied_payload, previous, digest)
        self._entries.append(entry)
        return entry

    def verify(self) -> AuditVerification:
        previous = self.GENESIS_HASH
        for expected_index, entry in enumerate(self._entries):
            if entry.index != expected_index:
                return AuditVerification(False, expected_index, expected_index, "Audit index is discontinuous.")
            if entry.previous_hash != previous:
                return AuditVerification(False, expected_index, expected_index, "Previous hash does not match.")
            expected_hash = self._hash(
                entry.index, entry.timestamp, entry.event_type, entry.payload, entry.previous_hash
            )
            if entry.hash != expected_hash:
                return AuditVerification(False, expected_index, expected_index, "Entry hash is invalid.")
            previous = entry.hash
        return AuditVerification(True, len(self._entries), None, "Audit chain is intact.")
