import { X, FileWarning, Loader2, FileText, AlertCircle } from "lucide-react";
import { Highlight, themes } from "prism-react-renderer";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

import { useFileStore } from "@/stores/fileStore";
import { cn } from "@/lib/utils";

export function FileViewer() {
  const { openFiles, activeFilePath, closeFile, setActiveFile } = useFileStore();

  if (openFiles.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <div className="text-center">
          <FileText className="mx-auto h-12 w-12 opacity-50" />
          <p className="mt-4 text-sm">No files open</p>
          <p className="mt-1 text-xs">Select a file from the tree to view its contents</p>
        </div>
      </div>
    );
  }

  return (
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
                  <span className="mr-2 text-sm">{file.name}</span>
                  {file.isLoading && <Loader2 className="h-3 w-3 animate-spin" />}
                  {file.error && <AlertCircle className="h-3 w-3 text-destructive" />}
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
                  <X className="h-3 w-3" />
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
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : file.error ? (
            <div className="flex h-full items-center justify-center p-8">
              <Alert variant="destructive" className="max-w-md">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Error loading file</AlertTitle>
                <AlertDescription>{file.error}</AlertDescription>
              </Alert>
            </div>
          ) : file.isBinary ? (
            <div className="flex h-full items-center justify-center p-8">
              <Alert className="max-w-md">
                <FileWarning className="h-4 w-4" />
                <AlertTitle>Binary file</AlertTitle>
                <AlertDescription>
                  The file "{file.name}" appears to be a binary file and cannot be displayed as text.
                </AlertDescription>
              </Alert>
            </div>
          ) : (
            <FileContent file={file} />
          )}
        </TabsContent>
      ))}
    </Tabs>
  );
}

interface FileContentProps {
  file: {
    content: string;
    language?: string;
    name: string;
  };
}

function FileContent({ file }: FileContentProps) {
  const isLightTheme = typeof document !== 'undefined' && document.documentElement.classList.contains("light");
  const theme = isLightTheme ? themes.oneLight : themes.oneDark;

  // For non-code files or when syntax highlighting fails
  if (!file.language || file.language === "text") {
    return (
      <ScrollArea className="h-full">
        <pre className="p-4 text-sm leading-relaxed">
          <code>{file.content}</code>
        </pre>
      </ScrollArea>
    );
  }

  return (
    <ScrollArea className="h-full">
      <Highlight theme={theme} code={file.content} language={file.language}>
        {({ className, style, tokens, getLineProps, getTokenProps }) => (
          <pre className={cn(className, "p-4 text-sm leading-relaxed")} style={style}>
            {tokens.map((line, lineIndex) => (
              <div key={lineIndex} {...getLineProps({ line })}>
                <span className="mr-4 inline-block w-10 select-none text-right text-muted-foreground/50">
                  {lineIndex + 1}
                </span>
                {line.map((token, tokenIndex) => (
                  <span key={tokenIndex} {...getTokenProps({ token })} />
                ))}
              </div>
            ))}
          </pre>
        )}
      </Highlight>
    </ScrollArea>
  );
}
