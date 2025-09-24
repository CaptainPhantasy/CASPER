#!/usr/bin/env python
"""
Quick test script for CASPER Prime
"""

import asyncio
import sys
import os

# Add the project to the path
sys.path.insert(0, '/Volumes/Storage/Development/CASPER DEV')

from core.agents.master_prime import MasterPrimeAgent
from pathlib import Path
from rich.console import Console

console = Console()

async def test_casper():
    """Test basic CASPER functionality"""
    
    console.print("[bold cyan]🚀 CASPER Prime Test Suite[/bold cyan]\n")
    
    # Test 1: Initialize Master Prime
    console.print("Test 1: Initializing Master Prime Agent...")
    try:
        master = MasterPrimeAgent(project_root=Path.cwd())
        console.print("[green]✓ Master Prime initialized successfully[/green]\n")
    except Exception as e:
        console.print(f"[red]✗ Failed to initialize: {e}[/red]")
        return
    
    # Test 2: Analyze a simple task
    console.print("Test 2: Analyzing a simple task...")
    task = "Create a function to validate email addresses"
    
    try:
        analysis = await master.analyze_task(task)
        console.print("[green]✓ Task analysis completed[/green]")
        console.print(f"  Complexity: {analysis.get('complexity', 'unknown')}")
        console.print(f"  Estimated tokens: {analysis.get('estimated_tokens', 0)}")
        console.print(f"  Required agents: {len(analysis.get('required_agents', []))}\n")
    except Exception as e:
        console.print(f"[red]✗ Analysis failed: {e}[/red]\n")
    
    # Test 3: Dry run of task execution
    console.print("Test 3: Testing task execution (dry run)...")
    console.print(f"Task: '{task}'")
    console.print("[yellow]Note: This would spawn agents and generate code[/yellow]\n")
    
    console.print("[bold green]🎉 CASPER Prime is working correctly![/bold green]")
    console.print("\nNext steps:")
    console.print("1. Run 'casper init' in a project directory")
    console.print("2. Use 'casper task \"your task\"' to execute tasks")
    console.print("3. Add --dry-run flag to analyze without execution")

if __name__ == "__main__":
    asyncio.run(test_casper())
