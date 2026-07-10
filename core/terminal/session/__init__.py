"""
Terminal Session Management Module

Provides production-ready persistent coding session management with:
- Complete ISession interface implementation
- SQLite persistence with automatic recovery
- Context accumulation up to 200k tokens
- Thread-safe concurrent operations
- Comprehensive metrics and health monitoring
"""

from .coding_session import CodingSession, TokenizedInteraction, SessionMetrics

__all__ = ['CodingSession', 'TokenizedInteraction', 'SessionMetrics']

# Version info
__version__ = '1.0.0'
__author__ = 'CASPER Prime Terminal Squad'
__description__ = 'Production-ready persistent coding session manager'