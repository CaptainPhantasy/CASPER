import { useEffect } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { useAgentStore } from './stores/agentStore';

export function WebSocketTestComponent() {
  const { agents, tasks, metrics, approvalQueue } = useAgentStore();

  const {
    connected,
    connecting,
    connectionStatus,
    lastEvent,
    eventHistory,
    send,
    reconnect,
    clearHistory
  } = useWebSocket({
    onMessage: (message) => {
      console.log('[WebSocket Test] Received message:', message);
    },
    onConnectionChange: (status) => {
      console.log('[WebSocket Test] Connection status changed:', status);
    }
  });

  useEffect(() => {
    console.log('[WebSocket Test] Component mounted');
    console.log('Connection status:', connectionStatus);
    console.log('Connected:', connected);
    console.log('Connecting:', connecting);

    // Log store state
    console.log('Agents:', Array.from(agents.values()));
    console.log('Tasks:', Array.from(tasks.values()));
    console.log('Metrics:', metrics);
    console.log('Approval Queue:', approvalQueue);
  }, [connectionStatus, connected, connecting, agents, tasks, metrics, approvalQueue]);

  useEffect(() => {
    if (lastEvent) {
      console.log('[WebSocket Test] Last event:', lastEvent);
    }
  }, [lastEvent]);

  // Test functions
  const testSendMessage = () => {
    send({
      type: 'test',
      message: 'Test message from dashboard',
      timestamp: new Date().toISOString()
    });
  };

  const testSubmitTask = async () => {
    const { submitTask } = useAgentStore.getState();
    await submitTask('Test task: Build a simple counter component', 'medium');
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace' }}>
      <h2>WebSocket Integration Test</h2>

      <div>
        <h3>Connection Status</h3>
        <p>Status: {connectionStatus}</p>
        <p>Connected: {connected ? 'Yes' : 'No'}</p>
        <p>Connecting: {connecting ? 'Yes' : 'No'}</p>
        <button onClick={reconnect}>Reconnect</button>
      </div>

      <div style={{ marginTop: '20px' }}>
        <h3>Store State</h3>
        <p>Active Agents: {agents.size}</p>
        <p>Active Tasks: {tasks.size}</p>
        <p>Total Tokens: {metrics.totalTokens}</p>
        <p>Cost: ${metrics.costUSD?.toFixed(2) ?? '0.00'}</p>
        <p>Pending Approvals: {approvalQueue.length}</p>
      </div>

      <div style={{ marginTop: '20px' }}>
        <h3>Event History</h3>
        <p>Events received: {eventHistory.length}</p>
        {lastEvent && (
          <div>
            <p>Last event type: {lastEvent.type}</p>
            <p>Last event time: {lastEvent.timestamp || 'N/A'}</p>
          </div>
        )}
        <button onClick={clearHistory}>Clear History</button>
      </div>

      <div style={{ marginTop: '20px' }}>
        <h3>Test Actions</h3>
        <button onClick={testSendMessage}>Send Test Message</button>
        {' '}
        <button onClick={testSubmitTask}>Submit Test Task</button>
      </div>

      <div style={{ marginTop: '20px' }}>
        <h3>Raw Event Log (last 5)</h3>
        <pre style={{ background: '#f0f0f0', padding: '10px', fontSize: '12px' }}>
          {JSON.stringify(eventHistory.slice(-5), null, 2)}
        </pre>
      </div>
    </div>
  );
}

// Example usage in your App or another component:
// import { WebSocketTestComponent } from './test-websocket';
// Add <WebSocketTestComponent /> to your component tree