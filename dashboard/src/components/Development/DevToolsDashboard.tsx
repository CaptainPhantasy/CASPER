import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  IconTool as Wrench,
  IconDatabase as Database,
  IconShield as Shield,
  IconCode as Code,
  IconBolt as Zap,
  IconFileText as FileText,
  IconActivity as Activity,
  IconRefresh as RefreshCw,
  IconCircleCheck as CheckCircle,
  IconAlertCircle as AlertCircle,
  IconAlertTriangle as AlertTriangle,
  IconClock as Clock,
  IconLoader2 as Loader2,
  IconTrendingUp as TrendingUp,
  IconTrendingDown as TrendingDown,
  IconArrowRight as ArrowRight,
  IconSettings as Settings,
  IconChartBar as BarChart3,
  IconTarget as Target
} from "@tabler/icons-react";
import { cn } from "@/lib/utils";
import { API_BASE } from "@/services/api";

// Import individual tool components
import { DatabaseManager } from "./DatabaseManager";
import { SecurityScanner } from "./SecurityScanner";
import { CodeQuality } from "./CodeQuality";
import { APIGenerator } from "./APIGenerator";
import { LogAnalyzer } from "./LogAnalyzer";

interface DevToolStatus {
  tool: 'database' | 'security' | 'quality' | 'api-gen' | 'logs';
  name: string;
  status: 'active' | 'idle' | 'error' | 'disabled';
  last_run?: string;
  success_rate?: number;
  current_operation?: string;
  metrics?: {
    total_runs: number;
    avg_duration: number;
    recent_errors: number;
  };
}

interface OverallMetrics {
  tools_active: number;
  total_operations: number;
  success_rate: number;
  avg_response_time: number;
  recent_activity: {
    timestamp: string;
    tool: string;
    operation: string;
    status: 'success' | 'error' | 'warning';
    duration?: number;
  }[];
  health_score: number;
  trends: {
    operations: 'up' | 'down' | 'stable';
    quality: 'up' | 'down' | 'stable';
    performance: 'up' | 'down' | 'stable';
  };
}

interface QuickAction {
  id: string;
  title: string;
  description: string;
  icon: React.ComponentType<any>;
  tool: string;
  action: string;
  disabled?: boolean;
  loading?: boolean;
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'active': return <CheckCircle className="h-3 w-3 text-green-500" />;
    case 'idle': return <Clock className="h-3 w-3 text-muted-foreground" />;
    case 'error': return <AlertCircle className="h-3 w-3 text-red-500" />;
    case 'disabled': return <AlertTriangle className="h-3 w-3 text-gray-400" />;
    default: return <Activity className="h-3 w-3" />;
  }
};

const getStatusBadgeVariant = (status: string): "default" | "secondary" | "outline" | "destructive" => {
  switch (status) {
    case 'active': return 'secondary';
    case 'error': return 'destructive';
    case 'idle':
    case 'disabled':
    default: return 'outline';
  }
};

const getTrendIcon = (trend: string) => {
  switch (trend) {
    case 'up': return <TrendingUp className="h-3 w-3 text-green-500" />;
    case 'down': return <TrendingDown className="h-3 w-3 text-red-500" />;
    case 'stable': return <Activity className="h-3 w-3 text-muted-foreground" />;
    default: return <Activity className="h-3 w-3" />;
  }
};

const getHealthScoreColor = (score: number) => {
  if (score >= 90) return 'text-green-600 dark:text-green-400';
  if (score >= 70) return 'text-yellow-600 dark:text-yellow-400';
  if (score >= 50) return 'text-orange-600 dark:text-orange-400';
  return 'text-red-600 dark:text-red-400';
};

export const DevToolsDashboard: React.FC = () => {
  const [toolStatuses, setToolStatuses] = React.useState<DevToolStatus[]>([]);
  const [overallMetrics, setOverallMetrics] = React.useState<OverallMetrics | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [activeQuickActions, setActiveQuickActions] = React.useState<Set<string>>(new Set());
  const [selectedTool, setSelectedTool] = React.useState<string | null>(null);

  // Quick actions configuration
  const quickActions: QuickAction[] = [
    {
      id: 'db-migrate',
      title: 'Run Migrations',
      description: 'Apply pending database migrations',
      icon: Database,
      tool: 'database',
      action: 'migrate'
    },
    {
      id: 'security-scan',
      title: 'Security Scan',
      description: 'Run full security vulnerability scan',
      icon: Shield,
      tool: 'security',
      action: 'scan'
    },
    {
      id: 'lint-check',
      title: 'Lint Code',
      description: 'Run code quality checks',
      icon: Code,
      tool: 'quality',
      action: 'lint'
    },
    {
      id: 'api-gen',
      title: 'Generate API',
      description: 'Generate API documentation and schemas',
      icon: Zap,
      tool: 'api-gen',
      action: 'generate'
    },
    {
      id: 'log-analyze',
      title: 'Analyze Logs',
      description: 'Analyze recent application logs',
      icon: FileText,
      tool: 'logs',
      action: 'analyze'
    }
  ];

  // Fetch development tools status and metrics
  const fetchDevToolsInfo = React.useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [statusRes, metricsRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/dev/status`),
        fetch(`${API_BASE}/api/dev/metrics`)
      ]);

      if (statusRes.status === 'fulfilled' && statusRes.value.ok) {
        const status = await statusRes.value.json();
        setToolStatuses(status.tools || []);
      }

      if (metricsRes.status === 'fulfilled' && metricsRes.value.ok) {
        const metrics = await metricsRes.value.json();
        setOverallMetrics(metrics);
      }

    } catch (err) {
      console.error('Error fetching dev tools info:', err);
      setError('Failed to connect to development tools services');
    } finally {
      setLoading(false);
    }
  }, []);

  // Execute quick action
  const executeQuickAction = React.useCallback(async (action: QuickAction) => {
    try {
      setActiveQuickActions(prev => new Set([...prev, action.id]));
      setError(null);

      const endpoint = `/api/dev/${action.tool === 'api-gen' ? 'api-gen' : action.tool}`;
      const body = { action: action.action };

      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        throw new Error(`${action.title} failed: ${res.statusText}`);
      }

      // Refresh data after action
      await fetchDevToolsInfo();

    } catch (err) {
      console.error(`Quick action ${action.id} error:`, err);
      setError(err instanceof Error ? err.message : `${action.title} failed`);
    } finally {
      setActiveQuickActions(prev => {
        const newSet = new Set(prev);
        newSet.delete(action.id);
        return newSet;
      });
    }
  }, [fetchDevToolsInfo]);

  // Load initial data
  React.useEffect(() => {
    fetchDevToolsInfo();

    // Set up polling for real-time updates
    const interval = setInterval(fetchDevToolsInfo, 30000); // Poll every 30 seconds
    return () => clearInterval(interval);
  }, [fetchDevToolsInfo]);

  return (
    <div className="space-y-4">
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Overview Header */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Wrench className="h-5 w-5 text-blue-500" />
              Development Tools Dashboard
            </CardTitle>
            <div className="flex items-center gap-2">
              {overallMetrics && (
                <Badge variant="outline" className="gap-1">
                  <BarChart3 className="h-3 w-3" />
                  Health: {overallMetrics.health_score}%
                </Badge>
              )}
              <Button
                size="sm"
                variant="outline"
                onClick={fetchDevToolsInfo}
                disabled={loading}
              >
                <RefreshCw className={cn("h-3 w-3", loading && "animate-spin")} />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {overallMetrics && (
            <>
              {/* Health Score */}
              <div className="text-center space-y-2">
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">Overall System Health</p>
                  <p className={cn("text-3xl font-bold", getHealthScoreColor(overallMetrics.health_score))}>
                    {overallMetrics.health_score}%
                  </p>
                </div>
                <Progress value={overallMetrics.health_score} className="h-2" />
              </div>

              <Separator />

              {/* Key Metrics */}
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-1">
                    <p className="text-xs text-muted-foreground">Active Tools</p>
                    {getTrendIcon(overallMetrics.trends.operations)}
                  </div>
                  <p className="text-lg font-semibold">{overallMetrics.tools_active}</p>
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-1">
                    <p className="text-xs text-muted-foreground">Success Rate</p>
                    {getTrendIcon(overallMetrics.trends.quality)}
                  </div>
                  <p className="text-lg font-semibold">{overallMetrics.success_rate}%</p>
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-1">
                    <p className="text-xs text-muted-foreground">Avg Response</p>
                    {getTrendIcon(overallMetrics.trends.performance)}
                  </div>
                  <p className="text-lg font-semibold">{overallMetrics.avg_response_time}ms</p>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Tool Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {toolStatuses.map((tool) => (
          <Card key={tool.tool} className="hover:shadow-md transition-shadow">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  {tool.tool === 'database' && <Database className="h-4 w-4 text-blue-500" />}
                  {tool.tool === 'security' && <Shield className="h-4 w-4 text-red-500" />}
                  {tool.tool === 'quality' && <Code className="h-4 w-4 text-green-500" />}
                  {tool.tool === 'api-gen' && <Zap className="h-4 w-4 text-purple-500" />}
                  {tool.tool === 'logs' && <FileText className="h-4 w-4 text-orange-500" />}
                  {tool.name}
                </CardTitle>
                <Badge variant={getStatusBadgeVariant(tool.status)} className="gap-1">
                  {getStatusIcon(tool.status)}
                  {tool.status}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {tool.current_operation && (
                <div className="flex items-center gap-2">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  <span className="text-xs text-muted-foreground">{tool.current_operation}</span>
                </div>
              )}

              {tool.metrics && (
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <p className="text-muted-foreground">Total Runs</p>
                    <p className="font-medium">{tool.metrics.total_runs}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Avg Duration</p>
                    <p className="font-medium">{tool.metrics.avg_duration}ms</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Success Rate</p>
                    <p className="font-medium">{tool.success_rate}%</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Recent Errors</p>
                    <p className="font-medium text-red-600">{tool.metrics.recent_errors}</p>
                  </div>
                </div>
              )}

              {tool.last_run && (
                <p className="text-xs text-muted-foreground">
                  Last run: {new Date(tool.last_run).toLocaleString()}
                </p>
              )}

              <Button
                size="sm"
                variant="outline"
                className="w-full"
                onClick={() => setSelectedTool(tool.tool)}
              >
                <Settings className="h-3 w-3 mr-2" />
                Configure
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Target className="h-4 w-4 text-blue-500" />
            Quick Actions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {quickActions.map((action) => (
              <Button
                key={action.id}
                variant="outline"
                className="h-auto p-4 flex flex-col items-start gap-2"
                onClick={() => executeQuickAction(action)}
                disabled={activeQuickActions.has(action.id) || action.disabled}
              >
                <div className="flex items-center gap-2 w-full">
                  {activeQuickActions.has(action.id) ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <action.icon className="h-4 w-4" />
                  )}
                  <span className="font-medium text-sm">{action.title}</span>
                  <ArrowRight className="h-3 w-3 ml-auto opacity-50" />
                </div>
                <p className="text-xs text-muted-foreground text-left">
                  {action.description}
                </p>
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Recent Activity */}
      {overallMetrics && overallMetrics.recent_activity.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Activity className="h-4 w-4 text-blue-500" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[200px]">
              <div className="p-4 space-y-2">
                {overallMetrics.recent_activity.map((activity, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between gap-2 p-2 rounded-sm hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        {activity.tool === 'database' && <Database className="h-3 w-3" />}
                        {activity.tool === 'security' && <Shield className="h-3 w-3" />}
                        {activity.tool === 'quality' && <Code className="h-3 w-3" />}
                        {activity.tool === 'api-gen' && <Zap className="h-3 w-3" />}
                        {activity.tool === 'logs' && <FileText className="h-3 w-3" />}
                        <span className="text-sm font-medium">{activity.operation}</span>
                        <Badge variant="outline" className="text-xs">
                          {activity.tool}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {new Date(activity.timestamp).toLocaleString()}
                        {activity.duration && ` • ${activity.duration}ms`}
                      </p>
                    </div>
                    <Badge
                      variant={
                        activity.status === 'success' ? 'secondary' :
                        activity.status === 'error' ? 'destructive' : 'default'
                      }
                      className="gap-1"
                    >
                      {activity.status === 'success' && <CheckCircle className="h-3 w-3" />}
                      {activity.status === 'error' && <AlertCircle className="h-3 w-3" />}
                      {activity.status === 'warning' && <AlertTriangle className="h-3 w-3" />}
                      {activity.status}
                    </Badge>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}

      {/* Tool Detail Panel */}
      {selectedTool && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium">
                {selectedTool.charAt(0).toUpperCase() + selectedTool.slice(1)} Tool Configuration
              </CardTitle>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setSelectedTool(null)}
              >
                Close
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <Tabs value={selectedTool} className="w-full">
              <TabsList className="grid w-full grid-cols-5">
                <TabsTrigger value="database">Database</TabsTrigger>
                <TabsTrigger value="security">Security</TabsTrigger>
                <TabsTrigger value="quality">Quality</TabsTrigger>
                <TabsTrigger value="api-gen">API Gen</TabsTrigger>
                <TabsTrigger value="logs">Logs</TabsTrigger>
              </TabsList>

              <TabsContent value="database">
                <DatabaseManager />
              </TabsContent>
              <TabsContent value="security">
                <SecurityScanner />
              </TabsContent>
              <TabsContent value="quality">
                <CodeQuality />
              </TabsContent>
              <TabsContent value="api-gen">
                <APIGenerator />
              </TabsContent>
              <TabsContent value="logs">
                <LogAnalyzer />
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
