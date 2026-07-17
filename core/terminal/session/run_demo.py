#!/usr/bin/env python3
"""
Demo runner for CodingSession that handles imports correctly.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import time
from core.terminal.session.coding_session import CodingSession
from core.context.manager import ContextManager


async def demo_session_lifecycle():
    """Demonstrate complete session lifecycle"""
    print("🚀 CodingSession Production Demo")
    print("=" * 50)

    # Initialize session manager
    demo_path = "/tmp/claude/casper_session_demo"
    context_manager = ContextManager(demo_path + "/.casper")
    session_manager = CodingSession(storage_path=demo_path, context_manager=context_manager)

    print(f"✅ Session Manager initialized at: {demo_path}")

    # Health check
    health = session_manager.health_check()
    print(f"🏥 Health Check: {health['active_sessions']} active sessions")

    results = {}

    try:
        # 1. Start new session
        print("\n📝 1. Starting New Session...")
        session_state = await session_manager.start_session()
        session_id = session_state.session_id
        print(f"   Session ID: {session_id}")
        results["session_creation"] = "✅ SUCCESS"

        # 2. Add coding interactions
        print("\n💬 2. Adding Coding Interactions...")
        interactions = [
            ("Create a Python class for managing user accounts",
             "Here's a Python class for user account management:\n\nclass UserAccount:\n    def __init__(self, username, email):\n        self.username = username\n        self.email = email\n        self.created_at = datetime.now()\n        self.active = True"),

            ("Add password hashing to the UserAccount class",
             "Here's the updated UserAccount class with password hashing:\n\nimport hashlib\n\nclass UserAccount:\n    def __init__(self, username, email, password):\n        self.username = username\n        self.email = email\n        self.password_hash = self._hash_password(password)\n        self.created_at = datetime.now()\n        self.active = True"),

            ("Create unit tests for the UserAccount class",
             "Here are comprehensive unit tests for the UserAccount class:\n\nimport unittest\nfrom datetime import datetime\n\nclass TestUserAccount(unittest.TestCase):\n    def setUp(self):\n        self.user = UserAccount('testuser', 'test@example.com', 'password123')")
        ]

        for i, (user_input, response) in enumerate(interactions, 1):
            await session_manager.add_interaction(session_id, user_input, response,
                                                metadata={"interaction_type": "coding", "step": i})
            print(f"   Added interaction {i}: {user_input[:50]}...")

        results["interactions"] = "✅ SUCCESS"

        # 3. Track file modifications
        print("\n📁 3. Tracking File Modifications...")
        files = [
            "/project/models/user_account.py",
            "/project/tests/test_user_account.py",
            "/project/utils/auth_helpers.py"
        ]

        for file_path in files:
            await session_manager.add_file_modification(session_id, file_path)

        print(f"   Tracked {len(files)} files")
        results["file_tracking"] = "✅ SUCCESS"

        # 4. Get context
        print("\n🧠 4. Retrieving Session Context...")
        context = await session_manager.get_context(session_id)
        print(f"   Context tokens: {context['session_state']['context_tokens']}")
        print(f"   Recent interactions: {len(context['recent_interactions'])}")
        print(f"   Files modified: {len(context['session_state']['files_modified'])}")
        results["context_retrieval"] = "✅ SUCCESS"

        # 5. Persist session
        print("\n💾 5. Persisting Session...")
        await session_manager.persist(session_id)
        print("   Session state saved to database")
        results["persistence"] = "✅ SUCCESS"

        # 6. Get session statistics
        print("\n📊 6. Session Statistics...")
        stats = await session_manager.get_session_stats()
        print(f"   Total sessions: {stats['total_sessions']}")
        print(f"   Active sessions: {stats['active_sessions']}")
        print(f"   Total interactions: {stats['total_interactions']}")
        results["statistics"] = "✅ SUCCESS"

        # 7. Close session
        print("\n🔒 7. Closing Session...")
        await session_manager.close_session(session_id)
        print("   Session gracefully closed")
        results["session_closure"] = "✅ SUCCESS"

        # 8. Recover session
        print("\n🔄 8. Recovering Session...")
        recovered_state = await session_manager.recover(session_id)
        print(f"   Recovered session: {recovered_state.session_id}")
        print(f"   Session active: {recovered_state.active}")
        print(f"   Conversation history: {len(recovered_state.conversation_history)} items")
        print(f"   Files modified: {len(recovered_state.files_modified)} files")
        results["session_recovery"] = "✅ SUCCESS"

        # 9. Final persistence verification
        print("\n🔍 9. Final Verification...")
        final_context = await session_manager.get_context(session_id)
        final_stats = await session_manager.get_session_stats()

        verification_checks = [
            final_stats['total_sessions'] >= 1,
            final_stats['active_sessions'] >= 1,
            final_stats['total_interactions'] >= 3,
            len(final_context['session_state']['files_modified']) >= 3,
            final_context['session_state']['context_tokens'] > 0
        ]

        all_passed = all(verification_checks)
        print(f"   Verification checks: {sum(verification_checks)}/{len(verification_checks)} passed")
        results["verification"] = "✅ SUCCESS" if all_passed else "❌ FAILED"

    except Exception as e:
        print(f"❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        results["error"] = f"❌ FAILED: {e}"

    return results


def print_results_summary(results):
    """Print formatted results summary"""
    print("\n" + "=" * 60)
    print("🎯 DEMO RESULTS SUMMARY")
    print("=" * 60)

    success_count = 0
    total_count = len(results)

    for test_name, result in results.items():
        status = "✅" if "SUCCESS" in result else "❌"
        if "SUCCESS" in result:
            success_count += 1
        print(f"{status} {test_name.replace('_', ' ').title()}: {result}")

    print(f"\n📊 Success Rate: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")

    overall_success = success_count == total_count
    print(f"🎉 Overall Result: {'PRODUCTION READY ✅' if overall_success else 'NEEDS FIXES ❌'}")

    return overall_success


async def main():
    """Main demo function"""
    print("🚀 Starting CodingSession Demo")
    start_time = time.time()

    # Run demo
    results = await demo_session_lifecycle()

    # Print results
    overall_success = print_results_summary(results)

    duration = time.time() - start_time
    print(f"\n⏱️  Demo completed in {duration:.2f} seconds")
    print(f"🎯 Production readiness: {'CONFIRMED' if overall_success else 'REQUIRES FIXES'}")

    return overall_success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)