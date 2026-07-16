import './App.css';
import * as React from 'react';
import {
  IconCode as Code2,
  IconShield as Shield,
  IconFolderOpen as FolderOpen,
  IconSearch as Search,
  IconBell as Bell,
  IconUser as User,
  IconChevronRight as ChevronRight,
  IconGitBranch as GitBranch,
  IconWifi as Wifi,
  IconWifiOff as WifiOff,
  IconLoader2 as Loader2
} from '@tabler/icons-react';

import { WelcomeScreen } from '@/components/WelcomeScreen';
import { FileTree } from '@/components/FileTree';
import { FileViewer } from '@/components/FileViewer';
import { AgentActivityDashboard } from '@/components/AgentActivityDashboard';
import { ApprovalQueue } from '@/components/ApprovalQueue';
import { TerminalPanel } from '@/components/Terminal';
import { CommandPalette } from '@/components/CommandPalette';
import { CasperChat } from '@/components/CasperChat';
import { LLMSelector } from '@/components/LLMSelector';
import { ApprovalModeStatus, type ApprovalMode } from '@/components/ApprovalModeSelector';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { Toaster } from '@/components/ui/toaster';
import { useToast } from '@/hooks/use-toast';
import { useFileStore } from '@/stores/fileStore';
import { useAgentStore } from '@/stores/agentStore';
import { getWorkspaceInfo, getApprovalMode } from '@/services/api';
import { wsManager, ConnectionStatus } from '@/services/websocket';
import { cn } from '@/lib/utils';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';

export default function AppImproved() {
  const { toast } = useToast();
  const { openFile, openFiles } = useFileStore();
  const pendingApprovals = useAgentStore((state) => state.approvalQueue.filter(a => a.status === 'pending').length);
  const [selectedFilePath, setSelectedFilePath] = React.useState<string | null>(null);
  const [workspaceInfo, setWorkspaceInfo] = React.useState<any>(null);
  const [workspaceLoading, setWorkspaceLoading] = React.useState(true);
  const [commandOpen, setCommandOpen] = React.useState(false);
  const [connectionStatus, setConnectionStatus] = React.useState<ConnectionStatus>('disconnected');
  const [terminalHeight, setTerminalHeight] = React.useState(30);
  const [explorerPanelSize, setExplorerPanelSize] = React.useState(20);
  const [approvalMode, setApprovalMode] = React.useState<ApprovalMode>('STRICT');

  // Initialize workspace
  React.useEffect(() => {
    const loadWorkspace = async () => {
      try {
        setWorkspaceLoading(true);
        const info = await getWorkspaceInfo();
        setWorkspaceInfo(info);
      } catch (error) {
        // Mock data for testing
        setWorkspaceInfo({
          workspace: { path: '/project', language: 'TypeScript', framework: 'React' },
          current_path: '/project'
        });
      } finally {
        setWorkspaceLoading(false);
      }
    };
    loadWorkspace();
  }, []);

  // Load approval mode from settings
  React.useEffect(() => {
    const loadApprovalMode = async () => {
      try {
        // Try to get approval mode from API
        const mode = await getApprovalMode();
        setApprovalMode(mode as ApprovalMode);
      } catch (error) {
        // Default to STRICT if settings can't be loaded
        setApprovalMode('STRICT');
      }
    };
    loadApprovalMode();
  }, []);

  // WebSocket connection
  React.useEffect(() => {
    const unsubscribe = wsManager.onConnectionChange((status) => setConnectionStatus(status));
    wsManager.connect();
    return () => {
      unsubscribe();
      wsManager.disconnect();
    };
  }, []);

  // Keyboard shortcuts
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
      const modKey = isMac ? e.metaKey : e.ctrlKey;

      // Cmd/Ctrl + K - Command Palette
      if (modKey && e.key === 'k') {
        e.preventDefault();
        setCommandOpen(true);
      }

      // Cmd/Ctrl + B - Toggle sidebar (File Explorer)
      if (modKey && e.key === 'b') {
        e.preventDefault();
        // Toggle first panel visibility - would need ref to panel
      }

      // Cmd/Ctrl + J - Toggle terminal
      if (modKey && e.key === 'j') {
        e.preventDefault();
        setTerminalHeight(prev => prev === 0 ? 30 : 0);
      }

      // Cmd/Ctrl + Shift + P - Command Palette (alternative)
      if (modKey && e.shiftKey && e.key === 'P') {
        e.preventDefault();
        setCommandOpen(true);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleFileSelect = (file: any) => {
    setSelectedFilePath(file.path);
    openFile(file.path);
  };

  const handleWelcomeAction = (action: string) => {
    switch (action) {
      case 'open-folder':
        // Show file explorer panel if hidden
        if (explorerPanelSize === 0) {
          setExplorerPanelSize(20);
        }
        toast({
          title: "File Explorer",
          description: "Browse files in the left panel. Click any file to open it.",
        });
        break;
      case 'new-file':
        {
        // Create a new untitled file
        const newFile = {
          path: `/untitled-${Date.now()}.txt`,
          name: `untitled-${Date.now()}.txt`,
        };
        openFile(newFile);
        toast({
          title: "New File Created",
          description: "Start typing to edit your new file.",
        });
        break;
        }
      case 'open-terminal':
        // Open terminal panel
        if (terminalHeight === 0 || terminalHeight < 20) {
          setTerminalHeight(40);
        }
        toast({
          title: "Terminal Opened",
          description: "Omega-secured terminal is ready for commands.",
        });
        break;
      case 'search':
        // Open command palette
        setCommandOpen(true);
        break;
    }
  };

  const hasOpenFiles = openFiles.length > 0;

  return (
    <div className="flex h-screen flex-col bg-background text-foreground" data-testid="dashboard-loaded">
      <Toaster />

      {/* Slim Header - 40px */}
      <header className="flex h-10 items-center justify-between border-b bg-card/50 px-4">
        {/* Left: Logo & Workspace */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Code2 className="h-4 w-4 text-primary" />
            <span className="font-semibold text-sm">CASPER</span>
          </div>
          <Separator orientation="vertical" className="h-5" />
          <div className="flex items-center gap-2 text-sm">
            <FolderOpen className="h-3 w-3 text-muted-foreground" />
            <span className="max-w-[200px] truncate">
              {workspaceInfo?.workspace?.path || 'No workspace'}
            </span>
            {workspaceInfo && (
              <>
                <ChevronRight className="h-3 w-3 text-muted-foreground" />
                <Badge variant="outline" className="h-5 text-xs">
                  {workspaceInfo.workspace?.language}
                </Badge>
              </>
            )}
          </div>
          {workspaceLoading && <Loader2 className="h-3 w-3 animate-spin" />}
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          <LLMSelector />
          <Separator orientation="vertical" className="h-5" />
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-1 text-xs"
            onClick={() => setCommandOpen(true)}
          >
            <Search className="h-3 w-3" />
            Search
            <Badge variant="secondary" className="ml-1 px-1 py-0 text-[10px]">⌘K</Badge>
          </Button>
          <Button variant="ghost" size="icon" className="h-7 w-7">
            <Bell className="h-3 w-3" />
          </Button>
          <Button variant="ghost" size="icon" className="h-7 w-7">
            <User className="h-3 w-3" />
          </Button>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden">
        <ResizablePanelGroup direction="vertical">
          {/* Work Area */}
          <ResizablePanel defaultSize={100 - terminalHeight} minSize={50}>
            <ResizablePanelGroup direction="horizontal">
              {/* File Explorer - Resizable */}
              <ResizablePanel defaultSize={20} minSize={15} maxSize={40} collapsible>
                <div className="h-full border-r bg-card/30">
                  <div className="flex h-9 items-center justify-between border-b px-3">
                    <span className="text-xs font-medium uppercase text-muted-foreground">Explorer</span>
                    <Button variant="ghost" size="icon" className="h-5 w-5">
                      <FolderOpen className="h-3 w-3" />
                    </Button>
                  </div>
                  <FileTree
                    onFileSelect={handleFileSelect}
                    selectedFile={selectedFilePath ?? undefined}
                    className="h-[calc(100%-2.25rem)]"
                  />
                </div>
              </ResizablePanel>

              <ResizableHandle withHandle />

              {/* Editor Area */}
              <ResizablePanel defaultSize={60} minSize={30}>
                <div className="h-full overflow-hidden">
                  {hasOpenFiles ? (
                    <FileViewer />
                  ) : (
                    <WelcomeScreen onAction={handleWelcomeAction} />
                  )}
                </div>
              </ResizablePanel>

              <ResizableHandle withHandle />

              {/* AI Assistant Panel - Resizable */}
              <ResizablePanel defaultSize={20} minSize={0} maxSize={40} collapsible>
                <div className="h-full border-l bg-card/30">
                  <div className="flex h-9 items-center justify-between border-b px-3">
                    <span className="text-xs font-medium uppercase text-muted-foreground">AI Assistant</span>
                  </div>
                  <Tabs defaultValue="agents" className="h-[calc(100%-2.25rem)]">
                    <TabsList className="h-8 w-full justify-start rounded-none border-b bg-transparent px-3">
                      <TabsTrigger value="chat" className="h-6 text-xs">Chat</TabsTrigger>
                      <TabsTrigger value="agents" className="h-6 text-xs">Agents</TabsTrigger>
                      <TabsTrigger value="approvals" className="h-6 text-xs">
                        Approvals
                        {pendingApprovals > 0 && (
                          <Badge variant="destructive" className="ml-1 h-4 px-1 text-[10px]">
                            {pendingApprovals}
                          </Badge>
                        )}
                      </TabsTrigger>
                    </TabsList>
                    <TabsContent value="chat" className="h-[calc(100%-2rem)] overflow-hidden p-0">
                      <CasperChat
                        className="h-full"
                        onTaskSubmit={(message) => {
                          // Handle task submission from chat
                          console.log('Chat task submission:', message);
                        }}
                      />
                    </TabsContent>
                    <TabsContent value="agents" className="h-[calc(100%-2rem)] overflow-auto p-3">
                      <AgentActivityDashboard />
                    </TabsContent>
                    <TabsContent value="approvals" className="h-[calc(100%-2rem)] overflow-auto p-3">
                      <ApprovalQueue />
                    </TabsContent>
                  </Tabs>
                </div>
              </ResizablePanel>
            </ResizablePanelGroup>
          </ResizablePanel>

          <ResizableHandle />

          {/* Terminal Panel */}
          <ResizablePanel
            defaultSize={terminalHeight}
            minSize={10}
            maxSize={70}
            onResize={(size) => setTerminalHeight(size)}
          >
            <TerminalPanel className="h-full" />
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>

      {/* Status Bar - 25px */}
      <footer className="flex h-6 items-center justify-between border-t bg-card/50 px-4 text-[11px]">
        {/* Left */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <Shield className={cn(
              "h-3 w-3",
              connectionStatus === 'connected' ? "text-green-500" : "text-yellow-500"
            )} />
            <span>Omega: Secure</span>
          </div>
          <Separator orientation="vertical" className="h-3" />
          <ApprovalModeStatus mode={approvalMode} className="text-[10px] px-1 py-0 h-4" />
          <Separator orientation="vertical" className="h-3" />
          <span>Ready</span>
        </div>

        {/* Center */}
        <div className="flex items-center gap-3">
          {selectedFilePath && (
            <>
              <span>Ln 1, Col 1</span>
              <Separator orientation="vertical" className="h-3" />
              <span>UTF-8</span>
              <Separator orientation="vertical" className="h-3" />
              <span>TypeScript</span>
            </>
          )}
        </div>

        {/* Right */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <GitBranch className="h-3 w-3" />
            <span>main</span>
          </div>
          <Separator orientation="vertical" className="h-3" />
          <div className="flex items-center gap-1">
            {connectionStatus === 'connected' ? (
              <>
                <Wifi className="h-3 w-3 text-green-500" />
                <span className="text-green-500">Connected</span>
              </>
            ) : (
              <>
                <WifiOff className="h-3 w-3 text-yellow-500" />
                <span className="text-yellow-500">Connecting</span>
              </>
            )}
          </div>
          <Separator orientation="vertical" className="h-3" />
          <span className="text-yellow-500">⚡ 50ms</span>
        </div>
      </footer>

      {/* Command Palette */}
      <CommandPalette
        open={commandOpen}
        onOpenChange={setCommandOpen}
        onOpenFile={(path: string) => {
          console.log('Opening file:', path);
          // Implementation can be added later
        }}
        onOpenSettings={() => {
          console.log('Opening settings');
          // Implementation can be added later
        }}
        onOpenWorkspace={() => {
          console.log('Opening workspace');
          // Implementation can be added later
        }}
      />
    </div>
  );
}
