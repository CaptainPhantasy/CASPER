import * as React from 'react';
import { Icon } from '../icons/IconMapping';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { useLayoutStore } from '@/stores/layoutStore';
import { cn } from '@/lib/utils';

interface LayoutPresetSelectorProps {
  className?: string;
}

const getBreakpointIcon = (breakpoint?: string) => {
  switch (breakpoint) {
    case 'mobile':
      return <Icon name="smartphone" className="h-3 w-3" />;
    case 'tablet':
      return <Icon name="tablet" className="h-3 w-3" />;
    case 'desktop':
    default:
      return <Icon name="monitor" className="h-3 w-3" />;
  }
};

export const LayoutPresetSelector: React.FC<LayoutPresetSelectorProps> = ({
  className,
}) => {
  const {
    currentLayout,
    presets,
    breakpoint,
    setCurrentLayout,
    resetLayout
  } = useLayoutStore();

  const currentPreset = presets[currentLayout];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className={cn('gap-2', className)}
          aria-label="Select layout preset"
        >
          <Icon name="layout" className="h-4 w-4" />
          {currentPreset?.name || 'Custom'}
          <Badge variant="secondary" className="ml-1 gap-1 text-xs">
            {getBreakpointIcon(breakpoint)}
            {breakpoint}
          </Badge>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel>Layout Presets</DropdownMenuLabel>
        <DropdownMenuSeparator />

        {Object.values(presets).map((preset) => (
          <DropdownMenuItem
            key={preset.id}
            onClick={() => setCurrentLayout(preset.id)}
            className="flex items-center justify-between gap-2 cursor-pointer"
          >
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium">{preset.name}</span>
                {preset.breakpoint && (
                  <Badge variant="outline" className="gap-1 text-xs">
                    {getBreakpointIcon(preset.breakpoint)}
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {preset.description}
              </p>
            </div>
            {currentLayout === preset.id && (
              <Icon name="check" className="h-4 w-4 text-primary" />
            )}
          </DropdownMenuItem>
        ))}

        <DropdownMenuSeparator />

        <DropdownMenuItem
          onClick={resetLayout}
          className="text-muted-foreground cursor-pointer"
        >
          Reset to Default
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};