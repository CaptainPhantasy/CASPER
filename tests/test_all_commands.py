#!/usr/bin/env python3
"""
Comprehensive tests for all 57 CASPER2 commands.
Validates complete implementation following COT methodology.
"""

import asyncio
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from io import StringIO
import time

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from casper_terminal_complete import CasperTerminalComplete, COMMAND_CATEGORIES
from rich.console import Console


class TestAllCommands:
    """Test suite for all 57 commands"""

    @pytest.fixture
    async def terminal(self):
        """Create terminal instance for testing"""
        terminal = CasperTerminalComplete()
        terminal.console = Console(file=StringIO(), force_terminal=True, width=120)

        # Mock CASPER CLI
        terminal.casper_cli = AsyncMock()
        terminal.casper_cli.execute_task = AsyncMock()
        terminal.casper_cli.analyze_only = AsyncMock()
        terminal.casper_cli.show_status = AsyncMock()
        terminal.casper_cli.shutdown = AsyncMock()
        terminal.casper_cli.initialize = AsyncMock()

        await terminal.initialize()
        return terminal

    # ============= TIER 1: CORE COMMANDS TESTS =============

    @pytest.mark.asyncio
    async def test_help_command(self, terminal):
        """Test help command"""
        await terminal.handle_help()
        output = terminal.console.file.getvalue()
        assert "CASPER2 Complete - All 57 Commands" in output

    @pytest.mark.asyncio
    async def test_task_command(self, terminal):
        """Test task command"""
        await terminal.handle_task("implement feature")
        terminal.casper_cli.execute_task.assert_called_once_with("implement feature")

    @pytest.mark.asyncio
    async def test_analyze_command(self, terminal):
        """Test analyze command"""
        await terminal.handle_analyze("complex task")
        terminal.casper_cli.analyze_only.assert_called_once_with("complex task")

    @pytest.mark.asyncio
    async def test_status_command(self, terminal):
        """Test status command"""
        await terminal.handle_status()
        terminal.casper_cli.show_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_exit_command(self, terminal):
        """Test exit command"""
        result = await terminal.handle_exit()
        assert result is True
        terminal.casper_cli.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_command(self, terminal):
        """Test list command"""
        await terminal.handle_list()
        output = terminal.console.file.getvalue()
        assert "Master Prime" in output
        assert "Alpha Prime" in output

    # ============= TIER 3: DEVELOPMENT COMMANDS TESTS =============

    @pytest.mark.asyncio
    async def test_create_command(self, terminal):
        """Test /create command"""
        await terminal.handle_create("component UserProfile")
        terminal.casper_cli.execute_task.assert_called()

    @pytest.mark.asyncio
    async def test_test_command(self, terminal):
        """Test /test command"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Tests passed")
            await terminal.handle_test("")
            mock_run.assert_called()

    @pytest.mark.asyncio
    async def test_debug_command(self, terminal):
        """Test /debug command"""
        await terminal.handle_debug("error in main.py")
        terminal.casper_cli.execute_task.assert_called()

    @pytest.mark.asyncio
    async def test_review_command(self, terminal):
        """Test /review command"""
        await terminal.handle_review("src/main.py")
        terminal.casper_cli.execute_task.assert_called()

    @pytest.mark.asyncio
    async def test_refactor_command(self, terminal):
        """Test /refactor command"""
        await terminal.handle_refactor("legacy code")
        terminal.casper_cli.execute_task.assert_called()

    @pytest.mark.asyncio
    async def test_init_command(self, terminal):
        """Test /init command"""
        await terminal.handle_init("python")
        terminal.casper_cli.execute_task.assert_called()

    @pytest.mark.asyncio
    async def test_build_command(self, terminal):
        """Test /build command"""
        with patch("subprocess.run") as mock_run:
            with patch("shutil.which", return_value=None):
                await terminal.handle_build("")
                output = terminal.console.file.getvalue()
                assert "No build configuration found" in output

    @pytest.mark.asyncio
    async def test_deploy_command(self, terminal):
        """Test /deploy command"""
        await terminal.handle_deploy("production")
        terminal.casper_cli.execute_task.assert_called()

    @pytest.mark.asyncio
    async def test_rollback_command(self, terminal):
        """Test /rollback command"""
        await terminal.handle_rollback("v1.0")
        terminal.casper_cli.execute_task.assert_called()

    @pytest.mark.asyncio
    async def test_migrate_command(self, terminal):
        """Test /migrate command"""
        with patch("shutil.which", return_value=None):
            await terminal.handle_migrate("")
            output = terminal.console.file.getvalue()
            assert "No migration system found" in output

    @pytest.mark.asyncio
    async def test_generate_command(self, terminal):
        """Test /generate command"""
        await terminal.handle_generate("model User")
        terminal.casper_cli.execute_task.assert_called()

    @pytest.mark.asyncio
    async def test_scaffold_command(self, terminal):
        """Test /scaffold command"""
        await terminal.handle_scaffold("mvc")
        terminal.casper_cli.execute_task.assert_called()

    @pytest.mark.asyncio
    async def test_optimize_command(self, terminal):
        """Test /optimize command"""
        await terminal.handle_optimize("database queries")
        terminal.casper_cli.execute_task.assert_called()

    @pytest.mark.asyncio
    async def test_profile_command(self, terminal):
        """Test /profile command"""
        await terminal.handle_profile("api endpoints")
        terminal.casper_cli.execute_task.assert_called()

    # ============= TIER 4: AI COMMANDS TESTS =============

    @pytest.mark.asyncio
    async def test_ai_review_command(self, terminal):
        """Test /ai-review command"""
        await terminal.handle_ai_review("main.py")
        terminal.casper_cli.execute_task.assert_called()

    @pytest.mark.asyncio
    async def test_ai_complete_command(self, terminal):
        """Test /ai-complete command"""
        await terminal.handle_ai_complete("def calculate")
        terminal.casper_cli.execute_task.assert_called()

    @pytest.mark.asyncio
    async def test_ai_explain_command(self, terminal):
        """Test /ai-explain command"""
        await terminal.handle_ai_explain("complex_algorithm.py")
        terminal.casper_cli.execute_task.assert_called()

    @pytest.mark.asyncio
    async def test_ai_suggest_command(self, terminal):
        """Test /ai-suggest command"""
        await terminal.handle_ai_suggest("optimization")
        terminal.casper_cli.execute_task.assert_called()

    @pytest.mark.asyncio
    async def test_ai_translate_command(self, terminal):
        """Test /ai-translate command"""
        await terminal.handle_ai_translate("python javascript code")
        terminal.casper_cli.execute_task.assert_called()

    # ============= TIER 4: BUSINESS COMMANDS TESTS =============

    @pytest.mark.asyncio
    async def test_invoice_command(self, terminal):
        """Test /invoice command"""
        await terminal.handle_invoice("client-abc")
        terminal.casper_cli.execute_task.assert_called()

    @pytest.mark.asyncio
    async def test_proposal_command(self, terminal):
        """Test /proposal command"""
        await terminal.handle_proposal("web development")
        terminal.casper_cli.execute_task.assert_called()

    @pytest.mark.asyncio
    async def test_contract_command(self, terminal):
        """Test /contract command"""
        await terminal.handle_contract("service")
        terminal.casper_cli.execute_task.assert_called()

    @pytest.mark.asyncio
    async def test_quote_command(self, terminal):
        """Test /quote command"""
        await terminal.handle_quote("mobile app")
        terminal.casper_cli.execute_task.assert_called()

    @pytest.mark.asyncio
    async def test_timesheet_command(self, terminal):
        """Test /timesheet command"""
        await terminal.handle_timesheet("view")
        terminal.casper_cli.execute_task.assert_called()

    # ============= TIER 4: TESTING COMMANDS TESTS =============

    @pytest.mark.asyncio
    async def test_unit_test_command(self, terminal):
        """Test /unit-test command"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            await terminal.handle_unit_test("module")
            mock_run.assert_called()

    @pytest.mark.asyncio
    async def test_integration_test_command(self, terminal):
        """Test /integration-test command"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            await terminal.handle_integration_test("")
            mock_run.assert_called()

    @pytest.mark.asyncio
    async def test_e2e_test_command(self, terminal):
        """Test /e2e-test command"""
        with patch("shutil.which", return_value=None):
            await terminal.handle_e2e_test("")
            output = terminal.console.file.getvalue()
            assert "No E2E test runner found" in output

    @pytest.mark.asyncio
    async def test_load_test_command(self, terminal):
        """Test /load-test command"""
        await terminal.handle_load_test("http://localhost:8000")
        terminal.casper_cli.execute_task.assert_called()

    @pytest.mark.asyncio
    async def test_security_test_command(self, terminal):
        """Test /security-test command"""
        await terminal.handle_security_test("")
        terminal.casper_cli.execute_task.assert_called()

    # ============= TIER 4: UTILITY COMMANDS TESTS =============

    @pytest.mark.asyncio
    async def test_search_command(self, terminal):
        """Test /search command"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="results")
            await terminal.handle_search("pattern")
            mock_run.assert_called()

    @pytest.mark.asyncio
    async def test_replace_command(self, terminal):
        """Test /replace command"""
        await terminal.handle_replace("old new")
        terminal.casper_cli.execute_task.assert_called()

    @pytest.mark.asyncio
    async def test_format_command(self, terminal):
        """Test /format command"""
        with patch("shutil.which", return_value=None):
            await terminal.handle_format("")
            output = terminal.console.file.getvalue()
            assert "No formatter found" in output

    @pytest.mark.asyncio
    async def test_lint_command(self, terminal):
        """Test /lint command"""
        with patch("shutil.which", return_value=None):
            await terminal.handle_lint("")
            output = terminal.console.file.getvalue()
            assert "No linter found" in output

    @pytest.mark.asyncio
    async def test_clean_command(self, terminal):
        """Test /clean command"""
        with patch("pathlib.Path.glob", return_value=[]):
            await terminal.handle_clean("")
            output = terminal.console.file.getvalue()
            assert "Cleaned" in output

    @pytest.mark.asyncio
    async def test_backup_command(self, terminal):
        """Test /backup command"""
        with patch("shutil.make_archive"):
            await terminal.handle_backup("test_backup")
            output = terminal.console.file.getvalue()
            assert "backup" in output.lower()

    @pytest.mark.asyncio
    async def test_restore_command(self, terminal):
        """Test /restore command"""
        # Test listing backups when no arg provided
        await terminal.handle_restore("")
        output = terminal.console.file.getvalue()
        assert "backup" in output.lower()

    @pytest.mark.asyncio
    async def test_export_command(self, terminal):
        """Test /export command"""
        await terminal.handle_export("json")
        terminal.casper_cli.execute_task.assert_called()

    @pytest.mark.asyncio
    async def test_import_command(self, terminal):
        """Test /import command"""
        await terminal.handle_import("data.json")
        terminal.casper_cli.execute_task.assert_called()

    @pytest.mark.asyncio
    async def test_sync_command(self, terminal):
        """Test /sync command"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="")
            await terminal.handle_sync("origin")
            assert mock_run.called


class TestCommandRouter:
    """Test command routing"""

    @pytest.fixture
    async def terminal(self):
        """Create terminal instance"""
        terminal = CasperTerminalComplete()
        terminal.console = Console(file=StringIO(), force_terminal=True, width=120)
        terminal.casper_cli = AsyncMock()
        await terminal.initialize()
        return terminal

    @pytest.mark.asyncio
    async def test_command_routing(self, terminal):
        """Test that all commands route correctly"""
        # Test a sample from each category
        test_commands = [
            ("help", False),
            ("task", False),
            ("/create", False),
            ("/test", False),
            ("/ai-review", False),
            ("/invoice", False),
            ("/unit-test", False),
            ("/search", False),
            ("exit", True),  # Should return True
        ]

        for cmd, should_exit in test_commands:
            with patch.object(
                terminal,
                f"handle_{cmd.lstrip('/').replace('-', '_')}",
                return_value=should_exit if cmd == "exit" else None,
            ):
                result = await terminal.handle_command(cmd, "")
                assert result == should_exit

    @pytest.mark.asyncio
    async def test_unknown_command(self, terminal):
        """Test unknown command handling"""
        result = await terminal.handle_command("unknown_cmd", "")
        output = terminal.console.file.getvalue()
        assert "Unknown command" in output
        assert result is False


class TestCommandCategories:
    """Test command category organization"""

    def test_all_categories_have_commands(self):
        """Test that all categories have commands"""
        for category, commands in COMMAND_CATEGORIES.items():
            assert len(commands) > 0, f"Category {category} has no commands"

    def test_total_command_count(self):
        """Test that the documented 57-command catalog remains complete."""
        total = sum(len(cmds) for cmds in COMMAND_CATEGORIES.values())
        assert total == 57, f"Expected 57 commands, got {total}"

    def test_command_descriptions(self):
        """Test that all commands have descriptions"""
        for category, commands in COMMAND_CATEGORIES.items():
            for cmd, desc in commands.items():
                assert desc, f"Command {cmd} in {category} has no description"
                assert len(desc) > 5, f"Command {cmd} description too short"


class TestPerformance:
    """Performance tests for all commands"""

    @pytest.fixture
    async def terminal(self):
        """Create terminal instance"""
        terminal = CasperTerminalComplete()
        terminal.console = Console(file=StringIO(), force_terminal=True, width=120)
        terminal.casper_cli = AsyncMock()
        await terminal.initialize()
        return terminal

    @pytest.mark.asyncio
    async def test_all_commands_performance(self, terminal):
        """Test that all command handlers complete quickly"""

        # Sample of commands to test performance
        test_handlers = [
            terminal.handle_help,
            terminal.handle_list,
            terminal.handle_status,
            terminal.handle_create,
            terminal.handle_ai_review,
            terminal.handle_search,
            terminal.handle_clean,
        ]

        for handler in test_handlers:
            start = time.time()

            # Provide required args for handlers that need them
            if handler.__name__ in [
                "handle_create",
                "handle_ai_review",
                "handle_search",
            ]:
                await handler("test_arg")
            else:
                await handler("")

            elapsed = time.time() - start

            # Each command should complete in under 2 seconds
            assert elapsed < 2.0, f"{handler.__name__} took {elapsed:.2f}s"


class TestEdgeCases:
    """Edge case tests"""

    @pytest.fixture
    async def terminal(self):
        """Create terminal instance"""
        terminal = CasperTerminalComplete()
        terminal.console = Console(file=StringIO(), force_terminal=True, width=120)
        terminal.casper_cli = AsyncMock()
        await terminal.initialize()
        return terminal

    @pytest.mark.asyncio
    async def test_empty_arguments(self, terminal):
        """Test commands with empty arguments"""
        # Commands that should handle empty args gracefully
        commands_ok_with_empty = [
            terminal.handle_help,
            terminal.handle_status,
            terminal.handle_list,
            terminal.handle_review,
            terminal.handle_test,
            terminal.handle_clean,
        ]

        for handler in commands_ok_with_empty:
            try:
                await handler("")
                # Should not raise exception
                assert True
            except Exception as e:
                pytest.fail(f"{handler.__name__} failed with empty args: {e}")

    @pytest.mark.asyncio
    async def test_commands_requiring_args(self, terminal):
        """Test commands that require arguments show usage"""
        commands_requiring_args = [
            (terminal.handle_create, "Usage"),
            (terminal.handle_search, "Usage"),
            (terminal.handle_import, "Usage"),
            (terminal.handle_ai_complete, "Usage"),
        ]

        for handler, expected in commands_requiring_args:
            terminal.console.file.truncate(0)
            terminal.console.file.seek(0)

            await handler("")
            output = terminal.console.file.getvalue()
            assert expected in output or "Usage" in output


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
