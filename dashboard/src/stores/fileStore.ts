import { create } from 'zustand';
import { getFileContent } from '@/services/api';

export interface OpenFile {
  path: string;
  name: string;
  content: string;
  originalContent?: string;
  isModified?: boolean;
  language?: string;
  isBinary?: boolean;
  isLoading?: boolean;
  error?: string;
}

interface FileStoreState {
  openFiles: OpenFile[];
  activeFilePath: string | null;

  // Actions
  openFile: (file: { path: string; name: string }) => Promise<void>;
  closeFile: (path: string) => void;
  setActiveFile: (path: string) => void;
  updateFileContent: (path: string, content: string) => void;
  saveFile: (path: string, newPath?: string) => Promise<boolean>;
  renameFile: (oldPath: string, newPath: string, newName: string) => void;
  clearAllFiles: () => void;
}

const getFileLanguage = (fileName: string): string => {
  const ext = fileName.split('.').pop()?.toLowerCase();
  const langMap: Record<string, string> = {
    js: 'javascript',
    jsx: 'jsx',
    ts: 'typescript',
    tsx: 'tsx',
    py: 'python',
    rs: 'rust',
    go: 'go',
    java: 'java',
    c: 'c',
    cpp: 'cpp',
    cs: 'csharp',
    rb: 'ruby',
    php: 'php',
    swift: 'swift',
    kt: 'kotlin',
    md: 'markdown',
    json: 'json',
    yaml: 'yaml',
    yml: 'yaml',
    toml: 'toml',
    xml: 'xml',
    html: 'html',
    css: 'css',
    scss: 'scss',
    sass: 'sass',
    less: 'less',
    sh: 'bash',
    bash: 'bash',
    zsh: 'bash',
    dockerfile: 'dockerfile',
    sql: 'sql',
    graphql: 'graphql',
    vue: 'vue',
    svelte: 'svelte',
  };
  return langMap[ext || ''] || 'text';
};

const isBinaryFile = (fileName: string): boolean => {
  const ext = fileName.split('.').pop()?.toLowerCase();
  const binaryExts = [
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'ico', 'webp',
    'mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm',
    'mp3', 'wav', 'flac', 'aac', 'ogg', 'wma',
    'zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz',
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    'exe', 'dll', 'so', 'dylib', 'bin', 'dat',
    'db', 'sqlite', 'sqlite3',
    'ttf', 'otf', 'woff', 'woff2', 'eot',
    'pyc', 'pyo', 'class', 'jar', 'war', 'ear',
  ];
  return binaryExts.includes(ext || '');
};

export const useFileStore = create<FileStoreState>((set, get) => ({
  openFiles: [],
  activeFilePath: null,

  openFile: async ({ path, name }) => {
    const state = get();

    // Check if file is already open
    const existingFile = state.openFiles.find(f => f.path === path);
    if (existingFile) {
      set({ activeFilePath: path });
      return;
    }

    // Check if it's a new untitled file
    if (path.startsWith('/untitled-')) {
      set(state => ({
        openFiles: [...state.openFiles, {
          path,
          name,
          content: '',
          originalContent: '',
          isModified: false,
          language: getFileLanguage(name),
        }],
        activeFilePath: path,
      }));
      return;
    }

    // Check if it's a binary file
    if (isBinaryFile(name)) {
      set(state => ({
        openFiles: [...state.openFiles, {
          path,
          name,
          content: '',
          isBinary: true,
          language: 'text',
        }],
        activeFilePath: path,
      }));
      return;
    }

    // Add file with loading state
    set(state => ({
      openFiles: [...state.openFiles, {
        path,
        name,
        content: '',
        language: getFileLanguage(name),
        isLoading: true,
      }],
      activeFilePath: path,
    }));

    // Fetch file content
    try {
      const data = await getFileContent(path);
      const content = data.content || '';

      // Update file with content
      set(state => ({
        openFiles: state.openFiles.map(f =>
          f.path === path
            ? { ...f, content, originalContent: content, isModified: false, isLoading: false }
            : f
        ),
      }));
    } catch (error) {
      console.error('Failed to fetch file:', error);

      // Update file with error
      set(state => ({
        openFiles: state.openFiles.map(f =>
          f.path === path
            ? { ...f, error: error instanceof Error ? error.message : 'Failed to load file', isLoading: false }
            : f
        ),
      }));
    }
  },

  closeFile: (path) => {
    set(state => {
      const newOpenFiles = state.openFiles.filter(f => f.path !== path);
      let newActiveFilePath = state.activeFilePath;

      // If closing the active file, switch to another open file
      if (state.activeFilePath === path) {
        const currentIndex = state.openFiles.findIndex(f => f.path === path);
        if (newOpenFiles.length > 0) {
          // Try to activate the file at the same index, or the previous one
          const newIndex = Math.min(currentIndex, newOpenFiles.length - 1);
          newActiveFilePath = newOpenFiles[newIndex]?.path || null;
        } else {
          newActiveFilePath = null;
        }
      }

      return {
        openFiles: newOpenFiles,
        activeFilePath: newActiveFilePath,
      };
    });
  },

  setActiveFile: (path) => {
    const state = get();
    if (state.openFiles.find(f => f.path === path)) {
      set({ activeFilePath: path });
    }
  },

  updateFileContent: (path, content) => {
    set(state => ({
      openFiles: state.openFiles.map(f =>
        f.path === path ? {
          ...f,
          content,
          isModified: content !== f.originalContent
        } : f
      ),
    }));
  },

  saveFile: async (path, newPath) => {
    const state = get();
    const file = state.openFiles.find(f => f.path === path);
    if (!file) return false;

    try {
      // For untitled files, we need to provide a real path
      const targetPath = newPath || path;
      const isUntitled = path.startsWith('/untitled-');

      if (isUntitled && !newPath) {
        // Can't save untitled without a new path
        return false;
      }

      // Here you would normally call an API to save the file
      // For now, we'll just update the store to mark it as saved

      set(state => ({
        openFiles: state.openFiles.map(f =>
          f.path === path ? {
            ...f,
            path: targetPath,
            name: targetPath.split('/').pop() || f.name,
            originalContent: f.content,
            isModified: false
          } : f
        ),
        activeFilePath: state.activeFilePath === path ? targetPath : state.activeFilePath
      }));

      return true;
    } catch (error) {
      console.error('Failed to save file:', error);
      return false;
    }
  },

  renameFile: (oldPath, newPath, newName) => {
    set(state => ({
      openFiles: state.openFiles.map(f =>
        f.path === oldPath ? {
          ...f,
          path: newPath,
          name: newName
        } : f
      ),
      activeFilePath: state.activeFilePath === oldPath ? newPath : state.activeFilePath
    }));
  },

  clearAllFiles: () => {
    set({
      openFiles: [],
      activeFilePath: null,
    });
  },
}));