import { Icon } from './icons/IconMapping';
import * as React from 'react';

import { OpenWorkspaceResult, getRecentWorkspaces, openWorkspace } from '@/services/api';
import { RecentWorkspace } from '@/types';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';

interface OpenWorkspaceDialogProps {
  onWorkspaceSelect?: (result: OpenWorkspaceResult) => void;
  currentWorkspace?: string | null;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export function OpenWorkspaceDialog({ onWorkspaceSelect, currentWorkspace, open: controlledOpen, onOpenChange }: OpenWorkspaceDialogProps) {
  const [uncontrolledOpen, setUncontrolledOpen] = React.useState(false);
  const [recents, setRecents] = React.useState<RecentWorkspace[]>([]);
  const [loadingRecents, setLoadingRecents] = React.useState(false);
  const [path, setPath] = React.useState('');
  const [selectedPath, setSelectedPath] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const fetchRecents = React.useCallback(async () => {
    try {
      setLoadingRecents(true);
      setError(null);
      const payload = await getRecentWorkspaces();
      setRecents(Array.isArray(payload?.recent) ? payload.recent : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load recent workspaces');
    } finally {
      setLoadingRecents(false);
    }
  }, []);

  const open = controlledOpen ?? uncontrolledOpen;
  const setOpen = React.useCallback((value: boolean) => {
    if (controlledOpen === undefined) {
      setUncontrolledOpen(value);
    }
    onOpenChange?.(value);
  }, [controlledOpen, onOpenChange]);

  React.useEffect(() => {
    if (open) {
      void fetchRecents();
    } else {
      setError(null);
      setSelectedPath(null);
    }
  }, [open, fetchRecents]);

  const handleSubmit = async (workspacePath: string) => {
    setIsSubmitting(true);
    setError(null);
    try {
      const result = await openWorkspace(workspacePath);
      onWorkspaceSelect?.(result);
      setOpen(false);
      setPath('');
      setSelectedPath(null);
      await fetchRecents();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to open workspace');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOpenClick = () => {
    const target = selectedPath || path.trim();
    if (!target) {
      setError('Enter a workspace path to continue.');
      return;
    }
    void handleSubmit(target);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <Icon name="folder-open" className="h-4 w-4" />
          Open Workspace
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Select workspace</DialogTitle>
          <DialogDescription>
            Provide a project directory or choose from recently opened workspaces.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <Icon name="alert-circle" className="h-4 w-4" />
              <AlertTitle>Workspace error</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="workspace-path">
              Workspace path
            </label>
            <div className="flex gap-2">
              <Input
                id="workspace-path"
                placeholder="/Users/me/projects/casper-prime"
                value={path}
                onChange={(event) => setPath(event.target.value)}
                spellCheck={false}
                autoComplete="off"
              />
              <Button onClick={() => void fetchRecents()} variant="ghost" size="icon" disabled={loadingRecents} aria-label="Refresh recent workspaces">
                <Icon name="refresh-cw" className={`h-4 w-4 ${loadingRecents ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </div>

          <Separator />

          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-muted-foreground">Recent workspaces</p>
            <Button
              variant="secondary"
              size="sm"
              className="gap-2"
              onClick={() => setError('Native browse dialogs are not yet supported.')}
            >
              <Icon name="database" className="h-4 w-4" />
              Browse…
            </Button>
          </div>

          <ScrollArea className="h-[360px] rounded-md border">
            <div className="p-4 space-y-2">
              {loadingRecents ? (
                Array.from({ length: 3 }).map((_, index) => (
                  <Skeleton key={index} className="h-20 w-full" />
                ))
              ) : recents.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No workspaces have been opened yet. Provide a directory path above to get started.
                </p>
              ) : (
                recents.map((workspace) => {
                  const isActive = currentWorkspace && workspace.path === currentWorkspace;
                  const isSelected = selectedPath === workspace.path;
                  return (
                    <button
                      key={workspace.path}
                      type="button"
                      className={`w-full rounded-md border p-4 text-left transition-colors ${
                        isSelected ? 'border-primary bg-muted/60' : 'hover:bg-muted/40'
                      } ${isActive ? 'opacity-60' : ''}`}
                      onClick={() => setSelectedPath(workspace.path)}
                      onDoubleClick={() => !isActive && handleSubmit(workspace.path)}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{workspace.name}</span>
                            {isActive && <Badge variant="secondary">Current</Badge>}
                          </div>
                          <p className="truncate text-sm text-muted-foreground">
                            {workspace.path}
                          </p>
                          <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                            <span className="inline-flex items-center gap-1">
                              <Icon name="clock" className="h-3 w-3" />
                              {new Date(workspace.last_opened).toLocaleString()}
                            </span>
                            <Badge variant="outline" className="text-xs">
                              {workspace.language || 'Unknown'}
                            </Badge>
                            {workspace.framework && workspace.framework !== 'unknown' && (
                              <Badge variant="secondary" className="text-xs">
                                {workspace.framework}
                              </Badge>
                            )}
                            <span>{workspace.file_count} files</span>
                          </div>
                        </div>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </ScrollArea>

          <Separator />

          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              Double-click a recent workspace or confirm the selected path to continue.
            </p>
            <div className="flex gap-2">
              <Button variant="ghost" onClick={() => setOpen(false)} disabled={isSubmitting}>
                Cancel
              </Button>
              <Button onClick={handleOpenClick} disabled={isSubmitting}>
                {isSubmitting ? 'Opening…' : 'Open'}
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
