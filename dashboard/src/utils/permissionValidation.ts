import { type ApprovalMode } from '../components/ApprovalModeSelector';

export interface OperationContext {
  type: 'file_create' | 'file_edit' | 'file_delete' | 'command_execute' | 'api_call';
  path?: string;
  command?: string;
  endpoint?: string;
  content?: string;
  details?: Record<string, any>;
}

export interface RiskAssessment {
  level: 'low' | 'medium' | 'high';
  factors: string[];
  score: number; // 0-100
}

export interface ValidationResult {
  allowed: boolean;
  requiresApproval: boolean;
  risk: RiskAssessment;
  reason: string;
  autoApprove: boolean;
}

// Critical system paths that require careful handling
const CRITICAL_PATHS = [
  '/etc',
  '/usr',
  '/bin',
  '/sbin',
  '/boot',
  '/proc',
  '/sys',
  'package.json',
  'package-lock.json',
  'yarn.lock',
  'pnpm-lock.yaml',
  'tsconfig.json',
  'jest.config',
  'webpack.config',
  'vite.config',
  '.env',
  '.env.local',
  '.env.production',
  'Dockerfile',
  'docker-compose',
  '.gitignore',
  '.eslintrc',
  '.prettierrc',
  'babel.config',
  'rollup.config',
  'next.config',
  'nuxt.config',
];

// Risky file extensions
const RISKY_EXTENSIONS = [
  '.sh', '.bash', '.zsh', '.fish',      // Shell scripts
  '.bat', '.cmd', '.ps1',               // Windows scripts
  '.py', '.rb', '.pl', '.php',          // Executable scripts
  '.exe', '.dll', '.so', '.dylib',      // Binaries
  '.sql', '.db', '.sqlite',             // Database files
];

// Dangerous commands
const DANGEROUS_COMMANDS = [
  'rm', 'rmdir', 'del', 'delete',       // File deletion
  'mv', 'move', 'cp', 'copy',           // File operations
  'chmod', 'chown', 'chgrp',            // Permission changes
  'sudo', 'su',                         // Privilege escalation
  'kill', 'killall', 'pkill',          // Process termination
  'shutdown', 'reboot', 'halt',         // System control
  'dd', 'fdisk', 'mkfs',               // Disk operations
  'iptables', 'ufw', 'firewall-cmd',   // Network/firewall
  'crontab', 'systemctl', 'service',    // System services
  'passwd', 'usermod', 'useradd',       // User management
  'mount', 'umount',                    // Filesystem mounting
];

// Safe API endpoints (patterns)
const SAFE_API_PATTERNS = [
  /^\/api\/workspace\/info$/,
  /^\/api\/workspace\/filetree$/,
  /^\/api\/workspace\/search\?/,
  /^\/api\/settings$/,
  /^\/api\/status$/,
  /^\/api\/agents$/,
  /^\/api\/tasks\//,
];

/**
 * Assess the risk level of an operation
 */
export function assessRisk(operation: OperationContext): RiskAssessment {
  const factors: string[] = [];
  let score = 0;

  switch (operation.type) {
    case 'file_delete':
      factors.push('File deletion operation');
      score += 40;
      break;

    case 'command_execute':
      factors.push('Command execution');
      score += 30;

      if (operation.command) {
        const cmd = operation.command.toLowerCase().trim();
        const isDangerous = DANGEROUS_COMMANDS.some(dangerous =>
          cmd.startsWith(dangerous + ' ') || cmd === dangerous
        );

        if (isDangerous) {
          factors.push('Dangerous command detected');
          score += 40;
        }

        // Check for shell operators
        if (cmd.includes('&&') || cmd.includes('||') || cmd.includes(';') || cmd.includes('|')) {
          factors.push('Command chaining/piping detected');
          score += 20;
        }

        // Check for sudo/root operations
        if (cmd.includes('sudo') || cmd.includes('su ')) {
          factors.push('Privilege escalation detected');
          score += 50;
        }
      }
      break;

    case 'file_edit':
    case 'file_create':
      if (operation.path) {
        const isCritical = CRITICAL_PATHS.some(critical =>
          operation.path!.includes(critical)
        );

        if (isCritical) {
          factors.push('Critical system file');
          score += 30;
        }

        const hasRiskyExtension = RISKY_EXTENSIONS.some(ext =>
          operation.path!.endsWith(ext)
        );

        if (hasRiskyExtension) {
          factors.push('Potentially executable file');
          score += 25;
        }

        // Check for configuration files
        if (operation.path.includes('config') || operation.path.includes('.rc')) {
          factors.push('Configuration file');
          score += 15;
        }
      }

      if (operation.content) {
        // Check for dangerous content patterns
        if (operation.content.includes('rm -rf') || operation.content.includes('del /f')) {
          factors.push('Destructive commands in content');
          score += 35;
        }

        if (operation.content.includes('eval(') || operation.content.includes('exec(')) {
          factors.push('Code execution patterns detected');
          score += 30;
        }

        if (operation.content.includes('subprocess') || operation.content.includes('system(')) {
          factors.push('System command execution detected');
          score += 25;
        }
      }

      score += operation.type === 'file_create' ? 10 : 5;
      break;

    case 'api_call':
      if (operation.endpoint) {
        const isSafe = SAFE_API_PATTERNS.some(pattern =>
          pattern.test(operation.endpoint!)
        );

        if (!isSafe) {
          factors.push('Non-whitelisted API endpoint');
          score += 20;
        }

        // Check for destructive operations
        if (operation.endpoint.includes('delete') || operation.endpoint.includes('remove')) {
          factors.push('Destructive API operation');
          score += 30;
        }
      }

      score += 15;
      break;

    default:
      factors.push('Unknown operation type');
      score += 25;
  }

  // Determine risk level based on score
  let level: 'low' | 'medium' | 'high';
  if (score >= 60) {
    level = 'high';
  } else if (score >= 30) {
    level = 'medium';
  } else {
    level = 'low';
  }

  return { level, factors, score: Math.min(100, score) };
}

/**
 * Validate an operation based on approval mode and risk assessment
 */
export function validateOperation(
  operation: OperationContext,
  approvalMode: ApprovalMode
): ValidationResult {
  const risk = assessRisk(operation);

  let allowed = true;
  let requiresApproval = false;
  let autoApprove = false;
  let reason = '';

  switch (approvalMode) {
    case 'STRICT':
      requiresApproval = true;
      reason = 'Strict mode requires approval for all operations';
      break;

    case 'AUTO':
      if (risk.level === 'high') {
        requiresApproval = true;
        reason = 'High-risk operation requires manual approval';
      } else if (risk.level === 'medium') {
        requiresApproval = true;
        reason = 'Medium-risk operation requires approval in auto mode';
      } else {
        autoApprove = true;
        reason = 'Low-risk operation auto-approved';
      }
      break;

    case 'YOLO':
      autoApprove = true;
      reason = 'YOLO mode auto-approves all operations';
      break;

    default:
      requiresApproval = true;
      reason = 'Unknown approval mode, defaulting to strict';
  }

  return {
    allowed,
    requiresApproval,
    risk,
    reason,
    autoApprove
  };
}

/**
 * Generate a human-readable explanation of the risk assessment
 */
export function explainRisk(risk: RiskAssessment): string {
  const { level, factors, score } = risk;

  let explanation = `Risk Level: ${level.toUpperCase()} (Score: ${score}/100)\n\n`;

  if (factors.length > 0) {
    explanation += 'Risk Factors:\n';
    factors.forEach((factor, index) => {
      explanation += `${index + 1}. ${factor}\n`;
    });
  }

  switch (level) {
    case 'low':
      explanation += '\nThis operation is considered safe and has minimal risk.';
      break;
    case 'medium':
      explanation += '\nThis operation has moderate risk. Review carefully before approving.';
      break;
    case 'high':
      explanation += '\nThis operation is high-risk and could cause significant damage. Approve only if you fully understand the implications.';
      break;
  }

  return explanation;
}

/**
 * Check if a path is considered critical
 */
export function isCriticalPath(path: string): boolean {
  return CRITICAL_PATHS.some(critical => path.includes(critical));
}

/**
 * Check if a command is considered dangerous
 */
export function isDangerousCommand(command: string): boolean {
  const cmd = command.toLowerCase().trim();
  return DANGEROUS_COMMANDS.some(dangerous =>
    cmd.startsWith(dangerous + ' ') || cmd === dangerous
  );
}

/**
 * Get approval mode configuration
 */
export function getApprovalModeConfig(mode: ApprovalMode) {
  switch (mode) {
    case 'STRICT':
      return {
        name: 'Strict Mode',
        description: 'All operations require explicit approval',
        autoApproveThreshold: -1, // Never auto-approve
        showAllOperations: true,
        auditTrail: true,
      };

    case 'AUTO':
      return {
        name: 'Auto Mode',
        description: 'Low-risk operations auto-approved, others require approval',
        autoApproveThreshold: 30, // Auto-approve if score < 30
        showAllOperations: true,
        auditTrail: true,
      };

    case 'YOLO':
      return {
        name: 'YOLO Mode',
        description: 'All operations auto-approved (DANGEROUS)',
        autoApproveThreshold: 100, // Auto-approve everything
        showAllOperations: false,
        auditTrail: false,
      };

    default:
      return getApprovalModeConfig('STRICT');
  }
}