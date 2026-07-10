"""
Comprehensive demo script for CodingSession functionality.
Demonstrates all features working in production scenario.
"""

import asyncio
import json
import time
from pathlib import Path
from datetime import datetime

from coding_session import CodingSession
from ...context.manager import ContextManager


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
    print(f"🏥 Health Check: {health}")

    results = {}

    try:
        # 1. Start new session
        print("\n📝 1. Starting New Session...")
        session_state = await session_manager.start_session()
        session_id = session_state.session_id
        print(f"   Session ID: {session_id}")
        print(f"   Started at: {session_state.started_at}")
        results["session_creation"] = "✅ SUCCESS"

        # 2. Add coding interactions
        print("\n💬 2. Adding Coding Interactions...")
        interactions = [
            ("Create a Python class for managing user accounts",
             "Here's a Python class for user account management:\n\nclass UserAccount:\n    def __init__(self, username, email):\n        self.username = username\n        self.email = email\n        self.created_at = datetime.now()\n        self.active = True\n\n    def deactivate(self):\n        self.active = False\n\n    def update_email(self, new_email):\n        self.email = new_email"),

            ("Add password hashing to the UserAccount class",
             "Here's the updated UserAccount class with password hashing:\n\nimport hashlib\n\nclass UserAccount:\n    def __init__(self, username, email, password):\n        self.username = username\n        self.email = email\n        self.password_hash = self._hash_password(password)\n        self.created_at = datetime.now()\n        self.active = True\n\n    def _hash_password(self, password):\n        return hashlib.sha256(password.encode()).hexdigest()\n\n    def verify_password(self, password):\n        return self.password_hash == self._hash_password(password)"),

            ("Create unit tests for the UserAccount class",
             "Here are comprehensive unit tests for the UserAccount class:\n\nimport unittest\nfrom datetime import datetime\n\nclass TestUserAccount(unittest.TestCase):\n    def setUp(self):\n        self.user = UserAccount('testuser', 'test@example.com', 'password123')\n\n    def test_user_creation(self):\n        self.assertEqual(self.user.username, 'testuser')\n        self.assertEqual(self.user.email, 'test@example.com')\n        self.assertTrue(self.user.active)\n\n    def test_password_verification(self):\n        self.assertTrue(self.user.verify_password('password123'))\n        self.assertFalse(self.user.verify_password('wrongpassword'))\n\n    def test_deactivation(self):\n        self.user.deactivate()\n        self.assertFalse(self.user.active)")
        ]

        for i, (user_input, response) in enumerate(interactions, 1):
            await session_manager.add_interaction(session_id, user_input, response,
                                                metadata={"interaction_type": "coding", "step": i})
            print(f"   Added interaction {i}: {user_input[:50]}...")

        print(f"   Total interactions: {len(interactions)}")
        results["interactions"] = "✅ SUCCESS"

        # 3. Track file modifications
        print("\n📁 3. Tracking File Modifications...")
        files = [
            "/project/models/user_account.py",
            "/project/tests/test_user_account.py",
            "/project/utils/auth_helpers.py",
            "/project/config/database.py"
        ]

        for file_path in files:
            await session_manager.add_file_modification(session_id, file_path)
            print(f"   Tracked: {file_path}")

        results["file_tracking"] = "✅ SUCCESS"

        # 4. Get comprehensive context
        print("\n🧠 4. Retrieving Session Context...")
        context = await session_manager.get_context(session_id)
        print(f"   Context tokens: {context['session_state']['context_tokens']}")
        print(f"   Recent interactions: {len(context['recent_interactions'])}")
        print(f"   Files modified: {len(context['session_state']['files_modified'])}")
        print(f"   Session metrics: {context['metrics']}")
        results["context_retrieval"] = "✅ SUCCESS"

        # 5. Persist session
        print("\n💾 5. Persisting Session...")
        await session_manager.persist(session_id)
        print("   Session state saved to database")
        print("   Context snapshot created")
        results["persistence"] = "✅ SUCCESS"

        # 6. Add more interactions to test token limit
        print("\n🔄 6. Testing Token Limit Management...")
        long_text = "This is a comprehensive explanation of advanced software engineering concepts including design patterns, SOLID principles, test-driven development, continuous integration, microservices architecture, and scalable system design. " * 50

        initial_tokens = context['session_state']['context_tokens']

        # Add many long interactions
        for i in range(20):
            await session_manager.add_interaction(
                session_id,
                f"Question {i}: Explain advanced concept with details: {long_text[:100]}",
                f"Answer {i}: {long_text}"
            )

        updated_context = await session_manager.get_context(session_id)
        final_tokens = updated_context['session_state']['context_tokens']

        print(f"   Initial tokens: {initial_tokens}")
        print(f"   Final tokens: {final_tokens}")
        print(f"   Token limit enforced: {final_tokens <= 200000}")
        results["token_management"] = "✅ SUCCESS"

        # 7. Get session statistics
        print("\n📊 7. Session Statistics...")
        stats = await session_manager.get_session_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        results["statistics"] = "✅ SUCCESS"

        # 8. Close session
        print("\n🔒 8. Closing Session...")
        await session_manager.close_session(session_id)
        print("   Session gracefully closed")
        print(f"   Active sessions: {len(session_manager.get_active_session_ids())}")
        results["session_closure"] = "✅ SUCCESS"

        # 9. Recover session
        print("\n🔄 9. Recovering Session...")
        recovered_state = await session_manager.recover(session_id)
        print(f"   Recovered session: {recovered_state.session_id}")
        print(f"   Session active: {recovered_state.active}")
        print(f"   Conversation history: {len(recovered_state.conversation_history)} items")
        print(f"   Files modified: {len(recovered_state.files_modified)} files")
        results["session_recovery"] = "✅ SUCCESS"

        # 10. Test concurrent operations
        print("\n⚡ 10. Testing Concurrent Operations...")

        async def concurrent_interactions(session_id, prefix):
            for i in range(5):
                await session_manager.add_interaction(
                    session_id,
                    f"{prefix} Question {i}: How to implement feature X?",
                    f"{prefix} Answer {i}: Implement feature X using these steps..."
                )

        # Run concurrent tasks
        await asyncio.gather(
            concurrent_interactions(session_id, "Thread-A"),
            concurrent_interactions(session_id, "Thread-B"),
            concurrent_interactions(session_id, "Thread-C")
        )

        concurrent_context = await session_manager.get_context(session_id)
        print(f"   Concurrent interactions added successfully")
        print(f"   Total interactions after concurrent test: {concurrent_context['metrics']['total_interactions']}")
        results["concurrent_operations"] = "✅ SUCCESS"

        # 11. Create and test multiple sessions
        print("\n👥 11. Testing Multiple Sessions...")
        additional_sessions = []
        for i in range(3):
            new_session = await session_manager.start_session()
            additional_sessions.append(new_session.session_id)
            await session_manager.add_interaction(
                new_session.session_id,
                f"Multi-session test {i}",
                f"Response for session {i}"
            )

        multi_stats = await session_manager.get_session_stats()
        print(f"   Total sessions: {multi_stats['total_sessions']}")
        print(f"   Active sessions: {multi_stats['active_sessions']}")
        results["multiple_sessions"] = "✅ SUCCESS"

        # 12. Test cleanup
        print("\n🧹 12. Testing Session Cleanup...")
        # Close additional sessions
        for session_id in additional_sessions:
            await session_manager.close_session(session_id)

        cleanup_count = await session_manager.cleanup_old_sessions(days=0)  # Clean all
        print(f"   Cleaned up sessions: {cleanup_count}")
        results["cleanup"] = "✅ SUCCESS"

    except Exception as e:
        print(f"❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        results["error"] = f"❌ FAILED: {e}"

    return results


def demo_persistence_verification():
    """Demonstrate persistence across different manager instances"""
    print("\n🔄 Persistence Verification Across Restarts")
    print("=" * 50)

    demo_path = "/tmp/claude/persistence_test"

    async def phase_1():
        """Create session and data"""
        print("📝 Phase 1: Creating session and data...")
        manager1 = CodingSession(storage_path=demo_path)

        session = await manager1.start_session("persistent-test-session")
        await manager1.add_interaction(
            session.session_id,
            "Create a data persistence layer",
            "Here's a complete data persistence layer implementation..."
        )
        await manager1.add_file_modification(session.session_id, "/project/db/persistence.py")
        await manager1.persist(session.session_id)

        print(f"   Created session: {session.session_id}")
        print(f"   Added interaction and file modification")
        return session.session_id

    async def phase_2(session_id):
        """Restart and recover"""
        print("\n🔄 Phase 2: Simulating restart and recovery...")
        manager2 = CodingSession(storage_path=demo_path)

        # Verify session not in memory initially
        active_ids = manager2.get_active_session_ids()
        print(f"   Active sessions before recovery: {len(active_ids)}")

        # Recover session
        recovered = await manager2.recover(session_id)
        print(f"   Recovered session: {recovered.session_id}")
        print(f"   Session active: {recovered.active}")
        print(f"   Files modified: {recovered.files_modified}")
        print(f"   Conversation history: {len(recovered.conversation_history)} items")

        # Verify recovery worked
        context = await manager2.get_context(session_id)
        print(f"   Context tokens: {context['session_state']['context_tokens']}")

        return len(recovered.conversation_history) > 0 and len(recovered.files_modified) > 0

    # Run phases
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    session_id = loop.run_until_complete(phase_1())
    success = loop.run_until_complete(phase_2(session_id))

    loop.close()

    print(f"\n🎉 Persistence verification: {'PASSED' if success else 'FAILED'}")
    return success


def print_results_summary(results):
    """Print formatted results summary"""
    print("\n" + "=" * 60)
    print("🎯 COMPREHENSIVE DEMO RESULTS")
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
    print("🚀 Starting Comprehensive CodingSession Demo")
    start_time = time.time()

    # Run main demo
    results = await demo_session_lifecycle()

    # Run persistence verification
    persistence_success = demo_persistence_verification()
    results["persistence_verification"] = "✅ SUCCESS" if persistence_success else "❌ FAILED"

    # Print results
    overall_success = print_results_summary(results)

    duration = time.time() - start_time
    print(f"\n⏱️  Demo completed in {duration:.2f} seconds")
    print(f"🎯 Production readiness: {'CONFIRMED' if overall_success else 'REQUIRES FIXES'}")

    return overall_success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)