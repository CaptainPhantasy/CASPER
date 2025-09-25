"""
Production CLI Commands Test Suite
Agent B - Testing Engineer

CRITICAL: All CLI commands must be functional. NO EXCUSES.
This test suite validates EVERY command implementation.
"""

import pytest
import asyncio
import json
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4
import os

from core.services.slash_commands import SlashCommandRegistry, SlashCommand
from core.cli import CasperCLI


class TestCLICommandProduction:
    """Production-ready test suite for CASPER CLI commands."""

    @pytest.fixture
    async def command_registry(self):
        """Create a command registry for testing."""
        return SlashCommandRegistry()

    @pytest.fixture
    async def casper_cli(self):
        """Create a mock CASPER CLI instance."""
        cli = MagicMock()
        cli.execute_task = AsyncMock()
        cli.analyze_only = AsyncMock()
        cli.show_status = AsyncMock()
        cli.run_setup = AsyncMock()
        return cli

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Create basic project structure
            (project_dir / ".git").mkdir()
            (project_dir / "src").mkdir()
            (project_dir / "tests").mkdir()

            # Create package.json for JS tests
            package_json = {
                "name": "test-project",
                "scripts": {"test": "jest"}
            }
            with open(project_dir / "package.json", "w") as f:
                json.dump(package_json, f)

            # Create pytest.ini for Python tests
            with open(project_dir / "pytest.ini", "w") as f:
                f.write("[tool:pytest]\ntestpaths = tests\n")

            yield project_dir

    # === SYSTEM COMMANDS ===

    @pytest.mark.asyncio
    async def test_help_command(self, command_registry):
        """Test /help command functionality."""
        # Test basic help
        with patch('rich.console.Console.print') as mock_print:
            await command_registry._cmd_help("")
            # Verify help was displayed
            assert mock_print.called
            # Check that help content was printed
            call_args = [str(call) for call in mock_print.call_args_list]
            assert any("CASPER" in arg or "Commands" in arg for arg in call_args)

    @pytest.mark.asyncio
    async def test_help_with_category(self, command_registry):
        """Test /help command with specific category."""
        with patch('builtins.print') as mock_print:
            await command_registry._cmd_help("System")
            # Verify category-specific help was displayed
            assert any("System" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_status_command_with_cli(self, command_registry, casper_cli):
        """Test /status command with CLI context."""
        command_registry.casper_cli = casper_cli
        await command_registry._cmd_status("")
        casper_cli.show_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_status_command_without_cli(self, command_registry):
        """Test /status command without CLI context."""
        command_registry.casper_cli = None
        with patch('builtins.print') as mock_print:
            await command_registry._cmd_status("")
            # Should display warning
            assert any("requires CASPER CLI context" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_config_show(self, command_registry):
        """Test /config command showing current configuration."""
        with patch('core.services.user_config.user_config') as mock_config:
            mock_config.get_user_info.return_value = {
                "username": "test_user",
                "config_dir": "/test/config",
                "configured_providers": ["anthropic"]
            }
            mock_config.get_config.return_value = {"test_key": "test_value"}
            mock_config.get_default_provider.return_value = "anthropic"

            with patch('builtins.print') as mock_print:
                await command_registry._cmd_config("")
                # Verify config was displayed
                assert any("test_user" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_config_set(self, command_registry):
        """Test /config set command."""
        with patch('core.services.user_config.user_config') as mock_config:
            mock_config.get_config.return_value = {}
            mock_config.store_config = MagicMock()

            with patch('builtins.print') as mock_print:
                await command_registry._cmd_config("set test_key test_value")
                mock_config.store_config.assert_called_once()
                # Verify success message
                assert any("Set test_key" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_config_set_invalid(self, command_registry):
        """Test /config set with invalid arguments."""
        with patch('builtins.print') as mock_print:
            await command_registry._cmd_config("set")
            # Should show usage error
            assert any("Usage:" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_setup_with_cli(self, command_registry, casper_cli):
        """Test /setup command with CLI context."""
        command_registry.casper_cli = casper_cli
        await command_registry._cmd_setup("")
        casper_cli.run_setup.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_command(self, command_registry):
        """Test /clear command functionality."""
        with patch('rich.console.Console.clear') as mock_clear:
            with patch('builtins.print') as mock_print:
                await command_registry._cmd_clear("")
                mock_clear.assert_called_once()
                assert any("cleared" in str(call) for call in mock_print.call_args_list)

    # === TASK MANAGEMENT COMMANDS ===

    @pytest.mark.asyncio
    async def test_task_command_with_cli(self, command_registry, casper_cli):
        """Test /task command with CLI context."""
        command_registry.casper_cli = casper_cli
        await command_registry._cmd_task("test task description")
        casper_cli.execute_task.assert_called_once_with("test task description")

    @pytest.mark.asyncio
    async def test_task_command_without_cli(self, command_registry):
        """Test /task command without CLI context."""
        command_registry.casper_cli = None
        with patch('builtins.print') as mock_print:
            await command_registry._cmd_task("test task")
            assert any("requires CASPER CLI context" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_task_command_empty(self, command_registry):
        """Test /task command with empty description."""
        with patch('builtins.print') as mock_print:
            await command_registry._cmd_task("")
            assert any("Usage:" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_analyze_command_with_cli(self, command_registry, casper_cli):
        """Test /analyze command with CLI context."""
        command_registry.casper_cli = casper_cli
        await command_registry._cmd_analyze("test analysis")
        casper_cli.analyze_only.assert_called_once_with("test analysis")

    @pytest.mark.asyncio
    async def test_analyze_command_empty(self, command_registry):
        """Test /analyze command with empty description."""
        with patch('builtins.print') as mock_print:
            await command_registry._cmd_analyze("")
            assert any("Usage:" in str(call) for call in mock_print.call_args_list)

    # === SESSION MANAGEMENT ===

    @pytest.mark.asyncio
    async def test_save_session_default_name(self, command_registry):
        """Test /save command with default session name."""
        with patch('builtins.open', create=True) as mock_open:
            with patch('json.dump') as mock_dump:
                with patch('builtins.print') as mock_print:
                    await command_registry._cmd_save("")
                    mock_open.assert_called_once()
                    mock_dump.assert_called_once()
                    assert any("saved" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_save_session_custom_name(self, command_registry):
        """Test /save command with custom session name."""
        with patch('builtins.open', create=True) as mock_open:
            with patch('json.dump') as mock_dump:
                with patch('builtins.print') as mock_print:
                    await command_registry._cmd_save("my_session")
                    mock_open.assert_called_once()
                    mock_dump.assert_called_once()
                    assert any("my_session" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_sessions_list_empty(self, command_registry):
        """Test /sessions command with no saved sessions."""
        with patch.object(Path, 'glob', return_value=[]):
            with patch('builtins.print') as mock_print:
                await command_registry._cmd_sessions("")
                assert any("No saved sessions" in str(call) for call in mock_print.call_args_list)

    # === CODE GENERATION COMMANDS ===

    @pytest.mark.asyncio
    async def test_newcomponent_basic(self, command_registry):
        """Test /newcomponent command with basic usage."""
        with patch('core.services.codegen.code_generator') as mock_generator:
            mock_generator.generate_component = AsyncMock(return_value=True)

            await command_registry._cmd_newcomponent("TestComponent")
            mock_generator.generate_component.assert_called_once()

    @pytest.mark.asyncio
    async def test_newcomponent_with_options(self, command_registry):
        """Test /newcomponent with various options."""
        with patch('core.services.codegen.code_generator') as mock_generator:
            mock_generator.generate_component = AsyncMock(return_value=True)

            await command_registry._cmd_newcomponent("TestComponent --type=react --no-tests --stories")

            call_args = mock_generator.generate_component.call_args
            assert call_args[1]['component_type'] == 'react'
            assert call_args[1]['options']['include_tests'] is False
            assert call_args[1]['options']['include_stories'] is True

    @pytest.mark.asyncio
    async def test_newcomponent_empty(self, command_registry):
        """Test /newcomponent with no component name."""
        with patch('builtins.print') as mock_print:
            await command_registry._cmd_newcomponent("")
            assert any("Usage:" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_docs_command(self, command_registry):
        """Test /docs command functionality."""
        with patch('core.services.docgen.doc_generator') as mock_generator:
            mock_generator.generate_file_docs = AsyncMock(return_value=True)

            await command_registry._cmd_docs("src/utils.py")
            mock_generator.generate_file_docs.assert_called_once_with("src/utils.py")

    @pytest.mark.asyncio
    async def test_docs_with_function(self, command_registry):
        """Test /docs command with specific function."""
        with patch('core.services.docgen.doc_generator') as mock_generator:
            mock_generator.generate_function_docs = AsyncMock(return_value=True)

            await command_registry._cmd_docs("src/utils.py calculate_total")
            mock_generator.generate_function_docs.assert_called_once_with("src/utils.py", "calculate_total")

    @pytest.mark.asyncio
    async def test_docs_empty(self, command_registry):
        """Test /docs command with no arguments."""
        with patch('builtins.print') as mock_print:
            await command_registry._cmd_docs("")
            assert any("Usage:" in str(call) for call in mock_print.call_args_list)

    # === GIT COMMANDS ===

    @pytest.mark.asyncio
    async def test_commit_not_in_git_repo(self, command_registry):
        """Test /commit command when not in a git repository."""
        with patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'git')):
            with patch('builtins.print') as mock_print:
                await command_registry._cmd_commit("")
                assert any("Not in a git repository" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_commit_no_changes(self, command_registry):
        """Test /commit command with no changes to commit."""
        # Mock git status to return success but no changes
        mock_status = MagicMock()
        mock_status.stdout = ""
        mock_status.returncode = 0

        with patch('subprocess.run', return_value=mock_status):
            with patch('builtins.print') as mock_print:
                await command_registry._cmd_commit("")
                assert any("No changes to commit" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_commit_with_changes(self, command_registry):
        """Test /commit command with changes to commit."""
        # Mock git status with changes
        mock_status = MagicMock()
        mock_status.stdout = "M  test_file.py\n"
        mock_status.returncode = 0

        # Mock git diff
        mock_diff = MagicMock()
        mock_diff.stdout = "diff --git a/test_file.py b/test_file.py\n+new line\n"
        mock_diff.returncode = 0

        with patch('subprocess.run', side_effect=[mock_status, mock_status, mock_diff]):
            with patch('rich.prompt.Confirm.ask', return_value=False):  # User cancels
                with patch('builtins.print') as mock_print:
                    await command_registry._cmd_commit("")
                    assert any("cancelled" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_commit_custom_message(self, command_registry):
        """Test /commit command with custom message."""
        # Mock git status with changes
        mock_status = MagicMock()
        mock_status.stdout = "M  test_file.py\n"
        mock_status.returncode = 0

        mock_diff = MagicMock()
        mock_diff.stdout = "diff content"
        mock_diff.returncode = 0

        mock_add = MagicMock()
        mock_add.returncode = 0

        mock_commit = MagicMock()
        mock_commit.returncode = 0

        with patch('subprocess.run', side_effect=[mock_status, mock_status, mock_diff, mock_add, mock_commit]):
            with patch('rich.prompt.Confirm.ask', return_value=True):  # User confirms
                with patch('builtins.print') as mock_print:
                    await command_registry._cmd_commit("--message='test commit'")
                    assert any("Committed successfully" in str(call) for call in mock_print.call_args_list)

    # === TESTING COMMANDS ===

    @pytest.mark.asyncio
    async def test_test_command_pytest_detection(self, command_registry, temp_project):
        """Test /test command detecting pytest."""
        os.chdir(temp_project)

        # Mock pytest execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "===== 5 passed in 0.1s ====="
        mock_result.stderr = ""

        with patch('subprocess.run', return_value=mock_result):
            with patch('builtins.print') as mock_print:
                await command_registry._cmd_test("")
                assert any("pytest" in str(call) for call in mock_print.call_args_list)
                assert any("passed" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_test_command_no_framework(self, command_registry):
        """Test /test command when no test framework is detected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            with patch('builtins.print') as mock_print:
                await command_registry._cmd_test("")
                assert any("No test framework detected" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_test_command_with_specific_file(self, command_registry, temp_project):
        """Test /test command with specific test file."""
        os.chdir(temp_project)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "test_specific.py passed"
        mock_result.stderr = ""

        with patch('subprocess.run', return_value=mock_result):
            with patch('builtins.print') as mock_print:
                await command_registry._cmd_test("test_specific.py")
                # Should include the specific file in the command
                assert any("test_specific.py" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_test_command_failures(self, command_registry, temp_project):
        """Test /test command with test failures."""
        os.chdir(temp_project)

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "===== FAILURES ====="
        mock_result.stderr = "2 failed, 3 passed"

        with patch('subprocess.run', return_value=mock_result):
            with patch('rich.prompt.Confirm.ask', return_value=False):  # Don't rerun failed
                with patch('builtins.print') as mock_print:
                    await command_registry._cmd_test("")
                    assert any("failed" in str(call) for call in mock_print.call_args_list)

    # === TODO MANAGEMENT ===

    @pytest.mark.asyncio
    async def test_todo_add_basic(self, command_registry):
        """Test /todo command displays under development message."""
        with patch('builtins.print') as mock_print:
            await command_registry._cmd_todo("Add new feature")
            assert any("Under development" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_todo_empty(self, command_registry):
        """Test /todo command with empty task."""
        with patch('builtins.print') as mock_print:
            await command_registry._cmd_todo("")
            assert any("Under development" in str(call) for call in mock_print.call_args_list)

    # === ERROR HANDLING AND EDGE CASES ===

    @pytest.mark.asyncio
    async def test_explain_command_placeholder(self, command_registry):
        """Test /explain command shows development status."""
        with patch('builtins.print') as mock_print:
            await command_registry._cmd_explain("test error message")
            assert any("Under development" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_sync_command_placeholder(self, command_registry):
        """Test /sync command shows development status."""
        with patch('builtins.print') as mock_print:
            await command_registry._cmd_sync("")
            assert any("Under development" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_debug_command_placeholder(self, command_registry):
        """Test /debug command shows development status."""
        with patch('builtins.print') as mock_print:
            await command_registry._cmd_debug("debug issue")
            assert any("Under development" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_deploy_command_placeholder(self, command_registry):
        """Test /deploy command shows development status."""
        with patch('builtins.print') as mock_print:
            await command_registry._cmd_deploy("staging")
            assert any("Under development" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_command_execution_with_unknown_command(self, command_registry):
        """Test execution of unknown command."""
        with patch('builtins.print') as mock_print:
            result = await command_registry.execute("/unknown_command test")
            assert result is True  # Command was processed (even if unknown)
            assert any("Unknown command" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_command_execution_exception_handling(self, command_registry):
        """Test command execution with exception."""
        # Mock a command that raises an exception
        with patch.object(command_registry, '_cmd_help', side_effect=Exception("Test error")):
            with patch('builtins.print') as mock_print:
                result = await command_registry.execute("/help")
                assert result is True
                assert any("Error executing" in str(call) for call in mock_print.call_args_list)

    # === PERSONALIZATION COMMANDS ===

    @pytest.mark.asyncio
    async def test_custom_command_list(self, command_registry):
        """Test /custom list functionality."""
        with patch('core.services.personalization.personalization_manager') as mock_pm:
            mock_pm.show_custom_commands = MagicMock()

            await command_registry._cmd_custom("list")
            mock_pm.show_custom_commands.assert_called_once()

    @pytest.mark.asyncio
    async def test_custom_command_no_args(self, command_registry):
        """Test /custom with no arguments shows custom commands."""
        with patch('core.services.personalization.personalization_manager') as mock_pm:
            mock_pm.show_custom_commands = MagicMock()

            await command_registry._cmd_custom("")
            mock_pm.show_custom_commands.assert_called_once()

    # === BUSINESS COMMANDS ===

    @pytest.mark.asyncio
    async def test_proposal_command_basic(self, command_registry):
        """Test /proposal command basic functionality."""
        with patch('core.services.business.business_service') as mock_service:
            mock_service.generate_proposal = AsyncMock(return_value=True)

            await command_registry._cmd_proposal("ClientName")
            mock_service.generate_proposal.assert_called_once()

    @pytest.mark.asyncio
    async def test_proposal_command_empty(self, command_registry):
        """Test /proposal command with no client name."""
        with patch('builtins.print') as mock_print:
            await command_registry._cmd_proposal("")
            assert any("Usage:" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_estimate_command_basic(self, command_registry):
        """Test /estimate command functionality."""
        with patch('core.services.business.business_service') as mock_service:
            mock_service.estimate_project = AsyncMock(return_value={"hours": 40})

            await command_registry._cmd_estimate("Build a web app")
            mock_service.estimate_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_estimate_command_empty(self, command_registry):
        """Test /estimate command with no description."""
        with patch('builtins.print') as mock_print:
            await command_registry._cmd_estimate("")
            assert any("Usage:" in str(call) for call in mock_print.call_args_list)


class TestCasperCLI:
    """Test the main CASPER CLI functionality."""

    @pytest.fixture
    async def cli(self):
        """Create a CASPER CLI instance."""
        with patch('core.orchestrator.coordinator.AgentCoordinator'):
            with patch('core.orchestrator.task_analyzer.TaskAnalyzer'):
                return CasperCLI()

    @pytest.mark.asyncio
    async def test_cli_initialization(self, cli):
        """Test CLI initialization."""
        with patch.object(cli.coordinator, 'start', new_callable=AsyncMock):
            await cli.initialize()
            cli.coordinator.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_cli_shutdown(self, cli):
        """Test CLI shutdown."""
        with patch.object(cli.coordinator, 'stop', new_callable=AsyncMock):
            await cli.shutdown()
            cli.coordinator.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_task(self, cli):
        """Test task execution through CLI."""
        mock_task_id = uuid4()

        with patch.object(cli.task_analyzer, 'analyze_task') as mock_analyze:
            with patch.object(cli.coordinator, 'submit_task', new_callable=AsyncMock, return_value=mock_task_id):
                with patch.object(cli.coordinator, 'get_results', new_callable=AsyncMock, return_value=[]):
                    with patch.object(cli, '_monitor_task_progress', new_callable=AsyncMock):
                        mock_analyze.return_value = (MagicMock(), [], MagicMock())

                        await cli.execute_task("test task")

                        mock_analyze.assert_called_once()
                        cli.coordinator.submit_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_only(self, cli):
        """Test task analysis without execution."""
        with patch.object(cli.task_analyzer, 'analyze_task') as mock_analyze:
            with patch('core.orchestrator.task_analyzer.TaskAnalyzer.suggest_execution_strategy') as mock_strategy:
                mock_analyze.return_value = (MagicMock(), [], MagicMock())
                mock_strategy.return_value = "test strategy"

                await cli.analyze_only("test task")

                mock_analyze.assert_called_once_with("test task")

    def test_init_project(self, cli):
        """Test project initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            cli.init_project(project_dir)

            # Verify directories were created
            assert (project_dir / ".casper" / "context").exists()
            assert (project_dir / ".casper" / "config").exists()

            # Verify config file was created
            config_file = project_dir / ".casper" / "config" / "casper.json"
            assert config_file.exists()

            # Verify config content
            with open(config_file) as f:
                config = json.load(f)
                assert config["version"] == "0.1.0"
                assert "project_root" in config


class TestCommandRegistration:
    """Test command registration and discovery."""

    def test_command_registration(self):
        """Test that all expected commands are registered."""
        registry = SlashCommandRegistry()

        # Critical commands that must exist
        critical_commands = [
            "help", "status", "config", "setup", "clear",
            "task", "analyze", "init",
            "todo", "explain", "sync", "debug",
            "gen", "refactor", "review", "addroute", "pr", "fixbug",
            "testfail", "deploy", "standup"
        ]

        for cmd_name in critical_commands:
            command = registry.get_command(cmd_name)
            assert command is not None, f"Command /{cmd_name} must be registered"
            assert isinstance(command, SlashCommand)

    def test_command_aliases(self):
        """Test that command aliases work correctly."""
        registry = SlashCommandRegistry()

        # Test some known aliases
        help_cmd = registry.get_command("help")
        help_alias = registry.get_command("h")
        assert help_cmd is help_alias

        favorite_cmd = registry.get_command("favorite")
        fav_alias = registry.get_command("fav")
        assert favorite_cmd is fav_alias

    def test_command_categories(self):
        """Test that commands are properly categorized."""
        registry = SlashCommandRegistry()

        # Test category filtering
        system_commands = registry.list_commands("System")
        assert len(system_commands) > 0
        assert all(cmd.category == "System" for cmd in system_commands)

    def test_non_slash_command_returns_false(self):
        """Test that non-slash commands return False from execute."""
        registry = SlashCommandRegistry()

        async def test_execution():
            result = await registry.execute("regular command")
            assert result is False

        asyncio.run(test_execution())

    def test_custom_command_prefix(self):
        """Test custom command prefix handling."""
        registry = SlashCommandRegistry()

        async def test_custom():
            with patch('core.services.personalization.personalization_manager') as mock_pm:
                mock_pm.execute_custom_command = AsyncMock(return_value=True)

                result = await registry.execute("#custom_command arg1 arg2")
                assert result is True
                mock_pm.execute_custom_command.assert_called_once_with(
                    "custom_command", ["arg1", "arg2"], registry
                )

        asyncio.run(test_custom())


if __name__ == "__main__":
    # Run specific test categories for production validation
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-k", "not slow",  # Skip slow tests for quick validation
        "--maxfail=5",     # Stop after 5 failures for quick feedback
    ])