"""Canonical CASPER coding-harness API."""

from .agents import AgentProfile, AgentProfileRegistry
from .cancellation import CancellationError, CancellationToken
from .commands import HARNESS_COMMANDS, HarnessCommandSpec, command_index, command_palette
from .context import ContextPack, IndexedFile, RepositoryContext
from .dependencies import DependencyEdge, DependencyGraph
from .diagnostics import Diagnostic, DiagnosticParser
from .health import (
    HealthCheckResult, HealthDiagnostics, HealthReport, HealthStatus,
)
from .evals import BenchmarkReport, EvalAttempt, EvalCase, HarnessEvaluator
from .extensions import ExtensionRegistry, ExtensionSpec
from .hooks import (
    HookContext, HookDispatch, HookExecution, HookFailure, HookRegistration,
    LifecycleEvent, LifecycleHooks, default_hook_paths,
)
from .jobs import BackgroundJobSupervisor, JobRecord, JobStatus
from .impact import ChangeImpactAnalyzer, ImpactReport
from .mcp import MCPServerConfig, MCPServerRegistry, MCPTransport
from .interaction import (
    CommandPalette, ContentCache, DiffPreview, DiffResult, DoctorCheck, Intent,
    ModelProfile, ModelRouter, NaturalLanguageIntentRouter, OnboardingDoctor,
    PatchConflictDetector, SessionBranch, SessionBranchManager, SessionBundle,
    SlashCommand, SlashCommandRegistry,
)
from .models import (
    ModelTurn, ObservationStatus, RunEvent, RunResult, RunState, RunStatus,
    ToolCall, ToolObservation, ToolSpec,
)
from .operations import (
    ArtifactRecord, ArtifactRegistry, ArtifactVerification, ConfigLayer,
    ConfigResolution, LayeredConfiguration, MetricSnapshot, SpanRecord, SpanStatus,
    TelemetryCollector, WorkspaceTrustDecision, WorkspaceTrustLevel,
    WorkspaceTrustManager, WorkspaceTrustProfile,
)
from .plans import PlanStatus, PlanStep, PlanTracker
from .policy import PermissionMode, PolicyDecision, PolicyDisposition, PolicyEngine
from .providers import (
    AnthropicToolProvider, CallableProvider, HarnessProvider, OpenAIToolProvider,
    ProviderChain, TextCompletionProvider, create_default_provider,
    normalize_anthropic_response, normalize_gemini_response, normalize_openai_response,
)
from .registry import ToolRegistry
from .review import CodeReviewSentinel, ReviewExecution, ReviewInput, ReviewValidationError
from .runtime import HarnessRuntime
from .safety import (
    AuditEntry, AuditVerification, BudgetDecision, BudgetLimits, BudgetUsage,
    CircuitBreaker, CircuitDecision, CircuitState, CommandRisk,
    CommandRiskAnalyzer, CommandRiskAssessment, CommandRiskFinding,
    RedactionResult, ResourceBudgetEnforcer, RetryDecision, RetryPolicy,
    SecretRedactor, TamperEvidentAuditChain,
)
from .scheduler import TaskDAGScheduler, TaskNode, TaskResult, TaskStatus
from .schema import JSONSchemaValidator, ValidationIssue, ValidationResult
from .search import RepositorySearch, SearchHit
from .skills import SkillDiscovery, SkillDiscoveryResult, SkillMetadata, default_skill_roots
from .store import RunStore
from .symbols import SymbolIndex, SymbolRecord
from .test_selection import TargetedTestSelector, TestSelection
from .prompts import PromptLibrary, PromptTemplate
from .watcher import FileChange, FileChangeDetector, FileState
from .worktrees import WorktreeLease, WorktreePlan, WorktreePlanner
from .workspace import WorkspaceChange, WorkspaceEngine

__all__ = [
    "AgentProfile", "AgentProfileRegistry", "AnthropicToolProvider", "ArtifactRecord",
    "ArtifactRegistry", "ArtifactVerification", "AuditEntry", "AuditVerification", "BackgroundJobSupervisor",
    "BudgetDecision", "BudgetLimits", "BudgetUsage", "CodeReviewSentinel",
    "BenchmarkReport", "CallableProvider", "CancellationError", "CancellationToken", "ContextPack",
    "ChangeImpactAnalyzer", "CircuitBreaker", "CircuitDecision", "CircuitState", "CommandRisk",
    "CommandRiskAnalyzer", "CommandRiskAssessment", "CommandRiskFinding", "ConfigLayer",
    "ConfigResolution", "DependencyEdge", "DependencyGraph", "Diagnostic", "DiagnosticParser",
    "EvalAttempt", "EvalCase", "ExtensionRegistry", "ExtensionSpec", "FileChange",
    "FileChangeDetector", "FileState",
    "HARNESS_COMMANDS", "HarnessCommandSpec", "HealthCheckResult", "HealthDiagnostics", "HealthReport", "HealthStatus",
    "HarnessEvaluator", "HarnessProvider", "HarnessRuntime", "ImpactReport", "IndexedFile",
    "JSONSchemaValidator", "LayeredConfiguration", "MetricSnapshot", "ModelTurn",
    "HookContext", "HookDispatch", "HookExecution", "HookFailure", "HookRegistration",
    "JobRecord", "JobStatus", "LifecycleEvent",
    "LifecycleHooks", "MCPServerConfig", "MCPServerRegistry", "MCPTransport",
    "ObservationStatus", "PermissionMode", "PolicyDecision", "PolicyDisposition", "ProviderChain",
    "PolicyEngine", "RepositoryContext", "RunEvent", "RunResult", "RunState", "RunStatus",
    "OpenAIToolProvider", "PlanStatus", "PlanStep", "PlanTracker", "PromptLibrary",
    "PromptTemplate", "RedactionResult", "RepositorySearch", "ResourceBudgetEnforcer",
    "ReviewExecution", "ReviewInput", "ReviewValidationError",
    "RetryDecision", "RetryPolicy", "RunStore", "SearchHit", "SecretRedactor", "SkillDiscovery",
    "SkillDiscoveryResult", "SkillMetadata", "SymbolIndex", "SymbolRecord", "TamperEvidentAuditChain",
    "default_hook_paths", "default_skill_roots",
    "TaskDAGScheduler", "TaskNode", "TaskResult", "TaskStatus", "TextCompletionProvider",
    "SpanRecord", "SpanStatus", "TargetedTestSelector", "TelemetryCollector", "TestSelection",
    "ToolCall", "ToolObservation", "ToolRegistry",
    "ToolSpec", "WorkspaceChange", "WorkspaceEngine", "normalize_anthropic_response",
    "ValidationIssue", "ValidationResult", "WorkspaceTrustDecision", "WorkspaceTrustLevel",
    "WorkspaceTrustManager", "WorkspaceTrustProfile", "WorktreeLease", "WorktreePlan", "WorktreePlanner",
    "command_index", "command_palette", "create_default_provider", "normalize_gemini_response", "normalize_openai_response",
    "CommandPalette", "ContentCache", "DiffPreview", "DiffResult", "DoctorCheck", "Intent",
    "ModelProfile", "ModelRouter", "NaturalLanguageIntentRouter", "OnboardingDoctor",
    "PatchConflictDetector", "SessionBranch", "SessionBranchManager", "SessionBundle",
    "SlashCommand", "SlashCommandRegistry",
]
