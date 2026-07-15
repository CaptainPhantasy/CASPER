import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  IconFileText as FileText,
  IconSearch as Search,
  IconRefresh as RefreshCw,
  IconCircleCheck as CheckCircle,
  IconAlertCircle as AlertCircle,
  IconAlertTriangle as AlertTriangle,
  IconClock as Clock,
  IconLoader2 as Loader2,
  IconBug as Bug,
  IconInfoCircle as Info,
  IconTrendingUp as TrendingUp,
  IconTrendingDown as TrendingDown,
  IconChevronDown as ChevronDown,
  IconChevronRight as ChevronRight,
  IconActivity as Activity
} from "@tabler/icons-react";
import { cn } from "@/lib/utils";
import { API_BASE } from "@/services/api";

interface LogEntry {
  id: string;
  timestamp: string;
  level: 'trace' | 'debug' | 'info' | 'warn' | 'error' | 'fatal';
  logger: string;
  message: string;
  source?: string;
  thread?: string;
  stackTrace?: string;
  metadata?: Record<string, any>;
  tags?: string[];
}

interface LogAnalysis {
  id: string;
  started_at: string;
  completed_at?: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  log_source: string;
  time_range: {
    start: string;
    end: string;
  };
  filters?: {
    levels?: string[];
    loggers?: string[];
    search?: string;
  };
  results: {
    total_entries: number;
    error_count: number;
    warning_count: number;
    info_count: number;
    debug_count: number;
    unique_loggers: number;
    time_span: number;
    patterns: {
      pattern: string;
      count: number;
      severity: 'high' | 'medium' | 'low';
    }[];
    anomalies: {
      type: 'spike' | 'drop' | 'pattern' | 'frequency';
      description: string;
      timestamp: string;
      severity: 'high' | 'medium' | 'low';
    }[];
  };
  entries: LogEntry[];
  duration?: number;
}

interface LogMetrics {
  total_log_files: number;
  recent_analyses: number;
  avg_errors_per_day: number;
  most_active_logger: string;
  log_sources: string[];
  supported_formats: string[];
  retention_days: number;
  storage_size_mb: number;
}

const getLevelColor = (level: string) => {
  switch (level) {
    case 'fatal':
    case 'error': return 'text-red-600 dark:text-red-400';
    case 'warn': return 'text-orange-600 dark:text-orange-400';
    case 'info': return 'text-blue-600 dark:text-blue-400';
    case 'debug': return 'text-purple-600 dark:text-purple-400';
    case 'trace': return 'text-gray-600 dark:text-gray-400';
    default: return 'text-muted-foreground';
  }
};

const getLevelIcon = (level: string) => {
  switch (level) {
    case 'fatal':
    case 'error': return <AlertCircle className="h-3 w-3 text-red-500" />;
    case 'warn': return <AlertTriangle className="h-3 w-3 text-orange-500" />;
    case 'info': return <Info className="h-3 w-3 text-blue-500" />;
    case 'debug': return <Bug className="h-3 w-3 text-purple-500" />;
    case 'trace': return <Activity className="h-3 w-3 text-gray-500" />;
    default: return <FileText className="h-3 w-3" />;
  }
};

const getLevelBadgeVariant = (level: string): "default" | "secondary" | "outline" | "destructive" => {
  switch (level) {
    case 'fatal':
    case 'error': return 'destructive';
    case 'warn': return 'default';
    case 'info': return 'secondary';
    case 'debug':
    case 'trace':
    default: return 'outline';
  }
};

const getSeverityIcon = (severity: string) => {
  switch (severity) {
    case 'high': return <TrendingUp className="h-3 w-3 text-red-500" />;
    case 'medium': return <Activity className="h-3 w-3 text-orange-500" />;
    case 'low': return <TrendingDown className="h-3 w-3 text-blue-500" />;
    default: return <Info className="h-3 w-3" />;
  }
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'running':
      return <Loader2 className="h-3 w-3 animate-spin" />;
    case 'completed':
      return <CheckCircle className="h-3 w-3 text-green-500" />;
    case 'failed':
      return <AlertCircle className="h-3 w-3 text-red-500" />;
    case 'cancelled':
      return <Clock className="h-3 w-3 text-muted-foreground" />;
    default:
      return <Clock className="h-3 w-3 text-muted-foreground" />;
  }
};

export const LogAnalyzer: React.FC = () => {
  const [logMetrics, setLogMetrics] = React.useState<LogMetrics | null>(null);
  const [analyses, setAnalyses] = React.useState<LogAnalysis[]>([]);
  const [currentAnalysis, setCurrentAnalysis] = React.useState<LogAnalysis | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Filter and search state
  const [logSource, setLogSource] = React.useState("");
  const [timeRange, setTimeRange] = React.useState("24h");
  const [logLevel, setLogLevel] = React.useState("all");
  const [searchQuery, setSearchQuery] = React.useState("");
  const [selectedLogger] = React.useState("all");

  // UI state
  const [expandedSections, setExpandedSections] = React.useState<Record<string, boolean>>({});
  const [, setSelectedEntry] = React.useState<LogEntry | null>(null);

  // Fetch log metrics and analysis history
  const fetchLogInfo = React.useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [metricsRes, historyRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/dev/logs/metrics`),
        fetch(`${API_BASE}/api/dev/logs/analyses`)
      ]);

      if (metricsRes.status === 'fulfilled' && metricsRes.value.ok) {
        const metrics = await metricsRes.value.json();
        setLogMetrics(metrics);
      }

      if (historyRes.status === 'fulfilled' && historyRes.value.ok) {
        const history = await historyRes.value.json();
        setAnalyses(history.analyses || []);

        // Check for active analysis
        const activeAnalysis = history.analyses?.find((analysis: LogAnalysis) => analysis.status === 'running');
        if (activeAnalysis) {
          setCurrentAnalysis(activeAnalysis);
        }
      }

    } catch (err) {
      console.error('Error fetching log info:', err);
      setError('Failed to connect to log analysis service');
    } finally {
      setLoading(false);
    }
  }, []);

  // Execute log analysis
  const executeAnalysis = React.useCallback(async () => {
    try {
      setError(null);

      const body: any = {
        log_source: logSource || "application.log",
        time_range: timeRange,
        filters: {
          levels: logLevel === 'all' ? undefined : [logLevel],
          loggers: selectedLogger === 'all' ? undefined : [selectedLogger],
          search: searchQuery || undefined
        }
      };

      const res = await fetch(`${API_BASE}/api/dev/logs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        throw new Error(`Log analysis failed: ${res.statusText}`);
      }

      const result = await res.json();

      if (result.analysis_id) {
        // Start polling for analysis progress
        pollAnalysisProgress(result.analysis_id);
      }

      // Refresh data
      await fetchLogInfo();

      if (result.error) {
        setError(result.error);
      }

    } catch (err) {
      console.error('Analysis error:', err);
      setError(err instanceof Error ? err.message : 'Log analysis failed');
    }
  }, [logSource, timeRange, logLevel, searchQuery, selectedLogger, fetchLogInfo]);

  // Poll for analysis progress
  const pollAnalysisProgress = React.useCallback(async (analysisId: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/dev/logs/analysis/${analysisId}`);
        if (res.ok) {
          const analysis = await res.json();
          setCurrentAnalysis(analysis);

          if (analysis.status === 'completed' || analysis.status === 'failed' || analysis.status === 'cancelled') {
            clearInterval(interval);
            setCurrentAnalysis(null);
            await fetchLogInfo();
          }
        }
      } catch (error) {
        console.error('Error polling analysis progress:', error);
        clearInterval(interval);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [fetchLogInfo]);

  // Toggle expanded section
  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // Group log entries by logger
  const groupedEntries = React.useMemo(() => {
    if (analyses.length === 0) return {};

    const latestAnalysis = analyses.find(analysis => analysis.status === 'completed');
    if (!latestAnalysis) return {};

    return latestAnalysis.entries.reduce((acc, entry) => {
      const logger = entry.logger || 'unknown';
      if (!acc[logger]) {
        acc[logger] = [];
      }
      acc[logger].push(entry);
      return acc;
    }, {} as Record<string, LogEntry[]>);
  }, [analyses]);

  // Load initial data
  React.useEffect(() => {
    fetchLogInfo();
  }, [fetchLogInfo]);

  return (
    <div className="space-y-4">
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Log Analysis Overview */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <FileText className="h-4 w-4 text-blue-500" />
              Log Analysis Overview
            </CardTitle>
            <div className="flex items-center gap-2">
              <Badge variant={logMetrics ? "secondary" : "destructive"} className="gap-1">
                <Activity className="h-3 w-3" />
                {logMetrics ? 'Active' : 'Not Available'}
              </Badge>
              <Button
                size="sm"
                variant="outline"
                onClick={fetchLogInfo}
                disabled={loading}
              >
                <RefreshCw className={cn("h-3 w-3", loading && "animate-spin")} />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {logMetrics && (
            <>
              {/* Metrics Grid */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">Log Files</p>
                  <p className="text-sm font-medium">{logMetrics.total_log_files}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">Recent Analyses</p>
                  <p className="text-sm font-medium">{logMetrics.recent_analyses}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">Avg Errors/Day</p>
                  <p className="text-sm font-medium text-red-600">{logMetrics.avg_errors_per_day}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">Storage Size</p>
                  <p className="text-sm font-medium">{logMetrics.storage_size_mb}MB</p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">Most Active</p>
                  <p className="text-sm font-medium truncate">{logMetrics.most_active_logger}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">Retention</p>
                  <p className="text-sm font-medium">{logMetrics.retention_days} days</p>
                </div>
              </div>

              <Separator />

              {/* Analysis Configuration */}
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-xs font-medium">Log Source</label>
                    <Select value={logSource} onValueChange={setLogSource}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select log file" />
                      </SelectTrigger>
                      <SelectContent>
                        {(logMetrics.log_sources || ['application.log', 'error.log', 'access.log']).map(source => (
                          <SelectItem key={source} value={source}>{source}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-medium">Time Range</label>
                    <Select value={timeRange} onValueChange={setTimeRange}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1h">Last Hour</SelectItem>
                        <SelectItem value="24h">Last 24 Hours</SelectItem>
                        <SelectItem value="7d">Last 7 Days</SelectItem>
                        <SelectItem value="30d">Last 30 Days</SelectItem>
                        <SelectItem value="custom">Custom Range</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-medium">Log Level</label>
                    <Select value={logLevel} onValueChange={setLogLevel}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Levels</SelectItem>
                        <SelectItem value="error">Error Only</SelectItem>
                        <SelectItem value="warn">Warn & Above</SelectItem>
                        <SelectItem value="info">Info & Above</SelectItem>
                        <SelectItem value="debug">Debug & Above</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-medium">Search</label>
                    <Input
                      placeholder="Search in logs..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>
                </div>

                <Button
                  onClick={executeAnalysis}
                  disabled={currentAnalysis !== null}
                  className="w-full"
                >
                  {currentAnalysis ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Search className="h-4 w-4 mr-2" />
                  )}
                  Analyze Logs
                </Button>
              </div>

              {/* Current Analysis Progress */}
              {currentAnalysis && (
                <>
                  <Separator />
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-medium">Analysis in progress...</p>
                      <Badge variant="default" className="gap-1">
                        {getStatusIcon(currentAnalysis.status)}
                        {currentAnalysis.log_source}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Time range: {currentAnalysis.time_range.start} to {currentAnalysis.time_range.end}
                      {currentAnalysis.results.total_entries > 0 && (
                        ` • ${currentAnalysis.results.total_entries} entries processed`
                      )}
                    </p>
                  </div>
                </>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Analysis Results */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Analysis Results</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Tabs defaultValue="summary" className="w-full">
            <div className="px-4 pt-2">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="summary">Summary</TabsTrigger>
                <TabsTrigger value="entries">Log Entries</TabsTrigger>
                <TabsTrigger value="patterns">Patterns</TabsTrigger>
                <TabsTrigger value="anomalies">Anomalies</TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="summary" className="mt-0">
              <div className="p-4">
                {analyses.length > 0 && analyses[0]?.results ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <p className="text-xs text-muted-foreground">Total Entries</p>
                        <p className="text-lg font-semibold">{analyses[0].results.total_entries}</p>
                      </div>
                      <div className="space-y-1">
                        <p className="text-xs text-muted-foreground">Unique Loggers</p>
                        <p className="text-lg font-semibold">{analyses[0].results.unique_loggers}</p>
                      </div>
                      <div className="space-y-1">
                        <p className="text-xs text-muted-foreground">Errors</p>
                        <p className="text-lg font-semibold text-red-600">{analyses[0].results.error_count}</p>
                      </div>
                      <div className="space-y-1">
                        <p className="text-xs text-muted-foreground">Warnings</p>
                        <p className="text-lg font-semibold text-orange-600">{analyses[0].results.warning_count}</p>
                      </div>
                      <div className="space-y-1">
                        <p className="text-xs text-muted-foreground">Info</p>
                        <p className="text-lg font-semibold text-blue-600">{analyses[0].results.info_count}</p>
                      </div>
                      <div className="space-y-1">
                        <p className="text-xs text-muted-foreground">Debug</p>
                        <p className="text-lg font-semibold text-purple-600">{analyses[0].results.debug_count}</p>
                      </div>
                    </div>
                    <Separator />
                    <div className="space-y-2">
                      <p className="text-xs text-muted-foreground">Time Span: {analyses[0].results.time_span} hours</p>
                      <p className="text-xs text-muted-foreground">
                        Analysis completed in {analyses[0].duration}ms
                      </p>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    No analysis results available
                  </p>
                )}
              </div>
            </TabsContent>

            <TabsContent value="entries" className="mt-0">
              <ScrollArea className="h-[400px]">
                <div className="p-4 space-y-2">
                  {Object.keys(groupedEntries).length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-8">
                      No log entries found
                    </p>
                  ) : (
                    Object.entries(groupedEntries).map(([logger, entries]) => (
                      <Collapsible
                        key={logger}
                        open={expandedSections[logger]}
                        onOpenChange={() => toggleSection(logger)}
                      >
                        <CollapsibleTrigger className="w-full">
                          <div className="flex items-center justify-between p-2 hover:bg-accent/50 rounded-sm">
                            <div className="flex items-center gap-2">
                              {expandedSections[logger] ? (
                                <ChevronDown className="h-4 w-4" />
                              ) : (
                                <ChevronRight className="h-4 w-4" />
                              )}
                              <Activity className="h-4 w-4" />
                              <span className="text-sm font-medium truncate">{logger}</span>
                            </div>
                            <Badge variant="outline" className="ml-2">
                              {entries.length} entries
                            </Badge>
                          </div>
                        </CollapsibleTrigger>
                        <CollapsibleContent className="space-y-1 ml-6">
                          {entries.slice(0, 10).map((entry) => (
                            <div
                              key={entry.id}
                              className={cn(
                                "flex items-start justify-between gap-2 p-2 rounded-sm hover:bg-accent/50 transition-colors cursor-pointer border-l-2",
                                entry.level === 'error' && "border-l-red-500 bg-red-50/50 dark:bg-red-950/20",
                                entry.level === 'warn' && "border-l-orange-500 bg-orange-50/50 dark:bg-orange-950/20"
                              )}
                              onClick={() => setSelectedEntry(entry)}
                            >
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                  {getLevelIcon(entry.level)}
                                  <span className="text-xs font-mono">
                                    {new Date(entry.timestamp).toLocaleTimeString()}
                                  </span>
                                  {entry.thread && (
                                    <Badge variant="outline" className="text-xs">
                                      {entry.thread}
                                    </Badge>
                                  )}
                                </div>
                                <p className="text-xs text-muted-foreground">
                                  {entry.message}
                                </p>
                                {entry.source && (
                                  <p className="text-xs text-muted-foreground mt-1">
                                    {entry.source}
                                  </p>
                                )}
                              </div>
                              <Badge
                                variant={getLevelBadgeVariant(entry.level)}
                                className={cn("gap-1 text-xs", getLevelColor(entry.level))}
                              >
                                {getLevelIcon(entry.level)}
                                {entry.level.toUpperCase()}
                              </Badge>
                            </div>
                          ))}
                          {entries.length > 10 && (
                            <p className="text-xs text-muted-foreground text-center py-2">
                              ... and {entries.length - 10} more entries
                            </p>
                          )}
                        </CollapsibleContent>
                      </Collapsible>
                    ))
                  )}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="patterns" className="mt-0">
              <ScrollArea className="h-[300px]">
                <div className="p-4 space-y-2">
                  {analyses.length === 0 || !analyses[0]?.results.patterns ? (
                    <p className="text-sm text-muted-foreground text-center py-8">
                      No patterns detected
                    </p>
                  ) : (
                    analyses[0].results.patterns.map((pattern, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between gap-2 p-3 rounded-sm hover:bg-accent/50 transition-colors border"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            {getSeverityIcon(pattern.severity)}
                            <code className="text-sm font-mono bg-muted px-2 py-1 rounded">
                              {pattern.pattern}
                            </code>
                          </div>
                          <p className="text-xs text-muted-foreground">
                            Occurred {pattern.count} times
                          </p>
                        </div>
                        <Badge variant={pattern.severity === 'high' ? 'destructive' : pattern.severity === 'medium' ? 'default' : 'outline'}>
                          {pattern.severity}
                        </Badge>
                      </div>
                    ))
                  )}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="anomalies" className="mt-0">
              <ScrollArea className="h-[300px]">
                <div className="p-4 space-y-2">
                  {analyses.length === 0 || !analyses[0]?.results.anomalies ? (
                    <p className="text-sm text-muted-foreground text-center py-8">
                      No anomalies detected
                    </p>
                  ) : (
                    analyses[0].results.anomalies.map((anomaly, index) => (
                      <div
                        key={index}
                        className="flex items-start justify-between gap-2 p-3 rounded-sm hover:bg-accent/50 transition-colors border"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            {getSeverityIcon(anomaly.severity)}
                            <span className="text-sm font-medium capitalize">{anomaly.type}</span>
                            <Badge variant="outline" className="text-xs">
                              {new Date(anomaly.timestamp).toLocaleString()}
                            </Badge>
                          </div>
                          <p className="text-xs text-muted-foreground">
                            {anomaly.description}
                          </p>
                        </div>
                        <Badge variant={anomaly.severity === 'high' ? 'destructive' : anomaly.severity === 'medium' ? 'default' : 'outline'}>
                          {anomaly.severity}
                        </Badge>
                      </div>
                    ))
                  )}
                </div>
              </ScrollArea>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
};
