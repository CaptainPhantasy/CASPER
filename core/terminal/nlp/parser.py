"""
CASPER Prime Terminal NLP Parser - PHI Agent Component
Natural language processing for coding intent understanding.
PRODUCTION GRADE - Full implementation of IParser interface.
"""

import re
import asyncio
from typing import Dict, Any, List, Tuple, Optional
import logging
from datetime import datetime

from ..interfaces import (
    IParser,
    CodingIntent,
    CodingAction,
    ParsingError,
    MAX_COMPLETIONS,
    DEFAULT_TEMPERATURE,
)

logger = logging.getLogger(__name__)


class NLParser(IParser):
    """
    Production-grade natural language parser for CASPER Prime Terminal.
    Converts natural language into structured coding intents.
    """

    def __init__(self):
        """Initialize the NLP parser with patterns and models."""
        self.action_patterns = self._initialize_action_patterns()
        self.entity_patterns = self._initialize_entity_patterns()
        self.language_patterns = self._initialize_language_patterns()
        self.completion_cache: Dict[str, List[str]] = {}
        self.parsing_stats = {
            "total_parses": 0,
            "successful_parses": 0,
            "failed_parses": 0,
            "average_confidence": 0.0,
        }

    def _initialize_action_patterns(self) -> Dict[CodingAction, List[str]]:
        """Initialize regex patterns for different coding actions."""
        return {
            CodingAction.IMPLEMENT: [
                r"\b(?:implement|create|build|develop|write|code|make)\b.*?(?:function|class|method|feature|component)",
                r"\b(?:add|new)\b.*?(?:function|class|method|feature|component)",
                r"\b(?:generate|produce)\b.*?(?:code|implementation)",
                r"\bimplement\b",
                r"\bcreate\b.*?\bclass\b",
                r"\bwrite\b.*?\bfunction\b",
            ],
            CodingAction.MODIFY: [
                r"\b(?:modify|change|update|edit|alter|revise)\b",
                r"\b(?:fix|correct|adjust)\b",
                r"\b(?:refactor|restructure)\b",
                r"\bmodify\b.*?\b(?:function|class|method|variable)\b",
                r"\bchange\b.*?\bto\b",
                r"\bupdate\b.*?\b(?:with|to)\b",
            ],
            CodingAction.DEBUG: [
                r"\b(?:debug|fix|solve|troubleshoot)\b.*?\b(?:bug|error|issue|problem)",
                r"\b(?:find|identify|locate)\b.*?\b(?:bug|error|issue|problem)",
                r"\b(?:why|what).*?(?:not working|broken|failing|error)",
                r"\berror\b.*?\bin\b",
                r"\bfix\b.*?\b(?:bug|issue|error)",
                r"\bdebug\b",
            ],
            CodingAction.TEST: [
                r"\b(?:test|check|verify|validate)\b",
                r"\b(?:run|execute)\b.*?\b(?:test|tests)\b",
                r"\bwrite\b.*?\b(?:test|tests)\b",
                r"\bunit test\b",
                r"\btest case\b",
                r"\btesting\b",
            ],
            CodingAction.EXPLAIN: [
                r"\b(?:explain|describe|tell|show).*?(?:how|what|why)",
                r"\bwhat\b.*?\b(?:does|is)\b",
                r"\bhow\b.*?\b(?:does|do|works?)\b",
                r"\bexplain\b",
                r"\bdocument\b",
                r"\bwhat is\b",
            ],
            CodingAction.REVIEW: [
                r"\b(?:review|check|examine|inspect|analyze)\b.*?\b(?:code|implementation)",
                r"\bcode review\b",
                r"\blook at\b.*?\bcode\b",
                r"\breview\b",
                r"\bcheck\b.*?\b(?:quality|style|standards)\b",
            ],
            CodingAction.REFACTOR: [
                r"\b(?:refactor|restructure|reorganize|improve)\b",
                r"\bclean up\b",
                r"\boptimize\b.*?\b(?:structure|design|architecture)\b",
                r"\brefactor\b",
                r"\breorganize\b",
                r"\bimprove\b.*?\b(?:structure|design)\b",
            ],
            CodingAction.OPTIMIZE: [
                r"\b(?:optimize|improve|enhance)\b.*?\b(?:performance|speed|efficiency)",
                r"\bmake\b.*?\b(?:faster|better|more efficient)\b",
                r"\boptimize\b",
                r"\bperformance\b",
                r"\bspeed up\b",
            ],
        }

    def _initialize_entity_patterns(self) -> Dict[str, str]:
        """Initialize patterns for entity extraction."""
        return {
            "file": r"\b[\w\-\.]+\.(?:py|js|ts|jsx|tsx|java|cpp|c|h|css|html|json|yaml|yml|md|txt|sql)\b",
            "function": r"\bdef\s+(\w+)|function\s+(\w+)|\b(\w+)\s*\(",
            "class": r"\bclass\s+(\w+)|interface\s+(\w+)|struct\s+(\w+)",
            "variable": r"\b(?:var|let|const|val)\s+(\w+)|(\w+)\s*=",
            "method": r"\.(\w+)\s*\(",
            "module": r"\bimport\s+(\w+)|from\s+(\w+)\s+import",
            "path": r'[\'"]([\/\w\-\.]+)[\'"]',
            "url": r"https?://[^\s]+",
            "package": r"@[\w\/\-]+|\b[\w\-]+(?:==|>=|<=|>|<)\d+[\.\d]*",
        }

    def _initialize_language_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for programming language detection."""
        return {
            "python": [
                r"\bdef\s+\w+\s*\(",
                r"\bclass\s+\w+\s*:",
                r"\bimport\s+\w+",
                r"\bfrom\s+\w+\s+import",
                r'\bif\s+__name__\s*==\s*[\'"]__main__[\'"]',
                r"\bprint\s*\(",
                r"\.py\b",
            ],
            "javascript": [
                r"\bfunction\s+\w+\s*\(",
                r"\bconst\s+\w+\s*=",
                r"\blet\s+\w+\s*=",
                r"\bvar\s+\w+\s*=",
                r"\.js\b",
                r"=>",
                r"\bconsole\.log\s*\(",
            ],
            "typescript": [
                r":\s*\w+\s*[=;]",
                r"\binterface\s+\w+",
                r"\btype\s+\w+\s*=",
                r"\.ts\b",
                r"\.tsx\b",
                r"\bas\s+\w+",
            ],
            "java": [
                r"\bpublic\s+class\s+\w+",
                r"\bpublic\s+static\s+void\s+main",
                r"\.java\b",
                r"\bSystem\.out\.println\s*\(",
                r"\bprivate\s+\w+\s+\w+",
                r"\bpublic\s+\w+\s+\w+\s*\(",
            ],
            "cpp": [
                r"#include\s*<\w+>",
                r"\bstd::\w+",
                r"\.cpp\b",
                r"\.hpp\b",
                r"\bint\s+main\s*\(",
                r"\bcout\s*<<",
            ],
            "sql": [
                r"\bSELECT\b",
                r"\bFROM\b",
                r"\bWHERE\b",
                r"\bINSERT\s+INTO\b",
                r"\bUPDATE\b",
                r"\bDELETE\s+FROM\b",
                r"\.sql\b",
            ],
        }

    async def parse_input(self, user_input: str) -> CodingIntent:
        """Parse natural language input into structured coding intent."""
        try:
            self.parsing_stats["total_parses"] += 1

            # Clean and normalize input
            normalized_input = self._normalize_input(user_input)

            # Detect coding action
            action, action_confidence = await self._detect_action(normalized_input)

            # Extract targets (files, functions, classes, etc.)
            targets = await self._extract_targets(normalized_input)

            # Determine scope
            scope = await self._determine_scope(normalized_input, targets)

            # Extract required context
            context_required = await self._extract_context_requirements(
                normalized_input, action
            )

            # Calculate overall confidence
            confidence = await self._calculate_confidence(
                action_confidence, targets, scope, normalized_input
            )

            # Create coding intent
            intent = CodingIntent(
                action=action,
                targets=targets,
                scope=scope,
                original_request=user_input,
                confidence=confidence,
                context_required=context_required,
            )

            self.parsing_stats["successful_parses"] += 1
            self.parsing_stats["average_confidence"] = (
                self.parsing_stats["average_confidence"]
                * (self.parsing_stats["successful_parses"] - 1)
                + confidence
            ) / self.parsing_stats["successful_parses"]

            logger.debug(
                f"Parsed intent: {action.value} with confidence {confidence:.2f}"
            )
            return intent

        except Exception as e:
            self.parsing_stats["failed_parses"] += 1
            logger.error(f"Failed to parse input '{user_input}': {e}")
            raise ParsingError(f"Failed to parse input: {e}")

    def _normalize_input(self, input_text: str) -> str:
        """Normalize input text for better parsing."""
        # Convert to lowercase for pattern matching
        normalized = input_text.lower().strip()

        # Remove extra whitespace
        normalized = re.sub(r"\s+", " ", normalized)

        # Handle common contractions
        contractions = {
            "won't": "will not",
            "can't": "cannot",
            "n't": " not",
            "'ll": " will",
            "'ve": " have",
            "'re": " are",
            "'d": " would",
        }

        for contraction, expansion in contractions.items():
            normalized = normalized.replace(contraction, expansion)

        return normalized

    async def _detect_action(self, normalized_input: str) -> Tuple[CodingAction, float]:
        """Detect the coding action with confidence score."""
        action_scores = {}

        for action, patterns in self.action_patterns.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, normalized_input, re.IGNORECASE)
                if matches:
                    score += len(matches) * (1.0 / len(patterns))

            if score > 0:
                action_scores[action] = score

        if not action_scores:
            # Default to EXPLAIN if no clear action is detected
            return CodingAction.EXPLAIN, 0.3

        # Get the action with highest score
        best_action = max(action_scores, key=action_scores.get)
        confidence = min(action_scores[best_action], 1.0)

        return best_action, confidence

    async def _extract_targets(self, normalized_input: str) -> List[str]:
        """Extract target entities from the input."""
        targets = []

        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, normalized_input, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    # Handle grouped matches
                    target = next((m for m in match if m), None)
                else:
                    target = match

                if target and target not in targets:
                    targets.append(target)

        # If no specific targets found, try to extract from general context
        if not targets:
            # Look for quoted strings
            quoted = re.findall(r'[\'"]([^\'"]*)[\'"]', normalized_input)
            targets.extend(quoted)

            # Look for capitalized words (potential class/module names)
            capitalized = re.findall(r"\b[A-Z]\w+\b", normalized_input)
            targets.extend(capitalized[:3])  # Limit to avoid noise

        return targets[:10] if targets else ["current_context"]  # Limit targets

    async def _determine_scope(self, normalized_input: str, targets: List[str]) -> str:
        """Determine the scope of the coding operation."""
        scope_indicators = {
            "project": ["project", "entire", "whole", "all files", "codebase"],
            "file": ["file", "module", "document"],
            "class": ["class", "object", "type"],
            "function": ["function", "method", "procedure", "def"],
            "line": ["line", "statement", "expression"],
        }

        for scope, indicators in scope_indicators.items():
            if any(indicator in normalized_input for indicator in indicators):
                return scope

        # Infer scope from targets
        if any(
            target.endswith((".py", ".js", ".ts", ".java", ".cpp"))
            for target in targets
        ):
            return "file"
        elif any("def " in target or "function" in target for target in targets):
            return "function"
        elif any("class" in target.lower() for target in targets):
            return "class"

        return "function"  # Default scope

    async def _extract_context_requirements(
        self, normalized_input: str, action: CodingAction
    ) -> List[str]:
        """Extract what context is required for this operation."""
        context_requirements = []

        # Action-specific context requirements
        action_contexts = {
            CodingAction.IMPLEMENT: ["requirements", "specifications", "interfaces"],
            CodingAction.MODIFY: ["current_code", "dependencies"],
            CodingAction.DEBUG: ["error_logs", "stack_trace", "current_code"],
            CodingAction.TEST: ["code_to_test", "test_framework"],
            CodingAction.EXPLAIN: ["code_to_explain", "documentation"],
            CodingAction.REVIEW: ["code_to_review", "coding_standards"],
            CodingAction.REFACTOR: ["current_code", "design_goals"],
            CodingAction.OPTIMIZE: ["current_code", "performance_metrics"],
        }

        context_requirements.extend(action_contexts.get(action, []))

        # Extract specific context mentions
        context_patterns = {
            "database": r"\b(?:database|db|sql|table|query)\b",
            "api": r"\b(?:api|endpoint|rest|http|request|response)\b",
            "frontend": r"\b(?:frontend|ui|interface|react|vue|angular)\b",
            "backend": r"\b(?:backend|server|service|controller)\b",
            "config": r"\b(?:config|configuration|settings|environment)\b",
        }

        for context_type, pattern in context_patterns.items():
            if re.search(pattern, normalized_input, re.IGNORECASE):
                context_requirements.append(context_type)

        return list(set(context_requirements))  # Remove duplicates

    async def _calculate_confidence(
        self,
        action_confidence: float,
        targets: List[str],
        scope: str,
        normalized_input: str,
    ) -> float:
        """Calculate overall confidence in the parsing result."""
        confidence_factors = [action_confidence]

        # Target clarity factor
        if targets and targets != ["current_context"]:
            target_factor = min(
                len(targets) / 3.0, 1.0
            )  # More targets = clearer intent
            confidence_factors.append(target_factor)
        else:
            confidence_factors.append(0.5)  # Moderate confidence for general context

        # Input length factor (longer inputs often have clearer intent)
        length_factor = min(len(normalized_input.split()) / 10.0, 1.0)
        confidence_factors.append(length_factor)

        # Scope specificity factor
        scope_factors = {
            "line": 1.0,
            "function": 0.9,
            "class": 0.8,
            "file": 0.7,
            "project": 0.6,
        }
        confidence_factors.append(scope_factors.get(scope, 0.5))

        # Calculate weighted average
        return sum(confidence_factors) / len(confidence_factors)

    async def extract_entities(self, text: str) -> List[Tuple[str, str]]:
        """Extract entities (name, type) from text."""
        entities = []

        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    entity_name = next((m for m in match if m), None)
                else:
                    entity_name = match

                if entity_name:
                    entities.append((entity_name, entity_type))

        return entities

    async def suggest_completion(
        self, partial: str, context: Dict[str, Any]
    ) -> List[str]:
        """Suggest completions for partial input based on context."""
        try:
            # Check cache first
            cache_key = f"{partial}:{hash(str(context))}"
            if cache_key in self.completion_cache:
                return self.completion_cache[cache_key]

            suggestions = []

            # Action-based completions
            if len(partial.split()) <= 2:  # Early in the input
                action_suggestions = await self._get_action_completions(partial)
                suggestions.extend(action_suggestions)

            # Context-based completions
            context_suggestions = await self._get_context_completions(partial, context)
            suggestions.extend(context_suggestions)

            # Pattern-based completions
            pattern_suggestions = await self._get_pattern_completions(partial)
            suggestions.extend(pattern_suggestions)

            # Deduplicate and limit
            suggestions = list(
                dict.fromkeys(suggestions)
            )  # Remove duplicates while preserving order
            suggestions = suggestions[:MAX_COMPLETIONS]

            # Cache the result
            self.completion_cache[cache_key] = suggestions

            return suggestions

        except Exception as e:
            logger.error(f"Failed to generate completions: {e}")
            return []

    async def _get_action_completions(self, partial: str) -> List[str]:
        """Get action-based completions."""
        action_starters = {
            "imp": ["implement", "import"],
            "cre": ["create"],
            "mod": ["modify"],
            "fix": ["fix", "debug"],
            "test": ["test"],
            "exp": ["explain"],
            "rev": ["review"],
            "ref": ["refactor"],
            "opt": ["optimize"],
            "add": ["add"],
            "del": ["delete"],
            "upd": ["update"],
        }

        suggestions = []
        partial_lower = partial.lower()

        for prefix, actions in action_starters.items():
            if partial_lower.startswith(prefix):
                suggestions.extend([f"{action} " for action in actions])

        return suggestions

    async def _get_context_completions(
        self, partial: str, context: Dict[str, Any]
    ) -> List[str]:
        """Get context-based completions."""
        suggestions = []

        # File-based completions
        if "files_modified" in context and context["files_modified"]:
            for file_path in context["files_modified"][:5]:  # Limit to recent files
                file_name = file_path.split("/")[-1]
                suggestions.append(f"modify {file_name}")
                suggestions.append(f"explain {file_name}")
                suggestions.append(f"review {file_name}")

        # Recent history completions
        if "recent_history" in context:
            for interaction in context["recent_history"][-3:]:  # Last few interactions
                user_input = interaction.get("user_input", "")
                if user_input and user_input != partial:
                    suggestions.append(user_input)

        return suggestions

    async def _get_pattern_completions(self, partial: str) -> List[str]:
        """Get pattern-based completions."""
        common_patterns = [
            "implement function",
            "create class",
            "modify method",
            "fix bug in",
            "test the",
            "explain how",
            "review code",
            "refactor this",
            "optimize performance",
            "add feature",
            "debug error",
            "write test for",
        ]

        suggestions = []
        partial_lower = partial.lower()

        for pattern in common_patterns:
            if pattern.startswith(partial_lower):
                suggestions.append(pattern)

        return suggestions

    async def detect_language(self, code_snippet: str) -> str:
        """Detect programming language from code snippet."""
        try:
            language_scores = {}

            for language, patterns in self.language_patterns.items():
                score = 0
                for pattern in patterns:
                    matches = len(
                        re.findall(pattern, code_snippet, re.IGNORECASE | re.MULTILINE)
                    )
                    score += matches

                if score > 0:
                    language_scores[language] = score

            if not language_scores:
                return "text"  # Default to text if no language detected

            # Return language with highest score
            detected_language = max(language_scores, key=language_scores.get)
            logger.debug(f"Detected language: {detected_language}")

            return detected_language

        except Exception as e:
            logger.error(f"Failed to detect language: {e}")
            return "text"
