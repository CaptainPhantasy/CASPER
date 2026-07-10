import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Icon } from './icons/IconMapping';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { ScrollArea } from './ui/scroll-area';
import { Badge } from './ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Separator } from './ui/separator';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';
import { wsManager } from '../services/websocket';
import { useAgentStore } from '../stores/agentStore';
import { Agent, AgentRole, AgentStatus } from '../types';
import { cn } from '../lib/utils';
import { toast } from '../hooks/use-toast';

// Chat message types extending the existing WSAgentUpdate protocol
export interface ChatMessage {
  id: string;
  type: 'user' | 'agent' | 'system' | 'task_response';
  content: string;
  timestamp: string;
  agentId?: string;
  agentRole?: AgentRole;
  status?: 'sending' | 'sent' | 'delivered' | 'error';
  metadata?: {
    taskId?: string;
    contextBundleId?: string;
    tokenUsage?: number;
    executionTime?: number;
    command?: string;
    commandType?: string;
    priority?: string;
  };
}

export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
  isActive: boolean;
}

interface CasperChatProps {
  className?: string;
  onTaskSubmit?: (message: string) => void;
  minimized?: boolean;
  onToggleMinimize?: () => void;
}

// Agent role to display name mapping
const AGENT_DISPLAY_NAMES: Record<AgentRole, string> = {
  master: 'Master Prime',
  frontend_prime: 'Frontend Prime',
  backend_prime: 'Backend Prime',
  testing_prime: 'Testing Prime',
  devops_prime: 'DevOps Prime',
  worker: 'Worker Agent'
};

// Agent role colors
const AGENT_COLORS: Record<AgentRole, string> = {
  master: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  frontend_prime: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  backend_prime: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  testing_prime: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  devops_prime: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  worker: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
};

// Command patterns for chat interpretation
interface ChatCommand {
  pattern: RegExp;
  type: 'task' | 'query' | 'system';
  description: string;
  priority?: 'high' | 'medium' | 'low';
}

const CHAT_COMMANDS: ChatCommand[] = [
  { pattern: /^\/task\s+(.+)/i, type: 'task', description: 'Execute a specific task', priority: 'medium' },
  { pattern: /^\/analyze\s+(.+)/i, type: 'task', description: 'Analyze code or project', priority: 'low' },
  { pattern: /^\/fix\s+(.+)/i, type: 'task', description: 'Fix an issue', priority: 'high' },
  { pattern: /^\/create\s+(.+)/i, type: 'task', description: 'Create something new', priority: 'medium' },
  { pattern: /^\/help/i, type: 'query', description: 'Show available commands' },
  { pattern: /^\/status/i, type: 'system', description: 'Show system status' },
  { pattern: /^\/agents/i, type: 'system', description: 'List active agents' },
];

// Helper function to parse chat commands
const parseCommand = (input: string): { isCommand: boolean; command?: string; args?: string; type?: string; priority?: string } => {
  const trimmedInput = input.trim();

  for (const cmd of CHAT_COMMANDS) {
    const match = trimmedInput.match(cmd.pattern);
    if (match) {
      return {
        isCommand: true,
        command: match[0],
        args: match[1] || '',
        type: cmd.type,
        priority: cmd.priority
      };
    }
  }

  // Check for natural language task indicators
  const taskIndicators = [
    /^(create|make|build|develop|implement)/i,
    /^(fix|resolve|debug|solve)/i,
    /^(analyze|review|check|examine)/i,
    /^(help me|can you|please)/i
  ];

  const isNaturalTask = taskIndicators.some(pattern => pattern.test(trimmedInput));

  return {
    isCommand: false,
    command: isNaturalTask ? 'natural_task' : 'chat',
    args: trimmedInput,
    type: isNaturalTask ? 'task' : 'query',
    priority: isNaturalTask ? 'medium' : undefined
  };
};

// Message persistence utilities
const STORAGE_KEY = 'casper-chat-messages';
const MAX_STORED_MESSAGES = 500; // Limit stored messages to prevent localStorage bloat

const saveMessages = (messages: ChatMessage[]) => {
  try {
    const toStore = messages.slice(-MAX_STORED_MESSAGES); // Keep only recent messages
    localStorage.setItem(STORAGE_KEY, JSON.stringify(toStore));
  } catch (error) {
    console.warn('Failed to save chat messages:', error);
  }
};

const loadMessages = (): ChatMessage[] => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return Array.isArray(parsed) ? parsed : [];
    }
  } catch (error) {
    console.warn('Failed to load chat messages:', error);
  }
  return [];
};

export function CasperChat({
  className,
  onTaskSubmit,
  minimized = false,
  onToggleMinimize
}: CasperChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>(() => loadMessages());
  const [inputValue, setInputValue] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [currentSession] = useState<ChatSession>({
    id: 'default',
    title: 'CASPER Chat Session',
    messages: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    isActive: true
  });

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { agents } = useAgentStore();
  const agentList = Array.from(agents.values());

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Save messages to localStorage whenever messages change
  useEffect(() => {
    saveMessages(messages);
  }, [messages]);

  // WebSocket connection management
  useEffect(() => {
    const unsubscribeConnection = wsManager.onConnectionChange((status) => {
      setIsConnected(status === 'connected');
    });

    const unsubscribe = wsManager.on((message) => {
      handleWebSocketMessage(message);
    });

    return () => {
      unsubscribeConnection();
      unsubscribe();
    };
  }, []);

  // Handle incoming WebSocket messages
  const handleWebSocketMessage = useCallback((wsMessage: any) => {
    // Convert WebSocket messages to chat messages
    let chatMessage: ChatMessage | null = null;

    switch (wsMessage.type) {
      case 'agent_progress':
      case 'agent_update':
        if (wsMessage.message || wsMessage.data?.status) {
          chatMessage = {
            id: `${Date.now()}-${Math.random()}`,
            type: 'agent',
            content: wsMessage.message || `Status: ${wsMessage.data?.status}`,
            timestamp: new Date().toISOString(),
            agentId: wsMessage.agent_id || wsMessage.id,
            agentRole: getAgentRole(wsMessage.agent_id || wsMessage.id),
            status: 'delivered',
            metadata: {
              tokenUsage: typeof wsMessage.data?.tokenUsage === 'number'
                ? wsMessage.data.tokenUsage
                : wsMessage.data?.tokenUsage?.current,
              contextBundleId: wsMessage.data?.context_bundle_id
            }
          };
        }
        break;

      case 'task_submitted':
        chatMessage = {
          id: `${Date.now()}-${Math.random()}`,
          type: 'system',
          content: `Task submitted: ${wsMessage.description || 'New task queued'}`,
          timestamp: new Date().toISOString(),
          status: 'delivered',
          metadata: {
            taskId: wsMessage.id
          }
        };
        break;

      case 'agent_spawned':
        chatMessage = {
          id: `${Date.now()}-${Math.random()}`,
          type: 'system',
          content: `Agent spawned: ${AGENT_DISPLAY_NAMES[getAgentRole(wsMessage.agent_id) || 'worker']}`,
          timestamp: new Date().toISOString(),
          status: 'delivered'
        };
        break;

      case 'agent_completed':
        chatMessage = {
          id: `${Date.now()}-${Math.random()}`,
          type: 'agent',
          content: wsMessage.message || 'Task completed successfully',
          timestamp: new Date().toISOString(),
          agentId: wsMessage.agent_id,
          agentRole: getAgentRole(wsMessage.agent_id),
          status: 'delivered'
        };
        break;

      case 'chat_received':
        // Echo back user's chat message for consistency
        chatMessage = {
          id: `${Date.now()}-${Math.random()}`,
          type: 'system',
          content: `Message received: ${wsMessage.message}`,
          timestamp: wsMessage.timestamp || new Date().toISOString(),
          status: 'delivered'
        };
        break;

      case 'agent_response':
        chatMessage = {
          id: `${Date.now()}-${Math.random()}`,
          type: 'agent',
          content: wsMessage.message || 'Processing your request...',
          timestamp: wsMessage.timestamp || new Date().toISOString(),
          agentRole: wsMessage.agent_role || 'master',
          status: 'delivered',
          metadata: {
            taskId: wsMessage.task_id
          }
        };
        break;

      case 'error':
        chatMessage = {
          id: `${Date.now()}-${Math.random()}`,
          type: 'system',
          content: `Error: ${wsMessage.message || 'Unknown error occurred'}`,
          timestamp: new Date().toISOString(),
          status: 'error'
        };
        break;
    }

    if (chatMessage) {
      setMessages(prev => [...prev, chatMessage!]);
    }
  }, []);

  // Helper function to get agent role from agent ID
  const getAgentRole = (agentId?: string): AgentRole | undefined => {
    if (!agentId) return undefined;
    const agent = agentList.find(a => a.id === agentId);
    return agent?.role;
  };

  // Send message with command interpretation
  const handleSendMessage = useCallback(async () => {
    if (!inputValue.trim() || !isConnected) return;

    const parsedCommand = parseCommand(inputValue.trim());

    const userMessage: ChatMessage = {
      id: `${Date.now()}-${Math.random()}`,
      type: 'user',
      content: inputValue.trim(),
      timestamp: new Date().toISOString(),
      status: 'sending',
      metadata: {
        ...(parsedCommand.isCommand && {
          command: parsedCommand.command,
          commandType: parsedCommand.type,
          priority: parsedCommand.priority
        })
      }
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsTyping(true);

    try {
      // Handle special commands locally first
      if (parsedCommand.command === '/help') {
        const helpMessage: ChatMessage = {
          id: `${Date.now()}-${Math.random()}`,
          type: 'system',
          content: `Available commands:
${CHAT_COMMANDS.map(cmd => `${cmd.pattern.source.replace(/\^|\$|\\s\+|\(\.+\)/g, '').replace(/\\/g, '')}: ${cmd.description}`).join('\n')}

You can also use natural language to describe tasks!`,
          timestamp: new Date().toISOString(),
          status: 'delivered'
        };
        setMessages(prev => [...prev, helpMessage]);
        setIsTyping(false);
        setMessages(prev =>
          prev.map(msg =>
            msg.id === userMessage.id
              ? { ...msg, status: 'sent' }
              : msg
          )
        );
        return;
      }

      // Send via WebSocket for real-time processing
      wsManager.send({
        type: 'chat_message',
        message: userMessage.content,
        timestamp: userMessage.timestamp,
        session_id: currentSession.id,
        command_info: parsedCommand.isCommand ? {
          command: parsedCommand.command,
          args: parsedCommand.args,
          type: parsedCommand.type,
          priority: parsedCommand.priority
        } : null
      });

      // Also trigger task submission if it's a task-type command
      if (parsedCommand.type === 'task' && onTaskSubmit) {
        onTaskSubmit(parsedCommand.args || userMessage.content);
      }

      // Update message status
      setMessages(prev =>
        prev.map(msg =>
          msg.id === userMessage.id
            ? { ...msg, status: 'sent' }
            : msg
        )
      );

      // Simulate agent typing
      setTimeout(() => {
        setIsTyping(false);
      }, 2000);

    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages(prev =>
        prev.map(msg =>
          msg.id === userMessage.id
            ? { ...msg, status: 'error' }
            : msg
        )
      );
      setIsTyping(false);
    }
  }, [inputValue, isConnected, currentSession.id, onTaskSubmit]);

  // Handle key press
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Copy message content
  const copyMessage = (content: string) => {
    navigator.clipboard.writeText(content);
    toast({
      title: 'Copied',
      description: 'Message copied to clipboard',
    });
  };

  // Reconnect WebSocket
  const handleReconnect = () => {
    wsManager.reconnect();
    toast({
      title: 'Reconnecting',
      description: 'Attempting to reconnect to CASPER backend...',
    });
  };

  // Clear chat history
  const handleClearHistory = () => {
    setMessages([]);
    localStorage.removeItem(STORAGE_KEY);
    toast({
      title: 'Chat Cleared',
      description: 'Chat history has been cleared',
    });
  };

  // Get active agents for display
  const activeAgents = agentList.filter(a => a.status !== 'idle');

  if (minimized) {
    return (
      <Card className={cn("w-80", className)}>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">CASPER Chat</CardTitle>
            <div className="flex items-center gap-2">
              <Badge variant={isConnected ? 'default' : 'destructive'} className="text-xs">
                {isConnected ? 'Online' : 'Offline'}
              </Badge>
              <Button size="sm" variant="ghost" onClick={onToggleMinimize}>
                <Icon name="maximize" className="h-3 w-3" />
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>
    );
  }

  return (
    <TooltipProvider>
      <Card className={cn("flex flex-col h-full", className)}>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Icon name="bot" className="h-4 w-4" />
              <CardTitle className="text-sm">CASPER Chat</CardTitle>
              <Badge variant={isConnected ? 'default' : 'destructive'} className="text-xs">
                {isConnected ? 'Online' : 'Offline'}
              </Badge>
            </div>
            <div className="flex items-center gap-1">
              {!isConnected && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button size="sm" variant="ghost" onClick={handleReconnect}>
                      <Icon name="refresh" className="h-3 w-3" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Reconnect</TooltipContent>
                </Tooltip>
              )}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button size="sm" variant="ghost" onClick={handleClearHistory}>
                    <Icon name="settings" className="h-3 w-3" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Clear Chat History</TooltipContent>
              </Tooltip>
              {onToggleMinimize && (
                <Button size="sm" variant="ghost" onClick={onToggleMinimize}>
                  <Icon name="minimize" className="h-3 w-3" />
                </Button>
              )}
            </div>
          </div>

          {/* Active Agents Display */}
          {activeAgents.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {activeAgents.map(agent => (
                <Tooltip key={agent.id}>
                  <TooltipTrigger asChild>
                    <Badge
                      variant="outline"
                      className={cn("text-xs", AGENT_COLORS[agent.role])}
                    >
                      {AGENT_DISPLAY_NAMES[agent.role]}
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent>
                    Status: {agent.status} • Progress: {agent.progress}%
                  </TooltipContent>
                </Tooltip>
              ))}
            </div>
          )}
        </CardHeader>

        <Separator />

        {/* Messages Area */}
        <CardContent className="flex-1 p-0">
          <ScrollArea className="h-full p-4">
            <div className="space-y-4">
              {messages.length === 0 && (
                <div className="text-center text-muted-foreground py-8">
                  <Icon name="bot" className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Start a conversation with CASPER</p>
                  <p className="text-xs mt-1">Ask me to create, analyze, or debug anything!</p>
                </div>
              )}

              {messages.map((message) => (
                <div key={message.id} className={cn(
                  "flex gap-3",
                  message.type === 'user' ? 'flex-row-reverse' : 'flex-row'
                )}>
                  <div className={cn(
                    "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center",
                    message.type === 'user'
                      ? 'bg-blue-100 dark:bg-blue-900'
                      : message.type === 'system'
                      ? 'bg-gray-100 dark:bg-gray-800'
                      : AGENT_COLORS[message.agentRole || 'worker']
                  )}>
                    {message.type === 'user' ? (
                      <Icon name="user" className="h-4 w-4" />
                    ) : message.type === 'system' ? (
                      <Icon name="alert-circle" className="h-4 w-4" />
                    ) : (
                      <Icon name="bot" className="h-4 w-4" />
                    )}
                  </div>

                  <div className={cn(
                    "flex-1 max-w-[80%]",
                    message.type === 'user' ? 'text-right' : 'text-left'
                  )}>
                    {/* Message Header */}
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-medium">
                        {message.type === 'user'
                          ? 'You'
                          : message.type === 'system'
                          ? 'System'
                          : AGENT_DISPLAY_NAMES[message.agentRole || 'worker']
                        }
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </span>
                      {message.status === 'sending' && <Icon name="loader" className="h-3 w-3 animate-spin" />}
                      {message.status === 'sent' && <Icon name="check" className="h-3 w-3" />}
                      {message.status === 'error' && <Icon name="alert-circle" className="h-3 w-3 text-red-500" />}
                    </div>

                    {/* Message Content */}
                    <div className={cn(
                      "rounded-lg px-3 py-2 text-sm relative group",
                      message.type === 'user'
                        ? 'bg-blue-500 text-white ml-auto'
                        : message.type === 'system'
                        ? 'bg-muted'
                        : 'bg-muted border',
                      message.status === 'error' && 'bg-red-100 border-red-200 dark:bg-red-900/20'
                    )}>
                      <p className="whitespace-pre-wrap break-words">{message.content}</p>

                      {/* Copy button */}
                      <Button
                        size="sm"
                        variant="ghost"
                        className="absolute -top-2 -right-2 opacity-0 group-hover:opacity-100 transition-opacity h-6 w-6 p-0"
                        onClick={() => copyMessage(message.content)}
                      >
                        <Icon name="copy" className="h-3 w-3" />
                      </Button>
                    </div>

                    {/* Message Metadata */}
                    {message.metadata && (
                      <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                        {message.metadata.tokenUsage && (
                          <span>Tokens: {message.metadata.tokenUsage}</span>
                        )}
                        {message.metadata.executionTime && (
                          <span>Time: {message.metadata.executionTime}ms</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {/* Typing Indicator */}
              {isTyping && (
                <div className="flex gap-3">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                    <Icon name="bot" className="h-4 w-4" />
                  </div>
                  <div className="bg-muted rounded-lg px-3 py-2">
                    <div className="flex items-center gap-1">
                      <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" />
                      <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce delay-100" />
                      <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce delay-200" />
                    </div>
                  </div>
                </div>
              )}

              <div ref={scrollRef} />
            </div>
          </ScrollArea>
        </CardContent>

        <Separator />

        {/* Input Area */}
        <div className="p-4">
          <div className="flex gap-2">
            <Input
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={isConnected ? "Ask CASPER anything or use /help for commands..." : "Connecting..."}
              disabled={!isConnected}
              className="flex-1"
            />
            <Button
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || !isConnected}
              size="sm"
            >
              <Icon name="send" className="h-4 w-4" />
            </Button>
          </div>

          <div className="flex items-center justify-between mt-2 text-xs text-muted-foreground">
            <span>Press Enter to send • Shift+Enter for new line</span>
            <div className="flex items-center gap-2">
              <Icon name="clock" className="h-3 w-3" />
              <span>{messages.length} messages</span>
            </div>
          </div>
        </div>
      </Card>
    </TooltipProvider>
  );
}