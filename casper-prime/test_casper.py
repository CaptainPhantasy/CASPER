#!/usr/bin/env python3
"""
CASPER Prime Test Script - Verify the system works
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
from core.agents.master_prime import MasterPrimeAgent
from core.context.manager import ContextManager
from rich.console import Console
from rich.panel import Panel

console = Console()


async def test_casper_prime():
    """Test CASPER Prime with a simple task"""
    
    console.print(Panel.fit(
        "[bold cyan]CASPER Prime Test[/bold cyan]\n"
        "Testing autonomous AI development platform",
        border_style="cyan"
    ))
    
    # Create a test task
    task = "Build a simple REST API endpoint for user registration with email validation"
    
    console.print(f"\n[bold]Task:[/bold] {task}\n")
    
    try:
        # Initialize the Master Prime agent
        console.print("[yellow]Initializing Master Prime Agent...[/yellow]")
        master = MasterPrimeAgent()
        
        # Analyze the task
        console.print("[yellow]Analyzing task complexity...[/yellow]")
        analysis = await master.analyze_task(task)
        
        console.print("\n[green]✓ Task Analysis Complete![/green]")
        console.print(f"  • Complexity: {analysis.complexity}")
        console.print(f"  • Estimated time: {analysis.estimated_time}")
        console.print(f"  • Required agents: {', '.join([a.value for a in analysis.required_agents])}")
        
        # Test context creation
        console.print("\n[yellow]Testing context management...[/yellow]")
        context_manager = ContextManager()
        context = await context_manager.create_initial_context(task)
        
        console.print("[green]✓ Context created successfully![/green]")
        console.print(f"  • Session ID: {context.session_id}")
        console.print(f"  • Token budget: {context.token_limit}")
        
        # Test agent spawning (without actual execution)
        console.print("\n[yellow]Testing agent spawning logic...[/yellow]")
        spawned_agents = await master.spawn_agents(analysis)
        
        console.print("[green]✓ Agent spawning successful![/green]")
        for agent in spawned_agents:
            console.print(f"  • {agent.name} ({agent.role.value}) - Ready")
        
        console.print("\n[bold green]✅ CASPER Prime is working correctly![/bold green]")
        console.print("\nYou can now use the system to delegate complex development tasks!")
        
        return True
        
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        console.print("\nPlease check:")
        console.print("  1. API keys are set in .env file")
        console.print("  2. All dependencies are installed")
        console.print("  3. Import paths are correct")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_casper_prime())
    sys.exit(0 if success else 1)
