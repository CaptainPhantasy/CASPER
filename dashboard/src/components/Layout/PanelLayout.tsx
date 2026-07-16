import * as React from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { cn } from '@/lib/utils';
import { useLayoutStore, PanelId } from '@/stores/layoutStore';
import { useLayoutPerformance } from '@/hooks/useLayoutPerformance';

interface PanelLayoutProps {
  children: React.ReactNode;
  className?: string;
}

interface LayoutPanelProps {
  panelId: PanelId;
  children: React.ReactNode;
  className?: string;
}

export const LayoutPanel: React.FC<LayoutPanelProps> = ({
  panelId,
  children,
  className,
}) => {
  const { panels, updatePanel } = useLayoutStore();
  const { trackResize } = useLayoutPerformance();
  const panelConfig = panels[panelId];

  if (!panelConfig.visible) {
    return null;
  }

  return (
    <Panel
      id={panelId}
      defaultSize={panelConfig.size}
      minSize={panelConfig.minSize}
      maxSize={panelConfig.maxSize}
      collapsible={panelConfig.collapsible}
      onResize={(size) => {
        const endTracking = trackResize();
        updatePanel(panelId, { size });
        endTracking();
      }}
      className={cn('relative', className)}
    >
      {children}
    </Panel>
  );
};

export const PanelLayout: React.FC<PanelLayoutProps> = ({
  children,
  className,
}) => {
  const { breakpoint, initializeResponsiveLayout } = useLayoutStore();

  React.useEffect(() => {
    // Initialize responsive layout handling
    const cleanup = initializeResponsiveLayout();
    return cleanup;
  }, [initializeResponsiveLayout]);

  // For mobile, render children directly without panels
  if (breakpoint === 'mobile') {
    return (
      <div className={cn('flex h-full w-full', className)}>
        {children}
      </div>
    );
  }

  // Separate horizontal and terminal (vertical) panels
  const horizontalPanels: React.ReactElement[] = [];
  let terminalPanel: React.ReactElement | null = null;

  React.Children.forEach(children, (child) => {
    if (React.isValidElement(child) && child.type === LayoutPanel) {
      if (child.props.panelId === 'terminal') {
        terminalPanel = child;
      } else {
        horizontalPanels.push(child);
      }
    }
  });

  return (
    <div className={cn('h-full w-full', className)}>
      <PanelGroup direction="vertical" className="h-full">
        {/* Main horizontal layout */}
        <Panel defaultSize={terminalPanel ? 70 : 100} minSize={50}>
          <PanelGroup direction="horizontal" className="h-full">
            {horizontalPanels.map((child, index) => (
              <React.Fragment key={child.props.panelId || index}>
                {child}
                {index < horizontalPanels.length - 1 && (
                  <PanelResizeHandle className="w-px bg-border hover:bg-border/80 transition-colors duration-200" />
                )}
              </React.Fragment>
            ))}
          </PanelGroup>
        </Panel>

        {/* Terminal panel at bottom */}
        {terminalPanel && (
          <>
            <PanelResizeHandle className="h-px bg-border hover:bg-border/80 transition-colors duration-200" />
            {terminalPanel}
          </>
        )}
      </PanelGroup>
    </div>
  );
};