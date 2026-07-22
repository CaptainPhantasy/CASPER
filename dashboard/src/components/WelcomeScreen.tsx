import { Icon } from './icons/IconMapping';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface WelcomeScreenProps {
  onAction?: (action: string) => void;
  className?: string;
}

export function WelcomeScreen({ onAction, className }: WelcomeScreenProps) {
  const quickActions = [
    {
      icon: 'folder-open',
      title: 'Open Folder',
      description: 'Browse and open a project folder',
      action: 'open-folder',
      color: 'text-blue-500'
    },
    {
      icon: 'file-text',
      title: 'New File',
      description: 'Create a new file in the workspace',
      action: 'new-file',
      shortcut: 'Ctrl+N',
      color: 'text-green-500'
    },
    {
      icon: 'terminal',
      title: 'Open Terminal',
      description: 'Launch Omega-secured terminal',
      action: 'open-terminal',
      shortcut: 'Ctrl+`',
      color: 'text-purple-500'
    },
    {
      icon: 'search',
      title: 'Search Files',
      description: 'Find files in your workspace',
      action: 'search',
      shortcut: 'Ctrl+P',
      color: 'text-orange-500'
    }
  ];


  return (
    <div className={cn('flex h-full items-center justify-center p-8', className)}>
      <div className="w-full max-w-4xl space-y-8">
        {/* Hero Section */}
        <div className="text-center space-y-4">
          <div className="flex justify-center">
            <div className="relative">
              <Icon name="code" className="h-16 w-16 text-primary" />
              <Icon name="shield" className="absolute -bottom-1 -right-1 h-8 w-8 text-green-500" />
            </div>
          </div>
          <h1 className="text-4xl font-bold">Welcome to CASPER IDE</h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Enterprise-grade development environment with Omega security layer and AI-powered assistance
          </p>
        </div>

        {/* Quick Actions */}
        <div>
          <h2 className="text-lg font-semibold mb-4">Quick Start</h2>
          <div className="grid grid-cols-2 gap-4">
            {quickActions.map((action) => (
              <Card
                key={action.action}
                className="group cursor-pointer transition-all hover:shadow-lg hover:scale-[1.02]"
                onClick={() => onAction?.(action.action)}
              >
                <CardHeader className="flex flex-row items-center gap-4 pb-2">
                  <div className={cn('p-2 rounded-lg bg-card', action.color)}>
                    <Icon name={action.icon} className="h-5 w-5" />
                  </div>
                  <div className="flex-1">
                    <CardTitle className="text-base flex items-center justify-between">
                      {action.title}
                      {action.shortcut && (
                        <Badge variant="secondary" className="ml-2 font-mono text-xs">
                          {action.shortcut}
                        </Badge>
                      )}
                    </CardTitle>
                    <CardDescription className="text-sm mt-1">
                      {action.description}
                    </CardDescription>
                  </div>
                  <Icon name="arrow-right" className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
                </CardHeader>
              </Card>
            ))}
          </div>
        </div>


        {/* Recent Files */}
        <div>
          <h2 className="text-lg font-semibold mb-4">Recent Files</h2>
          <Card className="border-muted">
            <CardContent className="pt-6">
              <div className="text-center py-8 text-muted-foreground">
                <Icon name="file-text" className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p className="text-sm">No recent files</p>
                <p className="text-xs mt-1">Open a file to see it here</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Keyboard Shortcuts */}
        <div className="text-center text-xs text-muted-foreground">
          <p>
            Press <Badge variant="outline" className="mx-1">Ctrl+K</Badge> for command palette
            <span className="mx-2">•</span>
            <Badge variant="outline" className="mx-1">Ctrl+Shift+P</Badge> for all commands
            <span className="mx-2">•</span>
            <Badge variant="outline" className="mx-1">F1</Badge> for help
          </p>
        </div>
      </div>
    </div>
  );
}
