"""
Integration example showing how to use the state manager in CASPER
"""

import asyncio
from pathlib import Path
from datetime import datetime, timezone

from core.state import create_state_manager, TaskStatus


async def casper_state_integration_demo():
    """Demonstrate how CASPER can use the state manager"""

    print("🚀 CASPER State Management Integration Demo")
    print("=" * 60)

    # Initialize state manager for CASPER
    casper_storage = "/Volumes/Storage/Development/CASPER DEV/.casper/transformation/state_management"
    state_manager = create_state_manager(
        storage_path=casper_storage, use_langgraph=False
    )

    print(f"✅ State manager initialized at: {casper_storage}")

    # Simulate CASPER workflow
    print("\n📋 Simulating CASPER Agent Workflow...")

    # 1. Master agent receives a complex task
    master_task = state_manager.create_task(
        description="Refactor authentication system across frontend and backend",
        assigned_agent="master_prime",
    )
    print(f"📝 Master task created: {master_task.task_id}")

    # 2. Master agent delegates to specialized agents
    subtasks = [
        ("Update backend auth middleware", "backend_prime"),
        ("Refactor frontend login components", "frontend_prime"),
        ("Update database schema", "database_prime"),
        ("Write integration tests", "test_prime"),
    ]

    subtask_ids = []
    for description, agent in subtasks:
        task = state_manager.create_task(description, agent)
        subtask_ids.append(task.task_id)
        print(f"   📋 Subtask: {task.task_id} → {agent}")

    # 3. Simulate agent execution
    print("\n⚡ Simulating Agent Execution...")

    # Start master task
    state_manager.update_task_status(master_task.task_id, TaskStatus.IN_PROGRESS)

    # Process subtasks
    for i, task_id in enumerate(subtask_ids):
        if i < 2:  # First two succeed
            result = {
                "status": "success",
                "files_modified": [f"file_{i+1}.py", f"file_{i+1}_test.py"],
                "lines_changed": 50 + i * 10,
                "duration_seconds": 30 + i * 15,
            }
            state_manager.complete_task(task_id, result)
            print(f"✅ Task {task_id[:8]}... completed successfully")
        elif i == 2:  # Third fails
            state_manager.fail_task(
                task_id, "Database connection timeout during migration"
            )
            print(f"❌ Task {task_id[:8]}... failed")
        else:  # Fourth pending
            state_manager.update_task_status(task_id, TaskStatus.IN_PROGRESS)
            print(f"⏳ Task {task_id[:8]}... in progress")

    # 4. Save system checkpoint
    system_state = {
        "session_id": "casper-demo-session",
        "master_task_id": master_task.task_id,
        "subtask_ids": subtask_ids,
        "active_agents": ["test_prime"],  # Only one still working
        "failed_tasks": 1,
        "completed_tasks": 2,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    checkpoint_id = state_manager.save_checkpoint("casper-demo", system_state)
    print(f"\n💾 System checkpoint saved: {checkpoint_id}")

    # 5. Health check
    health = state_manager.health_check()
    print(f"\n🏥 System Health: {health}")

    # 6. Generate status report
    all_tasks = state_manager.list_all_tasks()
    active_tasks = state_manager.get_active_tasks()

    print(f"\n📊 CASPER System Status:")
    print(f"   Total Tasks: {len(all_tasks)}")
    print(f"   Active Tasks: {len(active_tasks)}")
    print(f"   Database: {health['database_accessible']}")
    print(f"   Storage: {health['storage_path']}")

    # 7. Task breakdown by status
    status_counts = {}
    for task in all_tasks:
        status = task.status.value
        status_counts[status] = status_counts.get(status, 0) + 1

    print(f"\n📈 Task Status Breakdown:")
    for status, count in status_counts.items():
        print(f"   {status}: {count}")

    # 8. Show detailed task information
    print(f"\n📋 Detailed Task List:")
    for task in all_tasks:
        status_icon = {
            "completed": "✅",
            "failed": "❌",
            "in_progress": "⏳",
            "pending": "📋",
        }.get(task.status.value, "❓")

        print(
            f"   {status_icon} {task.task_id[:12]}... | {task.assigned_agent} | {task.description[:50]}"
        )
        if task.error:
            print(f"      Error: {task.error}")
        if task.result:
            print(f"      Result: {task.result.get('status', 'unknown')}")

    print(f"\n🎯 Integration Demo Complete!")
    print("State manager successfully integrated with CASPER workflow")

    return {
        "success": True,
        "tasks_processed": len(all_tasks),
        "checkpoint_id": checkpoint_id,
        "health_status": health,
    }


def demonstrate_recovery():
    """Demonstrate recovery from saved state"""
    print("\n🔄 Demonstrating State Recovery...")

    # Create new instance (simulates system restart)
    casper_storage = "/Volumes/Storage/Development/CASPER DEV/.casper/transformation/state_management"
    new_state_manager = create_state_manager(
        storage_path=casper_storage, use_langgraph=False
    )

    # Show that data persisted
    recovered_tasks = new_state_manager.list_all_tasks()
    print(f"✅ Recovered {len(recovered_tasks)} tasks after 'restart'")

    for task in recovered_tasks[-3:]:  # Show last 3 tasks
        print(
            f"   📋 {task.task_id[:12]}... | {task.status.value} | {task.assigned_agent}"
        )

    return len(recovered_tasks) > 0


if __name__ == "__main__":
    # Run the integration demo
    result = asyncio.run(casper_state_integration_demo())

    # Test recovery
    recovery_success = demonstrate_recovery()

    print(f"\n🏆 Final Results:")
    print(f"   Integration: {'SUCCESS' if result['success'] else 'FAILED'}")
    print(f"   Recovery: {'SUCCESS' if recovery_success else 'FAILED'}")
    print(f"   Tasks: {result['tasks_processed']}")
    print(f"   Checkpoint: {result['checkpoint_id'][:12]}...")
