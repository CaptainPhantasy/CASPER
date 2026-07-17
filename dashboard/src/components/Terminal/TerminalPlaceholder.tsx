import * as React from 'react';
import { Icon } from '../icons/IconMapping';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface TerminalPlaceholderProps {
  className?: string;
}

export const TerminalPlaceholder: React.FC<TerminalPlaceholderProps> = ({
  className,
}) => {
  return (
    <div className={className}>
      <Card className="h-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Icon name="terminal" className="h-5 w-5" />
            Terminal
          </CardTitle>
          <CardDescription>
            Interactive terminal with CASPER CLI integration
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center justify-center h-full space-y-4">
          <div className="text-center">
            <Icon name="terminal" className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-lg font-medium">Terminal Coming Soon</p>
            <p className="text-sm text-muted-foreground mb-4">
              Full XTerm.js integration with WebSocket backend will be available here
            </p>
            <Button variant="outline" disabled>
              Launch Terminal
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};