export type AgentType = 'Master' | 'Frontend' | 'Backend' | 'Testing' | 'DevOps' | 'Worker';

export type AgentRole = 'master' | 'frontend_prime' | 'backend_prime' | 'testing_prime' | 'devops_prime' | 'worker';

export type AgentStatus = 'idle' | 'planning' | 'building' | 'reviewing' | 'completed' | 'failed' | 'blocked';

export interface TokenUsage {
  current: number;
  limit: number;
  efficiency: number; // 0-100
}

export interface Decision {
  decision: string;
  rationale: string;
  timestamp?: string;
}

export interface Agent {
  id: string;
  role: AgentRole;
  type: AgentType;
  status: AgentStatus;
  currentTask?: string;
  progress: number; // 0-100
  tokenUsage: TokenUsage;
  startedAt?: number; // epoch ms
  updatedAt?: number; // epoch ms
  efficiencyScore?: number; // derived/fallback
  decisions?: Decision[];
}

export type TaskStatus = 'queued' | 'planning' | 'building' | 'reviewing' | 'shipped' | 'pending' | 'running' | 'completed' | 'failed';

export interface Task {
  id: string;
  description: string;
  status: TaskStatus;
  priority: 'high' | 'medium' | 'low';
  assignedAgents: string[];
  tokenUsage: number;
  createdAt: string;
  completedAt?: string;
}

export interface Metrics {
  totalTokens: number;
  costUSD: number | null;
  efficiencyVsSingle: number | null;
  activeAgents: number;
  contextHandoffs: number;
  avgCompletionMs: number | null;
}

export interface ApprovalItem {
  id: string;
  type: 'file_create' | 'file_edit' | 'file_delete' | 'command_execute' | 'api_call';
  agentId: string;
  description: string;
  details: {
    path?: string;
    command?: string;
    endpoint?: string;
    diff?: {
      before: string;
      after: string;
    };
  };
  timestamp: string;
  status: 'pending' | 'approved' | 'rejected';
  riskLevel: 'low' | 'medium' | 'high';
}

export type WSMessageType =
  | 'agent_spawned'
  | 'agent_progress'
  | 'agent_completed'
  | 'context_handoff'
  | 'error'
  | 'warning'
  | 'agent_update'
  | 'task_update'
  | 'task_submitted'
  | 'task_progress'
  | 'context_update'
  | 'connection'
  | 'heartbeat'
  | 'approval_request'
  | 'approval_resolved'
  | 'command_started'
  | 'command_completed'
  | 'terminal_output'
  | 'file_changed'
  | 'test_result'
  | 'build_result'
  | 'deployment_result'
  | 'ai_suggestion'
  | 'business_document_ready'
  | 'system_status';

export interface WSAgentUpdate {
  // Allow the known message types while remaining forward-compatible with
  // any additional backend event names.
  type: WSMessageType | (string & {});
  agent_id?: string;
  id?: string; // some backends use id
  data?: {
    status?: AgentStatus;
    progress?: number;
    token_usage?: TokenUsage;
    tokenUsage?: TokenUsage | number; // raw number fallback
    decisions?: Decision[];
    context_size?: number;
    approval?: ApprovalItem;
    // Action / approval lifecycle
    action?: string;
    approval_id?: string;
    // Command execution
    command?: string;
    success?: boolean;
    // File / test / build / deploy events
    file_path?: string;
    test_type?: string;
    build_target?: string;
    environment?: string;
    // AI / business document events
    suggestion?: string;
    document_type?: string;
    // Forward-compatibility for additional backend payload fields
    [key: string]: unknown;
  };
  message?: string;
  status?: AgentStatus | string;
  progress?: number;
  tokenUsage?: number;
  timestamp?: string;
  description?: string;
  priority?: string;
}

export interface TaskAnalysisMetrics {
  complexity: 'low' | 'medium' | 'high';
  linesOfCode?: number | null;
  files?: number | null;
  components?: number | null;
  integrationPoints?: number | null;
  externalDependencies?: number | null;
  suggestedPriority?: 'low' | 'medium' | 'high';
  estimatedTokens?: number | null;
  requiredAgents?: string[];
}

export interface TaskAnalysisResult {
  metrics: TaskAnalysisMetrics;
  source: 'api';
}

export interface RecentWorkspace {
  path: string;
  name: string;
  last_opened: string;
  language: string;
  framework: string;
  file_count: number;
}

export interface ProjectAnalysis {
  total_files: number;
  total_directories: number;
  file_types: Record<string, number>;
  largest_files: Array<{ path: string; size: number }>;
  recent_files: Array<{ path: string; modified: string }>;
}

export interface WorkspaceMetadata {
  name: string;
  path: string;
  created_at?: string;
  language?: string;
  framework?: string;
}

export interface SettingsPayload {
  general: Record<string, any>;
  agents: Record<string, any>;
  repository: Record<string, any>;
}

export interface WorkspaceInfo {
  workspace: WorkspaceMetadata;
  current_path: string;
  analysis: ProjectAnalysis;
  settings: SettingsPayload;
  recent: RecentWorkspace[];
}
