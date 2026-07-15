import * as React from "react";
import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import {
  DocumentTextIcon,
  CalculatorIcon,
  CreditCardIcon,
  ChartBarIcon,
  ArrowTrendingUpIcon,
  ClockIcon,
  CurrencyDollarIcon,
  UserGroupIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ArrowRightIcon,
  PlusIcon
} from "@heroicons/react/24/outline";
import { cn } from "@/lib/utils";

interface BusinessMetrics {
  totalRevenue: number;
  activeProjects: number;
  completedProjects: number;
  pendingInvoices: number;
  paidInvoices: number;
  overdueInvoices: number;
  avgProjectValue: number;
  clientSatisfaction: number;
}

interface RecentActivity {
  id: string;
  type: 'proposal' | 'estimate' | 'invoice' | 'payment';
  title: string;
  client: string;
  amount?: number;
  status: 'pending' | 'completed' | 'paid' | 'overdue';
  date: string;
}

interface ProjectOverview {
  id: string;
  name: string;
  client: string;
  value: number;
  progress: number;
  status: 'planning' | 'in-progress' | 'review' | 'completed';
  deadline: string;
}

interface QuickAction {
  id: string;
  title: string;
  description: string;
  icon: React.ComponentType<any>;
  color: string;
  action: () => void;
}

const SAMPLE_METRICS: BusinessMetrics = {
  totalRevenue: 487500,
  activeProjects: 12,
  completedProjects: 38,
  pendingInvoices: 7,
  paidInvoices: 31,
  overdueInvoices: 2,
  avgProjectValue: 12800,
  clientSatisfaction: 94
};

const SAMPLE_ACTIVITIES: RecentActivity[] = [
  {
    id: '1',
    type: 'proposal',
    title: 'E-commerce Platform Development',
    client: 'Acme Corporation',
    amount: 45000,
    status: 'pending',
    date: '2025-09-24'
  },
  {
    id: '2',
    type: 'invoice',
    title: 'Mobile App Development - Phase 1',
    client: 'TechStart Inc',
    amount: 28000,
    status: 'paid',
    date: '2025-09-23'
  },
  {
    id: '3',
    type: 'estimate',
    title: 'Data Analytics Dashboard',
    client: 'DataFlow Ltd',
    amount: 15000,
    status: 'completed',
    date: '2025-09-22'
  },
  {
    id: '4',
    type: 'payment',
    title: 'Website Redesign Project',
    client: 'Creative Agency',
    amount: 12000,
    status: 'completed',
    date: '2025-09-21'
  },
  {
    id: '5',
    type: 'invoice',
    title: 'API Development Services',
    client: 'StartupXYZ',
    amount: 8500,
    status: 'overdue',
    date: '2025-09-15'
  }
];

const SAMPLE_PROJECTS: ProjectOverview[] = [
  {
    id: '1',
    name: 'Customer Portal Redesign',
    client: 'Global Corp',
    value: 35000,
    progress: 75,
    status: 'in-progress',
    deadline: '2025-10-15'
  },
  {
    id: '2',
    name: 'Mobile Banking App',
    client: 'FinTech Solutions',
    value: 85000,
    progress: 45,
    status: 'in-progress',
    deadline: '2025-11-30'
  },
  {
    id: '3',
    name: 'Inventory Management System',
    client: 'Retail Chain',
    value: 28000,
    progress: 90,
    status: 'review',
    deadline: '2025-10-08'
  },
  {
    id: '4',
    name: 'Marketing Analytics Platform',
    client: 'AdTech Inc',
    value: 42000,
    progress: 25,
    status: 'planning',
    deadline: '2025-12-15'
  }
];

const ACTIVITY_COLORS = {
  proposal: 'bg-blue-100 text-blue-800',
  estimate: 'bg-purple-100 text-purple-800',
  invoice: 'bg-emerald-100 text-emerald-800',
  payment: 'bg-green-100 text-green-800'
};

const ACTIVITY_ICONS = {
  proposal: DocumentTextIcon,
  estimate: CalculatorIcon,
  invoice: CreditCardIcon,
  payment: CurrencyDollarIcon
};

const STATUS_COLORS = {
  pending: 'bg-yellow-100 text-yellow-800',
  completed: 'bg-green-100 text-green-800',
  paid: 'bg-emerald-100 text-emerald-800',
  overdue: 'bg-red-100 text-red-800'
};

const PROJECT_STATUS_COLORS = {
  planning: 'bg-blue-100 text-blue-800',
  'in-progress': 'bg-orange-100 text-orange-800',
  review: 'bg-purple-100 text-purple-800',
  completed: 'bg-green-100 text-green-800'
};

export function BusinessDashboard() {
  const { toast } = useToast();
  const [metrics] = useState<BusinessMetrics>(SAMPLE_METRICS);
  const [activities] = useState<RecentActivity[]>(SAMPLE_ACTIVITIES);
  const [projects] = useState<ProjectOverview[]>(SAMPLE_PROJECTS);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Simulate loading data
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  const quickActions: QuickAction[] = [
    {
      id: 'new-proposal',
      title: 'Generate Proposal',
      description: 'Create AI-powered project proposal',
      icon: DocumentTextIcon,
      color: 'bg-blue-500',
      action: () => {
        toast({
          title: "Opening Proposal Generator",
          description: "Launching AI proposal creation tool..."
        });
      }
    },
    {
      id: 'project-estimate',
      title: 'Project Estimate',
      description: 'Calculate project costs and timeline',
      icon: CalculatorIcon,
      color: 'bg-purple-500',
      action: () => {
        toast({
          title: "Opening Project Estimator",
          description: "Launching estimation and risk analysis tool..."
        });
      }
    },
    {
      id: 'create-invoice',
      title: 'Create Invoice',
      description: 'Generate professional invoice',
      icon: CreditCardIcon,
      color: 'bg-emerald-500',
      action: () => {
        toast({
          title: "Opening Invoice Generator",
          description: "Launching professional invoice creation..."
        });
      }
    },
    {
      id: 'view-analytics',
      title: 'Business Analytics',
      description: 'View detailed business metrics',
      icon: ChartBarIcon,
      color: 'bg-orange-500',
      action: () => {
        toast({
          title: "Business Analytics",
          description: "Opening detailed business intelligence dashboard..."
        });
      }
    }
  ];

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const getRevenueGrowth = (): number => {
    // Simulate revenue growth calculation
    return 23.5; // 23.5% growth
  };

  if (isLoading) {
    return (
      <div className="flex flex-col space-y-6 p-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center space-y-4">
              <ChartBarIcon className="mx-auto h-8 w-8 animate-pulse text-emerald-500" />
              <div>
                <div className="text-lg font-medium">Loading Business Dashboard</div>
                <div className="text-sm text-muted-foreground">
                  Fetching your business metrics and recent activity...
                </div>
              </div>
              <Progress value={60} className="w-full" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col space-y-6 p-4">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center space-x-2">
                <ChartBarIcon className="h-6 w-6 text-emerald-500" />
                <CardTitle className="text-emerald-700">Business Dashboard</CardTitle>
              </div>
              <CardDescription>
                Comprehensive overview of your business performance and operations
              </CardDescription>
            </div>
            <Badge variant="outline" className="text-emerald-700">
              Last updated: {formatDate(new Date().toISOString())}
            </Badge>
          </div>
        </CardHeader>
      </Card>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <CurrencyDollarIcon className="h-8 w-8 text-emerald-500" />
              <div>
                <div className="text-2xl font-bold text-emerald-700">
                  {formatCurrency(metrics.totalRevenue)}
                </div>
                <div className="text-sm text-muted-foreground">Total Revenue</div>
                <div className="flex items-center space-x-1 mt-1">
                  <ArrowTrendingUpIcon className="h-3 w-3 text-green-500" />
                  <span className="text-xs text-green-600">+{getRevenueGrowth()}%</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <UserGroupIcon className="h-8 w-8 text-blue-500" />
              <div>
                <div className="text-2xl font-bold text-blue-700">
                  {metrics.activeProjects}
                </div>
                <div className="text-sm text-muted-foreground">Active Projects</div>
                <div className="text-xs text-blue-600 mt-1">
                  {metrics.completedProjects} completed
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <CreditCardIcon className="h-8 w-8 text-purple-500" />
              <div>
                <div className="text-2xl font-bold text-purple-700">
                  {metrics.pendingInvoices}
                </div>
                <div className="text-sm text-muted-foreground">Pending Invoices</div>
                <div className="flex items-center space-x-2 mt-1">
                  <div className="text-xs text-green-600">{metrics.paidInvoices} paid</div>
                  {metrics.overdueInvoices > 0 && (
                    <div className="text-xs text-red-600">{metrics.overdueInvoices} overdue</div>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <CalculatorIcon className="h-8 w-8 text-orange-500" />
              <div>
                <div className="text-2xl font-bold text-orange-700">
                  {formatCurrency(metrics.avgProjectValue)}
                </div>
                <div className="text-sm text-muted-foreground">Avg Project Value</div>
                <div className="flex items-center space-x-1 mt-1">
                  <CheckCircleIcon className="h-3 w-3 text-green-500" />
                  <span className="text-xs text-green-600">{metrics.clientSatisfaction}% satisfaction</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Quick Actions</CardTitle>
          <CardDescription>Frequently used business operations</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {quickActions.map(action => {
              const IconComponent = action.icon;
              return (
                <Card
                  key={action.id}
                  className="cursor-pointer hover:shadow-md transition-shadow border-2 hover:border-emerald-200"
                  onClick={action.action}
                >
                  <CardContent className="pt-4">
                    <div className="flex flex-col items-center text-center space-y-3">
                      <div className={cn("p-3 rounded-lg", action.color)}>
                        <IconComponent className="h-6 w-6 text-white" />
                      </div>
                      <div>
                        <div className="font-medium text-sm">{action.title}</div>
                        <div className="text-xs text-muted-foreground">
                          {action.description}
                        </div>
                      </div>
                      <ArrowRightIcon className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="activity" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="activity">Recent Activity</TabsTrigger>
          <TabsTrigger value="projects">Active Projects</TabsTrigger>
        </TabsList>

        {/* Recent Activity Tab */}
        <TabsContent value="activity" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Recent Business Activity</CardTitle>
                <Button variant="outline" size="sm">
                  View All
                </Button>
              </div>
              <CardDescription>Latest proposals, invoices, and payments</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {activities.map(activity => {
                  const IconComponent = ACTIVITY_ICONS[activity.type];
                  return (
                    <div
                      key={activity.id}
                      className="flex items-center space-x-4 p-3 rounded-lg border hover:bg-muted/30"
                    >
                      <div className={cn("p-2 rounded-lg", ACTIVITY_COLORS[activity.type])}>
                        <IconComponent className="h-5 w-5" />
                      </div>

                      <div className="flex-1">
                        <div className="font-medium text-sm">{activity.title}</div>
                        <div className="text-xs text-muted-foreground">
                          {activity.client} • {formatDate(activity.date)}
                        </div>
                      </div>

                      <div className="text-right space-y-1">
                        {activity.amount && (
                          <div className="font-medium text-sm">
                            {formatCurrency(activity.amount)}
                          </div>
                        )}
                        <Badge
                          variant="secondary"
                          className={cn("text-xs", STATUS_COLORS[activity.status])}
                        >
                          {activity.status}
                        </Badge>
                      </div>

                      <ArrowRightIcon className="h-4 w-4 text-muted-foreground" />
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Active Projects Tab */}
        <TabsContent value="projects" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Active Projects Overview</CardTitle>
                <Button variant="outline" size="sm">
                  <PlusIcon className="mr-2 h-4 w-4" />
                  New Project
                </Button>
              </div>
              <CardDescription>Current project status and progress tracking</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {projects.map(project => (
                  <Card key={project.id}>
                    <CardContent className="pt-4">
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="font-medium">{project.name}</div>
                            <div className="text-sm text-muted-foreground">
                              {project.client}
                            </div>
                          </div>
                          <div className="text-right space-y-1">
                            <div className="font-medium">{formatCurrency(project.value)}</div>
                            <Badge
                              variant="secondary"
                              className={cn("text-xs", PROJECT_STATUS_COLORS[project.status])}
                            >
                              {project.status}
                            </Badge>
                          </div>
                        </div>

                        <div className="space-y-2">
                          <div className="flex items-center justify-between text-sm">
                            <span>Progress</span>
                            <span>{project.progress}%</span>
                          </div>
                          <Progress value={project.progress} className="h-2" />
                        </div>

                        <div className="flex items-center justify-between text-sm">
                          <div className="flex items-center space-x-1 text-muted-foreground">
                            <ClockIcon className="h-4 w-4" />
                            <span>Deadline: {formatDate(project.deadline)}</span>
                          </div>
                          {new Date(project.deadline) < new Date() && project.status !== 'completed' && (
                            <div className="flex items-center space-x-1 text-red-600">
                              <ExclamationTriangleIcon className="h-4 w-4" />
                              <span className="text-xs">Overdue</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Alerts/Notifications */}
      {metrics.overdueInvoices > 0 && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-3">
              <ExclamationTriangleIcon className="h-6 w-6 text-red-500" />
              <div>
                <div className="font-medium text-red-800">
                  {metrics.overdueInvoices} Overdue Invoice{metrics.overdueInvoices > 1 ? 's' : ''}
                </div>
                <div className="text-sm text-red-600">
                  Follow up with clients on outstanding payments
                </div>
              </div>
              <div className="ml-auto">
                <Button variant="outline" size="sm" className="border-red-300 text-red-700">
                  Review Invoices
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
