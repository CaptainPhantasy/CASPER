#!/usr/bin/env python3
"""
Test runner for CodingSession that handles imports correctly.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Now we can import properly
import asyncio
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

# Import our modules
from core.terminal.session.coding_session import CodingSession, TokenizedInteraction
from core.terminal.interfaces import ISession, SessionState, SessionError, MAX_CONTEXT_TOKENS
from core.context.manager import ContextManager


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
        shutil.rmtree(self.test_dir, ignore_errors=True)
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


def run_tests():
    """Run all tests and return results"""
    print("🧪 Running CodingSession Tests...\n")

    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestCodingSession)

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print(f"\n{'='*60}")
    print(f"Test Results Summary:")
    print(f"  Tests Run: {result.testsRun}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Errors: {len(result.errors)}")
    print(f"  Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")

    if result.failures:
        print(f"\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  - {test}")
            print(f"    {traceback}")

    if result.errors:
        print(f"\n💥 Errors:")
        for test, traceback in result.errors:
            print(f"  - {test}")
            print(f"    {traceback}")

    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n🎉 Overall Result: {'PASSED' if success else 'FAILED'}")
    return success


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)