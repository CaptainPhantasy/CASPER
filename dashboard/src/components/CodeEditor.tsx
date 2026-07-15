import { useRef, useState, useEffect } from 'react';
import Editor, { OnChange, OnMount } from '@monaco-editor/react';
import { editor } from 'monaco-editor';
import { useToast } from '@/hooks/use-toast';
import { Icon } from './icons/IconMapping';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { API_BASE } from '@/services/api';

interface CodeEditorProps {
  filePath: string;
  initialContent: string;
  language?: string;
  readOnly?: boolean;
  className?: string;
  onSave?: (content: string) => Promise<void>;
  onContentChange?: (content: string) => void;
}

export function CodeEditor({
  filePath,
  initialContent,
  language = 'typescript',
  readOnly = false,
  className,
  onSave,
  onContentChange,
}: CodeEditorProps) {
  const { toast } = useToast();
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const [content, setContent] = useState(initialContent);
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);

  // Detect language from file extension
  const detectLanguage = (path: string): string => {
    const ext = path.split('.').pop()?.toLowerCase();
    const languageMap: Record<string, string> = {
      js: 'javascript',
      jsx: 'javascript',
      ts: 'typescript',
      tsx: 'typescript',
      py: 'python',
      java: 'java',
      c: 'c',
      cpp: 'cpp',
      cs: 'csharp',
      go: 'go',
      rs: 'rust',
      rb: 'ruby',
      php: 'php',
      swift: 'swift',
      kt: 'kotlin',
      scala: 'scala',
      sh: 'shell',
      bash: 'shell',
      zsh: 'shell',
      ps1: 'powershell',
      yml: 'yaml',
      yaml: 'yaml',
      json: 'json',
      xml: 'xml',
      html: 'html',
      css: 'css',
      scss: 'scss',
      sass: 'sass',
      less: 'less',
      sql: 'sql',
      md: 'markdown',
      markdown: 'markdown',
      dockerfile: 'dockerfile',
      makefile: 'makefile',
      toml: 'toml',
      ini: 'ini',
      conf: 'ini',
    };
    return languageMap[ext || ''] || 'plaintext';
  };

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;

    // Configure editor options
    editor.updateOptions({
      minimap: { enabled: true },
      fontSize: 14,
      fontFamily: '"Fira Code", "Cascadia Code", "JetBrains Mono", monospace',
      fontLigatures: true,
      renderWhitespace: 'selection',
      bracketPairColorization: { enabled: true },
      formatOnPaste: true,
      formatOnType: true,
      automaticLayout: true,
    });

    // Add keyboard shortcuts
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      handleSave();
    });

    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyF, () => {
      editor.getAction('actions.find')?.run();
    });

    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.KeyF, () => {
      editor.getAction('editor.action.formatDocument')?.run();
    });
  };

  const handleEditorChange: OnChange = (value, _event) => {
    const newContent = value || '';
    setContent(newContent);
    setIsDirty(newContent !== initialContent);
    onContentChange?.(newContent);
  };

  const handleSave = async () => {
    if (readOnly || !isDirty || isSaving) return;

    setIsSaving(true);
    try {
      if (onSave) {
        await onSave(content);
      } else {
        // Default save implementation via API
        const response = await fetch(`${API_BASE}/api/workspace/file/save`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            path: filePath,
            content: content,
          }),
        });

        if (!response.ok) {
          throw new Error(`Failed to save: ${response.statusText}`);
        }
      }

      setIsDirty(false);
      setLastSaved(new Date());
      toast({
        title: 'File saved',
        description: `Successfully saved ${filePath}`,
      });
    } catch (error) {
      toast({
        title: 'Save failed',
        description: error instanceof Error ? error.message : 'Failed to save file',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleUndo = () => {
    editorRef.current?.trigger('keyboard', 'undo', null);
  };

  const handleRedo = () => {
    editorRef.current?.trigger('keyboard', 'redo', null);
  };

  const handleCopy = () => {
    const selection = editorRef.current?.getSelection();
    if (selection) {
      const text = editorRef.current?.getModel()?.getValueInRange(selection);
      if (text) {
        navigator.clipboard.writeText(text);
        toast({
          title: 'Copied',
          description: 'Selection copied to clipboard',
        });
      }
    }
  };

  const handleFormat = () => {
    editorRef.current?.getAction('editor.action.formatDocument')?.run();
  };

  // Auto-save on blur or after inactivity
  useEffect(() => {
    const autoSaveTimer = setTimeout(() => {
      if (isDirty && !readOnly) {
        handleSave();
      }
    }, 5000); // Auto-save after 5 seconds of inactivity

    return () => clearTimeout(autoSaveTimer);
  }, [content, isDirty]);

  // Keyboard shortcut hint
  const saveShortcut = navigator.platform.match('Mac') ? '⌘S' : 'Ctrl+S';

  return (
    <div className={cn('flex h-full flex-col', className)}>
      {/* Toolbar */}
      <div className="flex items-center justify-between border-b bg-card/60 px-4 py-2">
        <div className="flex items-center gap-2">
          <Icon name="file-text" className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">{filePath}</span>
          {isDirty && (
            <Badge variant="outline" className="ml-2">
              Modified
            </Badge>
          )}
          {readOnly && (
            <Badge variant="secondary" className="ml-2">
              Read Only
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-2">
          {lastSaved && (
            <span className="text-xs text-muted-foreground">
              Last saved: {lastSaved.toLocaleTimeString()}
            </span>
          )}

          {!readOnly && (
            <>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleUndo}
                disabled={isSaving}
                title="Undo"
              >
                <Icon name="undo" className="h-4 w-4" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleRedo}
                disabled={isSaving}
                title="Redo"
              >
                <Icon name="redo" className="h-4 w-4" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleCopy}
                title="Copy selection"
              >
                <Icon name="copy" className="h-4 w-4" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleFormat}
                disabled={isSaving}
                title="Format document"
              >
                <Icon name="search" className="h-4 w-4" />
              </Button>
              <div className="mx-2 h-4 w-px bg-border" />
              <Button
                size="sm"
                variant={isDirty ? 'default' : 'ghost'}
                onClick={handleSave}
                disabled={!isDirty || isSaving}
                title={`Save (${saveShortcut})`}
              >
                {isSaving ? (
                  <Icon name="loader" className="h-4 w-4 animate-spin" />
                ) : (
                  <Icon name="device-floppy" className="h-4 w-4" />
                )}
                <span className="ml-2">Save</span>
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1">
        <Editor
          height="100%"
          language={language || detectLanguage(filePath)}
          value={content}
          onChange={handleEditorChange}
          onMount={handleEditorDidMount}
          theme="vs-dark"
          options={{
            readOnly,
            wordWrap: 'on',
            scrollBeyondLastLine: false,
            smoothScrolling: true,
          }}
          loading={
            <div className="flex h-full items-center justify-center">
              <Icon name="loader" className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          }
        />
      </div>

      {/* Status bar */}
      <div className="flex items-center justify-between border-t bg-card/60 px-4 py-1 text-xs">
        <div className="flex items-center gap-4 text-muted-foreground">
          <span>{detectLanguage(filePath).toUpperCase()}</span>
          <span>UTF-8</span>
          {editorRef.current && (
            <>
              <span>
                Ln {editorRef.current.getPosition()?.lineNumber || 0},
                Col {editorRef.current.getPosition()?.column || 0}
              </span>
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isDirty ? (
            <div className="flex items-center gap-1 text-yellow-500">
              <Icon name="alert-circle" className="h-3 w-3" />
              <span>Unsaved changes</span>
            </div>
          ) : lastSaved ? (
            <div className="flex items-center gap-1 text-green-500">
              <Icon name="circle-check" className="h-3 w-3" />
              <span>Saved</span>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default CodeEditor;
