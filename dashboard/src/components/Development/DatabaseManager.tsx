import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  IconDatabase as Database,
  IconPlayerPlay as Play,
  IconRefresh as RefreshCw,
  IconCircleCheck as CheckCircle,
  IconAlertCircle as AlertCircle,
  IconClock as Clock,
  IconArrowUp as ArrowUp,
  IconArrowDown as ArrowDown,
  IconLoader2 as Loader2,
  IconPlant as Sprout,
} from "@tabler/icons-react";
import { cn } from "@/lib/utils";
import { API_BASE } from "@/services/api";

interface Migration {
  id: string;
  name: string;
  version: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  appliedAt?: string;
  executionTime?: number;
  description?: string;
}

interface SeedData {
  id: string;
  name: string;
  description: string;
  status: 'available' | 'running' | 'completed' | 'failed';
  lastRun?: string;
  recordCount?: number;
}

interface DatabaseStatus {
  connected: boolean;
  schema_version: string;
  pending_migrations: number;
  last_migration?: string;
  connection_pool?: {
    active: number;
    idle: number;
    total: number;
  };
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'running':
      return <Loader2 className="h-3 w-3 animate-spin" />;
    case 'completed':
      return <CheckCircle className="h-3 w-3 text-green-500" />;
    case 'failed':
      return <AlertCircle className="h-3 w-3 text-red-500" />;
    case 'pending':
    case 'available':
      return <Clock className="h-3 w-3 text-muted-foreground" />;
    default:
      return <Database className="h-3 w-3" />;
  }
};

const getStatusBadgeVariant = (status: string): "default" | "secondary" | "outline" | "destructive" => {
  switch (status) {
    case 'running':
      return 'default';
    case 'completed':
      return 'secondary';
    case 'failed':
      return 'destructive';
    case 'pending':
    case 'available':
    default:
      return 'outline';
  }
};

export const DatabaseManager: React.FC = () => {
  const [dbStatus, setDbStatus] = React.useState<DatabaseStatus | null>(null);
  const [migrations, setMigrations] = React.useState<Migration[]>([]);
  const [seedData, setSeedData] = React.useState<SeedData[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [selectedEnvironment, setSelectedEnvironment] = React.useState("development");
  const [migrationTarget, setMigrationTarget] = React.useState("");
  const [operation, setOperation] = React.useState<'migrate' | 'rollback' | 'seed' | null>(null);

  // Fetch database status and migration info
  const fetchDatabaseInfo = React.useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [statusRes, migrationsRes, seedRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/dev/database/status`),
        fetch(`${API_BASE}/api/dev/database/migrations`),
        fetch(`${API_BASE}/api/dev/database/seeds`)
      ]);

      if (statusRes.status === 'fulfilled' && statusRes.value.ok) {
        const status = await statusRes.value.json();
        setDbStatus(status);
      }

      if (migrationsRes.status === 'fulfilled' && migrationsRes.value.ok) {
        const migrationData = await migrationsRes.value.json();
        setMigrations(migrationData.migrations || []);
      }

      if (seedRes.status === 'fulfilled' && seedRes.value.ok) {
        const seedInfo = await seedRes.value.json();
        setSeedData(seedInfo.seeds || []);
      }

    } catch (err) {
      console.error('Error fetching database info:', err);
      setError('Failed to connect to database service');
    } finally {
      setLoading(false);
    }
  }, []);

  // Execute migration operation
  const executeMigration = React.useCallback(async (action: 'up' | 'down', target?: string) => {
    try {
      setOperation('migrate');
      setError(null);

      const body: any = { action, environment: selectedEnvironment };
      if (target) body.target = target;

      const res = await fetch(`${API_BASE}/api/dev/migrate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        throw new Error(`Migration failed: ${res.statusText}`);
      }

      const result = await res.json();

      // Refresh data after successful migration
      await fetchDatabaseInfo();

      if (result.error) {
        setError(result.error);
      }

    } catch (err) {
      console.error('Migration error:', err);
      setError(err instanceof Error ? err.message : 'Migration failed');
    } finally {
      setOperation(null);
    }
  }, [selectedEnvironment, fetchDatabaseInfo]);

  // Execute seed operation
  const executeSeed = React.useCallback(async (seedName?: string) => {
    try {
      setOperation('seed');
      setError(null);

      const body: any = { environment: selectedEnvironment };
      if (seedName) body.seed = seedName;

      const res = await fetch(`${API_BASE}/api/dev/seed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        throw new Error(`Seeding failed: ${res.statusText}`);
      }

      const result = await res.json();

      // Refresh data after successful seeding
      await fetchDatabaseInfo();

      if (result.error) {
        setError(result.error);
      }

    } catch (err) {
      console.error('Seed error:', err);
      setError(err instanceof Error ? err.message : 'Seeding failed');
    } finally {
      setOperation(null);
    }
  }, [selectedEnvironment, fetchDatabaseInfo]);

  // Load initial data
  React.useEffect(() => {
    fetchDatabaseInfo();
  }, [fetchDatabaseInfo]);

  return (
    <div className="space-y-4">
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Database Status Card */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Database className="h-4 w-4 text-blue-500" />
              Database Status
            </CardTitle>
            <div className="flex items-center gap-2">
              <Badge variant={dbStatus?.connected ? "secondary" : "destructive"} className="gap-1">
                {dbStatus?.connected ? (
                  <CheckCircle className="h-3 w-3" />
                ) : (
                  <AlertCircle className="h-3 w-3" />
                )}
                {dbStatus?.connected ? 'Connected' : 'Disconnected'}
              </Badge>
              <Button
                size="sm"
                variant="outline"
                onClick={fetchDatabaseInfo}
                disabled={loading}
              >
                <RefreshCw className={cn("h-3 w-3", loading && "animate-spin")} />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {dbStatus && (
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Schema Version</p>
                <p className="text-sm font-medium">{dbStatus.schema_version || 'Unknown'}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Pending Migrations</p>
                <p className="text-sm font-medium">
                  {dbStatus.pending_migrations || 0}
                </p>
              </div>
              {dbStatus.connection_pool && (
                <>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Active Connections</p>
                    <p className="text-sm font-medium">
                      {dbStatus.connection_pool.active}/{dbStatus.connection_pool.total}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Last Migration</p>
                    <p className="text-sm font-medium">
                      {dbStatus.last_migration || 'None'}
                    </p>
                  </div>
                </>
              )}
            </div>
          )}

          <Separator />

          {/* Environment Selection */}
          <div className="flex items-center gap-4">
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Environment</p>
              <Select value={selectedEnvironment} onValueChange={setSelectedEnvironment}>
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="development">Development</SelectItem>
                  <SelectItem value="testing">Testing</SelectItem>
                  <SelectItem value="staging">Staging</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Migration Management Card */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <ArrowUp className="h-4 w-4 text-blue-500" />
              Migration Management
            </CardTitle>
            <div className="flex items-center gap-2">
              <Input
                placeholder="Target version (optional)"
                value={migrationTarget}
                onChange={(e) => setMigrationTarget(e.target.value)}
                className="w-40"
              />
              <Button
                size="sm"
                onClick={() => executeMigration('up', migrationTarget || undefined)}
                disabled={operation === 'migrate' || !dbStatus?.connected}
              >
                {operation === 'migrate' ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <ArrowUp className="h-3 w-3" />
                )}
                Migrate Up
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => executeMigration('down', migrationTarget || undefined)}
                disabled={operation === 'migrate' || !dbStatus?.connected}
              >
                <ArrowDown className="h-3 w-3" />
                Rollback
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <ScrollArea className="h-[200px]">
            <div className="p-4 space-y-2">
              {migrations.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No migrations found
                </p>
              ) : (
                migrations.map((migration) => (
                  <div
                    key={migration.id}
                    className={cn(
                      "flex items-center justify-between gap-2 p-2 rounded-sm hover:bg-accent/50 transition-colors",
                      migration.status === 'failed' && "bg-destructive/5"
                    )}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium">{migration.name}</span>
                        <Badge variant="outline" className="text-xs">
                          v{migration.version}
                        </Badge>
                      </div>
                      {migration.description && (
                        <p className="text-xs text-muted-foreground mt-1 truncate">
                          {migration.description}
                        </p>
                      )}
                      {migration.appliedAt && (
                        <p className="text-xs text-muted-foreground">
                          Applied: {new Date(migration.appliedAt).toLocaleString()}
                          {migration.executionTime && ` (${migration.executionTime}ms)`}
                        </p>
                      )}
                    </div>
                    <Badge variant={getStatusBadgeVariant(migration.status)} className="gap-1">
                      {getStatusIcon(migration.status)}
                      {migration.status}
                    </Badge>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Seed Data Management Card */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Sprout className="h-4 w-4 text-blue-500" />
              Seed Data Management
            </CardTitle>
            <Button
              size="sm"
              onClick={() => executeSeed()}
              disabled={operation === 'seed' || !dbStatus?.connected}
            >
              {operation === 'seed' ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Play className="h-3 w-3" />
              )}
              Run All Seeds
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <ScrollArea className="h-[200px]">
            <div className="p-4 space-y-2">
              {seedData.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No seed data available
                </p>
              ) : (
                seedData.map((seed) => (
                  <div
                    key={seed.id}
                    className={cn(
                      "flex items-center justify-between gap-2 p-2 rounded-sm hover:bg-accent/50 transition-colors",
                      seed.status === 'failed' && "bg-destructive/5"
                    )}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium">{seed.name}</span>
                        {seed.recordCount && (
                          <Badge variant="outline" className="text-xs">
                            {seed.recordCount} records
                          </Badge>
                        )}
                      </div>
                      {seed.description && (
                        <p className="text-xs text-muted-foreground mt-1 truncate">
                          {seed.description}
                        </p>
                      )}
                      {seed.lastRun && (
                        <p className="text-xs text-muted-foreground">
                          Last run: {new Date(seed.lastRun).toLocaleString()}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={getStatusBadgeVariant(seed.status)} className="gap-1">
                        {getStatusIcon(seed.status)}
                        {seed.status}
                      </Badge>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => executeSeed(seed.name)}
                        disabled={operation === 'seed' || !dbStatus?.connected}
                      >
                        <Play className="h-2.5 w-2.5" />
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
};
