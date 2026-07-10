"""
Enhanced AI Command Interpreter for CASPER
Implements the comprehensive logic chains from the Claude Code Logic Plan
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from core.services.llm import llm_service


class CommandType(Enum):
    """Extended command types based on logic plan"""
    FILE_OPERATION = "file_operation"
    CODE_GENERATION = "code_generation"
    TESTING = "testing"
    DEBUGGING = "debugging"
    DOCUMENTATION = "documentation"
    SYSTEM_QUERY = "system_query"
    CONVERSATION = "conversation"
    GIT_OPERATION = "git_operation"
    PACKAGE_MANAGEMENT = "package_management"
    INITIALIZATION = "initialization"
    SEARCH_ANALYSIS = "search_analysis"
    MULTI_AGENT = "multi_agent"
    UNKNOWN = "unknown"


class ConfidenceLevel(Enum):
    """Confidence levels for command interpretation"""
    DIRECT_MATCH = 100  # Explicit command match
    HIGH = 80          # Partial match with clear intent
    MEDIUM = 60        # Natural language with probable intent
    LOW = 40           # Ambiguous, needs clarification
    UNCERTAIN = 20     # Multiple interpretations possible


class Priority(Enum):
    """Decision priority levels with timing constraints"""
    IMMEDIATE = "immediate"      # < 100ms
    QUICK = "quick"              # 100ms - 1s
    CONSIDERED = "considered"    # 1s - 5s
    COMPLEX = "complex"          # > 5s


class ErrorSeverity(Enum):
    """Error severity classification"""
    CRITICAL = "critical"    # Blocks all progress
    HIGH = "high"           # Blocks feature
    MEDIUM = "medium"       # Degraded function
    LOW = "low"            # Cosmetic/minor


@dataclass
class InterpretedCommand:
    """Enhanced command interpretation with confidence and priority"""
    command_type: CommandType
    action: str
    targets: List[Dict[str, Any]]
    context: Dict[str, Any]
    confidence: float
    confidence_level: ConfidenceLevel
    priority: Priority
    raw_input: str
    suggested_agent: str
    execution_strategy: str  # sequential, parallel, hybrid
    safety_checks: List[str] = field(default_factory=list)
    fallback_options: List[str] = field(default_factory=list)
    estimated_time_ms: int = 0


@dataclass
class ProjectContext:
    """Enhanced project context with multi-language support"""
    project_root: str
    project_type: Optional[str]
    languages: List[str]
    frameworks: List[str]
    package_managers: List[str]
    existing_files: List[str]
    recent_operations: List[Dict]
    git_status: Optional[Dict]
    dependencies: Dict[str, List]


class EnhancedCasperInterpreter:
    """
    Enhanced AI interpreter implementing comprehensive logic chains.
    This follows the complete decision framework from the logic plan.
    """

    def __init__(self):
        self.context_history: List[InterpretedCommand] = []
        self.project_context = self._load_comprehensive_context()
        self.error_patterns: List[Dict] = []
        self.user_preferences: Dict = {}
        self.decision_cache: Dict = {}
        self.start_time = time.time()

    def _load_comprehensive_context(self) -> ProjectContext:
        """Load comprehensive project context with multi-language detection"""
        root = Path(os.environ.get("CASPER_PROJECT_ROOT", Path.cwd()))

        context = ProjectContext(
            project_root=str(root),
            project_type=None,
            languages=[],
            frameworks=[],
            package_managers=[],
            existing_files=[],
            recent_operations=[],
            git_status=None,
            dependencies={}
        )

        # Detect languages and frameworks
        self._detect_languages(root, context)
        self._detect_frameworks(root, context)
        self._detect_package_managers(root, context)
        self._analyze_git_status(root, context)

        return context

    def _detect_languages(self, root: Path, context: ProjectContext):
        """Detect programming languages in project"""
        language_patterns = {
            "python": ["*.py", "requirements.txt", "pyproject.toml"],
            "javascript": ["*.js", "*.jsx", "package.json"],
            "typescript": ["*.ts", "*.tsx", "tsconfig.json"],
            "go": ["*.go", "go.mod"],
            "rust": ["*.rs", "Cargo.toml"],
            "java": ["*.java", "pom.xml", "build.gradle"],
            "ruby": ["*.rb", "Gemfile"],
        }

        for lang, patterns in language_patterns.items():
            for pattern in patterns:
                if list(root.glob(pattern)):
                    if lang not in context.languages:
                        context.languages.append(lang)
                    break

        # Set primary project type
        if context.languages:
            context.project_type = context.languages[0]

    def _detect_frameworks(self, root: Path, context: ProjectContext):
        """Detect frameworks used in project"""
        framework_files = {
            "react": ["package.json"],  # Check for react in dependencies
            "vue": ["vue.config.js", "nuxt.config.js"],
            "angular": ["angular.json"],
            "django": ["manage.py"],
            "flask": ["app.py", "application.py"],
            "fastapi": ["main.py"],
            "express": ["app.js", "server.js"],
            "nextjs": ["next.config.js"],
        }

        for framework, indicators in framework_files.items():
            for indicator in indicators:
                if (root / indicator).exists():
                    context.frameworks.append(framework)
                    break

    def _detect_package_managers(self, root: Path, context: ProjectContext):
        """Detect package managers with priority order"""
        manager_files = {
            "pnpm": "pnpm-lock.yaml",
            "yarn": "yarn.lock",
            "npm": "package-lock.json",
            "poetry": "poetry.lock",
            "pipenv": "Pipfile.lock",
            "pip": "requirements.txt",
            "cargo": "Cargo.lock",
            "go": "go.sum",
        }

        for manager, lockfile in manager_files.items():
            if (root / lockfile).exists():
                context.package_managers.append(manager)

    def _analyze_git_status(self, root: Path, context: ProjectContext):
        """Analyze git repository status"""
        git_dir = root / ".git"
        if git_dir.exists():
            context.git_status = {
                "initialized": True,
                "branch": "unknown",  # Would need git command to get actual
                "has_changes": False,
                "last_commit": None
            }

    async def interpret(self, user_input: str) -> InterpretedCommand:
        """
        Main interpretation method with comprehensive logic chains.
        Implements the decision framework from the logic plan.
        """

        # Phase 1: Input Classification
        classification = self._classify_input(user_input)

        # Phase 2: Confidence Scoring
        confidence_data = self._calculate_confidence(user_input, classification)

        # Phase 3: Context Evaluation
        context_enhanced = self._evaluate_context(user_input, classification)

        # Phase 4: Risk Assessment
        safety_checks = self._assess_risks(user_input, classification)

        # Phase 5: Build interpretation
        try:
            if confidence_data["level"] == ConfidenceLevel.DIRECT_MATCH:
                # Direct execution path
                return self._direct_interpretation(user_input, classification, confidence_data, safety_checks)
            elif confidence_data["level"] in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]:
                # AI-assisted interpretation
                return await self._ai_interpretation(user_input, classification, confidence_data, safety_checks)
            else:
                # Clarification needed
                return self._request_clarification(user_input, classification, confidence_data)

        except Exception as e:
            print(f"Interpretation failed: {e}")
            return self._fallback_interpretation(user_input, classification, safety_checks)

    def _classify_input(self, user_input: str) -> Dict:
        """Classify input according to logic plan patterns"""
        classification = {
            "type": None,
            "patterns_matched": [],
            "keywords": [],
            "structure": None
        }

        input_lower = user_input.lower()

        # Character analysis
        if user_input.startswith('/'):
            classification["type"] = "slash_command"
            classification["structure"] = "command"
        elif any(word in input_lower for word in ['init', 'initialize', 'setup']):
            classification["type"] = "initialization"
            classification["keywords"].append("init")
        elif any(word in input_lower for word in ['create', 'make', 'new', 'add', 'generate']):
            classification["type"] = "creation"
            classification["keywords"].append("create")
        elif any(word in input_lower for word in ['fix', 'debug', 'error', 'bug', 'issue']):
            classification["type"] = "debugging"
            classification["keywords"].append("fix")
        elif 'git' in input_lower or any(word in input_lower for word in ['commit', 'push', 'pull']):
            classification["type"] = "git_operation"
            classification["keywords"].append("git")
        elif any(word in input_lower for word in ['test', 'testing', 'tests']):
            classification["type"] = "testing"
            classification["keywords"].append("test")
        else:
            classification["type"] = "general"

        return classification

    def _calculate_confidence(self, user_input: str, classification: Dict) -> Dict:
        """Calculate confidence score based on input clarity"""
        confidence_data = {
            "score": 0.0,
            "level": ConfidenceLevel.UNCERTAIN,
            "reasons": []
        }

        # Direct command patterns (100% confidence)
        direct_patterns = [
            r'^create file \S+',
            r'^delete (file|folder) \S+',
            r'^run tests?$',
            r'^git commit',
            r'^npm install',
        ]

        for pattern in direct_patterns:
            if re.match(pattern, user_input.lower()):
                confidence_data["score"] = 100.0
                confidence_data["level"] = ConfidenceLevel.DIRECT_MATCH
                confidence_data["reasons"].append("Direct command match")
                return confidence_data

        # High confidence patterns (80%)
        if classification["type"] != "general" and len(classification["keywords"]) >= 1:
            confidence_data["score"] = 80.0
            confidence_data["level"] = ConfidenceLevel.HIGH
            confidence_data["reasons"].append("Clear intent with keywords")
            return confidence_data

        # Medium confidence (60%)
        if classification["keywords"]:
            confidence_data["score"] = 60.0
            confidence_data["level"] = ConfidenceLevel.MEDIUM
            confidence_data["reasons"].append("Natural language with identifiable intent")
            return confidence_data

        # Low confidence
        confidence_data["score"] = 40.0
        confidence_data["level"] = ConfidenceLevel.LOW
        confidence_data["reasons"].append("Ambiguous input")
        return confidence_data

    def _evaluate_context(self, user_input: str, classification: Dict) -> Dict:
        """Evaluate context for better interpretation"""
        context = {
            "current_directory": os.getcwd(),
            "recent_commands": self.context_history[-5:] if self.context_history else [],
            "project_info": self.project_context,
            "timestamp": datetime.now().isoformat(),
            "session_duration": time.time() - self.start_time
        }

        # Add specific context based on classification
        if classification["type"] == "creation":
            context["existing_structure"] = self._get_directory_structure()
        elif classification["type"] == "git_operation":
            context["git_status"] = self.project_context.git_status

        return context

    def _assess_risks(self, user_input: str, classification: Dict) -> List[str]:
        """Assess risks and required safety checks"""
        safety_checks = []

        if classification["type"] == "deletion":
            safety_checks.append("confirm_deletion")
            safety_checks.append("check_git_tracked")
            safety_checks.append("verify_backup_exists")

        if "rm -rf" in user_input or "sudo" in user_input:
            safety_checks.append("CRITICAL_BLOCK")
            safety_checks.append("require_explicit_confirmation")

        if classification["type"] == "git_operation":
            safety_checks.append("check_uncommitted_changes")
            safety_checks.append("verify_branch")

        if "production" in user_input.lower() or "prod" in user_input.lower():
            safety_checks.append("production_environment_warning")

        return safety_checks

    def _direct_interpretation(self, user_input: str, classification: Dict,
                              confidence_data: Dict, safety_checks: List[str]) -> InterpretedCommand:
        """Handle direct command interpretation"""

        # Map classification to command type
        type_mapping = {
            "initialization": CommandType.INITIALIZATION,
            "creation": CommandType.FILE_OPERATION,
            "debugging": CommandType.DEBUGGING,
            "testing": CommandType.TESTING,
            "deletion": CommandType.FILE_OPERATION,
            "git_operation": CommandType.GIT_OPERATION,
        }

        command_type = type_mapping.get(classification["type"], CommandType.UNKNOWN)

        # Determine action
        action = self._extract_action(user_input, classification)

        # Extract targets
        targets = self._extract_targets(user_input, classification)

        # Determine execution strategy
        if len(targets) > 3:
            execution_strategy = "parallel"
        else:
            execution_strategy = "sequential"

        # Select agent
        agent = self._select_agent(command_type, action)

        # Calculate priority
        priority = self._determine_priority(command_type, len(targets))

        return InterpretedCommand(
            command_type=command_type,
            action=action,
            targets=targets,
            context=self._evaluate_context(user_input, classification),
            confidence=confidence_data["score"],
            confidence_level=confidence_data["level"],
            priority=priority,
            raw_input=user_input,
            suggested_agent=agent,
            execution_strategy=execution_strategy,
            safety_checks=safety_checks,
            fallback_options=self._generate_fallbacks(command_type),
            estimated_time_ms=self._estimate_execution_time(command_type, len(targets))
        )

    async def _ai_interpretation(self, user_input: str, classification: Dict,
                                 confidence_data: Dict, safety_checks: List[str]) -> InterpretedCommand:
        """AI-powered interpretation for medium/high confidence cases"""

        prompt = self._build_enhanced_prompt(user_input, classification, confidence_data)

        try:
            response = await llm_service.complete(prompt=prompt, max_tokens=1000)

            if response:
                parsed = self._parse_ai_response(response, user_input)
                parsed.safety_checks = safety_checks
                parsed.confidence = confidence_data["score"]
                parsed.confidence_level = confidence_data["level"]
                return parsed
            else:
                return self._fallback_interpretation(user_input, classification, safety_checks)

        except Exception as e:
            print(f"AI interpretation failed: {e}")
            return self._fallback_interpretation(user_input, classification, safety_checks)

    def _build_enhanced_prompt(self, user_input: str, classification: Dict, confidence_data: Dict) -> str:
        """Build enhanced prompt with comprehensive context"""

        recent_context = ""
        if self.context_history:
            recent = self.context_history[-3:]
            recent_context = "Recent commands:\n"
            for cmd in recent:
                recent_context += f"- {cmd.action} ({cmd.command_type.value}): {cmd.raw_input[:50]}...\n"

        prompt = f"""
        You are the AI interpreter for CASPER, implementing comprehensive logic chains.

        Project Context:
        - Type: {self.project_context.project_type}
        - Languages: {', '.join(self.project_context.languages)}
        - Frameworks: {', '.join(self.project_context.frameworks)}
        - Package Managers: {', '.join(self.project_context.package_managers)}

        Classification Data:
        - Type: {classification['type']}
        - Keywords: {', '.join(classification['keywords'])}
        - Confidence: {confidence_data['score']}% ({confidence_data['level'].name})

        {recent_context}

        User Input: "{user_input}"

        Apply the comprehensive logic chains to determine:
        1. Command type (file_operation, code_generation, testing, etc.)
        2. Specific action with confidence scoring
        3. All targets with validation
        4. Execution strategy (sequential/parallel/hybrid)
        5. Required safety checks
        6. Suggested agent and fallback options
        7. Estimated execution time

        Consider:
        - Multi-language context switching if needed
        - Cascading failure risks
        - Multi-agent orchestration benefits
        - Error recovery strategies

        Return a JSON object with complete interpretation following the enhanced schema.
        Include priority level (immediate/quick/considered/complex) based on task complexity.
        """

        return prompt

    def _parse_ai_response(self, response: str, user_input: str) -> InterpretedCommand:
        """Parse enhanced AI response"""
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return self._fallback_interpretation(user_input, {}, [])

            data = json.loads(json_match.group())

            # Map to enums
            cmd_type = CommandType.UNKNOWN
            for ct in CommandType:
                if ct.value == data.get("command_type"):
                    cmd_type = ct
                    break

            priority = Priority.QUICK  # Default
            for p in Priority:
                if p.value == data.get("priority"):
                    priority = p
                    break

            return InterpretedCommand(
                command_type=cmd_type,
                action=data.get("action", "unknown"),
                targets=data.get("targets", []),
                context=data.get("context", {}),
                confidence=float(data.get("confidence", 50)),
                confidence_level=ConfidenceLevel.MEDIUM,
                priority=priority,
                raw_input=user_input,
                suggested_agent=data.get("suggested_agent", "worker"),
                execution_strategy=data.get("execution_strategy", "sequential"),
                safety_checks=data.get("safety_checks", []),
                fallback_options=data.get("fallback_options", []),
                estimated_time_ms=data.get("estimated_time_ms", 1000)
            )

        except Exception as e:
            print(f"Failed to parse AI response: {e}")
            return self._fallback_interpretation(user_input, {}, [])

    def _request_clarification(self, user_input: str, classification: Dict,
                              confidence_data: Dict) -> InterpretedCommand:
        """Request clarification for low confidence inputs"""

        possible_interpretations = self._generate_interpretations(user_input, classification)

        return InterpretedCommand(
            command_type=CommandType.UNKNOWN,
            action="clarification_needed",
            targets=[],
            context={
                "original_input": user_input,
                "possible_interpretations": possible_interpretations,
                "confidence_reasons": confidence_data["reasons"]
            },
            confidence=confidence_data["score"],
            confidence_level=confidence_data["level"],
            priority=Priority.IMMEDIATE,
            raw_input=user_input,
            suggested_agent="master",
            execution_strategy="interactive",
            safety_checks=[],
            fallback_options=possible_interpretations,
            estimated_time_ms=100
        )

    def _fallback_interpretation(self, user_input: str, classification: Dict,
                                 safety_checks: List[str]) -> InterpretedCommand:
        """Fallback interpretation with best-effort approach"""

        user_lower = user_input.lower()

        # Best effort command type detection
        if "file" in user_lower or "folder" in user_lower:
            cmd_type = CommandType.FILE_OPERATION
        elif "test" in user_lower:
            cmd_type = CommandType.TESTING
        elif "git" in user_lower:
            cmd_type = CommandType.GIT_OPERATION
        else:
            cmd_type = CommandType.CONVERSATION

        return InterpretedCommand(
            command_type=cmd_type,
            action="process",
            targets=[{"raw": user_input}],
            context={"fallback": True},
            confidence=30.0,
            confidence_level=ConfidenceLevel.UNCERTAIN,
            priority=Priority.QUICK,
            raw_input=user_input,
            suggested_agent="master",
            execution_strategy="sequential",
            safety_checks=safety_checks,
            fallback_options=["ask_user", "show_help"],
            estimated_time_ms=500
        )

    # Helper methods

    def _extract_action(self, user_input: str, classification: Dict) -> str:
        """Extract specific action from input"""
        action_keywords = {
            "create": ["create", "make", "new", "add", "generate"],
            "delete": ["delete", "remove", "rm", "destroy"],
            "modify": ["edit", "modify", "update", "change"],
            "run": ["run", "execute", "start", "launch"],
            "test": ["test", "check", "verify", "validate"],
            "debug": ["debug", "fix", "solve", "troubleshoot"],
            "commit": ["commit", "save", "push"],
        }

        input_lower = user_input.lower()
        for action, keywords in action_keywords.items():
            if any(keyword in input_lower for keyword in keywords):
                return action

        return "process"

    def _extract_targets(self, user_input: str, classification: Dict) -> List[Dict]:
        """Extract targets from user input"""
        targets = []

        # File/folder patterns - handle "named X" and "called X" formats
        # Match: "create folder named src" or "create file called test.py"
        file_pattern = r'(?:file|folder|directory)\s+(?:named|called)\s+([\w./]+)'
        matches = re.findall(file_pattern, user_input, re.IGNORECASE)

        for match in matches:
            targets.append({
                "type": "file" if "file" in user_input.lower() else "folder",
                "name": match,
                "path": match
            })

        # Fallback: simple "file X" or "folder X" pattern without named/called
        if not targets:
            simple_pattern = r'(?:file|folder|directory)\s+([\w./]+)'
            simple_matches = re.findall(simple_pattern, user_input, re.IGNORECASE)
            for match in simple_matches:
                if match.lower() not in ['named', 'called', 'file', 'folder', 'directory']:
                    targets.append({
                        "type": "file" if "file" in user_input.lower() else "folder",
                        "name": match,
                        "path": match
                    })

        # If no specific targets found, use raw input
        if not targets and classification["type"] != "general":
            targets.append({"raw": user_input})

        return targets

    def _select_agent(self, command_type: CommandType, action: str) -> str:
        """Select appropriate agent based on command type and action"""
        agent_mapping = {
            CommandType.FILE_OPERATION: "worker",
            CommandType.CODE_GENERATION: {
                "frontend": "frontend_prime",
                "backend": "backend_prime",
                "default": "worker"
            },
            CommandType.TESTING: "testing_prime",
            CommandType.DEBUGGING: "backend_prime",
            CommandType.GIT_OPERATION: "devops_prime",
            CommandType.PACKAGE_MANAGEMENT: "devops_prime",
            CommandType.INITIALIZATION: "master_prime",
            CommandType.MULTI_AGENT: "master_prime",
        }

        if isinstance(agent_mapping.get(command_type), dict):
            # Need to determine sub-type
            return agent_mapping[command_type].get("default", "worker")

        return agent_mapping.get(command_type, "master_prime")

    def _determine_priority(self, command_type: CommandType, target_count: int) -> Priority:
        """Determine execution priority based on command type and complexity"""
        if command_type in [CommandType.FILE_OPERATION, CommandType.SYSTEM_QUERY]:
            if target_count == 1:
                return Priority.IMMEDIATE
            else:
                return Priority.QUICK
        elif command_type in [CommandType.TESTING, CommandType.DEBUGGING]:
            return Priority.CONSIDERED
        elif command_type in [CommandType.CODE_GENERATION, CommandType.MULTI_AGENT]:
            return Priority.COMPLEX
        else:
            return Priority.QUICK

    def _generate_fallbacks(self, command_type: CommandType) -> List[str]:
        """Generate fallback options for command execution"""
        fallbacks = {
            CommandType.FILE_OPERATION: ["manual_creation", "template_selection"],
            CommandType.CODE_GENERATION: ["boilerplate", "example_code"],
            CommandType.TESTING: ["basic_test", "manual_verification"],
            CommandType.GIT_OPERATION: ["manual_git", "gui_client"],
        }

        return fallbacks.get(command_type, ["ask_user", "show_documentation"])

    def _estimate_execution_time(self, command_type: CommandType, target_count: int) -> int:
        """Estimate execution time in milliseconds"""
        base_times = {
            CommandType.FILE_OPERATION: 100,
            CommandType.CODE_GENERATION: 2000,
            CommandType.TESTING: 5000,
            CommandType.DEBUGGING: 3000,
            CommandType.GIT_OPERATION: 500,
            CommandType.PACKAGE_MANAGEMENT: 10000,
            CommandType.INITIALIZATION: 5000,
            CommandType.MULTI_AGENT: 10000,
        }

        base = base_times.get(command_type, 1000)
        return base * max(1, target_count)

    def _get_directory_structure(self) -> Dict:
        """Get current directory structure for context"""
        # Simplified - would implement full tree in production
        return {
            "current_dir": os.getcwd(),
            "subdirs": [],
            "files": []
        }

    def _generate_interpretations(self, user_input: str, classification: Dict) -> List[str]:
        """Generate possible interpretations for ambiguous input"""
        interpretations = []

        if "it" in user_input.lower():
            interpretations.append("Referring to the last modified file")
            interpretations.append("Referring to the current directory")
            interpretations.append("Referring to the last command output")

        if classification["type"] == "general":
            interpretations.append("Create a new file")
            interpretations.append("Run a command")
            interpretations.append("Search for something")

        return interpretations[:3]  # Limit to 3 options

    async def handle_cascading_failure(self, error: Exception, command: InterpretedCommand) -> Dict:
        """
        Handle cascading failures according to the comprehensive plan.
        Implements failure chain analysis and containment strategies.
        """
        failure_analysis = {
            "root_cause": str(error),
            "affected_components": [],
            "propagation_path": [],
            "containment_strategy": None,
            "recovery_plan": []
        }

        # Analyze failure chain
        if command.command_type == CommandType.MULTI_AGENT:
            failure_analysis["affected_components"] = command.targets
            failure_analysis["containment_strategy"] = "isolate_failed_agent"
            failure_analysis["recovery_plan"] = ["retry_with_single_agent", "fallback_to_sequential"]

        elif command.command_type in [CommandType.FILE_OPERATION, CommandType.CODE_GENERATION]:
            failure_analysis["containment_strategy"] = "rollback_changes"
            failure_analysis["recovery_plan"] = ["restore_backup", "manual_intervention"]

        # Log pattern for learning
        self.error_patterns.append({
            "timestamp": datetime.now().isoformat(),
            "command_type": command.command_type.value,
            "error": str(error),
            "recovery": failure_analysis["recovery_plan"]
        })

        return failure_analysis

    def update_user_preferences(self, command: InterpretedCommand, feedback: str):
        """Update user preferences based on feedback"""
        if feedback == "correct":
            # Increase confidence for similar patterns
            pattern_key = f"{command.command_type.value}_{command.action}"
            if pattern_key not in self.user_preferences:
                self.user_preferences[pattern_key] = {"success": 0, "failure": 0}
            self.user_preferences[pattern_key]["success"] += 1
        elif feedback == "incorrect":
            # Learn from mistake
            pattern_key = f"{command.command_type.value}_{command.action}"
            if pattern_key not in self.user_preferences:
                self.user_preferences[pattern_key] = {"success": 0, "failure": 0}
            self.user_preferences[pattern_key]["failure"] += 1

    def explain_interpretation(self, command: InterpretedCommand) -> str:
        """Generate detailed explanation of interpretation"""
        explanation = f"""
Command Interpretation:
- Type: {command.command_type.value}
- Action: {command.action}
- Confidence: {command.confidence:.0f}% ({command.confidence_level.name})
- Priority: {command.priority.value}
- Execution: {command.execution_strategy}
- Agent: {command.suggested_agent}
- Estimated Time: {command.estimated_time_ms}ms

Safety Checks: {', '.join(command.safety_checks) if command.safety_checks else 'None'}
Fallback Options: {', '.join(command.fallback_options) if command.fallback_options else 'None'}
"""

        if command.targets:
            explanation += f"\nTargets: {len(command.targets)} items"
            for target in command.targets[:3]:  # Show first 3
                explanation += f"\n  - {target}"

        return explanation.strip()


# Global enhanced interpreter instance
enhanced_interpreter = EnhancedCasperInterpreter()