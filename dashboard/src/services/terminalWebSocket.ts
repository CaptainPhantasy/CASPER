import { useTerminalStore } from '../stores/terminalStore';
import { toast } from '@/hooks/use-toast';

export interface TerminalMessage {
  type: 'connect' | 'disconnect' | 'input' | 'output' | 'resize' | 'error' | 'connected' | 'pong';
  sessionId: string;
  data?: any;
  payload?: string;
  cols?: number;
  rows?: number;
  error?: string;
}

type TerminalMessageListener = (message: TerminalMessage) => void;

class TerminalWebSocketManager {
  private ws: WebSocket | null = null;
  private url: string;
  private listeners: Set<TerminalMessageListener> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private isManuallyDisconnected = false;
  private pingInterval: ReturnType<typeof setInterval> | null = null;
  private messageQueue: TerminalMessage[] = [];
  private activeSessions = new Set<string>();

  constructor() {
    // Use dedicated terminal WebSocket endpoint on backend port 8742
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    this.url = `${protocol}//${location.hostname}:8742/ws/terminal`;
  }

  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return;
    }

    if (this.isManuallyDisconnected) {
      return;
    }

    // Clear any existing reconnect timeout
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    try {
      this.ws = new WebSocket(this.url);

      const connectionTimeout = setTimeout(() => {
        if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
          console.warn('[TerminalWS] Connection timeout');
          this.ws.close();
        }
      }, 5000);

      this.ws.onopen = () => {
        clearTimeout(connectionTimeout);
        console.log('[TerminalWS] Connected to', this.url);
        this.reconnectAttempts = 0;
        this.isManuallyDisconnected = false;
        this.startPingInterval();
        this.processMessageQueue();

        if (this.reconnectAttempts > 0) {
          toast({
            title: 'Terminal Connected',
            description: 'Terminal WebSocket connection restored',
          });
        }
      };

      this.ws.onmessage = (event) => {
        try {
          clearTimeout(connectionTimeout);
          const message = JSON.parse(event.data) as TerminalMessage;
          this.handleMessage(message);
        } catch (e) {
          console.warn('[TerminalWS] Message parse error', e);
        }
      };

      this.ws.onclose = (event) => {
        clearTimeout(connectionTimeout);
        console.log('[TerminalWS] Connection closed', event.code, event.reason);
        this.stopPingInterval();

        // Update all active sessions to disconnected status
        const store = useTerminalStore.getState();
        this.activeSessions.forEach(sessionId => {
          store.updateSession(sessionId, { status: 'disconnected', wsId: null });
        });

        if (!this.isManuallyDisconnected) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        clearTimeout(connectionTimeout);
        console.error('[TerminalWS] Connection error', error);

        // Update all active sessions to error status
        const store = useTerminalStore.getState();
        this.activeSessions.forEach(sessionId => {
          store.updateSession(sessionId, { status: 'error', wsId: null });
        });
      };

    } catch (e) {
      console.error('[TerminalWS] Initialization failed', e);
      this.scheduleReconnect();
    }
  }

  disconnect() {
    this.isManuallyDisconnected = true;
    this.stopPingInterval();

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    // Send disconnect messages for all active sessions
    this.activeSessions.forEach(sessionId => {
      this.send({
        type: 'disconnect',
        sessionId,
      });
    });

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.activeSessions.clear();
  }

  send(message: TerminalMessage) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify(message));
      } catch (e) {
        console.error('[TerminalWS] Send error', e);
        this.messageQueue.push(message);
      }
    } else {
      this.messageQueue.push(message);
      console.log('[TerminalWS] Message queued:', message.type, message.sessionId);
    }
  }

  connectSession(sessionId: string, cols: number = 80, rows: number = 24, cwd?: string) {
    this.activeSessions.add(sessionId);

    const store = useTerminalStore.getState();
    store.updateSession(sessionId, { status: 'connecting' });

    this.send({
      type: 'connect',
      sessionId,
      cols,
      rows,
      data: { cwd },
    });
  }

  disconnectSession(sessionId: string) {
    this.activeSessions.delete(sessionId);

    this.send({
      type: 'disconnect',
      sessionId,
    });

    const store = useTerminalStore.getState();
    store.updateSession(sessionId, { status: 'disconnected', wsId: null });
  }

  sendInput(sessionId: string, data: string) {
    this.send({
      type: 'input',
      sessionId,
      payload: data,
    });
  }

  resizeSession(sessionId: string, cols: number, rows: number) {
    this.send({
      type: 'resize',
      sessionId,
      cols,
      rows,
    });
  }

  onMessage(listener: TerminalMessageListener) {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  private emit(message: TerminalMessage) {
    for (const listener of this.listeners) {
      listener(message);
    }
  }

  private handleMessage(message: TerminalMessage) {
    // Handle pong messages
    if (message.type === 'pong') {
      return;
    }

    // Update session status based on message type
    const store = useTerminalStore.getState();

    switch (message.type) {
      case 'connected':
        store.updateSession(message.sessionId, {
          status: 'connected',
          wsId: message.data?.wsId || null
        });
        break;
      case 'error':
        store.updateSession(message.sessionId, { status: 'error' });
        toast({
          title: 'Terminal Error',
          description: message.error || 'An error occurred in the terminal session',
          variant: 'destructive',
        });
        break;
    }

    // Emit to listeners (terminal components)
    this.emit(message);
  }

  private scheduleReconnect() {
    if (this.isManuallyDisconnected) {
      return;
    }

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[TerminalWS] Max reconnection attempts reached');
      toast({
        title: 'Terminal Connection Failed',
        description: 'Unable to connect to terminal server. Please check your connection.',
        variant: 'destructive',
      });
      return;
    }

    this.reconnectAttempts += 1;
    const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts - 1), 10000);

    console.log(`[TerminalWS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private startPingInterval() {
    this.stopPingInterval();

    this.pingInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        try {
          this.ws.send(JSON.stringify({ type: 'ping', sessionId: 'ping', timestamp: Date.now() }));
        } catch (e) {
          console.error('[TerminalWS] Ping failed', e);
        }
      }
    }, 30000);
  }

  private stopPingInterval() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private processMessageQueue() {
    if (this.messageQueue.length > 0 && this.ws?.readyState === WebSocket.OPEN) {
      console.log(`[TerminalWS] Processing ${this.messageQueue.length} queued messages`);
      const queue = [...this.messageQueue];
      this.messageQueue = [];

      for (const msg of queue) {
        this.send(msg);
      }
    }
  }
}

export const terminalWsManager = new TerminalWebSocketManager();