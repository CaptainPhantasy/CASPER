import React from 'react';
import { Icon } from './icons/IconMapping';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';

interface LLMProvider {
  id: string;
  name: string;
  model: string;
  available: boolean;
  icon?: string;
}

const providers: LLMProvider[] = [
  {
    id: 'anthropic',
    name: 'Claude 3 Opus',
    model: 'claude-3-opus-20240229',
    available: true,
    icon: '🤖'
  },
  {
    id: 'openai',
    name: 'GPT-4 Turbo',
    model: 'gpt-4-turbo-preview',
    available: true,
    icon: '🧠'
  },
  {
    id: 'openai-gpt35',
    name: 'GPT-3.5 Turbo',
    model: 'gpt-3.5-turbo',
    available: true,
    icon: '⚡'
  },
  {
    id: 'local',
    name: 'Local LLM',
    model: 'llama-2-70b',
    available: false,
    icon: '🏠'
  }
];

interface LLMSelectorProps {
  className?: string;
}

export function LLMSelector({ className }: LLMSelectorProps) {
  const [selectedProvider, setSelectedProvider] = React.useState(providers[0]);
  const { toast } = useToast();

  const selectProvider = (provider: LLMProvider) => {
    if (!provider.available) {
      toast({
        title: "Provider Unavailable",
        description: `${provider.name} is not currently available`,
        variant: "destructive",
      });
      return;
    }

    setSelectedProvider(provider);

    // Store in localStorage for persistence
    localStorage.setItem('llm_provider', provider.id);

    toast({
      title: "LLM Provider Changed",
      description: `Now using ${provider.name}`,
    });

    // TODO: Update backend API to use new provider
    fetch('/api/settings/llm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider: provider.id, model: provider.model })
    }).catch(err => console.error('Failed to update LLM provider:', err));
  };

  // Load saved provider on mount
  React.useEffect(() => {
    const savedProviderId = localStorage.getItem('llm_provider');
    if (savedProviderId) {
      const provider = providers.find(p => p.id === savedProviderId);
      if (provider && provider.available) {
        setSelectedProvider(provider);
      }
    }
  }, []);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className={`h-7 gap-1 text-xs ${className}`}>
          <Icon name="brain" className="h-3 w-3" />
          <span className="hidden sm:inline">{selectedProvider.name}</span>
          <span className="sm:hidden">{selectedProvider.icon}</span>
          <Icon name="chevron-down" className="h-3 w-3 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <div className="px-2 py-1.5 text-xs font-medium text-muted-foreground">
          AI Provider
        </div>
        <DropdownMenuSeparator />
        {providers.map((provider) => (
          <DropdownMenuItem
            key={provider.id}
            onClick={() => selectProvider(provider)}
            disabled={!provider.available}
            className="flex items-center justify-between"
          >
            <div className="flex items-center gap-2">
              <span className="text-base">{provider.icon}</span>
              <div className="flex flex-col">
                <span className="text-sm">{provider.name}</span>
                <span className="text-xs text-muted-foreground">{provider.model}</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {!provider.available && (
                <Badge variant="outline" className="text-[10px] px-1">
                  Unavailable
                </Badge>
              )}
              {selectedProvider.id === provider.id && (
                <Icon name="check" className="h-3 w-3" />
              )}
            </div>
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <div className="px-2 py-1.5 text-xs text-muted-foreground">
          {selectedProvider.available ? '✅ Connected' : '❌ Disconnected'}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}