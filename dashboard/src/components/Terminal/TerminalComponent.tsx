import React, { useEffect, useRef, useCallback } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import { SearchAddon } from '@xterm/addon-search';
import { useTerminalStore } from '@/stores/terminalStore';
import { terminalWsManager, TerminalMessage } from '@/services/terminalWebSocket';
import { cn } from '@/lib/utils';

// Import XTerm CSS
import '@xterm/xterm/css/xterm.css';

interface TerminalComponentProps {
  sessionId: string;
  className?: string;
}

export const TerminalComponent: React.FC<TerminalComponentProps> = ({
  sessionId,
  className,
}) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const terminalInstance = useRef<Terminal | null>(null);
  const fitAddon = useRef<FitAddon | null>(null);
  const webLinksAddon = useRef<WebLinksAddon | null>(null);
  const searchAddon = useRef<SearchAddon | null>(null);
  const isInitialized = useRef(false);

  const { updateSession, getActiveSession } = useTerminalStore();
  const session = useTerminalStore((state) => state.sessions.get(sessionId));

  const initializeTerminal = useCallback(() => {
    if (!terminalRef.current || isInitialized.current || terminalInstance.current) {
      return;
    }

    // Create terminal instance
    const terminal = new Terminal({
      cursorBlink: true,
      cursorStyle: 'block',
      fontSize: 14,
      fontFamily: '"Fira Code", "Cascadia Code", "JetBrains Mono", "SF Mono", Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
      theme: {
        background: '#0f0f23',
        foreground: '#cccccc',
        cursor: '#cccccc',
        cursorAccent: '#000000',
        selectionBackground: '#316ac5',
        black: '#000000',
        red: '#cd3131',
        green: '#0dbc79',
        yellow: '#e5e510',
        blue: '#2472c8',
        magenta: '#bc3fbc',
        cyan: '#11a8cd',
        white: '#e5e5e5',
        brightBlack: '#666666',
        brightRed: '#f14c4c',
        brightGreen: '#23d18b',
        brightYellow: '#f5f543',
        brightBlue: '#3b8eea',
        brightMagenta: '#d670d6',
        brightCyan: '#29b8db',
        brightWhite: '#ffffff',
      },
      allowTransparency: false,
      allowProposedApi: true,
    });

    // Create and load addons
    fitAddon.current = new FitAddon();
    webLinksAddon.current = new WebLinksAddon();
    searchAddon.current = new SearchAddon();

    terminal.loadAddon(fitAddon.current);
    terminal.loadAddon(webLinksAddon.current);
    terminal.loadAddon(searchAddon.current);

    // Open terminal in DOM element
    terminal.open(terminalRef.current);

    // Store terminal instance
    terminalInstance.current = terminal;
    updateSession(sessionId, { terminal });

    // Fit terminal to container
    if (fitAddon.current) {
      fitAddon.current.fit();
    }

    // Handle terminal input
    terminal.onData((data) => {
      terminalWsManager.sendInput(sessionId, data);
    });

    // Handle terminal resize
    terminal.onResize(({ cols, rows }) => {
      terminalWsManager.resizeSession(sessionId, cols, rows);
    });

    // Connect to WebSocket
    const { cols, rows } = terminal;
    terminalWsManager.connectSession(sessionId, cols, rows, session?.cwd);

    isInitialized.current = true;

    // Show welcome message
    terminal.writeln('\x1b[1;34mCASPER Terminal\x1b[0m');
    terminal.writeln('Connecting to terminal server...\n');
  }, [sessionId, updateSession, session?.cwd]);

  const handleResize = useCallback(() => {
    if (fitAddon.current && terminalInstance.current) {
      fitAddon.current.fit();
    }
  }, []);

  // Initialize terminal on mount
  useEffect(() => {
    const timer = setTimeout(initializeTerminal, 100);
    return () => clearTimeout(timer);
  }, [initializeTerminal]);

  // Handle WebSocket messages
  useEffect(() => {
    const handleMessage = (message: TerminalMessage) => {
      if (message.sessionId !== sessionId || !terminalInstance.current) {
        return;
      }

      switch (message.type) {
        case 'output':
          if (message.payload) {
            terminalInstance.current.write(message.payload);
          }
          break;
        case 'connected':
          terminalInstance.current.clear();
          terminalInstance.current.writeln('\x1b[1;32mConnected to terminal server\x1b[0m\n');
          break;
        case 'error':
          terminalInstance.current.writeln(`\x1b[1;31mError: ${message.error || 'Unknown error'}\x1b[0m\n`);
          break;
      }
    };

    const unsubscribe = terminalWsManager.onMessage(handleMessage);
    return unsubscribe;
  }, [sessionId]);

  // Handle window resize
  useEffect(() => {
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [handleResize]);

  // Fit terminal when container size changes
  useEffect(() => {
    const resizeObserver = new ResizeObserver(() => {
      handleResize();
    });

    if (terminalRef.current) {
      resizeObserver.observe(terminalRef.current);
    }

    return () => resizeObserver.disconnect();
  }, [handleResize]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (terminalInstance.current) {
        terminalWsManager.disconnectSession(sessionId);
        terminalInstance.current.dispose();
        terminalInstance.current = null;
      }
      isInitialized.current = false;
    };
  }, [sessionId]);

  // Focus terminal when it becomes active
  useEffect(() => {
    const activeSession = getActiveSession();
    if (activeSession?.id === sessionId && terminalInstance.current) {
      terminalInstance.current.focus();
    }
  }, [sessionId, getActiveSession]);

  return (
    <div
      ref={terminalRef}
      className={cn(
        'w-full h-full bg-[#0f0f23] rounded-md overflow-hidden',
        'focus-within:ring-2 focus-within:ring-blue-500 focus-within:ring-opacity-50',
        className
      )}
      style={{ minHeight: '200px' }}
    />
  );
};