import { SettingsPayload, TaskAnalysisResult, WorkspaceInfo } from '@/types';
export type { TaskAnalysisResult };

// Use Vite proxy in development and same-origin in production
export const API_BASE = '';

const jsonHeaders = { 'Content-Type': 'application/json' } as const;

const ensureOk = async (res: Response) => {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const payload = await res.json();
      detail = payload?.detail || payload?.message || detail;
    } catch (_) {
      /* ignore JSON parse errors */
    }
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res;
};

const toNumber = (value: unknown): number | null => {
  if (value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

export interface OpenWorkspaceResult {
  info: WorkspaceInfo;
  fileTree: any[];
}

export const submitTask = async (
  description: string,
  priority: 'low' | 'medium' | 'high' = 'medium',
) => {
  if (!description.trim()) {
    throw new Error('Task description is required');
  }

  const candidates = ['/api/tasks', '/api/task'];
  let failure: unknown = null;

  for (const path of candidates) {
    try {
      const body = path.endsWith('tasks')
        ? { description, priority }
        : { task: description, priority };
      const res = await fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: jsonHeaders,
        body: JSON.stringify(body),
      });
      await ensureOk(res);
      return res.json().catch(() => ({}));
    } catch (error) {
      failure = error;
    }
  }

  throw (failure ?? new Error('Failed to submit task'));
};

export const analyzeTask = async (description: string): Promise<TaskAnalysisResult> => {
  const trimmed = description.trim();
  if (!trimmed) {
    throw new Error('Please describe the task before requesting an analysis.');
  }

  const res = await fetch(`${API_BASE}/api/task/analyze`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ task: trimmed }),
  });
  await ensureOk(res);

  const data = await res.json();
  const metrics = {
    complexity: (data?.complexity ?? 'medium') as TaskAnalysisResult['metrics']['complexity'],
    linesOfCode: toNumber(data?.metrics?.linesOfCode ?? data?.linesOfCode ?? null),
    files: toNumber(data?.metrics?.files ?? data?.files ?? null),
    components: toNumber(data?.metrics?.components ?? data?.components ?? null),
    integrationPoints: toNumber(data?.metrics?.integrationPoints ?? data?.integrationPoints ?? null),
    externalDependencies: toNumber(data?.metrics?.externalDependencies ?? data?.externalDependencies ?? null),
    estimatedTokens: toNumber(data?.metrics?.estimatedTokens ?? data?.estimatedTokens ?? null),
    suggestedPriority: data?.metrics?.suggestedPriority ?? data?.suggestedPriority ?? undefined,
    requiredAgents: Array.isArray(data?.metrics?.requiredAgents)
      ? data.metrics.requiredAgents.map((role: unknown) => String(role))
      : Array.isArray(data?.requiredAgents)
      ? data.requiredAgents.map((role: unknown) => String(role))
      : undefined,
  } as TaskAnalysisResult['metrics'];

  return { metrics, source: 'api' };
};

export const getFileTree = async () => {
  const res = await fetch(`${API_BASE}/api/workspace/filetree`);
  await ensureOk(res);
  return res.json();
};

export const getFileContent = async (path: string) => {
  const res = await fetch(`${API_BASE}/api/workspace/file`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ path }),
  });
  await ensureOk(res);
  return res.json();
};

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const getWorkspaceInfoWithRetry = async (retries = 5): Promise<WorkspaceInfo> => {
  let attempt = 0;
  let delay = 300;
  for (;;) {
    try {
      return await getWorkspaceInfo();
    } catch (error) {
      attempt += 1;
      if (attempt >= retries) {
        throw error;
      }
      await sleep(delay);
      delay = Math.min(delay * 2, 2000);
    }
  }
};

export const openWorkspace = async (path: string): Promise<OpenWorkspaceResult> => {
  const res = await fetch(`${API_BASE}/api/workspace/open`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ path }),
  });
  const payload = await ensureOk(res).then((r) => r.json());
  const info = await getWorkspaceInfoWithRetry();
  return { info, fileTree: payload?.file_tree ?? [] };
};

export const getWorkspaceInfo = async (): Promise<WorkspaceInfo> => {
  const res = await fetch(`${API_BASE}/api/workspace/info`);
  await ensureOk(res);
  return res.json();
};

export const getRecentWorkspaces = async () => {
  const res = await fetch(`${API_BASE}/api/workspace/recent`);
  await ensureOk(res);
  return res.json();
};

export const searchWorkspace = async (query: string, limit = 20) => {
  const params = new URLSearchParams({ query, limit: String(limit) });
  const res = await fetch(`${API_BASE}/api/workspace/search?${params.toString()}`);
  await ensureOk(res);
  return res.json();
};

export const getSettings = async (): Promise<SettingsPayload> => {
  const res = await fetch(`${API_BASE}/api/settings`);
  await ensureOk(res);
  return res.json();
};

export const updateSettings = async (payload: SettingsPayload) => {
  const res = await fetch(`${API_BASE}/api/settings`, {
    method: 'PUT',
    headers: jsonHeaders,
    body: JSON.stringify(payload),
  });
  await ensureOk(res);
  return res.json();
};

export const getAgentStatus = async () => {
  const res = await fetch(`${API_BASE}/api/status`);
  await ensureOk(res);
  return res.json();
};

export const getTaskResults = async (limit = 10) => {
  const res = await fetch(`${API_BASE}/api/results?limit=${limit}`);
  await ensureOk(res);
  return res.json();
};

export const approveOperation = async (approvalId: string) => {
  const res = await fetch(`${API_BASE}/api/approvals/${approvalId}/approve`, {
    method: 'POST',
    headers: jsonHeaders,
  });
  await ensureOk(res);
  return res.json();
};

export const rejectOperation = async (approvalId: string) => {
  const res = await fetch(`${API_BASE}/api/approvals/${approvalId}/reject`, {
    method: 'POST',
    headers: jsonHeaders,
  });
  await ensureOk(res);
  return res.json();
};

export const getAgents = async () => {
  const res = await fetch(`${API_BASE}/api/agents`);
  await ensureOk(res);
  return res.json();
};

export const getTask = async (taskId: string) => {
  const endpoints = [`/api/tasks/${taskId}`, `/api/task/${taskId}`];
  for (const path of endpoints) {
    const res = await fetch(`${API_BASE}${path}`);
    if (res.ok) return res.json();
  }
  throw new Error('Failed to fetch task');
};
