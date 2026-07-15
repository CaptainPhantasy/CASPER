import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { detectGatewayDialect, streamModelCompletion } from './modelGateway';


describe('modelGateway', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('detects OpenCode Go dialects from the model schema', () => {
    expect(detectGatewayDialect({ provider: 'opencode-go', model: 'minimax-m2.7' })).toBe('anthropic');
    expect(detectGatewayDialect({ provider: 'minimax', model: 'MiniMax-M2.7-highspeed' })).toBe('openai');
    expect(detectGatewayDialect({ provider: 'opencode-go', model: 'glm-5.2' })).toBe('openai');
    expect(detectGatewayDialect({ provider: 'opencode-zen', model: 'gpt-5.5' })).toBe('responses');
  });

  it('parses normalized SSE split across network chunks', async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode('event: delta\ndata: {"type":"delta","text":"he'));
        controller.enqueue(encoder.encode('llo"}\n\nevent: done\ndata: {"type":"done"}\n\n'));
        controller.close();
      },
    });
    vi.mocked(fetch).mockResolvedValue(new Response(stream, { status: 200 }));

    const events = [];
    for await (const event of streamModelCompletion({
      provider: 'opencode-go',
      model: 'glm-5.2',
      messages: [{ role: 'user', content: 'hello' }],
    })) {
      events.push(event);
    }
    expect(events).toEqual([{ type: 'delta', text: 'hello' }, { type: 'done' }]);
  });

  it('preserves the relay status and vendor error payload', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(
      JSON.stringify({ error: { message: 'vendor rate limit', code: 'rate_limit' } }),
      { status: 429, headers: { 'content-type': 'application/json' } },
    ));

    const consume = async () => {
      for await (const _ of streamModelCompletion({
        provider: 'opencode-go',
        model: 'glm-5.2',
        messages: [{ role: 'user', content: 'hello' }],
      })) {
        // Consume the iterator to surface the request failure.
      }
    };
    await expect(consume()).rejects.toMatchObject({
      status: 429,
      payload: { error: { message: 'vendor rate limit', code: 'rate_limit' } },
    });
  });

  it('cancels the browser stream when the consumer stops early', async () => {
    const cancel = vi.fn();
    const encoder = new TextEncoder();
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode('event: delta\ndata: {"type":"delta","text":"one"}\n\n'));
      },
      cancel,
    });
    vi.mocked(fetch).mockResolvedValue(new Response(stream, { status: 200 }));

    for await (const _ of streamModelCompletion({
      provider: 'opencode-go',
      model: 'glm-5.2',
      messages: [{ role: 'user', content: 'hello' }],
    })) {
      break;
    }
    expect(cancel).toHaveBeenCalledOnce();
  });
});
