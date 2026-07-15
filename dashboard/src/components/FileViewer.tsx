import { Icon } from './icons/IconMapping';
import { useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CodeEditor } from "@/components/CodeEditor";
import { Highlight, themes } from "prism-react-renderer";
import { SaveDialog } from "@/components/SaveDialog";
import { useToast } from "@/hooks/use-toast";

import { useFileStore } from "@/stores/fileStore";
import { cn } from "@/lib/utils";

export function FileViewer() {
  const { openFiles, activeFilePath, closeFile, setActiveFile, updateFileContent, saveFile } = useFileStore();
  const [editMode, setEditMode] = useState<Record<string, boolean>>({});
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [fileToSave, setFileToSave] = useState<string | null>(null);
  const { toast } = useToast();

  const toggleEditMode = (filePath: string) => {
    setEditMode(prev => ({
      ...prev,
      [filePath]: !prev[filePath]
    }));
  };

  const handleSaveFile = async (filePath: string) => {
    // Check if it's an untitled file
    if (filePath.startsWith('/untitled-')) {
      setFileToSave(filePath);
      setSaveDialogOpen(true);
    } else {
      // Save existing file
      const success = await saveFile(filePath);
      if (success) {
        toast({
          title: "File Saved",
          description: `Successfully saved ${filePath}`,
        });
      } else {
        toast({
          title: "Save Failed",
          description: "Failed to save the file. Please try again.",
          variant: "destructive",
        });
      }
    }
  };

  const handleSaveAs = async (newPath: string) => {
    if (fileToSave) {
      const success = await saveFile(fileToSave, newPath);
      if (success) {
        toast({
          title: "File Saved",
          description: `Successfully saved as ${newPath}`,
        });
        setSaveDialogOpen(false);
        setFileToSave(null);
      } else {
        toast({
          title: "Save Failed",
          description: "Failed to save the file. Please try again.",
          variant: "destructive",
        });
      }
    }
  };

  if (openFiles.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <div className="text-center">
          <Icon name="file-text" className="mx-auto h-12 w-12 opacity-50" />
          <p className="mt-4 text-sm">No files open</p>
          <p className="mt-1 text-xs">Select a file from the tree to view its contents</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <Tabs value={activeFilePath || ""} onValueChange={setActiveFile} className="flex h-full flex-col">
      <TabsList className="h-auto w-full justify-start rounded-none border-b bg-card/60 p-0">
        <ScrollArea className="w-full">
          <div className="flex">
            {openFiles.map((file) => (
              <div key={file.path} className="relative flex items-center">
                <TabsTrigger
                  value={file.path}
                  className={cn(
                    "relative rounded-none border-r px-3 py-2 data-[state=active]:bg-background",
                    "data-[state=active]:shadow-none data-[state=active]:after:absolute",
                    "data-[state=active]:after:bottom-0 data-[state=active]:after:left-0",
                    "data-[state=active]:after:right-0 data-[state=active]:after:h-[2px]",
                    "data-[state=active]:after:bg-primary"
                  )}
                >
                  <span className="mr-2 text-sm flex items-center gap-1">
                    {file.isModified && (
                      <span className="h-2 w-2 rounded-full bg-orange-500" title="Unsaved changes" />
                    )}
                    {file.name}
                  </span>
                  {file.isLoading && <Icon name="loader" className="h-3 w-3 animate-spin" />}
                  {file.error && <Icon name="alert-circle" className="h-3 w-3 text-destructive" />}
                  {editMode[file.path] && <Icon name="edit" className="h-3 w-3 ml-1 text-primary" />}
                </TabsTrigger>
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute right-1 top-1/2 h-4 w-4 -translate-y-1/2 rounded-sm opacity-70 hover:opacity-100"
                  onClick={(e) => {
                    e.stopPropagation();
                    closeFile(file.path);
                  }}
                >
                  <Icon name="x" className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </div>
        </ScrollArea>
      </TabsList>

      {openFiles.map((file) => (
        <TabsContent key={file.path} value={file.path} className="mt-0 flex-1 overflow-hidden">
          {file.isLoading ? (
            <div className="flex h-full items-center justify-center">
              <Icon name="loader" className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : file.error ? (
            <div className="flex h-full items-center justify-center p-8">
              <Alert variant="destructive" className="max-w-md">
                <Icon name="alert-circle" className="h-4 w-4" />
                <AlertTitle>Error loading file</AlertTitle>
                <AlertDescription>{file.error}</AlertDescription>
              </Alert>
            </div>
          ) : file.isBinary ? (
            <div className="flex h-full items-center justify-center p-8">
              <Alert className="max-w-md">
                <Icon name="file-warning" className="h-4 w-4" />
                <AlertTitle>Binary file</AlertTitle>
                <AlertDescription>
                  The file "{file.name}" appears to be a binary file and cannot be displayed as text.
                </AlertDescription>
              </Alert>
            </div>
          ) : (
            <div className="flex h-full flex-col">
              {/* Edit/View toggle button and Save button */}
              <div className="flex items-center justify-between border-b bg-card/60 px-4 py-2">
                <div className="flex items-center gap-2">
                  {file.isModified && (
                    <span className="text-xs text-muted-foreground">• Unsaved changes</span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {(file.isModified || file.path.startsWith('/untitled-')) && (
                    <Button
                      size="sm"
                      variant="default"
                      onClick={() => handleSaveFile(file.path)}
                      className="gap-2"
                    >
                      <Icon name="save" className="h-4 w-4" />
                      Save
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant={editMode[file.path] ? "default" : "outline"}
                    onClick={() => toggleEditMode(file.path)}
                    className="gap-2"
                  >
                    {editMode[file.path] ? (
                      <>
                        <Icon name="edit" className="h-4 w-4" />
                        Edit Mode
                      </>
                    ) : (
                      <>
                        <Icon name="eye" className="h-4 w-4" />
                        View Mode
                      </>
                    )}
                  </Button>
                </div>
              </div>

              {/* Content display */}
              <div className="flex-1 overflow-hidden">
                {editMode[file.path] ? (
                  <CodeEditor
                    filePath={file.path}
                    initialContent={file.content}
                    readOnly={false}
                    className="h-full"
                    onContentChange={(content) => updateFileContent(file.path, content)}
                  />
                ) : (
                  <FileContent file={file} />
                )}
              </div>
            </div>
          )}
        </TabsContent>
      ))}
      </Tabs>

      <SaveDialog
        open={saveDialogOpen}
        onOpenChange={setSaveDialogOpen}
        currentPath={fileToSave || ''}
        onSave={handleSaveAs}
      />
    </>
  );
}

interface FileContentProps {
  file: {
    content: string;
    name: string;
    path: string;
  };
}

function FileContent({ file }: FileContentProps) {
  const getLanguage = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    const languageMap: Record<string, string> = {
      js: 'javascript',
      jsx: 'jsx',
      ts: 'typescript',
      tsx: 'tsx',
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
      sh: 'bash',
      bash: 'bash',
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
    };
    return languageMap[ext || ''] || 'plaintext';
  };

  const language = getLanguage(file.name);
  return (
    <ScrollArea className="h-full">
      {language === 'plaintext' ? (
        <div className="p-4">
          <pre className="text-sm">{file.content}</pre>
        </div>
      ) : (
        <Highlight theme={themes.vsDark} code={file.content} language={language}>
          {({ className, style, tokens, getLineProps, getTokenProps }) => (
            <pre className={cn(className, "p-4 text-sm")} style={style}>
              <code>
                {tokens.map((line, i) => (
                  <div key={i} {...getLineProps({ line, key: i })}>
                    <span className="mr-4 inline-block w-8 select-none text-right text-muted-foreground">
                      {i + 1}
                    </span>
                    {line.map((token, key) => (
                      <span key={key} {...getTokenProps({ token, key })} />
                    ))}
                  </div>
                ))}
              </code>
            </pre>
          )}
        </Highlight>
      )}
    </ScrollArea>
  );
}

export { FileContent };
