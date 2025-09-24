import { BarChart3, Clock, Files, FolderTree, TrendingUp } from 'lucide-react';

import { ProjectAnalysis } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';

interface ProjectAnalysisPanelProps {
  analysis?: ProjectAnalysis | null;
  loading?: boolean;
}

const formatBytes = (bytes: number | undefined) => {
  if (!bytes || Number.isNaN(bytes)) return '—';
  const units = ['B', 'KB', 'MB', 'GB'];
  const index = Math.min(units.length - 1, Math.floor(Math.log(bytes) / Math.log(1024)));
  return `${(bytes / Math.pow(1024, index)).toFixed(1)} ${units[index]}`;
};

export function ProjectAnalysisPanel({ analysis, loading }: ProjectAnalysisPanelProps) {
  if (loading) {
    return (
      <Card className="bg-card/70">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Project insights</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-24 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!analysis) {
    return (
      <Card className="bg-card/70">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Project insights</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          No analysis available yet. Open a workspace to view structure insights.
        </CardContent>
      </Card>
    );
  }

  const topTypes = Object.entries(analysis.file_types || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);

  return (
    <Card className="bg-card/70">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Project insights</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="flex flex-col gap-1 rounded-md border border-border/60 bg-muted/30 p-3">
            <span className="flex items-center gap-2 font-medium text-foreground">
              <Files className="h-3.5 w-3.5 text-primary" />
              Files
            </span>
            <span className="text-lg font-semibold">{analysis.total_files}</span>
          </div>
          <div className="flex flex-col gap-1 rounded-md border border-border/60 bg-muted/30 p-3">
            <span className="flex items-center gap-2 font-medium text-foreground">
              <FolderTree className="h-3.5 w-3.5 text-primary" />
              Directories
            </span>
            <span className="text-lg font-semibold">{analysis.total_directories}</span>
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground">
            <BarChart3 className="h-3 w-3" />
            File type distribution
          </div>
          <div className="flex flex-wrap gap-2">
            {topTypes.length === 0 ? (
              <span className="text-sm text-muted-foreground">No file types detected.</span>
            ) : (
              topTypes.map(([ext, count]) => (
                <Badge key={ext} variant="outline" className="gap-1">
                  {ext === 'no_extension' ? 'No extension' : ext}
                  <span className="text-muted-foreground">{count}</span>
                </Badge>
              ))
            )}
          </div>
        </div>

        <Separator />

        <div className="space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground">
            <TrendingUp className="h-3 w-3" />
            Largest files
          </div>
          <div className="space-y-2 text-xs">
            {analysis.largest_files.length === 0 ? (
              <p className="text-muted-foreground">No measurable files yet.</p>
            ) : (
              analysis.largest_files.map((file) => (
                <div key={file.path} className="flex items-center justify-between rounded-sm border border-border/40 bg-background/80 px-2 py-1">
                  <span className="truncate font-medium">{file.path}</span>
                  <span className="text-muted-foreground">{formatBytes(file.size)}</span>
                </div>
              ))
            )}
          </div>
        </div>

        <Separator />

        <div className="space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground">
            <Clock className="h-3 w-3" />
            Recently modified
          </div>
          <div className="space-y-2 text-xs">
            {analysis.recent_files.length === 0 ? (
              <p className="text-muted-foreground">No recent file activity recorded.</p>
            ) : (
              analysis.recent_files.map((file) => (
                <div key={file.path} className="flex items-center justify-between rounded-sm border border-border/40 bg-background/80 px-2 py-1">
                  <span className="truncate font-medium">{file.path}</span>
                  <span className="text-muted-foreground">{new Date(file.modified).toLocaleString()}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
