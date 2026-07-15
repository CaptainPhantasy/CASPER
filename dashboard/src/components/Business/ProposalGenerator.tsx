import { useState, useCallback } from "react";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import {
  DocumentTextIcon,
  SparklesIcon,
  ArrowDownTrayIcon,
  EyeIcon,
  ClockIcon,
  CurrencyDollarIcon
} from "@heroicons/react/24/outline";
import { cn } from "@/lib/utils";

interface ProposalFormData {
  title: string;
  client: string;
  description: string;
  budget: string;
  timeline: string;
  template: string;
  industry: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
}

interface ProposalTemplate {
  id: string;
  name: string;
  description: string;
  industry: string;
  estimatedSections: number;
}

const PROPOSAL_TEMPLATES: ProposalTemplate[] = [
  {
    id: 'web-development',
    name: 'Web Development',
    description: 'Full-stack web application development',
    industry: 'Technology',
    estimatedSections: 8
  },
  {
    id: 'mobile-app',
    name: 'Mobile Application',
    description: 'Native or cross-platform mobile app',
    industry: 'Technology',
    estimatedSections: 10
  },
  {
    id: 'consulting',
    name: 'Business Consulting',
    description: 'Strategic business consulting services',
    industry: 'Consulting',
    estimatedSections: 6
  },
  {
    id: 'data-analytics',
    name: 'Data Analytics',
    description: 'Data analysis and reporting solutions',
    industry: 'Analytics',
    estimatedSections: 7
  },
  {
    id: 'custom',
    name: 'Custom Proposal',
    description: 'Create a proposal from scratch',
    industry: 'General',
    estimatedSections: 5
  }
];

const PRIORITY_CONFIG = {
  low: { color: 'bg-blue-500', label: 'Low Priority' },
  medium: { color: 'bg-yellow-500', label: 'Medium Priority' },
  high: { color: 'bg-orange-500', label: 'High Priority' },
  urgent: { color: 'bg-red-500', label: 'Urgent' }
};

export function ProposalGenerator() {
  const { toast } = useToast();
  const [formData, setFormData] = useState<ProposalFormData>({
    title: '',
    client: '',
    description: '',
    budget: '',
    timeline: '',
    template: '',
    industry: '',
    priority: 'medium'
  });

  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [generatedProposal, setGeneratedProposal] = useState<string | null>(null);

  const selectedTemplate = PROPOSAL_TEMPLATES.find(t => t.id === formData.template);

  const handleInputChange = useCallback((field: keyof ProposalFormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  }, []);

  const validateForm = (): boolean => {
    if (!formData.title.trim()) {
      toast({
        title: "Validation Error",
        description: "Project title is required",
        variant: "destructive"
      });
      return false;
    }

    if (!formData.client.trim()) {
      toast({
        title: "Validation Error",
        description: "Client name is required",
        variant: "destructive"
      });
      return false;
    }

    if (!formData.template) {
      toast({
        title: "Validation Error",
        description: "Please select a proposal template",
        variant: "destructive"
      });
      return false;
    }

    return true;
  };

  const simulateProgress = () => {
    setProgress(0);
    const intervals = [15, 35, 60, 80, 95, 100];
    const messages = [
      'Analyzing project requirements...',
      'Researching industry best practices...',
      'Structuring proposal sections...',
      'Generating executive summary...',
      'Adding timeline and budget details...',
      'Finalizing proposal document...'
    ];

    intervals.forEach((target, index) => {
      setTimeout(() => {
        setProgress(target);
        if (index < messages.length) {
          toast({
            title: "Generating Proposal",
            description: messages[index]
          });
        }
      }, (index + 1) * 800);
    });
  };

  const handleGenerate = async () => {
    if (!validateForm()) return;

    setIsGenerating(true);
    simulateProgress();

    try {
      // Simulate API call to generate proposal
      setTimeout(() => {
        const proposalContent = `# ${formData.title}\n\n**Client:** ${formData.client}\n**Priority:** ${PRIORITY_CONFIG[formData.priority].label}\n\n## Executive Summary\n\nThis proposal outlines the ${formData.description || 'project requirements'} for ${formData.client}.\n\n## Project Scope\n\n${selectedTemplate ? `Based on the ${selectedTemplate.name} template, this project will include:` : 'Custom project scope to be defined.'}\n\n## Timeline\n\n${formData.timeline || 'Timeline to be discussed'}\n\n## Investment\n\n${formData.budget || 'Budget to be determined'}\n\n---\n\nGenerated by CASPER Prime AI Assistant`;

        setGeneratedProposal(proposalContent);
        setIsGenerating(false);
        setProgress(100);

        toast({
          title: "Success!",
          description: `Proposal "${formData.title}" generated successfully`,
        });
      }, 5000);

    } catch (error) {
      console.error('Error generating proposal:', error);
      setIsGenerating(false);
      setProgress(0);
      toast({
        title: "Generation Failed",
        description: "Failed to generate proposal. Please try again.",
        variant: "destructive"
      });
    }
  };

  const handleExport = (format: 'pdf' | 'markdown' | 'docx') => {
    toast({
      title: `Export ${format.toUpperCase()}`,
      description: `Exporting proposal as ${format.toUpperCase()}...`
    });

    // Simulate export functionality
    setTimeout(() => {
      toast({
        title: "Export Complete",
        description: `Proposal exported as ${format.toUpperCase()}`
      });
    }, 2000);
  };

  const handlePreview = () => {
    toast({
      title: "Preview",
      description: "Opening proposal preview..."
    });
  };

  return (
    <div className="flex flex-col space-y-6 p-4">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2">
            <DocumentTextIcon className="h-6 w-6 text-emerald-500" />
            <CardTitle className="text-emerald-700">AI Proposal Generator</CardTitle>
          </div>
          <CardDescription>
            Create professional project proposals with AI assistance
          </CardDescription>
        </CardHeader>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Form */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Project Details</CardTitle>
            <CardDescription>
              Provide project information to generate your proposal
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="title">Project Title *</Label>
              <Input
                id="title"
                placeholder="e.g., E-commerce Platform Development"
                value={formData.title}
                onChange={(e) => handleInputChange('title', e.target.value)}
                className="w-full"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="client">Client Name *</Label>
              <Input
                id="client"
                placeholder="e.g., Acme Corporation"
                value={formData.client}
                onChange={(e) => handleInputChange('client', e.target.value)}
                className="w-full"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="template">Proposal Template *</Label>
              <Select value={formData.template} onValueChange={(value) => handleInputChange('template', value)}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a template" />
                </SelectTrigger>
                <SelectContent>
                  {PROPOSAL_TEMPLATES.map(template => (
                    <SelectItem key={template.id} value={template.id}>
                      <div>
                        <div className="font-medium">{template.name}</div>
                        <div className="text-xs text-muted-foreground">{template.description}</div>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedTemplate && (
                <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                  <Badge variant="secondary">{selectedTemplate.industry}</Badge>
                  <span>~{selectedTemplate.estimatedSections} sections</span>
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="priority">Priority Level</Label>
              <Select value={formData.priority} onValueChange={(value: any) => handleInputChange('priority', value)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(PRIORITY_CONFIG).map(([key, config]) => (
                    <SelectItem key={key} value={key}>
                      <div className="flex items-center space-x-2">
                        <div className={cn("w-2 h-2 rounded-full", config.color)} />
                        <span>{config.label}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Project Description</Label>
              <Textarea
                id="description"
                placeholder="Describe the project scope, objectives, and key requirements..."
                value={formData.description}
                onChange={(e) => handleInputChange('description', e.target.value)}
                rows={3}
                className="w-full"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="budget">Budget Estimate</Label>
                <div className="relative">
                  <CurrencyDollarIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="budget"
                    placeholder="50,000"
                    value={formData.budget}
                    onChange={(e) => handleInputChange('budget', e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="timeline">Timeline</Label>
                <div className="relative">
                  <ClockIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="timeline"
                    placeholder="12 weeks"
                    value={formData.timeline}
                    onChange={(e) => handleInputChange('timeline', e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>
            </div>
          </CardContent>
          <CardFooter>
            <Button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="w-full bg-emerald-600 hover:bg-emerald-700"
            >
              <SparklesIcon className="mr-2 h-4 w-4" />
              {isGenerating ? 'Generating...' : 'Generate AI Proposal'}
            </Button>
          </CardFooter>
        </Card>

        {/* Progress/Preview */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              {generatedProposal ? 'Generated Proposal' : 'Generation Progress'}
            </CardTitle>
            <CardDescription>
              {generatedProposal ? 'Your AI-generated proposal is ready' : 'AI is creating your proposal'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isGenerating && (
              <div className="space-y-4">
                <Progress value={progress} className="w-full" />
                <div className="text-center text-sm text-muted-foreground">
                  {progress}% complete
                </div>
              </div>
            )}

            {generatedProposal && !isGenerating && (
              <div className="space-y-4">
                <div className="border rounded-md p-4 bg-muted/30 max-h-96 overflow-y-auto">
                  <pre className="text-sm whitespace-pre-wrap font-sans">
                    {generatedProposal}
                  </pre>
                </div>

                <Separator />

                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" size="sm" onClick={handlePreview}>
                    <EyeIcon className="mr-2 h-4 w-4" />
                    Preview
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => handleExport('pdf')}>
                    <ArrowDownTrayIcon className="mr-2 h-4 w-4" />
                    Export PDF
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => handleExport('markdown')}>
                    <ArrowDownTrayIcon className="mr-2 h-4 w-4" />
                    Export MD
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => handleExport('docx')}>
                    <ArrowDownTrayIcon className="mr-2 h-4 w-4" />
                    Export DOCX
                  </Button>
                </div>
              </div>
            )}

            {!isGenerating && !generatedProposal && (
              <div className="text-center py-8 text-muted-foreground">
                <DocumentTextIcon className="mx-auto h-12 w-12 mb-4 opacity-50" />
                <p>Fill in the project details and click "Generate AI Proposal" to get started</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
