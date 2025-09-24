import { useState } from 'react';
import { useAgentStore } from '../stores/agentStore';
import { Alert, AlertTitle, AlertDescription } from './ui/alert';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from './ui/alert-dialog';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import { CheckIcon, XIcon, AlertCircleIcon, FileEditIcon, FileIcon, TrashIcon, TerminalIcon, GlobeIcon } from 'lucide-react';

export function ApprovalQueue() {
  const { approvalQueue, updateApproval, removeApproval } = useAgentStore();
  const [selectedApproval, setSelectedApproval] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const pendingApprovals = approvalQueue.filter(item => item.status === 'pending');
  const currentApproval = selectedApproval ? approvalQueue.find(a => a.id === selectedApproval) : null;

  const getOperationIcon = (type: string) => {
    switch (type) {
      case 'file_create':
        return <FileIcon className="h-4 w-4" />;
      case 'file_edit':
        return <FileEditIcon className="h-4 w-4" />;
      case 'file_delete':
        return <TrashIcon className="h-4 w-4" />;
      case 'command_execute':
        return <TerminalIcon className="h-4 w-4" />;
      case 'api_call':
        return <GlobeIcon className="h-4 w-4" />;
      default:
        return <AlertCircleIcon className="h-4 w-4" />;
    }
  };

  const getRiskBadgeVariant = (level: string): "default" | "secondary" | "destructive" | "outline" => {
    switch (level) {
      case 'high':
        return 'destructive';
      case 'medium':
        return 'secondary';
      case 'low':
        return 'outline';
      default:
        return 'default';
    }
  };

  const handleApprove = async () => {
    if (!currentApproval) return;
    setIsProcessing(true);
    try {
      await updateApproval(currentApproval.id, 'approved');
      setTimeout(() => removeApproval(currentApproval.id), 2000);
      setSelectedApproval(null);
    } catch (error) {
      console.error('Failed to approve operation:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReject = async () => {
    if (!currentApproval) return;
    setIsProcessing(true);
    try {
      await updateApproval(currentApproval.id, 'rejected');
      setTimeout(() => removeApproval(currentApproval.id), 2000);
      setSelectedApproval(null);
    } catch (error) {
      console.error('Failed to reject operation:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const formatDiff = (before: string, after: string) => {
    const beforeLines = before.split('\n');
    const afterLines = after.split('\n');
    const maxLines = Math.max(beforeLines.length, afterLines.length);

    return (
      <div className="font-mono text-xs space-y-1">
        {Array.from({ length: maxLines }, (_, i) => {
          const beforeLine = beforeLines[i] || '';
          const afterLine = afterLines[i] || '';

          if (beforeLine === afterLine) {
            return (
              <div key={i} className="text-muted-foreground">
                {beforeLine}
              </div>
            );
          } else if (beforeLine && !afterLine) {
            return (
              <div key={i} className="bg-red-500/10 text-red-700 dark:text-red-400 px-2 py-0.5 rounded">
                - {beforeLine}
              </div>
            );
          } else if (!beforeLine && afterLine) {
            return (
              <div key={i} className="bg-green-500/10 text-green-700 dark:text-green-400 px-2 py-0.5 rounded">
                + {afterLine}
              </div>
            );
          } else {
            return (
              <div key={i} className="space-y-0.5">
                <div className="bg-red-500/10 text-red-700 dark:text-red-400 px-2 py-0.5 rounded">
                  - {beforeLine}
                </div>
                <div className="bg-green-500/10 text-green-700 dark:text-green-400 px-2 py-0.5 rounded">
                  + {afterLine}
                </div>
              </div>
            );
          }
        })}
      </div>
    );
  };

  if (pendingApprovals.length === 0) {
    return null;
  }

  return (
    <>
      {/* Pending Operations Alert */}
      <Alert className="mb-4">
        <AlertCircleIcon className="h-4 w-4" />
        <AlertTitle>Pending Operations</AlertTitle>
        <AlertDescription className="mt-2 space-y-2">
          <div className="text-sm text-muted-foreground">
            {pendingApprovals.length} operation{pendingApprovals.length !== 1 ? 's' : ''} requiring approval
          </div>
          <div className="flex flex-wrap gap-2">
            {pendingApprovals.map(approval => (
              <Button
                key={approval.id}
                variant="outline"
                size="sm"
                onClick={() => setSelectedApproval(approval.id)}
                className="flex items-center gap-2"
              >
                {getOperationIcon(approval.type)}
                <span className="max-w-[200px] truncate">{approval.description}</span>
                <Badge variant={getRiskBadgeVariant(approval.riskLevel)}>
                  {approval.riskLevel}
                </Badge>
              </Button>
            ))}
          </div>
        </AlertDescription>
      </Alert>

      {/* Approval Dialog */}
      <AlertDialog open={!!selectedApproval} onOpenChange={(open) => !open && setSelectedApproval(null)}>
        <AlertDialogContent className="max-w-3xl">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              {currentApproval && getOperationIcon(currentApproval.type)}
              Approval Required
            </AlertDialogTitle>
            <AlertDialogDescription className="space-y-4">
              {currentApproval && (
                <>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{currentApproval.description}</span>
                      <Badge variant={getRiskBadgeVariant(currentApproval.riskLevel)}>
                        {currentApproval.riskLevel} risk
                      </Badge>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Requested by Agent {currentApproval.agentId} • {new Date(currentApproval.timestamp).toLocaleString()}
                    </div>
                  </div>

                  {/* Operation Details */}
                  <div className="rounded-lg border p-3 space-y-2">
                    <div className="text-sm font-medium">Operation Details</div>
                    {currentApproval.details.path && (
                      <div className="text-xs">
                        <span className="text-muted-foreground">Path:</span>{' '}
                        <code className="bg-muted px-1 py-0.5 rounded">{currentApproval.details.path}</code>
                      </div>
                    )}
                    {currentApproval.details.command && (
                      <div className="text-xs">
                        <span className="text-muted-foreground">Command:</span>{' '}
                        <code className="bg-muted px-1 py-0.5 rounded">{currentApproval.details.command}</code>
                      </div>
                    )}
                    {currentApproval.details.endpoint && (
                      <div className="text-xs">
                        <span className="text-muted-foreground">Endpoint:</span>{' '}
                        <code className="bg-muted px-1 py-0.5 rounded">{currentApproval.details.endpoint}</code>
                      </div>
                    )}
                  </div>

                  {/* Diff Preview */}
                  {currentApproval.details.diff && (
                    <div className="space-y-2">
                      <div className="text-sm font-medium">Changes Preview</div>
                      <ScrollArea className="h-[300px] rounded-lg border p-3 bg-muted/30">
                        {formatDiff(currentApproval.details.diff.before, currentApproval.details.diff.after)}
                      </ScrollArea>
                    </div>
                  )}
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isProcessing}>
              Cancel
            </AlertDialogCancel>
            <Button
              variant="destructive"
              onClick={handleReject}
              disabled={isProcessing}
              className="flex items-center gap-2"
            >
              <XIcon className="h-4 w-4" />
              Reject
            </Button>
            <AlertDialogAction
              onClick={handleApprove}
              disabled={isProcessing}
              className="flex items-center gap-2"
            >
              <CheckIcon className="h-4 w-4" />
              Approve
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}