import React from 'react';
import { Icon } from '../icons/IconMapping';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useTerminalStore } from '@/stores/terminalStore';
import { cn } from '@/lib/utils';

export const TerminalTabs: React.FC = () => {
  const {
    sessions,
    activeSessionId,
    createSession,
    removeSession,
    setActiveSession,
  } = useTerminalStore();

  const sessionList = Array.from(sessions.values()).sort((a, b) => a.createdAt - b.createdAt);

  const handleCreateSession = () => {
    createSession();
  };

  const handleRemoveSession = (sessionId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    removeSession(sessionId);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected':
        return 'text-green-500';
      case 'connecting':
        return 'text-yellow-500';
      case 'error':
        return 'text-red-500';
      default:
        return 'text-gray-500';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'connected':
        return 'Connected';
      case 'connecting':
        return 'Connecting';
      case 'error':
        return 'Error';
      default:
        return 'Disconnected';
    }
  };

  if (sessionList.length === 0) {
    return (
      <div className="flex items-center justify-between p-2 border-b border-border bg-card/40">
        <div className="flex items-center gap-2">
          <Icon name="terminal" className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium text-muted-foreground">No Terminal Sessions</span>
        </div>
        <Button size="sm" variant="outline" onClick={handleCreateSession} className="gap-2">
          <Icon name="plus" className="h-4 w-4" />
          New Terminal
        </Button>
      </div>
    );
  }

  return (
    <div className="border-b border-border bg-card/40">
      <div className="flex items-center justify-between p-2">
        <ScrollArea className="flex-1 mr-2">
          <div className="flex gap-1">
            {sessionList.map((session) => (
              <div
                key={session.id}
                className={cn(
                  'relative flex items-center gap-2 px-3 py-1.5 text-xs rounded-md cursor-pointer transition-colors',
                  'hover:bg-accent/50 min-w-0',
                  activeSessionId === session.id
                    ? 'bg-accent text-accent-foreground'
                    : 'bg-background/60 text-muted-foreground'
                )}
                onClick={() => setActiveSession(session.id)}
                title={session.title}
              >
                <Icon name="circle" className={cn('h-2 w-2 flex-shrink-0', getStatusColor(session.status))} />
                <span className="truncate max-w-24">{session.title}</span>
                {sessionList.length > 1 && (
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-auto p-0.5 ml-1 hover:bg-destructive hover:text-destructive-foreground"
                    onClick={(e) => handleRemoveSession(session.id, e)}
                    title="Close terminal"
                  >
                    <Icon name="x" className="h-3 w-3" />
                  </Button>
                )}
              </div>
            ))}
          </div>
        </ScrollArea>
        <Button size="sm" variant="outline" onClick={handleCreateSession} className="gap-2 flex-shrink-0">
          <Icon name="plus" className="h-4 w-4" />
          New
        </Button>
      </div>
      {/* Status bar */}
      <div className="flex items-center justify-between px-2 py-1 bg-background/20 text-xs text-muted-foreground border-t border-border/50">
        <div className="flex items-center gap-4">
          <span>Active: {sessionList.length} session{sessionList.length !== 1 ? 's' : ''}</span>
          {activeSessionId && (
            <Badge variant="outline" className="gap-1 text-xs">
              <Icon name="circle" className={cn('h-2 w-2', getStatusColor(sessions.get(activeSessionId || '')?.status || 'disconnected'))} />
              {getStatusText(sessions.get(activeSessionId || '')?.status || 'disconnected')}
            </Badge>
          )}
        </div>
        <span>{sessions.get(activeSessionId || '')?.cwd || '~'}</span>
      </div>
    </div>
  );
};