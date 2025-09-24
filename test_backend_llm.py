#!/usr/bin/env python3
"""
Test Backend Prime LLM integration specifically
"""

import asyncio
from core.agents.backend_prime import BackendPrimeAgent
from core.services.llm import llm_service

async def test_backend_llm():
    print("=== Testing Backend Prime LLM Integration ===")
    
    # Test LLM service directly
    print("\n1. Testing LLM service directly:")
    try:
        result = await llm_service.complete("Create a FastAPI endpoint", max_tokens=1500)
        print(f"✓ Direct LLM call successful: {result[:100]}...")
    except Exception as e:
        print(f"✗ Direct LLM call failed: {e}")
        return
    
    # Test Backend Prime's _call_llm method
    print("\n2. Testing Backend Prime _call_llm:")
    agent = BackendPrimeAgent()
    
    try:
        prompt = """You are Backend Prime inside CASPER.
Task: Create a FastAPI endpoint for user registration with email validation
Technologies: Python, FastAPI, SQLAlchemy
Artifacts to emit, each delimited by '=== <path> ===':
- backend/api.py
- backend/schemas.py
Guidance: Produce FastAPI code with request/response models, dependency injection, and clear error handling.
Produce production-ready code with docstrings and basic tests or inline examples where appropriate."""
        
        result = await agent._call_llm(prompt)
        print(f"✓ Backend _call_llm successful")
        print(f"Result length: {len(result)}")
        print(f"First 200 chars: {result[:200]}...")
        
        if "=== backend/api.py ===" in result:
            print("✓ Contains expected artifact delimiter")
        else:
            print("✗ Missing expected artifact delimiter - using fallback")
            
    except Exception as e:
        print(f"✗ Backend _call_llm failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_backend_llm())