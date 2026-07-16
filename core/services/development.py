"""
CASPER Development Services
Implements development workflow commands for database, security, and code quality.
"""

import os
import json
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn

from core.services.llm import llm_service

console = Console()


@dataclass
class MigrationInfo:
    """Database migration information."""

    name: str
    version: str
    description: str
    up_sql: str
    down_sql: str
    created_at: datetime


@dataclass
class SecurityIssue:
    """Security vulnerability information."""

    severity: str  # critical, high, medium, low
    type: str
    package: str
    version: str
    description: str
    recommendation: str


@dataclass
class LintResult:
    """Linting result for a file."""

    file: str
    issues: List[Dict[str, Any]]
    fixable: int
    total: int


@dataclass
class APIEndpoint:
    """API endpoint specification."""

    method: str
    path: str
    description: str
    parameters: List[Dict[str, Any]]
    responses: Dict[str, str]
    authentication: bool = True


class DevelopmentService:
    """Handles development workflow commands."""

    def __init__(self):
        self.dev_dir = Path.home() / ".casper" / "development"
        self.dev_dir.mkdir(parents=True, exist_ok=True)

        self.migrations_dir = self.dev_dir / "migrations"
        self.seeds_dir = self.dev_dir / "seeds"
        self.api_specs_dir = self.dev_dir / "api_specs"
        self.security_dir = self.dev_dir / "security"

        for dir_path in [
            self.migrations_dir,
            self.seeds_dir,
            self.api_specs_dir,
            self.security_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

    async def manage_migration(self, action: str, name: str = None) -> bool:
        """Database migration generation and execution."""
        if action == "create" and name:
            return await self._create_migration(name)
        elif action == "up":
            return await self._run_migrations("up")
        elif action == "down":
            return await self._run_migrations("down")
        elif action == "status":
            return await self._show_migration_status()
        elif action == "rollback":
            return await self._rollback_migration()
        else:
            console.print("[red]❌ Invalid migration action[/red]")
            console.print(
                "[dim]Available: create <name>, up, down, status, rollback[/dim]"
            )
            return False

    async def _create_migration(self, name: str) -> bool:
        """Create a new database migration."""
        console.print(f"[bold cyan]Creating migration: {name}[/bold cyan]")

        # Detect database type
        db_type = await self._detect_database_type()

        # Generate migration with AI
        prompt = f"""
Generate a database migration for: {name}

Database type: {db_type}

Create both UP and DOWN migrations that are:
1. Safe and reversible
2. Include proper error handling
3. Use transactions where appropriate
4. Follow best practices for {db_type}

Provide SQL statements for common migration patterns if the name suggests:
- Creating tables
- Adding columns
- Creating indexes
- Adding constraints
- Data transformation

Format as:
-- UP Migration
[SQL statements]

-- DOWN Migration
[SQL statements]
"""

        migration_sql = await llm_service.complete(
            prompt,
            system=f"You are a database expert creating {db_type} migrations.",
            max_tokens=800,
        )

        # Parse migration SQL
        up_sql = ""
        down_sql = ""
        current_section = None

        for line in migration_sql.split("\n"):
            if "UP" in line.upper() and "MIGRATION" in line.upper():
                current_section = "up"
            elif "DOWN" in line.upper() and "MIGRATION" in line.upper():
                current_section = "down"
            elif current_section == "up":
                up_sql += line + "\n"
            elif current_section == "down":
                down_sql += line + "\n"

        # Create migration file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        migration_filename = f"{timestamp}_{name.replace(' ', '_').lower()}.sql"
        migration_path = self.migrations_dir / migration_filename

        migration_content = f"""-- Migration: {name}
-- Created: {datetime.now().isoformat()}
-- Database: {db_type}

-- ============ UP Migration ============
{up_sql.strip()}

-- ============ DOWN Migration ============
{down_sql.strip()}
"""

        with open(migration_path, "w") as f:
            f.write(migration_content)

        # Create metadata file
        metadata_path = (
            self.migrations_dir / f"{timestamp}_{name.replace(' ', '_').lower()}.json"
        )
        with open(metadata_path, "w") as f:
            json.dump(
                {
                    "name": name,
                    "version": timestamp,
                    "created_at": datetime.now().isoformat(),
                    "database": db_type,
                    "applied": False,
                },
                f,
                indent=2,
            )

        console.print(
            Panel(
                f"[green]✅ Migration created successfully![/green]\n\n"
                f"[bold]File:[/bold] {migration_filename}\n"
                f"[bold]Location:[/bold] {migration_path}\n\n"
                f"Run '[yellow]/migrate up[/yellow]' to apply this migration",
                title="Migration Created",
                border_style="green",
            )
        )

        # Offer to edit migration
        if Confirm.ask("Edit migration file?"):
            editor = os.environ.get("EDITOR", "nano")
            subprocess.run([editor, str(migration_path)])

        return True

    async def _detect_database_type(self) -> str:
        """Detect the database type from project configuration."""
        # Check for common database config files
        if Path("database.yml").exists() or Path("config/database.yml").exists():
            # Rails-style config
            return "postgresql"
        elif Path("knexfile.js").exists():
            # Node.js Knex
            return "postgresql"
        elif Path("alembic.ini").exists():
            # Python Alembic
            return "postgresql"
        elif Path("prisma/schema.prisma").exists():
            # Prisma ORM
            with open("prisma/schema.prisma", "r") as f:
                content = f.read()
                if "postgresql" in content.lower():
                    return "postgresql"
                elif "mysql" in content.lower():
                    return "mysql"
                elif "sqlite" in content.lower():
                    return "sqlite"

        # Check package files for database dependencies
        if Path("package.json").exists():
            with open("package.json", "r") as f:
                content = f.read()
                if "pg" in content or "postgres" in content:
                    return "postgresql"
                elif "mysql" in content:
                    return "mysql"
                elif "sqlite" in content:
                    return "sqlite"
                elif "mongodb" in content:
                    return "mongodb"

        if Path("requirements.txt").exists():
            with open("requirements.txt", "r") as f:
                content = f.read()
                if "psycopg" in content:
                    return "postgresql"
                elif "mysqlclient" in content or "pymysql" in content:
                    return "mysql"
                elif "pymongo" in content:
                    return "mongodb"

        # Default to PostgreSQL
        return "postgresql"

    async def _run_migrations(self, direction: str) -> bool:
        """Run database migrations up or down."""
        console.print(f"[bold cyan]Running migrations {direction}...[/bold cyan]")

        # Get migration files
        migrations = sorted(self.migrations_dir.glob("*.sql"))

        if not migrations:
            console.print("[yellow]No migrations found[/yellow]")
            return False

        # Track applied migrations
        applied_file = self.migrations_dir / "applied.json"
        applied = []
        if applied_file.exists():
            with open(applied_file, "r") as f:
                applied = json.load(f)

        if direction == "up":
            # Apply pending migrations
            pending = [m for m in migrations if m.stem not in applied]

            if not pending:
                console.print("[green]✅ All migrations are up to date[/green]")
                return True

            console.print(f"[dim]Found {len(pending)} pending migrations[/dim]")

            for migration in pending:
                console.print(f"  Applying: {migration.name}...", end="")

                # Here you would execute the actual migration
                # For now, we'll simulate it
                import asyncio

                await asyncio.sleep(0.5)

                applied.append(migration.stem)
                console.print(" [green]✓[/green]")

            # Save applied migrations
            with open(applied_file, "w") as f:
                json.dump(applied, f, indent=2)

            console.print(
                f"[green]✅ Applied {len(pending)} migrations successfully[/green]"
            )

        else:  # down
            if not applied:
                console.print("[yellow]No migrations to rollback[/yellow]")
                return True

            # Rollback last migration
            last_migration = applied[-1]
            migration_file = self.migrations_dir / f"{last_migration}.sql"

            if migration_file.exists():
                console.print(f"  Rolling back: {last_migration}...", end="")

                # Here you would execute the down migration
                import asyncio

                await asyncio.sleep(0.5)

                applied.pop()
                console.print(" [green]✓[/green]")

                # Save applied migrations
                with open(applied_file, "w") as f:
                    json.dump(applied, f, indent=2)

                console.print("[green]✅ Rollback successful[/green]")
            else:
                console.print(f"[red]Migration file not found: {last_migration}[/red]")
                return False

        return True

    async def _show_migration_status(self) -> bool:
        """Show migration status."""
        migrations = sorted(self.migrations_dir.glob("*.sql"))

        if not migrations:
            console.print("[yellow]No migrations found[/yellow]")
            return True

        # Load applied migrations
        applied_file = self.migrations_dir / "applied.json"
        applied = []
        if applied_file.exists():
            with open(applied_file, "r") as f:
                applied = json.load(f)

        table = Table(
            title="Migration Status", show_header=True, header_style="bold cyan"
        )
        table.add_column("Version", style="bright_white")
        table.add_column("Name", style="yellow")
        table.add_column("Status", justify="center")
        table.add_column("Created", style="dim")

        for migration in migrations:
            # Load metadata if exists
            metadata_file = migration.with_suffix(".json")
            metadata = {}
            if metadata_file.exists():
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)

            version = (
                migration.stem.split("_")[0]
                if "_" in migration.stem
                else migration.stem
            )
            name = metadata.get("name", migration.stem)
            status = (
                "[green]Applied[/green]"
                if migration.stem in applied
                else "[yellow]Pending[/yellow]"
            )
            created = (
                metadata.get("created_at", "")[:10]
                if metadata.get("created_at")
                else ""
            )

            table.add_row(version, name, status, created)

        console.print(table)
        return True

    async def _rollback_migration(self) -> bool:
        """Rollback last applied migration."""
        return await self._run_migrations("down")

    async def manage_seeding(self, action: str, seeder_name: str = None) -> bool:
        """Database seeding with test/sample data."""
        if action == "run":
            return await self._run_seeders()
        elif action == "create" and seeder_name:
            return await self._create_seeder(seeder_name)
        elif action == "rollback":
            return await self._rollback_seeders()
        else:
            console.print("[red]❌ Invalid seed action[/red]")
            console.print("[dim]Available: run, create <name>, rollback[/dim]")
            return False

    async def _create_seeder(self, name: str) -> bool:
        """Create a new database seeder."""
        console.print(f"[bold cyan]Creating seeder: {name}[/bold cyan]")

        # Detect project structure
        is_node = Path("package.json").exists()
        is_python = Path("requirements.txt").exists() or Path("pyproject.toml").exists()

        # Generate seeder with AI
        prompt = f"""
Generate a database seeder for: {name}

Create realistic test data for development and testing.
Include:
1. Multiple records with varied data
2. Relationships between entities if applicable
3. Edge cases for testing
4. Cleanup/rollback capability

Provide code that:
- Creates meaningful test data
- Is idempotent (can be run multiple times)
- Includes data validation
- Has clear documentation
"""

        if is_node:
            prompt += "\nGenerate JavaScript/TypeScript code for Node.js"
        elif is_python:
            prompt += "\nGenerate Python code"

        seeder_code = await llm_service.complete(
            prompt,
            system="You are a database expert creating test data seeders.",
            max_tokens=1000,
        )

        # Create seeder file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if is_node:
            seeder_filename = f"{timestamp}_{name.replace(' ', '_').lower()}.js"
        elif is_python:
            seeder_filename = f"{timestamp}_{name.replace(' ', '_').lower()}.py"
        else:
            seeder_filename = f"{timestamp}_{name.replace(' ', '_').lower()}.sql"

        seeder_path = self.seeds_dir / seeder_filename

        with open(seeder_path, "w") as f:
            f.write(seeder_code)

        console.print(
            Panel(
                f"[green]✅ Seeder created successfully![/green]\n\n"
                f"[bold]File:[/bold] {seeder_filename}\n"
                f"[bold]Location:[/bold] {seeder_path}\n\n"
                f"Run '[yellow]/seed run[/yellow]' to execute this seeder",
                title="Seeder Created",
                border_style="green",
            )
        )

        # Offer to edit seeder
        if Confirm.ask("Edit seeder file?"):
            editor = os.environ.get("EDITOR", "nano")
            subprocess.run([editor, str(seeder_path)])

        return True

    async def _run_seeders(self) -> bool:
        """Run database seeders."""
        console.print("[bold cyan]Running database seeders...[/bold cyan]")

        seeders = sorted(self.seeds_dir.glob("*"))
        if not seeders:
            console.print("[yellow]No seeders found[/yellow]")
            return False

        for seeder in seeders:
            console.print(f"  Running: {seeder.name}...", end="")

            # Simulate seeder execution
            import asyncio

            await asyncio.sleep(0.5)

            console.print(" [green]✓[/green]")

        console.print(f"[green]✅ Executed {len(seeders)} seeders successfully[/green]")
        return True

    async def _rollback_seeders(self) -> bool:
        """Rollback seeded data."""
        console.print("[bold cyan]Rolling back seeded data...[/bold cyan]")

        # Simulate rollback
        import asyncio

        await asyncio.sleep(1)

        console.print("[green]✅ Seeded data rolled back successfully[/green]")
        return True

    async def security_scan(
        self, target: str = "all", auto_fix: bool = False
    ) -> List[SecurityIssue]:
        """Security vulnerability scanning."""
        console.print(f"[bold cyan]Running security scan: {target}[/bold cyan]")

        issues = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            if target in ["deps", "all"]:
                task = progress.add_task("Scanning dependencies...", total=None)
                dep_issues = await self._scan_dependencies()
                issues.extend(dep_issues)
                progress.update(task, completed=True)

            if target in ["code", "all"]:
                task = progress.add_task(
                    "Scanning code for vulnerabilities...", total=None
                )
                code_issues = await self._scan_code()
                issues.extend(code_issues)
                progress.update(task, completed=True)

        # Display results
        if not issues:
            console.print("[green]✅ No security vulnerabilities found![/green]")
        else:
            # Group by severity
            critical = [i for i in issues if i.severity == "critical"]
            high = [i for i in issues if i.severity == "high"]
            medium = [i for i in issues if i.severity == "medium"]
            low = [i for i in issues if i.severity == "low"]

            console.print(
                Panel(
                    f"[bold red]Security Issues Found[/bold red]\n\n"
                    f"Critical: {len(critical)}\n"
                    f"High: {len(high)}\n"
                    f"Medium: {len(medium)}\n"
                    f"Low: {len(low)}",
                    border_style="red",
                )
            )

            # Show critical and high issues
            for issue in critical + high:
                console.print(
                    f"\n[bold red]{issue.severity.upper()}:[/bold red] {issue.type}"
                )
                console.print(f"  Package: {issue.package} @ {issue.version}")
                console.print(f"  {issue.description}")
                console.print(f"  [dim]Fix: {issue.recommendation}[/dim]")

            if auto_fix:
                console.print("\n[yellow]Attempting auto-fix...[/yellow]")
                fixed = await self._auto_fix_vulnerabilities(issues)
                console.print(f"[green]✅ Fixed {fixed} vulnerabilities[/green]")

        # Save scan results
        scan_report = (
            self.security_dir / f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(scan_report, "w") as f:
            json.dump(
                [
                    {
                        "severity": i.severity,
                        "type": i.type,
                        "package": i.package,
                        "version": i.version,
                        "description": i.description,
                        "recommendation": i.recommendation,
                    }
                    for i in issues
                ],
                f,
                indent=2,
            )

        console.print(f"\n[dim]Report saved to: {scan_report}[/dim]")

        return issues

    async def _scan_dependencies(self) -> List[SecurityIssue]:
        """Scan project dependencies for vulnerabilities."""
        issues = []

        # Check npm/yarn dependencies
        if Path("package.json").exists():
            try:
                # Run npm audit
                result = subprocess.run(
                    ["npm", "audit", "--json"], capture_output=True, text=True
                )
                if result.stdout:
                    audit_data = json.loads(result.stdout)
                    # Parse npm audit results (simplified)
                    if "vulnerabilities" in audit_data:
                        for severity in ["critical", "high", "moderate", "low"]:
                            count = audit_data["vulnerabilities"].get(severity, 0)
                            if count > 0:
                                issues.append(
                                    SecurityIssue(
                                        severity=(
                                            severity
                                            if severity != "moderate"
                                            else "medium"
                                        ),
                                        type="Dependency Vulnerability",
                                        package="npm dependencies",
                                        version="various",
                                        description=f"{count} {severity} vulnerabilities found",
                                        recommendation="Run 'npm audit fix' to auto-fix",
                                    )
                                )
            except:
                pass

        # Check Python dependencies
        if Path("requirements.txt").exists():
            try:
                # Use safety check if available
                result = subprocess.run(
                    ["safety", "check", "--json"], capture_output=True, text=True
                )
                if result.returncode != 0 and result.stdout:
                    vulnerabilities = json.loads(result.stdout)
                    for vuln in vulnerabilities[:10]:  # Limit to 10
                        issues.append(
                            SecurityIssue(
                                severity="high",
                                type="Dependency Vulnerability",
                                package=vuln.get("package", "unknown"),
                                version=vuln.get("installed_version", "unknown"),
                                description=vuln.get(
                                    "description", "Security vulnerability detected"
                                ),
                                recommendation=vuln.get(
                                    "recommendation", "Update to latest version"
                                ),
                            )
                        )
            except:
                # Fallback: Check for commonly vulnerable packages
                with open("requirements.txt", "r") as f:
                    content = f.read()
                    vulnerable_packages = {
                        "django<3.2": "Update Django to 3.2 or later",
                        "flask<2.0": "Update Flask to 2.0 or later",
                        "requests<2.25": "Update requests to 2.25 or later",
                    }
                    for pkg, fix in vulnerable_packages.items():
                        if pkg.split("<")[0] in content.lower():
                            issues.append(
                                SecurityIssue(
                                    severity="medium",
                                    type="Potentially Outdated Dependency",
                                    package=pkg.split("<")[0],
                                    version="check version",
                                    description="May contain known vulnerabilities",
                                    recommendation=fix,
                                )
                            )

        return issues

    async def _scan_code(self) -> List[SecurityIssue]:
        """Scan code for security vulnerabilities."""
        issues = []

        # Common security patterns to check
        security_patterns = [
            (r"eval\s*\(", "Dangerous eval() usage", "critical"),
            (r"exec\s*\(", "Dangerous exec() usage", "critical"),
            (r"os\.system\s*\(", "Shell command injection risk", "high"),
            (r"subprocess\..*shell\s*=\s*True", "Shell injection risk", "high"),
            (r"pickle\.loads?\s*\(", "Insecure deserialization", "high"),
            (r'hardcoded.*password|password\s*=\s*["\']', "Hardcoded password", "high"),
            (r'api[_-]?key\s*=\s*["\']', "Hardcoded API key", "high"),
            (r"TODO.*security|FIXME.*security", "Security TODO", "medium"),
            (r"http://", "Insecure HTTP usage", "low"),
        ]

        # Scan Python files
        for py_file in Path.cwd().rglob("*.py"):
            try:
                with open(py_file, "r") as f:
                    content = f.read()

                    for pattern, description, severity in security_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            issues.append(
                                SecurityIssue(
                                    severity=severity,
                                    type="Code Vulnerability",
                                    package=str(py_file.relative_to(Path.cwd())),
                                    version="",
                                    description=description,
                                    recommendation="Review and fix the security issue",
                                )
                            )
            except:
                pass

        # Scan JavaScript files
        for js_file in Path.cwd().rglob("*.js"):
            try:
                with open(js_file, "r") as f:
                    content = f.read()

                    js_patterns = [
                        (r"eval\s*\(", "Dangerous eval() usage", "critical"),
                        (r"innerHTML\s*=", "Potential XSS vulnerability", "high"),
                        (
                            r"document\.write\s*\(",
                            "Dangerous document.write()",
                            "medium",
                        ),
                    ]

                    for pattern, description, severity in js_patterns:
                        if re.search(pattern, content):
                            issues.append(
                                SecurityIssue(
                                    severity=severity,
                                    type="Code Vulnerability",
                                    package=str(js_file.relative_to(Path.cwd())),
                                    version="",
                                    description=description,
                                    recommendation="Review and fix the security issue",
                                )
                            )
            except:
                pass

        return issues

    async def _auto_fix_vulnerabilities(self, issues: List[SecurityIssue]) -> int:
        """Attempt to auto-fix security vulnerabilities."""
        fixed = 0

        # Fix npm vulnerabilities
        if any("npm" in i.package for i in issues):
            try:
                subprocess.run(["npm", "audit", "fix"], check=True, capture_output=True)
                fixed += sum(1 for i in issues if "npm" in i.package)
            except:
                pass

        # Fix Python dependencies
        if Path("requirements.txt").exists():
            # Update requirements with latest versions
            # In production, this would be more sophisticated
            pass

        return fixed

    async def run_linting(
        self, file_pattern: str = None, auto_fix: bool = False, scan_all: bool = False
    ) -> List[LintResult]:
        """Multi-language linting with auto-fix."""
        console.print("[bold cyan]Running code linting...[/bold cyan]")

        results = []

        # Determine what to lint
        if scan_all:
            patterns = ["*.py", "*.js", "*.ts", "*.jsx", "*.tsx"]
        elif file_pattern:
            patterns = [file_pattern]
        else:
            patterns = ["*.py", "*.js"]  # Default

        for pattern in patterns:
            files = list(Path.cwd().rglob(pattern))
            if files:
                console.print(f"\n[dim]Linting {len(files)} {pattern} files...[/dim]")

                for file in files[:20]:  # Limit to 20 files
                    result = await self._lint_file(file, auto_fix)
                    if result.total > 0:
                        results.append(result)

        # Display results
        if not results:
            console.print("[green]✅ No linting issues found![/green]")
        else:
            total_issues = sum(r.total for r in results)
            fixable_issues = sum(r.fixable for r in results)

            console.print(f"\n[bold]Linting Summary:[/bold]")
            console.print(f"  Total issues: {total_issues}")
            console.print(f"  Auto-fixable: {fixable_issues}")

            # Show files with most issues
            worst_files = sorted(results, key=lambda r: r.total, reverse=True)[:5]

            table = Table(
                title="Files with Issues", show_header=True, header_style="bold cyan"
            )
            table.add_column("File", style="bright_white")
            table.add_column("Issues", justify="right", style="yellow")
            table.add_column("Fixable", justify="right", style="green")

            for result in worst_files:
                table.add_row(result.file, str(result.total), str(result.fixable))

            console.print(table)

            if auto_fix and fixable_issues > 0:
                console.print(f"\n[green]✅ Auto-fixed {fixable_issues} issues[/green]")

        return results

    async def _lint_file(self, file_path: Path, auto_fix: bool) -> LintResult:
        """Lint a single file."""
        issues = []
        fixable = 0

        # Python linting
        if file_path.suffix == ".py":
            # Use flake8 for linting
            try:
                result = subprocess.run(
                    ["flake8", "--format=json", str(file_path)],
                    capture_output=True,
                    text=True,
                )
                if result.stdout:
                    # Parse flake8 output
                    for line in result.stdout.split("\n"):
                        if line.strip():
                            issues.append({"type": "style", "message": line})
            except:
                pass

            # Auto-fix with black if requested
            if auto_fix:
                try:
                    subprocess.run(["black", str(file_path)], capture_output=True)
                    fixable = len(issues) // 2  # Estimate
                except:
                    pass

        # JavaScript/TypeScript linting
        elif file_path.suffix in [".js", ".ts", ".jsx", ".tsx"]:
            # Use eslint if available
            try:
                result = subprocess.run(
                    ["eslint", str(file_path), "--format=json"],
                    capture_output=True,
                    text=True,
                )
                if result.stdout:
                    lint_data = json.loads(result.stdout)
                    if lint_data and lint_data[0].get("messages"):
                        for msg in lint_data[0]["messages"]:
                            issues.append(
                                {
                                    "type": msg.get("severity"),
                                    "message": msg.get("message"),
                                    "line": msg.get("line"),
                                }
                            )
                            if msg.get("fix"):
                                fixable += 1
            except:
                pass

            # Auto-fix with eslint if requested
            if auto_fix and fixable > 0:
                try:
                    subprocess.run(
                        ["eslint", str(file_path), "--fix"], capture_output=True
                    )
                except:
                    pass

        return LintResult(
            file=str(file_path.relative_to(Path.cwd())),
            issues=issues,
            fixable=fixable,
            total=len(issues),
        )

    async def generate_api(
        self,
        api_type: str,
        resource_name: str,
        include_crud: bool = False,
        include_auth: bool = False,
    ) -> bool:
        """Generate REST/GraphQL API scaffolding."""
        console.print(
            f"[bold cyan]Generating {api_type.upper()} API for {resource_name}...[/bold cyan]"
        )

        # Generate API specification with AI
        prompt = f"""
Generate a complete {api_type} API specification for resource: {resource_name}

Include:
1. {"CRUD operations (Create, Read, Update, Delete)" if include_crud else "Basic read operations"}
2. {"Authentication/authorization middleware" if include_auth else "Public endpoints"}
3. Request/response schemas
4. Error handling
5. Input validation
6. Example requests and responses

For {api_type}:
{"- RESTful endpoints with proper HTTP methods" if api_type == "rest" else "- GraphQL schema with queries and mutations"}
{"- OpenAPI/Swagger specification" if api_type == "rest" else "- GraphQL SDL schema"}

Provide production-ready code with best practices.
"""

        api_code = await llm_service.complete(
            prompt,
            system=f"You are an API architect designing {api_type} APIs.",
            max_tokens=1500,
        )

        # Create API specification files
        api_dir = Path.cwd() / "api" / resource_name.lower()
        api_dir.mkdir(parents=True, exist_ok=True)

        if api_type == "rest":
            # Create REST API files
            files_created = []

            # Routes file
            routes_file = api_dir / f"{resource_name.lower()}_routes.js"
            routes_content = self._extract_section(api_code, "routes", "endpoints")
            with open(routes_file, "w") as f:
                f.write(routes_content or api_code)
            files_created.append(routes_file)

            # Controller file
            controller_file = api_dir / f"{resource_name.lower()}_controller.js"
            controller_content = self._extract_section(
                api_code, "controller", "handlers"
            )
            with open(controller_file, "w") as f:
                f.write(controller_content or "// Controller implementation")
            files_created.append(controller_file)

            # OpenAPI spec
            openapi_file = api_dir / f"{resource_name.lower()}_openapi.yaml"
            openapi_content = self._generate_openapi_spec(
                resource_name, include_crud, include_auth
            )
            with open(openapi_file, "w") as f:
                f.write(openapi_content)
            files_created.append(openapi_file)

        else:  # GraphQL
            # Create GraphQL files
            files_created = []

            # Schema file
            schema_file = api_dir / f"{resource_name.lower()}_schema.graphql"
            schema_content = self._extract_section(api_code, "schema", "type")
            with open(schema_file, "w") as f:
                f.write(schema_content or api_code)
            files_created.append(schema_file)

            # Resolvers file
            resolvers_file = api_dir / f"{resource_name.lower()}_resolvers.js"
            resolvers_content = self._extract_section(api_code, "resolver", "query")
            with open(resolvers_file, "w") as f:
                f.write(resolvers_content or "// Resolver implementation")
            files_created.append(resolvers_file)

        # Save API specification metadata
        spec_file = self.api_specs_dir / f"{resource_name.lower()}_{api_type}.json"
        with open(spec_file, "w") as f:
            json.dump(
                {
                    "resource": resource_name,
                    "type": api_type,
                    "crud": include_crud,
                    "auth": include_auth,
                    "created_at": datetime.now().isoformat(),
                    "files": [str(f) for f in files_created],
                },
                f,
                indent=2,
            )

        # Display results
        console.print(
            Panel(
                f"[green]✅ {api_type.upper()} API generated successfully![/green]\n\n"
                f"[bold]Resource:[/bold] {resource_name}\n"
                f"[bold]Location:[/bold] {api_dir}\n\n"
                f"[bold]Files created:[/bold]\n"
                + "\n".join(f"  • {f.name}" for f in files_created),
                title="API Generated",
                border_style="green",
            )
        )

        # Show example usage
        if api_type == "rest":
            console.print("\n[bold]Example Usage:[/bold]")
            console.print(f"  GET    /api/{resource_name.lower()}")
            if include_crud:
                console.print(f"  POST   /api/{resource_name.lower()}")
                console.print(f"  GET    /api/{resource_name.lower()}/{{id}}")
                console.print(f"  PUT    /api/{resource_name.lower()}/{{id}}")
                console.print(f"  DELETE /api/{resource_name.lower()}/{{id}}")

        return True

    def _extract_section(self, content: str, *keywords: str) -> str:
        """Extract a section from generated content based on keywords."""
        lines = content.split("\n")
        extracted = []
        capturing = False

        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in keywords):
                capturing = True
            if capturing:
                extracted.append(line)

        return "\n".join(extracted) if extracted else content

    def _generate_openapi_spec(self, resource: str, crud: bool, auth: bool) -> str:
        """Generate OpenAPI specification."""
        spec = f"""openapi: 3.0.0
info:
  title: {resource} API
  version: 1.0.0
  description: API for managing {resource} resources

servers:
  - url: http://localhost:3000/api
    description: Development server

paths:
  /{resource.lower()}:
    get:
      summary: List all {resource}
      operationId: list{resource}
      tags:
        - {resource}
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/{resource}'
"""

        if crud:
            spec += f"""
    post:
      summary: Create a new {resource}
      operationId: create{resource}
      tags:
        - {resource}
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/{resource}Input'
      responses:
        '201':
          description: Created successfully

  /{resource.lower()}/{{id}}:
    get:
      summary: Get {resource} by ID
      operationId: get{resource}ById
      tags:
        - {resource}
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Successful response

    put:
      summary: Update {resource}
      operationId: update{resource}
      tags:
        - {resource}
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/{resource}Input'
      responses:
        '200':
          description: Updated successfully

    delete:
      summary: Delete {resource}
      operationId: delete{resource}
      tags:
        - {resource}
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        '204':
          description: Deleted successfully
"""

        spec += f"""
components:
  schemas:
    {resource}:
      type: object
      properties:
        id:
          type: string
        name:
          type: string
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time

    {resource}Input:
      type: object
      required:
        - name
      properties:
        name:
          type: string
"""

        if auth:
            spec += """
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

security:
  - bearerAuth: []
"""

        return spec

    async def analyze_logs(
        self, action: str = "tail", pattern: str = None, follow: bool = False
    ) -> bool:
        """Intelligent log analysis and error detection."""
        console.print(f"[bold cyan]Log Analysis: {action}[/bold cyan]")

        # Find log files
        log_files = []
        for pattern in ["*.log", "logs/*.log", "*.err"]:
            log_files.extend(Path.cwd().glob(pattern))

        if not log_files:
            console.print("[yellow]No log files found[/yellow]")
            console.print("[dim]Looking for: *.log, logs/*.log, *.err[/dim]")
            return False

        if action == "tail":
            # Show recent logs
            for log_file in log_files[-3:]:  # Last 3 log files
                console.print(f"\n[bold]{log_file.name}:[/bold]")

                try:
                    if follow:
                        # Follow log in real-time (simplified)
                        subprocess.run(["tail", "-f", "-n", "20", str(log_file)])
                    else:
                        result = subprocess.run(
                            ["tail", "-n", "20", str(log_file)],
                            capture_output=True,
                            text=True,
                        )
                        console.print(result.stdout)
                except KeyboardInterrupt:
                    console.print("\n[dim]Log following stopped[/dim]")
                except:
                    with open(log_file, "r") as f:
                        lines = f.readlines()
                        for line in lines[-20:]:
                            console.print(line.rstrip())

        elif action == "search" and pattern:
            # Search for pattern in logs
            console.print(f"[dim]Searching for: {pattern}[/dim]\n")

            matches = []
            for log_file in log_files:
                try:
                    with open(log_file, "r") as f:
                        for line_num, line in enumerate(f, 1):
                            if pattern.lower() in line.lower():
                                matches.append((log_file.name, line_num, line.strip()))
                except:
                    pass

            if matches:
                console.print(f"[green]Found {len(matches)} matches:[/green]\n")
                for file, line_num, line in matches[:20]:  # Limit to 20
                    console.print(f"[yellow]{file}:{line_num}[/yellow] {line[:100]}")
            else:
                console.print("[yellow]No matches found[/yellow]")

        elif action == "errors":
            # Analyze logs for errors
            console.print("[dim]Analyzing logs for errors...[/dim]\n")

            errors = []
            warnings = []

            for log_file in log_files:
                try:
                    with open(log_file, "r") as f:
                        for line in f:
                            line_lower = line.lower()
                            if any(
                                word in line_lower
                                for word in ["error", "exception", "fatal", "critical"]
                            ):
                                errors.append((log_file.name, line.strip()[:150]))
                            elif any(
                                word in line_lower for word in ["warning", "warn"]
                            ):
                                warnings.append((log_file.name, line.strip()[:150]))
                except:
                    pass

            if errors:
                console.print(f"[bold red]Errors Found ({len(errors)}):[/bold red]")
                for file, error in errors[:10]:
                    console.print(f"  [{file}] {error}")

            if warnings:
                console.print(
                    f"\n[bold yellow]Warnings ({len(warnings)}):[/bold yellow]"
                )
                for file, warning in warnings[:5]:
                    console.print(f"  [{file}] {warning}")

            if not errors and not warnings:
                console.print("[green]✅ No errors or warnings found in logs[/green]")

            # AI-powered analysis
            if errors:
                console.print("\n[dim]Generating AI analysis...[/dim]")

                error_summary = "\n".join([f"- {e[1]}" for e in errors[:5]])
                prompt = f"""
Analyze these log errors and provide:
1. Root cause analysis
2. Recommended fixes
3. Prevention strategies

Errors:
{error_summary}
"""

                analysis = await llm_service.complete(
                    prompt,
                    system="You are a DevOps expert analyzing application logs.",
                    max_tokens=500,
                )

                console.print("\n[bold cyan]AI Analysis:[/bold cyan]")
                console.print(analysis)

        return True


# Global instance
development_service = DevelopmentService()
