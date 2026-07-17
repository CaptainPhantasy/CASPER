"""
Comprehensive test suite for CodingSession implementation.
Tests all ISession interface methods and production scenarios.
"""

import asyncio
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import uuid4

from .coding_session import CodingSession
from ..interfaces import SessionError, SessionState, MAX_CONTEXT_TOKENS


class TestCodingSession(unittest.TestCase):
    """Comprehensive test suite for CodingSession"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.session_manager = CodingSession(storage_path=str(self.test_dir))
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """Clean up test environment"""
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.test_dir)
        self.loop.close()

    def run_async(self, coro):
        """Helper to run async functions in tests"""
        return self.loop.run_until_complete(coro)

    def test_initialization(self):
        """Test session manager initialization"""
        # Check database and directories created
        self.assertTrue(self.session_manager.db_path.exists())
        self.assertTrue(self.session_manager.storage_path.exists())

        # Check database schema
        with sqlite3.connect(self.session_manager.db_path) as conn:
            cursor = conn.cursor()

            # Check tables exist
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name IN ('sessions', 'interactions', 'session_snapshots')
            """)
            tables = [row[0] for row in cursor.fetchall()]
            self.assertIn('sessions', tables)
            self.assertIn('interactions', tables)
            self.assertIn('session_snapshots', tables)

    def test_start_session(self):
        """Test session creation"""
        session_state = self.run_async(self.session_manager.start_session())

        # Verify session state
        self.assertIsInstance(session_state, SessionState)
        self.assertTrue(session_state.active)
        self.assertEqual(session_state.context_tokens, 0)
        self.assertEqual(len(session_state.files_modified), 0)
        self.assertEqual(len(session_state.conversation_history), 0)

        # Verify in database
        with sqlite3.connect(self.session_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_state.session_id,))
            row = cursor.fetchone()
            self.assertIsNotNone(row)

        # Verify in active sessions
        self.assertIn(session_state.session_id, self.session_manager._active_sessions)

    def test_start_session_with_existing_id(self):
        """Test error when starting session with existing ID"""
        session_id = "test-session-1"
        self.run_async(self.session_manager.start_session(session_id))

        # Should raise error on duplicate
        with self.assertRaises(SessionError):
            self.run_async(self.session_manager.start_session(session_id))

    def test_add_interaction(self):
        """Test adding interactions to session"""
        # Start session
        session_state = self.run_async(self.session_manager.start_session())
        session_id = session_state.session_id

        # Add interaction
        user_input = "Write a Python function to calculate fibonacci numbers"
        response = "Here's a Python function that calculates fibonacci numbers:\n\ndef fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)"

        self.run_async(self.session_manager.add_interaction(session_id, user_input, response))

        # Verify in session state
        updated_state = self.session_manager._active_sessions[session_id]
        self.assertEqual(len(updated_state.conversation_history), 1)
        self.assertGreater(updated_state.context_tokens, 0)

        # Verify in database
        with sqlite3.connect(self.session_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM interactions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[3], user_input)  # user_input column
            self.assertEqual(row[4], response)    # response column

    def test_add_interaction_invalid_session(self):
        """Test error when adding interaction to invalid session"""
        with self.assertRaises(SessionError):
            self.run_async(self.session_manager.add_interaction("invalid-session", "test", "response"))

    def test_token_limit_management(self):
        """Test token limit management and reduction"""
        # Start session
        session_state = self.run_async(self.session_manager.start_session())
        session_id = session_state.session_id

        # Add many interactions to exceed token limit
        long_text = "This is a very long text that will contribute many tokens. " * 1000

        # Add enough interactions to exceed MAX_CONTEXT_TOKENS
        interactions_needed = (MAX_CONTEXT_TOKENS // (len(long_text) // 4)) + 10

        for i in range(interactions_needed):
            user_input = f"Request {i}: {long_text}"
            response = f"Response {i}: {long_text}"
            self.run_async(self.session_manager.add_interaction(session_id, user_input, response))

        # Verify token count is managed
        final_state = self.session_manager._active_sessions[session_id]
        self.assertLessEqual(final_state.context_tokens, MAX_CONTEXT_TOKENS)

        # Verify some interactions were removed from database
        with sqlite3.connect(self.session_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM interactions WHERE session_id = ?", (session_id,))
            remaining_count = cursor.fetchone()[0]
            self.assertLess(remaining_count, interactions_needed)

    def test_get_context(self):
        """Test context retrieval"""
        # Start session and add interactions
        session_state = self.run_async(self.session_manager.start_session())
        session_id = session_state.session_id

        user_input = "Test input"
        response = "Test response"
        self.run_async(self.session_manager.add_interaction(session_id, user_input, response))

        # Get context
        context = self.run_async(self.session_manager.get_context(session_id))

        # Verify context structure
        self.assertIn("session_id", context)
        self.assertIn("session_state", context)
        self.assertIn("recent_interactions", context)
        self.assertIn("stored_context", context)
        self.assertIn("metrics", context)
        self.assertIn("timestamp", context)

        # Verify data
        self.assertEqual(context["session_id"], session_id)
        self.assertEqual(len(context["recent_interactions"]), 1)
        self.assertEqual(context["recent_interactions"][0]["user_input"], user_input)

    def test_get_context_invalid_session(self):
        """Test error when getting context for invalid session"""
        with self.assertRaises(SessionError):
            self.run_async(self.session_manager.get_context("invalid-session"))

    def test_persist_session(self):
        """Test session persistence"""
        # Start session and add data
        session_state = self.run_async(self.session_manager.start_session())
        session_id = session_state.session_id

        self.run_async(self.session_manager.add_interaction(session_id, "test", "response"))

        # Persist session
        self.run_async(self.session_manager.persist(session_id))

        # Verify snapshot created
        with sqlite3.connect(self.session_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM session_snapshots WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            self.assertIsNotNone(row)

            # Verify snapshot data
            snapshot_data = json.loads(row[2])
            self.assertIn("session_state", snapshot_data)
            self.assertIn("recent_context", snapshot_data)
            self.assertIn("timestamp", snapshot_data)

    def test_persist_invalid_session(self):
        """Test error when persisting invalid session"""
        with self.assertRaises(SessionError):
            self.run_async(self.session_manager.persist("invalid-session"))

    def test_recover_session(self):
        """Test session recovery from storage"""
        # Create session, add data, and close
        original_session = self.run_async(self.session_manager.start_session())
        session_id = original_session.session_id

        user_input = "Recovery test input"
        response = "Recovery test response"
        self.run_async(self.session_manager.add_interaction(session_id, user_input, response))
        self.run_async(self.session_manager.add_file_modification(session_id, "/test/file.py"))

        # Close session (remove from memory)
        self.run_async(self.session_manager.close_session(session_id))
        self.assertNotIn(session_id, self.session_manager._active_sessions)

        # Recover session
        recovered_session = self.run_async(self.session_manager.recover(session_id))

        # Verify recovery
        self.assertEqual(recovered_session.session_id, session_id)
        self.assertTrue(recovered_session.active)
        self.assertEqual(len(recovered_session.conversation_history), 1)
        self.assertEqual(recovered_session.conversation_history[0]["user"], user_input)
        self.assertIn("/test/file.py", recovered_session.files_modified)

        # Verify back in active sessions
        self.assertIn(session_id, self.session_manager._active_sessions)

    def test_recover_nonexistent_session(self):
        """Test error when recovering non-existent session"""
        with self.assertRaises(SessionError):
            self.run_async(self.session_manager.recover("non-existent-session"))

    def test_cleanup_old_sessions(self):
        """Test cleanup of old sessions"""
        # Create sessions with different ages
        current_session = self.run_async(self.session_manager.start_session())

        # Create old session by manipulating database
        old_session_id = str(uuid4())
        old_date = (datetime.now(timezone.utc) - timedelta(days=35)).isoformat()

        with sqlite3.connect(self.session_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions
                (session_id, started_at, last_activity, context_tokens,
                 files_modified, knowledge_base_id, active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (old_session_id, old_date, old_date, 100, "[]", "kb_old", 1))
            conn.commit()

        # Add old session to active sessions to test removal
        old_session_state = SessionState(
            session_id=old_session_id,
            started_at=datetime.fromisoformat(old_date),
            last_activity=datetime.fromisoformat(old_date),
            context_tokens=100,
            files_modified=[],
            conversation_history=[],
            knowledge_base_id="kb_old",
            active=True
        )
        self.session_manager._active_sessions[old_session_id] = old_session_state

        # Run cleanup
        cleaned_count = self.run_async(self.session_manager.cleanup_old_sessions(30))

        # Verify cleanup
        self.assertEqual(cleaned_count, 1)
        self.assertNotIn(old_session_id, self.session_manager._active_sessions)
        self.assertIn(current_session.session_id, self.session_manager._active_sessions)

        # Verify in database
        with sqlite3.connect(self.session_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT active FROM sessions WHERE session_id = ?", (old_session_id,))
            row = cursor.fetchone()
            self.assertEqual(row[0], 0)  # Should be inactive

    def test_file_modification_tracking(self):
        """Test file modification tracking"""
        session_state = self.run_async(self.session_manager.start_session())
        session_id = session_state.session_id

        # Add file modifications
        files = ["/test/file1.py", "/test/file2.js", "/test/file3.md"]
        for file_path in files:
            self.run_async(self.session_manager.add_file_modification(session_id, file_path))

        # Verify tracking
        updated_state = self.session_manager._active_sessions[session_id]
        self.assertEqual(len(updated_state.files_modified), 3)
        for file_path in files:
            self.assertIn(file_path, updated_state.files_modified)

        # Verify no duplicates
        self.run_async(self.session_manager.add_file_modification(session_id, files[0]))
        final_state = self.session_manager._active_sessions[session_id]
        self.assertEqual(len(final_state.files_modified), 3)  # Still 3, no duplicate

    def test_session_stats(self):
        """Test session statistics"""
        # Create multiple sessions
        sessions = []
        for i in range(3):
            session = self.run_async(self.session_manager.start_session())
            sessions.append(session)
            self.run_async(self.session_manager.add_interaction(
                session.session_id, f"Input {i}", f"Response {i}"
            ))

        # Get stats
        stats = self.run_async(self.session_manager.get_session_stats())

        # Verify stats
        self.assertEqual(stats["total_sessions"], 3)
        self.assertEqual(stats["active_sessions"], 3)
        self.assertEqual(stats["sessions_in_memory"], 3)
        self.assertEqual(stats["total_interactions"], 3)
        self.assertGreater(stats["total_context_tokens"], 0)

    def test_health_check(self):
        """Test health check functionality"""
        health = self.session_manager.health_check()

        # Verify health check response
        self.assertTrue(health["database_accessible"])
        self.assertTrue(health["storage_directory_exists"])
        self.assertEqual(health["active_sessions"], 0)
        self.assertTrue(health["context_manager_available"])
        self.assertIn("timestamp", health)
        self.assertEqual(health["max_context_tokens"], MAX_CONTEXT_TOKENS)

    def test_session_metrics_calculation(self):
        """Test session metrics calculation"""
        session_state = self.run_async(self.session_manager.start_session())
        session_id = session_state.session_id

        # Add multiple interactions
        for i in range(5):
            self.run_async(self.session_manager.add_interaction(
                session_id, f"Input {i}", f"Response {i}"
            ))

        # Calculate metrics
        metrics = self.run_async(self.session_manager._calculate_session_metrics(session_id))

        # Verify metrics
        self.assertEqual(metrics["total_interactions"], 5)
        self.assertGreater(metrics["total_tokens"], 0)
        self.assertGreater(metrics["session_duration_minutes"], 0)
        self.assertGreater(metrics["avg_tokens_per_interaction"], 0)
        self.assertGreater(metrics["tokens_per_minute"], 0)

    def test_concurrent_session_access(self):
        """Test thread-safe concurrent access"""
        session_state = self.run_async(self.session_manager.start_session())
        session_id = session_state.session_id

        async def add_interactions(start_idx):
            """Add interactions concurrently"""
            for i in range(start_idx, start_idx + 10):
                await self.session_manager.add_interaction(
                    session_id, f"Concurrent input {i}", f"Concurrent response {i}"
                )

        # Run concurrent operations
        async def run_concurrent():
            await asyncio.gather(
                add_interactions(0),
                add_interactions(10),
                add_interactions(20)
            )

        self.run_async(run_concurrent())

        # Verify all interactions added
        final_state = self.session_manager._active_sessions[session_id]
        self.assertEqual(len(final_state.conversation_history), 30)

    def test_context_manager_integration(self):
        """Test integration with context manager"""
        session_state = self.run_async(self.session_manager.start_session())
        session_id = session_state.session_id

        # Add interaction to create context
        self.run_async(self.session_manager.add_interaction(
            session_id, "Test context integration", "Context integration response"
        ))

        # Get context and verify context manager integration
        context = self.run_async(self.session_manager.get_context(session_id))
        self.assertIn("stored_context", context)

        # Verify context manager has data
        from uuid import UUID
        session_uuid = UUID(session_id)
        stored_context = self.session_manager.context_manager.load_context(session_uuid)
        self.assertIsNotNone(stored_context)
        self.assertEqual(stored_context["session_id"], session_id)


def run_comprehensive_tests():
    """Run all tests and return results"""
    print("🧪 Running Comprehensive CodingSession Tests...\n")

    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestCodingSession)

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print(f"\n{'='*60}")
    print("Test Results Summary:")
    print(f"  Tests Run: {result.testsRun}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Errors: {len(result.errors)}")
    print(f"  Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")

    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")

    if result.errors:
        print("\n💥 Errors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")

    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n🎉 Overall Result: {'PASSED' if success else 'FAILED'}")
    return success


if __name__ == "__main__":
    success = run_comprehensive_tests()
    exit(0 if success else 1)
