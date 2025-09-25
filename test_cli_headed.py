#!/usr/bin/env python3
"""
CASPER CLI Headed Test Suite
Executes all CLI commands with visual output and comprehensive logging
"""

import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import os

# Rich for beautiful console output
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.live import Live
from rich.layout import Layout
from rich import box
from rich.text import Text

console = Console()

class CLITestRunner:
    """Headed test runner for CASPER CLI commands with visual feedback"""

    def __init__(self):
        self.results = []
        self.log_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.console = Console(record=True)
        self.test_commands = self._get_test_commands()

    def _get_test_commands(self) -> List[Dict]:
        """Define all CLI commands to test with their expected behaviors"""
        return [
            # System Commands
            {"cmd": "/help", "category": "System", "expect": "Available commands", "timeout": 5},
            {"cmd": "/help Git", "category": "System", "expect": "Git commands", "timeout": 5},
            {"cmd": "/status", "category": "System", "expect": "System Status", "timeout": 5},
            {"cmd": "/config show", "category": "System", "expect": "Configuration", "timeout": 5},

            # Task Management
            {"cmd": '/todo "Test task from headed test"', "category": "Tasks", "expect": "Todo added", "timeout": 5},
            {"cmd": "/todo list", "category": "Tasks", "expect": "ID", "timeout": 5},
            {"cmd": "/todo done 1", "category": "Tasks", "expect": "marked as completed", "timeout": 5},

            # Development Commands
            {"cmd": '/explain "What is a closure?"', "category": "Development", "expect": "closure", "timeout": 10},
            {"cmd": "/newcomponent TestComponent --type react", "category": "Development", "expect": "Component", "timeout": 8},
            {"cmd": "/addroute /test TestPage", "category": "Development", "expect": "route", "timeout": 8},

            # Git Commands
            {"cmd": "/commit", "category": "Git", "expect": "commit", "timeout": 10},
            {"cmd": "/standup", "category": "Git", "expect": "Standup Summary", "timeout": 8},
            {"cmd": "/review", "category": "Git", "expect": "review", "timeout": 10},

            # Testing Commands
            {"cmd": "/test", "category": "Testing", "expect": "test", "timeout": 15},
            {"cmd": "/lint", "category": "Testing", "expect": "lint", "timeout": 10},
            {"cmd": "/debug main.py", "category": "Testing", "expect": "debug", "timeout": 8},

            # Workflow Commands
            {"cmd": "/sync", "category": "Workflow", "expect": "sync", "timeout": 10},
            {"cmd": '/fixbug "Test bug"', "category": "Workflow", "expect": "bug fix workflow", "timeout": 8},
            {"cmd": "/deploy staging", "category": "Workflow", "expect": "deployment", "timeout": 10},

            # Code Generation
            {"cmd": "/gen TestFeature --api", "category": "CodeGen", "expect": "generat", "timeout": 10},
            {"cmd": "/refactor test.py", "category": "CodeGen", "expect": "refactor", "timeout": 10},

            # Session Management
            {"cmd": "/save test_session", "category": "Session", "expect": "session", "timeout": 5},
            {"cmd": "/sessions", "category": "Session", "expect": "session", "timeout": 5},
        ]

    def create_test_environment(self):
        """Set up test environment with necessary files"""
        self.console.print("[cyan]🔧 Setting up test environment...[/cyan]")

        # Create test files if they don't exist
        test_files = [
            ("test.py", "def test_function():\n    return 'test'"),
            ("main.py", "if __name__ == '__main__':\n    print('main')"),
            (".env", "TEST_VAR=test_value"),
        ]

        for filename, content in test_files:
            if not Path(filename).exists():
                Path(filename).write_text(content)
                self.console.print(f"  ✅ Created {filename}")

    def run_command(self, command: str, timeout: int = 10) -> Tuple[bool, str, float]:
        """
        Execute a CLI command and capture output
        Returns: (success, output, execution_time)
        """
        start_time = time.time()

        try:
            # Use echo to pipe command to CLI
            process = subprocess.Popen(
                ["python3", "-m", "core.cli"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Send command and close stdin
            stdout, stderr = process.communicate(input=command + "\n", timeout=timeout)
            execution_time = time.time() - start_time

            output = stdout + stderr
            success = process.returncode == 0 or "Error" not in output

            return success, output, execution_time

        except subprocess.TimeoutExpired:
            process.kill()
            return False, "Command timed out", timeout
        except Exception as e:
            return False, str(e), time.time() - start_time

    def display_test_header(self):
        """Display test suite header"""
        header = Panel.fit(
            "[bold cyan]CASPER CLI Headed Test Suite[/bold cyan]\n"
            "[dim]Visual testing of all CLI commands with logging[/dim]",
            box=box.DOUBLE,
            border_style="cyan"
        )
        self.console.print(header)
        self.console.print()

    def display_category_header(self, category: str):
        """Display category section header"""
        self.console.print()
        self.console.rule(f"[bold yellow]{category} Commands[/bold yellow]")
        self.console.print()

    def display_test_result(self, cmd: str, success: bool, output: str, exec_time: float):
        """Display individual test result with visual feedback"""
        status = "[green]✅ PASS[/green]" if success else "[red]❌ FAIL[/red]"

        # Create result panel
        result_text = Text()
        result_text.append(f"Command: ", style="bold")
        result_text.append(f"{cmd}\n", style="cyan")
        result_text.append(f"Status: {status}\n")
        result_text.append(f"Time: ", style="bold")
        result_text.append(f"{exec_time:.2f}s\n", style="yellow")

        # Add output preview (first 200 chars)
        if output:
            preview = output[:200].replace('\n', ' ')
            if len(output) > 200:
                preview += "..."
            result_text.append(f"Output: ", style="bold")
            result_text.append(f"{preview}", style="dim")

        panel = Panel(
            result_text,
            title=f"Test #{len(self.results) + 1}",
            border_style="green" if success else "red",
            expand=False
        )

        self.console.print(panel)

    async def run_test_suite(self):
        """Execute all tests with visual progress"""
        self.display_test_header()
        self.create_test_environment()

        self.console.print("\n[bold cyan]📊 Starting Test Execution[/bold cyan]\n")

        # Group commands by category
        categories = {}
        for test in self.test_commands:
            cat = test["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(test)

        total_tests = len(self.test_commands)
        passed = 0
        failed = 0

        # Progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console
        ) as progress:

            task = progress.add_task("[cyan]Running tests...", total=total_tests)

            for category, tests in categories.items():
                self.display_category_header(category)

                for test in tests:
                    cmd = test["cmd"]
                    expect = test["expect"]
                    timeout = test["timeout"]

                    # Update progress
                    progress.update(task, description=f"Testing: {cmd[:30]}...")

                    # Run command
                    success, output, exec_time = self.run_command(cmd, timeout)

                    # Check for expected output
                    if expect and expect.lower() not in output.lower():
                        success = False

                    # Display result
                    self.display_test_result(cmd, success, output, exec_time)

                    # Log result
                    result = {
                        "command": cmd,
                        "category": category,
                        "success": success,
                        "execution_time": exec_time,
                        "output": output[:1000],  # Limit output in logs
                        "timestamp": datetime.now().isoformat()
                    }
                    self.results.append(result)

                    if success:
                        passed += 1
                    else:
                        failed += 1

                    # Update progress
                    progress.update(task, advance=1)

                    # Brief pause for visual effect
                    await asyncio.sleep(0.5)

        # Display summary
        self.display_summary(passed, failed, total_tests)

        # Save results
        self.save_results()

    def display_summary(self, passed: int, failed: int, total: int):
        """Display test summary with statistics"""
        self.console.print("\n")
        self.console.rule("[bold cyan]Test Summary[/bold cyan]")

        # Create summary table
        table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Value", justify="right")

        table.add_row("Total Tests", str(total))
        table.add_row("Passed", f"[green]{passed}[/green]")
        table.add_row("Failed", f"[red]{failed}[/red]")
        table.add_row("Success Rate", f"{(passed/total)*100:.1f}%")

        # Category breakdown
        category_stats = {}
        for result in self.results:
            cat = result["category"]
            if cat not in category_stats:
                category_stats[cat] = {"passed": 0, "failed": 0}

            if result["success"]:
                category_stats[cat]["passed"] += 1
            else:
                category_stats[cat]["failed"] += 1

        self.console.print(table)
        self.console.print()

        # Category results
        cat_table = Table(
            title="Results by Category",
            show_header=True,
            header_style="bold cyan",
            box=box.SIMPLE
        )
        cat_table.add_column("Category", style="yellow")
        cat_table.add_column("Passed", justify="center", style="green")
        cat_table.add_column("Failed", justify="center", style="red")

        for cat, stats in category_stats.items():
            cat_table.add_row(
                cat,
                str(stats["passed"]),
                str(stats["failed"])
            )

        self.console.print(cat_table)

        # Failed commands list
        if failed > 0:
            self.console.print("\n[bold red]Failed Commands:[/bold red]")
            for result in self.results:
                if not result["success"]:
                    self.console.print(f"  • {result['command']}")

    def save_results(self):
        """Save test results to JSON log file"""
        log_dir = Path(".casper/test_logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        log_path = log_dir / self.log_file

        with open(log_path, 'w') as f:
            json.dump({
                "test_run": datetime.now().isoformat(),
                "total_tests": len(self.results),
                "passed": sum(1 for r in self.results if r["success"]),
                "failed": sum(1 for r in self.results if not r["success"]),
                "results": self.results
            }, f, indent=2)

        self.console.print(f"\n[green]📝 Results saved to: {log_path}[/green]")

        # Also save HTML report
        html_path = log_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        self.console.save_html(str(html_path))
        self.console.print(f"[green]📊 HTML report saved to: {html_path}[/green]")

async def main():
    """Main test execution"""
    runner = CLITestRunner()

    try:
        await runner.run_test_suite()
        console.print("\n[bold green]✅ Test suite completed successfully![/bold green]")
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Test suite interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Test suite failed: {str(e)}[/red]")
        raise

if __name__ == "__main__":
    # Set environment for testing
    os.environ["CASPER_TEST_MODE"] = "true"

    # Run the test suite
    asyncio.run(main())