"""
Natural Language Processing Module for CASPER Terminal
Agent PHI - Natural Language Parser

Production-grade NLP components for intent parsing and entity extraction.
Integrates with LangChain and ChromaDB for intelligent text processing.

Created: 2025-09-25T14:30:00Z
Agent: PHI - Natural Language Parser
"""

from .intent_parser import IntentParser, EntityMatch, ParsedContext

__all__ = [
    'IntentParser',
    'EntityMatch',
    'ParsedContext'
]

# Module version
__version__ = "1.0.0"