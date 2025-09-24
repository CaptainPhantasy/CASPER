"""
Context Reducer - R&D Framework REDUCE strategy.
Minimizes context to essential information only.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple


class ContextReducer:
    """
    Implements REDUCE strategy for context optimization.
    Focuses on minimizing token usage while preserving essential information.
    """

    # Maximum tokens for different context types
    TOKEN_LIMITS = {
        "handoff": 2000,
        "summary": 500,
        "pointer": 100,
        "decision": 200
    }

    @classmethod
    def reduce_code_context(cls, code: str, max_lines: int = 50) -> str:
        """
        Reduce code to essential structure.
        Keeps signatures, key logic, removes implementation details.
        """
        lines = code.split('\n')
        if len(lines) <= max_lines:
            return code

        reduced_lines = []
        in_function = False
        function_depth = 0

        for line in lines:
            stripped = line.strip()

            # Keep imports, class definitions, function signatures
            if (stripped.startswith(('import ', 'from ', 'class ', 'def ', '@'))
                or stripped.startswith(('async def', 'export ', 'interface '))):
                reduced_lines.append(line)
                if 'def ' in line:
                    in_function = True
                    function_depth = len(line) - len(line.lstrip())

            # Keep docstrings
            elif stripped.startswith(('"""', "'''")):
                reduced_lines.append(line)

            # Skip function body details but show structure
            elif in_function and len(line) - len(line.lstrip()) > function_depth:
                if len(reduced_lines) < max_lines:
                    # Add ellipsis to indicate omitted code
                    if not (reduced_lines and reduced_lines[-1].strip() == "..."):
                        reduced_lines.append(" " * (function_depth + 4) + "...")
            else:
                in_function = False
                if len(reduced_lines) < max_lines:
                    reduced_lines.append(line)

        return '\n'.join(reduced_lines[:max_lines])

    @classmethod
    def create_file_pointer(cls, file_path: str, key_elements: List[str]) -> Dict[str, str]:
        """
        Create a lightweight pointer to file location with key elements.
        """
        return {
            "type": "file_pointer",
            "path": file_path,
            "contains": key_elements[:5],  # Limit elements
            "instruction": f"Load {file_path} for details"
        }

    @classmethod
    def reduce_decisions(cls, decisions: List[Dict]) -> List[Dict]:
        """
        Reduce decisions to key outcomes only.
        """
        if len(decisions) <= 5:
            return decisions

        # Keep first 2 and last 3 decisions (most relevant)
        reduced = decisions[:2] + decisions[-3:]

        # Simplify each decision
        simplified = []
        for decision in reduced:
            simplified.append({
                "decision": decision.get("decision", "")[:100],  # Truncate
                "rationale": decision.get("rationale", "")[:50],  # Brief rationale
                "timestamp": decision.get("timestamp", "")
            })

        return simplified

    @classmethod
    def extract_key_artifacts(cls, artifacts: List[str]) -> List[str]:
        """
        Extract only the most important artifacts.
        """
        # Prioritize by file type importance
        priority_extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs']
        config_files = ['package.json', 'requirements.txt', 'Cargo.toml', '.env']

        prioritized = []

        # Add config files first
        for artifact in artifacts:
            if any(config in artifact for config in config_files):
                prioritized.append(artifact)
                if len(prioritized) >= 10:
                    return prioritized

        # Add priority extensions
        for ext in priority_extensions:
            for artifact in artifacts:
                if artifact.endswith(ext) and artifact not in prioritized:
                    prioritized.append(artifact)
                    if len(prioritized) >= 10:
                        return prioritized

        # Add remaining up to limit
        for artifact in artifacts:
            if artifact not in prioritized:
                prioritized.append(artifact)
                if len(prioritized) >= 10:
                    return prioritized

        return prioritized

    @classmethod
    def create_task_summary(cls, task: str, status: str, key_outcomes: List[str]) -> Dict:
        """
        Create ultra-compact task summary.
        """
        return {
            "task": task[:100],  # Truncate long tasks
            "status": status,
            "outcomes": key_outcomes[:3],  # Top 3 outcomes only
            "token_estimate": len(task.split()) + len(' '.join(key_outcomes).split())
        }

    @classmethod
    def reduce_error_context(cls, errors: List[str]) -> List[str]:
        """
        Reduce error messages to essential information.
        """
        reduced = []
        for error in errors[:5]:  # Max 5 errors
            # Extract key error info
            if 'Traceback' in error:
                # Get just the error type and message
                lines = error.split('\n')
                for line in lines:
                    if 'Error' in line or 'Exception' in line:
                        reduced.append(line.strip())
                        break
            else:
                # Truncate long errors
                reduced.append(error[:200])

        return reduced

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """
        Rough estimate of token count.
        Approximation: 1 token ~= 4 characters or 0.75 words
        """
        char_estimate = len(text) / 4
        word_estimate = len(text.split()) / 0.75
        return int((char_estimate + word_estimate) / 2)

    @classmethod
    def reduce_to_token_limit(cls, content: Dict, limit: int = 2000) -> Dict:
        """
        Reduce entire context to fit within token limit.
        """
        current_estimate = cls.estimate_tokens(str(content))

        if current_estimate <= limit:
            return content

        # Progressive reduction strategies
        reduced = content.copy()

        # Level 1: Reduce decisions
        if "decisions_made" in reduced:
            reduced["decisions_made"] = cls.reduce_decisions(reduced["decisions_made"])
            current_estimate = cls.estimate_tokens(str(reduced))
            if current_estimate <= limit:
                return reduced

        # Level 2: Reduce artifacts
        if "artifacts_created" in reduced:
            reduced["artifacts_created"] = cls.extract_key_artifacts(reduced["artifacts_created"])
            current_estimate = cls.estimate_tokens(str(reduced))
            if current_estimate <= limit:
                return reduced

        # Level 3: Convert to pointers
        if "structural_pointers" in reduced:
            # Keep only essential pointers
            pointers = reduced["structural_pointers"]
            if len(pointers) > 5:
                reduced["structural_pointers"] = dict(list(pointers.items())[:5])
            current_estimate = cls.estimate_tokens(str(reduced))
            if current_estimate <= limit:
                return reduced

        # Level 4: Aggressive truncation
        reduced["_truncated"] = True
        reduced["_original_size"] = current_estimate

        # Keep only absolutely essential fields
        essential = {
            "parent_task": reduced.get("parent_task", "")[:100],
            "next_actions": reduced.get("next_actions", [])[:3],
            "key_artifacts": reduced.get("artifacts_created", [])[:3],
            "_truncated": True
        }

        return essential

    @classmethod
    def create_handoff_summary(cls, from_agent: str, to_agent: str,
                               completed: str, next_task: str,
                               context: Dict) -> Dict:
        """
        Create efficient handoff summary between agents.
        """
        summary = {
            "handoff": {
                "from": from_agent,
                "to": to_agent,
                "completed": completed[:200],
                "next_task": next_task[:200]
            },
            "essential_context": {}
        }

        # Include only essential context items
        if "structural_pointers" in context:
            # Top 3 most relevant pointers
            pointers = context["structural_pointers"]
            summary["essential_context"]["key_locations"] = dict(list(pointers.items())[:3])

        if "artifacts_created" in context:
            # Most recent artifacts
            summary["essential_context"]["new_artifacts"] = context["artifacts_created"][-3:]

        if "decisions_made" in context:
            # Last major decision
            decisions = context["decisions_made"]
            if decisions:
                last_decision = decisions[-1]
                summary["essential_context"]["last_decision"] = {
                    "what": last_decision.get("decision", "")[:100],
                    "why": last_decision.get("rationale", "")[:50]
                }

        # Ensure within token limit
        return cls.reduce_to_token_limit(summary, cls.TOKEN_LIMITS["handoff"])