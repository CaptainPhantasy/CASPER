import * as React from "react";
import { useState, useCallback, useMemo } from "react";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import {
  CalculatorIcon,
  ClockIcon,
  CurrencyDollarIcon,
  ExclamationTriangleIcon,
  ChartBarIcon,
  CalendarDaysIcon,
  UserGroupIcon,
  CogIcon
} from "@heroicons/react/24/outline";
import { cn } from "@/lib/utils";

interface ProjectRequirement {
  id: string;
  name: string;
  description: string;
  complexity: 'low' | 'medium' | 'high';
  hours: number;
  dependencies: string[];
}

interface RiskFactor {
  id: string;
  name: string;
  impact: 'low' | 'medium' | 'high';
  probability: 'low' | 'medium' | 'high';
  mitigation: string;
}

interface EstimationData {
  projectName: string;
  projectType: string;
  teamSize: string;
  hourlyRate: string;
  timeline: string;
  complexity: 'simple' | 'moderate' | 'complex' | 'enterprise';
  requirements: ProjectRequirement[];
  risks: RiskFactor[];
}

const PROJECT_TYPES = [
  { value: 'web-app', label: 'Web Application', baseHours: 400, complexityMultiplier: 1.0 },
  { value: 'mobile-app', label: 'Mobile Application', baseHours: 600, complexityMultiplier: 1.2 },
  { value: 'desktop-app', label: 'Desktop Application', baseHours: 500, complexityMultiplier: 1.1 },
  { value: 'api-service', label: 'API/Microservice', baseHours: 300, complexityMultiplier: 0.9 },
  { value: 'data-pipeline', label: 'Data Pipeline', baseHours: 450, complexityMultiplier: 1.3 },
  { value: 'ai-ml', label: 'AI/ML Solution', baseHours: 800, complexityMultiplier: 1.8 },
  { value: 'ecommerce', label: 'E-commerce Platform', baseHours: 700, complexityMultiplier: 1.4 },
  { value: 'cms', label: 'Content Management', baseHours: 350, complexityMultiplier: 1.0 }
];

const COMPLEXITY_FACTORS = {
  simple: { multiplier: 0.7, label: 'Simple', description: 'Basic functionality, standard patterns' },
  moderate: { multiplier: 1.0, label: 'Moderate', description: 'Some custom features, integrations' },
  complex: { multiplier: 1.5, label: 'Complex', description: 'Advanced features, multiple systems' },
  enterprise: { multiplier: 2.2, label: 'Enterprise', description: 'High scalability, compliance requirements' }
};

const RISK_IMPACTS = {
  low: { color: 'bg-green-500', multiplier: 1.05, label: 'Low Impact' },
  medium: { color: 'bg-yellow-500', multiplier: 1.15, label: 'Medium Impact' },
  high: { color: 'bg-red-500', multiplier: 1.30, label: 'High Impact' }
};

const RISK_PROBABILITIES = {
  low: { multiplier: 0.2, label: 'Low Probability (20%)' },
  medium: { multiplier: 0.5, label: 'Medium Probability (50%)' },
  high: { multiplier: 0.8, label: 'High Probability (80%)' }
};

const DEFAULT_REQUIREMENTS: ProjectRequirement[] = [
  {
    id: 'analysis',
    name: 'Requirements Analysis',
    description: 'Detailed project requirements gathering and analysis',
    complexity: 'medium',
    hours: 40,
    dependencies: []
  },
  {
    id: 'design',
    name: 'System Design',
    description: 'Architecture and UI/UX design phase',
    complexity: 'high',
    hours: 80,
    dependencies: ['analysis']
  },
  {
    id: 'development',
    name: 'Core Development',
    description: 'Main application development phase',
    complexity: 'high',
    hours: 200,
    dependencies: ['design']
  },
  {
    id: 'testing',
    name: 'Testing & QA',
    description: 'Comprehensive testing and quality assurance',
    complexity: 'medium',
    hours: 60,
    dependencies: ['development']
  },
  {
    id: 'deployment',
    name: 'Deployment & Setup',
    description: 'Production deployment and environment setup',
    complexity: 'medium',
    hours: 30,
    dependencies: ['testing']
  }
];

const DEFAULT_RISKS: RiskFactor[] = [
  {
    id: 'scope-creep',
    name: 'Scope Creep',
    impact: 'high',
    probability: 'medium',
    mitigation: 'Clear requirements documentation and change control process'
  },
  {
    id: 'technical-complexity',
    name: 'Technical Complexity',
    impact: 'medium',
    probability: 'medium',
    mitigation: 'Technical proof of concept and early prototyping'
  },
  {
    id: 'resource-availability',
    name: 'Resource Availability',
    impact: 'medium',
    probability: 'low',
    mitigation: 'Resource planning and backup team members'
  },
  {
    id: 'external-dependencies',
    name: 'External Dependencies',
    impact: 'high',
    probability: 'low',
    mitigation: 'Early integration testing and contingency plans'
  }
];

export function ProjectEstimator() {
  const { toast } = useToast();
  const [estimationData, setEstimationData] = useState<EstimationData>({
    projectName: '',
    projectType: '',
    teamSize: '3',
    hourlyRate: '100',
    timeline: '',
    complexity: 'moderate',
    requirements: DEFAULT_REQUIREMENTS,
    risks: DEFAULT_RISKS
  });

  const [isCalculating, setIsCalculating] = useState(false);
  const [activeTab, setActiveTab] = useState('basics');

  const selectedProjectType = PROJECT_TYPES.find(pt => pt.value === estimationData.projectType);
  const complexityConfig = COMPLEXITY_FACTORS[estimationData.complexity];

  const calculations = useMemo(() => {
    if (!selectedProjectType) {
      return {
        baseHours: 0,
        adjustedHours: 0,
        riskAdjustment: 0,
        finalHours: 0,
        estimatedCost: 0,
        timelineWeeks: 0,
        confidenceLevel: 0
      };
    }

    // Base calculation
    const baseHours = selectedProjectType.baseHours * selectedProjectType.complexityMultiplier;
    const complexityAdjustedHours = baseHours * complexityConfig.multiplier;

    // Requirements-based adjustment
    const requirementsHours = estimationData.requirements.reduce((sum, req) => sum + req.hours, 0);
    const adjustedHours = Math.max(complexityAdjustedHours, requirementsHours);

    // Risk assessment
    let riskMultiplier = 1.0;
    estimationData.risks.forEach(risk => {
      const impactMultiplier = RISK_IMPACTS[risk.impact].multiplier;
      const probabilityMultiplier = RISK_PROBABILITIES[risk.probability].multiplier;
      riskMultiplier += (impactMultiplier - 1.0) * probabilityMultiplier;
    });

    const riskAdjustedHours = adjustedHours * riskMultiplier;
    const finalHours = Math.ceil(riskAdjustedHours);

    // Cost and timeline
    const hourlyRate = parseFloat(estimationData.hourlyRate) || 100;
    const teamSize = parseInt(estimationData.teamSize) || 3;
    const estimatedCost = finalHours * hourlyRate;
    const timelineWeeks = Math.ceil(finalHours / (teamSize * 40)); // 40 hours per person per week

    // Confidence level based on risk factors
    const highRiskCount = estimationData.risks.filter(r => r.impact === 'high' && r.probability === 'high').length;
    const confidenceLevel = Math.max(60, 95 - (highRiskCount * 15) - (estimationData.complexity === 'enterprise' ? 10 : 0));

    return {
      baseHours: Math.ceil(baseHours),
      adjustedHours: Math.ceil(adjustedHours),
      riskAdjustment: Math.ceil(riskAdjustedHours - adjustedHours),
      finalHours,
      estimatedCost,
      timelineWeeks,
      confidenceLevel
    };
  }, [selectedProjectType, complexityConfig, estimationData.requirements, estimationData.risks, estimationData.hourlyRate, estimationData.teamSize, estimationData.complexity]);

  const handleInputChange = useCallback((field: keyof EstimationData, value: any) => {
    setEstimationData(prev => ({ ...prev, [field]: value }));
  }, []);

  const handleRequirementChange = useCallback((id: string, field: keyof ProjectRequirement, value: any) => {
    setEstimationData(prev => ({
      ...prev,
      requirements: prev.requirements.map(req =>
        req.id === id ? { ...req, [field]: value } : req
      )
    }));
  }, []);

  const handleRiskChange = useCallback((id: string, field: keyof RiskFactor, value: any) => {
    setEstimationData(prev => ({
      ...prev,
      risks: prev.risks.map(risk =>
        risk.id === id ? { ...risk, [field]: value } : risk
      )
    }));
  }, []);

  const generateEstimateReport = async () => {
    if (!estimationData.projectName || !estimationData.projectType) {
      toast({
        title: "Validation Error",
        description: "Please provide project name and type",
        variant: "destructive"
      });
      return;
    }

    setIsCalculating(true);

    // Simulate calculation processing
    setTimeout(() => {
      setIsCalculating(false);
      toast({
        title: "Estimation Complete",
        description: `Project estimate generated: ${calculations.finalHours} hours, $${calculations.estimatedCost.toLocaleString()}`,
      });
      setActiveTab('estimate');
    }, 2000);
  };

  const exportEstimate = (format: 'pdf' | 'excel' | 'json') => {
    toast({
      title: `Export ${format.toUpperCase()}`,
      description: `Exporting estimate as ${format.toUpperCase()}...`
    });
  };

  return (
    <div className="flex flex-col space-y-6 p-4">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2">
            <CalculatorIcon className="h-6 w-6 text-emerald-500" />
            <CardTitle className="text-emerald-700">AI Project Estimator</CardTitle>
          </div>
          <CardDescription>
            Comprehensive project estimation with risk analysis and timeline planning
          </CardDescription>
        </CardHeader>
      </Card>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="basics">Project Basics</TabsTrigger>
          <TabsTrigger value="requirements">Requirements</TabsTrigger>
          <TabsTrigger value="risks">Risk Analysis</TabsTrigger>
          <TabsTrigger value="estimate">Final Estimate</TabsTrigger>
        </TabsList>

        {/* Project Basics Tab */}
        <TabsContent value="basics" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Project Information</CardTitle>
              <CardDescription>Basic project details and parameters</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="projectName">Project Name *</Label>
                  <Input
                    id="projectName"
                    placeholder="e.g., Customer Portal Application"
                    value={estimationData.projectName}
                    onChange={(e) => handleInputChange('projectName', e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="projectType">Project Type *</Label>
                  <Select value={estimationData.projectType} onValueChange={(value) => handleInputChange('projectType', value)}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select project type" />
                    </SelectTrigger>
                    <SelectContent>
                      {PROJECT_TYPES.map(type => (
                        <SelectItem key={type.value} value={type.value}>
                          <div>
                            <div className="font-medium">{type.label}</div>
                            <div className="text-xs text-muted-foreground">Base: {type.baseHours}h</div>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="complexity">Project Complexity</Label>
                  <Select value={estimationData.complexity} onValueChange={(value: any) => handleInputChange('complexity', value)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(COMPLEXITY_FACTORS).map(([key, config]) => (
                        <SelectItem key={key} value={key}>
                          <div>
                            <div className="font-medium">{config.label} ({config.multiplier}x)</div>
                            <div className="text-xs text-muted-foreground">{config.description}</div>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="teamSize">Team Size</Label>
                  <div className="relative">
                    <UserGroupIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="teamSize"
                      type="number"
                      min="1"
                      max="20"
                      value={estimationData.teamSize}
                      onChange={(e) => handleInputChange('teamSize', e.target.value)}
                      className="pl-10"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="hourlyRate">Hourly Rate ($)</Label>
                  <div className="relative">
                    <CurrencyDollarIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="hourlyRate"
                      type="number"
                      min="1"
                      value={estimationData.hourlyRate}
                      onChange={(e) => handleInputChange('hourlyRate', e.target.value)}
                      className="pl-10"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="timeline">Target Timeline</Label>
                  <div className="relative">
                    <CalendarDaysIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="timeline"
                      placeholder="e.g., 3 months, 12 weeks"
                      value={estimationData.timeline}
                      onChange={(e) => handleInputChange('timeline', e.target.value)}
                      className="pl-10"
                    />
                  </div>
                </div>
              </div>

              {selectedProjectType && (
                <div className="mt-4 p-4 bg-muted/30 rounded-lg">
                  <h4 className="font-medium mb-2">Quick Estimation Preview</h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Base Hours:</span>
                      <div className="font-medium">{calculations.baseHours}h</div>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Adjusted Hours:</span>
                      <div className="font-medium">{calculations.adjustedHours}h</div>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Estimated Cost:</span>
                      <div className="font-medium">${calculations.estimatedCost.toLocaleString()}</div>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Timeline:</span>
                      <div className="font-medium">{calculations.timelineWeeks} weeks</div>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
            <CardFooter>
              <Button onClick={() => setActiveTab('requirements')}>
                Next: Requirements Analysis
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>

        {/* Requirements Tab */}
        <TabsContent value="requirements" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Project Requirements</CardTitle>
              <CardDescription>Define and estimate individual project components</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {estimationData.requirements.map(requirement => (
                  <Card key={requirement.id}>
                    <CardContent className="pt-4">
                      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-center">
                        <div className="space-y-1">
                          <Label className="font-medium">{requirement.name}</Label>
                          <p className="text-xs text-muted-foreground">{requirement.description}</p>
                        </div>
                        <div>
                          <Select
                            value={requirement.complexity}
                            onValueChange={(value: any) => handleRequirementChange(requirement.id, 'complexity', value)}
                          >
                            <SelectTrigger className="h-8">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="low">Low Complexity</SelectItem>
                              <SelectItem value="medium">Medium Complexity</SelectItem>
                              <SelectItem value="high">High Complexity</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="relative">
                          <ClockIcon className="absolute left-2 top-2 h-3 w-3 text-muted-foreground" />
                          <Input
                            type="number"
                            min="1"
                            value={requirement.hours}
                            onChange={(e) => handleRequirementChange(requirement.id, 'hours', parseInt(e.target.value))}
                            className="h-8 pl-7"
                            placeholder="Hours"
                          />
                        </div>
                        <div>
                          <Badge variant={
                            requirement.complexity === 'high' ? 'destructive' :
                            requirement.complexity === 'medium' ? 'default' : 'secondary'
                          }>
                            {requirement.complexity}
                          </Badge>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
            <CardFooter className="justify-between">
              <Button variant="outline" onClick={() => setActiveTab('basics')}>
                Previous: Project Basics
              </Button>
              <Button onClick={() => setActiveTab('risks')}>
                Next: Risk Analysis
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>

        {/* Risk Analysis Tab */}
        <TabsContent value="risks" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Risk Assessment</CardTitle>
              <CardDescription>Identify and evaluate project risks</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {estimationData.risks.map(risk => (
                  <Card key={risk.id}>
                    <CardContent className="pt-4">
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="space-y-1">
                            <Label className="font-medium flex items-center">
                              <ExclamationTriangleIcon className="h-4 w-4 mr-1" />
                              {risk.name}
                            </Label>
                          </div>
                          <div className="flex space-x-2">
                            <Badge variant={
                              risk.impact === 'high' ? 'destructive' :
                              risk.impact === 'medium' ? 'default' : 'secondary'
                            }>
                              {RISK_IMPACTS[risk.impact].label}
                            </Badge>
                            <Badge variant="outline">
                              {RISK_PROBABILITIES[risk.probability].label}
                            </Badge>
                          </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label className="text-xs">Impact Level</Label>
                            <Select
                              value={risk.impact}
                              onValueChange={(value: any) => handleRiskChange(risk.id, 'impact', value)}
                            >
                              <SelectTrigger className="h-8">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="low">Low Impact</SelectItem>
                                <SelectItem value="medium">Medium Impact</SelectItem>
                                <SelectItem value="high">High Impact</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="space-y-2">
                            <Label className="text-xs">Probability</Label>
                            <Select
                              value={risk.probability}
                              onValueChange={(value: any) => handleRiskChange(risk.id, 'probability', value)}
                            >
                              <SelectTrigger className="h-8">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="low">Low (20%)</SelectItem>
                                <SelectItem value="medium">Medium (50%)</SelectItem>
                                <SelectItem value="high">High (80%)</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>

                        <div className="space-y-2">
                          <Label className="text-xs">Mitigation Strategy</Label>
                          <Textarea
                            value={risk.mitigation}
                            onChange={(e) => handleRiskChange(risk.id, 'mitigation', e.target.value)}
                            placeholder="Describe how to mitigate this risk..."
                            className="h-16 text-xs"
                          />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
            <CardFooter className="justify-between">
              <Button variant="outline" onClick={() => setActiveTab('requirements')}>
                Previous: Requirements
              </Button>
              <Button onClick={generateEstimateReport} disabled={isCalculating}>
                <ChartBarIcon className="mr-2 h-4 w-4" />
                {isCalculating ? 'Calculating...' : 'Generate Final Estimate'}
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>

        {/* Final Estimate Tab */}
        <TabsContent value="estimate" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Estimation Summary</CardTitle>
                <CardDescription>Final project estimation breakdown</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center p-4 bg-emerald-50 rounded-lg">
                    <div className="text-2xl font-bold text-emerald-700">
                      {calculations.finalHours}h
                    </div>
                    <div className="text-sm text-emerald-600">Total Hours</div>
                  </div>
                  <div className="text-center p-4 bg-blue-50 rounded-lg">
                    <div className="text-2xl font-bold text-blue-700">
                      ${calculations.estimatedCost.toLocaleString()}
                    </div>
                    <div className="text-sm text-blue-600">Estimated Cost</div>
                  </div>
                  <div className="text-center p-4 bg-purple-50 rounded-lg">
                    <div className="text-2xl font-bold text-purple-700">
                      {calculations.timelineWeeks}
                    </div>
                    <div className="text-sm text-purple-600">Weeks</div>
                  </div>
                  <div className="text-center p-4 bg-orange-50 rounded-lg">
                    <div className="text-2xl font-bold text-orange-700">
                      {calculations.confidenceLevel}%
                    </div>
                    <div className="text-sm text-orange-600">Confidence</div>
                  </div>
                </div>

                <Separator />

                <div className="space-y-3">
                  <h4 className="font-medium">Estimation Breakdown</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>Base Hours ({selectedProjectType?.label}):</span>
                      <span>{calculations.baseHours}h</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Complexity Adjustment ({complexityConfig.label}):</span>
                      <span>{calculations.adjustedHours - calculations.baseHours}h</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Risk Buffer:</span>
                      <span>+{calculations.riskAdjustment}h</span>
                    </div>
                    <Separator />
                    <div className="flex justify-between font-medium">
                      <span>Final Estimate:</span>
                      <span>{calculations.finalHours}h</span>
                    </div>
                  </div>
                </div>
              </CardContent>
              <CardFooter className="flex space-x-2">
                <Button variant="outline" onClick={() => exportEstimate('pdf')}>
                  Export PDF
                </Button>
                <Button variant="outline" onClick={() => exportEstimate('excel')}>
                  Export Excel
                </Button>
                <Button variant="outline" onClick={() => exportEstimate('json')}>
                  Export JSON
                </Button>
              </CardFooter>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Timeline Visualization</CardTitle>
                <CardDescription>Project timeline and milestones</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {estimationData.requirements.map((req, index) => (
                    <div key={req.id} className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium">{req.name}</span>
                        <span className="text-muted-foreground">{req.hours}h</span>
                      </div>
                      <Progress
                        value={100}
                        className={cn(
                          "h-2",
                          req.complexity === 'high' ? 'bg-red-100' :
                          req.complexity === 'medium' ? 'bg-yellow-100' : 'bg-green-100'
                        )}
                      />
                      <div className="text-xs text-muted-foreground">
                        Week {Math.ceil((index + 1) * calculations.timelineWeeks / estimationData.requirements.length)}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {isCalculating && (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center space-y-4">
              <CogIcon className="mx-auto h-8 w-8 animate-spin text-emerald-500" />
              <div>
                <div className="text-lg font-medium">Calculating Project Estimate</div>
                <div className="text-sm text-muted-foreground">
                  Analyzing requirements, complexity, and risk factors...
                </div>
              </div>
              <Progress value={50} className="w-full" />
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}