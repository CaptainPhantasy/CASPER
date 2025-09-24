"""
Codebase Management Service for CASPER Prime IDE
Handles project opening, file tree generation, and workspace management.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from .settings import get_settings_store


@dataclass
class FileNode:
    """Represents a file or directory in the file tree."""
    name: str
    path: str
    type: str  # "file" or "directory"
    size: Optional[int] = None
    modified: Optional[str] = None
    children: Optional[List['FileNode']] = None
    is_expanded: bool = False


class CodebaseService:
    """
    Manages codebase operations for the CASPER Prime IDE.
    """
    
    def __init__(self):
        self.current_workspace: Optional[Path] = None
        self.workspace_config: Dict[str, Any] = {}
        self.workspace_analysis: Dict[str, Any] = {}
        self.ignored_patterns = {
            '.git', '.casper', 'node_modules', '__pycache__', '.pytest_cache',
            '.venv', 'venv', '.env', '.DS_Store', '*.pyc', '*.log'
        }
        self._recent_workspaces: List[Dict[str, Any]] = []
        self.state_dir = Path(os.environ.get("CASPER_STATE_DIR", Path.home() / ".casper"))
    
    def open_workspace(self, workspace_path: str) -> Dict[str, Any]:
        """
        Open a workspace/codebase and initialize project context.
        """
        workspace = Path(workspace_path).resolve()
        
        if not workspace.exists():
            raise ValueError(f"Workspace path does not exist: {workspace_path}")
        
        if not workspace.is_dir():
            raise ValueError(f"Workspace path is not a directory: {workspace_path}")

        self.current_workspace = workspace
        os.environ["CASPER_PROJECT_ROOT"] = str(workspace)

        # Load or create workspace configuration
        config_file = workspace / '.casper' / 'workspace.json'
        if config_file.exists():
            with open(config_file, 'r') as f:
                self.workspace_config = json.load(f)
        else:
            self.workspace_config = {
                'name': workspace.name,
                'path': str(workspace),
                'created_at': str(workspace.stat().st_ctime),
                'language': self._detect_primary_language(workspace),
                'framework': self._detect_framework(workspace)
            }
            self._save_workspace_config()

        self.workspace_analysis = self._analyze_project_structure()
        settings_store = get_settings_store(workspace)
        # Ensure a settings file exists so updates from the dashboard persist.
        settings_store.save(settings_store.load())
        self._record_recent_workspace(workspace)

        return {
            'workspace': self.workspace_config,
            'file_tree': self.get_file_tree(),
            'project_info': self.workspace_analysis
        }

    def get_file_tree(self, max_depth: int = 5) -> List[Dict]:
        """
        Generate file tree for the current workspace.
        """
        if not self.current_workspace:
            return []
        
        return self._build_file_tree(self.current_workspace, max_depth=max_depth)
    
    def _build_file_tree(self, path: Path, current_depth: int = 0, max_depth: int = 5) -> List[Dict]:
        """
        Recursively build file tree structure.
        """
        if current_depth > max_depth:
            return []
        
        items = []
        
        try:
            # Sort: directories first, then files, both alphabetically
            entries = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
            
            for entry in entries:
                # Skip ignored patterns
                if self._should_ignore(entry):
                    continue
                
                relative_path = entry.relative_to(self.current_workspace)
                
                if entry.is_dir():
                    children = self._build_file_tree(entry, current_depth + 1, max_depth)
                    node = FileNode(
                        name=entry.name,
                        path=str(relative_path),
                        type="folder",
                        children=children,
                        is_expanded=current_depth < 2  # Auto-expand first 2 levels
                    )
                else:
                    stat = entry.stat()
                    node = FileNode(
                        name=entry.name,
                        path=str(relative_path),
                        type="file",
                        size=stat.st_size,
                        modified=datetime.fromtimestamp(stat.st_mtime).isoformat()
                    )

                items.append(asdict(node))

        except PermissionError:
            # Skip directories we can't read
            pass
        
        return items
    
    def _should_ignore(self, path: Path) -> bool:
        """
        Check if a file/directory should be ignored.
        """
        name = path.name
        
        # Check exact matches
        if name in self.ignored_patterns:
            return True
        
        # Check pattern matches
        for pattern in self.ignored_patterns:
            if '*' in pattern:
                import fnmatch
                if fnmatch.fnmatch(name, pattern):
                    return True
        
        # Skip hidden files (starting with .)
        if name.startswith('.') and name not in {'.gitignore', '.env.example'}:
            return True
        
        return False
    
    def _detect_primary_language(self, workspace: Path) -> str:
        """
        Detect the primary programming language in the workspace.
        """
        language_files = {
            'python': ['.py'],
            'javascript': ['.js', '.jsx'],
            'typescript': ['.ts', '.tsx'],
            'java': ['.java'],
            'go': ['.go'],
            'rust': ['.rs'],
            'cpp': ['.cpp', '.cc', '.cxx'],
            'c': ['.c'],
            'php': ['.php'],
            'ruby': ['.rb']
        }
        
        file_counts = {}
        
        for file_path in workspace.rglob('*'):
            if file_path.is_file() and not self._should_ignore(file_path):
                suffix = file_path.suffix.lower()
                for lang, extensions in language_files.items():
                    if suffix in extensions:
                        file_counts[lang] = file_counts.get(lang, 0) + 1
        
        if file_counts:
            return max(file_counts, key=file_counts.get)
        
        return 'unknown'
    
    def _detect_framework(self, workspace: Path) -> str:
        """
        Detect the framework/platform being used.
        """
        framework_indicators = {
            'react': ['package.json', 'src/App.jsx', 'src/App.tsx'],
            'vue': ['package.json', 'src/App.vue'],
            'angular': ['angular.json', 'src/app/app.module.ts'],
            'django': ['manage.py', 'settings.py'],
            'flask': ['app.py', 'wsgi.py'],
            'fastapi': ['main.py', 'requirements.txt'],
            'express': ['package.json', 'server.js'],
            'spring': ['pom.xml', 'build.gradle'],
            'rails': ['Gemfile', 'config/application.rb']
        }
        
        for framework, indicators in framework_indicators.items():
            if all((workspace / indicator).exists() or 
                   any(workspace.rglob(indicator)) for indicator in indicators):
                return framework
        
        return 'unknown'
    
    def _analyze_project_structure(self) -> Dict[str, Any]:
        """
        Analyze project structure and provide insights.
        """
        if not self.current_workspace:
            return {}
        
        analysis = {
            'total_files': 0,
            'total_directories': 0,
            'file_types': {},
            'largest_files': [],
            'recent_files': []
        }

        files_by_size = []
        files_by_time = []

        for file_path in self.current_workspace.rglob('*'):
            if file_path.is_file() and not self._should_ignore(file_path):
                analysis['total_files'] += 1
                
                # Count file types
                ext = file_path.suffix.lower() or 'no_extension'
                analysis['file_types'][ext] = analysis['file_types'].get(ext, 0) + 1
                
                # Track for largest/recent files
                stat = file_path.stat()
                relative_path = file_path.relative_to(self.current_workspace)
                
                files_by_size.append({
                    'path': str(relative_path),
                    'size': stat.st_size
                })

                files_by_time.append({
                    'path': str(relative_path),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

            elif file_path.is_dir() and not self._should_ignore(file_path):
                analysis['total_directories'] += 1

        # Get top 5 largest and most recent files
        analysis['largest_files'] = sorted(files_by_size, key=lambda x: x['size'], reverse=True)[:5]
        analysis['recent_files'] = sorted(files_by_time, key=lambda x: x['modified'], reverse=True)[:5]

        return analysis

    def read_file(self, file_path: str) -> Dict[str, Any]:
        """
        Read file content safely.
        """
        if not self.current_workspace:
            raise ValueError("No workspace opened")
        
        full_path = self.current_workspace / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not full_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")
        
        # Check if file is too large (>1MB)
        if full_path.stat().st_size > 1024 * 1024:
            return {
                'path': file_path,
                'content': '[File too large to display]',
                'size': full_path.stat().st_size,
                'binary': True
            }
        
        try:
            content = full_path.read_text(encoding='utf-8')
            return {
                'path': file_path,
                'content': content,
                'size': len(content),
                'binary': False
            }
        except UnicodeDecodeError:
            return {
                'path': file_path,
                'content': '[Binary file]',
                'size': full_path.stat().st_size,
                'binary': True
            }
    
    def _save_workspace_config(self):
        """
        Save workspace configuration to .casper/workspace.json
        """
        if not self.current_workspace:
            return
        
        config_dir = self.current_workspace / '.casper'
        config_dir.mkdir(exist_ok=True)
        
        config_file = config_dir / 'workspace.json'
        with open(config_file, 'w') as f:
            json.dump(self.workspace_config, f, indent=2)

    def _record_recent_workspace(self, workspace: Path) -> None:
        """Track a recently opened workspace for the Open Workspace dialog."""

        if not self._recent_workspaces:
            self._recent_workspaces = self._load_recent_workspaces()

        entry = {
            'path': str(workspace),
            'name': workspace.name,
            'last_opened': datetime.utcnow().isoformat(),
            'language': self.workspace_config.get('language', 'unknown'),
            'framework': self.workspace_config.get('framework', 'unknown'),
            'file_count': self.workspace_analysis.get('total_files', 0),
        }

        existing = [ws for ws in self._recent_workspaces if ws['path'] != entry['path']]
        self._recent_workspaces = [entry] + existing[:9]
        self._save_recent_workspaces(self._recent_workspaces)

    def _recent_file(self) -> Path:
        return self.state_dir / 'recent-workspaces.json'

    def _load_recent_workspaces(self) -> List[Dict[str, Any]]:
        path = self._recent_file()
        if not path.exists():
            return []
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                data = json.load(handle)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            return []
        return []

    def _save_recent_workspaces(self, data: List[Dict[str, Any]]) -> None:
        path = self._recent_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, indent=2)

    def get_recent_workspaces(self) -> List[Dict[str, Any]]:
        if not self._recent_workspaces:
            self._recent_workspaces = self._load_recent_workspaces()
        return self._recent_workspaces

    def get_workspace_info(self) -> Dict[str, Any]:
        if not self.current_workspace:
            raise ValueError("No workspace opened")

        settings_store = get_settings_store(self.current_workspace)
        settings = settings_store.load()

        if not self.workspace_analysis:
            self.workspace_analysis = self._analyze_project_structure()

        return {
            'workspace': self.workspace_config,
            'current_path': str(self.current_workspace),
            'analysis': self.workspace_analysis,
            'settings': settings,
            'recent': self.get_recent_workspaces(),
        }

    def update_settings(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.current_workspace:
            raise ValueError("No workspace opened")
        settings_store = get_settings_store(self.current_workspace)
        return settings_store.save(payload)

    def search_files(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.current_workspace:
            return []
        matches: List[Dict[str, Any]] = []
        lowered = query.lower().strip()
        if not lowered:
            return matches

        for file_path in self.current_workspace.rglob('*'):
            if len(matches) >= limit:
                break
            if not file_path.is_file() or self._should_ignore(file_path):
                continue
            name = file_path.name
            if lowered in name.lower():
                stat = file_path.stat()
                matches.append({
                    'path': str(file_path.relative_to(self.current_workspace)),
                    'name': name,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
        return matches


# Global instance
codebase_service = CodebaseService()
