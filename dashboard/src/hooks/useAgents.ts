import { useMemo } from 'react';
import { useAgentStore } from '../stores/agentStore';
import { AgentStatus } from '../types';

export function useAgents() {
  const { agents, tasks, metrics } = useAgentStore();

  const list = useMemo(() => Array.from(agents.values()), [agents]);
  const byStatus = useMemo(() => {
    const map: Record<AgentStatus, typeof list> = {
      idle: [], planning: [], building: [], reviewing: [], completed: [], failed: [], blocked: []
    } as any;
    for (const a of list) map[a.status].push(a);
    return map;
  }, [list]);

  return { agents: list, byStatus, tasks: Array.from(tasks.values()), metrics };
}

