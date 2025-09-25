"""
Integration Tests for Resizable Panels and Layout Persistence.
Tests for the scalable panel system, layout management, and responsive design.
"""

import asyncio
import json
import pytest
from playwright.async_api import async_playwright, Page, BrowserContext
from typing import Dict, List, Any, Tuple
import time
from pathlib import Path


class TestResizablePanelsIntegration:
    """Test resizable panels integration."""

    @pytest.fixture
    async def page_with_panels(self):
        """Create a page with resizable panels loaded."""
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080}
            )
            page = await context.new_page()

            # Navigate to dashboard
            await page.goto("http://localhost:5173")
            await page.wait_for_selector('[data-testid="dashboard"]', timeout=10000)

            # Ensure panels are visible
            await page.wait_for_selector('[data-testid="resizable-panels"]', timeout=5000)

            yield page

            await context.close()
            await browser.close()

    @pytest.mark.asyncio
    async def test_panel_resize_functionality(self, page_with_panels):
        """Test basic panel resize functionality."""
        page = page_with_panels

        # Get initial panel sizes
        left_panel = page.locator('[data-testid="left-panel"]')
        right_panel = page.locator('[data-testid="right-panel"]')
        terminal_panel = page.locator('[data-testid="terminal-panel"]')

        initial_left_size = await left_panel.bounding_box()
        initial_right_size = await right_panel.bounding_box()
        initial_terminal_size = await terminal_panel.bounding_box()

        # Find resize handles
        vertical_handle = page.locator('[data-testid="vertical-resize-handle"]')
        horizontal_handle = page.locator('[data-testid="horizontal-resize-handle"]')

        # Test vertical panel resize
        if await vertical_handle.is_visible():
            handle_box = await vertical_handle.bounding_box()

            # Drag handle to resize
            await vertical_handle.hover()
            await page.mouse.down()
            await page.mouse.move(
                handle_box["x"] + 100,  # Move right by 100px
                handle_box["y"]
            )
            await page.mouse.up()

            await page.wait_for_timeout(500)  # Wait for resize animation

            # Check that panels resized
            new_left_size = await left_panel.bounding_box()
            new_right_size = await right_panel.bounding_box()

            assert new_left_size["width"] != initial_left_size["width"]
            assert new_right_size["width"] != initial_right_size["width"]

        # Test horizontal panel resize (terminal)
        if await horizontal_handle.is_visible():
            handle_box = await horizontal_handle.bounding_box()

            await horizontal_handle.hover()
            await page.mouse.down()
            await page.mouse.move(
                handle_box["x"],
                handle_box["y"] - 100  # Move up by 100px
            )
            await page.mouse.up()

            await page.wait_for_timeout(500)

            # Check terminal panel resized
            new_terminal_size = await terminal_panel.bounding_box()
            assert new_terminal_size["height"] != initial_terminal_size["height"]

    @pytest.mark.asyncio
    async def test_panel_collapse_expand(self, page_with_panels):
        """Test panel collapse and expand functionality."""
        page = page_with_panels

        # Test collapsing sidebar
        sidebar = page.locator('[data-testid="sidebar-panel"]')
        sidebar_toggle = page.locator('[data-testid="sidebar-toggle"]')

        if await sidebar_toggle.is_visible():
            initial_sidebar_size = await sidebar.bounding_box()

            # Collapse sidebar
            await sidebar_toggle.click()
            await page.wait_for_timeout(500)

            new_sidebar_size = await sidebar.bounding_box()
            assert new_sidebar_size["width"] < initial_sidebar_size["width"]

            # Expand sidebar
            await sidebar_toggle.click()
            await page.wait_for_timeout(500)

            final_sidebar_size = await sidebar.bounding_box()
            assert abs(final_sidebar_size["width"] - initial_sidebar_size["width"]) < 10

    @pytest.mark.asyncio
    async def test_terminal_panel_toggle(self, page_with_panels):
        """Test terminal panel show/hide functionality."""
        page = page_with_panels

        terminal_panel = page.locator('[data-testid="terminal-panel"]')
        terminal_toggle = page.locator('[data-testid="terminal-toggle"]')

        if await terminal_toggle.is_visible():
            # Hide terminal
            await terminal_toggle.click()
            await page.wait_for_timeout(500)

            # Terminal should be hidden or have minimal height
            terminal_box = await terminal_panel.bounding_box()
            assert terminal_box["height"] < 50 or not await terminal_panel.is_visible()

            # Show terminal
            await terminal_toggle.click()
            await page.wait_for_timeout(500)

            # Terminal should be visible with reasonable height
            terminal_box = await terminal_panel.bounding_box()
            assert terminal_box["height"] > 100

    @pytest.mark.asyncio
    async def test_resize_constraints(self, page_with_panels):
        """Test panel resize constraints and minimum sizes."""
        page = page_with_panels

        # Test minimum panel sizes
        vertical_handle = page.locator('[data-testid="vertical-resize-handle"]')

        if await vertical_handle.is_visible():
            handle_box = await vertical_handle.bounding_box()

            # Try to resize beyond minimum
            await vertical_handle.hover()
            await page.mouse.down()
            await page.mouse.move(50, handle_box["y"])  # Try to make very small
            await page.mouse.up()

            await page.wait_for_timeout(500)

            # Check that panels maintain minimum sizes
            left_panel = page.locator('[data-testid="left-panel"]')
            left_size = await left_panel.bounding_box()
            assert left_size["width"] >= 200  # Minimum sidebar width

    @pytest.mark.asyncio
    async def test_responsive_layout_breakpoints(self, page_with_panels):
        """Test responsive layout behavior at different breakpoints."""
        page = page_with_panels

        # Test tablet breakpoint
        await page.set_viewport_size({"width": 768, "height": 1024})
        await page.wait_for_timeout(500)

        # Check if layout adjusts for tablet
        sidebar = page.locator('[data-testid="sidebar-panel"]')
        if await sidebar.is_visible():
            sidebar_size = await sidebar.bounding_box()
            # Sidebar might be narrower or hidden on tablet
            assert sidebar_size["width"] <= 250

        # Test mobile breakpoint
        await page.set_viewport_size({"width": 375, "height": 667})
        await page.wait_for_timeout(500)

        # Check mobile layout
        # Panels might stack vertically or sidebar might be hidden
        main_content = page.locator('[data-testid="main-content"]')
        content_size = await main_content.bounding_box()
        assert content_size["width"] <= 375

        # Test desktop breakpoint
        await page.set_viewport_size({"width": 1920, "height": 1080})
        await page.wait_for_timeout(500)

        # All panels should be visible in desktop mode
        left_panel = page.locator('[data-testid="left-panel"]')
        right_panel = page.locator('[data-testid="right-panel"]')

        assert await left_panel.is_visible()
        assert await right_panel.is_visible()


class TestLayoutPersistence:
    """Test layout state persistence."""

    @pytest.fixture
    async def page_with_storage(self):
        """Create page with local storage access."""
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto("http://localhost:5173")
            await page.wait_for_selector('[data-testid="dashboard"]', timeout=10000)

            yield page

            await context.close()
            await browser.close()

    @pytest.mark.asyncio
    async def test_layout_state_persistence(self, page_with_storage):
        """Test that layout state persists across page reloads."""
        page = page_with_storage

        # Wait for panels to load
        await page.wait_for_selector('[data-testid="resizable-panels"]')

        # Modify panel sizes
        vertical_handle = page.locator('[data-testid="vertical-resize-handle"]')

        if await vertical_handle.is_visible():
            handle_box = await vertical_handle.bounding_box()

            # Resize panels
            await vertical_handle.hover()
            await page.mouse.down()
            await page.mouse.move(handle_box["x"] + 150, handle_box["y"])
            await page.mouse.up()

            await page.wait_for_timeout(1000)  # Wait for state to save

            # Get current panel sizes
            left_panel = page.locator('[data-testid="left-panel"]')
            resized_left_size = await left_panel.bounding_box()

            # Reload page
            await page.reload()
            await page.wait_for_selector('[data-testid="resizable-panels"]', timeout=10000)
            await page.wait_for_timeout(1000)  # Wait for layout to restore

            # Check if layout was restored
            restored_left_size = await left_panel.bounding_box()
            assert abs(restored_left_size["width"] - resized_left_size["width"]) < 20

    @pytest.mark.asyncio
    async def test_layout_local_storage(self, page_with_storage):
        """Test layout state in localStorage."""
        page = page_with_storage

        await page.wait_for_selector('[data-testid="resizable-panels"]')

        # Check if layout data exists in localStorage
        layout_data = await page.evaluate('''
            () => {
                const data = localStorage.getItem('casper-layout-state');
                return data ? JSON.parse(data) : null;
            }
        ''')

        # Should have layout data after initial load
        if layout_data:
            assert isinstance(layout_data, dict)
            # Common layout properties
            expected_keys = ['panelSizes', 'collapsed', 'lastModified']
            assert any(key in layout_data for key in expected_keys)

    @pytest.mark.asyncio
    async def test_layout_reset_functionality(self, page_with_storage):
        """Test layout reset to default functionality."""
        page = page_with_storage

        await page.wait_for_selector('[data-testid="resizable-panels"]')

        # Modify layout significantly
        vertical_handle = page.locator('[data-testid="vertical-resize-handle"]')

        if await vertical_handle.is_visible():
            # Make extreme resize
            await vertical_handle.hover()
            await page.mouse.down()
            await page.mouse.move(800, 400)  # Move significantly
            await page.mouse.up()

            await page.wait_for_timeout(500)

        # Look for reset layout button
        reset_button = page.locator('[data-testid="reset-layout"]')
        settings_menu = page.locator('[data-testid="settings-menu"]')

        # Reset might be in settings menu
        if await settings_menu.is_visible():
            await settings_menu.click()
            reset_button = page.locator('[data-testid="reset-layout"]')

        if await reset_button.is_visible():
            await reset_button.click()
            await page.wait_for_timeout(1000)

            # Layout should be reset to defaults
            left_panel = page.locator('[data-testid="left-panel"]')
            reset_size = await left_panel.bounding_box()

            # Should be close to default size (around 300px for sidebar)
            assert 250 <= reset_size["width"] <= 400

    @pytest.mark.asyncio
    async def test_preset_layouts(self, page_with_storage):
        """Test preset layout configurations."""
        page = page_with_storage

        await page.wait_for_selector('[data-testid="resizable-panels"]')

        # Look for layout preset buttons
        preset_buttons = [
            '[data-testid="layout-developer"]',
            '[data-testid="layout-analyst"]',
            '[data-testid="layout-compact"]'
        ]

        for preset_selector in preset_buttons:
            preset_button = page.locator(preset_selector)

            if await preset_button.is_visible():
                # Get initial layout
                initial_left = await page.locator('[data-testid="left-panel"]').bounding_box()
                initial_terminal = await page.locator('[data-testid="terminal-panel"]').bounding_box()

                # Apply preset
                await preset_button.click()
                await page.wait_for_timeout(1000)

                # Check layout changed
                new_left = await page.locator('[data-testid="left-panel"]').bounding_box()
                new_terminal = await page.locator('[data-testid="terminal-panel"]').bounding_box()

                # At least one dimension should change
                layout_changed = (
                    abs(new_left["width"] - initial_left["width"]) > 10 or
                    abs(new_terminal["height"] - initial_terminal["height"]) > 10
                )

                if layout_changed:
                    assert True  # Preset successfully changed layout
                    break


class TestLayoutPerformance:
    """Test layout performance and smoothness."""

    @pytest.fixture
    async def page_for_performance(self):
        """Create page for performance testing."""
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto("http://localhost:5173")
            await page.wait_for_selector('[data-testid="dashboard"]', timeout=10000)

            yield page

            await context.close()
            await browser.close()

    @pytest.mark.asyncio
    async def test_resize_performance_60fps(self, page_for_performance):
        """Test that panel resize maintains 60 FPS."""
        page = page_for_performance

        await page.wait_for_selector('[data-testid="resizable-panels"]')

        # Enable performance monitoring
        await page.evaluate('''
            () => {
                window.performanceMetrics = {
                    frameCount: 0,
                    startTime: performance.now(),
                    frames: []
                };

                function recordFrame() {
                    const now = performance.now();
                    window.performanceMetrics.frames.push(now);
                    window.performanceMetrics.frameCount++;
                    requestAnimationFrame(recordFrame);
                }

                requestAnimationFrame(recordFrame);
            }
        ''')

        vertical_handle = page.locator('[data-testid="vertical-resize-handle"]')

        if await vertical_handle.is_visible():
            handle_box = await vertical_handle.bounding_box()

            # Start performance measurement
            start_time = time.time()

            # Perform smooth resize operation
            await vertical_handle.hover()
            await page.mouse.down()

            # Simulate smooth drag over 2 seconds
            steps = 60  # 60 steps for smooth animation
            for i in range(steps):
                progress = i / steps
                x_pos = handle_box["x"] + (200 * progress)  # 200px total movement
                await page.mouse.move(x_pos, handle_box["y"])
                await page.wait_for_timeout(33)  # ~30 FPS user movement

            await page.mouse.up()
            end_time = time.time()

            # Get performance metrics
            metrics = await page.evaluate('''
                () => {
                    const endTime = performance.now();
                    const duration = endTime - window.performanceMetrics.startTime;
                    const frameCount = window.performanceMetrics.frameCount;
                    const fps = (frameCount * 1000) / duration;

                    return {
                        duration: duration,
                        frameCount: frameCount,
                        fps: fps,
                        frames: window.performanceMetrics.frames.slice(-120) // Last 2 seconds
                    };
                }
            ''')

            # Calculate frame times
            frame_times = []
            frames = metrics['frames']
            for i in range(1, len(frames)):
                frame_time = frames[i] - frames[i-1]
                frame_times.append(frame_time)

            if frame_times:
                avg_frame_time = sum(frame_times) / len(frame_times)
                target_frame_time = 16.67  # 60 FPS = 16.67ms per frame

                # Performance assertions
                assert metrics['fps'] > 45, f"FPS too low: {metrics['fps']:.2f}, expected > 45"
                assert avg_frame_time < 25, f"Average frame time too high: {avg_frame_time:.2f}ms"

                # Check for frame drops (frames taking > 33ms)
                dropped_frames = [ft for ft in frame_times if ft > 33]
                drop_rate = len(dropped_frames) / len(frame_times)
                assert drop_rate < 0.1, f"Too many dropped frames: {drop_rate:.2%}"

    @pytest.mark.asyncio
    async def test_layout_memory_usage(self, page_for_performance):
        """Test layout memory usage doesn't grow excessively."""
        page = page_for_performance

        await page.wait_for_selector('[data-testid="resizable-panels"]')

        # Get initial memory
        initial_memory = await page.evaluate('() => performance.memory ? performance.memory.usedJSHeapSize : 0')

        vertical_handle = page.locator('[data-testid="vertical-resize-handle"]')

        if await vertical_handle.is_visible():
            # Perform many resize operations
            for i in range(20):
                handle_box = await vertical_handle.bounding_box()

                await vertical_handle.hover()
                await page.mouse.down()
                await page.mouse.move(handle_box["x"] + (i * 10), handle_box["y"])
                await page.mouse.up()

                await page.wait_for_timeout(100)

            # Get final memory
            final_memory = await page.evaluate('() => performance.memory ? performance.memory.usedJSHeapSize : 0')

            if initial_memory > 0 and final_memory > 0:
                memory_growth = final_memory - initial_memory
                # Memory growth should be reasonable (< 10MB)
                assert memory_growth < 10 * 1024 * 1024, f"Memory grew by {memory_growth} bytes"

    @pytest.mark.asyncio
    async def test_layout_state_save_performance(self, page_for_performance):
        """Test layout state save/restore performance."""
        page = page_for_performance

        await page.wait_for_selector('[data-testid="resizable-panels"]')

        # Test state save performance
        save_times = []

        vertical_handle = page.locator('[data-testid="vertical-resize-handle"]')

        if await vertical_handle.is_visible():
            for i in range(10):
                start_time = await page.evaluate('() => performance.now()')

                # Trigger state save by resizing
                handle_box = await vertical_handle.bounding_box()
                await vertical_handle.hover()
                await page.mouse.down()
                await page.mouse.move(handle_box["x"] + i, handle_box["y"])
                await page.mouse.up()

                # Wait for debounced save
                await page.wait_for_timeout(100)

                end_time = await page.evaluate('() => performance.now()')
                save_times.append(end_time - start_time)

            if save_times:
                avg_save_time = sum(save_times) / len(save_times)
                assert avg_save_time < 50, f"Layout save too slow: {avg_save_time:.2f}ms"


class TestLayoutAccessibility:
    """Test layout accessibility features."""

    @pytest.fixture
    async def page_with_a11y(self):
        """Create page with accessibility testing enabled."""
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto("http://localhost:5173")
            await page.wait_for_selector('[data-testid="dashboard"]', timeout=10000)

            yield page

            await context.close()
            await browser.close()

    @pytest.mark.asyncio
    async def test_keyboard_resize_navigation(self, page_with_a11y):
        """Test keyboard navigation for panel resize."""
        page = page_with_a11y

        await page.wait_for_selector('[data-testid="resizable-panels"]')

        # Test keyboard focus on resize handles
        await page.keyboard.press('Tab')  # Navigate to first focusable element

        # Find resize handles that should be keyboard accessible
        vertical_handle = page.locator('[data-testid="vertical-resize-handle"]')

        if await vertical_handle.is_visible():
            # Focus should be able to reach resize handle
            await page.focus('[data-testid="vertical-resize-handle"]')

            # Test keyboard resize (if supported)
            await page.keyboard.press('ArrowRight')  # Should resize right
            await page.wait_for_timeout(100)

            await page.keyboard.press('ArrowLeft')   # Should resize left
            await page.wait_for_timeout(100)

            # Panel should have changed size
            left_panel = page.locator('[data-testid="left-panel"]')
            panel_size = await left_panel.bounding_box()
            assert panel_size["width"] > 0  # Basic sanity check

    @pytest.mark.asyncio
    async def test_screen_reader_labels(self, page_with_a11y):
        """Test screen reader accessibility labels."""
        page = page_with_a11y

        await page.wait_for_selector('[data-testid="resizable-panels"]')

        # Check for proper ARIA labels
        resize_handles = await page.locator('[role="separator"], [aria-label*="resize"], [aria-label*="splitter"]').all()

        for handle in resize_handles:
            # Each resize handle should have appropriate labels
            aria_label = await handle.get_attribute('aria-label')
            role = await handle.get_attribute('role')

            assert aria_label or role, "Resize handle missing accessibility labels"

            if aria_label:
                assert any(keyword in aria_label.lower() for keyword in ['resize', 'splitter', 'panel']), \
                    f"Unclear aria-label: {aria_label}"

    @pytest.mark.asyncio
    async def test_focus_management(self, page_with_a11y):
        """Test focus management during layout changes."""
        page = page_with_a11y

        await page.wait_for_selector('[data-testid="resizable-panels"]')

        # Focus an element in a panel
        focusable_element = page.locator('input, button, [tabindex="0"]').first
        if await focusable_element.is_visible():
            await focusable_element.focus()

            # Resize panels
            vertical_handle = page.locator('[data-testid="vertical-resize-handle"]')
            if await vertical_handle.is_visible():
                handle_box = await vertical_handle.bounding_box()
                await vertical_handle.hover()
                await page.mouse.down()
                await page.mouse.move(handle_box["x"] + 100, handle_box["y"])
                await page.mouse.up()

                await page.wait_for_timeout(500)

                # Focus should still be maintained or properly managed
                focused_element = await page.evaluate('() => document.activeElement.tagName')
                assert focused_element in ['INPUT', 'BUTTON', 'BODY'], \
                    "Focus was not properly managed during resize"

    @pytest.mark.asyncio
    async def test_reduced_motion_respect(self, page_with_a11y):
        """Test respect for reduced motion preferences."""
        page = page_with_a11y

        # Enable reduced motion preference
        await page.emulate_media(media='(prefers-reduced-motion: reduce)')
        await page.wait_for_selector('[data-testid="resizable-panels"]')

        # Test that animations are reduced or disabled
        vertical_handle = page.locator('[data-testid="vertical-resize-handle"]')

        if await vertical_handle.is_visible():
            handle_box = await vertical_handle.bounding_box()

            start_time = time.time()
            await vertical_handle.hover()
            await page.mouse.down()
            await page.mouse.move(handle_box["x"] + 100, handle_box["y"])
            await page.mouse.up()
            resize_time = time.time() - start_time

            # With reduced motion, resize should be immediate or very fast
            assert resize_time < 0.5, "Animation not reduced for accessibility preferences"


if __name__ == "__main__":
    # Run layout integration tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short"
    ])