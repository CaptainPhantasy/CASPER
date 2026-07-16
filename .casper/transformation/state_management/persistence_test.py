"""
Real persistence verification for ProductionStateManager
Tests actual file/database storage and recovery
"""

import asyncio
import os
import sqlite3
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

import sys
sys.path.append('/Volumes/Storage/Development/CASPER DEV')

from core.state.langgraph_orchestrator import ProductionStateManager, AgentTask, TaskStatus


class PersistenceVerifier:
    """Verifies actual persistence capabilities - NO MOCKS"""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="casper_state_test_")
        self.test_results = []

    def cleanup(self):
        """Clean up test directory"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    async def test_database_persistence(self) -> bool:
        """Test SQLite database persistence"""
        print("🔍 Testing database persistence...")

        try:
            # Create state manager with temp directory
            sm = ProductionStateManager(storage_path=self.temp_dir)

            # Process a task
            result = await sm.process_task("Test database persistence", "db-test-001")

            if not result["success"]:
                self.test_results.append({"test": "database_persistence", "status": "FAILED", "error": result.get("error")})
                return False

            # Verify database file exists
            db_file = Path(self.temp_dir) / "state_manager.db"
            if not db_file.exists():
                self.test_results.append({"test": "database_persistence", "status": "FAILED", "error": "Database file not created"})
                return False

            # Verify database contains data
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM tasks")
            task_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM state_snapshots")
            snapshot_count = cursor.fetchone()[0]

            conn.close()

            if task_count == 0 or snapshot_count == 0:
                self.test_results.append({
                    "test": "database_persistence",
                    "status": "FAILED",
                    "error": f"No data in database: tasks={task_count}, snapshots={snapshot_count}"
                })
                return False

            self.test_results.append({
                "test": "database_persistence",
                "status": "PASSED",
                "details": f"tasks={task_count}, snapshots={snapshot_count}"
            })
            return True

        except Exception as e:
            self.test_results.append({"test": "database_persistence", "status": "FAILED", "error": str(e)})
            return False

    async def test_checkpoint_recovery(self) -> bool:
        """Test checkpoint creation and recovery"""
        print("🔍 Testing checkpoint recovery...")

        try:
            # Create first instance
            sm1 = ProductionStateManager(storage_path=self.temp_dir)

            # Process task and save checkpoint
            result = await sm1.process_task("Test checkpoint recovery", "checkpoint-test-001")

            if not result["success"]:
                self.test_results.append({"test": "checkpoint_recovery", "status": "FAILED", "error": result.get("error")})
                return False

            checkpoint_id = result["final_checkpoint"]

            # Create second instance (simulating restart)
            sm2 = ProductionStateManager(storage_path=self.temp_dir)

            # Recover from checkpoint
            recovered = sm2.recover_from_checkpoint(checkpoint_id)

            if not recovered:
                self.test_results.append({"test": "checkpoint_recovery", "status": "FAILED", "error": "Failed to recover checkpoint"})
                return False

            # Verify checkpoint file exists
            checkpoint_file = Path(self.temp_dir) / "checkpoints" / f"{checkpoint_id}.json"
            if not checkpoint_file.exists():
                self.test_results.append({"test": "checkpoint_recovery", "status": "FAILED", "error": "Checkpoint file not created"})
                return False

            # Verify checkpoint content
            with open(checkpoint_file, 'r') as f:
                checkpoint_data = json.load(f)

            if not checkpoint_data.get("state") or not checkpoint_data.get("thread_id"):
                self.test_results.append({"test": "checkpoint_recovery", "status": "FAILED", "error": "Invalid checkpoint content"})
                return False

            self.test_results.append({
                "test": "checkpoint_recovery",
                "status": "PASSED",
                "details": f"checkpoint_id={checkpoint_id}, thread_id={checkpoint_data['thread_id']}"
            })
            return True

        except Exception as e:
            self.test_results.append({"test": "checkpoint_recovery", "status": "FAILED", "error": str(e)})
            return False

    async def test_restart_persistence(self) -> bool:
        """Test persistence across system restarts"""
        print("🔍 Testing restart persistence...")

        try:
            # Phase 1: Create and populate
            sm1 = ProductionStateManager(storage_path=self.temp_dir)

            # Process multiple tasks
            tasks = [
                "Task 1 - File operations",
                "Task 2 - Data processing",
                "Task 3 - System verification"
            ]

            for i, task in enumerate(tasks):
                result = await sm1.process_task(task, f"restart-test-{i:03d}")
                if not result["success"]:
                    self.test_results.append({
                        "test": "restart_persistence",
                        "status": "FAILED",
                        "error": f"Task {i} failed: {result.get('error')}"
                    })
                    return False

            # Record state before "restart"
            tasks_before = len(sm1.list_all_tasks())
            active_before = len(sm1.get_active_tasks())

            # Phase 2: Simulate restart by creating new instance
            sm2 = ProductionStateManager(storage_path=self.temp_dir)

            # Verify data was loaded
            tasks_after = len(sm2.list_all_tasks())
            active_after = len(sm2.get_active_tasks())

            if tasks_before != tasks_after:
                self.test_results.append({
                    "test": "restart_persistence",
                    "status": "FAILED",
                    "error": f"Task count mismatch: before={tasks_before}, after={tasks_after}"
                })
                return False

            # Verify specific task data
            all_tasks = sm2.list_all_tasks()
            task_descriptions = [task.description for task in all_tasks]

            for original_task in tasks:
                if original_task not in task_descriptions:
                    self.test_results.append({
                        "test": "restart_persistence",
                        "status": "FAILED",
                        "error": f"Missing task after restart: {original_task}"
                    })
                    return False

            self.test_results.append({
                "test": "restart_persistence",
                "status": "PASSED",
                "details": f"Restored {tasks_after} tasks, {active_after} active"
            })
            return True

        except Exception as e:
            self.test_results.append({"test": "restart_persistence", "status": "FAILED", "error": str(e)})
            return False

    async def test_concurrent_operations(self) -> bool:
        """Test concurrent task processing with persistence"""
        print("🔍 Testing concurrent operations...")

        try:
            sm = ProductionStateManager(storage_path=self.temp_dir)

            # Run multiple tasks concurrently
            concurrent_tasks = [
                sm.process_task(f"Concurrent task {i}", f"concurrent-{i:03d}")
                for i in range(5)
            ]

            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)

            # Check for exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.test_results.append({
                        "test": "concurrent_operations",
                        "status": "FAILED",
                        "error": f"Task {i} raised exception: {result}"
                    })
                    return False

            # Verify all tasks were successful
            successful_tasks = sum(1 for r in results if isinstance(r, dict) and r.get("success", False))

            if successful_tasks != len(concurrent_tasks):
                self.test_results.append({
                    "test": "concurrent_operations",
                    "status": "FAILED",
                    "error": f"Only {successful_tasks}/{len(concurrent_tasks)} tasks succeeded"
                })
                return False

            # Verify database integrity after concurrent operations
            db_file = Path(self.temp_dir) / "state_manager.db"
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM tasks")
            final_task_count = cursor.fetchone()[0]

            conn.close()

            self.test_results.append({
                "test": "concurrent_operations",
                "status": "PASSED",
                "details": f"Processed {successful_tasks} concurrent tasks, {final_task_count} in database"
            })
            return True

        except Exception as e:
            self.test_results.append({"test": "concurrent_operations", "status": "FAILED", "error": str(e)})
            return False

    def generate_report(self) -> Dict:
        """Generate comprehensive test report"""
        passed = sum(1 for r in self.test_results if r["status"] == "PASSED")
        failed = sum(1 for r in self.test_results if r["status"] == "FAILED")

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_tests": len(self.test_results),
                "passed": passed,
                "failed": failed,
                "success_rate": f"{(passed/len(self.test_results)*100):.1f}%" if self.test_results else "0%"
            },
            "test_directory": self.temp_dir,
            "test_results": self.test_results
        }

        return report

    async def run_all_tests(self) -> Dict:
        """Run all persistence tests"""
        print("🚀 Starting comprehensive persistence tests...")

        tests = [
            self.test_database_persistence,
            self.test_checkpoint_recovery,
            self.test_restart_persistence,
            self.test_concurrent_operations
        ]

        for test in tests:
            try:
                await test()
            except Exception as e:
                self.test_results.append({
                    "test": test.__name__,
                    "status": "FAILED",
                    "error": f"Test runner error: {e}"
                })

        return self.generate_report()


async def main():
    """Run persistence verification"""
    verifier = PersistenceVerifier()

    try:
        report = await verifier.run_all_tests()

        print("\n" + "="*60)
        print("📊 PERSISTENCE TEST REPORT")
        print("="*60)
        print(f"Total Tests: {report['summary']['total_tests']}")
        print(f"Passed: {report['summary']['passed']}")
        print(f"Failed: {report['summary']['failed']}")
        print(f"Success Rate: {report['summary']['success_rate']}")
        print(f"Test Directory: {report['test_directory']}")
        print()

        for result in report['test_results']:
            status_icon = "✅" if result['status'] == 'PASSED' else "❌"
            print(f"{status_icon} {result['test']}: {result['status']}")
            if result['status'] == 'FAILED':
                print(f"   Error: {result['error']}")
            elif 'details' in result:
                print(f"   Details: {result['details']}")

        # Save report
        report_file = Path(verifier.temp_dir) / "persistence_test_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n📁 Full report saved to: {report_file}")

        return report['summary']['failed'] == 0

    finally:
        verifier.cleanup()


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)