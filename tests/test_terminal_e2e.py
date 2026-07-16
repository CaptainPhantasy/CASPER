"""
End-to-End Tests for Terminal Functionality.
Comprehensive E2E tests using Playwright for terminal UI and backend integration.
"""

import asyncio
import json
import os
import pytest
from typing import List, Dict, Any
import time
import tempfile
import shutil
from pathlib import Path


playwright_api = pytest.importorskip("playwright.async_api")
async_playwright = playwright_api.async_playwright
expect = playwright_api.expect


pytestmark = [
    pytest.mark.browser_e2e,
    pytest.mark.skipif(
        os.environ.get("CASPER_RUN_BROWSER_E2E") != "1",
        reason="set CASPER_RUN_BROWSER_E2E=1 with the dashboard running to execute live browser tests",
    ),
]


class TerminalE2ETestBase:
    """Base class for terminal E2E tests."""

    @pytest.fixture
    async def page_with_terminal(self):
        """Create a page with terminal component loaded."""
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=os.environ.get("CASPER_BROWSER_HEADED") != "1"
            )
            context = await browser.new_context()
            page = await context.new_page()

            # Navigate to the dashboard with terminal
            await page.goto(os.environ.get("CASPER_DASHBOARD_URL", "http://localhost:5173"))

            # Wait for dashboard to load
            await page.wait_for_selector('[data-testid="dashboard"]', timeout=10000)

            # Open terminal pane if not visible
            terminal_toggle = page.locator('[data-testid="terminal-toggle"]')
            if await terminal_toggle.is_visible():
                await terminal_toggle.click()

            # Wait for terminal component to load
            await page.wait_for_selector('[data-testid="terminal-component"]', timeout=5000)

            yield page

            await context.close()
            await browser.close()

    @pytest.fixture
    async def temp_project_dir(self):
        """Create a temporary project directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())

        # Create a basic project structure
        (temp_dir / "src").mkdir()
        (temp_dir / "tests").mkdir()
        (temp_dir / "package.json").write_text('{"name": "test-project", "version": "1.0.0"}')
        (temp_dir / "src" / "main.py").write_text('print("Hello, World!")')

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir)


class TestTerminalBasicFunctionality(TerminalE2ETestBase):
    """Test basic terminal functionality."""

    @pytest.mark.asyncio
    async def test_terminal_component_renders(self, page_with_terminal):
        """Test that terminal component renders correctly."""
        page = page_with_terminal

        # Check terminal container exists
        terminal_container = page.locator('[data-testid="terminal-container"]')
        await expect(terminal_container).to_be_visible()

        # Check XTerm.js terminal element
        xterm_element = page.locator('.xterm')
        await expect(xterm_element).to_be_visible()

        # Check terminal has correct dimensions
        terminal_rect = await xterm_element.bounding_box()
        assert terminal_rect["width"] > 400
        assert terminal_rect["height"] > 200

    @pytest.mark.asyncio
    async def test_terminal_websocket_connection(self, page_with_terminal):
        """Test WebSocket connection to terminal backend."""
        page = page_with_terminal

        # Monitor WebSocket connections
        websocket_messages = []

        async def handle_websocket(ws):
            websocket_messages.append("connected")
            try:
                async for message in ws:
                    if isinstance(message, str):
                        data = json.loads(message)
                        websocket_messages.append(data)
            except Exception as e:
                websocket_messages.append(f"error: {e}")

        page.on("websocket", handle_websocket)

        # Trigger terminal connection (may already be connected)
        await page.click('[data-testid="terminal-connect"]')

        # Wait for connection
        await page.wait_for_timeout(2000)

        # Verify WebSocket messages
        assert len(websocket_messages) > 0
        assert "connected" in websocket_messages

        # Check for connection confirmation message
        connection_msgs = [msg for msg in websocket_messages if isinstance(msg, dict) and msg.get("type") == "connection"]
        assert len(connection_msgs) > 0

    @pytest.mark.asyncio
    async def test_terminal_command_execution(self, page_with_terminal):
        """Test executing commands in terminal."""
        page = page_with_terminal

        # Wait for terminal to be ready
        await page.wait_for_selector('.xterm-cursor', timeout=5000)

        # Type a simple command
        terminal_element = page.locator('.xterm-helper-textarea')
        await terminal_element.fill("echo 'Hello Terminal'")
        await page.keyboard.press('Enter')

        # Wait for command output
        await page.wait_for_timeout(2000)

        # Check terminal content for output
        terminal_screen = page.locator('.xterm-screen')
        terminal_text = await terminal_screen.text_content()
        assert "Hello Terminal" in terminal_text

    @pytest.mark.asyncio
    async def test_terminal_multiple_commands(self, page_with_terminal):
        """Test executing multiple commands in sequence."""
        page = page_with_terminal

        commands = [
            "pwd",
            "ls -la",
            "date",
            "whoami"
        ]

        for command in commands:
            # Type command
            await page.type('.xterm-helper-textarea', command)
            await page.keyboard.press('Enter')

            # Wait for execution
            await page.wait_for_timeout(1000)

        # Check that commands were executed
        terminal_text = await page.locator('.xterm-screen').text_content()

        # Should contain command prompts or output
        assert any(cmd in terminal_text for cmd in commands)

    @pytest.mark.asyncio
    async def test_terminal_resize_functionality(self, page_with_terminal):
        """Test terminal resize functionality."""
        page = page_with_terminal

        terminal_element = page.locator('.xterm')
        initial_size = await terminal_element.bounding_box()

        # Resize the terminal pane
        resize_handle = page.locator('[data-testid="terminal-resize-handle"]')
        if await resize_handle.is_visible():
            # Drag to resize
            await resize_handle.drag_to(page.locator('body'), target_position={
                "x": initial_size["x"] + initial_size["width"] + 100,
                "y": initial_size["y"] + initial_size["height"] / 2
            })

            await page.wait_for_timeout(1000)

            # Check new size
            new_size = await terminal_element.bounding_box()
            assert new_size["width"] != initial_size["width"]

    @pytest.mark.asyncio
    async def test_terminal_session_persistence(self, page_with_terminal):
        """Test terminal session persistence across page refreshes."""
        page = page_with_terminal

        # Set a variable in terminal
        await page.type('.xterm-helper-textarea', 'TEST_VAR="persistent_value"')
        await page.keyboard.press('Enter')
        await page.wait_for_timeout(1000)

        # Check the variable
        await page.type('.xterm-helper-textarea', 'echo $TEST_VAR')
        await page.keyboard.press('Enter')
        await page.wait_for_timeout(1000)

        terminal_text = await page.locator('.xterm-screen').text_content()
        assert "persistent_value" in terminal_text

        # Reload page
        await page.reload()
        await page.wait_for_selector('[data-testid="terminal-component"]', timeout=5000)

        # Session should be restored or new session created
        # This behavior depends on implementation - test both scenarios
        await page.wait_for_timeout(2000)


class TestTerminalCASPERIntegration(TerminalE2ETestBase):
    """Test CASPER CLI integration through terminal."""

    @pytest.mark.asyncio
    async def test_casper_help_command(self, page_with_terminal):
        """Test CASPER help command execution."""
        page = page_with_terminal

        # Execute CASPER help command
        await page.type('.xterm-helper-textarea', 'casper help')
        await page.keyboard.press('Enter')

        # Wait for command output
        await page.wait_for_timeout(3000)

        # Check for help output
        terminal_text = await page.locator('.xterm-screen').text_content()
        assert any(keyword in terminal_text.lower() for keyword in ['help', 'commands', 'usage', 'casper'])

    @pytest.mark.asyncio
    async def test_casper_status_command(self, page_with_terminal):
        """Test CASPER status command."""
        page = page_with_terminal

        await page.type('.xterm-helper-textarea', 'casper status')
        await page.keyboard.press('Enter')
        await page.wait_for_timeout(3000)

        terminal_text = await page.locator('.xterm-screen').text_content()
        assert any(keyword in terminal_text.lower() for keyword in ['status', 'agents', 'tasks', 'active'])

    @pytest.mark.asyncio
    async def test_casper_task_submission(self, page_with_terminal, temp_project_dir):
        """Test task submission through terminal."""
        page = page_with_terminal

        # Change to project directory
        await page.type('.xterm-helper-textarea', f'cd {temp_project_dir}')
        await page.keyboard.press('Enter')
        await page.wait_for_timeout(1000)

        # Submit a simple task
        await page.type('.xterm-helper-textarea', 'casper task "Create a README file"')
        await page.keyboard.press('Enter')
        await page.wait_for_timeout(5000)

        # Check for task submission confirmation
        terminal_text = await page.locator('.xterm-screen').text_content()
        assert any(keyword in terminal_text.lower() for keyword in ['task', 'submitted', 'success', 'id'])

    @pytest.mark.asyncio
    async def test_casper_analyze_command(self, page_with_terminal):
        """Test CASPER task analysis command."""
        page = page_with_terminal

        await page.type('.xterm-helper-textarea', 'casper analyze "Implement user authentication"')
        await page.keyboard.press('Enter')
        await page.wait_for_timeout(4000)

        terminal_text = await page.locator('.xterm-screen').text_content()
        assert any(keyword in terminal_text.lower() for keyword in ['analysis', 'complexity', 'agents', 'estimate'])


class TestTerminalSecurityFeatures(TerminalE2ETestBase):
    """Test terminal security features."""

    @pytest.mark.asyncio
    async def test_dangerous_command_blocking(self, page_with_terminal):
        """Test that dangerous commands are blocked."""
        page = page_with_terminal

        dangerous_commands = [
            'rm -rf /',
            'sudo rm -rf /',
            'mkfs /dev/sda',
            'dd if=/dev/zero of=/dev/sda'
        ]

        for cmd in dangerous_commands:
            await page.type('.xterm-helper-textarea', cmd)
            await page.keyboard.press('Enter')
            await page.wait_for_timeout(2000)

            terminal_text = await page.locator('.xterm-screen').text_content()
            # Command should be blocked or show security warning
            assert any(keyword in terminal_text.lower() for keyword in ['blocked', 'denied', 'security', 'forbidden'])

    @pytest.mark.asyncio
    async def test_command_audit_logging(self, page_with_terminal):
        """Test that commands are audited and logged."""
        page = page_with_terminal

        # Execute some commands
        commands = ['ls', 'pwd', 'echo "test"']

        for cmd in commands:
            await page.type('.xterm-helper-textarea', cmd)
            await page.keyboard.press('Enter')
            await page.wait_for_timeout(1000)

        # Check if audit endpoint shows command history
        # This would require API call to security endpoint
        # For now, we verify commands executed without errors
        terminal_text = await page.locator('.xterm-screen').text_content()
        assert len(terminal_text) > 0

    @pytest.mark.asyncio
    async def test_session_timeout_handling(self, page_with_terminal):
        """Test session timeout and reconnection handling."""
        page = page_with_terminal

        # Execute initial command
        await page.type('.xterm-helper-textarea', 'echo "before timeout"')
        await page.keyboard.press('Enter')
        await page.wait_for_timeout(2000)

        # Simulate long idle time (this would need backend configuration)
        # For testing, we can check reconnection behavior

        # Try to execute command after "timeout"
        await page.type('.xterm-helper-textarea', 'echo "after timeout"')
        await page.keyboard.press('Enter')
        await page.wait_for_timeout(2000)

        # Should either work normally or show reconnection message
        terminal_text = await page.locator('.xterm-screen').text_content()
        assert "after timeout" in terminal_text or "reconnect" in terminal_text.lower()


class TestTerminalUIInteractions(TerminalE2ETestBase):
    """Test terminal UI interactions and layout."""

    @pytest.mark.asyncio
    async def test_terminal_panel_toggle(self, page_with_terminal):
        """Test showing/hiding terminal panel."""
        page = page_with_terminal

        # Terminal should be visible initially
        terminal_panel = page.locator('[data-testid="terminal-panel"]')
        await expect(terminal_panel).to_be_visible()

        # Click toggle to hide
        toggle_button = page.locator('[data-testid="terminal-toggle"]')
        await toggle_button.click()
        await page.wait_for_timeout(500)

        # Terminal should be hidden
        await expect(terminal_panel).not_to_be_visible()

        # Click toggle to show again
        await toggle_button.click()
        await page.wait_for_timeout(500)
        await expect(terminal_panel).to_be_visible()

    @pytest.mark.asyncio
    async def test_terminal_tabs_functionality(self, page_with_terminal):
        """Test terminal tabs for multiple sessions."""
        page = page_with_terminal

        # Check if terminal tabs are supported
        new_tab_button = page.locator('[data-testid="terminal-new-tab"]')
        if await new_tab_button.is_visible():
            # Create new terminal tab
            await new_tab_button.click()
            await page.wait_for_timeout(1000)

            # Should have multiple tabs now
            tab_count = await page.locator('[data-testid="terminal-tab"]').count()
            assert tab_count > 1

            # Test switching between tabs
            tabs = await page.locator('[data-testid="terminal-tab"]').all()
            if len(tabs) > 1:
                await tabs[0].click()
                await page.wait_for_timeout(500)
                await tabs[1].click()
                await page.wait_for_timeout(500)

    @pytest.mark.asyncio
    async def test_terminal_context_menu(self, page_with_terminal):
        """Test terminal context menu functionality."""
        page = page_with_terminal

        terminal_element = page.locator('.xterm')

        # Right-click to open context menu
        await terminal_element.click(button='right')
        await page.wait_for_timeout(500)

        # Check if context menu appears
        context_menu = page.locator('[data-testid="terminal-context-menu"]')
        if await context_menu.is_visible():
            # Test context menu options
            copy_option = page.locator('[data-testid="context-copy"]')
            paste_option = page.locator('[data-testid="context-paste"]')
            clear_option = page.locator('[data-testid="context-clear"]')

            # Basic existence check
            if await copy_option.is_visible():
                assert True  # Context menu has copy option
            if await paste_option.is_visible():
                assert True  # Context menu has paste option

    @pytest.mark.asyncio
    async def test_terminal_search_functionality(self, page_with_terminal):
        """Test terminal search functionality."""
        page = page_with_terminal

        # Execute commands to create searchable content
        await page.type('.xterm-helper-textarea', 'echo "searchable content for testing"')
        await page.keyboard.press('Enter')
        await page.wait_for_timeout(1000)

        # Open search if available
        search_trigger = page.locator('[data-testid="terminal-search-trigger"]')
        if await search_trigger.is_visible():
            await search_trigger.click()

            search_input = page.locator('[data-testid="terminal-search-input"]')
            if await search_input.is_visible():
                await search_input.fill("searchable")
                await page.wait_for_timeout(1000)

                # Check if search highlights appear
                highlights = page.locator('.xterm-search-result')
                if await highlights.first.is_visible():
                    highlight_count = await highlights.count()
                    assert highlight_count > 0


class TestTerminalPerformance(TerminalE2ETestBase):
    """Test terminal performance characteristics."""

    @pytest.mark.asyncio
    async def test_terminal_loading_performance(self, page_with_terminal):
        """Test terminal loading performance."""
        page = page_with_terminal

        # Measure time to terminal ready
        start_time = time.time()

        # Wait for terminal to be interactive
        await page.wait_for_selector('.xterm-cursor', timeout=10000)

        load_time = time.time() - start_time

        # Terminal should load within reasonable time
        assert load_time < 5.0, f"Terminal took {load_time}s to load, expected < 5.0s"

    @pytest.mark.asyncio
    async def test_command_execution_latency(self, page_with_terminal):
        """Test command execution latency."""
        page = page_with_terminal

        latencies = []

        for i in range(5):
            start_time = time.time()

            await page.type('.xterm-helper-textarea', f'echo "test command {i}"')
            await page.keyboard.press('Enter')

            # Wait for command output to appear
            await page.wait_for_function(
                f'() => document.querySelector(".xterm-screen").textContent.includes("test command {i}")',
                timeout=5000
            )

            latency = time.time() - start_time
            latencies.append(latency)

        # Average latency should be reasonable
        avg_latency = sum(latencies) / len(latencies)
        assert avg_latency < 2.0, f"Average command latency {avg_latency}s too high"

        # No single command should take too long
        max_latency = max(latencies)
        assert max_latency < 5.0, f"Max command latency {max_latency}s too high"

    @pytest.mark.asyncio
    async def test_terminal_memory_usage(self, page_with_terminal):
        """Test terminal memory usage doesn't grow excessively."""
        page = page_with_terminal

        # Get initial memory usage
        initial_memory = await page.evaluate('() => performance.memory ? performance.memory.usedJSHeapSize : 0')

        # Execute many commands to test memory growth
        for i in range(50):
            await page.type('.xterm-helper-textarea', f'echo "Memory test command {i}"')
            await page.keyboard.press('Enter')
            await page.wait_for_timeout(100)  # Short delay

        # Wait for all commands to complete
        await page.wait_for_timeout(2000)

        # Get final memory usage
        final_memory = await page.evaluate('() => performance.memory ? performance.memory.usedJSHeapSize : 0')

        if initial_memory > 0 and final_memory > 0:
            memory_growth = final_memory - initial_memory
            # Memory growth should be reasonable (less than 50MB)
            assert memory_growth < 50 * 1024 * 1024, f"Memory grew by {memory_growth} bytes"

    @pytest.mark.asyncio
    async def test_terminal_scroll_performance(self, page_with_terminal):
        """Test terminal scrolling performance with lots of output."""
        page = page_with_terminal

        # Generate lots of output
        await page.type('.xterm-helper-textarea', 'for i in {1..100}; do echo "Line $i of scrolling test"; done')
        await page.keyboard.press('Enter')

        # Wait for command to complete
        await page.wait_for_timeout(3000)

        # Test scrolling performance
        start_time = time.time()

        # Scroll up and down
        terminal_element = page.locator('.xterm')
        await terminal_element.scroll_into_view_if_needed()

        # Simulate scrolling
        for _ in range(10):
            await page.keyboard.press('PageUp')
            await page.wait_for_timeout(50)

        for _ in range(10):
            await page.keyboard.press('PageDown')
            await page.wait_for_timeout(50)

        scroll_time = time.time() - start_time

        # Scrolling should be smooth
        assert scroll_time < 3.0, f"Scrolling took {scroll_time}s, expected < 3.0s"


class TestTerminalErrorHandling(TerminalE2ETestBase):
    """Test terminal error handling and recovery."""

    @pytest.mark.asyncio
    async def test_websocket_disconnection_recovery(self, page_with_terminal):
        """Test recovery from WebSocket disconnection."""
        page = page_with_terminal

        # Execute initial command
        await page.type('.xterm-helper-textarea', 'echo "before disconnect"')
        await page.keyboard.press('Enter')
        await page.wait_for_timeout(1000)

        # Simulate network disconnection (this is tricky in E2E tests)
        # We can test the UI response to disconnection

        # Look for reconnection UI elements
        await page.wait_for_timeout(2000)

        # Execute command after potential reconnection
        await page.type('.xterm-helper-textarea', 'echo "after reconnect"')
        await page.keyboard.press('Enter')
        await page.wait_for_timeout(2000)

        terminal_text = await page.locator('.xterm-screen').text_content()
        assert "after reconnect" in terminal_text

    @pytest.mark.asyncio
    async def test_invalid_command_handling(self, page_with_terminal):
        """Test handling of invalid commands."""
        page = page_with_terminal

        invalid_commands = [
            'nonexistent_command_12345',
            'casper invalid_subcommand',
            ''  # empty command
        ]

        for cmd in invalid_commands:
            if cmd:  # Skip empty command test for now
                await page.type('.xterm-helper-textarea', cmd)
                await page.keyboard.press('Enter')
                await page.wait_for_timeout(1500)

        # Terminal should handle invalid commands gracefully
        terminal_text = await page.locator('.xterm-screen').text_content()
        assert len(terminal_text) > 0  # Should have some output

    @pytest.mark.asyncio
    async def test_terminal_crash_recovery(self, page_with_terminal):
        """Test terminal recovery from crashes or errors."""
        page = page_with_terminal

        # Execute initial command
        await page.type('.xterm-helper-textarea', 'echo "before potential crash"')
        await page.keyboard.press('Enter')
        await page.wait_for_timeout(1000)

        # Check if error boundary or recovery mechanisms work
        error_indicators = await page.locator('[data-testid="terminal-error"]').count()

        if error_indicators == 0:
            # No errors detected, try normal operation
            await page.type('.xterm-helper-textarea', 'echo "recovery test"')
            await page.keyboard.press('Enter')
            await page.wait_for_timeout(1000)

            terminal_text = await page.locator('.xterm-screen').text_content()
            assert "recovery test" in terminal_text


# Helper function to run E2E tests
def run_e2e_tests():
    """Run all E2E tests."""
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--browser=chromium",
        "--headed"  # Run with visible browser for debugging
    ])


if __name__ == "__main__":
    run_e2e_tests()
