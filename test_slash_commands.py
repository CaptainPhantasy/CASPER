#!/usr/bin/env python3
"""
Direct Slash Command Test Suite with Visual Output and Logging
Tests commands directly through the SlashCommandHandler
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import io
from contextlib import redirect_stdout, redirect_stderr

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich import box
from rich.text import Text

# Import the slash command handler
from core.services.slash_commands import SlashCommandRegistry
from core.cli import CasperCLI

console = Console()

class SlashCommandTester:
    """Visual test runner for slash commands with comprehensive logging"""

    def __init__(self):
        self.handler = SlashCommandRegistry()
        self.cli = CasperCLI()
        self.handler.casper_cli = self.cli  # Connect CLI context
        self.results = []
        self.log_file = f".casper/test_logs/slash_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        Path(".casper/test_logs").mkdir(parents=True, exist_ok=True)

    def get_test_commands(self) -> List[Dict]:
        """Define comprehensive test suite for all commands"""
        return [
            # ===== SYSTEM COMMANDS =====
            {"cmd": "help", "args": "", "category": "System", "expect_success": True, "expect_output": "commands"},
            {"cmd": "help", "args": "Git", "category": "System", "expect_success": True, "expect_output": "Git"},
            {"cmd": "status", "args": "", "category": "System", "expect_success": True, "expect_output": "Status"},
            {"cmd": "config", "args": "show", "category": "System", "expect_success": True, "expect_output": "config"},

            # ===== TASK MANAGEMENT =====
            {"cmd": "todo", "args": "Test task from visual suite", "category": "Tasks", "expect_success": True, "expect_output": "added"},
            {"cmd": "todo", "args": "list", "category": "Tasks", "expect_success": True, "expect_output": "ID"},
            {"cmd": "todo", "args": "done 1", "category": "Tasks", "expect_success": True, "expect_output": "completed"},

            # ===== DEVELOPMENT COMMANDS =====
            {"cmd": "explain", "args": "What is a Python decorator?", "category": "Dev", "expect_success": True, "expect_output": "decorator"},
            {"cmd": "newcomponent", "args": "TestButton --type react", "category": "Dev", "expect_success": True, "expect_output": "component"},
            {"cmd": "addroute", "args": "/test TestPage", "category": "Dev", "expect_success": True, "expect_output": "route"},
            {"cmd": "gen", "args": "User --api", "category": "Dev", "expect_success": True, "expect_output": "generat"},
            {"cmd": "refactor", "args": "test.py", "category": "Dev", "expect_success": True, "expect_output": "refactor"},

            # ===== GIT COMMANDS =====
            {"cmd": "commit", "args": "", "category": "Git", "expect_success": True, "expect_output": "commit"},
            {"cmd": "pr", "args": "Test PR", "category": "Git", "expect_success": True, "expect_output": "pull request"},
            {"cmd": "review", "args": "", "category": "Git", "expect_success": True, "expect_output": "review"},
            {"cmd": "fixbug", "args": "Test bug fix", "category": "Git", "expect_success": True, "expect_output": "bug fix"},
            {"cmd": "standup", "args": "", "category": "Git", "expect_success": True, "expect_output": "Standup"},

            # ===== TESTING COMMANDS =====
            {"cmd": "test", "args": "", "category": "Testing", "expect_success": True, "expect_output": "test"},
            {"cmd": "testfail", "args": "", "category": "Testing", "expect_success": True, "expect_output": "test"},
            {"cmd": "lint", "args": "", "category": "Testing", "expect_success": True, "expect_output": "lint"},
            {"cmd": "debug", "args": "test.py", "category": "Testing", "expect_success": True, "expect_output": "debug"},

            # ===== WORKFLOW COMMANDS =====
            {"cmd": "sync", "args": "", "category": "Workflow", "expect_success": True, "expect_output": "sync"},
            {"cmd": "deploy", "args": "staging", "category": "Workflow", "expect_success": True, "expect_output": "deploy"},

            # ===== ERROR CASES =====
            {"cmd": "nonexistent", "args": "", "category": "Errors", "expect_success": False, "expect_output": "Unknown command"},
            {"cmd": "todo", "args": "invalid_action", "category": "Errors", "expect_success": True, "expect_output": "Usage"},
        ]

    async def test_command(self, cmd: str, args: str) -> Tuple[bool, str, float]:
        """Execute a single command and capture output"""
        start_time = time.time()

        # Capture output
        output_buffer = io.StringIO()
        error_buffer = io.StringIO()

        try:
            # Create a console that writes to our buffer
            test_console = Console(file=output_buffer, force_terminal=True)

            # Temporarily replace the handler's console
            original_console = self.handler.console
            self.handler.console = test_console

            # Execute command
            full_command = f"/{cmd} {args}".strip()
            result = await self.handler.handle_command(full_command)

            # Restore original console
            self.handler.console = original_console

            output = output_buffer.getvalue()
            execution_time = time.time() - start_time

            return result if result is not None else True, output, execution_time

        except Exception as e:
            execution_time = time.time() - start_time
            return False, f"Error: {str(e)}", execution_time

    def display_header(self):
        """Display test suite header"""
        header = Panel.fit(
            "[bold cyan]🧪 CASPER Slash Commands Visual Test Suite[/bold cyan]\n"
            "[dim]Testing all CLI commands with real-time visual feedback[/dim]\n"
            f"[yellow]Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/yellow]",
            box=box.DOUBLE,
            border_style="cyan"
        )
        console.print(header)
        console.print()

    def display_test_progress(self, cmd: str, args: str, index: int, total: int):
        """Display current test being executed"""
        console.print(f"[dim]Test {index}/{total}:[/dim] [cyan]/{cmd}[/cyan] {args}")

    def display_test_result(self, cmd: str, args: str, success: bool, output: str, exec_time: float, expected: bool):
        """Display individual test result with visual indicators"""
        # Determine pass/fail
        passed = success == expected
        status_icon = "✅" if passed else "❌"
        status_color = "green" if passed else "red"

        # Create result display
        result_panel = Panel(
            f"[bold]Command:[/bold] [cyan]/{cmd} {args}[/cyan]\n"
            f"[bold]Expected:[/bold] {'Success' if expected else 'Failure'}\n"
            f"[bold]Actual:[/bold] {'Success' if success else 'Failure'}\n"
            f"[bold]Time:[/bold] {exec_time:.3f}s\n"
            f"[bold]Output Preview:[/bold]\n[dim]{output[:150]}{'...' if len(output) > 150 else ''}[/dim]",
            title=f"{status_icon} Test Result",
            border_style=status_color,
            expand=False
        )
        console.print(result_panel)
        console.print()

    async def run_visual_tests(self):
        """Execute all tests with visual feedback"""
        self.display_header()

        # Initialize CLI
        console.print("[cyan]🔧 Initializing CASPER CLI...[/cyan]")
        await self.cli.initialize()
        console.print("[green]✅ CLI initialized[/green]\n")

        # Get test commands
        tests = self.get_test_commands()
        total_tests = len(tests)

        # Statistics
        passed = 0
        failed = 0

        # Group by category
        categories = {}
        for test in tests:
            cat = test["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(test)

        # Run tests with progress
        test_index = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:

            task = progress.add_task("[cyan]Running tests...", total=total_tests)

            for category, cat_tests in categories.items():
                console.print(f"\n[bold yellow]━━━ {category} Commands ━━━[/bold yellow]\n")

                for test in cat_tests:
                    test_index += 1

                    # Update progress
                    progress.update(task, description=f"Testing /{test['cmd']}...")

                    # Run test
                    success, output, exec_time = await self.test_command(
                        test["cmd"],
                        test["args"]
                    )

                    # Check expectations
                    expected_success = test["expect_success"]
                    expected_output = test["expect_output"].lower()

                    # Verify output contains expected text
                    output_matches = expected_output in output.lower() if expected_output else True
                    test_passed = (success == expected_success) and output_matches

                    # Display result
                    self.display_test_result(
                        test["cmd"],
                        test["args"],
                        success,
                        output,
                        exec_time,
                        expected_success
                    )

                    # Log result
                    result = {
                        "command": f"/{test['cmd']} {test['args']}".strip(),
                        "category": category,
                        "success": success,
                        "expected_success": expected_success,
                        "output_matches": output_matches,
                        "test_passed": test_passed,
                        "execution_time": exec_time,
                        "output": output[:500],
                        "timestamp": datetime.now().isoformat()
                    }
                    self.results.append(result)

                    # Update counters
                    if test_passed:
                        passed += 1
                    else:
                        failed += 1

                    # Update progress
                    progress.update(task, advance=1)

                    # Brief pause for visual effect
                    await asyncio.sleep(0.3)

        # Display final summary
        self.display_summary(passed, failed, total_tests)

        # Save results
        self.save_results()

        # Shutdown CLI
        await self.cli.shutdown()

    def display_summary(self, passed: int, failed: int, total: int):
        """Display comprehensive test summary"""
        console.print("\n")
        console.rule("[bold cyan]📊 Test Summary[/bold cyan]")
        console.print()

        # Overall statistics
        success_rate = (passed / total) * 100 if total > 0 else 0

        summary_table = Table(
            title="Overall Results",
            show_header=True,
            header_style="bold magenta",
            box=box.ROUNDED
        )
        summary_table.add_column("Metric", style="cyan", width=20)
        summary_table.add_column("Value", justify="right", style="white")

        summary_table.add_row("Total Tests", str(total))
        summary_table.add_row("✅ Passed", f"[green]{passed}[/green]")
        summary_table.add_row("❌ Failed", f"[red]{failed}[/red]")
        summary_table.add_row("Success Rate", f"[{'green' if success_rate >= 80 else 'yellow' if success_rate >= 60 else 'red'}]{success_rate:.1f}%")

        console.print(summary_table)
        console.print()

        # Category breakdown
        cat_stats = {}
        for result in self.results:
            cat = result["category"]
            if cat not in cat_stats:
                cat_stats[cat] = {"passed": 0, "failed": 0, "total": 0}

            cat_stats[cat]["total"] += 1
            if result["test_passed"]:
                cat_stats[cat]["passed"] += 1
            else:
                cat_stats[cat]["failed"] += 1

        cat_table = Table(
            title="Results by Category",
            show_header=True,
            header_style="bold cyan",
            box=box.SIMPLE
        )
        cat_table.add_column("Category", style="yellow", width=15)
        cat_table.add_column("Passed", justify="center", style="green")
        cat_table.add_column("Failed", justify="center", style="red")
        cat_table.add_column("Total", justify="center")
        cat_table.add_column("Rate", justify="center")

        for cat, stats in cat_stats.items():
            rate = (stats["passed"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            cat_table.add_row(
                cat,
                str(stats["passed"]),
                str(stats["failed"]),
                str(stats["total"]),
                f"{rate:.0f}%"
            )

        console.print(cat_table)

        # List failed tests if any
        if failed > 0:
            console.print("\n[bold red]❌ Failed Tests:[/bold red]")
            for result in self.results:
                if not result["test_passed"]:
                    console.print(f"  • {result['command']} - {result['category']}")

    def save_results(self):
        """Save test results to JSON log"""
        with open(self.log_file, 'w') as f:
            json.dump({
                "test_run": datetime.now().isoformat(),
                "total_tests": len(self.results),
                "passed": sum(1 for r in self.results if r["test_passed"]),
                "failed": sum(1 for r in self.results if not r["test_passed"]),
                "results": self.results
            }, f, indent=2)

        console.print(f"\n[green]📝 Results saved to: {self.log_file}[/green]")

        # Generate HTML report
        html_file = self.log_file.replace('.json', '.html')
        self.generate_html_report(html_file)
        console.print(f"[green]📊 HTML report: {html_file}[/green]")

    def generate_html_report(self, filename: str):
        """Generate an HTML report of test results"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>CASPER CLI Test Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }}
        h1 {{ color: #16c79a; }}
        .summary {{ background: #0f3460; padding: 20px; border-radius: 10px; margin: 20px 0; }}
        .passed {{ color: #16c79a; font-weight: bold; }}
        .failed {{ color: #e94560; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; background: #0f3460; }}
        th {{ background: #16213e; padding: 10px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #16213e; }}
        tr:hover {{ background: #1a1a2e; }}
        .command {{ color: #00d9ff; font-family: monospace; }}
    </style>
</head>
<body>
    <h1>🧪 CASPER CLI Test Report</h1>
    <div class="summary">
        <h2>Summary</h2>
        <p>Test Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Total Tests: {len(self.results)}</p>
        <p class="passed">Passed: {sum(1 for r in self.results if r['test_passed'])}</p>
        <p class="failed">Failed: {sum(1 for r in self.results if not r['test_passed'])}</p>
    </div>
    <h2>Test Results</h2>
    <table>
        <tr>
            <th>Command</th>
            <th>Category</th>
            <th>Result</th>
            <th>Time (s)</th>
        </tr>
"""

        for result in self.results:
            status = "✅" if result['test_passed'] else "❌"
            html_content += f"""
        <tr>
            <td class="command">{result['command']}</td>
            <td>{result['category']}</td>
            <td>{status}</td>
            <td>{result['execution_time']:.3f}</td>
        </tr>
"""

        html_content += """
    </table>
</body>
</html>
"""

        with open(filename, 'w') as f:
            f.write(html_content)

async def main():
    """Run the visual test suite"""
    tester = SlashCommandTester()

    try:
        await tester.run_visual_tests()
        console.print("\n[bold green]✅ Test suite completed successfully![/bold green]")
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Test suite interrupted[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Test suite error: {str(e)}[/red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())