import { wsManager } from './websocket';
import * as api from './api';
import { toast } from '@/hooks/use-toast';

export interface CommandResult {
  success: boolean;
  output?: string;
  error?: string;
  data?: any;
  executionTime?: number;
}

export interface CommandOptions {
  sessionId?: string;
  showProgress?: boolean;
  showToasts?: boolean;
  timeout?: number;
}

class CommandService {
  private commandQueue: Map<string, { resolve: Function; reject: Function; startTime: number }> = new Map();

  constructor() {
    // Listen for command completion events from WebSocket
    wsManager.on((message) => {
      if (message.type === 'command_completed' && message.data?.commandId) {
        this.handleCommandCompletion(String(message.data.commandId), {
          success: message.data.success !== false,
          output: message.data.output as string | undefined,
          error: message.data.error as string | undefined,
          data: message.data,
        });
      }
    });
  }

  private handleCommandCompletion(commandId: string, result: CommandResult) {
    const pending = this.commandQueue.get(commandId);
    if (pending) {
      const executionTime = Date.now() - pending.startTime;
      result.executionTime = executionTime;

      if (result.success) {
        pending.resolve(result);
      } else {
        pending.reject(new Error(result.error || 'Command execution failed'));
      }

      this.commandQueue.delete(commandId);
    }
  }

  // Core Commands
  async executeTask(description: string, priority: 'low' | 'medium' | 'high' = 'medium', options: CommandOptions = {}): Promise<CommandResult> {
    try {
      if (options.showToasts !== false) {
        toast({
          title: 'Task Submitted',
          description: `Executing: ${description.substring(0, 50)}${description.length > 50 ? '...' : ''}`,
        });
      }

      const result = await api.submitTask(description, priority);
      return {
        success: true,
        data: result,
        output: `Task submitted successfully with ID: ${result.task_id}`,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      if (options.showToasts !== false) {
        toast({
          title: 'Task Execution Failed',
          description: errorMessage,
          variant: 'destructive',
        });
      }
      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  async analyzeTask(description: string, _options: CommandOptions = {}): Promise<CommandResult> {
    try {
      const result = await api.analyzeTask(description);
      return {
        success: true,
        data: result,
        output: `Task analyzed - Complexity: ${result.metrics.complexity}`,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  // Development Commands
  async createComponent(type: string, name: string, componentOptions: any = {}, options: CommandOptions = {}): Promise<CommandResult> {
    try {
      const result = await api.createComponent(type, name, componentOptions);
      if (options.showToasts !== false) {
        toast({
          title: 'Component Created',
          description: `${type} component '${name}' created successfully`,
        });
      }
      return {
        success: true,
        data: result,
        output: `Created ${type} component: ${name}`,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      if (options.showToasts !== false) {
        toast({
          title: 'Component Creation Failed',
          description: errorMessage,
          variant: 'destructive',
        });
      }
      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  async runTests(testType: string = 'all', path?: string, options: CommandOptions = {}): Promise<CommandResult> {
    try {
      const result = await api.runTests(testType, path);
      const passed = result.success !== false;

      if (options.showToasts !== false) {
        toast({
          title: passed ? 'Tests Passed' : 'Tests Failed',
          description: `${testType} tests completed`,
          variant: passed ? 'default' : 'destructive',
        });
      }

      return {
        success: passed,
        data: result,
        output: `Tests completed - ${passed ? 'PASSED' : 'FAILED'}`,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  async buildProject(target: string = 'production', buildOptions: any = {}, options: CommandOptions = {}): Promise<CommandResult> {
    try {
      const result = await api.buildProject(target, buildOptions);
      const success = result.success !== false;

      if (options.showToasts !== false) {
        toast({
          title: success ? 'Build Successful' : 'Build Failed',
          description: `${target} build completed`,
          variant: success ? 'default' : 'destructive',
        });
      }

      return {
        success,
        data: result,
        output: `Build ${success ? 'completed successfully' : 'failed'}`,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  async deployApplication(environment: string, deployOptions: any = {}, options: CommandOptions = {}): Promise<CommandResult> {
    try {
      const result = await api.deployApplication(environment, deployOptions);
      const success = result.success !== false;

      if (options.showToasts !== false) {
        toast({
          title: success ? 'Deployment Successful' : 'Deployment Failed',
          description: `Deployed to ${environment}`,
          variant: success ? 'default' : 'destructive',
        });
      }

      return {
        success,
        data: result,
        output: `Deployment to ${environment} ${success ? 'completed successfully' : 'failed'}`,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  // AI Commands
  async aiReviewCode(files: string[], focusAreas: string[] = [], options: CommandOptions = {}): Promise<CommandResult> {
    try {
      const result = await api.aiReviewCode(files, focusAreas);

      if (options.showToasts !== false) {
        toast({
          title: 'AI Code Review Complete',
          description: `Reviewed ${files.length} file(s)`,
        });
      }

      return {
        success: true,
        data: result,
        output: `AI code review completed for ${files.length} file(s)`,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  async aiExplainCode(codeSnippet: string, context?: string, _options: CommandOptions = {}): Promise<CommandResult> {
    try {
      const result = await api.aiExplainCode(codeSnippet, context);
      return {
        success: true,
        data: result,
        output: result.explanation || 'Code explanation generated',
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  // Business Commands
  async generateInvoice(clientInfo: any, items: any[], invoiceOptions: any = {}, options: CommandOptions = {}): Promise<CommandResult> {
    try {
      const result = await api.generateInvoice(clientInfo, items, invoiceOptions);

      if (options.showToasts !== false) {
        toast({
          title: 'Invoice Generated',
          description: `Invoice created for ${clientInfo.name || 'client'}`,
        });
      }

      return {
        success: true,
        data: result,
        output: `Invoice generated successfully`,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  async createProposal(clientName: string, projectDescription: string, templateType: string = 'standard', options: CommandOptions = {}): Promise<CommandResult> {
    try {
      const result = await api.createProposal(clientName, projectDescription, templateType);

      if (options.showToasts !== false) {
        toast({
          title: 'Proposal Created',
          description: `Business proposal created for ${clientName}`,
        });
      }

      return {
        success: true,
        data: result,
        output: `Proposal created for ${clientName}`,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  // Utility Commands
  async searchCodebase(query: string, fileTypes: string[] = [], caseSensitive: boolean = false, _options: CommandOptions = {}): Promise<CommandResult> {
    try {
      const result = await api.searchCodebase(query, fileTypes, caseSensitive);
      return {
        success: true,
        data: result,
        output: `Found ${result.matches?.length || 0} matches for "${query}"`,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  async backupProject(includeDependencies: boolean = false, options: CommandOptions = {}): Promise<CommandResult> {
    try {
      const result = await api.backupProject(includeDependencies);

      if (options.showToasts !== false) {
        toast({
          title: 'Backup Created',
          description: 'Project backup completed successfully',
        });
      }

      return {
        success: true,
        data: result,
        output: `Project backup created: ${result.backupId || 'unknown'}`,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  // Terminal Integration
  async executeTerminalCommand(command: string, sessionId?: string, _options: CommandOptions = {}): Promise<CommandResult> {
    try {
      // Use provided session ID or create a new one
      let terminalSessionId = sessionId;
      if (!terminalSessionId) {
        const sessionResult = await api.createTerminalSession();
        terminalSessionId = sessionResult.session_id;
      }

      if (!terminalSessionId) {
        throw new Error('Unable to establish a terminal session');
      }

      const result = await api.executeTerminalCommand(terminalSessionId, command);
      return {
        success: result.exit_code === 0,
        output: result.output,
        error: result.error,
        data: result,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  // Approval System Integration
  async approveOperation(approvalId: string, options: CommandOptions = {}): Promise<CommandResult> {
    try {
      const result = await api.approveOperation(approvalId);

      if (options.showToasts !== false) {
        toast({
          title: 'Operation Approved',
          description: `Approval ${approvalId} has been approved`,
        });
      }

      return {
        success: true,
        data: result,
        output: `Operation ${approvalId} approved`,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  async rejectOperation(approvalId: string, options: CommandOptions = {}): Promise<CommandResult> {
    try {
      const result = await api.rejectOperation(approvalId);

      if (options.showToasts !== false) {
        toast({
          title: 'Operation Rejected',
          description: `Approval ${approvalId} has been rejected`,
          variant: 'destructive',
        });
      }

      return {
        success: true,
        data: result,
        output: `Operation ${approvalId} rejected`,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  // Status and Information
  async getSystemStatus(_options: CommandOptions = {}): Promise<CommandResult> {
    try {
      const result = await api.getAgentStatus();
      return {
        success: true,
        data: result,
        output: `System Status - Active Tasks: ${result.active_tasks}, Agents: ${result.total_agents}`,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  async getPendingApprovals(_options: CommandOptions = {}): Promise<CommandResult> {
    try {
      const result = await api.getPendingApprovals();
      return {
        success: true,
        data: result,
        output: `Found ${result.length || 0} pending approval(s)`,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  // Generic command parser for natural language input
  async parseAndExecute(input: string, options: CommandOptions = {}): Promise<CommandResult> {
    const trimmedInput = input.trim().toLowerCase();

    // Task execution patterns
    if (trimmedInput.startsWith('task ') || trimmedInput.startsWith('/task ')) {
      const description = input.substring(input.indexOf(' ') + 1);
      return this.executeTask(description, 'medium', options);
    }

    // Analysis patterns
    if (trimmedInput.startsWith('analyze ') || trimmedInput.startsWith('/analyze ')) {
      const description = input.substring(input.indexOf(' ') + 1);
      return this.analyzeTask(description, options);
    }

    // Status patterns
    if (trimmedInput === 'status' || trimmedInput === '/status') {
      return this.getSystemStatus(options);
    }

    // Approval patterns
    if (trimmedInput === 'approvals' || trimmedInput === '/approvals') {
      return this.getPendingApprovals(options);
    }

    // Test patterns
    if (trimmedInput.startsWith('test') || trimmedInput.startsWith('/test')) {
      const parts = input.split(' ');
      const testType = parts[1] || 'all';
      const path = parts[2];
      return this.runTests(testType, path, options);
    }

    // Build patterns
    if (trimmedInput.startsWith('build') || trimmedInput.startsWith('/build')) {
      const parts = input.split(' ');
      const target = parts[1] || 'production';
      return this.buildProject(target, {}, options);
    }

    // For unrecognized commands, try to execute as a task
    return this.executeTask(input, 'medium', options);
  }
}

export const commandService = new CommandService();
export default commandService;
