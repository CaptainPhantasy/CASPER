import * as React from 'react';
import {
  CommandDialog,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandEmpty,
  CommandSeparator,
} from '@/components/ui/command';
import { searchWorkspace, API_BASE } from '@/services/api';
import {
  FileSearch,
  Settings2,
  SquarePen,
  Wand2,
  // Business Commands
  FileText as DocumentText,
  Calculator,
  CreditCard,
  // Development Commands
  Database,
  ShieldCheck,
  Code2 as Code,
  Box as Cube,
  FileText,
  // Productivity Commands
  Clock,
  Edit as Pencil,
  Lightbulb,
  // Emergency Commands
  AlertTriangle,
  Wrench
} from 'lucide-react';

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onOpenFile: (path: string) => void;
  onOpenSettings: () => void;
  onOpenWorkspace: () => void;
}

interface SearchResult {
  path: string;
  name: string;
  size?: number;
  modified?: string;
}

interface Command {
  id: string;
  label: string;
  description: string;
  category: 'business' | 'development' | 'productivity' | 'emergency';
  icon: React.ComponentType<any>;
  shortcut?: string;
  action: () => void | Promise<void>;
}

interface CommandGroup {
  category: 'business' | 'development' | 'productivity' | 'emergency';
  title: string;
  color: string;
  commands: Command[];
}

// Define command categories as per UI.md specifications
const createCommandGroups = (): CommandGroup[] => {
  const executeCommand = async (commandId: string, params?: any) => {
    try {
      console.log(`Executing command: ${commandId}`, params);

      // Execute command via appropriate API endpoint
      let response;
      switch (commandId) {
        // Business Commands - integrate with /api/business/* endpoints
        case 'proposal':
          response = await fetch(`${API_BASE}/api/business/proposal`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params || {}),
          });
          break;
        case 'estimate':
          response = await fetch(`${API_BASE}/api/business/estimate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params || {}),
          });
          break;
        case 'invoice':
          response = await fetch(`${API_BASE}/api/business/invoice`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params || {}),
          });
          break;

        // Development Commands - integrate with /api/dev/* endpoints
        case 'migrate':
          response = await fetch(`${API_BASE}/api/dev/migrate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params || {}),
          });
          break;
        case 'seed':
          response = await fetch(`${API_BASE}/api/dev/seed`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params || {}),
          });
          break;
        case 'scan':
          response = await fetch(`${API_BASE}/api/dev/scan`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params || {}),
          });
          break;
        case 'lint':
          response = await fetch(`${API_BASE}/api/dev/lint`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params || {}),
          });
          break;
        case 'api-gen':
          response = await fetch(`${API_BASE}/api/dev/api-gen`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params || {}),
          });
          break;
        case 'logs':
          response = await fetch(`${API_BASE}/api/dev/logs`, {
            method: 'GET',
          });
          break;

        // Productivity Commands - integrate with /api/productivity/* endpoints
        case 'focus':
          response = await fetch(`${API_BASE}/api/productivity/focus`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params || {}),
          });
          break;
        case 'notes':
          response = await fetch(`${API_BASE}/api/productivity/notes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params || {}),
          });
          break;
        case 'til':
          response = await fetch(`${API_BASE}/api/productivity/til`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params || {}),
          });
          break;

        // Emergency Commands - integrate with /api/emergency/* endpoints
        case 'panic':
          response = await fetch(`${API_BASE}/api/emergency/panic`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params || {}),
          });
          break;
        case 'hotfix':
          response = await fetch(`${API_BASE}/api/emergency/hotfix`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params || {}),
          });
          break;

        default:
          console.warn(`Unknown command: ${commandId}`);
          return;
      }

      if (response && !response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = response ? await response.json().catch(() => ({})) : {};
      console.log(`Command ${commandId} completed:`, result);

      // TODO: Show success notification
      // toast.success(`${commandId} command completed successfully`);

    } catch (error) {
      console.error(`Command execution failed for ${commandId}:`, error);
      // TODO: Show error notification
      // toast.error(`${commandId} command failed: ${error.message}`);
      throw error;
    }
  };

  return [
    {
      category: 'business',
      title: 'Business Operations',
      color: 'text-emerald-500',
      commands: [
        {
          id: 'proposal',
          label: 'Generate Proposal',
          description: 'AI-powered project proposals',
          category: 'business',
          icon: DocumentText,
          shortcut: 'Ctrl+P',
          action: () => executeCommand('proposal')
        },
        {
          id: 'estimate',
          label: 'Create Estimate',
          description: 'Project cost and timeline estimation',
          category: 'business',
          icon: Calculator,
          action: () => executeCommand('estimate')
        },
        {
          id: 'invoice',
          label: 'Generate Invoice',
          description: 'Professional invoice generation',
          category: 'business',
          icon: CreditCard,
          action: () => executeCommand('invoice')
        }
      ]
    },
    {
      category: 'development',
      title: 'Development Tools',
      color: 'text-blue-500',
      commands: [
        {
          id: 'migrate',
          label: 'Database Migration',
          description: 'Run database migrations',
          category: 'development',
          icon: Database,
          action: () => executeCommand('migrate')
        },
        {
          id: 'seed',
          label: 'Seed Database',
          description: 'Populate database with test data',
          category: 'development',
          icon: Database,
          action: () => executeCommand('seed')
        },
        {
          id: 'scan',
          label: 'Security Scan',
          description: 'Vulnerability and security analysis',
          category: 'development',
          icon: ShieldCheck,
          shortcut: 'Ctrl+Shift+S',
          action: () => executeCommand('scan')
        },
        {
          id: 'lint',
          label: 'Code Linting',
          description: 'Code quality and style analysis',
          category: 'development',
          icon: Code,
          action: () => executeCommand('lint')
        },
        {
          id: 'api-gen',
          label: 'Generate API',
          description: 'Scaffold API endpoints',
          category: 'development',
          icon: Cube,
          action: () => executeCommand('api-gen')
        },
        {
          id: 'logs',
          label: 'View Logs',
          description: 'System and application log analysis',
          category: 'development',
          icon: FileText,
          action: () => executeCommand('logs')
        }
      ]
    },
    {
      category: 'productivity',
      title: 'Productivity Tools',
      color: 'text-purple-500',
      commands: [
        {
          id: 'focus',
          label: 'Start Focus Session',
          description: 'Pomodoro timer and focus mode',
          category: 'productivity',
          icon: Clock,
          shortcut: 'Ctrl+F',
          action: () => executeCommand('focus')
        },
        {
          id: 'notes',
          label: 'Quick Notes',
          description: 'Contextual note-taking',
          category: 'productivity',
          icon: Pencil,
          action: () => executeCommand('notes')
        },
        {
          id: 'til',
          label: 'Today I Learned',
          description: 'Knowledge capture and insights',
          category: 'productivity',
          icon: Lightbulb,
          action: () => executeCommand('til')
        }
      ]
    },
    {
      category: 'emergency',
      title: 'Emergency Operations',
      color: 'text-red-500',
      commands: [
        {
          id: 'panic',
          label: 'Panic Mode',
          description: 'Emergency system diagnostics',
          category: 'emergency',
          icon: AlertTriangle,
          shortcut: 'Ctrl+Shift+P',
          action: () => executeCommand('panic')
        },
        {
          id: 'hotfix',
          label: 'Emergency Hotfix',
          description: 'Rapid issue resolution',
          category: 'emergency',
          icon: Wrench,
          action: () => executeCommand('hotfix')
        }
      ]
    }
  ];
};

export function CommandPalette({
  open,
  onOpenChange,
  onOpenFile,
  onOpenSettings,
  onOpenWorkspace,
}: CommandPaletteProps) {
  const [query, setQuery] = React.useState('');
  const [results, setResults] = React.useState<SearchResult[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Initialize command groups
  const commandGroups = React.useMemo(() => createCommandGroups(), []);

  // Filter commands based on search query
  const filteredCommands = React.useMemo(() => {
    if (!query.trim()) return [];

    const searchTerm = query.toLowerCase().trim();
    const matchedCommands: Command[] = [];

    commandGroups.forEach(group => {
      group.commands.forEach(command => {
        if (
          command.label.toLowerCase().includes(searchTerm) ||
          command.description.toLowerCase().includes(searchTerm) ||
          command.id.toLowerCase().includes(searchTerm)
        ) {
          matchedCommands.push(command);
        }
      });
    });

    return matchedCommands;
  }, [query, commandGroups]);

  React.useEffect(() => {
    if (!open) {
      setQuery('');
      setResults([]);
      setError(null);
    }
  }, [open]);

  React.useEffect(() => {
    if (!query || query.trim().length < 2) {
      setResults([]);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    const timeout = setTimeout(async () => {
      try {
        const payload = await searchWorkspace(query.trim(), 15);
        if (cancelled) return;
        setResults(Array.isArray(payload?.results) ? payload.results : []);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Search failed');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 250);

    return () => {
      cancelled = true;
      clearTimeout(timeout);
    };
  }, [query]);

  const handleSelect = (value: string) => {
    onOpenFile(value);
    onOpenChange(false);
  };

  const handleCommandSelect = async (command: Command) => {
    try {
      await command.action();
      onOpenChange(false);
    } catch (error) {
      console.error('Command execution failed:', error);
    }
  };

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput
        value={query}
        onValueChange={setQuery}
        placeholder="Search files or run commands…"
      />
      <CommandList>
        <CommandEmpty>
          {loading ? 'Searching…' : error ? error : 'No results found'}
        </CommandEmpty>

        <CommandGroup heading="Quick actions">
          <CommandItem onSelect={() => { onOpenWorkspace(); onOpenChange(false); }}>
            <SquarePen className="mr-2 h-4 w-4" />
            Open workspace…
          </CommandItem>
          <CommandItem onSelect={() => { onOpenSettings(); onOpenChange(false); }}>
            <Settings2 className="mr-2 h-4 w-4" />
            Open settings
          </CommandItem>
        </CommandGroup>

        {/* Show filtered commands when searching */}
        {filteredCommands.length > 0 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Commands">
              {filteredCommands.map((command) => {
                const Icon = command.icon;
                return (
                  <CommandItem
                    key={command.id}
                    value={command.id}
                    onSelect={() => handleCommandSelect(command)}
                  >
                    <Icon className={`mr-2 h-4 w-4 ${
                      commandGroups.find(g => g.category === command.category)?.color || ''
                    }`} />
                    <div className="flex flex-col">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">{command.label}</span>
                        {command.shortcut && (
                          <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                            {command.shortcut}
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-muted-foreground">{command.description}</span>
                    </div>
                  </CommandItem>
                );
              })}
            </CommandGroup>
          </>
        )}

        {/* Show file search results */}
        {results.length > 0 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Files">
              {results.map((file) => (
                <CommandItem key={file.path} value={file.path} onSelect={handleSelect}>
                  <FileSearch className="mr-2 h-4 w-4" />
                  <div className="flex flex-col">
                    <span className="text-sm font-medium">{file.name}</span>
                    <span className="text-xs text-muted-foreground">{file.path}</span>
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}

        {/* Show command categories when no query */}
        {!query.trim() && (
          <>
            {commandGroups.map((group, index) => (
              <React.Fragment key={group.category}>
                {index > 0 && <CommandSeparator />}
                <CommandGroup heading={group.title}>
                  {group.commands.map((command) => {
                    const Icon = command.icon;
                    return (
                      <CommandItem
                        key={command.id}
                        value={command.id}
                        onSelect={() => handleCommandSelect(command)}
                      >
                        <Icon className={`mr-2 h-4 w-4 ${group.color}`} />
                        <div className="flex flex-col">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium">{command.label}</span>
                            {command.shortcut && (
                              <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                                {command.shortcut}
                              </span>
                            )}
                          </div>
                          <span className="text-xs text-muted-foreground">{command.description}</span>
                        </div>
                      </CommandItem>
                    );
                  })}
                </CommandGroup>
              </React.Fragment>
            ))}

            <CommandSeparator />
            <CommandGroup heading="Agent tools">
              <CommandItem onSelect={() => { /* placeholder for future actions */ }} disabled>
                <Wand2 className="mr-2 h-4 w-4" />
                Spawn worker agent (coming soon)
              </CommandItem>
            </CommandGroup>
          </>
        )}
      </CommandList>
    </CommandDialog>
  );
}
