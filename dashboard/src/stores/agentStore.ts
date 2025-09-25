import { create } from 'zustand';
import { Agent, AgentRole, AgentStatus, ApprovalItem, Metrics, Task, TokenUsage, WSAgentUpdate } from '../types';

type Maps<T> = Map<string, T>;

interface AgentStoreState {
  agents: Maps<Agent>;
  tasks: Maps<Task>;
  metrics: Metrics;
  handoffs: number;
  approvalQueue: ApprovalItem[];

  // actions
  spawnAgent: (agent: Agent) => void;
  updateAgent: (id: string, update: Partial<Agent>) => void;
  upsertTask: (task: Task) => void;
  submitTask: (description: string, priority?: 'low' | 'medium' | 'high') => Promise<void>;
  applyWS: (message: WSAgentUpdate) => void;
  setMetrics: (metrics: Partial<Metrics>) => void;
  addApproval: (item: ApprovalItem) => void;
  updateApproval: (id: string, status: 'approved' | 'rejected') => Promise<void>;
  removeApproval: (id: string) => void;
  fetchPendingApprovals: () => Promise<void>;
  reset: () => void;
}

const roleToType = (role: AgentRole): Agent['type'] => {
  switch (role) {
    case 'master':
      return 'Master';
    case 'frontend_prime':
      return 'Frontend';
    case 'backend_prime':
      return 'Backend';
    case 'testing_prime':
      return 'Testing';
    case 'devops_prime':
      return 'DevOps';
    default:
      return 'Worker';
  }
};

const defaultTokenUsage: TokenUsage = { current: 0, limit: 1000000, efficiency: 0 };

const initialState: Omit<AgentStoreState, 'spawnAgent' | 'updateAgent' | 'upsertTask' | 'submitTask' | 'applyWS' | 'setMetrics' | 'addApproval' | 'updateApproval' | 'removeApproval' | 'fetchPendingApprovals' | 'reset'> = {
  agents: new Map(),
  tasks: new Map(),
  handoffs: 0,
  approvalQueue: [],
  metrics: {
    totalTokens: 0,
    costUSD: null,
    efficiencyVsSingle: null,
    activeAgents: 0,
    contextHandoffs: 0,
    avgCompletionMs: null,
  },
};

export const useAgentStore = create<AgentStoreState>((set, _get) => ({
  ...initialState,

  spawnAgent: (agent) => set((state) => {
    const agents = new Map(state.agents);
    agents.set(agent.id, {
      ...agent,
      tokenUsage: agent.tokenUsage || defaultTokenUsage,
      startedAt: agent.startedAt || Date.now(),
      updatedAt: Date.now(),
    });
    return { agents };
  }),

  updateAgent: (id, update) => set((state) => {
    const agents = new Map(state.agents);
    const existing = agents.get(id);
    if (!existing) return {} as any;

    // derive efficiency if not provided
    const tokenUsage = update.tokenUsage || existing.tokenUsage || defaultTokenUsage;
    const efficiencyScore = update.efficiencyScore ?? existing.efficiencyScore ?? (existing.progress > 0 && (tokenUsage.current > 0)
      ? Math.min(100, Math.max(0, (existing.progress / Math.max(1, tokenUsage.current)) * 10000))
      : 0);

    agents.set(id, {
      ...existing,
      ...update,
      tokenUsage,
      efficiencyScore,
      updatedAt: Date.now(),
    });
    return { agents };
  }),

  upsertTask: (task) => set((state) => {
    const tasks = new Map(state.tasks);
    tasks.set(task.id, task);
    return { tasks };
  }),

  submitTask: async (description: string, priority: 'low' | 'medium' | 'high' = 'medium') => {
    const { submitTask } = await import('../services/api');
    await submitTask(description, priority);
  },

  setMetrics: (metrics) => set((state) => {
    const merged = { ...state.metrics, ...metrics };
    return { metrics: merged };
  }),

  addApproval: (item) => set((state) => ({
    approvalQueue: [...state.approvalQueue, item]
  })),

  updateApproval: async (id: string, status: 'approved' | 'rejected') => {
    const { approveOperation, rejectOperation } = await import('../services/api');

    if (status === 'approved') {
      await approveOperation(id);
    } else {
      await rejectOperation(id);
    }

    set((state) => ({
      approvalQueue: state.approvalQueue.map(item =>
        item.id === id ? { ...item, status } : item
      )
    }));
  },

  removeApproval: (id) => set((state) => ({
    approvalQueue: state.approvalQueue.filter(item => item.id !== id)
  })),

  fetchPendingApprovals: async () => {
    try {
      const response = await fetch('/api/approvals');
      if (!response.ok) return;

      const data = await response.json();
      const pending = data.pending || [];

      const approvals: ApprovalItem[] = pending.map((item: any) => ({
        id: item.id,
        type: item.operation_type === 'create' ? 'file_create' : 'file_edit',
        agentId: item.agent_id,
        description: `${item.operation_type} ${item.path}`,
        details: {
          path: item.path,
          diff: item.content ? {
            before: '',
            after: item.content.substring(0, 500) + (item.content.length > 500 ? '...' : '')
          } : undefined
        },
        timestamp: item.created_at,
        status: item.status as 'pending' | 'approved' | 'rejected',
        riskLevel: 'medium' as const
      }));

      set((state) => ({
        approvalQueue: [
          ...state.approvalQueue.filter(existing =>
            !approvals.find(newItem => newItem.id === existing.id)
          ),
          ...approvals
        ]
      }));
    } catch (error) {
      console.error('Failed to fetch pending approvals:', error);
    }
  },

  applyWS: (msg) => set((state) => {
    const agents = new Map(state.agents);
    const tasks = new Map(state.tasks);
    let { metrics, handoffs, approvalQueue } = state;

    const now = Date.now();

    const normalizeTokenUsage = (tu?: any): TokenUsage => {
      if (!tu) return defaultTokenUsage;
      if (typeof tu === 'number') return { current: tu, limit: 1000000, efficiency: 0 };
      if ('current' in tu) return tu as TokenUsage;
      if ('tokenUsage' in tu && typeof tu.tokenUsage === 'number')
        return { current: tu.tokenUsage, limit: 1000000, efficiency: 0 };
      return defaultTokenUsage;
    };

    const id = msg.agent_id || msg.id;

    switch (msg.type) {
      case 'agent_spawned': {
        if (id) {
          const role = (msg as any).role as AgentRole | undefined;
          const status: AgentStatus = 'idle';
          agents.set(id, {
            id,
            role: role || 'worker',
            type: roleToType(role || 'worker'),
            status,
            currentTask: '',
            progress: 0,
            tokenUsage: normalizeTokenUsage(msg.data?.token_usage || msg.data?.tokenUsage),
            startedAt: now,
            updatedAt: now,
            decisions: [],
          });
        }
        break;
      }
      case 'agent_progress':
      case 'agent_update': {
        if (!id) break;
        const existing = agents.get(id) || {
          id,
          role: 'worker' as AgentRole,
          type: 'Worker' as Agent['type'],
          status: 'idle' as AgentStatus,
          progress: 0,
          tokenUsage: defaultTokenUsage,
          startedAt: now,
        };
        const status = (msg.data?.status || msg.status || existing.status) as AgentStatus;
        const progress = (msg.data?.progress ?? msg.progress ?? existing.progress) as number;
        const tokenUsage = normalizeTokenUsage(msg.data?.token_usage || msg.data?.tokenUsage || msg.tokenUsage);
        const decisions = msg.data?.decisions || existing.decisions || [];
        agents.set(id, {
          ...existing,
          status,
          progress: typeof progress === 'number' ? progress : existing.progress,
          tokenUsage,
          decisions,
          updatedAt: now,
        });
        break;
      }
      case 'agent_completed': {
        if (!id) break;
        const existing = agents.get(id);
        if (existing) {
          existing.status = 'completed';
          existing.progress = 100;
          existing.updatedAt = now;
          agents.set(id, existing);
        }
        break;
      }
      case 'context_handoff': {
        handoffs += 1;
        break;
      }
      case 'task_update': {
        if (!msg.id) break;
        const status = (msg.status as Task['status']) || 'pending';
        const desc = (msg.description as string) || '';
        const priority = ((msg.priority as string) || 'medium') as Task['priority'];
        const tokenUsage = typeof msg.tokenUsage === 'number' ? msg.tokenUsage : 0;
        const task: Task = {
          id: msg.id,
          description: desc,
          status,
          priority,
          assignedAgents: [],
          tokenUsage,
          createdAt: new Date().toISOString(),
        };
        tasks.set(task.id, task);
        break;
      }
      case 'context_update': {
        // Some backends send metrics periodically
        const totalTokens = (msg as any).total_tokens ?? (msg as any).totalTokens ?? state.metrics.totalTokens;
        const efficiency = (msg as any).efficiency;
        const activeSessions = (msg as any).activeSessions;
        const costUSD = (msg as any).costUSD;
        metrics = {
          ...metrics,
          totalTokens,
          efficiencyVsSingle: typeof efficiency === 'number' ? efficiency : metrics.efficiencyVsSingle,
          contextHandoffs: typeof activeSessions === 'number' ? activeSessions : metrics.contextHandoffs,
          costUSD: typeof costUSD === 'number' ? costUSD : metrics.costUSD,
        };
        // store activeSessions as avgCompletionMs placeholder if needed, or ignore
        break;
      }
      case 'approval_request': {
        // Handle approval request from WebSocket message
        const approval: ApprovalItem = {
          id: (msg as any).id,
          type: 'file_create', // Map operation_type to our types
          agentId: (msg as any).agent_id,
          description: `${(msg as any).operation_type} ${(msg as any).path}`,
          details: {
            path: (msg as any).path,
          },
          timestamp: (msg as any).created_at,
          status: (msg as any).status === 'pending' ? 'pending' : 'approved',
          riskLevel: 'medium', // Default risk level
        };

        // Add content preview if available
        if ((msg as any).content) {
          approval.details.diff = {
            before: '',
            after: (msg as any).content.substring(0, 500) + '...'
          };
        }

        approvalQueue = [...approvalQueue, approval];
        break;
      }
      default:
        break;
    }

    // derive total tokens from agents if available
    const sumTokens = Array.from(agents.values()).reduce((acc, a) => acc + (a.tokenUsage?.current || 0), 0);
    metrics.totalTokens = Math.max(metrics.totalTokens, sumTokens);
    metrics.contextHandoffs = Math.max(metrics.contextHandoffs, handoffs);
    if (typeof (msg as any).costUSD === 'number') {
      const incomingCost = (msg as any).costUSD as number;
      metrics.costUSD = metrics.costUSD === null
        ? incomingCost
        : Math.max(metrics.costUSD, incomingCost);
    }

    metrics.activeAgents = Array.from(agents.values()).filter(a => a.status !== 'completed' && a.status !== 'failed' && a.status !== 'idle').length;

    return { agents, tasks, metrics, handoffs, approvalQueue };
  }),

  reset: () => set(() => ({ ...initialState, agents: new Map(), tasks: new Map(), approvalQueue: [] })),
}));
