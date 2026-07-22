import { useState, useEffect } from 'react';
import { Icon } from './icons/IconMapping';

import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from './ui/alert-dialog';
import { toast } from '@/hooks/use-toast';
import * as api from '../services/api';

export type ApprovalMode = 'STRICT' | 'AUTO' | 'YOLO';

interface ApprovalModeInfo {
  mode: ApprovalMode;
  icon: React.ReactNode;
  label: string;
  description: string;
  variant: 'default' | 'secondary' | 'destructive' | 'outline';
  color: string;
}

const APPROVAL_MODES: Record<ApprovalMode, ApprovalModeInfo> = {
  STRICT: {
    mode: 'STRICT',
    icon: <Icon name="shield-check" className="h-4 w-4" />,
    label: 'Strict Mode',
    description: 'All operations require explicit approval. No auto-approval, full audit trail.',
    variant: 'default',
    color: 'text-blue-600'
  },
  AUTO: {
    mode: 'AUTO',
    icon: <Icon name="shield" className="h-4 w-4" />,
    label: 'Auto Mode',
    description: 'Safe operations auto-approved, risky operations require approval with smart risk assessment.',
    variant: 'secondary',
    color: 'text-green-600'
  },
  YOLO: {
    mode: 'YOLO',
    icon: <Icon name="bolt" className="h-4 w-4" />,
    label: 'YOLO Mode',
    description: 'All operations auto-approved. No approval dialogs. Use with extreme caution.',
    variant: 'destructive',
    color: 'text-red-600'
  }
};

interface ApprovalModeSelectorProps {
  currentMode?: ApprovalMode;
  onModeChange?: (mode: ApprovalMode) => void;
  showLabel?: boolean;
  variant?: 'dropdown' | 'buttons';
  className?: string;
}

export function ApprovalModeSelector({
  currentMode = 'STRICT',
  onModeChange,
  showLabel = true,
  variant = 'dropdown',
  className = ''
}: ApprovalModeSelectorProps) {
  const [mode, setMode] = useState<ApprovalMode>(currentMode);
  const [isChanging, setIsChanging] = useState(false);
  const [showYoloWarning, setShowYoloWarning] = useState(false);
  const [pendingMode, setPendingMode] = useState<ApprovalMode | null>(null);

  useEffect(() => {
    setMode(currentMode);
  }, [currentMode]);

  // Get current approval mode from settings on mount
  useEffect(() => {
    const fetchCurrentMode = async () => {
      try {
        const approvalMode = await api.getApprovalMode();
        if (approvalMode && Object.keys(APPROVAL_MODES).includes(approvalMode)) {
          setMode(approvalMode as ApprovalMode);
        }
      } catch (error) {
        console.warn('Failed to fetch current approval mode:', error);
      }
    };
    fetchCurrentMode();
  }, []);

  const handleModeChange = async (newMode: ApprovalMode) => {
    if (newMode === mode) return;

    // Show warning for YOLO mode
    if (newMode === 'YOLO') {
      setPendingMode(newMode);
      setShowYoloWarning(true);
      return;
    }

    await applyModeChange(newMode);
  };

  const applyModeChange = async (newMode: ApprovalMode) => {
    setIsChanging(true);
    try {
      // Call API to change approval mode
      await api.setApprovalMode(newMode);

      setMode(newMode);
      onModeChange?.(newMode);

      const modeInfo = APPROVAL_MODES[newMode];
      toast({
        title: 'Approval Mode Changed',
        description: `Switched to ${modeInfo.label}. ${modeInfo.description}`,
        variant: newMode === 'YOLO' ? 'destructive' : 'default',
      });
    } catch (error) {
      console.error('Failed to change approval mode:', error);
      toast({
        title: 'Mode Change Failed',
        description: error instanceof Error ? error.message : 'Failed to update approval mode',
        variant: 'destructive',
      });
    } finally {
      setIsChanging(false);
      setShowYoloWarning(false);
      setPendingMode(null);
    }
  };

  const confirmYoloMode = async () => {
    if (pendingMode === 'YOLO') {
      await applyModeChange('YOLO');
    }
  };

  const currentModeInfo = APPROVAL_MODES[mode];

  if (variant === 'buttons') {
    return (
      <>
        <div className={`flex items-center gap-2 ${className}`}>
          {Object.values(APPROVAL_MODES).map((modeInfo) => (
            <Button
              key={modeInfo.mode}
              variant={mode === modeInfo.mode ? 'default' : 'outline'}
              size="sm"
              onClick={() => handleModeChange(modeInfo.mode)}
              disabled={isChanging}
              className={`flex items-center gap-2 ${mode === modeInfo.mode ? currentModeInfo.color : ''}`}
            >
              {modeInfo.icon}
              {showLabel && <span>{modeInfo.label}</span>}
            </Button>
          ))}
        </div>

        {/* YOLO Warning Dialog */}
        <AlertDialog open={showYoloWarning} onOpenChange={setShowYoloWarning}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle className="flex items-center gap-2 text-destructive">
                <Icon name="alert-triangle" className="h-5 w-5" />
                YOLO Mode Warning
              </AlertDialogTitle>
              <AlertDialogDescription className="space-y-2">
                <p>
                  You are about to enable <strong>YOLO Mode</strong>, which will:
                </p>
                <ul className="list-disc list-inside space-y-1 text-sm">
                  <li>Auto-approve ALL operations without prompting</li>
                  <li>Disable all safety checks and approval dialogs</li>
                  <li>Allow potentially destructive actions to run automatically</li>
                  <li>Bypass security validations</li>
                </ul>
                <p className="font-medium text-destructive">
                  This mode is intended for experienced users only and can cause data loss or security issues.
                </p>
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={confirmYoloMode}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                Enable YOLO Mode
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </>
    );
  }

  return (
    <>
      <div className={`flex items-center gap-2 ${className}`}>
        <Select value={mode} onValueChange={(value) => handleModeChange(value as ApprovalMode)} disabled={isChanging}>
          <SelectTrigger className="w-[180px]">
            <div className="flex items-center gap-2">
              <span className={currentModeInfo.color}>{currentModeInfo.icon}</span>
              <SelectValue />
            </div>
          </SelectTrigger>
          <SelectContent>
            {Object.values(APPROVAL_MODES).map((modeInfo) => (
              <SelectItem key={modeInfo.mode} value={modeInfo.mode}>
                <div className="flex items-center gap-2">
                  <span className={modeInfo.color}>{modeInfo.icon}</span>
                  <span>{modeInfo.label}</span>
                  {modeInfo.mode === 'YOLO' && (
                    <Badge variant="destructive" className="ml-1 text-xs">
                      ⚠️
                    </Badge>
                  )}
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {showLabel && (
          <div className="text-xs text-muted-foreground max-w-[200px]">
            {currentModeInfo.description}
          </div>
        )}
      </div>

      {/* YOLO Warning Dialog */}
      <AlertDialog open={showYoloWarning} onOpenChange={setShowYoloWarning}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2 text-destructive">
              <Icon name="alert-triangle" className="h-5 w-5" />
              YOLO Mode Warning
            </AlertDialogTitle>
            <AlertDialogDescription className="space-y-2">
              <p>
                You are about to enable <strong>YOLO Mode</strong>, which will:
              </p>
              <ul className="list-disc list-inside space-y-1 text-sm">
                <li>Auto-approve ALL operations without prompting</li>
                <li>Disable all safety checks and approval dialogs</li>
                <li>Allow potentially destructive actions to run automatically</li>
                <li>Bypass security validations</li>
              </ul>
              <p className="font-medium text-destructive">
                This mode is intended for experienced users only and can cause data loss or security issues.
              </p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmYoloMode}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Enable YOLO Mode
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

// Utility function to get mode info
export const getApprovalModeInfo = (mode: ApprovalMode): ApprovalModeInfo => {
  return APPROVAL_MODES[mode];
};

// Status indicator component
interface ApprovalModeStatusProps {
  mode: ApprovalMode;
  className?: string;
}

export function ApprovalModeStatus({ mode, className = '' }: ApprovalModeStatusProps) {
  const modeInfo = APPROVAL_MODES[mode];

  return (
    <Badge variant={modeInfo.variant} className={`flex items-center gap-1 ${className}`}>
      <span className={modeInfo.color}>{modeInfo.icon}</span>
      <span>{modeInfo.label}</span>
      {mode === 'YOLO' && <span>⚠️</span>}
    </Badge>
  );
}