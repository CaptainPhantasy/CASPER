import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  IconCode as Code,
  IconPlayerPlay as Play,
  IconRefresh as RefreshCw,
  IconCircleCheck as CheckCircle,
  IconAlertCircle as AlertCircle,
  IconAlertTriangle as AlertTriangle,
  IconClock as Clock,
  IconLoader2 as Loader2,
  IconFileText as FileText,
  IconBolt as Zap,
  IconTrendingUp as TrendingUp,
  IconTrendingDown as TrendingDown,
  IconChevronDown as ChevronDown,
  IconChevronRight as ChevronRight,
  IconDownload as Download
} from "@tabler/icons-react";
import { cn } from "@/lib/utils";
import { API_BASE } from "@/services/api";

interface LintIssue {
  id: string;
  severity: 'error' | 'warning' | 'info' | 'suggestion';
  rule: string;
  message: string;
  file: string;
  line: number;
  column: number;
  context?: string;
  suggestion?: string;
  autoFixable?: boolean;
  fixed?: boolean;
}

interface LintResult {
  id: string;
  started_at: string;
  completed_at?: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  linter: string;
  target_path: string;
  progress?: number;
  issues_found: number;
  issues: LintIssue[];
  metrics?: {
    total_files: number;
    files_with_issues: number;
    error_count: number;
    warning_count: number;
    suggestion_count: number;
    quality_score: number;
    complexity_score?: number;
    maintainability_index?: number;
  };
  duration?: number;
}

interface QualityMetrics {
  overall_score: number;
  trend: 'up' | 'down' | 'stable';
  linters_available: string[];
  recent_scans: number;
  total_issues: number;
  fixed_issues: number;
  code_coverage?: number;
  technical_debt?: number;
}

const getSeverityColor = (severity: string) => {
  switch (severity) {
    case 'error': return 'text-red-600 dark:text-red-400';
    case 'warning': return 'text-orange-600 dark:text-orange-400';
    case 'info': return 'text-blue-600 dark:text-blue-400';
    case 'suggestion': return 'text-purple-600 dark:text-purple-400';
    default: return 'text-muted-foreground';
  }
};

const getSeverityIcon = (severity: string) => {
  switch (severity) {
    case 'error': return <AlertCircle className="h-3 w-3 text-red-500" />;
    case 'warning': return <AlertTriangle className="h-3 w-3 text-orange-500" />;
    case 'info': return <CheckCircle className="h-3 w-3 text-blue-500" />;
    case 'suggestion': return <Zap className="h-3 w-3 text-purple-500" />;
    default: return <Code className="h-3 w-3" />;
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

const getTrendIcon = (trend: string) => {
  switch (trend) {
    case 'up': return <TrendingUp className="h-3 w-3 text-green-500" />;
    case 'down': return <TrendingDown className="h-3 w-3 text-red-500" />;
    case 'stable': return <Code className="h-3 w-3 text-muted-foreground" />;
    default: return <Code className="h-3 w-3" />;
  }
};

const getQualityScoreColor = (score: number) => {
  if (score >= 90) return 'text-green-600 dark:text-green-400';
  if (score >= 70) return 'text-yellow-600 dark:text-yellow-400';
  if (score >= 50) return 'text-orange-600 dark:text-orange-400';
  return 'text-red-600 dark:text-red-400';
};

export const CodeQuality: React.FC = () => {
  const [qualityMetrics, setQualityMetrics] = React.useState<QualityMetrics | null>(null);
  const [lintResults, setLintResults] = React.useState<LintResult[]>([]);
  const [currentLint, setCurrentLint] = React.useState<LintResult | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [selectedLinter, setSelectedLinter] = React.useState("eslint");
  const [targetPath, setTargetPath] = React.useState("");
  const [fixMode, setFixMode] = React.useState("check");
  const [, setSelectedIssue] = React.useState<LintIssue | null>(null);
  const [issueCategoriesOpen, setIssueCategoriesOpen] = React.useState<Record<string, boolean>>({});

  // Fetch quality metrics and lint history
  const fetchQualityInfo = React.useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [metricsRes, historyRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/dev/quality/metrics`),
        fetch(`${API_BASE}/api/dev/quality/history`)
      ]);

      if (metricsRes.status === 'fulfilled' && metricsRes.value.ok) {
        const metrics = await metricsRes.value.json();
        setQualityMetrics(metrics);
      }

      if (historyRes.status === 'fulfilled' && historyRes.value.ok) {
        const history = await historyRes.value.json();
        setLintResults(history.results || []);

        // Check for active lint
        const activeLint = history.results?.find((result: LintResult) => result.status === 'running');
        if (activeLint) {
          setCurrentLint(activeLint);
        }
      }

    } catch (err) {
      console.error('Error fetching quality info:', err);
      setError('Failed to connect to code quality service');
    } finally {
      setLoading(false);
    }
  }, []);

  // Execute linting
  const executeLint = React.useCallback(async (linter: string, options?: any) => {
    try {
      setError(null);

      const body: any = {
        linter: linter,
        target_path: targetPath || ".",
        fix: fixMode === 'fix',
        ...options
      };

      const res = await fetch(`${API_BASE}/api/dev/lint`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        throw new Error(`Code linting failed: ${res.statusText}`);
      }

      const result = await res.json();

      if (result.lint_id) {
        // Start polling for lint progress
        pollLintProgress(result.lint_id);
      }

      // Refresh data
      await fetchQualityInfo();

      if (result.error) {
        setError(result.error);
      }

    } catch (err) {
      console.error('Lint error:', err);
      setError(err instanceof Error ? err.message : 'Code linting failed');
    }
  }, [targetPath, fixMode, fetchQualityInfo]);

  // Poll for lint progress
  const pollLintProgress = React.useCallback(async (lintId: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/dev/quality/lint/${lintId}`);
        if (res.ok) {
          const lint = await res.json();
          setCurrentLint(lint);

          if (lint.status === 'completed' || lint.status === 'failed' || lint.status === 'cancelled') {
            clearInterval(interval);
            setCurrentLint(null);
            await fetchQualityInfo();
          }
        }
      } catch (error) {
        console.error('Error polling lint progress:', error);
        clearInterval(interval);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [fetchQualityInfo]);

  // Group issues by file
  const groupedIssues = React.useMemo(() => {
    if (lintResults.length === 0) return {};

    const latestResult = lintResults.find(result => result.status === 'completed');
    if (!latestResult) return {};

    return latestResult.issues.reduce((acc, issue) => {
      if (!acc[issue.file]) {
        acc[issue.file] = [];
      }
      acc[issue.file].push(issue);
      return acc;
    }, {} as Record<string, LintIssue[]>);
  }, [lintResults]);

  // Toggle issue category
  const toggleCategory = (file: string) => {
    setIssueCategoriesOpen(prev => ({
      ...prev,
      [file]: !prev[file]
    }));
  };

  // Load initial data
  React.useEffect(() => {
    fetchQualityInfo();
  }, [fetchQualityInfo]);

  return (
    <div className="space-y-4">
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Quality Overview Card */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Code className="h-4 w-4 text-blue-500" />
              Code Quality Overview
            </CardTitle>
            <div className="flex items-center gap-2">
              {qualityMetrics && (
                <Badge variant="outline" className="gap-1">
                  {getTrendIcon(qualityMetrics.trend)}
                  {qualityMetrics.trend}
                </Badge>
              )}
              <Button
                size="sm"
                variant="outline"
                onClick={fetchQualityInfo}
                disabled={loading}
              >
                <RefreshCw className={cn("h-3 w-3", loading && "animate-spin")} />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {qualityMetrics && (
            <>
              {/* Quality Score */}
              <div className="text-center space-y-2">
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">Overall Quality Score</p>
                  <p className={cn("text-3xl font-bold", getQualityScoreColor(qualityMetrics.overall_score))}>
                    {qualityMetrics.overall_score}%
                  </p>
                </div>
                <Progress value={qualityMetrics.overall_score} className="h-2" />
              </div>

              <Separator />

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">Recent Scans</p>
                  <p className="text-sm font-medium">{qualityMetrics.recent_scans}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">Total Issues</p>
                  <p className="text-sm font-medium">{qualityMetrics.total_issues}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">Fixed Issues</p>
                  <p className="text-sm font-medium text-green-600">
                    {qualityMetrics.fixed_issues}
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">Fix Rate</p>
                  <p className="text-sm font-medium">
                    {qualityMetrics.total_issues > 0
                      ? Math.round((qualityMetrics.fixed_issues / qualityMetrics.total_issues) * 100)
                      : 0}%
                  </p>
                </div>
                {qualityMetrics.code_coverage !== undefined && (
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Code Coverage</p>
                    <p className="text-sm font-medium">{qualityMetrics.code_coverage}%</p>
                  </div>
                )}
                {qualityMetrics.technical_debt !== undefined && (
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Tech Debt</p>
                    <p className="text-sm font-medium">{qualityMetrics.technical_debt}h</p>
                  </div>
                )}
              </div>

              <Separator />

              {/* Linting Configuration */}
              <div className="space-y-3">
                <div className="flex items-center gap-4">
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Linter</p>
                    <Select value={selectedLinter} onValueChange={setSelectedLinter}>
                      <SelectTrigger className="w-32">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {(qualityMetrics.linters_available || ['eslint', 'prettier', 'pylint']).map(linter => (
                          <SelectItem key={linter} value={linter}>{linter}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1 flex-1">
                    <p className="text-xs text-muted-foreground">Target Path</p>
                    <Input
                      placeholder="./src (default: current directory)"
                      value={targetPath}
                      onChange={(e) => setTargetPath(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Mode</p>
                    <Select value={fixMode} onValueChange={setFixMode}>
                      <SelectTrigger className="w-24">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="check">Check</SelectItem>
                        <SelectItem value="fix">Fix</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <Button
                    onClick={() => executeLint(selectedLinter)}
                    disabled={currentLint !== null}
                    className="mt-6"
                  >
                    {currentLint ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="h-4 w-4" />
                    )}
                    Run Lint
                  </Button>
                </div>
              </div>

              {/* Current Lint Progress */}
              {currentLint && (
                <>
                  <Separator />
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-medium">Linting in progress...</p>
                      <Badge variant="default" className="gap-1">
                        {getStatusIcon(currentLint.status)}
                        {currentLint.linter}
                      </Badge>
                    </div>
                    {currentLint.progress !== undefined && (
                      <Progress value={currentLint.progress} className="h-2" />
                    )}
                    <p className="text-xs text-muted-foreground">
                      Target: {currentLint.target_path}
                      {currentLint.issues_found > 0 && ` • ${currentLint.issues_found} issues found`}
                    </p>
                  </div>
                </>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Issues and Results */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Lint Results</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Tabs defaultValue="issues" className="w-full">
            <div className="px-4 pt-2">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="issues">Issues</TabsTrigger>
                <TabsTrigger value="metrics">Metrics</TabsTrigger>
                <TabsTrigger value="history">History</TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="issues" className="mt-0">
              <ScrollArea className="h-[400px]">
                <div className="p-4 space-y-2">
                  {Object.keys(groupedIssues).length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-8">
                      No lint results available
                    </p>
                  ) : (
                    Object.entries(groupedIssues).map(([file, issues]) => (
                      <Collapsible
                        key={file}
                        open={issueCategoriesOpen[file]}
                        onOpenChange={() => toggleCategory(file)}
                      >
                        <CollapsibleTrigger className="w-full">
                          <div className="flex items-center justify-between p-2 hover:bg-accent/50 rounded-sm">
                            <div className="flex items-center gap-2">
                              {issueCategoriesOpen[file] ? (
                                <ChevronDown className="h-4 w-4" />
                              ) : (
                                <ChevronRight className="h-4 w-4" />
                              )}
                              <FileText className="h-4 w-4" />
                              <span className="text-sm font-medium truncate">{file}</span>
                            </div>
                            <Badge variant="outline" className="ml-2">
                              {issues.length} issues
                            </Badge>
                          </div>
                        </CollapsibleTrigger>
                        <CollapsibleContent className="space-y-1 ml-6">
                          {issues.map((issue) => (
                            <div
                              key={issue.id}
                              className={cn(
                                "flex items-start justify-between gap-2 p-2 rounded-sm hover:bg-accent/50 transition-colors cursor-pointer border-l-2",
                                issue.severity === 'error' && "border-l-red-500 bg-red-50/50 dark:bg-red-950/20",
                                issue.severity === 'warning' && "border-l-orange-500 bg-orange-50/50 dark:bg-orange-950/20"
                              )}
                              onClick={() => setSelectedIssue(issue)}
                            >
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                  {getSeverityIcon(issue.severity)}
                                  <span className="text-xs font-medium">{issue.rule}</span>
                                  <Badge variant="outline" className="text-xs">
                                    {issue.line}:{issue.column}
                                  </Badge>
                                </div>
                                <p className="text-xs text-muted-foreground">
                                  {issue.message}
                                </p>
                                {issue.context && (
                                  <code className="text-xs bg-muted px-1 py-0.5 rounded mt-1 block">
                                    {issue.context}
                                  </code>
                                )}
                              </div>
                              <div className="flex flex-col items-end gap-1">
                                <Badge
                                  variant={issue.fixed ? "secondary" : "destructive"}
                                  className={cn("gap-1 text-xs", getSeverityColor(issue.severity))}
                                >
                                  {issue.fixed ? <CheckCircle className="h-3 w-3" /> : getSeverityIcon(issue.severity)}
                                  {issue.severity}
                                </Badge>
                                {issue.autoFixable && (
                                  <Badge variant="outline" className="text-xs">
                                    Auto-fixable
                                  </Badge>
                                )}
                              </div>
                            </div>
                          ))}
                        </CollapsibleContent>
                      </Collapsible>
                    ))
                  )}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="metrics" className="mt-0">
              <div className="p-4">
                {lintResults.length > 0 && lintResults[0]?.metrics ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <p className="text-xs text-muted-foreground">Files Scanned</p>
                        <p className="text-lg font-semibold">{lintResults[0].metrics.total_files}</p>
                      </div>
                      <div className="space-y-1">
                        <p className="text-xs text-muted-foreground">Files with Issues</p>
                        <p className="text-lg font-semibold">{lintResults[0].metrics.files_with_issues}</p>
                      </div>
                      <div className="space-y-1">
                        <p className="text-xs text-muted-foreground">Errors</p>
                        <p className="text-lg font-semibold text-red-600">{lintResults[0].metrics.error_count}</p>
                      </div>
                      <div className="space-y-1">
                        <p className="text-xs text-muted-foreground">Warnings</p>
                        <p className="text-lg font-semibold text-orange-600">{lintResults[0].metrics.warning_count}</p>
                      </div>
                    </div>
                    <Separator />
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <p className="text-xs text-muted-foreground">Quality Score</p>
                        <p className={cn("text-sm font-medium", getQualityScoreColor(lintResults[0].metrics.quality_score))}>
                          {lintResults[0].metrics.quality_score}%
                        </p>
                      </div>
                      <Progress value={lintResults[0].metrics.quality_score} className="h-2" />
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    No metrics available
                  </p>
                )}
              </div>
            </TabsContent>

            <TabsContent value="history" className="mt-0">
              <ScrollArea className="h-[300px]">
                <div className="p-4 space-y-2">
                  {lintResults.map((result) => (
                    <div
                      key={result.id}
                      className="flex items-center justify-between gap-2 p-3 rounded-sm hover:bg-accent/50 transition-colors border"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          {getStatusIcon(result.status)}
                          <span className="text-sm font-medium">{result.linter}</span>
                          {result.issues_found > 0 && (
                            <Badge variant="outline" className="text-xs">
                              {result.issues_found} issues
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {result.target_path} • {new Date(result.started_at).toLocaleString()}
                          {result.completed_at && result.duration && (
                            ` • ${result.duration}ms`
                          )}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={result.status === 'completed' ? 'secondary' : result.status === 'failed' ? 'destructive' : 'default'} className="gap-1">
                          {getStatusIcon(result.status)}
                          {result.status}
                        </Badge>
                        <Button size="sm" variant="ghost" className="h-6 px-2">
                          <Download className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
};
