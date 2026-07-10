import * as React from "react";
import { Icon } from './icons/IconMapping';
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { getFileTree } from "@/services/api";

interface FileNode {
  type: 'file' | 'folder' | 'directory';
  name: string;
  path: string;
  size?: number | null;
  modified?: string;
  children?: FileNode[];
}

interface FileTreeProps {
  onFileSelect?: (file: FileNode) => void;
  selectedFile?: string;
  className?: string;
  collapsed?: boolean;
  refreshToken?: number;
}

const formatFileSize = (bytes: number | null | undefined): string => {
  if (!bytes) return '';
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
};

const formatModifiedDate = (dateString?: string): string => {
  if (!dateString) return '';
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  return date.toLocaleDateString();
};

const getFileIcon = (fileName: string) => {
  const ext = fileName.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'tsx':
    case 'ts':
    case 'jsx':
    case 'js':
    case 'py':
    case 'java':
    case 'cpp':
    case 'c':
    case 'go':
    case 'rs':
      return <Icon name="file-code" className="h-4 w-4" />;
    case 'md':
    case 'txt':
    case 'doc':
    case 'pdf':
      return <Icon name="file-text" className="h-4 w-4" />;
    case 'png':
    case 'jpg':
    case 'jpeg':
    case 'gif':
    case 'svg':
    case 'ico':
      return <Icon name="image" className="h-4 w-4" />;
    case 'zip':
    case 'tar':
    case 'gz':
    case 'rar':
      return <Icon name="archive" className="h-4 w-4" />;
    default:
      return <Icon name="file" className="h-4 w-4" />;
  }
};

export function FileTree({ onFileSelect, selectedFile, className, collapsed = false, refreshToken }: FileTreeProps) {
  const [fileTree, setFileTree] = React.useState<FileNode[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [expandedFolders, setExpandedFolders] = React.useState<Set<string>>(new Set());

  const normaliseNodes = React.useCallback((nodes: FileNode[] = []): FileNode[] => {
    return nodes.map((node) => {
      const isFolder = node.type === 'folder' || node.type === 'directory';
      return {
        ...node,
        type: isFolder ? 'folder' : 'file',
        children: isFolder ? normaliseNodes(node.children) : undefined,
      };
    });
  }, []);

  const fetchTree = React.useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getFileTree();
      const raw = (data?.file_tree || data?.files || []) as FileNode[];
      setFileTree(normaliseNodes(raw));
    } catch (err) {
      setFileTree([]);
      setError(err instanceof Error ? err.message : 'Failed to load workspace');
    } finally {
      setLoading(false);
    }
  }, [normaliseNodes]);

  React.useEffect(() => {
    fetchTree();
  }, [fetchTree, refreshToken]);

  const toggleFolder = (path: string) => {
    setExpandedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  };

  const handleContextMenuAction = (action: string, node: FileNode) => {
    switch (action) {
      case 'open':
        if (node.type === 'file' && onFileSelect) {
          onFileSelect(node);
        }
        break;
      case 'copy':
        navigator.clipboard.writeText(node.path);
        break;
      case 'delete':
        console.log('Delete:', node.path);
        break;
      case 'rename':
        console.log('Rename:', node.path);
        break;
    }
  };

  const renderNode = (node: FileNode, depth = 0) => {
    const isExpanded = expandedFolders.has(node.path);
    const isSelected = selectedFile === node.path;

    if (node.type === 'folder') {
      return (
        <div key={node.path}>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <div
                className={cn(
                  "group flex items-center gap-1 rounded-md px-2 py-1 text-sm hover:bg-muted cursor-pointer",
                  isSelected && "bg-muted"
                )}
                style={{ paddingLeft: `${depth * 12 + 8}px` }}
                onClick={() => toggleFolder(node.path)}
                onContextMenu={(e) => e.preventDefault()}
              >
                <div className="p-0.5">
                  {isExpanded ? (
                    <Icon name="chevron-down" className="h-3 w-3" />
                  ) : (
                    <Icon name="chevron-right" className="h-3 w-3" />
                  )}
                </div>
                <TooltipProvider delayDuration={700}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div className="flex items-center gap-2 flex-1">
                        {isExpanded ? (
                          <Icon name="folder-open" className="h-4 w-4 text-primary" />
                        ) : (
                          <Icon name="folder" className="h-4 w-4 text-primary" />
                        )}
                        {!collapsed && <span className="truncate">{node.name}</span>}
                      </div>
                    </TooltipTrigger>
                    <TooltipContent side="right">
                      <div className="text-xs space-y-1">
                        <div className="font-semibold">{node.name}</div>
                        <div className="text-muted-foreground">
                          {node.children?.length || 0} items
                        </div>
                        {node.modified && (
                          <div className="text-muted-foreground">
                            Modified: {formatModifiedDate(node.modified)}
                          </div>
                        )}
                      </div>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              <DropdownMenuItem onClick={() => toggleFolder(node.path)}>
                <Icon name="eye" className="mr-2 h-4 w-4" />
                {isExpanded ? 'Collapse' : 'Expand'}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleContextMenuAction('copy', node)}>
                <Icon name="copy" className="mr-2 h-4 w-4" />
                Copy Path
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => handleContextMenuAction('rename', node)}>
                <Icon name="edit" className="mr-2 h-4 w-4" />
                Rename
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => handleContextMenuAction('delete', node)}
                className="text-destructive"
              >
                <Icon name="trash" className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          {isExpanded && node.children && (
            <div>
              {node.children.map((child) => renderNode(child, depth + 1))}
            </div>
          )}
        </div>
      );
    }

    // File node - Click to open, right-click for menu
    return (
      <TooltipProvider key={node.path} delayDuration={700}>
        <Tooltip>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <TooltipTrigger asChild>
                <div
                  className={cn(
                    "group flex items-center gap-2 rounded-md px-2 py-1 text-sm hover:bg-muted cursor-pointer",
                    isSelected && "bg-muted text-foreground"
                  )}
                  style={{ paddingLeft: `${depth * 12 + 28}px` }}
                  onClick={(e) => {
                    // Left click opens file directly
                    if (e.button === 0) {
                      e.preventDefault();
                      e.stopPropagation();
                      onFileSelect?.(node);
                    }
                  }}
                  onContextMenu={(e) => {
                    // Right click opens menu
                    e.preventDefault();
                    // Trigger dropdown programmatically
                  }}
                >
                  {getFileIcon(node.name)}
                  {!collapsed && (
                    <>
                      <span className="truncate flex-1">{node.name}</span>
                      {node.size && (
                        <span className="text-xs text-muted-foreground">
                          {formatFileSize(node.size)}
                        </span>
                      )}
                    </>
                  )}
                </div>
              </TooltipTrigger>
            </DropdownMenuTrigger>
            <TooltipContent side="right">
              <div className="text-xs space-y-1">
                <div className="font-semibold">{node.name}</div>
                {node.size && (
                  <div className="text-muted-foreground">
                    Size: {formatFileSize(node.size)}
                  </div>
                )}
                {node.modified && (
                  <div className="text-muted-foreground">
                    Modified: {formatModifiedDate(node.modified)}
                  </div>
                )}
                <div className="text-muted-foreground">Path: {node.path}</div>
              </div>
            </TooltipContent>
            <DropdownMenuContent align="start">
              <DropdownMenuItem onClick={() => handleContextMenuAction('open', node)}>
                <Icon name="eye" className="mr-2 h-4 w-4" />
                Open
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleContextMenuAction('copy', node)}>
                <Icon name="copy" className="mr-2 h-4 w-4" />
                Copy Path
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => handleContextMenuAction('rename', node)}>
                <Icon name="edit" className="mr-2 h-4 w-4" />
                Rename
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => handleContextMenuAction('delete', node)}
                className="text-destructive"
              >
                <Icon name="trash" className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </Tooltip>
      </TooltipProvider>
    );
  };

  return (
    <div className={cn('h-full', className)}>
      {loading ? (
        <div className="px-4 py-4 text-sm text-muted-foreground">Loading files…</div>
      ) : error ? (
        <div className="flex h-full flex-col items-start justify-center gap-3 px-4 py-6 text-sm text-muted-foreground">
          <span className="font-medium text-destructive">{error}</span>
          <Button variant="outline" size="sm" onClick={fetchTree}>
            Retry
          </Button>
        </div>
      ) : (
        <ScrollArea className="h-full">
          <div className="py-2">
            {fileTree.map((node) => renderNode(node))}
            {fileTree.length === 0 && (
              <div className="px-2 py-4 text-sm text-muted-foreground">
                No files found
              </div>
            )}
          </div>
        </ScrollArea>
      )}
    </div>
  );
}
