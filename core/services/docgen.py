"""
CASPER Documentation Generation Service
Real implementation of documentation generation features.
"""

import os
import re
import ast
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.services.llm import llm_service

console = Console()

class DocGenerator:
    """Generates documentation for code files and functions."""

    def __init__(self):
        self.console = Console()
        self.llm_service = None

    async def _get_llm_service(self):
        """Get LLM service for AI-powered documentation."""
        if not self.llm_service:
            self.llm_service = llm_service
        return self.llm_service

    def extract_python_info(self, file_path: Path) -> Dict[str, Any]:
        """Extract information from Python files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            info = {
                'classes': [],
                'functions': [],
                'imports': [],
                'docstring': ast.get_docstring(tree),
                'file_path': str(file_path)
            }

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    info['classes'].append({
                        'name': node.name,
                        'docstring': ast.get_docstring(node),
                        'methods': [m.name for m in node.body if isinstance(m, ast.FunctionDef)],
                        'line': node.lineno
                    })
                elif isinstance(node, ast.FunctionDef) and node.col_offset == 0:  # Top-level functions
                    info['functions'].append({
                        'name': node.name,
                        'docstring': ast.get_docstring(node),
                        'args': [arg.arg for arg in node.args.args],
                        'line': node.lineno
                    })
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            info['imports'].append(alias.name)
                    else:
                        module = node.module or ''
                        for alias in node.names:
                            info['imports'].append(f"{module}.{alias.name}")

            return info

        except Exception as e:
            console.print(f"[red]❌ Error parsing Python file: {str(e)}[/red]")
            return {}

    def extract_js_info(self, file_path: Path) -> Dict[str, Any]:
        """Extract basic information from JavaScript/TypeScript files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            info = {
                'exports': [],
                'imports': [],
                'functions': [],
                'classes': [],
                'file_path': str(file_path)
            }

            # Extract imports
            import_patterns = [
                r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]',
                r'import\s+[\'"]([^\'"]+)[\'"]',
                r'const\s+.*?\s+=\s+require\([\'"]([^\'"]+)[\'"]\)'
            ]

            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                info['imports'].extend(matches)

            # Extract exports
            export_patterns = [
                r'export\s+(?:default\s+)?(?:function|class|const|let|var)\s+(\w+)',
                r'export\s+\{\s*([^}]+)\s*\}',
                r'module\.exports\s*=\s*(\w+)'
            ]

            for pattern in export_patterns:
                matches = re.findall(pattern, content)
                info['exports'].extend(matches)

            # Extract function declarations
            function_patterns = [
                r'function\s+(\w+)\s*\(',
                r'const\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>',
                r'(\w+)\s*:\s*(?:async\s+)?function'
            ]

            for pattern in function_patterns:
                matches = re.findall(pattern, content)
                info['functions'].extend(matches)

            # Extract class declarations
            class_matches = re.findall(r'class\s+(\w+)', content)
            info['classes'].extend(class_matches)

            return info

        except Exception as e:
            console.print(f"[red]❌ Error parsing JS/TS file: {str(e)}[/red]")
            return {}

    async def generate_function_docs(self, file_path: str, function_name: str) -> bool:
        """Generate documentation for a specific function."""
        try:
            path = Path(file_path)
            if not path.exists():
                console.print(f"[red]❌ File not found: {file_path}[/red]")
                return False

            # Extract function information
            if path.suffix == '.py':
                info = self.extract_python_info(path)
                function_info = None

                # Find the function
                for func in info.get('functions', []):
                    if func['name'] == function_name:
                        function_info = func
                        break

                # Check class methods
                if not function_info:
                    for cls in info.get('classes', []):
                        if function_name in cls.get('methods', []):
                            function_info = {
                                'name': function_name,
                                'class': cls['name'],
                                'line': cls['line']
                            }
                            break

                if not function_info:
                    console.print(f"[red]❌ Function '{function_name}' not found in {file_path}[/red]")
                    return False

            else:
                console.print(f"[yellow]⚠️ Documentation generation for {path.suffix} files is basic[/yellow]")
                info = self.extract_js_info(path)
                function_info = {'name': function_name}

            # Generate AI-powered documentation
            llm = await self._get_llm_service()
            if llm:
                with open(path, 'r') as f:
                    content = f.read()

                prompt = f"""
Analyze this code and generate comprehensive documentation for the function '{function_name}':

```{path.suffix[1:]}
{content}
```

Generate documentation that includes:
1. Purpose and functionality
2. Parameters and their types
3. Return value and type
4. Usage examples
5. Any side effects or important notes

Format the response as markdown.
"""

                docs = await llm.complete(prompt)

                # Display generated documentation
                console.print(Panel(
                    docs,
                    title=f"📚 Documentation for {function_name}",
                    border_style="green"
                ))

                return True

            else:
                # Fallback to basic documentation
                self._generate_basic_docs(function_info, path)
                return True

        except Exception as e:
            console.print(f"[red]❌ Error generating documentation: {str(e)}[/red]")
            return False

    async def generate_file_docs(self, file_path: str) -> bool:
        """Generate documentation for an entire file."""
        try:
            path = Path(file_path)
            if not path.exists():
                console.print(f"[red]❌ File not found: {file_path}[/red]")
                return False

            console.print(f"[dim]→ Analyzing file: {path.name}[/dim]")

            # Extract file information
            if path.suffix == '.py':
                info = self.extract_python_info(path)
            else:
                info = self.extract_js_info(path)

            # Create documentation table
            table = Table(title=f"📄 File Overview: {path.name}", show_header=True, header_style="bold cyan")
            table.add_column("Type", style="yellow")
            table.add_column("Name", style="white")
            table.add_column("Details", style="dim")

            # Add imports
            for imp in info.get('imports', [])[:5]:  # Show first 5
                table.add_row("Import", imp, "")

            # Add classes
            for cls in info.get('classes', []):
                methods = ', '.join(cls.get('methods', [])[:3])
                if len(cls.get('methods', [])) > 3:
                    methods += "..."
                table.add_row("Class", cls['name'], f"Methods: {methods}")

            # Add functions
            for func in info.get('functions', []):
                args = ', '.join(func.get('args', []))
                table.add_row("Function", func['name'], f"Args: {args}")

            console.print(table)

            # Generate AI-powered file documentation if available
            llm = await self._get_llm_service()
            if llm:
                with open(path, 'r') as f:
                    content = f.read()[:2000]  # Limit content for prompt

                prompt = f"""
Analyze this code file and generate a concise overview:

File: {path.name}
```{path.suffix[1:]}
{content}
```

Provide a brief summary including:
1. Main purpose of the file
2. Key components (classes/functions)
3. Dependencies and relationships
4. Usage or integration notes

Keep it concise (2-3 paragraphs).
"""

                overview = await llm.complete(prompt)

                console.print(Panel(
                    overview,
                    title="🔍 File Analysis",
                    border_style="blue"
                ))

            return True

        except Exception as e:
            console.print(f"[red]❌ Error generating file documentation: {str(e)}[/red]")
            return False

    def _generate_basic_docs(self, function_info: Dict, file_path: Path):
        """Generate basic documentation without AI."""
        docs = f"""
# {function_info['name']}

**File:** `{file_path}`
**Line:** {function_info.get('line', 'Unknown')}

{function_info.get('docstring', 'No description available.')}

"""

        if 'args' in function_info:
            docs += f"**Parameters:** {', '.join(function_info['args'])}\n"

        console.print(Panel(
            docs,
            title=f"📚 Basic Documentation for {function_info['name']}",
            border_style="yellow"
        ))

# Global instance
doc_generator = DocGenerator()