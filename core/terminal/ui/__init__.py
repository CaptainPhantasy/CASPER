"""
Terminal UI module for CASPER Prime.

This module provides the interactive terminal user interface implementation
with multi-pane layout, streaming support, and advanced input handling.
"""

from .terminal_ui import TerminalUI, create_terminal_ui, PaneState

__all__ = [
    "TerminalUI",
    "create_terminal_ui",
    "PaneState"
]

# Version information
__version__ = "1.0.0"
__author__ = "CASPER Prime Terminal Squad"