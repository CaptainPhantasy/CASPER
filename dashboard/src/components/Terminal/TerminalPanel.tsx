import React, { useEffect, useState } from 'react';
import { Icon } from '../icons/IconMapping';
import { TerminalTabs } from './TerminalTabs';
import { TerminalComponent } from './TerminalComponent';
import { OmegaTerminal } from './OmegaTerminal';
import { useTerminalStore } from '@/stores/terminalStore';
import { terminalWsManager } from '@/services/terminalWebSocket';
import { cn } from '@/lib/utils';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';

interface TerminalPanelProps {
  className?: string;
}

export const TerminalPanel: React.FC<TerminalPanelProps> = ({ className }) => {
  const { sessions, activeSessionId, createSession, isTerminalVisible } = useTerminalStore();
  const sessionList = Array.from(sessions.values());
  const [useOmegaTerminal, setUseOmegaTerminal] = useState(true);

  // Initialize WebSocket connection and create first session
  useEffect(() => {
    terminalWsManager.connect();

    // Create initial session if none exists
    if (sessionList.length === 0) {
      createSession('Terminal 1');
    }

    // Cleanup on unmount
    return () => {
      terminalWsManager.disconnect();
    };
  }, []);

  // Don't render if terminal is not visible
  if (!isTerminalVisible) {
    return null;
  }

  return (
    <div className={cn('flex flex-col bg-background border border-border rounded-lg overflow-hidden', className)}>
      <div className="flex items-center justify-between border-b bg-card/60 px-4 py-2">
        <TerminalTabs />
        <div className="flex items-center gap-2">
          <Icon name="shield" className={cn("h-4 w-4", useOmegaTerminal ? "text-green-500" : "text-muted-foreground")} />
          <Label htmlFor="omega-mode" className="text-sm">Omega Security</Label>
          <Switch
            id="omega-mode"
            checked={useOmegaTerminal}
            onCheckedChange={setUseOmegaTerminal}
          />
        </div>
      </div>

      <div className="flex-1 overflow-hidden">
        {activeSessionId ? (
          useOmegaTerminal ? (
            <OmegaTerminal sessionId={activeSessionId} className="h-full" />
          ) : (
            <TerminalComponent sessionId={activeSessionId} className="h-full" />
          )
        ) : (
          <div className="h-full flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <Icon name="terminal" className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-medium">No Terminal Session</p>
              <p className="text-sm">Create a new terminal session to get started</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};