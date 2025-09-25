import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Zap,
  Play,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  Clock,
  Loader2,
  FileText,
  Code,
  Database,
  Settings,
  Plus,
  Minus,
  Eye,
  Download,
  Copy,
  Server
} from "lucide-react";
import { cn } from "@/lib/utils";
import { API_BASE } from "@/services/api";

interface APIEndpoint {
  id: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  path: string;
  description: string;
  parameters?: {
    name: string;
    type: string;
    required: boolean;
    description?: string;
  }[];
  requestBody?: {
    type: string;
    properties: Record<string, any>;
  };
  responses?: {
    status: number;
    description: string;
    schema?: any;
  }[];
}

interface APISchema {
  id: string;
  name: string;
  description: string;
  version: string;
  endpoints: APIEndpoint[];
  models?: {
    name: string;
    properties: Record<string, any>;
  }[];
}

interface GenerationResult {
  id: string;
  started_at: string;
  completed_at?: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  generator_type: 'openapi' | 'rest' | 'graphql' | 'swagger';
  schema: APISchema;
  generated_files: {
    path: string;
    type: 'controller' | 'model' | 'route' | 'test' | 'documentation';
    content?: string;
  }[];
  progress?: number;
  duration?: number;
}

interface GeneratorStatus {
  available_generators: string[];
  recent_generations: number;
  total_endpoints_generated: number;
  supported_frameworks: string[];
  supported_languages: string[];
}

const getMethodColor = (method: string) => {
  switch (method) {
    case 'GET': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
    case 'POST': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
    case 'PUT': return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200';
    case 'DELETE': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
    case 'PATCH': return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
    default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
  }
};

const getFileTypeIcon = (type: string) => {
  switch (type) {
    case 'controller': return <Server className="h-3 w-3" />;
    case 'model': return <Database className="h-3 w-3" />;
    case 'route': return <Zap className="h-3 w-3" />;
    case 'test': return <CheckCircle className="h-3 w-3" />;
    case 'documentation': return <FileText className="h-3 w-3" />;
    default: return <Code className="h-3 w-3" />;
  }
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'running':
      return <Loader2 className="h-3 w-3 animate-spin" />;
    case 'completed':
      return <CheckCircle className="h-3 w-3 text-green-500" />;
    case 'failed':
      return <AlertCircle className="h-3 w-3 text-red-500" />;
    case 'cancelled':
      return <Clock className="h-3 w-3 text-muted-foreground" />;
    default:
      return <Clock className="h-3 w-3 text-muted-foreground" />;
  }
};

export const APIGenerator: React.FC = () => {
  const [generatorStatus, setGeneratorStatus] = React.useState<GeneratorStatus | null>(null);
  const [generationResults, setGenerationResults] = React.useState<GenerationResult[]>([]);
  const [currentGeneration, setCurrentGeneration] = React.useState<GenerationResult | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Form state
  const [schemaName, setSchemaName] = React.useState("");
  const [schemaDescription, setSchemaDescription] = React.useState("");
  const [schemaVersion, setSchemaVersion] = React.useState("1.0.0");
  const [generatorType, setGeneratorType] = React.useState("openapi");
  const [framework, setFramework] = React.useState("express");
  const [language, setLanguage] = React.useState("typescript");
  const [endpoints, setEndpoints] = React.useState<Partial<APIEndpoint>[]>([{
    method: 'GET',
    path: '/api/example',
    description: 'Example endpoint'
  }]);

  // Fetch generator status and history
  const fetchGeneratorInfo = React.useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [statusRes, historyRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/dev/api-gen/status`),
        fetch(`${API_BASE}/api/dev/api-gen/history`)
      ]);

      if (statusRes.status === 'fulfilled' && statusRes.value.ok) {
        const status = await statusRes.value.json();
        setGeneratorStatus(status);
      }

      if (historyRes.status === 'fulfilled' && historyRes.value.ok) {
        const history = await historyRes.value.json();
        setGenerationResults(history.results || []);

        // Check for active generation
        const activeGeneration = history.results?.find((result: GenerationResult) => result.status === 'running');
        if (activeGeneration) {
          setCurrentGeneration(activeGeneration);
        }
      }

    } catch (err) {
      console.error('Error fetching generator info:', err);
      setError('Failed to connect to API generator service');
    } finally {
      setLoading(false);
    }
  }, []);

  // Execute API generation
  const executeGeneration = React.useCallback(async () => {
    try {
      setError(null);

      // Validate required fields
      if (!schemaName.trim() || !schemaDescription.trim() || endpoints.length === 0) {
        setError('Please provide schema name, description, and at least one endpoint');
        return;
      }

      const schema: APISchema = {
        id: Date.now().toString(),
        name: schemaName,
        description: schemaDescription,
        version: schemaVersion,
        endpoints: endpoints.map(ep => ({
          ...ep,
          id: Date.now().toString() + Math.random()
        })) as APIEndpoint[]
      };

      const body = {
        generator_type: generatorType,
        framework: framework,
        language: language,
        schema: schema
      };

      const res = await fetch(`${API_BASE}/api/dev/api-gen`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        throw new Error(`API generation failed: ${res.statusText}`);
      }

      const result = await res.json();

      if (result.generation_id) {
        // Start polling for generation progress
        pollGenerationProgress(result.generation_id);
      }

      // Refresh data
      await fetchGeneratorInfo();

      if (result.error) {
        setError(result.error);
      }

    } catch (err) {
      console.error('Generation error:', err);
      setError(err instanceof Error ? err.message : 'API generation failed');
    }
  }, [schemaName, schemaDescription, schemaVersion, generatorType, framework, language, endpoints, fetchGeneratorInfo]);

  // Poll for generation progress
  const pollGenerationProgress = React.useCallback(async (generationId: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/dev/api-gen/${generationId}`);
        if (res.ok) {
          const generation = await res.json();
          setCurrentGeneration(generation);

          if (generation.status === 'completed' || generation.status === 'failed' || generation.status === 'cancelled') {
            clearInterval(interval);
            setCurrentGeneration(null);
            await fetchGeneratorInfo();
          }
        }
      } catch (error) {
        console.error('Error polling generation progress:', error);
        clearInterval(interval);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [fetchGeneratorInfo]);

  // Add endpoint
  const addEndpoint = () => {
    setEndpoints(prev => [...prev, {
      method: 'GET',
      path: '/api/new',
      description: 'New endpoint'
    }]);
  };

  // Remove endpoint
  const removeEndpoint = (index: number) => {
    setEndpoints(prev => prev.filter((_, i) => i !== index));
  };

  // Update endpoint
  const updateEndpoint = (index: number, field: string, value: any) => {
    setEndpoints(prev => prev.map((endpoint, i) =>
      i === index ? { ...endpoint, [field]: value } : endpoint
    ));
  };

  // Load initial data
  React.useEffect(() => {
    fetchGeneratorInfo();
  }, [fetchGeneratorInfo]);

  return (
    <div className="space-y-4">
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Generator Status Card */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Zap className="h-4 w-4 text-blue-500" />
              API Generator
            </CardTitle>
            <div className="flex items-center gap-2">
              <Badge variant={generatorStatus ? "secondary" : "destructive"} className="gap-1">
                <Server className="h-3 w-3" />
                {generatorStatus ? 'Ready' : 'Not Available'}
              </Badge>
              <Button
                size="sm"
                variant="outline"
                onClick={fetchGeneratorInfo}
                disabled={loading}
              >
                <RefreshCw className={cn("h-3 w-3", loading && "animate-spin")} />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {generatorStatus && (
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Recent Generations</p>
                <p className="text-sm font-medium">{generatorStatus.recent_generations}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Total Endpoints</p>
                <p className="text-sm font-medium">{generatorStatus.total_endpoints_generated}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Generators</p>
                <p className="text-sm font-medium">{generatorStatus.available_generators.length}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Frameworks</p>
                <p className="text-sm font-medium">{generatorStatus.supported_frameworks.length}</p>
              </div>
            </div>
          )}

          {/* Current Generation Progress */}
          {currentGeneration && (
            <>
              <Separator />
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium">Generation in progress...</p>
                  <Badge variant="default" className="gap-1">
                    {getStatusIcon(currentGeneration.status)}
                    {currentGeneration.generator_type}
                  </Badge>
                </div>
                {currentGeneration.progress !== undefined && (
                  <Progress value={currentGeneration.progress} className="h-2" />
                )}
                <p className="text-xs text-muted-foreground">
                  Schema: {currentGeneration.schema.name}
                  {currentGeneration.generated_files.length > 0 && ` • ${currentGeneration.generated_files.length} files`}
                </p>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* API Schema Builder */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">API Schema Builder</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Basic Schema Info */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-medium">Schema Name</label>
              <Input
                placeholder="My API"
                value={schemaName}
                onChange={(e) => setSchemaName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-medium">Version</label>
              <Input
                placeholder="1.0.0"
                value={schemaVersion}
                onChange={(e) => setSchemaVersion(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium">Description</label>
            <Textarea
              placeholder="Describe your API..."
              value={schemaDescription}
              onChange={(e) => setSchemaDescription(e.target.value)}
              rows={2}
            />
          </div>

          <Separator />

          {/* Generator Configuration */}
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-medium">Generator Type</label>
              <Select value={generatorType} onValueChange={setGeneratorType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(generatorStatus?.available_generators || ['openapi', 'swagger', 'rest']).map(type => (
                    <SelectItem key={type} value={type}>{type.toUpperCase()}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-medium">Framework</label>
              <Select value={framework} onValueChange={setFramework}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(generatorStatus?.supported_frameworks || ['express', 'fastapi', 'spring']).map(fw => (
                    <SelectItem key={fw} value={fw}>{fw}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-medium">Language</label>
              <Select value={language} onValueChange={setLanguage}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(generatorStatus?.supported_languages || ['typescript', 'python', 'java']).map(lang => (
                    <SelectItem key={lang} value={lang}>{lang}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <Separator />

          {/* Endpoints Configuration */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium">API Endpoints</label>
              <Button size="sm" variant="outline" onClick={addEndpoint}>
                <Plus className="h-3 w-3" />
                Add Endpoint
              </Button>
            </div>

            <ScrollArea className="h-[200px] border rounded-md p-2">
              <div className="space-y-2">
                {endpoints.map((endpoint, index) => (
                  <div key={index} className="flex items-center gap-2 p-2 border rounded-sm">
                    <Select
                      value={endpoint.method || 'GET'}
                      onValueChange={(value) => updateEndpoint(index, 'method', value)}
                    >
                      <SelectTrigger className="w-20">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="GET">GET</SelectItem>
                        <SelectItem value="POST">POST</SelectItem>
                        <SelectItem value="PUT">PUT</SelectItem>
                        <SelectItem value="DELETE">DELETE</SelectItem>
                        <SelectItem value="PATCH">PATCH</SelectItem>
                      </SelectContent>
                    </Select>
                    <Input
                      placeholder="/api/path"
                      value={endpoint.path || ''}
                      onChange={(e) => updateEndpoint(index, 'path', e.target.value)}
                      className="flex-1"
                    />
                    <Input
                      placeholder="Description"
                      value={endpoint.description || ''}
                      onChange={(e) => updateEndpoint(index, 'description', e.target.value)}
                      className="flex-1"
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => removeEndpoint(index)}
                      disabled={endpoints.length <= 1}
                    >
                      <Minus className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>

          <Button
            onClick={executeGeneration}
            disabled={currentGeneration !== null || !generatorStatus}
            className="w-full"
          >
            {currentGeneration ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <Play className="h-4 w-4 mr-2" />
            )}
            Generate API
          </Button>
        </CardContent>
      </Card>

      {/* Generation Results */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Generation History</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Tabs defaultValue="results" className="w-full">
            <div className="px-4 pt-2">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="results">Results</TabsTrigger>
                <TabsTrigger value="files">Generated Files</TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="results" className="mt-0">
              <ScrollArea className="h-[300px]">
                <div className="p-4 space-y-2">
                  {generationResults.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-8">
                      No API generations performed yet
                    </p>
                  ) : (
                    generationResults.map((result) => (
                      <div
                        key={result.id}
                        className="flex items-center justify-between gap-2 p-3 rounded-sm hover:bg-accent/50 transition-colors border"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            {getStatusIcon(result.status)}
                            <span className="text-sm font-medium">{result.schema.name}</span>
                            <Badge variant="outline" className="text-xs">
                              v{result.schema.version}
                            </Badge>
                            <Badge variant="outline" className="text-xs">
                              {result.generator_type}
                            </Badge>
                          </div>
                          <p className="text-xs text-muted-foreground">
                            {result.schema.endpoints.length} endpoints • {result.generated_files.length} files
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {new Date(result.started_at).toLocaleString()}
                            {result.completed_at && result.duration && (
                              ` • ${result.duration}ms`
                            )}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant={result.status === 'completed' ? 'secondary' : result.status === 'failed' ? 'destructive' : 'default'} className="gap-1">
                            {getStatusIcon(result.status)}
                            {result.status}
                          </Badge>
                          {result.status === 'completed' && (
                            <Button size="sm" variant="ghost" className="h-6 px-2">
                              <Download className="h-3 w-3" />
                            </Button>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="files" className="mt-0">
              <ScrollArea className="h-[300px]">
                <div className="p-4 space-y-2">
                  {generationResults.length === 0 || !generationResults.some(r => r.generated_files.length > 0) ? (
                    <p className="text-sm text-muted-foreground text-center py-8">
                      No generated files available
                    </p>
                  ) : (
                    generationResults
                      .filter(result => result.generated_files.length > 0)
                      .flatMap(result =>
                        result.generated_files.map(file => ({
                          ...file,
                          schemaName: result.schema.name,
                          generationId: result.id
                        }))
                      )
                      .map((file, index) => (
                        <div
                          key={index}
                          className="flex items-center justify-between gap-2 p-2 rounded-sm hover:bg-accent/50 transition-colors"
                        >
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              {getFileTypeIcon(file.type)}
                              <span className="text-sm font-medium truncate">{file.path}</span>
                              <Badge variant="outline" className="text-xs">
                                {file.type}
                              </Badge>
                            </div>
                            <p className="text-xs text-muted-foreground">
                              {file.schemaName}
                            </p>
                          </div>
                          <div className="flex items-center gap-1">
                            <Button size="sm" variant="ghost" className="h-6 px-2">
                              <Eye className="h-3 w-3" />
                            </Button>
                            <Button size="sm" variant="ghost" className="h-6 px-2">
                              <Copy className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>
                      ))
                  )}
                </div>
              </ScrollArea>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
};