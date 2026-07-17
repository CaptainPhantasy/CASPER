/** Dependency-free browser driver for CASPER's same-origin model relay. */

export type GatewayDialect = 'openai' | 'anthropic' | 'responses';
export type GatewayProvider =
  | 'opencode-zen'
  | 'opencode-go'
  | 'openai'
  | 'anthropic'
  | 'minimax'
  | 'custom';

export interface GatewayMessage {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: unknown;
}

export interface GatewayConfig {
  provider: GatewayProvider;
  model: string;
  apiKey?: string;
  baseUrl?: string;
  dialect?: GatewayDialect;
  relayPath?: string;
}

export interface GatewayCompletionRequest extends GatewayConfig {
  messages: GatewayMessage[];
  maxTokens?: number;
  temperature?: number;
  signal?: AbortSignal;
}

export type GatewayEvent =
  | { type: 'delta'; text: string }
  | { type: 'usage'; usage: Record<string, unknown> }
  | { type: 'error'; error: unknown }
  | { type: 'done'; finish_reason?: string };

export const PROVIDER_BASE_URLS: Record<GatewayProvider, string> = {
  'opencode-zen': 'https://opencode.ai/zen/v1',
  'opencode-go': 'https://opencode.ai/zen/go/v1',
  openai: 'https://api.openai.com/v1',
  anthropic: 'https://api.anthropic.com/v1',
  minimax: 'https://api.minimax.io/v1',
  custom: '',
};

export class GatewayError extends Error {
  readonly status: number;
  readonly payload: unknown;

  constructor(status: number, payload: unknown) {
    const message =
      typeof payload === 'object' && payload !== null
        ? String((payload as any)?.error?.message ?? (payload as any)?.message ?? `HTTP ${status}`)
        : String(payload || `HTTP ${status}`);
    super(message);
    this.name = 'GatewayError';
    this.status = status;
    this.payload = payload;
  }
}

export function detectGatewayDialect(config: GatewayConfig): GatewayDialect {
  if (config.dialect) return config.dialect;
  const endpoint = config.baseUrl ?? PROVIDER_BASE_URLS[config.provider];
  if (endpoint.endsWith('/messages')) return 'anthropic';
  if (endpoint.endsWith('/responses')) return 'responses';
  if (endpoint.endsWith('/chat/completions')) return 'openai';
  if (config.provider === 'anthropic') return 'anthropic';

  const model = config.model.toLowerCase();
  if (config.provider !== 'minimax' && /^(anthropic\/|claude-|minimax-m|qwen3\.[67]-)/.test(model)) return 'anthropic';
  if (config.provider === 'opencode-zen' && model.startsWith('gpt-')) return 'responses';
  return 'openai';
}

async function errorPayload(response: Response): Promise<unknown> {
  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function parseFrame(frame: string): GatewayEvent | null {
  const data = frame
    .split('\n')
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trim())
    .join('\n');
  if (!data) return null;
  return JSON.parse(data) as GatewayEvent;
}

export async function* streamModelCompletion(request: GatewayCompletionRequest): AsyncGenerator<GatewayEvent> {
  const relayPath = request.relayPath ?? '/gateway';
  const dialect = detectGatewayDialect(request);
  const controller = new AbortController();

  // Mirror caller cancellation into the fetch owned by this iterator.  When the
  // iterator closes early, the finally block aborts fetch and cancels the reader;
  // that disconnect is what immediately trips the server's upstream watcher.
  const abort = () => controller.abort(request.signal?.reason);
  request.signal?.addEventListener('abort', abort, { once: true });

  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (request.apiKey) {
    if (dialect === 'anthropic') {
      headers['x-api-key'] = request.apiKey;
      headers['anthropic-version'] = '2023-06-01';
    } else {
      headers.Authorization = `Bearer ${request.apiKey}`;
    }
  }

  let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
  try {
    const response = await fetch(relayPath, {
      method: 'POST',
      headers,
      signal: controller.signal,
      body: JSON.stringify({
        provider: request.provider,
        model: request.model,
        messages: request.messages,
        base_url: request.baseUrl,
        dialect,
        stream: true,
        max_tokens: request.maxTokens ?? 2048,
        temperature: request.temperature,
      }),
    });

    if (!response.ok) throw new GatewayError(response.status, await errorPayload(response));
    if (!response.body) throw new GatewayError(response.status, 'Gateway returned no response stream.');

    reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    for (;;) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, '\n');

      let boundary = buffer.indexOf('\n\n');
      while (boundary !== -1) {
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const event = parseFrame(frame);
        if (event) yield event;
        boundary = buffer.indexOf('\n\n');
      }
      if (done) break;
    }

    if (buffer.trim()) {
      const event = parseFrame(buffer);
      if (event) yield event;
    }
  } finally {
    request.signal?.removeEventListener('abort', abort);
    // Cancelling the reader discards queued chunks; aborting fetch closes the
    // browser socket instead of leaving a background generation running.
    await reader?.cancel().catch(() => undefined);
    controller.abort();
  }
}

export async function completeModel(request: GatewayCompletionRequest): Promise<string> {
  let output = '';
  for await (const event of streamModelCompletion(request)) {
    if (event.type === 'delta') output += event.text;
    if (event.type === 'error') throw new GatewayError(502, event.error);
  }
  return output;
}
