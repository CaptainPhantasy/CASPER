#!/usr/bin/env python
"""
CASPER Prime Demo - Watch AI agents build code autonomously
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project to the path
sys.path.insert(0, '/Volumes/Storage/Development/CASPER DEV')

from core.agents.master_prime import MasterPrimeAgent
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax

console = Console()

async def demo_casper():
    """Demonstrate CASPER Prime's autonomous development capabilities"""
    
    console.print(Panel.fit(
        "[bold cyan]🚀 CASPER Prime Demo[/bold cyan]\n"
        "Watch AI agents autonomously build code!",
        border_style="cyan"
    ))
    
    # Initialize Master Prime
    master = MasterPrimeAgent(project_root=Path.cwd())
    
    # Demo tasks to execute
    demo_tasks = [
        {
            "description": "Create a REST API endpoint for user registration with email validation",
            "type": "backend"
        },
        {
            "description": "Build a React component for displaying user profiles with edit capability",
            "type": "frontend"
        },
        {
            "description": "Generate comprehensive unit tests for a shopping cart module",
            "type": "testing"
        }
    ]
    
    for i, task_info in enumerate(demo_tasks, 1):
        console.print(f"\n[bold]Demo Task {i}:[/bold] {task_info['description']}")
        console.print(f"[dim]Type: {task_info['type']}[/dim]\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Analyze the task
            analyze_task = progress.add_task("[cyan]Analyzing task complexity...", total=None)
            analysis = await master.analyze_task(task_info["description"])
            progress.update(analyze_task, completed=100)
            
            # Display analysis
            console.print("[green]✓ Analysis Complete[/green]")
            console.print(f"  • Complexity: {analysis.get('complexity', 'unknown')}")
            console.print(f"  • Estimated tokens: {analysis.get('estimated_tokens', 0)}")
            console.print(f"  • Required agents: {len(analysis.get('required_agents', []))}")
            
            # Cost estimation
            estimated_cost = (analysis.get('estimated_tokens', 0) / 1000) * 0.003
            console.print(f"  • Estimated cost: ${estimated_cost:.2f}\n")
            
            # Execute task (in demo mode, we'll just show what would happen)
            if i == 1:  # Only execute the first task as a real demo
                console.print("[yellow]Executing first task as demonstration...[/yellow]")
                
                execute_task = progress.add_task("[cyan]Spawning agents and generating code...", total=None)
                
                # Actually execute the task
                result = await master.execute_task(task_info["description"])
                progress.update(execute_task, completed=100)
                
                if result.success:
                    console.print("[bold green]✅ Task Completed![/bold green]")
                    console.print(f"Duration: {result.duration_seconds:.1f} seconds")
                    console.print(f"Tokens used: {result.token_usage}")
                    
                    # Show generated code snippet
                    if result.output and isinstance(result.output, dict):
                        results = result.output.get('results', [])
                        if results and len(results) > 0:
                            first_result = results[0]
                            if hasattr(first_result, 'output') and first_result.output:
                                code = first_result.output.get('code', '')
                                if code:
                                    console.print("\n[bold]Generated Code Preview:[/bold]")
                                    # Show first 20 lines of generated code
                                    code_lines = code.split('\n')[:20]
                                    code_preview = '\n'.join(code_lines)
                                    if len(code.split('\n')) > 20:
                                        code_preview += '\n// ... more code ...'
                                    
                                    syntax = Syntax(code_preview, "javascript", theme="monokai", line_numbers=True)
                                    console.print(syntax)
                else:
                    console.print(f"[red]Task failed: {result.error}[/red]")
            else:
                console.print("[dim]Skipping execution (demo mode)[/dim]")
        
        if i < len(demo_tasks):
            console.print("\n" + "─" * 50)
    
    # Summary
    console.print(Panel.fit(
        "[bold green]🎉 Demo Complete![/bold green]\n\n"
        "CASPER Prime demonstrated:\n"
        "• Task analysis and complexity assessment\n"
        "• Agent spawning and coordination\n"
        "• Autonomous code generation\n"
        "• Token usage and cost tracking\n\n"
        "[yellow]Ready to build your own projects![/yellow]",
        title="Summary",
        border_style="green"
    ))

if __name__ == "__main__":
    console.print("\n[bold]Starting CASPER Prime Demo...[/bold]\n")
    asyncio.run(demo_casper())
