import { useCallback, useEffect, useRef, useState } from 'react';
import { wsManager, ConnectionStatus } from '../services/websocket';
import { WSAgentUpdate } from '../types';

export interface UseWebSocketOptions {
  url?: string;
  onMessage?: (message: WSAgentUpdate) => void;
  onConnectionChange?: (status: ConnectionStatus) => void;
  autoConnect?: boolean;
  reconnectOnMount?: boolean;
}

export interface UseWebSocketReturn {
  connected: boolean;
  connecting: boolean;
  connectionStatus: ConnectionStatus;
  lastEvent: WSAgentUpdate | null;
  eventHistory: WSAgentUpdate[];
  send: (data: any) => void;
  connect: () => void;
  disconnect: () => void;
  reconnect: () => void;
  clearHistory: () => void;
}

export function useWebSocket({
  url = 'ws://localhost:8000/ws',
  onMessage,
  onConnectionChange,
  autoConnect = true,
}: UseWebSocketOptions = {}): UseWebSocketReturn {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [lastEvent, setLastEvent] = useState<WSAgentUpdate | null>(null);
  const [eventHistory, setEventHistory] = useState<WSAgentUpdate[]>([]);
  const maxHistorySize = 100; // Keep last 100 events

  // Refs to avoid recreating callbacks
  const onMessageRef = useRef(onMessage);
  const onConnectionChangeRef = useRef(onConnectionChange);

  // Update refs when props change
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    onConnectionChangeRef.current = onConnectionChange;
  }, [onConnectionChange]);

  // Message handler
  useEffect(() => {
    const unsubscribe = wsManager.on((msg) => {
      setLastEvent(msg);
      setEventHistory((prev) => {
        const newHistory = [...prev, msg];
        // Keep only the last N events
        if (newHistory.length > maxHistorySize) {
          return newHistory.slice(-maxHistorySize);
        }
        return newHistory;
      });

      // Call user's onMessage callback if provided
      if (onMessageRef.current) {
        onMessageRef.current(msg);
      }
    });

    return () => unsubscribe();
  }, []);

  // Connection status handler
  useEffect(() => {
    const unsubscribe = wsManager.onConnectionChange((status) => {
      setConnectionStatus(status);

      // Call user's onConnectionChange callback if provided
      if (onConnectionChangeRef.current) {
        onConnectionChangeRef.current(status);
      }
    });

    return () => unsubscribe();
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      wsManager.connect(url);
    }

    return () => {
      // Don't disconnect on unmount to keep connection alive for other components
      // User can explicitly disconnect if needed
    };
  }, [url, autoConnect]);

  // Exposed methods
  const send = useCallback((data: any) => {
    wsManager.send(data);
  }, []);

  const connect = useCallback(() => {
    wsManager.connect(url);
  }, [url]);

  const disconnect = useCallback(() => {
    wsManager.disconnect();
  }, []);

  const reconnect = useCallback(() => {
    wsManager.reconnect();
  }, []);

  const clearHistory = useCallback(() => {
    setEventHistory([]);
  }, []);

  return {
    connected: connectionStatus === 'connected',
    connecting: connectionStatus === 'connecting',
    connectionStatus,
    lastEvent,
    eventHistory,
    send,
    connect,
    disconnect,
    reconnect,
    clearHistory,
  };
}
