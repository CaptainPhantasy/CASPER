"""Task-level completion, retry, latency, token, and cost evaluation."""

from __future__ import annotations

import inspect
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Iterable, Optional

from .models import RunResult, RunStatus


ResultVerifier = Callable[[RunResult, list[dict[str, Any]]], Awaitable[bool] | bool]
RuntimeFactory = Callable[[], Any]


@dataclass(frozen=True)
class EvalCase:
    name: str
    prompt: str
    verifier: Optional[ResultVerifier] = None
    required_tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvalAttempt:
    case: str
    attempt: int
    passed: bool
    status: str
    elapsed_ms: float
    steps: int
    retries: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    tools: tuple[str, ...]
    error: str = ""


@dataclass
class BenchmarkReport:
    attempts: list[EvalAttempt] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        cases = sorted({item.case for item in self.attempts})
        first = {case: next(item for item in self.attempts if item.case == case) for case in cases}
        passed_any = {case: any(item.passed for item in self.attempts if item.case == case) for case in cases}
        successful = [item for item in self.attempts if item.passed]
        return {
            "cases": len(cases),
            "completion_rate": sum(passed_any.values()) / len(cases) if cases else 0.0,
            "pass_at_1": sum(item.passed for item in first.values()) / len(cases) if cases else 0.0,
            "pass_at_3": sum(passed_any.values()) / len(cases) if cases else 0.0,
            "retries_per_success": (
                sum(item.retries for item in successful) / len(successful) if successful else 0.0
            ),
            "cost_per_success_usd": (
                sum(item.estimated_cost_usd for item in self.attempts) / len(successful) if successful else 0.0
            ),
            "attempts": [vars(item) for item in self.attempts],
        }


class HarnessEvaluator:
    def __init__(
        self, runtime_factory: RuntimeFactory, *, max_attempts: int = 3,
        input_cost_per_million: float = 0.0, output_cost_per_million: float = 0.0,
    ) -> None:
        self.runtime_factory = runtime_factory
        self.max_attempts = max(1, min(max_attempts, 3))
        self.input_cost = input_cost_per_million / 1_000_000
        self.output_cost = output_cost_per_million / 1_000_000

    async def run(self, cases: Iterable[EvalCase]) -> BenchmarkReport:
        report = BenchmarkReport()
        for case in cases:
            for attempt_number in range(1, self.max_attempts + 1):
                runtime = self.runtime_factory()
                started = time.perf_counter()
                result = await runtime.run(case.prompt)
                event_dicts = [event.to_dict() for event in runtime.events]
                tools = tuple(
                    event.payload["call"]["name"] for event in runtime.events
                    if event.type == "tool.completed"
                )
                passed = result.status == RunStatus.COMPLETE and all(name in tools for name in case.required_tools)
                if passed and case.verifier:
                    verdict = case.verifier(result, event_dicts)
                    if inspect.isawaitable(verdict):
                        verdict = await verdict
                    passed = bool(verdict)
                input_tokens = int(result.usage.get("input_tokens", 0))
                output_tokens = int(result.usage.get("output_tokens", 0))
                report.attempts.append(EvalAttempt(
                    case.name, attempt_number, passed, result.status.value,
                    round((time.perf_counter() - started) * 1000, 2), result.steps,
                    attempt_number - 1, input_tokens, output_tokens,
                    round(input_tokens * self.input_cost + output_tokens * self.output_cost, 8),
                    tools, result.error,
                ))
                if passed:
                    break
        return report
