import { create } from 'zustand';
import { Terminal } from '@xterm/xterm';

export interface TerminalSession {
  id: string;
  title: string;
  terminal: Terminal | null;
  wsId: string | null;
  status: 'connecting' | 'connected' | 'disconnected' | 'error';
  cwd: string;
  createdAt: number;
  lastActiveAt: number;
}

interface TerminalState {
  sessions: Map<string, TerminalSession>;
  activeSessionId: string | null;
  isTerminalVisible: boolean;
  terminalHeight: number;

  // Actions
  createSession: (title?: string, cwd?: string) => string;
  removeSession: (sessionId: string) => void;
  setActiveSession: (sessionId: string) => void;
  updateSession: (sessionId: string, updates: Partial<TerminalSession>) => void;
  setTerminalVisible: (visible: boolean) => void;
  setTerminalHeight: (height: number) => void;
  getActiveSession: () => TerminalSession | null;
  reset: () => void;
}

const generateSessionId = () => {
  return `terminal-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

export const useTerminalStore = create<TerminalState>((set, get) => ({
  sessions: new Map(),
  activeSessionId: null,
  isTerminalVisible: false,
  terminalHeight: 300,

  createSession: (title?: string, cwd?: string) => {
    const sessionId = generateSessionId();
    const session: TerminalSession = {
      id: sessionId,
      title: title || `Terminal ${get().sessions.size + 1}`,
      terminal: null,
      wsId: null,
      status: 'disconnected',
      cwd: cwd || '~',
      createdAt: Date.now(),
      lastActiveAt: Date.now(),
    };

    set((state) => {
      const sessions = new Map(state.sessions);
      sessions.set(sessionId, session);

      return {
        sessions,
        activeSessionId: state.activeSessionId || sessionId,
        isTerminalVisible: true, // Show terminal when creating first session
      };
    });

    return sessionId;
  },

  removeSession: (sessionId: string) => {
    set((state) => {
      const sessions = new Map(state.sessions);
      const session = sessions.get(sessionId);

      // Dispose of terminal instance
      if (session?.terminal) {
        session.terminal.dispose();
      }

      sessions.delete(sessionId);

      let newActiveSessionId = state.activeSessionId;

      // If we removed the active session, switch to another one
      if (state.activeSessionId === sessionId) {
        const remainingSessions = Array.from(sessions.keys());
        newActiveSessionId = remainingSessions.length > 0 ? remainingSessions[0] : null;
      }

      return {
        sessions,
        activeSessionId: newActiveSessionId,
        isTerminalVisible: sessions.size > 0 && state.isTerminalVisible,
      };
    });
  },

  setActiveSession: (sessionId: string) => {
    set((state) => {
      if (state.sessions.has(sessionId)) {
        const sessions = new Map(state.sessions);
        const session = sessions.get(sessionId)!;
        sessions.set(sessionId, { ...session, lastActiveAt: Date.now() });

        return {
          sessions,
          activeSessionId: sessionId,
        };
      }
      return state;
    });
  },

  updateSession: (sessionId: string, updates: Partial<TerminalSession>) => {
    set((state) => {
      const sessions = new Map(state.sessions);
      const session = sessions.get(sessionId);

      if (session) {
        sessions.set(sessionId, {
          ...session,
          ...updates,
          lastActiveAt: Date.now(),
        });
      }

      return { sessions };
    });
  },

  setTerminalVisible: (visible: boolean) => {
    set({ isTerminalVisible: visible });
  },

  setTerminalHeight: (height: number) => {
    set({ terminalHeight: Math.max(200, Math.min(800, height)) }); // Constrain height
  },

  getActiveSession: () => {
    const state = get();
    return state.activeSessionId ? state.sessions.get(state.activeSessionId) || null : null;
  },

  reset: () => {
    const state = get();
    // Dispose all terminal instances
    state.sessions.forEach((session) => {
      if (session.terminal) {
        session.terminal.dispose();
      }
    });

    set({
      sessions: new Map(),
      activeSessionId: null,
      isTerminalVisible: false,
      terminalHeight: 300,
    });
  },
}));