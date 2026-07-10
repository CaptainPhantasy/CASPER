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

    // Close existing connection if it exists
    if (this.ws && this.ws.readyState !== WebSocket.CLOSED) {
      this.ws.close();
    }

    this.emitConnectionStatus('connecting');

    try {
      // Validate URL before attempting connection
      try {
        new URL(this.url);
      } catch (urlError) {
        console.error('[WebSocket] Invalid WebSocket URL:', this.url);
        this.emitConnectionStatus('error');
        return;
      }

      this.ws = new WebSocket(this.url);

      // Set a timeout for the initial connection
      const connectionTimeout = setTimeout(() => {
        if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
          console.warn('[WebSocket] Connection timeout, closing connection');
          this.ws.close();
        }
      }, 10000); // 10 second timeout

      this.ws.onopen = (event) => {
        clearTimeout(connectionTimeout);
        console.log('[WebSocket] Connected to', this.url);
        this.reconnectAttempts = 0;
        const wasReconnecting = this.isReconnecting;
        this.isReconnecting = false;
        this.emitConnectionStatus('connected');

        // Show success toast if this was a reconnection
        if (wasReconnecting) {
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

        // Send initial handshake
        this.send({
          type: 'handshake',
          client: 'dashboard',
          version: '1.0.0',
          timestamp: Date.now(),
        });
      };

      this.ws.onmessage = (event) => {
        try {
          clearTimeout(connectionTimeout);

          // Validate message data
          if (!event.data || typeof event.data !== 'string') {
            console.warn('[WebSocket] Invalid message data received');
            return;
          }

          const data = JSON.parse(event.data) as WSAgentUpdate;

          // Validate message structure
          if (!data.type) {
            console.warn('[WebSocket] Message missing type field');
            return;
          }

          this.handleMessage(data);
        } catch (e) {
          console.warn('[WebSocket] Message parse error', e, 'Raw data:', event.data);
        }
      };

      this.ws.onclose = (event) => {
        clearTimeout(connectionTimeout);
        const { code, reason, wasClean } = event;
        console.log(`[WebSocket] Connection closed - Code: ${code}, Reason: ${reason}, Clean: ${wasClean}`);
        this.stopPingInterval();
        this.emitConnectionStatus('disconnected');

        if (!this.isManuallyDisconnected) {
          // Determine if we should attempt to reconnect based on close code
          const shouldReconnect = this.shouldAttemptReconnect(code);

          if (shouldReconnect) {
            // Show toast only on unexpected disconnection
            if (this.connectionStatus === 'connected' || this.connectionStatus === 'connecting') {
              toast({
                title: 'Connection Lost',
                description: 'Attempting to reconnect to CASPER backend...',
                variant: 'destructive',
              });
            }
            this.scheduleReconnect();
          } else {
            console.log('[WebSocket] Not attempting reconnect due to close code:', code);
            this.emitConnectionStatus('error');
          }
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
      if (!this.isManuallyDisconnected) {
        this.scheduleReconnect();
      }
      return;
    }
  }

  private shouldAttemptReconnect(closeCode: number): boolean {
    // Don't reconnect for these close codes
    const noReconnectCodes = [
      1000, // Normal closure
      1001, // Going away
      1005, // No status received
      1006, // Abnormal closure (will reconnect)
      4000, // Custom: Server shutdown
      4001, // Custom: Server maintenance
    ];

    // Always reconnect for abnormal closure (1006)
    if (closeCode === 1006) {
      return true;
    }

    return !noReconnectCodes.includes(closeCode);
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

    // Handle heartbeat messages
    if (message.type === 'heartbeat') {
      return; // Don't forward heartbeat messages
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
      case 'agent_completed':
        if (message.agent_id) {
          toast({
            title: 'Agent Completed',
            description: `Agent ${message.agent_id} has finished its task`,
            variant: 'default',
          });
        }
        break;
      case 'command_started':
        if (message.data?.command) {
          console.log(`[WebSocket] Command started: ${message.data.command}`);
        }
        break;
      case 'command_completed':
        if (message.data?.command) {
          const success = message.data.success !== false;
          toast({
            title: success ? 'Command Completed' : 'Command Failed',
            description: `${message.data.command}: ${message.message || (success ? 'Success' : 'Failed')}`,
            variant: success ? 'default' : 'destructive',
          });
        }
        break;
      case 'approval_resolved':
        if (message.data?.approval_id) {
          const action = message.data.action || 'resolved';
          toast({
            title: 'Approval Updated',
            description: `Approval ${message.data.approval_id} was ${action}`,
            variant: action === 'approved' ? 'default' : 'destructive',
          });
        }
        break;
      case 'terminal_output':
        // Terminal output is handled by terminal components, just log
        console.log(`[WebSocket] Terminal output received`);
        break;
      case 'file_changed':
        if (message.data?.file_path) {
          console.log(`[WebSocket] File changed: ${message.data.file_path}`);
        }
        break;
      case 'test_result':
        if (message.data?.test_type) {
          const passed = message.data.success !== false;
          toast({
            title: `${message.data.test_type} Tests ${passed ? 'Passed' : 'Failed'}`,
            description: message.message || `${message.data.test_type} test execution completed`,
            variant: passed ? 'default' : 'destructive',
          });
        }
        break;
      case 'build_result':
        if (message.data?.build_target) {
          const success = message.data.success !== false;
          toast({
            title: `Build ${success ? 'Successful' : 'Failed'}`,
            description: `${message.data.build_target}: ${message.message || (success ? 'Build completed' : 'Build failed')}`,
            variant: success ? 'default' : 'destructive',
          });
        }
        break;
      case 'deployment_result':
        if (message.data?.environment) {
          const success = message.data.success !== false;
          toast({
            title: `Deployment ${success ? 'Successful' : 'Failed'}`,
            description: `${message.data.environment}: ${message.message || (success ? 'Deployed successfully' : 'Deployment failed')}`,
            variant: success ? 'default' : 'destructive',
          });
        }
        break;
      case 'ai_suggestion':
        if (message.data?.suggestion) {
          toast({
            title: 'AI Suggestion',
            description: message.data.suggestion.substring(0, 100) + (message.data.suggestion.length > 100 ? '...' : ''),
            variant: 'default',
          });
        }
        break;
      case 'business_document_ready':
        if (message.data?.document_type) {
          toast({
            title: 'Document Ready',
            description: `${message.data.document_type} has been generated and is ready for review`,
            variant: 'default',
          });
        }
        break;
      case 'error':
        toast({
          title: 'Agent Error',
          description: message.message || 'An error occurred in the agent system',
          variant: 'destructive',
        });
        break;
      case 'warning':
        toast({
          title: 'Warning',
          description: message.message || 'A warning was issued by the agent system',
          variant: 'destructive',
        });
        break;
      case 'task_submitted':
        toast({
          title: 'Task Submitted',
          description: message.description || 'New task has been queued',
        });
        break;
      case 'task_progress':
        // Progress updates are frequent, only show for major milestones
        if (message.data?.progress && message.data.progress % 25 === 0) {
          console.log(`[WebSocket] Task progress: ${message.data.progress}%`);
        }
        break;
      case 'system_status':
        // System status updates are handled by store, just log
        console.log(`[WebSocket] System status updated`);
        break;
      default:
        // Log unhandled message types for debugging
        console.log(`[WebSocket] Unhandled message type: ${message.type}`, message);
        break;
    }
  }
}

export const wsManager = new WebSocketManager();
