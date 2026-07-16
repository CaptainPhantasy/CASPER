import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type PanelId = 'sidebar' | 'main' | 'activity' | 'terminal';

export interface PanelConfig {
  id: PanelId;
  size: number;
  minSize?: number;
  maxSize?: number;
  collapsible?: boolean;
  collapsed?: boolean;
  visible: boolean;
}

export interface LayoutPreset {
  id: string;
  name: string;
  description: string;
  panels: Record<PanelId, Omit<PanelConfig, 'id'>>;
  breakpoint?: 'desktop' | 'tablet' | 'mobile';
}

export interface LayoutState {
  currentLayout: string;
  panels: Record<PanelId, PanelConfig>;
  presets: Record<string, LayoutPreset>;
  breakpoint: 'desktop' | 'tablet' | 'mobile';

  // Actions
  setCurrentLayout: (layoutId: string) => void;
  updatePanel: (panelId: PanelId, config: Partial<Omit<PanelConfig, 'id'>>) => void;
  togglePanel: (panelId: PanelId) => void;
  collapsePanel: (panelId: PanelId) => void;
  expandPanel: (panelId: PanelId) => void;
  resetLayout: () => void;
  setBreakpoint: (breakpoint: 'desktop' | 'tablet' | 'mobile') => void;
  initializeResponsiveLayout: () => void;
}

// Default panel configurations
const defaultPanels: Record<PanelId, PanelConfig> = {
  sidebar: {
    id: 'sidebar',
    size: 280,
    minSize: 200,
    maxSize: 400,
    collapsible: true,
    collapsed: false,
    visible: true,
  },
  main: {
    id: 'main',
    size: 60, // percentage of remaining space
    minSize: 30,
    maxSize: 80,
    collapsible: false,
    visible: true,
  },
  activity: {
    id: 'activity',
    size: 320,
    minSize: 250,
    maxSize: 500,
    collapsible: true,
    collapsed: false,
    visible: true,
  },
  terminal: {
    id: 'terminal',
    size: 250,
    minSize: 150,
    maxSize: 400,
    collapsible: true,
    collapsed: true,
    visible: false,
  },
};

// Layout presets
const defaultPresets: Record<string, LayoutPreset> = {
  developer: {
    id: 'developer',
    name: 'Developer',
    description: 'Optimal for coding with terminal and file explorer',
    panels: {
      sidebar: { size: 300, minSize: 200, maxSize: 400, collapsible: true, collapsed: false, visible: true },
      main: { size: 50, minSize: 30, maxSize: 70, collapsible: false, visible: true },
      activity: { size: 280, minSize: 250, maxSize: 400, collapsible: true, collapsed: false, visible: true },
      terminal: { size: 200, minSize: 150, maxSize: 300, collapsible: true, collapsed: false, visible: true },
    },
  },
  analyst: {
    id: 'analyst',
    name: 'Analyst',
    description: 'Focus on metrics and monitoring with expanded activity panel',
    panels: {
      sidebar: { size: 250, minSize: 200, maxSize: 350, collapsible: true, collapsed: false, visible: true },
      main: { size: 45, minSize: 30, maxSize: 60, collapsible: false, visible: true },
      activity: { size: 400, minSize: 350, maxSize: 600, collapsible: true, collapsed: false, visible: true },
      terminal: { size: 180, minSize: 150, maxSize: 250, collapsible: true, collapsed: true, visible: false },
    },
  },
  compact: {
    id: 'compact',
    name: 'Compact',
    description: 'Minimal layout for smaller screens',
    panels: {
      sidebar: { size: 220, minSize: 180, maxSize: 300, collapsible: true, collapsed: false, visible: true },
      main: { size: 70, minSize: 40, maxSize: 80, collapsible: false, visible: true },
      activity: { size: 260, minSize: 200, maxSize: 350, collapsible: true, collapsed: true, visible: true },
      terminal: { size: 150, minSize: 120, maxSize: 200, collapsible: true, collapsed: true, visible: false },
    },
  },
  mobile: {
    id: 'mobile',
    name: 'Mobile',
    description: 'Single panel layout for mobile devices',
    breakpoint: 'mobile',
    panels: {
      sidebar: { size: 100, collapsible: true, collapsed: true, visible: false },
      main: { size: 100, minSize: 80, maxSize: 100, collapsible: false, visible: true },
      activity: { size: 100, collapsible: true, collapsed: true, visible: false },
      terminal: { size: 100, collapsible: true, collapsed: true, visible: false },
    },
  },
};

export const useLayoutStore = create<LayoutState>()(
  persist(
    (set, get) => ({
      currentLayout: 'developer',
      panels: { ...defaultPanels },
      presets: { ...defaultPresets },
      breakpoint: 'desktop',

      setCurrentLayout: (layoutId: string) => {
        const preset = get().presets[layoutId];
        if (preset) {
          set((state) => {
            const newPanels = { ...state.panels };
            Object.entries(preset.panels).forEach(([panelId, config]) => {
              newPanels[panelId as PanelId] = {
                id: panelId as PanelId,
                ...config,
              };
            });
            return {
              currentLayout: layoutId,
              panels: newPanels,
            };
          });
        }
      },

      updatePanel: (panelId: PanelId, config: Partial<Omit<PanelConfig, 'id'>>) => {
        set((state) => ({
          panels: {
            ...state.panels,
            [panelId]: {
              ...state.panels[panelId],
              ...config,
            },
          },
        }));
      },

      togglePanel: (panelId: PanelId) => {
        set((state) => ({
          panels: {
            ...state.panels,
            [panelId]: {
              ...state.panels[panelId],
              visible: !state.panels[panelId].visible,
            },
          },
        }));
      },

      collapsePanel: (panelId: PanelId) => {
        set((state) => ({
          panels: {
            ...state.panels,
            [panelId]: {
              ...state.panels[panelId],
              collapsed: true,
            },
          },
        }));
      },

      expandPanel: (panelId: PanelId) => {
        set((state) => ({
          panels: {
            ...state.panels,
            [panelId]: {
              ...state.panels[panelId],
              collapsed: false,
            },
          },
        }));
      },

      resetLayout: () => {
        set(() => ({
          panels: { ...defaultPanels },
          currentLayout: 'developer',
        }));
      },

      setBreakpoint: (breakpoint: 'desktop' | 'tablet' | 'mobile') => {
        set((state) => {
          // Auto-switch to appropriate layout for breakpoint
          let newLayout = state.currentLayout;
          if (breakpoint === 'mobile' && state.currentLayout !== 'mobile') {
            newLayout = 'mobile';
          } else if (breakpoint === 'tablet' && state.currentLayout === 'mobile') {
            newLayout = 'compact';
          } else if (breakpoint === 'desktop' && (state.currentLayout === 'mobile' || state.currentLayout === 'compact')) {
            newLayout = 'developer';
          }

          if (newLayout !== state.currentLayout) {
            const preset = state.presets[newLayout];
            if (preset) {
              const newPanels = { ...state.panels };
              Object.entries(preset.panels).forEach(([panelId, config]) => {
                newPanels[panelId as PanelId] = {
                  id: panelId as PanelId,
                  ...config,
                };
              });
              return {
                breakpoint,
                currentLayout: newLayout,
                panels: newPanels,
              };
            }
          }

          return { breakpoint };
        });
      },

      initializeResponsiveLayout: () => {
        const updateBreakpoint = () => {
          const width = window.innerWidth;
          let breakpoint: 'desktop' | 'tablet' | 'mobile';

          if (width < 768) {
            breakpoint = 'mobile';
          } else if (width < 1024) {
            breakpoint = 'tablet';
          } else {
            breakpoint = 'desktop';
          }

          const currentBreakpoint = get().breakpoint;
          if (breakpoint !== currentBreakpoint) {
            get().setBreakpoint(breakpoint);
          }
        };

        // Set initial breakpoint
        updateBreakpoint();

        // Listen for window resize
        const handleResize = () => {
          updateBreakpoint();
        };

        window.addEventListener('resize', handleResize);

        // Return cleanup function
        return () => {
          window.removeEventListener('resize', handleResize);
        };
      },
    }),
    {
      name: 'casper-layout-store',
      partialize: (state) => ({
        currentLayout: state.currentLayout,
        panels: state.panels,
      }),
    }
  )
);