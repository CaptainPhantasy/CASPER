import { useState } from "react";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { analyzeTask, TaskAnalysisResult } from "@/services/api";
import { useAgentStore } from "@/stores/agentStore";

const PRIORITY_OPTIONS: Array<{ label: string; value: "low" | "medium" | "high" }> = [
  { label: "Low", value: "low" },
  { label: "Medium", value: "medium" },
  { label: "High", value: "high" },
];

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 }).format(value);
}

export function TaskPanel() {
  const { toast } = useToast();
  const submitTask = useAgentStore((state) => state.submitTask);

  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<"low" | "medium" | "high">("medium");
  const [analysis, setAnalysis] = useState<TaskAnalysisResult | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    if (!description.trim()) {
      setError("Please describe the task before running an analysis.");
      return;
    }
    setError(null);
    setAnalyzing(true);
    try {
      const result = await analyzeTask(description.trim());
      setAnalysis(result);
    } catch (err) {
      setAnalysis(null);
      setError(err instanceof Error ? err.message : "Failed to analyze task.");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleExecute = async () => {
    if (!description.trim()) {
      setError("Please describe the task before executing.");
      return;
    }
    setError(null);
    setExecuting(true);
    try {
      await submitTask(description.trim(), priority);
      toast({
        title: "Task submitted",
        description: `CASPER agents are processing the request (${priority} priority).`,
      });
      setDescription("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to submit the task.");
    } finally {
      setExecuting(false);
    }
  };

  const badges = analysis?.metrics.requiredAgents ?? [];

  return (
    <Card className="bg-card/80">
      <CardHeader className="pb-4">
        <CardTitle className="text-base">Task Submission</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <Alert variant="destructive">
            <AlertTitle>Action required</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor="task-input">
            Describe the feature or fix
          </label>
          <Textarea
            id="task-input"
            placeholder="Example: Build authentication flow with email verification and session dashboard"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={4}
            spellCheck={false}
          />
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-1">
            <p className="text-xs uppercase text-muted-foreground">Priority</p>
            <Select value={priority} onValueChange={(value: "low" | "medium" | "high") => setPriority(value)}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Select priority" />
              </SelectTrigger>
              <SelectContent>
                {PRIORITY_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleAnalyze} disabled={analyzing}>
              {analyzing ? 'Analyzing…' : 'Analyze Task'}
            </Button>
            <Button onClick={handleExecute} disabled={executing}>
              {executing ? 'Submitting…' : 'Execute Task'}
            </Button>
          </div>
        </div>
        {analysis && (
          <div className="space-y-3 rounded-md border border-border/60 bg-muted/30 p-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline" className="capitalize">
                Complexity: {analysis.metrics.complexity}
              </Badge>
              <Badge variant="secondary" className="capitalize">
                Suggested priority: {analysis.metrics.suggestedPriority}
              </Badge>
              <Badge>
                Tokens ≈ {formatNumber(analysis.metrics.estimatedTokens)}
              </Badge>
            </div>
            <div className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
              <span>Estimated LOC: {formatNumber(analysis.metrics.linesOfCode ?? null)}</span>
              <span>Files impacted: {formatNumber(analysis.metrics.files ?? null)}</span>
              <span>Components: {formatNumber(analysis.metrics.components ?? null)}</span>
              <span>Integration points: {formatNumber(analysis.metrics.integrationPoints ?? null)}</span>
              <span>External deps: {formatNumber(analysis.metrics.externalDependencies ?? null)}</span>
            </div>
            <div className="space-y-1">
              <p className="text-xs font-semibold text-muted-foreground uppercase">Agents Involved</p>
              <div className="flex flex-wrap gap-2">
                {badges.map((agent: string) => (
                  <Badge key={agent} variant="outline">
                    {agent}
                  </Badge>
                ))}
              </div>
            </div>
            <p className="text-[11px] text-muted-foreground/80">
              Source: {analysis.source === 'api' ? 'Backend analyzer' : 'Local heuristic'}
            </p>
          </div>
        )}
      </CardContent>
      <CardFooter className="text-xs text-muted-foreground">
        Tip: Run “Analyze Task” before executing to preview agent allocation and token impact.
      </CardFooter>
    </Card>
  );
}
