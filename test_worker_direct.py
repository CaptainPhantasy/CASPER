#!/usr/bin/env python3
"""
Test Worker Agent directly to see where it's failing
"""

import asyncio
import os
from core.agents.worker import WorkerAgent
from core.agents.base import ContextBundle

async def test_worker_direct():
    """Test Worker agent execution directly."""
    
    print("=== Testing Worker Agent Directly ===")
    
    # Set up environment
    os.environ["CASPER_OUTPUT_DIR"] = ".casper/test_output"
    
    # Create agent and context
    agent = WorkerAgent()
    context = ContextBundle()
    
    print(f"Agent created: {agent.role}")
    
    # Test task analysis
    task = "Create a simple hello world function"
    can_handle, reason = await agent.analyze_task(task, context)
    print(f"Can handle: {can_handle} - {reason}")
    
    # Test execution step by step
    print("\n=== Step-by-step execution ===")
    
    try:
        print("1. Starting execution...")
        agent.current_context = context
        
        print("2. Identifying operation...")
        operation = agent._identify_operation(task)
        print(f"   Operation: {operation}")
        
        print("3. Creating plan...")
        plan = agent._create_simple_plan(task, operation)
        print(f"   Plan: {plan}")
        
        print("4. Building prompt...")
        prompt = agent._build_prompt(task, operation, plan)
        print(f"   Prompt length: {len(prompt)}")
        
        print("5. Calling LLM...")
        diff = await agent._call_llm(prompt, task, operation, plan)
        print(f"   Diff length: {len(diff)}")
        print(f"   Diff preview: {diff[:200]}...")
        
        print("6. Writing artifact...")
        from core.services.files import write_artifact
        base_dir = os.environ.get("CASPER_OUTPUT_DIR", ".casper/output")
        session_id = str(context.session_id)
        patch_dir = f"patches/{operation}"
        patch_name = f"{operation}_changes.diff"
        
        path = write_artifact(base_dir, session_id, f"{patch_dir}/{patch_name}", diff.rstrip() + "\n")
        print(f"   Artifact written to: {path}")
        
        print("✓ Worker agent completed successfully!")
        
    except Exception as e:
        print(f"✗ Worker agent failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_worker_direct())