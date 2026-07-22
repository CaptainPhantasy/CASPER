import React, { useEffect, useRef, useCallback, useState } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import { SearchAddon } from '@xterm/addon-search';
import { useTerminalStore } from '@/stores/terminalStore';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Icon } from '../icons/IconMapping';
import { useToast } from '@/hooks/use-toast';

// Import XTerm CSS
import '@xterm/xterm/css/xterm.css';

interface OmegaTerminalProps {
  sessionId: string;
  className?: string;
}

interface OmegaMessage {
  type: 'command' | 'response' | 'error' | 'security' | 'fast_path' | 'approval';
  content: string;
  metadata?: {
    blocked?: boolean;
    sanitized?: boolean;
    fast_path?: boolean;
    response_time?: number;
    requires_approval?: boolean;
    approval_id?: string;
    risk_level?: 'low' | 'medium' | 'high' | 'critical';
  };
}

export const OmegaTerminal: React.FC<OmegaTerminalProps> = ({
  sessionId,
  className,
}) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const terminalInstance = useRef<Terminal | null>(null);
  const fitAddon = useRef<FitAddon | null>(null);
  const webLinksAddon = useRef<WebLinksAddon | null>(null);
  const searchAddon = useRef<SearchAddon | null>(null);
  const isInitialized = useRef(false);
  const commandBuffer = useRef<string>('');
  const wsRef = useRef<WebSocket | null>(null);

  const [isConnected, setIsConnected] = useState(false);
  const [securityStatus] = useState<'active' | 'inactive'>('active');
  const [fastPathEnabled] = useState(true);
  const { toast } = useToast();

  const { updateSession } = useTerminalStore();

  const connectToOmega = useCallback(() => {
    // Connect to Omega layer WebSocket endpoint
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.hostname}:8742/ws/omega`;

    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      setIsConnected(true);
      if (terminalInstance.current) {
        terminalInstance.current.writeln('\r\n🛡️ Connected to OMEGA PRIME - Layer 0 Security Active');
        terminalInstance.current.writeln('⚡ Fast Path enabled for /commands (< 50ms response)');
        terminalInstance.current.writeln('✅ All commands routed through security layer\r\n');
        terminalInstance.current.write('omega> ');
      }
    };

    wsRef.current.onmessage = (event) => {
      try {
        const message: OmegaMessage = JSON.parse(event.data);
        handleOmegaMessage(message);
      } catch (e) {
        // Handle plain text messages
        if (terminalInstance.current) {
          terminalInstance.current.write(event.data);
        }
      }
    };

    wsRef.current.onclose = () => {
      setIsConnected(false);
      if (terminalInstance.current) {
        terminalInstance.current.writeln('\r\n⚠️ Disconnected from Omega layer');
      }
      // Attempt reconnection after 2 seconds
      setTimeout(connectToOmega, 2000);
    };

    wsRef.current.onerror = (error) => {
      console.error('Omega WebSocket error:', error);
      if (terminalInstance.current) {
        terminalInstance.current.writeln('\r\n❌ Connection error to Omega layer');
      }
    };
  }, []);

  const handleOmegaMessage = (message: OmegaMessage) => {
    if (!terminalInstance.current) return;

    const terminal = terminalInstance.current;

    switch (message.type) {
      case 'response':
        // Clear the current line and write response
        terminal.write('\r\n');

        // Show response time for fast path commands
        if (message.metadata?.fast_path && message.metadata?.response_time) {
          terminal.writeln(`⚡ Fast Path: ${message.metadata.response_time}ms`);
        }

        // Write the actual response
        terminal.writeln(message.content);
        terminal.write('\r\nomega> ');
        break;

      case 'security':
        terminal.write('\r\n');
        if (message.metadata?.blocked) {
          terminal.writeln('🚫 BLOCKED: Direct tool access denied');
          terminal.writeln('   ' + message.content);
        } else if (message.metadata?.sanitized) {
          terminal.writeln('⚠️ SANITIZED: Input modified for safety');
          terminal.writeln('   ' + message.content);
        }
        terminal.write('\r\nomega> ');
        break;

      case 'approval':
        {
        terminal.write('\r\n');
        const riskColor = {
          low: '\x1b[32m',      // Green
          medium: '\x1b[33m',   // Yellow
          high: '\x1b[31m',     // Red
          critical: '\x1b[35m', // Magenta
        }[message.metadata?.risk_level || 'medium'];

        terminal.writeln(`${riskColor}⚡ APPROVAL REQUIRED [${message.metadata?.risk_level?.toUpperCase()}]\x1b[0m`);
        terminal.writeln(message.content);
        terminal.writeln('Type "y" to approve, "n" to reject, or "i" for more info');
        terminal.write('approval> ');
        break;
        }

      case 'error':
        terminal.write('\r\n');
        terminal.writeln('❌ ' + message.content);
        terminal.write('\r\nomega> ');
        break;

      case 'fast_path':
        // Show fast path indicator
        if (message.metadata?.response_time) {
          terminal.write(`\r\n⚡ <${message.metadata.response_time}ms> `);
        }
        break;
    }
  };

  const sendToOmega = useCallback((command: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      if (terminalInstance.current) {
        terminalInstance.current.writeln('\r\n⚠️ Not connected to Omega layer');
        terminalInstance.current.write('omega> ');
      }
      return;
    }

    // Check if it's a fast path command
    const isFastPath = command.startsWith('/');

    const message: OmegaMessage = {
      type: 'command',
      content: command,
      metadata: {
        fast_path: isFastPath && fastPathEnabled,
      }
    };

    wsRef.current.send(JSON.stringify(message));

    // Show fast path indicator
    if (isFastPath && fastPathEnabled && terminalInstance.current) {
      terminalInstance.current.write(' ⚡');
    }
  }, [fastPathEnabled]);

  const initializeTerminal = useCallback(() => {
    if (!terminalRef.current || isInitialized.current || terminalInstance.current) {
      return;
    }

    // Create terminal instance with Omega theme
    const terminal = new Terminal({
      cursorBlink: true,
      cursorStyle: 'block',
      fontSize: 14,
      fontFamily: '"Fira Code", "Cascadia Code", "JetBrains Mono", monospace',
      theme: {
        background: '#0a0a0f',  // Darker for Omega layer
        foreground: '#e0e0e0',
        cursor: '#00ff00',      // Green cursor for security
        cursorAccent: '#000000',
        selectionBackground: '#316ac5',
        black: '#000000',
        red: '#ff3333',         // Brighter red for warnings
        green: '#00ff00',       // Bright green for success
        yellow: '#ffff00',      // Bright yellow for caution
        blue: '#4444ff',
        magenta: '#ff00ff',
        cyan: '#00ffff',
        white: '#ffffff',
        brightBlack: '#666666',
        brightRed: '#ff6666',
        brightGreen: '#66ff66',
        brightYellow: '#ffff66',
        brightBlue: '#6666ff',
        brightMagenta: '#ff66ff',
        brightCyan: '#66ffff',
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

    // Welcome message
    terminal.writeln('╔══════════════════════════════════════════════════════════╗');
    terminal.writeln('║           OMEGA PRIME TERMINAL - LAYER 0                 ║');
    terminal.writeln('║                                                          ║');
    terminal.writeln('║  🛡️  Security: ACTIVE    ⚡ Fast Path: ENABLED           ║');
    terminal.writeln('║  All commands routed through Omega security layer       ║');
    terminal.writeln('╚══════════════════════════════════════════════════════════╝');
    terminal.writeln('');
    terminal.writeln('Type /help for fast commands or use natural language');
    terminal.writeln('');

    // Handle terminal input
    terminal.onData((data) => {
      // Handle special characters
      if (data === '\r' || data === '\n') {
        // Enter pressed - send command
        if (commandBuffer.current.trim()) {
          sendToOmega(commandBuffer.current.trim());
          commandBuffer.current = '';
        } else {
          terminal.write('\r\nomega> ');
        }
      } else if (data === '\x7f') {
        // Backspace
        if (commandBuffer.current.length > 0) {
          commandBuffer.current = commandBuffer.current.slice(0, -1);
          terminal.write('\b \b');
        }
      } else if (data === '\x03') {
        // Ctrl+C - clear current input
        commandBuffer.current = '';
        terminal.write('^C\r\nomega> ');
      } else if (data >= ' ') {
        // Regular character
        commandBuffer.current += data;
        terminal.write(data);
      }
    });

    // Handle terminal resize
    terminal.onResize(() => {
      // Send resize event to Omega if needed
    });

    // Connect to Omega layer
    connectToOmega();

    isInitialized.current = true;
  }, [sessionId, updateSession, sendToOmega, connectToOmega]);

  useEffect(() => {
    initializeTerminal();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (terminalInstance.current) {
        terminalInstance.current.dispose();
      }
    };
  }, [initializeTerminal]);

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      if (fitAddon.current) {
        fitAddon.current.fit();
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div className={cn('flex h-full flex-col', className)}>
      {/* Status bar */}
      <div className="flex items-center justify-between border-b bg-card/60 px-4 py-2">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Icon name="shield" className={cn(
              "h-4 w-4",
              securityStatus === 'active' ? "text-green-500" : "text-red-500"
            )} />
            <span className="text-sm font-medium">Omega Security</span>
            <Badge variant={securityStatus === 'active' ? "default" : "destructive"}>
              {securityStatus === 'active' ? "Active" : "Inactive"}
            </Badge>
          </div>

          <div className="mx-2 h-4 w-px bg-border" />

          <div className="flex items-center gap-2">
            <Icon name="bolt" className={cn(
              "h-4 w-4",
              fastPathEnabled ? "text-yellow-500" : "text-muted-foreground"
            )} />
            <span className="text-sm">Fast Path</span>
            <Badge variant={fastPathEnabled ? "secondary" : "outline"}>
              {fastPathEnabled ? "Enabled" : "Disabled"}
            </Badge>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isConnected ? (
            <div className="flex items-center gap-1 text-green-500">
              <Icon name="circle-check" className="h-3 w-3" />
              <span className="text-xs">Connected</span>
            </div>
          ) : (
            <div className="flex items-center gap-1 text-yellow-500">
              <Icon name="alert-circle" className="h-3 w-3" />
              <span className="text-xs">Connecting...</span>
            </div>
          )}

          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              if (terminalInstance.current) {
                terminalInstance.current.clear();
                terminalInstance.current.write('omega> ');
              }
            }}
          >
            Clear
          </Button>

          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              toast({
                title: "Omega Terminal",
                description: (
                  <div className="space-y-2">
                    <p>All commands are routed through the Omega security layer.</p>
                    <p>Use /commands for fast path (&lt;50ms response).</p>
                    <p>Natural language commands go through full interpretation.</p>
                  </div>
                ),
              });
            }}
          >
            <Icon name="info-circle" className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Terminal */}
      <div ref={terminalRef} className="flex-1 bg-[#0a0a0f]" />

      {/* Command hints */}
      <div className="flex items-center gap-4 border-t bg-card/60 px-4 py-1 text-xs text-muted-foreground">
        <span>Ctrl+C: Cancel</span>
        <span>Ctrl+F: Search</span>
        <span>/help: Fast commands</span>
        <span>Natural language: Full AI interpretation</span>
      </div>
    </div>
  );
};

export default OmegaTerminal;
