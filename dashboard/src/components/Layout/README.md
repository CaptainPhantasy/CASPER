# Scalable Panel System

This directory contains the implementation of CASPER's scalable panel system, providing resizable and configurable UI panels for optimal developer experience.

## Features

✅ **Resizable Panels**: Smooth 60 FPS resizing with drag handles
✅ **Layout Persistence**: State persists across browser sessions
✅ **Preset Layouts**: Pre-configured layouts for different workflows
✅ **Responsive Design**: Automatic layout adaptation for mobile/tablet/desktop
✅ **Performance Monitoring**: Built-in FPS and resize performance tracking
✅ **Collapsible Panels**: Individual panel collapse/expand functionality

## Components

### Core Components

- `PanelLayout`: Main layout container with resizable panels
- `LayoutPanel`: Individual panel component with configuration
- `LayoutPresetSelector`: Dropdown for switching between layouts
- `PanelControls`: Buttons for toggling panel visibility

### Utility Components

- `LayoutTest`: Testing component for development
- `useLayoutPerformance`: Hook for performance monitoring

## Usage

```tsx
import { PanelLayout, LayoutPanel } from '@/components/Layout';

function App() {
  return (
    <PanelLayout>
      <LayoutPanel panelId="sidebar">
        <FileExplorer />
      </LayoutPanel>

      <LayoutPanel panelId="main">
        <MainContent />
      </LayoutPanel>

      <LayoutPanel panelId="activity">
        <AgentActivity />
      </LayoutPanel>

      <LayoutPanel panelId="terminal">
        <Terminal />
      </LayoutPanel>
    </PanelLayout>
  );
}
```

## Layout Presets

### Developer Layout
- **File Explorer**: 300px (collapsible)
- **Main Content**: 50% (remaining space)
- **Agent Activity**: 280px (collapsible)
- **Terminal**: 200px (visible by default)

### Analyst Layout
- **File Explorer**: 250px (collapsible)
- **Main Content**: 45% (remaining space)
- **Agent Activity**: 400px (expanded for metrics)
- **Terminal**: 180px (collapsed by default)

### Compact Layout
- **File Explorer**: 220px (collapsible)
- **Main Content**: 70% (maximized)
- **Agent Activity**: 260px (collapsed by default)
- **Terminal**: 150px (hidden by default)

### Mobile Layout
- **Single Panel**: Full width, mobile-optimized
- **Collapsible**: All panels can be toggled via menu

## Performance

The panel system is optimized for:
- **60 FPS resize operations**: Smooth dragging experience
- **<2ms resize latency**: Near-instantaneous panel updates
- **Memory efficient**: Lightweight state management with Zustand
- **CPU optimized**: RAF-based performance monitoring

## State Management

Panel configuration is persisted using Zustand with localStorage:
- Panel sizes and visibility
- Collapsed/expanded states
- Current active layout
- Responsive breakpoint detection

## Responsive Breakpoints

- **Desktop**: ≥1024px - Full panel layout
- **Tablet**: 768px-1023px - Compact layout with some collapsed panels
- **Mobile**: <768px - Single panel with drawer navigation

## Integration

The panel system integrates seamlessly with:
- Existing CASPER dashboard components
- Terminal system (when implemented)
- Agent activity monitoring
- File explorer and viewer
- Settings and configuration

## Technical Details

- **Library**: react-resizable-panels v3.0.6
- **State**: Zustand with localStorage persistence
- **Styling**: Tailwind CSS with design system tokens
- **Performance**: RAF-based monitoring and tracking
- **TypeScript**: Fully typed with strict mode compliance