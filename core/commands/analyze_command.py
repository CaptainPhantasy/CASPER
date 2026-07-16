"""
Transformed Analyze Command
Production-ready code analysis with ReAct reasoning and structured results.
Zero tolerance for print-only behavior - returns real analysis data.
"""

import os
import ast
from pathlib import Path
from typing import Any, Dict, List, Optional
from core.commands.base import BaseCommand, CommandResult
from core.commands.react_engine import ReActEngine
from datetime import datetime


class AnalyzeCommand(BaseCommand):
    """
    Transform the /analyze command to return structured analysis results.
    Performs real code analysis with metrics and insights.
    """

    def __init__(self):
        super().__init__(name="analyze")
        self.description = (
            "Analyze code, files, or project structure with detailed insights"
        )
        self.usage = "/analyze <target_path_or_description>"
        self.category = "Code Analysis"
        self.react_engine = ReActEngine()

    def _validate_input(self, args: str) -> bool:
        """Validate analyze command input"""
        return bool(args.strip())

    async def execute(self, args: str, context: Any = None) -> CommandResult:
        """
        Execute analysis with ReAct reasoning pattern.
        MUST return CommandResult with actual analysis data.
        """
        # Clear previous reasoning
        self.react_engine.clear_reasoning_chain()

        try:
            # REASON phase
            reasoning = self.react_engine.reason(
                f"Analyze target: {args}", {"context_available": context is not None}
            )

            # ACT phase - perform analysis
            action_result = self.react_engine.act(
                "Performing comprehensive analysis",
                {"target": args, "analysis_type": "multi-dimensional"},
            )

            # Determine analysis type and execute
            analysis_data = await self._perform_analysis(args)

            # OBSERVE phase
            if analysis_data["success"]:
                observation = self.react_engine.observe(
                    f"Analysis completed successfully with {len(analysis_data['results'])} findings",
                    analysis_data,
                )
            else:
                observation = self.react_engine.observe(
                    f"Analysis encountered issues: {analysis_data.get('error', 'Unknown error')}",
                    analysis_data,
                )

            return CommandResult(
                success=analysis_data["success"],
                output=analysis_data["summary"],
                data={
                    "target": args,
                    "analysis": analysis_data,
                    "reasoning_summary": self.react_engine.summarize_reasoning(),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                },
                error=analysis_data.get("error"),
                reasoning=self.react_engine.get_reasoning_chain(),
            )

        except Exception as e:
            # OBSERVE phase - execution error
            self.react_engine.observe(
                f"Analysis execution encountered error: {str(e)}",
                {"error": str(e), "target": args},
            )

            return CommandResult(
                success=False,
                output=f"Analysis error: {str(e)}",
                error=str(e),
                data={
                    "target": args,
                    "error_details": str(e),
                    "reasoning_summary": self.react_engine.summarize_reasoning(),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                },
                reasoning=self.react_engine.get_reasoning_chain(),
            )

    async def _perform_analysis(self, target: str) -> Dict[str, Any]:
        """
        Perform actual analysis based on target type.
        Returns real analysis data - not placeholders.
        """
        try:
            # Check if target is a file path
            if os.path.exists(target):
                return await self._analyze_file_or_directory(target)
            else:
                # Treat as description/concept analysis
                return await self._analyze_concept(target)

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": {},
                "summary": f"Analysis failed: {str(e)}",
            }

    async def _analyze_file_or_directory(self, path: str) -> Dict[str, Any]:
        """Analyze a file or directory structure"""
        path_obj = Path(path)

        if path_obj.is_file():
            return await self._analyze_file(path)
        elif path_obj.is_dir():
            return await self._analyze_directory(path)
        else:
            return {
                "success": False,
                "error": f"Path does not exist or is not accessible: {path}",
                "results": {},
                "summary": "Invalid path provided",
            }

    async def _analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a single file"""
        try:
            path_obj = Path(file_path)
            file_size = path_obj.stat().st_size
            file_ext = path_obj.suffix.lower()

            analysis_results = {
                "file_info": {
                    "name": path_obj.name,
                    "path": str(path_obj.absolute()),
                    "size_bytes": file_size,
                    "extension": file_ext,
                    "modified": datetime.fromtimestamp(
                        path_obj.stat().st_mtime
                    ).isoformat()
                    + "Z",
                }
            }

            # Analyze Python files
            if file_ext == ".py":
                analysis_results.update(await self._analyze_python_file(file_path))
            # Analyze text files
            elif file_ext in [".txt", ".md", ".json", ".yaml", ".yml", ".toml"]:
                analysis_results.update(await self._analyze_text_file(file_path))
            else:
                analysis_results["content_analysis"] = {
                    "type": "binary_or_unsupported",
                    "analyzable": False,
                }

            return {
                "success": True,
                "results": analysis_results,
                "summary": f"File analysis completed: {path_obj.name} ({file_size} bytes, {file_ext})",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": {},
                "summary": f"File analysis failed: {str(e)}",
            }

    async def _analyze_python_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze Python file structure and complexity"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse AST
            tree = ast.parse(content)

            # Count different elements
            functions = [
                node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
            ]
            classes = [
                node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
            ]
            imports = [
                node
                for node in ast.walk(tree)
                if isinstance(node, (ast.Import, ast.ImportFrom))
            ]

            # Calculate complexity metrics
            lines_of_code = len(
                [
                    line
                    for line in content.split("\n")
                    if line.strip() and not line.strip().startswith("#")
                ]
            )
            total_lines = len(content.split("\n"))

            return {
                "python_analysis": {
                    "functions": len(functions),
                    "classes": len(classes),
                    "imports": len(imports),
                    "lines_of_code": lines_of_code,
                    "total_lines": total_lines,
                    "complexity_score": min(len(functions) + len(classes) * 2, 100),
                    "function_names": [
                        f.name for f in functions[:10]
                    ],  # First 10 functions
                    "class_names": [c.name for c in classes[:10]],  # First 10 classes
                }
            }

        except Exception as e:
            return {"python_analysis": {"error": str(e), "analyzable": False}}

    async def _analyze_text_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze text-based files"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            words = content.split()
            lines = content.split("\n")

            return {
                "text_analysis": {
                    "word_count": len(words),
                    "line_count": len(lines),
                    "character_count": len(content),
                    "average_line_length": (
                        sum(len(line) for line in lines) / len(lines) if lines else 0
                    ),
                    "empty_lines": len([line for line in lines if not line.strip()]),
                    "max_line_length": max(len(line) for line in lines) if lines else 0,
                }
            }

        except Exception as e:
            return {"text_analysis": {"error": str(e), "analyzable": False}}

    async def _analyze_directory(self, dir_path: str) -> Dict[str, Any]:
        """Analyze directory structure"""
        try:
            path_obj = Path(dir_path)

            all_files = []
            directories = []
            file_extensions = {}

            for item in path_obj.rglob("*"):
                if item.is_file():
                    all_files.append(str(item.relative_to(path_obj)))
                    ext = item.suffix.lower()
                    file_extensions[ext] = file_extensions.get(ext, 0) + 1
                elif item.is_dir() and item != path_obj:
                    directories.append(str(item.relative_to(path_obj)))

            # Calculate total size
            total_size = sum(
                f.stat().st_size for f in path_obj.rglob("*") if f.is_file()
            )

            return {
                "success": True,
                "results": {
                    "directory_analysis": {
                        "total_files": len(all_files),
                        "total_directories": len(directories),
                        "total_size_bytes": total_size,
                        "file_extensions": file_extensions,
                        "recent_files": all_files[:20],  # First 20 files
                        "directory_depth": (
                            max(len(Path(d).parts) for d in directories)
                            if directories
                            else 1
                        ),
                    }
                },
                "summary": f"Directory analysis: {len(all_files)} files, {len(directories)} dirs, {total_size} bytes",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": {},
                "summary": f"Directory analysis failed: {str(e)}",
            }

    async def _analyze_concept(self, concept: str) -> Dict[str, Any]:
        """Analyze a concept or description"""
        try:
            # Basic concept analysis
            words = concept.lower().split()

            # Categorize the concept
            categories = []
            if any(
                word in words
                for word in ["code", "programming", "function", "class", "method"]
            ):
                categories.append("programming")
            if any(
                word in words for word in ["bug", "error", "issue", "problem", "fix"]
            ):
                categories.append("debugging")
            if any(
                word in words for word in ["test", "testing", "spec", "requirement"]
            ):
                categories.append("testing")
            if any(
                word in words
                for word in ["design", "architecture", "pattern", "structure"]
            ):
                categories.append("design")

            if not categories:
                categories = ["general"]

            return {
                "success": True,
                "results": {
                    "concept_analysis": {
                        "input": concept,
                        "word_count": len(words),
                        "categories": categories,
                        "complexity_indicators": [
                            w
                            for w in words
                            if w in ["complex", "difficult", "challenging", "advanced"]
                        ],
                        "action_words": [
                            w
                            for w in words
                            if w
                            in ["create", "build", "fix", "analyze", "test", "deploy"]
                        ],
                        "technical_terms": [
                            w
                            for w in words
                            if w
                            in [
                                "api",
                                "database",
                                "server",
                                "client",
                                "frontend",
                                "backend",
                            ]
                        ],
                    }
                },
                "summary": f"Concept analysis: {len(words)} words, categories: {', '.join(categories)}",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": {},
                "summary": f"Concept analysis failed: {str(e)}",
            }
