import { useAgentStore } from '../stores/agentStore';
import { WSAgentUpdate } from '../types';
import { toast } from '@/hooks/use-toast';

type Listener = (msg: WSAgentUpdate) => void;
type ConnectionListener = (status: 'connected' | 'disconnected' | 'connecting' | 'error') => void;

export type ConnectionStatus = 'connected' | 'disconnected' | 'connecting' | 'error';

class WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectDelay = 15_000;
  private maxReconnectAttempts = 10;
  private listeners: Set<Listener> = new Set();
  private connectionListeners: Set<ConnectionListener> = new Set();
  private url: string;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private isManuallyDisconnected = false;
  private connectionStatus: ConnectionStatus = 'disconnected';
  private pingInterval: ReturnType<typeof setInterval> | null = null;
  private messageQueue: any[] = [];
  private isReconnecting = false;

  constructor(url = (location.origin.replace('http', 'ws') + '/ws')) {
    this.url = url;
  }

  on(listener: Listener) {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  onConnectionChange(listener: ConnectionListener) {
    this.connectionListeners.add(listener);
    // Immediately notify of current status
    listener(this.connectionStatus);
    return () => {
      this.connectionListeners.delete(listener);
    };
  }

  private emit(msg: WSAgentUpdate) {
    for (const l of this.listeners) l(msg);
  }

  private emitConnectionStatus(status: ConnectionStatus) {
    this.connectionStatus = status;
    for (const l of this.connectionListeners) l(status);
  }

  connect(url?: string) {
    if (url) this.url = url;

    // Don't reconnect if manually disconnected
    if (this.isManuallyDisconnected) {
      return;
    }

    // Clear any existing reconnect timeout
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    this.emitConnectionStatus('connecting');

    try {
      this.ws = new WebSocket(this.url);
      
      // Set a timeout for the initial connection
      const connectionTimeout = setTimeout(() => {
        if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
          console.warn('[WebSocket] Connection timeout, closing connection');
          this.ws.close();
        }
      }, 5000); // 5 second timeout

      this.ws.onopen = () => {
        clearTimeout(connectionTimeout);
        console.log('[WebSocket] Connected to', this.url);
        this.reconnectAttempts = 0;
        this.isReconnecting = false;
        this.emitConnectionStatus('connected');

        // Show success toast if this was a reconnection
        if (this.reconnectAttempts > 0 || this.isReconnecting) {
          toast({
            title: 'Connection Restored',
            description: 'Successfully reconnected to CASPER backend',
            variant: 'default',
          });
        }

        // Start ping interval
        this.startPingInterval();

        // Process any queued messages
        this.processMessageQueue();
      };

      this.ws.onmessage = (event) => {
        try {
          clearTimeout(connectionTimeout);
          const data = JSON.parse(event.data) as WSAgentUpdate;
          this.handleMessage(data);
        } catch (e) {
          console.warn('[WebSocket] Message parse error', e);
        }
      };

      this.ws.onclose = (event) => {
        clearTimeout(connectionTimeout);
        console.log('[WebSocket] Connection closed', event.code, event.reason);
        this.stopPingInterval();
        this.emitConnectionStatus('disconnected');

        if (!this.isManuallyDisconnected) {
          // Show toast only on unexpected disconnection
          if (this.connectionStatus === 'connected') {
            toast({
              title: 'Connection Lost',
              description: 'Attempting to reconnect to CASPER backend...',
              variant: 'destructive',
            });
          }
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        clearTimeout(connectionTimeout);
        console.error('[WebSocket] Connection error', error);
        this.emitConnectionStatus('error');
        // onclose will be triggered automatically after error
      };
    } catch (e) {
      console.error('WebSocket initialization failed', e);
      this.emitConnectionStatus('error');
      this.scheduleReconnect();
      return;
    }
  }

  readyState() {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }

  getConnectionStatus(): ConnectionStatus {
    return this.connectionStatus;
  }

  send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify(data));
      } catch (e) {
        console.error('[WebSocket] Send error', e);
        this.messageQueue.push(data);
      }
    } else {
      // Queue message for later sending
      this.messageQueue.push(data);
      console.log('[WebSocket] Message queued (not connected):', data);
    }
  }

  disconnect() {
    this.isManuallyDisconnected = true;
    this.stopPingInterval();

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.emitConnectionStatus('disconnected');
  }

  reconnect() {
    this.isManuallyDisconnected = false;
    this.connect();
  }

  private scheduleReconnect() {
    if (this.isManuallyDisconnected) {
      return;
    }

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WebSocket] Max reconnection attempts reached');
      toast({
        title: 'Connection Failed',
        description: 'Unable to connect to CASPER backend. Please check your connection.',
        variant: 'destructive',
      });
      this.emitConnectionStatus('error');
      return;
    }

    this.isReconnecting = true;
    this.reconnectAttempts += 1;
    const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts - 1), this.maxReconnectDelay);

    console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private startPingInterval() {
    this.stopPingInterval();

    // Send ping every 30 seconds
    this.pingInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        try {
          this.ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
        } catch (e) {
          console.error('[WebSocket] Ping failed', e);
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
      console.log(`[WebSocket] Processing ${this.messageQueue.length} queued messages`);
      const queue = [...this.messageQueue];
      this.messageQueue = [];

      for (const msg of queue) {
        this.send(msg);
      }
    }
  }

  private handleMessage(message: WSAgentUpdate) {
    // Handle pong messages
    if (message.type === 'connection' && message.message === 'pong') {
      return; // Don't forward pong messages
    }

    // Forward to listeners and store
    this.emit(message);

    // Update store based on message type
    const store = useAgentStore.getState();

    // Handle approval requests specially
    if (message.type === 'approval_request' && message.data?.approval) {
      store.addApproval(message.data.approval);

      // Show toast for high-risk approvals
      if (message.data.approval.riskLevel === 'high') {
        toast({
          title: 'High-Risk Action Pending',
          description: `Agent ${message.agent_id} requires approval: ${message.data.approval.description}`,
          variant: 'destructive',
        });
      }
    } else {
      store.applyWS(message);
    }

    // Show toast for important events
    switch (message.type) {
      case 'agent_spawned':
        if (message.agent_id) {
          console.log(`[WebSocket] Agent spawned: ${message.agent_id}`);
        }
        break;
      case 'error':
        toast({
          title: 'Agent Error',
          description: message.message || 'An error occurred in the agent system',
          variant: 'destructive',
        });
        break;
      case 'task_submitted':
        toast({
          title: 'Task Submitted',
          description: message.description || 'New task has been queued',
        });
        break;
    }
  }
}

export const wsManager = new WebSocketManager();
