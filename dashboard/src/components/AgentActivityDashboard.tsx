import * as React from "react";
import { useAgentStore } from "@/stores/agentStore";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { getAgentStatus, getTaskResults } from "@/services/api";
import {
  Activity,
  AlertCircle,
  CheckCircle,
  Clock,
  Cpu,
  Zap,
  TrendingUp,
  Users,
  FileText,
  Loader2
} from "lucide-react";
import { cn } from "@/lib/utils";

interface TaskResult {
  id: string;
  description: string;
  status: 'completed' | 'failed' | 'in_progress';
  timestamp: string;
  agentId?: string;
  tokenUsage?: number;
}

interface AgentStatusData {
  agents: Array<{
    id: string;
    name: string;
    status: 'active' | 'idle' | 'error';
    currentTask?: string;
    progress?: number;
    tokenUsage?: number;
  }>;
  metrics?: {
    totalTokens: number;
    activeAgents: number;
    completedTasks: number;
    averageTime?: number;
  };
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'active':
    case 'working':
      return <Loader2 className="h-3 w-3 animate-spin" />;
    case 'completed':
      return <CheckCircle className="h-3 w-3 text-green-500" />;
    case 'failed':
    case 'error':
      return <AlertCircle className="h-3 w-3 text-red-500" />;
    case 'idle':
      return <Clock className="h-3 w-3 text-muted-foreground" />;
    default:
      return <Activity className="h-3 w-3" />;
  }
};

const getStatusBadgeVariant = (status: string): "default" | "secondary" | "outline" | "destructive" => {
  switch (status) {
    case 'active':
    case 'working':
      return 'default';
    case 'completed':
      return 'secondary';
    case 'failed':
    case 'error':
      return 'destructive';
    case 'idle':
    default:
      return 'outline';
  }
};

export const AgentActivityDashboard: React.FC = () => {
  const { agents, metrics, tasks } = useAgentStore();
  const [taskHistory, setTaskHistory] = React.useState<TaskResult[]>([]);
  const [apiStatus, setApiStatus] = React.useState<AgentStatusData | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Poll for status updates
  React.useEffect(() => {
    const fetchStatus = async () => {
      try {
        setLoading(true);
        const [statusData, resultsData] = await Promise.allSettled([
          getAgentStatus(),
          getTaskResults(15)
        ]);

        if (statusData.status === 'fulfilled') {
          setApiStatus(statusData.value);
          setError(null);
        } else {
          console.warn('Failed to fetch status:', statusData.reason);
        }

        if (resultsData.status === 'fulfilled' && Array.isArray(resultsData.value)) {
          setTaskHistory(resultsData.value);
        } else if (resultsData.status === 'fulfilled' && resultsData.value?.results) {
          setTaskHistory(resultsData.value.results);
        }
      } catch (err) {
        console.error('Error fetching agent data:', err);
        setError('Unable to connect to backend services');
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, []);

  // Merge store agents with API status
  const activeAgents = React.useMemo(() => {
    const agentList = Array.from(agents.values());
    const apiAgents = apiStatus?.agents || [];

    // Create a map for deduplication
    const agentMap = new Map();

    // Add store agents
    agentList.forEach(agent => {
      if (agent.status !== 'idle' && agent.status !== 'completed') {
        agentMap.set(agent.id, agent);
      }
    });

    // Add API agents (will override store if duplicate)
    apiAgents.forEach(apiAgent => {
      if (apiAgent.status === 'active') {
        agentMap.set(apiAgent.id, {
          id: apiAgent.id,
          role: apiAgent.name?.toLowerCase() || 'worker',
          type: apiAgent.name || 'Worker',
          status: 'working',
          currentTask: apiAgent.currentTask || '',
          progress: apiAgent.progress || 0,
          tokenUsage: { current: apiAgent.tokenUsage || 0, limit: 100000, efficiency: 0 }
        });
      }
    });

    return Array.from(agentMap.values());
  }, [agents, apiStatus]);

  // Calculate aggregated metrics
  const aggregatedMetrics = React.useMemo(() => {
    const storeTokens = metrics.totalTokens || 0;
    const apiTokens = apiStatus?.metrics?.totalTokens || 0;
    const totalTokens = Math.max(storeTokens, apiTokens);

    const costUSD = metrics.costUSD ?? null;
    const efficiency = metrics.efficiencyVsSingle ?? null;

    return {
      totalTokens,
      costUSD,
      activeAgents: activeAgents.length,
      completedTasks: apiStatus?.metrics?.completedTasks || tasks.size,
      efficiency,
    };
  }, [metrics, apiStatus, activeAgents, tasks]);

  return (
    <div className="space-y-4">
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium">Active Agents</CardTitle>
            <Badge variant="secondary" className="gap-1">
              <Users className="h-3 w-3" />
              {activeAgents.length} active
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {activeAgents.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-2">
              No active agents
            </p>
          ) : (
            activeAgents.map((agent) => (
              <div key={agent.id} className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <Cpu className="h-3 w-3 text-muted-foreground" />
                    <span className="font-medium">{agent.type || agent.role}</span>
                  </div>
                  <Badge variant={getStatusBadgeVariant(agent.status)} className="gap-1">
                    {getStatusIcon(agent.status)}
                    {agent.status}
                  </Badge>
                </div>
                {agent.currentTask && (
                  <p className="text-xs text-muted-foreground truncate pl-5">
                    {agent.currentTask}
                  </p>
                )}
                {agent.progress > 0 && (
                  <Progress value={agent.progress} className="h-1.5" />
                )}
                {agent.tokenUsage && agent.tokenUsage.current > 0 && (
                  <div className="flex items-center gap-2 pl-5">
                    <Badge variant="outline" className="text-xs gap-1">
                      <Zap className="h-2.5 w-2.5" />
                      {agent.tokenUsage.current.toLocaleString()} tokens
                    </Badge>
                  </div>
                )}
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium">Metrics Overview</CardTitle>
            <Badge variant="outline" className="gap-1">
              <TrendingUp className="h-3 w-3" />
              Live
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Total Tokens</p>
              <p className="text-lg font-semibold">
                {aggregatedMetrics.totalTokens.toLocaleString()}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Est. Cost</p>
              <p className="text-lg font-semibold">
                {typeof aggregatedMetrics.costUSD === 'number'
                  ? `$${aggregatedMetrics.costUSD.toFixed(2)}`
                  : '—'}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Active Agents</p>
              <p className="text-lg font-semibold">
                {aggregatedMetrics.activeAgents}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Completed</p>
              <p className="text-lg font-semibold">
                {aggregatedMetrics.completedTasks}
              </p>
            </div>
          </div>
          {typeof aggregatedMetrics.efficiency === 'number' && aggregatedMetrics.efficiency > 0 && (
            <>
              <Separator />
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Efficiency</span>
                  <span className="font-medium">{aggregatedMetrics.efficiency.toFixed(1)}%</span>
                </div>
                <Progress value={aggregatedMetrics.efficiency} className="h-1.5" />
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium">Task History</CardTitle>
            <Badge variant="outline" className="gap-1">
              <FileText className="h-3 w-3" />
              {taskHistory.length}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <ScrollArea className="h-[200px]">
            <div className="p-4 space-y-2">
              {loading && taskHistory.length === 0 ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              ) : taskHistory.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No task history available
                </p>
              ) : (
                taskHistory.map((task) => (
                  <div
                    key={task.id}
                    className={cn(
                      "flex items-start justify-between gap-2 p-2 rounded-sm hover:bg-accent/50 transition-colors",
                      task.status === 'failed' && "bg-destructive/5"
                    )}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium truncate">
                        {task.description}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-muted-foreground">
                          {new Date(task.timestamp).toLocaleTimeString()}
                        </span>
                        {task.agentId && (
                          <span className="text-xs text-muted-foreground">
                            • {task.agentId}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <Badge
                        variant={getStatusBadgeVariant(task.status)}
                        className="gap-1 text-xs"
                      >
                        {getStatusIcon(task.status)}
                        {task.status}
                      </Badge>
                      {task.tokenUsage && (
                        <Badge variant="outline" className="text-xs">
                          {task.tokenUsage} tokens
                        </Badge>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
};
