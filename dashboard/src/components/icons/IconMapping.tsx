/**
 * Icon Mapping Component - Tabler Icons
 * Professional grade icons replacing lucide-react
 * Maps commonly used icon names to Tabler Icons equivalents
 */

import * as TablerIcons from '@tabler/icons-react';
import { ElementType, HTMLAttributes, SVGAttributes } from 'react';

type TablerModule = Record<string, ElementType>;
const Tabler = TablerIcons as unknown as TablerModule;

// Fallback rendered when a requested Tabler icon cannot be resolved.
const FallbackIcon: ElementType = Tabler.IconHelpCircle ?? Tabler.IconSquare;

/**
 * Resolve a Tabler icon by its base (un-prefixed) name. All Tabler icons are
 * exported with an `Icon` prefix (e.g. `IconHome`), so we prepend it here.
 * Falls back to a placeholder icon if the name is not present in the package.
 */
const ic = (base: string): ElementType => Tabler[`Icon${base}`] ?? FallbackIcon;

// Mapping from Lucide/common icon names to Tabler icons
export const iconMap: Record<string, ElementType> = {
  // Navigation
  'home': ic('Home'),
  'settings': ic('Settings'),
  'terminal': ic('Terminal'),
  'layout': ic('Layout'),
  'panel-left': ic('LayoutSidebar'),
  'panel-right': ic('LayoutSidebarRight'),

  // File operations
  'file': ic('File'),
  'file-text': ic('FileText'),
  'file-warning': ic('FileAlert'),
  'file-code': ic('FileCode'),
  'file-edit': ic('FilePencil'),
  'folder': ic('Folder'),
  'folder-open': ic('FolderOpen'),
  'folder-tree': ic('Folders'),
  'save': ic('DeviceFloppy'),
  'files': ic('Files'),

  // Actions
  'check': ic('Check'),
  'x': ic('X'),
  'x-circle': ic('CircleX'),
  'plus': ic('Plus'),
  'plus-circle': ic('CirclePlus'),
  'minus': ic('Minus'),
  'minus-circle': ic('CircleMinus'),
  'trash': ic('Trash'),
  'trash-2': ic('Trash'),
  'edit': ic('Edit'),
  'edit-2': ic('Edit'),
  'edit-3': ic('Edit'),
  'pencil': ic('Pencil'),
  'eye': ic('Eye'),
  'eye-off': ic('EyeOff'),
  'copy': ic('Copy'),
  'clipboard': ic('Clipboard'),
  'clipboard-copy': ic('ClipboardCopy'),

  // Status & Alerts
  'alert-circle': ic('AlertCircle'),
  'alert-triangle': ic('AlertTriangle'),
  'alert-octagon': ic('AlertOctagon'),
  'info': ic('InfoCircle'),
  'help-circle': ic('HelpCircle'),
  'check-circle': ic('CircleCheck'),
  'check-circle-2': ic('CircleCheck'),
  'loader': ic('Loader'),
  'loader-2': ic('Loader'),
  'refresh-cw': ic('Refresh'),
  'refresh-ccw': ic('RefreshAlert'),
  'rotate-ccw': ic('Rotate'),
  'rotate-cw': ic('RotateClockwise'),
  'sparkles': ic('Stars'),

  // Security
  'shield': ic('Shield'),
  'shield-check': ic('ShieldCheck'),
  'shield-alert': ic('ShieldExclamation'),
  'shield-x': ic('ShieldX'),
  'lock': ic('Lock'),
  'unlock': ic('LockOpen'),
  'key': ic('Key'),

  // Business & Analytics
  'bar-chart': ic('ChartBar'),
  'bar-chart-2': ic('ChartBar'),
  'bar-chart-3': ic('ChartBar'),
  'bar-chart-4': ic('ChartBar'),
  'line-chart': ic('ChartLine'),
  'pie-chart': ic('ChartPie'),
  'trending-up': ic('TrendingUp'),
  'trending-down': ic('TrendingDown'),
  'activity': ic('Activity'),
  'zap': ic('Bolt'),
  'bolt': ic('Bolt'),
  'target': ic('Target'),

  // Time & Calendar
  'clock': ic('Clock'),
  'calendar': ic('Calendar'),
  'timer': ic('Hourglass'),
  'hourglass': ic('Hourglass'),

  // UI Components
  'command': ic('Command'),
  'moon': ic('Moon'),
  'sun': ic('Sun'),
  'chevron-down': ic('ChevronDown'),
  'chevron-up': ic('ChevronUp'),
  'chevron-left': ic('ChevronLeft'),
  'chevron-right': ic('ChevronRight'),
  'chevrons-down': ic('ChevronsDown'),
  'chevrons-up': ic('ChevronsUp'),
  'chevrons-left': ic('ChevronsLeft'),
  'chevrons-right': ic('ChevronsRight'),
  'search': ic('Search'),
  'filter': ic('Filter'),
  'more-horizontal': ic('Dots'),
  'more-vertical': ic('DotsVertical'),
  'menu': ic('Menu'),
  'menu-square': ic('Menu2'),

  // Code & Development
  'code': ic('Code'),
  'code-2': ic('Code'),
  'braces': ic('Braces'),
  'terminal-square': ic('Terminal'),
  'git-branch': ic('GitBranch'),
  'git-commit': ic('GitCommit'),
  'git-merge': ic('GitMerge'),
  'git-pull-request': ic('GitPullRequest'),

  // Connectivity
  'globe': ic('World'),
  'wifi': ic('Wifi'),
  'wifi-off': ic('WifiOff'),
  'server': ic('Server'),
  'database': ic('Database'),
  'cloud': ic('Cloud'),
  'cloud-off': ic('CloudOff'),

  // AI & Intelligence
  'brain': ic('Brain'),
  'cpu': ic('Cpu'),
  'bot': ic('Robot'),
  'sparkle': ic('Star'),

  // Layout & Containers
  'layout-dashboard': ic('LayoutDashboard'),
  'layout-grid': ic('LayoutGrid'),
  'layout-list': ic('List'),
  'columns': ic('Columns'),
  'sidebar': ic('LayoutSidebar'),

  // Input & Output
  'upload': ic('Upload'),
  'download': ic('Download'),
  'send': ic('Send'),
  'message-square': ic('Message'),
  'message-circle': ic('MessageCircle'),
  'mail': ic('Mail'),
  'at-sign': ic('At'),
  'link': ic('Link'),
  'unlink': ic('LinkOff'),

  // User & People
  'user': ic('User'),
  'users': ic('Users'),
  'user-plus': ic('UserPlus'),
  'user-minus': ic('UserMinus'),
  'user-check': ic('UserCheck'),
  'user-x': ic('UserX'),
  'user-circle': ic('UserCircle'),
  'avatar': ic('UserCircle'),

  // Settings & Tools
  'settings-2': ic('Settings'),
  'tool': ic('Tool'),
  'wrench': ic('Tool'),
  'hammer': ic('Hammer'),
  'sliders': ic('Adjustments'),
  'tune': ic('Adjustments'),
  'adjustments': ic('Adjustments'),

  // Misc
  'play': ic('PlayerPlay'),
  'pause': ic('PlayerPause'),
  'stop': ic('PlayerStop'),
  'skip-back': ic('PlayerSkipBack'),
  'skip-forward': ic('PlayerSkipForward'),
  'volume': ic('Volume'),
  'volume-2': ic('Volume'),
  'mic': ic('Microphone'),
  'mic-off': ic('MicrophoneOff'),
  'video': ic('Video'),
  'video-off': ic('VideoOff'),
  'image': ic('Photo'),
  'film': ic('Movie'),
  'music': ic('Music'),
  'bookmark': ic('Bookmark'),
  'heart': ic('Heart'),
  'star': ic('Star'),
  'flag': ic('Flag'),
  'log-in': ic('Login'),
  'log-out': ic('Logout'),
  'external-link': ic('ExternalLink'),
  'expand': ic('Maximize'),
  'shrink': ic('Minimize'),
  'maximize': ic('Maximize'),
  'minimize': ic('Minimize'),
  'corner-down-left': ic('CornerDownLeft'),
  'corner-down-right': ic('CornerDownRight'),
};

export interface IconProps extends Omit<SVGAttributes<SVGElement>, 'stroke'> {
  name: keyof typeof iconMap;
  size?: number | string;
  stroke?: number;
  className?: string;
}

/**
 * Icon component that renders Tabler Icons by name
 * @param name - Icon name from the iconMap
 * @param size - Icon size (default: 24)
 * @param stroke - Stroke width (default: 1.5)
 * @param className - Additional CSS classes
 */
export const Icon = ({ name, size = 24, stroke = 1.5, className = '', ...props }: IconProps) => {
  const IconComponent = iconMap[name];

  if (!IconComponent) {
    console.warn(`Icon not found: ${name}. Available icons: ${Object.keys(iconMap).slice(0, 10).join(', ')}...`);
    return (
      <span
        className={`inline-flex items-center justify-center text-xs ${className}`}
        style={{ width: size, height: size }}
        {...(props as HTMLAttributes<HTMLSpanElement>)}
      >
        ?
      </span>
    );
  }

  return (
    <IconComponent
      size={size}
      strokeWidth={stroke}
      className={className}
      {...props}
    />
  );
};

export default Icon;
