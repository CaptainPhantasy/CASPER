import { useState, useEffect } from 'react';
import { useAgentStore } from '../stores/agentStore';
import { Alert, AlertTitle, AlertDescription } from './ui/alert';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from './ui/alert-dialog';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import { Icon } from './icons/IconMapping';
import * as api from '../services/api';
import { toast } from '@/hooks/use-toast';
import { ApprovalModeSelector, ApprovalModeStatus, getApprovalModeInfo, type ApprovalMode } from './ApprovalModeSelector';
import { validateOperation, explainRisk, type OperationContext } from '../utils/permissionValidation';

export function ApprovalQueue() {
  const { approvalQueue, updateApproval, removeApproval, addApproval } = useAgentStore();
  const [selectedApproval, setSelectedApproval] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastFetch, setLastFetch] = useState<number>(0);
  const [approvalMode, setApprovalMode] = useState<ApprovalMode>('STRICT');

  const pendingApprovals = approvalQueue.filter(item => item.status === 'pending');
  const currentApproval = selectedApproval ? approvalQueue.find(a => a.id === selectedApproval) : null;

  // Convert approval item to operation context for validation
  const approvalToOperation = (approval: any): OperationContext => {
    return {
      type: approval.type,
      path: approval.details?.path,
      command: approval.details?.command,
      endpoint: approval.details?.endpoint,
      content: approval.details?.content,
      details: approval.details,
    };
  };

  // Enhanced validation using the new system
  const validateApprovalOperation = (approval: any) => {
    const operation = approvalToOperation(approval);
    return validateOperation(operation, approvalMode);
  };

  // Fetch pending approvals from backend
  const fetchPendingApprovals = async () => {
    try {
      setIsRefreshing(true);
      const approvals = await api.getPendingApprovals();

      // Add new approvals to store
      if (Array.isArray(approvals)) {
        for (const approval of approvals) {
          // Only add if not already in queue
          const exists = approvalQueue.find(a => a.id === approval.id);
          if (!exists) {
            const approvalItem = {
              id: approval.id,
              type: approval.type || 'unknown',
              description: approval.description || 'No description',
              riskLevel: approval.riskLevel || approval.risk_level || 'medium',
              agentId: approval.agentId || approval.agent_id || 'unknown',
              timestamp: approval.timestamp || Date.now(),
              status: approval.status || 'pending',
              details: approval.details || {},
            };

            // Validate operation using new system
            const validation = validateApprovalOperation(approvalItem);

            // Update risk level based on validation
            approvalItem.riskLevel = validation.risk.level;

            // Auto-approve if validation allows it
            if (validation.autoApprove) {
              try {
                await api.approveOperation(approvalItem.id);
                approvalItem.status = 'approved';

                toast({
                  title: 'Auto-Approved',
                  description: `${approvalItem.description} was automatically approved (${approvalMode} mode)`,
                  duration: 3000,
                });

                // Remove from queue after short delay
                setTimeout(() => removeApproval(approvalItem.id), 2000);
              } catch (autoApprovalError) {
                console.error('Auto-approval failed:', autoApprovalError);
                // If auto-approval fails, add to queue for manual approval
                addApproval(approvalItem);
              }
            } else {
              addApproval(approvalItem);
            }
          }
        }
      }

      setLastFetch(Date.now());
    } catch (error) {
      console.error('Failed to fetch pending approvals:', error);
      toast({
        title: 'Failed to Fetch Approvals',
        description: 'Could not retrieve pending approvals from backend',
        variant: 'destructive',
      });
    } finally {
      setIsRefreshing(false);
    }
  };

  // Load approval mode from settings on mount
  useEffect(() => {
    const loadApprovalMode = async () => {
      try {
        const mode = await api.getApprovalMode();
        setApprovalMode(mode as ApprovalMode);
      } catch (error) {
        console.warn('Failed to load approval mode, using STRICT as default');
        setApprovalMode('STRICT');
      }
    };
    loadApprovalMode();
  }, []);

  // Auto-refresh every 30 seconds or when component mounts
  useEffect(() => {
    const now = Date.now();
    if (now - lastFetch > 30000 || lastFetch === 0) {
      fetchPendingApprovals();
    }

    const interval = setInterval(() => {
      fetchPendingApprovals();
    }, 30000);

    return () => clearInterval(interval);
  }, [approvalMode]); // Re-fetch when approval mode changes

  // Refresh on approval queue changes from WebSocket
  useEffect(() => {
    const hasNewPending = approvalQueue.some(a => a.status === 'pending' && Number(a.timestamp) > lastFetch);
    if (hasNewPending) {
      setLastFetch(Date.now());
    }
  }, [approvalQueue]);

  const getOperationIcon = (type: string) => {
    switch (type) {
      case 'file_create':
        return <Icon name="file" className="h-4 w-4 text-green-500" />;
      case 'file_edit':
        return <Icon name="file-edit" className="h-4 w-4 text-blue-500" />;
      case 'file_delete':
        return <Icon name="trash" className="h-4 w-4 text-red-500" />;
      case 'command_execute':
        return <Icon name="terminal" className="h-4 w-4 text-purple-500" />;
      case 'api_call':
        return <Icon name="globe" className="h-4 w-4 text-orange-500" />;
      default:
        return <Icon name="alert-circle" className="h-4 w-4 text-gray-500" />;
    }
  };

  const getOperationLabel = (type: string) => {
    switch (type) {
      case 'file_create':
        return 'Create File';
      case 'file_edit':
        return 'Edit File';
      case 'file_delete':
        return 'Delete File';
      case 'command_execute':
        return 'Run Command';
      case 'api_call':
        return 'API Call';
      default:
        return 'Unknown Operation';
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
      // Call backend API to approve
      await api.approveOperation(currentApproval.id);

      // Update local store
      await updateApproval(currentApproval.id, 'approved');

      // Remove from queue after short delay
      setTimeout(() => removeApproval(currentApproval.id), 2000);

      setSelectedApproval(null);

      toast({
        title: 'Operation Approved',
        description: `${currentApproval.description} has been approved`,
      });
    } catch (error) {
      console.error('Failed to approve operation:', error);
      toast({
        title: 'Approval Failed',
        description: error instanceof Error ? error.message : 'Failed to approve operation',
        variant: 'destructive',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReject = async () => {
    if (!currentApproval) return;
    setIsProcessing(true);
    try {
      // Call backend API to reject
      await api.rejectOperation(currentApproval.id);

      // Update local store
      await updateApproval(currentApproval.id, 'rejected');

      // Remove from queue after short delay
      setTimeout(() => removeApproval(currentApproval.id), 2000);

      setSelectedApproval(null);

      toast({
        title: 'Operation Rejected',
        description: `${currentApproval.description} has been rejected`,
        variant: 'destructive',
      });
    } catch (error) {
      console.error('Failed to reject operation:', error);
      toast({
        title: 'Rejection Failed',
        description: error instanceof Error ? error.message : 'Failed to reject operation',
        variant: 'destructive',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleModeChange = (newMode: ApprovalMode) => {
    setApprovalMode(newMode);
    // Re-fetch approvals to apply new mode logic
    setTimeout(() => {
      fetchPendingApprovals();
    }, 500);
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

  return (
    <>
      {/* Approval Mode Selector */}
      <div className="mb-4 p-3 rounded-lg border bg-card">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon name="shield" className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Approval Mode</span>
            <ApprovalModeStatus mode={approvalMode} />
          </div>
          <ApprovalModeSelector
            currentMode={approvalMode}
            onModeChange={handleModeChange}
            showLabel={false}
            variant="dropdown"
            className="w-auto"
          />
        </div>
        <div className="mt-2 text-xs text-muted-foreground">
          {getApprovalModeInfo(approvalMode).description}
        </div>
      </div>

      {/* Pending Operations Alert */}
      {pendingApprovals.length > 0 && (
        <Alert className="mb-4">
          <Icon name="alert-circle" className="h-4 w-4" />
          <AlertTitle>Pending Operations</AlertTitle>
          <AlertDescription className="mt-2 space-y-2">
            <div className="text-sm text-muted-foreground">
              {pendingApprovals.length} operation{pendingApprovals.length !== 1 ? 's' : ''} requiring approval
            </div>
            <div className="flex flex-wrap gap-2 items-center">
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
              <Button
                variant="ghost"
                size="sm"
                onClick={fetchPendingApprovals}
                disabled={isRefreshing}
                className="flex items-center gap-1 ml-auto"
              >
                <Icon name="refresh-cw" className={`h-3 w-3 ${isRefreshing ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* Show mode info when no pending approvals */}
      {pendingApprovals.length === 0 && (
        <div className="p-4 rounded-lg border bg-card/30 text-center text-muted-foreground">
          <Icon name="shield" className="h-8 w-8 mx-auto mb-2" />
          <p className="text-sm">No pending approvals</p>
          <p className="text-xs mt-1">
            Current mode: <ApprovalModeStatus mode={approvalMode} className="inline-flex" />
          </p>
        </div>
      )}

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
                      <div className="flex items-center gap-2">
                        {getOperationIcon(currentApproval.type)}
                        <span className="font-medium">{getOperationLabel(currentApproval.type)}</span>
                      </div>
                      <Badge variant={getRiskBadgeVariant(currentApproval.riskLevel)}>
                        {currentApproval.riskLevel} risk
                      </Badge>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {currentApproval.description}
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

                  {/* Risk Assessment */}
                  {(() => {
                    const validation = validateApprovalOperation(currentApproval);
                    const riskExplanation = explainRisk(validation.risk);

                    return (
                      <div className="rounded-lg border p-3 space-y-2">
                        <div className="flex items-center gap-2">
                          <Icon name="info" className="h-4 w-4 text-blue-500" />
                          <div className="text-sm font-medium">Security Assessment</div>
                          <Badge variant={getRiskBadgeVariant(validation.risk.level)} className="ml-auto">
                            {validation.risk.level} risk ({validation.risk.score}/100)
                          </Badge>
                        </div>
                        <div className="text-xs text-muted-foreground whitespace-pre-line">
                          {riskExplanation}
                        </div>
                        {validation.reason && (
                          <div className="text-xs">
                            <span className="text-muted-foreground">Validation:</span>{' '}
                            <span className={validation.autoApprove ? 'text-green-600' : 'text-yellow-600'}>
                              {validation.reason}
                            </span>
                          </div>
                        )}
                      </div>
                    );
                  })()}

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
              <Icon name="x" className="h-4 w-4" />
              Reject
            </Button>
            <AlertDialogAction
              onClick={handleApprove}
              disabled={isProcessing}
              className="flex items-center gap-2"
            >
              <Icon name="check" className="h-4 w-4" />
              Approve
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}