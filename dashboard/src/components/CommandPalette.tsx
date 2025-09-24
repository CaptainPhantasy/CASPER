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
import { searchWorkspace } from '@/services/api';
import { FileSearch, Settings2, SquarePen, Wand2 } from 'lucide-react';

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

        <CommandSeparator />
        <CommandGroup heading="Agent tools">
          <CommandItem onSelect={() => { /* placeholder for future actions */ }} disabled>
            <Wand2 className="mr-2 h-4 w-4" />
            Spawn worker agent (coming soon)
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
