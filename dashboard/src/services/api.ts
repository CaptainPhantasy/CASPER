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

// Terminal Command Execution
export const executeCommand = async (command: string, args: string[] = [], options: any = {}) => {
  const res = await fetch(`${API_BASE}/api/commands/execute`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ command, args, options }),
  });
  await ensureOk(res);
  return res.json();
};

// Development Commands
export const createComponent = async (type: string, name: string, options: any = {}) => {
  const res = await fetch(`${API_BASE}/api/dev/create`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ type, name, options }),
  });
  await ensureOk(res);
  return res.json();
};

export const runTests = async (testType = 'all', path?: string) => {
  const res = await fetch(`${API_BASE}/api/dev/test`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ testType, path }),
  });
  await ensureOk(res);
  return res.json();
};

export const debugCode = async (file: string, breakpoints: number[] = []) => {
  const res = await fetch(`${API_BASE}/api/dev/debug`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ file, breakpoints }),
  });
  await ensureOk(res);
  return res.json();
};

export const reviewCode = async (files: string[], options: any = {}) => {
  const res = await fetch(`${API_BASE}/api/dev/review`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ files, options }),
  });
  await ensureOk(res);
  return res.json();
};

export const refactorCode = async (target: string, refactorType: string, options: any = {}) => {
  const res = await fetch(`${API_BASE}/api/dev/refactor`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ target, refactorType, options }),
  });
  await ensureOk(res);
  return res.json();
};

export const initProject = async (projectType: string, name: string, options: any = {}) => {
  const res = await fetch(`${API_BASE}/api/dev/init`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ projectType, name, options }),
  });
  await ensureOk(res);
  return res.json();
};

export const buildProject = async (target = 'production', options: any = {}) => {
  const res = await fetch(`${API_BASE}/api/dev/build`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ target, options }),
  });
  await ensureOk(res);
  return res.json();
};

export const deployApplication = async (environment: string, options: any = {}) => {
  const res = await fetch(`${API_BASE}/api/dev/deploy`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ environment, options }),
  });
  await ensureOk(res);
  return res.json();
};

export const rollbackDeployment = async (version?: string) => {
  const res = await fetch(`${API_BASE}/api/dev/rollback`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ version }),
  });
  await ensureOk(res);
  return res.json();
};

export const runMigrations = async (direction = 'up', target?: string) => {
  const res = await fetch(`${API_BASE}/api/dev/migrate`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ direction, target }),
  });
  await ensureOk(res);
  return res.json();
};

export const generateCode = async (template: string, name: string, options: any = {}) => {
  const res = await fetch(`${API_BASE}/api/dev/generate`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ template, name, options }),
  });
  await ensureOk(res);
  return res.json();
};

export const scaffoldProject = async (framework: string, options: any = {}) => {
  const res = await fetch(`${API_BASE}/api/dev/scaffold`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ framework, options }),
  });
  await ensureOk(res);
  return res.json();
};

export const optimizeCode = async (target: string, optimizationType: string) => {
  const res = await fetch(`${API_BASE}/api/dev/optimize`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ target, optimizationType }),
  });
  await ensureOk(res);
  return res.json();
};

export const profilePerformance = async (target: string, duration = 30) => {
  const res = await fetch(`${API_BASE}/api/dev/profile`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ target, duration }),
  });
  await ensureOk(res);
  return res.json();
};

// AI-Powered Commands
export const aiReviewCode = async (files: string[], focusAreas: string[] = []) => {
  const res = await fetch(`${API_BASE}/api/ai/review`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ files, focusAreas }),
  });
  await ensureOk(res);
  return res.json();
};

export const aiCompleteCode = async (file: string, position: { line: number; column: number }) => {
  const res = await fetch(`${API_BASE}/api/ai/complete`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ file, position }),
  });
  await ensureOk(res);
  return res.json();
};

export const aiExplainCode = async (codeSnippet: string, context?: string) => {
  const res = await fetch(`${API_BASE}/api/ai/explain`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ codeSnippet, context }),
  });
  await ensureOk(res);
  return res.json();
};

export const aiSuggestImprovements = async (file: string, analysisType = 'general') => {
  const res = await fetch(`${API_BASE}/api/ai/suggest`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ file, analysisType }),
  });
  await ensureOk(res);
  return res.json();
};

export const aiTranslateCode = async (code: string, fromLanguage: string, toLanguage: string) => {
  const res = await fetch(`${API_BASE}/api/ai/translate`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ code, fromLanguage, toLanguage }),
  });
  await ensureOk(res);
  return res.json();
};

// Business Operations
export const generateInvoice = async (clientInfo: any, items: any[], options: any = {}) => {
  const res = await fetch(`${API_BASE}/api/business/invoice`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ clientInfo, items, options }),
  });
  await ensureOk(res);
  return res.json();
};

export const createProposal = async (clientName: string, projectDescription: string, templateType = 'standard') => {
  const res = await fetch(`${API_BASE}/api/business/proposal`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ clientName, projectDescription, templateType }),
  });
  await ensureOk(res);
  return res.json();
};

export const draftContract = async (contractType: string, parties: any[], terms: any) => {
  const res = await fetch(`${API_BASE}/api/business/contract`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ contractType, parties, terms }),
  });
  await ensureOk(res);
  return res.json();
};

export const generateQuote = async (projectDetails: any, hourlyRate: number) => {
  const res = await fetch(`${API_BASE}/api/business/quote`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ projectDetails, hourlyRate }),
  });
  await ensureOk(res);
  return res.json();
};

export const manageTimesheet = async (action: 'start' | 'stop' | 'view', taskDescription?: string) => {
  const res = await fetch(`${API_BASE}/api/business/timesheet`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ action, taskDescription }),
  });
  await ensureOk(res);
  return res.json();
};

// Testing Commands
export const runUnitTests = async (path?: string, coverage = false) => {
  const res = await fetch(`${API_BASE}/api/test/unit`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ path, coverage }),
  });
  await ensureOk(res);
  return res.json();
};

export const runIntegrationTests = async (services: string[] = []) => {
  const res = await fetch(`${API_BASE}/api/test/integration`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ services }),
  });
  await ensureOk(res);
  return res.json();
};

export const runE2ETests = async (browser = 'chrome', headless = true) => {
  const res = await fetch(`${API_BASE}/api/test/e2e`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ browser, headless }),
  });
  await ensureOk(res);
  return res.json();
};

export const runLoadTests = async (target: string, concurrency = 10, duration = 60) => {
  const res = await fetch(`${API_BASE}/api/test/load`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ target, concurrency, duration }),
  });
  await ensureOk(res);
  return res.json();
};

export const runSecurityTests = async (scanType = 'basic', target?: string) => {
  const res = await fetch(`${API_BASE}/api/test/security`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ scanType, target }),
  });
  await ensureOk(res);
  return res.json();
};

// Utility Commands
export const searchCodebase = async (query: string, fileTypes: string[] = [], caseSensitive = false) => {
  const res = await fetch(`${API_BASE}/api/util/search`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ query, fileTypes, caseSensitive }),
  });
  await ensureOk(res);
  return res.json();
};

export const findAndReplace = async (searchPattern: string, replacement: string, files: string[] = []) => {
  const res = await fetch(`${API_BASE}/api/util/replace`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ searchPattern, replacement, files }),
  });
  await ensureOk(res);
  return res.json();
};

export const formatCode = async (files: string[] = [], formatter = 'prettier') => {
  const res = await fetch(`${API_BASE}/api/util/format`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ files, formatter }),
  });
  await ensureOk(res);
  return res.json();
};

export const lintCode = async (files: string[] = [], autofix = false) => {
  const res = await fetch(`${API_BASE}/api/dev/lint`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ files, autofix }),
  });
  await ensureOk(res);
  return res.json();
};

export const cleanProject = async (target = 'build') => {
  const res = await fetch(`${API_BASE}/api/util/clean`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ target }),
  });
  await ensureOk(res);
  return res.json();
};

export const backupProject = async (includeDependencies = false) => {
  const res = await fetch(`${API_BASE}/api/util/backup`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ includeDependencies }),
  });
  await ensureOk(res);
  return res.json();
};

export const restoreFromBackup = async (backupId: string) => {
  const res = await fetch(`${API_BASE}/api/util/restore`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ backupId }),
  });
  await ensureOk(res);
  return res.json();
};

export const exportData = async (dataType: string, format = 'json') => {
  const res = await fetch(`${API_BASE}/api/util/export`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ dataType, format }),
  });
  await ensureOk(res);
  return res.json();
};

export const importData = async (dataType: string, source: string) => {
  const res = await fetch(`${API_BASE}/api/util/import`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ dataType, source }),
  });
  await ensureOk(res);
  return res.json();
};

export const syncRepositories = async (remotes: string[] = ['origin']) => {
  const res = await fetch(`${API_BASE}/api/util/sync`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ remotes }),
  });
  await ensureOk(res);
  return res.json();
};

// Get pending approvals
export const getPendingApprovals = async () => {
  const res = await fetch(`${API_BASE}/api/approvals`);
  await ensureOk(res);
  return res.json();
};

// Terminal session management
export const createTerminalSession = async () => {
  const res = await fetch(`${API_BASE}/api/terminal/sessions`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({}),
  });
  await ensureOk(res);
  return res.json();
};

export const executeTerminalCommand = async (sessionId: string, command: string) => {
  const res = await fetch(`${API_BASE}/api/terminal/sessions/${sessionId}/command`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ command }),
  });
  await ensureOk(res);
  return res.json();
};

export const getActiveTerminalSessions = async () => {
  const res = await fetch(`${API_BASE}/api/terminal/sessions/active`);
  await ensureOk(res);
  return res.json();
};

export const getTerminalStatus = async () => {
  const res = await fetch(`${API_BASE}/api/terminal/status`);
  await ensureOk(res);
  return res.json();
};

// Approval Mode Management
export const getApprovalMode = async (): Promise<string> => {
  const res = await fetch(`${API_BASE}/api/approvals/mode`);
  await ensureOk(res);
  const data = await res.json();
  return data.mode || 'STRICT';
};

export const setApprovalMode = async (mode: 'STRICT' | 'AUTO' | 'YOLO') => {
  const res = await fetch(`${API_BASE}/api/approvals/mode`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ mode }),
  });
  await ensureOk(res);
  return res.json();
};

export const getApprovalModeStatus = async () => {
  const res = await fetch(`${API_BASE}/api/settings/approval-mode/status`);
  await ensureOk(res);
  return res.json();
};
