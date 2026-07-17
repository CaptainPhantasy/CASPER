import * as React from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { SettingsPayload } from '@/types';
import { getSettings, updateSettings } from '@/services/api';
import { Icon } from './icons/IconMapping';

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
  const [settings, setSettings] = React.useState<SettingsPayload | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const original = React.useRef<SettingsPayload | null>(null);

  const loadSettings = React.useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const snapshot = await getSettings();
      setSettings(snapshot);
      original.current = snapshot;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load settings');
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    if (open) {
      void loadSettings();
    } else {
      setError(null);
      setSaving(false);
    }
  }, [open, loadSettings]);

  const mutate = <K extends keyof SettingsPayload>(section: K, key: string, value: unknown) => {
    setSettings((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        [section]: {
          ...prev[section],
          [key]: value,
        },
      };
    });
  };

  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    setError(null);
    try {
      const snapshot = await updateSettings(settings);
      setSettings(snapshot);
      original.current = snapshot;
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const hasChanges = React.useMemo(() => {
    if (!settings || !original.current) return false;
    return JSON.stringify(settings) !== JSON.stringify(original.current);
  }, [settings]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Icon name="settings" className="h-4 w-4" />
            Workspace settings
          </DialogTitle>
          <DialogDescription>
            Configure agent behaviour, workflow safeguards, and repository preferences.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <Alert variant="destructive" className="mb-4">
            <AlertTitle>Settings error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {loading || !settings ? (
          <div className="flex items-center justify-center py-16 text-muted-foreground">
            <Icon name="loader-2" className="h-5 w-5 animate-spin" />
            <span className="ml-2 text-sm">Loading settings…</span>
          </div>
        ) : (
          <Tabs defaultValue="general" className="space-y-4">
            <TabsList>
              <TabsTrigger value="general">General</TabsTrigger>
              <TabsTrigger value="agents">Agents</TabsTrigger>
              <TabsTrigger value="repository">Repository</TabsTrigger>
            </TabsList>

            <TabsContent value="general" className="space-y-4">
              <div className="flex items-center justify-between rounded-md border border-border/60 bg-muted/30 p-4">
                <div>
                  <p className="text-sm font-medium">Auto launch dashboard</p>
                  <p className="text-xs text-muted-foreground">Start the IDE whenever CASPER Prime boots.</p>
                </div>
                <Switch
                  id="auto-launch"
                  checked={Boolean(settings.general.auto_launch_dashboard)}
                  onCheckedChange={(checked) => mutate('general', 'auto_launch_dashboard', checked)}
                />
              </div>

              <div className="flex items-center justify-between rounded-md border border-border/60 bg-muted/30 p-4">
                <div>
                  <p className="text-sm font-medium">Confirm destructive operations</p>
                  <p className="text-xs text-muted-foreground">Require human approval before risky edits or deletes.</p>
                </div>
                <Switch
                  id="confirm-actions"
                  checked={Boolean(settings.general.confirm_destructive_actions)}
                  onCheckedChange={(checked) => mutate('general', 'confirm_destructive_actions', checked)}
                />
              </div>

              <div className="flex items-center justify-between rounded-md border border-border/60 bg-muted/30 p-4">
                <div>
                  <p className="text-sm font-medium">Share anonymous telemetry</p>
                  <p className="text-xs text-muted-foreground">Help improve CASPER Prime by sending usage signals.</p>
                </div>
                <Switch
                  id="telemetry"
                  checked={Boolean(settings.general.telemetry_opt_in)}
                  onCheckedChange={(checked) => mutate('general', 'telemetry_opt_in', checked)}
                />
              </div>
            </TabsContent>

            <TabsContent value="agents" className="space-y-4">
              <div className="flex items-center justify-between gap-4 rounded-md border border-border/60 bg-muted/30 p-4">
                <div>
                  <p className="text-sm font-medium">Max parallel agents</p>
                  <p className="text-xs text-muted-foreground">Limit concurrent workers to control resource usage.</p>
                </div>
                <Input
                  id="parallel-agents"
                  type="number"
                  min={1}
                  value={Number(settings.agents.max_parallel_agents ?? 4)}
                  onChange={(event) => mutate('agents', 'max_parallel_agents', Number(event.target.value))}
                  className="w-24"
                />
              </div>

              <div className="flex items-center justify-between gap-4 rounded-md border border-border/60 bg-muted/30 p-4">
                <div>
                  <p className="text-sm font-medium">Default task priority</p>
                  <p className="text-xs text-muted-foreground">Used when no explicit priority is supplied.</p>
                </div>
                <Input
                  id="default-priority"
                  value={String(settings.agents.default_priority ?? 'medium')}
                  onChange={(event) => mutate('agents', 'default_priority', event.target.value)}
                  className="w-32 uppercase"
                />
              </div>

              <div className="flex items-center justify-between rounded-md border border-border/60 bg-muted/30 p-4">
                <div>
                  <p className="text-sm font-medium">Allow DevOps operations</p>
                  <p className="text-xs text-muted-foreground">Enable deployment and infrastructure changes.</p>
                </div>
                <Switch
                  id="devops-ops"
                  checked={Boolean(settings.agents.allow_devops_operations)}
                  onCheckedChange={(checked) => mutate('agents', 'allow_devops_operations', checked)}
                />
              </div>
            </TabsContent>

            <TabsContent value="repository" className="space-y-4">
              <div className="space-y-2 rounded-md border border-border/60 bg-muted/30 p-4">
                <p className="text-sm font-medium">Ignored patterns</p>
                <Textarea
                  id="ignored"
                  rows={4}
                  value={(settings.repository.ignored_patterns || []).join('\n')}
                  onChange={(event) =>
                    mutate(
                      'repository',
                      'ignored_patterns',
                      event.target.value
                        .split('\n')
                        .map((line) => line.trim())
                        .filter(Boolean),
                    )
                  }
                />
                <p className="text-xs text-muted-foreground">One glob per line. Directories and files listed here are hidden from agents.</p>
              </div>

              <div className="flex items-center justify-between rounded-md border border-border/60 bg-muted/30 p-4">
                <div>
                  <p className="text-sm font-medium">Auto format patches</p>
                  <p className="text-xs text-muted-foreground">Apply project formatters before presenting changes.</p>
                </div>
                <Switch
                  id="auto-format"
                  checked={Boolean(settings.repository.auto_format_on_apply)}
                  onCheckedChange={(checked) => mutate('repository', 'auto_format_on_apply', checked)}
                />
              </div>

              <div className="flex items-center justify-between rounded-md border border-border/60 bg-muted/30 p-4">
                <div>
                  <p className="text-sm font-medium">Require human approval</p>
                  <p className="text-xs text-muted-foreground">Force a human review before applying generated edits.</p>
                </div>
                <Switch
                  id="hil-required"
                  checked={Boolean(settings.repository.require_human_approval)}
                  onCheckedChange={(checked) => mutate('repository', 'require_human_approval', checked)}
                />
              </div>
            </TabsContent>
          </Tabs>
        )}

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={!hasChanges || saving || !settings}>
            {saving ? 'Saving…' : 'Save changes'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
