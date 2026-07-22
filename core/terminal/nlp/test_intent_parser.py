"""Compatibility tests for the terminal intent parser's LangChain adapter."""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from .intent_parser import IntentParser


class FakeChatModel:
    """Small protocol fake for LangChain's async chat-model interface."""

    def __init__(self) -> None:
        self.messages = []

    async def ainvoke(self, messages):
        self.messages = messages
        return AIMessage(content="create a module\nadd focused tests\nrun verification")


def test_parser_uses_live_working_directory_by_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    parser = IntentParser()
    assert parser.project_root == tmp_path.resolve()


@pytest.mark.asyncio
async def test_llm_completions_use_modern_chat_model_protocol(tmp_path):
    parser = IntentParser(str(tmp_path))
    model = FakeChatModel()
    parser.llm = model

    completions = await parser._generate_llm_completions("cre", {"current_files": []})

    assert completions == [
        "create a module",
        "add focused tests",
        "run verification",
    ]
    assert len(model.messages) == 1
    assert isinstance(model.messages[0], HumanMessage)
