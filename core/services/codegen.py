"""
CASPER Code Generation Service
Real implementation of code generation features including components, routes, and scaffolding.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

from core.services.personalization import personalization_manager

console = Console()

class CodeTemplates:
    """Code templates for different frameworks and languages."""

    REACT_COMPONENT = """import React from 'react';
import './{component_name}.css';

interface {component_name}Props {{
  // Add your props here
}}

const {component_name}: React.FC<{component_name}Props> = (props) => {{
  return (
    <div className="{component_name_lower}">
      <h1>{component_name}</h1>
      {/* Add your component content here */}
    </div>
  );
}};

export default {component_name};
"""

    REACT_CSS = """.{component_name_lower} {{
  /* Add your styles here */
  padding: 1rem;
}}

.{component_name_lower} h1 {{
  color: #333;
  margin: 0 0 1rem 0;
}}
"""

    REACT_TEST = """import {{ render, screen }} from '@testing-library/react';
import {component_name} from './{component_name}';

describe('{component_name}', () => {{
  it('renders without crashing', () => {{
    render(<{component_name} />);
    expect(screen.getByText('{component_name}')).toBeInTheDocument();
  }});
}});
"""

    REACT_STORY = """import type {{ Meta, StoryObj }} from '@storybook/react';
import {component_name} from './{component_name}';

const meta: Meta<typeof {component_name}> = {{
  title: 'Components/{component_name}',
  component: {component_name},
  parameters: {{
    layout: 'centered',
  }},
  tags: ['autodocs'],
}};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {{
  args: {{
    // Add default props here
  }},
}};
"""

    VUE_COMPONENT = """<template>
  <div class="{component_name_lower}">
    <h1>{{ title }}</h1>
    <!-- Add your component content here -->
  </div>
</template>

<script setup lang="ts">
interface Props {{
  title?: string;
}}

withDefaults(defineProps<Props>(), {{
  title: '{component_name}',
}});
</script>

<style scoped>
.{component_name_lower} {{
  /* Add your styles here */
  padding: 1rem;
}}

.{component_name_lower} h1 {{
  color: #333;
  margin: 0 0 1rem 0;
}}
</style>
"""

    PYTHON_CLASS = """\"\"\"
{component_name} module.
Created by CASPER on {date}.
\"\"\"

from typing import Optional, Dict, Any


class {component_name}:
    \"\"\"
    {component_name} class for handling {description}.
    \"\"\"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        \"\"\"
        Initialize {component_name}.

        Args:
            config: Optional configuration dictionary
        \"\"\"
        self.config = config or {{}}
        self._initialize()

    def _initialize(self) -> None:
        \"\"\"Initialize the component.\"\"\"
        pass

    def process(self, data: Any) -> Any:
        \"\"\"
        Process data using this component.

        Args:
            data: Input data to process

        Returns:
            Processed data
        \"\"\"
        # TODO: Implement processing logic
        return data

    def __repr__(self) -> str:
        return f\"{component_name}(config={{len(self.config)}} items)\"
"""

    PYTHON_TEST = """\"\"\"
Tests for {component_name} module.
\"\"\"

import pytest
from {module_name} import {component_name}


class Test{component_name}:
    \"\"\"Test cases for {component_name}.\"\"\"

    def test_initialization(self):
        \"\"\"Test component initialization.\"\"\"
        component = {component_name}()
        assert component is not None
        assert component.config == {{}}

    def test_initialization_with_config(self):
        \"\"\"Test component initialization with config.\"\"\"
        config = {{"test": "value"}}
        component = {component_name}(config)
        assert component.config == config

    def test_process(self):
        \"\"\"Test process method.\"\"\"
        component = {component_name}()
        test_data = "test"
        result = component.process(test_data)
        assert result == test_data

    def test_repr(self):
        \"\"\"Test string representation.\"\"\"
        component = {component_name}()
        assert "{component_name}" in str(component)
"""

class ComponentGenerator:
    """Generates components with proper file structure and boilerplate."""

    def __init__(self):
        self.console = Console()
        self.templates = CodeTemplates()

    def detect_project_type(self, path: Path) -> str:
        """Detect the project type based on files in the directory."""
        if (path / "package.json").exists():
            package_json = path / "package.json"
            try:
                import json
                with open(package_json) as f:
                    data = json.load(f)
                    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                    if "react" in deps:
                        return "react"
                    elif "vue" in deps:
                        return "vue"
                    else:
                        return "nodejs"
            except:
                return "nodejs"

        elif (path / "pyproject.toml").exists() or (path / "requirements.txt").exists():
            return "python"

        elif (path / "Cargo.toml").exists():
            return "rust"

        elif (path / "go.mod").exists():
            return "go"

        return "unknown"

    def find_component_directory(self, project_type: str, base_path: Path) -> Optional[Path]:
        """Find the appropriate directory to place components."""
        common_paths = {
            "react": ["src/components", "components", "src"],
            "vue": ["src/components", "components", "src"],
            "python": ["src", "lib", "."],
            "nodejs": ["src", "lib", "."]
        }

        for potential_path in common_paths.get(project_type, ["."]):
            full_path = base_path / potential_path
            if full_path.exists():
                return full_path

        return base_path

    def create_react_component(self, name: str, path: Path, options: Dict) -> List[Path]:
        """Create a React component with all associated files."""
        created_files = []

        # Create component directory
        component_dir = path / name
        component_dir.mkdir(exist_ok=True)

        # Generate component file
        component_code = self.templates.REACT_COMPONENT.format(
            component_name=name,
            component_name_lower=name.lower()
        )

        component_file = component_dir / f"{name}.tsx"
        with open(component_file, 'w') as f:
            f.write(component_code)
        created_files.append(component_file)

        # Generate CSS file
        css_code = self.templates.REACT_CSS.format(
            component_name_lower=name.lower()
        )

        css_file = component_dir / f"{name}.css"
        with open(css_file, 'w') as f:
            f.write(css_code)
        created_files.append(css_file)

        # Generate test file if requested
        if options.get("include_tests", True):
            test_code = self.templates.REACT_TEST.format(
                component_name=name
            )

            test_file = component_dir / f"{name}.test.tsx"
            with open(test_file, 'w') as f:
                f.write(test_code)
            created_files.append(test_file)

        # Generate Storybook story if requested
        if options.get("include_stories", False):
            story_code = self.templates.REACT_STORY.format(
                component_name=name
            )

            story_file = component_dir / f"{name}.stories.tsx"
            with open(story_file, 'w') as f:
                f.write(story_code)
            created_files.append(story_file)

        # Generate index file for easy importing
        index_code = f"export {{ default }} from './{name}';\n"
        index_file = component_dir / "index.ts"
        with open(index_file, 'w') as f:
            f.write(index_code)
        created_files.append(index_file)

        return created_files

    def create_vue_component(self, name: str, path: Path, options: Dict) -> List[Path]:
        """Create a Vue component."""
        created_files = []

        component_code = self.templates.VUE_COMPONENT.format(
            component_name=name,
            component_name_lower=name.lower()
        )

        component_file = path / f"{name}.vue"
        with open(component_file, 'w') as f:
            f.write(component_code)
        created_files.append(component_file)

        return created_files

    def create_python_component(self, name: str, path: Path, options: Dict) -> List[Path]:
        """Create a Python class/module."""
        created_files = []

        # Convert component name to appropriate formats
        module_name = re.sub(r'([A-Z])', r'_\1', name).lower().lstrip('_')
        description = options.get("description", f"{name} functionality")

        component_code = self.templates.PYTHON_CLASS.format(
            component_name=name,
            module_name=module_name,
            description=description,
            date=datetime.now().strftime("%Y-%m-%d")
        )

        component_file = path / f"{module_name}.py"
        with open(component_file, 'w') as f:
            f.write(component_code)
        created_files.append(component_file)

        # Generate test file if requested
        if options.get("include_tests", True):
            test_code = self.templates.PYTHON_TEST.format(
                component_name=name,
                module_name=module_name
            )

            test_file = path / f"test_{module_name}.py"
            with open(test_file, 'w') as f:
                f.write(test_code)
            created_files.append(test_file)

        return created_files

    async def generate_component(self, name: str, component_type: Optional[str] = None,
                               options: Optional[Dict] = None) -> bool:
        """
        Generate a new component with boilerplate code.

        Args:
            name: Component name
            component_type: Type of component (react, vue, python)
            options: Additional options for generation

        Returns:
            True if successful, False otherwise
        """
        if not name:
            console.print("[red]❌ Component name is required[/red]")
            return False

        # Validate component name
        if not re.match(r'^[A-Za-z][A-Za-z0-9_]*$', name):
            console.print("[red]❌ Invalid component name. Use letters, numbers, and underscores only.[/red]")
            return False

        # Detect project type if not specified
        current_path = Path.cwd()
        if not component_type:
            detected_type = self.detect_project_type(current_path)
            if detected_type == "unknown":
                component_type = Prompt.ask(
                    "Component type",
                    choices=["react", "vue", "python", "nodejs"],
                    default="react"
                )
            else:
                component_type = detected_type
                console.print(f"[dim]→ Detected project type: {component_type}[/dim]")

        # Get user preferences
        prefs = personalization_manager.codegen_prefs
        options = options or {}

        # Set default options based on preferences
        options.setdefault("include_tests", True)
        options.setdefault("include_stories", prefs.include_stories)
        options.setdefault("include_types", prefs.include_types)

        # Find appropriate directory
        component_dir = self.find_component_directory(component_type, current_path)
        if not component_dir:
            console.print("[red]❌ Could not find appropriate directory for components[/red]")
            return False

        console.print(f"[dim]→ Creating {component_type} component '{name}' in {component_dir}[/dim]")

        try:
            created_files = []

            if component_type == "react":
                created_files = self.create_react_component(name, component_dir, options)
            elif component_type == "vue":
                created_files = self.create_vue_component(name, component_dir, options)
            elif component_type == "python":
                created_files = self.create_python_component(name, component_dir, options)
            else:
                console.print(f"[yellow]⚠️  Component type '{component_type}' not yet supported[/yellow]")
                return False

            # Display success message with created files
            console.print(f"[green]✅ Component '{name}' created successfully![/green]")

            # Show created files in a nice table
            if created_files:
                table = Table(title="Created Files", show_header=True, header_style="bold green")
                table.add_column("File", style="bright_white")
                table.add_column("Type", style="bright_cyan")

                for file_path in created_files:
                    file_type = self._get_file_type(file_path)
                    table.add_row(str(file_path.relative_to(current_path)), file_type)

                console.print(table)

            return True

        except Exception as e:
            console.print(f"[red]❌ Failed to create component: {str(e)}[/red]")
            return False

    def _get_file_type(self, file_path: Path) -> str:
        """Get a friendly description of the file type."""
        suffix = file_path.suffix.lower()
        name = file_path.name.lower()

        if "test" in name:
            return "Test file"
        elif "story" in name or "stories" in name:
            return "Storybook story"
        elif suffix in [".tsx", ".jsx"]:
            return "React component"
        elif suffix == ".vue":
            return "Vue component"
        elif suffix == ".py":
            return "Python module"
        elif suffix == ".css":
            return "Stylesheet"
        elif suffix == ".ts":
            return "TypeScript"
        else:
            return "File"

# Global instance
code_generator = ComponentGenerator()