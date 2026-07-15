import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request

from core.routers import gateway as gateway_module
from core.routers.gateway import (
    GatewayRequest,
    PROVIDERS,
    build_upstream_headers,
    build_upstream_payload,
    detect_dialect,
    gateway,
    normalize_sse_event,
    resolve_upstream_url,
    _stream_response,
    _watch_disconnect,
)
from core.services.llm import DEFAULT_SYSTEM_PROMPT, LLMService
from core.services.setup import AIProviders
from core.services.slash_commands import SlashCommandRegistry
from core.services.user_config import user_config
from core.server import app


def request_with_headers(**headers):
    raw = [
        (name.replace("_", "-").encode(), value.encode())
        for name, value in headers.items()
    ]
    return Request(
        {"type": "http", "method": "POST", "path": "/gateway", "headers": raw}
    )


def gateway_request(**overrides):
    data = {
        "provider": "opencode-go",
        "model": "minimax-m2.7",
        "messages": [
            {"role": "system", "content": "Be exact."},
            {"role": "user", "content": "Review this."},
        ],
    }
    data.update(overrides)
    return GatewayRequest(**data)


def test_provider_endpoints_and_minimax_default_are_exact():
    assert PROVIDERS["opencode-zen"].base_url == "https://opencode.ai/zen/v1"
    assert PROVIDERS["opencode-go"].base_url == "https://opencode.ai/zen/go/v1"
    assert AIProviders.PROVIDERS["minimax"].default_model == "MiniMax-M2.7-highspeed"


def test_dialect_detection_and_endpoint_resolution():
    assert (
        detect_dialect("opencode-go", "minimax-m2.7", "https://opencode.ai/zen/go/v1")
        == "anthropic"
    )
    assert (
        detect_dialect("minimax", "MiniMax-M2.7-highspeed", "https://api.minimax.io/v1")
        == "openai"
    )
    assert (
        detect_dialect("opencode-go", "glm-5.2", "https://opencode.ai/zen/go/v1")
        == "openai"
    )
    assert (
        detect_dialect("opencode-zen", "gpt-5.5", "https://opencode.ai/zen/v1")
        == "responses"
    )
    assert resolve_upstream_url("https://opencode.ai/zen/go/v1", "anthropic").endswith(
        "/v1/messages"
    )
    assert (
        resolve_upstream_url("https://example.com/v1/chat/completions", "anthropic")
        == "https://example.com/v1/messages"
    )


def test_anthropic_translation_moves_system_and_auth_headers():
    body = gateway_request(api_key="secret")
    payload = build_upstream_payload(body, "anthropic")
    assert payload["system"] == "Be exact."
    assert [message["role"] for message in payload["messages"]] == ["user"]

    headers = build_upstream_headers(
        request_with_headers(authorization="Bearer original"), body, "anthropic"
    )
    assert headers["x-api-key"] == "original"
    assert headers["anthropic-version"] == "2023-06-01"
    assert "authorization" not in headers


def test_openai_headers_are_forwarded_without_rewriting():
    body = gateway_request(model="glm-5.2")
    headers = build_upstream_headers(
        request_with_headers(authorization="Bearer exact-token"), body, "openai"
    )
    assert headers["authorization"] == "Bearer exact-token"


def test_stream_events_normalize_across_dialects():
    openai = normalize_sse_event(
        "openai", json.dumps({"choices": [{"delta": {"content": "A"}}]})
    )
    anthropic = normalize_sse_event(
        "anthropic", json.dumps({"type": "content_block_delta", "delta": {"text": "B"}})
    )
    responses = normalize_sse_event(
        "responses", json.dumps({"type": "response.output_text.delta", "delta": "C"})
    )
    assert [events[0][1]["text"] for events in (openai, anthropic, responses)] == [
        "A",
        "B",
        "C",
    ]


@pytest.mark.asyncio
async def test_gateway_preserves_upstream_error_status_and_payload(monkeypatch):
    class FakeResponse:
        status_code = 429
        headers = {"content-type": "application/json"}

        async def aread(self):
            return b'{"error":{"message":"vendor rate limit"}}'

        async def aclose(self):
            return None

    class FakeClient:
        def build_request(self, *args, **kwargs):
            return object()

        async def send(self, request, stream=False):
            return FakeResponse()

        async def aclose(self):
            return None

    monkeypatch.setattr(gateway_module, "_new_client", FakeClient)
    response = await gateway(
        request_with_headers(authorization="Bearer key"),
        gateway_request(model="glm-5.2"),
    )
    assert response.status_code == 429
    assert response.body == b'{"error":{"message":"vendor rate limit"}}'


@pytest.mark.asyncio
async def test_disconnect_watcher_immediately_closes_upstream_resources():
    incoming = MagicMock()
    incoming.is_disconnected = AsyncMock(return_value=True)
    upstream = MagicMock()
    upstream.aclose = AsyncMock()
    client = MagicMock()
    client.aclose = AsyncMock()

    await _watch_disconnect(incoming, upstream, client)
    upstream.aclose.assert_awaited_once()
    client.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_stream_normalization_closes_resources_and_emits_one_done():
    incoming = MagicMock()
    incoming.is_disconnected = AsyncMock(return_value=False)

    class Upstream:
        def __init__(self):
            self.closed = False

        async def aiter_lines(self):
            yield 'data: {"choices":[{"delta":{"content":"ok"}}]}'
            yield 'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}'
            yield "data: [DONE]"

        async def aclose(self):
            self.closed = True

    class Client:
        def __init__(self):
            self.closed = False

        async def aclose(self):
            self.closed = True

    upstream = Upstream()
    client = Client()
    frames = [
        frame async for frame in _stream_response(incoming, upstream, client, "openai")
    ]
    assert sum(frame.startswith(b"event: done") for frame in frames) == 1
    assert b'"text":"ok"' in b"".join(frames)
    assert upstream.closed is True
    assert client.closed is True


@pytest.mark.asyncio
async def test_minimax_uses_compact_verified_default_prompt():
    service = LLMService()
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content="ok"))]
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=response)
    service._minimax = client

    result = await service._call_minimax_with_retry(
        "task", "", "MiniMax-M2.7-highspeed", 50
    )
    assert result == "ok"
    sent = client.chat.completions.create.await_args.kwargs
    assert sent["messages"][0] == {"role": "system", "content": DEFAULT_SYSTEM_PROMPT}
    assert "INCOMPLETE" in DEFAULT_SYSTEM_PROMPT
    assert len(DEFAULT_SYSTEM_PROMPT) < 300


@pytest.mark.asyncio
async def test_selected_opencode_provider_keeps_its_minimax_model_on_go():
    service = LLMService()
    service.opencode_go_key = "test-key"
    service._minimax = MagicMock()
    with (
        patch.object(user_config, "get_default_provider", return_value="opencode-go"),
        patch.object(
            service,
            "_call_opencode_with_retry",
            new_callable=AsyncMock,
            return_value="go response",
        ) as go_call,
        patch.object(
            service, "_call_minimax_with_retry", new_callable=AsyncMock
        ) as native_call,
    ):
        result = await service.complete("task", model="minimax-m2.7")
    assert result == "go response"
    assert go_call.await_args.args[0] == "opencode-go"
    native_call.assert_not_awaited()


def test_familiar_agent_commands_are_registered():
    registry = SlashCommandRegistry()
    for name in ("goal", "model", "plan", "diff", "pwd", "review", "status", "init"):
        assert registry.get_command(name) is not None


def test_gateway_is_mounted_on_the_casper_server():
    assert "/gateway" in app.openapi()["paths"]


@pytest.mark.asyncio
async def test_complete_terminal_routes_new_agent_commands():
    from casper_terminal_complete import CasperTerminalComplete

    terminal = CasperTerminalComplete()
    terminal.slash_commands = MagicMock()
    terminal.slash_commands.execute = AsyncMock(return_value=True)
    should_exit = await terminal.handle_command("/goal", "status")
    assert should_exit is False
    terminal.slash_commands.execute.assert_awaited_once_with("/goal status")


@pytest.mark.asyncio
async def test_global_cli_without_subcommand_launches_interactive_terminal(monkeypatch):
    from core import cli as cli_module

    run = AsyncMock()
    terminal = MagicMock()
    terminal.run = run
    monkeypatch.setattr("sys.argv", ["casper"])
    with patch(
        "casper_terminal_complete.CasperTerminalComplete", return_value=terminal
    ):
        await cli_module.main_async()
    run.assert_awaited_once()
