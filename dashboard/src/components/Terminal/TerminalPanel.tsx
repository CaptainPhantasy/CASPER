import React, { useEffect } from 'react';
import { Terminal as TerminalIcon } from 'lucide-react';
import { TerminalTabs } from './TerminalTabs';
import { TerminalComponent } from './TerminalComponent';
import { useTerminalStore } from '@/stores/terminalStore';
import { terminalWsManager } from '@/services/terminalWebSocket';
import { cn } from '@/lib/utils';

interface TerminalPanelProps {
  className?: string;
}

export const TerminalPanel: React.FC<TerminalPanelProps> = ({ className }) => {
  const { sessions, activeSessionId, createSession, isTerminalVisible } = useTerminalStore();
  const sessionList = Array.from(sessions.values());

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
      <TerminalTabs />

      <div className="flex-1 overflow-hidden">
        {activeSessionId ? (
          <TerminalComponent sessionId={activeSessionId} className="h-full" />
        ) : (
          <div className="h-full flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <TerminalIcon className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-medium">No Terminal Session</p>
              <p className="text-sm">Create a new terminal session to get started</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};