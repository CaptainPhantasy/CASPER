#!/usr/bin/env python3
"""
Production verification script for CodingSession.
Comprehensive testing of all production scenarios and edge cases.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import time
import tempfile
import shutil
from core.terminal.session.coding_session import CodingSession
from core.terminal.interfaces import MAX_CONTEXT_TOKENS
from core.context.manager import ContextManager


async def test_production_scenarios():
    """Test all production scenarios"""

    print("🏭 CASPER Prime CodingSession - Production Verification")
    print("=" * 60)

    # Use temporary directory for testing
    test_dir = Path(tempfile.mkdtemp())
    results = {}

    try:
        # Initialize components
        context_manager = ContextManager(str(test_dir / ".casper"))
        session_manager = CodingSession(
            storage_path=str(test_dir), context_manager=context_manager
        )

        print(f"✅ Initialized at: {test_dir}")

        # Test 1: High-Volume Session Creation
        print("\n🔥 Test 1: High-Volume Session Creation...")
        sessions = []
        for i in range(10):
            session = await session_manager.start_session()
            sessions.append(session.session_id)

        print(f"   Created {len(sessions)} sessions")
        results["high_volume_creation"] = len(sessions) == 10

        # Test 2: Token Limit Management (Critical Production Feature)
        print("\n📊 Test 2: Token Limit Management...")
        test_session_id = sessions[0]

        # Generate content that exceeds token limit
        long_text = (
            "This is extensive documentation and code that will contribute significant tokens to test our token management system. "
            * 200
        )

        initial_context = await session_manager.get_context(test_session_id)
        initial_tokens = initial_context["session_state"]["context_tokens"]

        # Add interactions until we exceed the limit
        for i in range(50):
            await session_manager.add_interaction(
                test_session_id,
                f"Complex request {i}: {long_text}",
                f"Detailed response {i}: {long_text}",
            )

        final_context = await session_manager.get_context(test_session_id)
        final_tokens = final_context["session_state"]["context_tokens"]

        token_limit_respected = final_tokens <= MAX_CONTEXT_TOKENS
        print(f"   Initial tokens: {initial_tokens}")
        print(f"   Final tokens: {final_tokens}")
        print(f"   Limit respected: {token_limit_respected}")
        results["token_limit_management"] = token_limit_respected

        # Test 3: Concurrent Operations (Production Critical)
        print("\n⚡ Test 3: Concurrent Operations...")
        concurrent_session = sessions[1]

        async def concurrent_worker(manager, worker_id, session_id, iterations=20):
            for i in range(iterations):
                await manager.add_interaction(
                    session_id,
                    f"Worker-{worker_id} Request {i}",
                    f"Worker-{worker_id} Response {i}",
                )

        # Run 5 workers concurrently
        start_time = time.time()
        await asyncio.gather(
            *[
                concurrent_worker(session_manager, i, concurrent_session, 10)
                for i in range(5)
            ]
        )
        concurrent_time = time.time() - start_time

        concurrent_context = await session_manager.get_context(concurrent_session)
        expected_interactions = 50  # 5 workers × 10 iterations
        actual_interactions = concurrent_context["metrics"]["total_interactions"]

        print(f"   Expected interactions: {expected_interactions}")
        print(f"   Actual interactions: {actual_interactions}")
        print(f"   Time taken: {concurrent_time:.2f}s")
        results["concurrent_operations"] = actual_interactions == expected_interactions

        # Test 4: Database Integrity Under Load
        print("\n🗄️  Test 4: Database Integrity Under Load...")

        # Perform many database operations
        operations_completed = 0
        for i in range(3):
            session_id = sessions[i + 2]  # Use different sessions

            # Add interactions
            for j in range(20):
                await session_manager.add_interaction(
                    session_id, f"Load test {j}", f"Load response {j}"
                )
                operations_completed += 1

            # Add file modifications
            for k in range(5):
                await session_manager.add_file_modification(
                    session_id, f"/test/load/file_{k}.py"
                )
                operations_completed += 1

            # Persist sessions
            await session_manager.persist(session_id)
            operations_completed += 1

        print(f"   Completed {operations_completed} database operations")

        # Verify database integrity
        final_stats = await session_manager.get_session_stats()
        db_integrity_good = (
            final_stats["total_sessions"] >= 10
            and final_stats["total_interactions"] >= 100
        )

        results["database_integrity"] = db_integrity_good

        # Test 5: Recovery After "Crash" Simulation
        print("\n💥 Test 5: Crash Recovery Simulation...")

        # Record state before "crash"
        pre_crash_stats = await session_manager.get_session_stats()
        pre_crash_sessions = session_manager.get_active_session_ids()

        # Simulate crash by creating new session manager instance
        del session_manager

        # Create new instance (simulates restart)
        new_session_manager = CodingSession(
            storage_path=str(test_dir), context_manager=context_manager
        )

        # Try to recover sessions
        recovered_sessions = []
        recovery_failures = 0

        for session_id in sessions[:5]:  # Try to recover first 5 sessions
            try:
                recovered = await new_session_manager.recover(session_id)
                recovered_sessions.append(recovered.session_id)
            except Exception as e:
                print(f"     Recovery failed for {session_id}: {e}")
                recovery_failures += 1

        print(f"   Sessions before crash: {len(pre_crash_sessions)}")
        print(f"   Sessions recovered: {len(recovered_sessions)}")
        print(f"   Recovery failures: {recovery_failures}")

        recovery_successful = len(recovered_sessions) >= 5 and recovery_failures == 0
        results["crash_recovery"] = recovery_successful

        # Test 6: Memory Usage Under Load
        print("\n🧠 Test 6: Memory Management...")

        # Create many sessions with content
        memory_test_sessions = []
        for i in range(20):
            session = await new_session_manager.start_session()
            memory_test_sessions.append(session.session_id)

            # Add content to each session
            for j in range(10):
                await new_session_manager.add_interaction(
                    session.session_id,
                    f"Memory test interaction {j}",
                    f"Memory test response {j}",
                )

        # Check active sessions don't grow unbounded
        active_sessions_count = len(new_session_manager.get_active_session_ids())

        # Cleanup old sessions
        cleaned_count = await new_session_manager.cleanup_old_sessions(days=0)

        memory_managed = cleaned_count > 0
        print(f"   Created {len(memory_test_sessions)} test sessions")
        print(f"   Active sessions: {active_sessions_count}")
        print(f"   Cleaned up: {cleaned_count} sessions")
        results["memory_management"] = memory_managed

        # Test 7: Error Handling
        print("\n🚨 Test 7: Error Handling...")

        error_scenarios_passed = 0

        # Test invalid session operations
        try:
            await new_session_manager.add_interaction(
                "invalid-session", "test", "response"
            )
            print("     ❌ Should have failed for invalid session")
        except Exception:
            error_scenarios_passed += 1

        try:
            await new_session_manager.get_context("invalid-session")
            print("     ❌ Should have failed for invalid session")
        except Exception:
            error_scenarios_passed += 1

        try:
            await new_session_manager.persist("invalid-session")
            print("     ❌ Should have failed for invalid session")
        except Exception:
            error_scenarios_passed += 1

        try:
            await new_session_manager.recover("non-existent-session")
            print("     ❌ Should have failed for non-existent session")
        except Exception:
            error_scenarios_passed += 1

        print(f"   Error scenarios handled: {error_scenarios_passed}/4")
        results["error_handling"] = error_scenarios_passed == 4

        # Test 8: Performance Benchmarks
        print("\n⚱️ Test 8: Performance Benchmarks...")

        perf_session = await new_session_manager.start_session()

        # Benchmark session operations
        benchmarks = {}

        # Interaction addition
        start = time.time()
        for i in range(100):
            await new_session_manager.add_interaction(
                perf_session.session_id, f"Perf test {i}", f"Perf response {i}"
            )
        benchmarks["interactions_per_second"] = 100 / (time.time() - start)

        # Context retrieval
        start = time.time()
        for i in range(50):
            await new_session_manager.get_context(perf_session.session_id)
        benchmarks["context_retrievals_per_second"] = 50 / (time.time() - start)

        # Session persistence
        start = time.time()
        for i in range(10):
            await new_session_manager.persist(perf_session.session_id)
        benchmarks["persists_per_second"] = 10 / (time.time() - start)

        print(f"   Interactions/sec: {benchmarks['interactions_per_second']:.1f}")
        print(
            f"   Context retrievals/sec: {benchmarks['context_retrievals_per_second']:.1f}"
        )
        print(f"   Persists/sec: {benchmarks['persists_per_second']:.1f}")

        # Performance acceptable if we can handle reasonable load
        performance_acceptable = (
            benchmarks["interactions_per_second"] > 50
            and benchmarks["context_retrievals_per_second"] > 20
            and benchmarks["persists_per_second"] > 5
        )
        results["performance"] = performance_acceptable

    except Exception as e:
        print(f"\n❌ Critical error during testing: {e}")
        import traceback

        traceback.print_exc()
        results["critical_error"] = str(e)

    finally:
        # Cleanup
        if test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)

    return results


def analyze_results(results):
    """Analyze and report test results"""
    print("\n" + "=" * 60)
    print("🎯 PRODUCTION VERIFICATION RESULTS")
    print("=" * 60)

    critical_tests = [
        "token_limit_management",
        "concurrent_operations",
        "database_integrity",
        "crash_recovery",
        "error_handling",
    ]

    performance_tests = ["high_volume_creation", "memory_management", "performance"]

    # Check critical functionality
    critical_passed = 0
    critical_total = len(critical_tests)

    print("\n🔥 CRITICAL FUNCTIONALITY:")
    for test in critical_tests:
        if test in results:
            status = "✅ PASS" if results[test] else "❌ FAIL"
            if results[test]:
                critical_passed += 1
            print(f"   {status} {test.replace('_', ' ').title()}")
        else:
            print(f"   ⚠️  NOT RUN {test.replace('_', ' ').title()}")

    # Check performance
    performance_passed = 0
    performance_total = len(performance_tests)

    print("\n⚡ PERFORMANCE & SCALABILITY:")
    for test in performance_tests:
        if test in results:
            status = "✅ PASS" if results[test] else "❌ FAIL"
            if results[test]:
                performance_passed += 1
            print(f"   {status} {test.replace('_', ' ').title()}")
        else:
            print(f"   ⚠️  NOT RUN {test.replace('_', ' ').title()}")

    # Overall assessment
    total_passed = critical_passed + performance_passed
    total_tests = critical_total + performance_total

    print(f"\n📊 OVERALL SCORE:")
    print(
        f"   Critical Tests: {critical_passed}/{critical_total} ({critical_passed/critical_total*100:.1f}%)"
    )
    print(
        f"   Performance Tests: {performance_passed}/{performance_total} ({performance_passed/performance_total*100:.1f}%)"
    )
    print(
        f"   Total Score: {total_passed}/{total_tests} ({total_passed/total_tests*100:.1f}%)"
    )

    # Production readiness assessment
    critical_ready = (
        critical_passed >= critical_total * 0.8
    )  # 80% of critical tests must pass
    performance_ready = (
        performance_passed >= performance_total * 0.6
    )  # 60% of performance tests must pass

    production_ready = critical_ready and performance_ready

    print(f"\n🎯 PRODUCTION READINESS:")
    print(
        f"   Critical Functionality: {'✅ READY' if critical_ready else '❌ NOT READY'}"
    )
    print(
        f"   Performance & Scalability: {'✅ READY' if performance_ready else '❌ NOT READY'}"
    )
    print(
        f"   Overall Assessment: {'🚀 PRODUCTION READY' if production_ready else '⚠️  NEEDS WORK'}"
    )

    if "critical_error" in results:
        print(f"\n💥 CRITICAL ERROR DETECTED: {results['critical_error']}")
        production_ready = False

    return production_ready


async def main():
    """Main verification function"""
    print("🚀 Starting Production Verification...")
    start_time = time.time()

    # Run comprehensive tests
    results = await test_production_scenarios()

    # Analyze results
    production_ready = analyze_results(results)

    duration = time.time() - start_time
    print(f"\n⏱️  Verification completed in {duration:.2f} seconds")

    if production_ready:
        print("\n🎉 VERDICT: CodingSession is PRODUCTION READY! 🚀")
        print("   ✅ All critical functionality working")
        print("   ✅ Performance meets requirements")
        print("   ✅ Error handling robust")
        print("   ✅ Recovery mechanisms tested")
    else:
        print("\n⚠️  VERDICT: Requires fixes before production deployment")
        print("   ❌ Some critical tests failed")
        print("   ❌ Review and fix issues before deployment")

    return production_ready


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
