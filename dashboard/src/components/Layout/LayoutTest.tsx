import * as React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useLayoutStore } from '@/stores/layoutStore';
import { Badge } from '@/components/ui/badge';

export const LayoutTest: React.FC = () => {
  const {
    currentLayout,
    panels,
    presets,
    breakpoint,
    setCurrentLayout,
    updatePanel,
    togglePanel,
  } = useLayoutStore();

  const testPanelResize = () => {
    // Simulate panel resize
    updatePanel('sidebar', { size: Math.random() * 200 + 200 });
    updatePanel('activity', { size: Math.random() * 200 + 250 });
  };

  const testLayoutSwitch = () => {
    const layoutIds = Object.keys(presets);
    const currentIndex = layoutIds.indexOf(currentLayout);
    const nextIndex = (currentIndex + 1) % layoutIds.length;
    setCurrentLayout(layoutIds[nextIndex]);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Panel System Test</CardTitle>
        <CardDescription>Test layout functionality and performance</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <h4 className="text-sm font-medium mb-2">Current State</h4>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm">Layout:</span>
                <Badge variant="secondary">{currentLayout}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Breakpoint:</span>
                <Badge variant="outline">{breakpoint}</Badge>
              </div>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-medium mb-2">Panel Visibility</h4>
            <div className="space-y-1">
              {Object.entries(panels).map(([id, config]) => (
                <div key={id} className="flex items-center justify-between text-sm">
                  <span className="capitalize">{id}:</span>
                  <Badge variant={config.visible ? 'default' : 'secondary'}>
                    {config.visible ? 'Visible' : 'Hidden'}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <Button onClick={testLayoutSwitch} variant="outline" size="sm">
            Switch Layout
          </Button>
          <Button onClick={testPanelResize} variant="outline" size="sm">
            Random Resize
          </Button>
          <Button onClick={() => togglePanel('terminal')} variant="outline" size="sm">
            Toggle Terminal
          </Button>
          <Button onClick={() => togglePanel('activity')} variant="outline" size="sm">
            Toggle Activity
          </Button>
        </div>

        <div>
          <h4 className="text-sm font-medium mb-2">Panel Sizes</h4>
          <div className="grid grid-cols-2 gap-2 text-sm">
            {Object.entries(panels).map(([id, config]) => (
              <div key={id} className="flex justify-between">
                <span className="capitalize">{id}:</span>
                <span>{config.size}px</span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};