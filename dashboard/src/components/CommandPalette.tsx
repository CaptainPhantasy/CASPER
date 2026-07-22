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
import { Icon } from './icons/IconMapping';

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
  category: 'business' | 'development' | 'productivity' | 'ai' | 'testing' | 'utility' | 'emergency';
  icon: string;
  shortcut?: string;
  action: () => void | Promise<void>;
}

interface CommandGroupDefinition {
  category: 'business' | 'development' | 'productivity' | 'ai' | 'testing' | 'utility' | 'emergency';
  title: string;
  color: string;
  commands: Command[];
}

// Define all 49+ command categories as per CASPER terminal specifications
const createCommandGroups = (): CommandGroupDefinition[] => {
  const executeCommand = async (commandId: string, params?: any) => {
    try {
      console.log(`Executing command: ${commandId}`, params);

      // Execute command via appropriate API endpoint
      let response;
      const endpoint = getCommandEndpoint(commandId);

      if (endpoint) {
        response = await fetch(`${API_BASE}${endpoint}`, {
          method: endpoint.includes('logs') || endpoint.includes('status') ? 'GET' : 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: endpoint.includes('logs') || endpoint.includes('status') ? undefined : JSON.stringify(params || {}),
        });
      } else {
        console.warn(`Unknown command: ${commandId}`);
        return;
      }

      if (response && !response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = response ? await response.json().catch(() => ({})) : {};
      console.log(`Command ${commandId} completed:`, result);

    } catch (error) {
      console.error(`Command execution failed for ${commandId}:`, error);
      throw error;
    }
  };

  // Map commands to their API endpoints
  const getCommandEndpoint = (commandId: string): string | null => {
    const endpointMap: Record<string, string> = {
      // Core Commands
      'task': '/api/task',
      'analyze': '/api/analyze',
      'status': '/api/status',
      'approve': '/api/approve',

      // Business Commands
      'proposal': '/api/business/proposal',
      'invoice': '/api/business/invoice',
      'contract': '/api/business/contract',
      'quote': '/api/business/quote',
      'timesheet': '/api/business/timesheet',
      'estimate': '/api/business/estimate',

      // Development Commands
      'create': '/api/dev/create',
      'test': '/api/dev/test',
      'debug': '/api/dev/debug',
      'review': '/api/dev/review',
      'refactor': '/api/dev/refactor',
      'init': '/api/dev/init',
      'build': '/api/dev/build',
      'deploy': '/api/dev/deploy',
      'rollback': '/api/dev/rollback',
      'migrate': '/api/dev/migrate',
      'generate': '/api/dev/generate',
      'scaffold': '/api/dev/scaffold',
      'optimize': '/api/dev/optimize',
      'profile': '/api/dev/profile',
      'scan': '/api/dev/scan',
      'lint': '/api/dev/lint',
      'api-gen': '/api/dev/api-gen',
      'logs': '/api/dev/logs',

      // AI Commands
      'ai-review': '/api/ai/review',
      'ai-complete': '/api/ai/complete',
      'ai-explain': '/api/ai/explain',
      'ai-suggest': '/api/ai/suggest',
      'ai-translate': '/api/ai/translate',

      // Testing Commands
      'unit-test': '/api/test/unit',
      'integration-test': '/api/test/integration',
      'e2e-test': '/api/test/e2e',
      'load-test': '/api/test/load',
      'security-test': '/api/test/security',

      // Utility Commands
      'search': '/api/utility/search',
      'replace': '/api/utility/replace',
      'format': '/api/utility/format',
      'clean': '/api/utility/clean',
      'backup': '/api/utility/backup',
      'restore': '/api/utility/restore',
      'export': '/api/utility/export',
      'import': '/api/utility/import',
      'sync': '/api/utility/sync',

      // Productivity Commands
      'focus': '/api/productivity/focus',
      'notes': '/api/productivity/notes',
      'til': '/api/productivity/til',

      // Emergency Commands
      'panic': '/api/emergency/panic',
      'hotfix': '/api/emergency/hotfix'
    };

    return endpointMap[commandId] || null;
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
          icon: 'file-text',
          shortcut: 'Ctrl+P',
          action: () => executeCommand('proposal')
        },
        {
          id: 'estimate',
          label: 'Create Estimate',
          description: 'Project cost and timeline estimation',
          category: 'business',
          icon: 'calculator',
          action: () => executeCommand('estimate')
        },
        {
          id: 'invoice',
          label: 'Generate Invoice',
          description: 'Professional invoice generation',
          category: 'business',
          icon: 'credit-card',
          action: () => executeCommand('invoice')
        },
        {
          id: 'contract',
          label: 'Draft Contract',
          description: 'Generate legal contracts',
          category: 'business',
          icon: 'file-text',
          action: () => executeCommand('contract')
        },
        {
          id: 'quote',
          label: 'Generate Quote',
          description: 'Create project quotes',
          category: 'business',
          icon: 'receipt',
          action: () => executeCommand('quote')
        },
        {
          id: 'timesheet',
          label: 'Manage Timesheet',
          description: 'Time tracking and logging',
          category: 'business',
          icon: 'clock',
          action: () => executeCommand('timesheet')
        }
      ]
    },
    {
      category: 'development',
      title: 'Development Tools',
      color: 'text-blue-500',
      commands: [
        {
          id: 'create',
          label: 'Create Components',
          description: 'Generate new code components',
          category: 'development',
          icon: 'code',
          action: () => executeCommand('create')
        },
        {
          id: 'test',
          label: 'Run Tests',
          description: 'Execute test suites',
          category: 'development',
          icon: 'test-tube',
          shortcut: 'Ctrl+T',
          action: () => executeCommand('test')
        },
        {
          id: 'debug',
          label: 'Debug Code',
          description: 'Debug application issues',
          category: 'development',
          icon: 'bug',
          action: () => executeCommand('debug')
        },
        {
          id: 'review',
          label: 'Code Review',
          description: 'Review code changes',
          category: 'development',
          icon: 'eye',
          action: () => executeCommand('review')
        },
        {
          id: 'refactor',
          label: 'Refactor Code',
          description: 'Improve code structure',
          category: 'development',
          icon: 'refresh-cw',
          action: () => executeCommand('refactor')
        },
        {
          id: 'init',
          label: 'Initialize Project',
          description: 'Set up new project',
          category: 'development',
          icon: 'cube',
          action: () => executeCommand('init')
        },
        {
          id: 'build',
          label: 'Build Project',
          description: 'Compile and build application',
          category: 'development',
          icon: 'cube',
          shortcut: 'Ctrl+B',
          action: () => executeCommand('build')
        },
        {
          id: 'deploy',
          label: 'Deploy Application',
          description: 'Deploy to production',
          category: 'development',
          icon: 'rocket',
          action: () => executeCommand('deploy')
        },
        {
          id: 'rollback',
          label: 'Rollback Deployment',
          description: 'Revert to previous version',
          category: 'development',
          icon: 'arrow-left',
          action: () => executeCommand('rollback')
        },
        {
          id: 'migrate',
          label: 'Database Migration',
          description: 'Run database migrations',
          category: 'development',
          icon: 'database',
          action: () => executeCommand('migrate')
        },
        {
          id: 'generate',
          label: 'Generate Code',
          description: 'Auto-generate code templates',
          category: 'development',
          icon: 'bolt',
          action: () => executeCommand('generate')
        },
        {
          id: 'scaffold',
          label: 'Scaffold Structure',
          description: 'Generate project scaffolding',
          category: 'development',
          icon: 'cube',
          action: () => executeCommand('scaffold')
        },
        {
          id: 'optimize',
          label: 'Optimize Code',
          description: 'Performance optimization',
          category: 'development',
          icon: 'trending-up',
          action: () => executeCommand('optimize')
        },
        {
          id: 'profile',
          label: 'Profile Performance',
          description: 'Analyze performance metrics',
          category: 'development',
          icon: 'trending-up',
          action: () => executeCommand('profile')
        },
        {
          id: 'scan',
          label: 'Security Scan',
          description: 'Vulnerability and security analysis',
          category: 'development',
          icon: 'shield-check',
          shortcut: 'Ctrl+Shift+S',
          action: () => executeCommand('scan')
        },
        {
          id: 'lint',
          label: 'Code Linting',
          description: 'Code quality and style analysis',
          category: 'development',
          icon: 'code',
          action: () => executeCommand('lint')
        },
        {
          id: 'api-gen',
          label: 'Generate API',
          description: 'Scaffold API endpoints',
          category: 'development',
          icon: 'cube',
          action: () => executeCommand('api-gen')
        },
        {
          id: 'logs',
          label: 'View Logs',
          description: 'System and application log analysis',
          category: 'development',
          icon: 'file-text',
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
          icon: 'clock',
          shortcut: 'Ctrl+F',
          action: () => executeCommand('focus')
        },
        {
          id: 'notes',
          label: 'Quick Notes',
          description: 'Contextual note-taking',
          category: 'productivity',
          icon: 'pencil',
          action: () => executeCommand('notes')
        },
        {
          id: 'til',
          label: 'Today I Learned',
          description: 'Knowledge capture and insights',
          category: 'productivity',
          icon: 'lightbulb',
          action: () => executeCommand('til')
        }
      ]
    },
    {
      category: 'ai',
      title: 'AI-Powered Tools',
      color: 'text-indigo-500',
      commands: [
        {
          id: 'ai-review',
          label: 'AI Code Review',
          description: 'Automated code analysis and suggestions',
          category: 'ai',
          icon: 'brain',
          action: () => executeCommand('ai-review')
        },
        {
          id: 'ai-complete',
          label: 'AI Code Completion',
          description: 'Intelligent code completion',
          category: 'ai',
          icon: 'sparkle',
          action: () => executeCommand('ai-complete')
        },
        {
          id: 'ai-explain',
          label: 'AI Code Explanation',
          description: 'Explain complex code segments',
          category: 'ai',
          icon: 'message-square',
          action: () => executeCommand('ai-explain')
        },
        {
          id: 'ai-suggest',
          label: 'AI Suggestions',
          description: 'Get AI-powered improvement suggestions',
          category: 'ai',
          icon: 'lightbulb',
          action: () => executeCommand('ai-suggest')
        },
        {
          id: 'ai-translate',
          label: 'AI Code Translation',
          description: 'Convert code between languages',
          category: 'ai',
          icon: 'language',
          action: () => executeCommand('ai-translate')
        }
      ]
    },
    {
      category: 'testing',
      title: 'Testing Suite',
      color: 'text-orange-500',
      commands: [
        {
          id: 'unit-test',
          label: 'Unit Tests',
          description: 'Run unit test suite',
          category: 'testing',
          icon: 'check-circle',
          action: () => executeCommand('unit-test')
        },
        {
          id: 'integration-test',
          label: 'Integration Tests',
          description: 'Run integration tests',
          category: 'testing',
          icon: 'workflow',
          action: () => executeCommand('integration-test')
        },
        {
          id: 'e2e-test',
          label: 'End-to-End Tests',
          description: 'Run E2E test suite',
          category: 'testing',
          icon: 'globe',
          action: () => executeCommand('e2e-test')
        },
        {
          id: 'load-test',
          label: 'Load Testing',
          description: 'Performance and load testing',
          category: 'testing',
          icon: 'trending-up',
          action: () => executeCommand('load-test')
        },
        {
          id: 'security-test',
          label: 'Security Testing',
          description: 'Security vulnerability testing',
          category: 'testing',
          icon: 'shield',
          action: () => executeCommand('security-test')
        }
      ]
    },
    {
      category: 'utility',
      title: 'Utility Tools',
      color: 'text-cyan-500',
      commands: [
        {
          id: 'search',
          label: 'Search Codebase',
          description: 'Search through project files',
          category: 'utility',
          icon: 'search',
          shortcut: 'Ctrl+Shift+F',
          action: () => executeCommand('search')
        },
        {
          id: 'replace',
          label: 'Find & Replace',
          description: 'Find and replace text across files',
          category: 'utility',
          icon: 'replace',
          action: () => executeCommand('replace')
        },
        {
          id: 'format',
          label: 'Format Code',
          description: 'Auto-format code files',
          category: 'utility',
          icon: 'palette',
          action: () => executeCommand('format')
        },
        {
          id: 'clean',
          label: 'Clean Project',
          description: 'Clean build artifacts and cache',
          category: 'utility',
          icon: 'trash',
          action: () => executeCommand('clean')
        },
        {
          id: 'backup',
          label: 'Backup Project',
          description: 'Create project backup',
          category: 'utility',
          icon: 'archive',
          action: () => executeCommand('backup')
        },
        {
          id: 'restore',
          label: 'Restore Backup',
          description: 'Restore from backup',
          category: 'utility',
          icon: 'rotate-ccw',
          action: () => executeCommand('restore')
        },
        {
          id: 'export',
          label: 'Export Data',
          description: 'Export project data',
          category: 'utility',
          icon: 'download',
          action: () => executeCommand('export')
        },
        {
          id: 'import',
          label: 'Import Data',
          description: 'Import external data',
          category: 'utility',
          icon: 'upload',
          action: () => executeCommand('import')
        },
        {
          id: 'sync',
          label: 'Sync Repositories',
          description: 'Synchronize with remote repositories',
          category: 'utility',
          icon: 'refresh-cw',
          action: () => executeCommand('sync')
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
          icon: 'alert-triangle',
          shortcut: 'Ctrl+Shift+P',
          action: () => executeCommand('panic')
        },
        {
          id: 'hotfix',
          label: 'Emergency Hotfix',
          description: 'Rapid issue resolution',
          category: 'emergency',
          icon: 'wrench',
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
            <Icon name="edit" className="mr-2 h-4 w-4" />
            Open workspace…
          </CommandItem>
          <CommandItem onSelect={() => { onOpenSettings(); onOpenChange(false); }}>
            <Icon name="settings" className="mr-2 h-4 w-4" />
            Open settings
          </CommandItem>
        </CommandGroup>

        {/* Show filtered commands when searching */}
        {filteredCommands.length > 0 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Commands">
              {filteredCommands.map((command) => {
                return (
                  <CommandItem
                    key={command.id}
                    value={command.id}
                    onSelect={() => handleCommandSelect(command)}
                  >
                    <Icon name={command.icon} className={`mr-2 h-4 w-4 ${
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
                  <Icon name="search" className="mr-2 h-4 w-4" />
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
                    return (
                      <CommandItem
                        key={command.id}
                        value={command.id}
                        onSelect={() => handleCommandSelect(command)}
                      >
                        <Icon name={command.icon} className={`mr-2 h-4 w-4 ${group.color}`} />
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
                <Icon name="sparkle" className="mr-2 h-4 w-4" />
                Spawn worker agent (coming soon)
              </CommandItem>
            </CommandGroup>
          </>
        )}
      </CommandList>
    </CommandDialog>
  );
}
