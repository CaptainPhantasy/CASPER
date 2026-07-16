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
import {
  IconShield as Shield,
  IconShieldExclamation as ShieldAlert,
  IconShieldCheck as ShieldCheck,
  IconShieldX as ShieldX,
  IconPlayerPlay as Play,
  IconRefresh as RefreshCw,
  IconAlertTriangle as AlertTriangle,
  IconAlertCircle as AlertCircle,
  IconCircleCheck as CheckCircle,
  IconClock as Clock,
  IconLoader2 as Loader2,
  IconEye as Eye,
  IconDownload as Download
} from "@tabler/icons-react";
import { cn } from "@/lib/utils";
import { API_BASE } from "@/services/api";

interface SecurityIssue {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  type: 'vulnerability' | 'dependency' | 'code' | 'configuration' | 'secret';
  title: string;
  description: string;
  file?: string;
  line?: number;
  solution?: string;
  cve?: string;
  cvss_score?: number;
  fixed?: boolean;
}

interface ScanResult {
  id: string;
  started_at: string;
  completed_at?: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  scan_type: 'full' | 'dependencies' | 'secrets' | 'code' | 'configuration';
  progress?: number;
  issues_found: number;
  issues: SecurityIssue[];
  duration?: number;
}

interface ScannerStatus {
  last_scan?: string;
  scan_count: number;
  total_issues: number;
  critical_issues: number;
  tools_available: string[];
  scanning_capabilities: string[];
}

const getSeverityColor = (severity: string) => {
  switch (severity) {
    case 'critical': return 'text-red-600 dark:text-red-400';
    case 'high': return 'text-orange-600 dark:text-orange-400';
    case 'medium': return 'text-yellow-600 dark:text-yellow-400';
    case 'low': return 'text-blue-600 dark:text-blue-400';
    case 'info': return 'text-gray-600 dark:text-gray-400';
    default: return 'text-muted-foreground';
  }
};

const getSeverityIcon = (severity: string) => {
  switch (severity) {
    case 'critical': return <ShieldAlert className="h-3 w-3 text-red-500" />;
    case 'high': return <ShieldX className="h-3 w-3 text-orange-500" />;
    case 'medium': return <AlertTriangle className="h-3 w-3 text-yellow-500" />;
    case 'low': return <AlertCircle className="h-3 w-3 text-blue-500" />;
    case 'info': return <CheckCircle className="h-3 w-3 text-gray-500" />;
    default: return <Shield className="h-3 w-3" />;
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
      return <ShieldX className="h-3 w-3 text-muted-foreground" />;
    default:
      return <Clock className="h-3 w-3 text-muted-foreground" />;
  }
};

export const SecurityScanner: React.FC = () => {
  const [scannerStatus, setScannerStatus] = React.useState<ScannerStatus | null>(null);
  const [scanResults, setScanResults] = React.useState<ScanResult[]>([]);
  const [currentScan, setCurrentScan] = React.useState<ScanResult | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [selectedScanType, setSelectedScanType] = React.useState("full");
  const [targetPath, setTargetPath] = React.useState("");
  const [, setSelectedIssue] = React.useState<SecurityIssue | null>(null);

  // Fetch scanner status and scan history
  const fetchScannerInfo = React.useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [statusRes, historyRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/dev/security/status`),
        fetch(`${API_BASE}/api/dev/security/scans`)
      ]);

      if (statusRes.status === 'fulfilled' && statusRes.value.ok) {
        const status = await statusRes.value.json();
        setScannerStatus(status);
      }

      if (historyRes.status === 'fulfilled' && historyRes.value.ok) {
        const history = await historyRes.value.json();
        setScanResults(history.scans || []);

        // Check for active scan
        const activeScan = history.scans?.find((scan: ScanResult) => scan.status === 'running');
        if (activeScan) {
          setCurrentScan(activeScan);
        }
      }

    } catch (err) {
      console.error('Error fetching scanner info:', err);
      setError('Failed to connect to security scanner service');
    } finally {
      setLoading(false);
    }
  }, []);

  // Execute security scan
  const executeScan = React.useCallback(async (scanType: string, options?: any) => {
    try {
      setError(null);

      const body: any = {
        scan_type: scanType,
        target_path: targetPath || ".",
        ...options
      };

      const res = await fetch(`${API_BASE}/api/dev/scan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        throw new Error(`Security scan failed: ${res.statusText}`);
      }

      const result = await res.json();

      if (result.scan_id) {
        // Start polling for scan progress
        pollScanProgress(result.scan_id);
      }

      // Refresh data
      await fetchScannerInfo();

      if (result.error) {
        setError(result.error);
      }

    } catch (err) {
      console.error('Scan error:', err);
      setError(err instanceof Error ? err.message : 'Security scan failed');
    }
  }, [targetPath, fetchScannerInfo]);

  // Poll for scan progress
  const pollScanProgress = React.useCallback(async (scanId: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/dev/security/scan/${scanId}`);
        if (res.ok) {
          const scan = await res.json();
          setCurrentScan(scan);

          if (scan.status === 'completed' || scan.status === 'failed' || scan.status === 'cancelled') {
            clearInterval(interval);
            setCurrentScan(null);
            await fetchScannerInfo();
          }
        }
      } catch (error) {
        console.error('Error polling scan progress:', error);
        clearInterval(interval);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [fetchScannerInfo]);

  // Load initial data
  React.useEffect(() => {
    fetchScannerInfo();
  }, [fetchScannerInfo]);

  return (
    <div className="space-y-4">
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Scanner Status Card */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Shield className="h-4 w-4 text-blue-500" />
              Security Scanner
            </CardTitle>
            <div className="flex items-center gap-2">
              <Badge variant={scannerStatus ? "secondary" : "destructive"} className="gap-1">
                <ShieldCheck className="h-3 w-3" />
                {scannerStatus ? 'Ready' : 'Not Available'}
              </Badge>
              <Button
                size="sm"
                variant="outline"
                onClick={fetchScannerInfo}
                disabled={loading}
              >
                <RefreshCw className={cn("h-3 w-3", loading && "animate-spin")} />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {scannerStatus && (
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Total Scans</p>
                <p className="text-sm font-medium">{scannerStatus.scan_count}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Total Issues</p>
                <p className="text-sm font-medium">{scannerStatus.total_issues}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Critical Issues</p>
                <p className="text-sm font-medium text-red-600">
                  {scannerStatus.critical_issues}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Last Scan</p>
                <p className="text-sm font-medium">
                  {scannerStatus.last_scan
                    ? new Date(scannerStatus.last_scan).toLocaleDateString()
                    : 'Never'}
                </p>
              </div>
            </div>
          )}

          <Separator />

          {/* Scan Configuration */}
          <div className="space-y-3">
            <div className="flex items-center gap-4">
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Scan Type</p>
                <Select value={selectedScanType} onValueChange={setSelectedScanType}>
                  <SelectTrigger className="w-40">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="full">Full Scan</SelectItem>
                    <SelectItem value="dependencies">Dependencies</SelectItem>
                    <SelectItem value="secrets">Secrets</SelectItem>
                    <SelectItem value="code">Code Quality</SelectItem>
                    <SelectItem value="configuration">Configuration</SelectItem>
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
              <Button
                onClick={() => executeScan(selectedScanType)}
                disabled={currentScan !== null || !scannerStatus}
                className="mt-6"
              >
                {currentScan ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                Start Scan
              </Button>
            </div>
          </div>

          {/* Current Scan Progress */}
          {currentScan && (
            <>
              <Separator />
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium">Scanning in progress...</p>
                  <Badge variant="default" className="gap-1">
                    {getStatusIcon(currentScan.status)}
                    {currentScan.scan_type} scan
                  </Badge>
                </div>
                {currentScan.progress !== undefined && (
                  <Progress value={currentScan.progress} className="h-2" />
                )}
                <p className="text-xs text-muted-foreground">
                  Started: {new Date(currentScan.started_at).toLocaleTimeString()}
                  {currentScan.issues_found > 0 && ` • ${currentScan.issues_found} issues found`}
                </p>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Scan Results Tabs */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Scan Results</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Tabs defaultValue="issues" className="w-full">
            <div className="px-4 pt-2">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="issues">Security Issues</TabsTrigger>
                <TabsTrigger value="history">Scan History</TabsTrigger>
                <TabsTrigger value="reports">Reports</TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="issues" className="mt-0">
              <ScrollArea className="h-[300px]">
                <div className="p-4 space-y-2">
                  {scanResults.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-8">
                      No security scans performed yet
                    </p>
                  ) : (
                    scanResults
                      .filter(scan => scan.status === 'completed')
                      .flatMap(scan => scan.issues)
                      .map((issue) => (
                        <div
                          key={issue.id}
                          className={cn(
                            "flex items-start justify-between gap-2 p-3 rounded-sm hover:bg-accent/50 transition-colors cursor-pointer border",
                            issue.severity === 'critical' && "border-red-200 bg-red-50/50 dark:border-red-800 dark:bg-red-950/20",
                            issue.severity === 'high' && "border-orange-200 bg-orange-50/50 dark:border-orange-800 dark:bg-orange-950/20"
                          )}
                          onClick={() => setSelectedIssue(issue)}
                        >
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              {getSeverityIcon(issue.severity)}
                              <span className="text-sm font-medium">{issue.title}</span>
                              <Badge variant="outline" className="text-xs">
                                {issue.type}
                              </Badge>
                            </div>
                            <p className="text-xs text-muted-foreground truncate">
                              {issue.description}
                            </p>
                            {issue.file && (
                              <p className="text-xs text-muted-foreground mt-1">
                                {issue.file}
                                {issue.line && `:${issue.line}`}
                              </p>
                            )}
                            {issue.cve && (
                              <div className="flex items-center gap-2 mt-1">
                                <Badge variant="outline" className="text-xs">
                                  {issue.cve}
                                </Badge>
                                {issue.cvss_score && (
                                  <Badge variant="outline" className="text-xs">
                                    CVSS: {issue.cvss_score}
                                  </Badge>
                                )}
                              </div>
                            )}
                          </div>
                          <div className="flex flex-col items-end gap-1">
                            <Badge
                              variant={issue.fixed ? "secondary" : "destructive"}
                              className={cn("gap-1 text-xs", getSeverityColor(issue.severity))}
                            >
                              {issue.fixed ? <CheckCircle className="h-3 w-3" /> : getSeverityIcon(issue.severity)}
                              {issue.severity.toUpperCase()}
                            </Badge>
                            <Button size="sm" variant="ghost" className="h-6 px-2">
                              <Eye className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>
                      ))
                  )}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="history" className="mt-0">
              <ScrollArea className="h-[300px]">
                <div className="p-4 space-y-2">
                  {scanResults.map((scan) => (
                    <div
                      key={scan.id}
                      className="flex items-center justify-between gap-2 p-3 rounded-sm hover:bg-accent/50 transition-colors border"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          {getStatusIcon(scan.status)}
                          <span className="text-sm font-medium capitalize">{scan.scan_type} Scan</span>
                          {scan.issues_found > 0 && (
                            <Badge variant="outline" className="text-xs">
                              {scan.issues_found} issues
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">
                          Started: {new Date(scan.started_at).toLocaleString()}
                          {scan.completed_at && scan.duration && (
                            ` • Duration: ${scan.duration}ms`
                          )}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={scan.status === 'completed' ? 'secondary' : scan.status === 'failed' ? 'destructive' : 'default'} className="gap-1">
                          {getStatusIcon(scan.status)}
                          {scan.status}
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

            <TabsContent value="reports" className="mt-0">
              <div className="p-4 text-center py-8">
                <p className="text-sm text-muted-foreground">
                  Report generation and export features coming soon
                </p>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
};
