import * as React from 'react';
import {
  EyeOff,
  Maximize2,
  Minimize2,
  PanelLeft,
  Terminal,
  Activity,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useLayoutStore, PanelId } from '@/stores/layoutStore';
import { cn } from '@/lib/utils';

interface PanelControlsProps {
  className?: string;
}

interface PanelControlButtonProps {
  panelId: PanelId;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
}

const panelConfigs: Record<PanelId, { icon: React.ComponentType<{ className?: string }>; label: string }> = {
  sidebar: { icon: PanelLeft, label: 'File Explorer' },
  main: { icon: Maximize2, label: 'Main Content' },
  activity: { icon: Activity, label: 'Agent Activity' },
  terminal: { icon: Terminal, label: 'Terminal' },
};

const PanelControlButton: React.FC<PanelControlButtonProps> = ({
  panelId,
  icon: Icon,
  label,
}) => {
  const {
    panels,
    togglePanel,
    collapsePanel,
    expandPanel,
  } = useLayoutStore();

  const panelConfig = panels[panelId];
  const { visible, collapsed, collapsible } = panelConfig;

  const handleToggle = () => {
    if (collapsible && visible && !collapsed) {
      collapsePanel(panelId);
    } else if (collapsible && visible && collapsed) {
      expandPanel(panelId);
    } else {
      togglePanel(panelId);
    }
  };

  const getButtonState = () => {
    if (!visible) return 'hidden';
    if (collapsed) return 'collapsed';
    return 'visible';
  };

  const getButtonIcon = () => {
    const state = getButtonState();
    if (state === 'hidden') return EyeOff;
    if (state === 'collapsed') return Minimize2;
    return Icon;
  };

  const getButtonVariant = () => {
    const state = getButtonState();
    return state === 'visible' ? 'default' : 'outline';
  };

  const ButtonIcon = getButtonIcon();

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant={getButtonVariant()}
            size="sm"
            onClick={handleToggle}
            className={cn(
              'gap-2',
              !visible && 'opacity-50'
            )}
          >
            <ButtonIcon className="h-4 w-4" />
            <span className="hidden sm:inline">{label}</span>
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p>
            {!visible ? `Show ${label}` : collapsed ? `Expand ${label}` : `Collapse ${label}`}
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};

export const PanelControls: React.FC<PanelControlsProps> = ({ className }) => {
  const { breakpoint } = useLayoutStore();

  // Don't show panel controls on mobile
  if (breakpoint === 'mobile') {
    return null;
  }

  return (
    <div className={cn('flex items-center gap-2', className)}>
      {Object.entries(panelConfigs).map(([panelId, config]) => {
        // Skip main panel control as it's always visible
        if (panelId === 'main') return null;

        return (
          <PanelControlButton
            key={panelId}
            panelId={panelId as PanelId}
            icon={config.icon}
            label={config.label}
          />
        );
      })}
    </div>
  );
};