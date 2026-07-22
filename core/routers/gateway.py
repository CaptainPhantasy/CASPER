"""Provider-neutral streaming relay for browser clients.

The browser sends one normalized request to ``/gateway``.  This router chooses
the upstream wire dialect, translates the payload, and relays the response.  It
uses CASPER's existing HTTP stack and no provider SDK, so adding a compatible
endpoint does not add another runtime dependency.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Iterable, List, Literal, Optional, Tuple
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field


router = APIRouter(tags=["model-gateway"])

Dialect = Literal["openai", "anthropic", "responses"]


@dataclass(frozen=True)
class ProviderSpec:
    base_url: str
    dialect: Dialect


PROVIDERS: Dict[str, ProviderSpec] = {
    "opencode-zen": ProviderSpec("https://opencode.ai/zen/v1", "openai"),
    "opencode-go": ProviderSpec("https://opencode.ai/zen/go/v1", "openai"),
    "openai": ProviderSpec("https://api.openai.com/v1", "openai"),
    "anthropic": ProviderSpec("https://api.anthropic.com/v1", "anthropic"),
    "minimax": ProviderSpec("https://api.minimax.io/v1", "openai"),
    "custom": ProviderSpec("", "openai"),
}

# OpenCode currently exposes these families through its Anthropic-compatible
# /messages endpoint.  Explicit request dialects or endpoint suffixes always win.
_ANTHROPIC_MODEL_PREFIXES = (
    "anthropic/",
    "claude-",
    "minimax-m",
    "qwen3.6-",
    "qwen3.7-",
)
_RESPONSES_MODEL_PREFIXES = ("gpt-",)
_TERMINAL_PATHS = ("/chat/completions", "/messages", "/responses")
_FORWARDED_HEADERS = ("authorization", "x-api-key", "anthropic-version")


class GatewayRequest(BaseModel):
    provider: str = "opencode-go"
    model: str
    messages: List[Dict[str, Any]]
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    dialect: Optional[Dialect] = None
    stream: bool = True
    max_tokens: int = Field(default=2048, ge=1, le=131072)
    temperature: Optional[float] = Field(default=None, ge=0, le=2)


def detect_dialect(provider: str, model: str, base_url: str, explicit: Optional[Dialect] = None) -> Dialect:
    """Resolve the wire format from explicit config, URL, provider, then model."""
    if explicit:
        return explicit
    path = urlparse(base_url).path.rstrip("/").lower()
    if path.endswith("/messages"):
        return "anthropic"
    if path.endswith("/responses"):
        return "responses"
    if path.endswith("/chat/completions"):
        return "openai"
    if provider == "anthropic":
        return "anthropic"
    lowered = model.lower()
    if provider != "minimax" and lowered.startswith(_ANTHROPIC_MODEL_PREFIXES):
        return "anthropic"
    if provider == "opencode-zen" and lowered.startswith(_RESPONSES_MODEL_PREFIXES):
        return "responses"
    return PROVIDERS.get(provider, PROVIDERS["custom"]).dialect


def resolve_upstream_url(base_url: str, dialect: Dialect) -> str:
    parsed = urlparse(base_url)
    allow_http = os.environ.get("CASPER_GATEWAY_ALLOW_HTTP") == "1"
    if parsed.scheme not in ({"https", "http"} if allow_http else {"https"}):
        raise ValueError("Gateway base_url must use HTTPS (or enable CASPER_GATEWAY_ALLOW_HTTP=1).")
    if not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("Gateway base_url must be an absolute URL without embedded credentials.")

    allowed_hosts = {h.strip().lower() for h in os.environ.get("CASPER_GATEWAY_ALLOWED_HOSTS", "").split(",") if h.strip()}
    if allowed_hosts and (parsed.hostname or "").lower() not in allowed_hosts:
        raise ValueError("Gateway upstream host is not in CASPER_GATEWAY_ALLOWED_HOSTS.")

    clean = base_url.rstrip("/")
    for suffix in _TERMINAL_PATHS:
        if clean.endswith(suffix):
            clean = clean[: -len(suffix)]
            break
    suffix = {"openai": "/chat/completions", "anthropic": "/messages", "responses": "/responses"}[dialect]
    return clean + suffix


def _system_text(messages: Iterable[Dict[str, Any]]) -> str:
    blocks: List[str] = []
    for message in messages:
        if message.get("role") != "system":
            continue
        content = message.get("content", "")
        if isinstance(content, str):
            blocks.append(content)
        elif isinstance(content, list):
            blocks.extend(str(item.get("text", "")) for item in content if isinstance(item, dict) and item.get("text"))
    return "\n\n".join(block for block in blocks if block)


def build_upstream_payload(request: GatewayRequest, dialect: Dialect) -> Dict[str, Any]:
    non_system = [message for message in request.messages if message.get("role") != "system"]
    common: Dict[str, Any] = {"model": request.model, "stream": request.stream}
    if request.temperature is not None:
        common["temperature"] = request.temperature

    if dialect == "anthropic":
        payload = {**common, "messages": non_system, "max_tokens": request.max_tokens}
        system = _system_text(request.messages)
        if system:
            payload["system"] = system
        return payload

    if dialect == "responses":
        payload = {**common, "input": non_system, "max_output_tokens": request.max_tokens}
        system = _system_text(request.messages)
        if system:
            payload["instructions"] = system
        return payload

    return {**common, "messages": request.messages, "max_tokens": request.max_tokens}


def build_upstream_headers(incoming: Request, request: GatewayRequest, dialect: Dialect) -> Dict[str, str]:
    """Copy supported auth headers byte-for-byte unless translation is required."""
    headers = {name: incoming.headers[name] for name in _FORWARDED_HEADERS if name in incoming.headers}
    key = request.api_key

    if dialect == "anthropic":
        if "x-api-key" not in headers:
            if headers.get("authorization", "").lower().startswith("bearer "):
                headers["x-api-key"] = headers["authorization"][7:]
            elif key:
                headers["x-api-key"] = key
        headers.pop("authorization", None)
        headers.setdefault("anthropic-version", "2023-06-01")
    elif "authorization" not in headers and key:
        headers["authorization"] = f"Bearer {key}"

    headers["content-type"] = "application/json"
    headers["accept"] = "text/event-stream" if request.stream else "application/json"
    return headers


def normalize_sse_event(dialect: Dialect, data: str) -> List[Tuple[str, Dict[str, Any]]]:
    """Convert provider SSE payloads into stable ``delta``, ``usage``, and ``done`` events."""
    if data == "[DONE]":
        return [("done", {"type": "done"})]
    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        return []

    if payload.get("type") == "error" or payload.get("error"):
        return [("error", {"type": "error", "error": payload.get("error", payload)})]

    events: List[Tuple[str, Dict[str, Any]]] = []
    if dialect == "openai":
        choice = (payload.get("choices") or [{}])[0]
        text = (choice.get("delta") or {}).get("content")
        if text:
            events.append(("delta", {"type": "delta", "text": text}))
        if payload.get("usage"):
            events.append(("usage", {"type": "usage", "usage": payload["usage"]}))
        if choice.get("finish_reason"):
            events.append(("done", {"type": "done", "finish_reason": choice["finish_reason"]}))
    elif dialect == "anthropic":
        event_type = payload.get("type")
        text = (payload.get("delta") or {}).get("text") if event_type == "content_block_delta" else None
        if text:
            events.append(("delta", {"type": "delta", "text": text}))
        if event_type == "message_delta" and payload.get("usage"):
            events.append(("usage", {"type": "usage", "usage": payload["usage"]}))
        if event_type == "message_stop":
            events.append(("done", {"type": "done"}))
    else:
        event_type = payload.get("type")
        if event_type == "response.output_text.delta" and payload.get("delta"):
            events.append(("delta", {"type": "delta", "text": payload["delta"]}))
        elif event_type == "response.completed":
            response = payload.get("response") or {}
            if response.get("usage"):
                events.append(("usage", {"type": "usage", "usage": response["usage"]}))
            events.append(("done", {"type": "done"}))
    return events


def _encode_sse(event: str, payload: Dict[str, Any]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n".encode("utf-8")


def _new_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=15.0), follow_redirects=False)


async def _watch_disconnect(request: Request, upstream: httpx.Response, client: httpx.AsyncClient) -> None:
    """Abort the upstream socket promptly when the browser disappears.

    This watcher runs independently of upstream reads, so a stalled provider
    cannot keep billing after the incoming ASGI request has disconnected.
    Closing the response tears down its read stream; closing the client releases
    the pooled socket and any buffered backpressure state.
    """
    while not await request.is_disconnected():
        await asyncio.sleep(0.05)
    await upstream.aclose()
    await client.aclose()


async def _stream_response(
    incoming: Request,
    upstream: httpx.Response,
    client: httpx.AsyncClient,
    dialect: Dialect,
) -> AsyncIterator[bytes]:
    disconnect_watcher = asyncio.create_task(_watch_disconnect(incoming, upstream, client))
    done_sent = False
    try:
        # aiter_lines buffers only the current SSE line.  Each yielded frame is
        # awaited by StreamingResponse, preserving downstream backpressure.
        async for line in upstream.aiter_lines():
            if await incoming.is_disconnected():
                break
            if not line.startswith("data:"):
                continue
            for event, payload in normalize_sse_event(dialect, line[5:].strip()):
                if event == "done" and done_sent:
                    continue
                done_sent = done_sent or event == "done"
                yield _encode_sse(event, payload)
        if not done_sent and not await incoming.is_disconnected():
            yield _encode_sse("done", {"type": "done"})
    except asyncio.CancelledError:
        raise
    except httpx.StreamClosed:
        if not await incoming.is_disconnected():
            raise
    finally:
        disconnect_watcher.cancel()
        await asyncio.gather(disconnect_watcher, return_exceptions=True)
        await upstream.aclose()
        await client.aclose()


@router.post("/gateway")
async def gateway(incoming: Request, body: GatewayRequest):
    spec = PROVIDERS.get(body.provider)
    if not spec and not body.base_url:
        return Response(content=json.dumps({"error": {"message": "Unknown provider and no base_url supplied."}}), status_code=400, media_type="application/json")

    base_url = body.base_url or (spec.base_url if spec else "")
    try:
        dialect = detect_dialect(body.provider, body.model, base_url, body.dialect)
        upstream_url = resolve_upstream_url(base_url, dialect)
        headers = build_upstream_headers(incoming, body, dialect)
        payload = build_upstream_payload(body, dialect)
    except ValueError as error:
        return Response(content=json.dumps({"error": {"message": str(error)}}), status_code=400, media_type="application/json")

    client = _new_client()
    try:
        request = client.build_request("POST", upstream_url, headers=headers, json=payload)
        upstream = await client.send(request, stream=True)
    except httpx.HTTPError as error:
        await client.aclose()
        return Response(content=json.dumps({"error": {"message": str(error), "type": type(error).__name__}}), status_code=502, media_type="application/json")

    # Preserve vendor failures exactly: status, content type, and response bytes.
    if upstream.status_code < 200 or upstream.status_code >= 300:
        content = await upstream.aread()
        content_type = upstream.headers.get("content-type", "application/json")
        await upstream.aclose()
        await client.aclose()
        return Response(content=content, status_code=upstream.status_code, headers={"content-type": content_type})

    if not body.stream:
        content = await upstream.aread()
        content_type = upstream.headers.get("content-type", "application/json")
        await upstream.aclose()
        await client.aclose()
        return Response(content=content, status_code=upstream.status_code, headers={"content-type": content_type})

    return StreamingResponse(
        _stream_response(incoming, upstream, client, dialect),
        status_code=upstream.status_code,
        media_type="text/event-stream",
        headers={"cache-control": "no-cache", "x-accel-buffering": "no"},
    )
