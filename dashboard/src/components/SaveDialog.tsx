import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Icon } from './icons/IconMapping';

interface SaveDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentPath: string;
  onSave: (newPath: string) => void;
}

export function SaveDialog({ open, onOpenChange, currentPath, onSave }: SaveDialogProps) {
  const [fileName, setFileName] = useState('');
  const [error, setError] = useState('');

  const handleSave = () => {
    if (!fileName.trim()) {
      setError('Please enter a file name');
      return;
    }

    // Ensure the file has an extension
    let finalPath = fileName;
    if (!finalPath.includes('.')) {
      finalPath += '.txt';
    }

    // Prepend slash if not present
    if (!finalPath.startsWith('/')) {
      finalPath = '/' + finalPath;
    }

    onSave(finalPath);
    setFileName('');
    setError('');
    onOpenChange(false);
  };

  const handleCancel = () => {
    setFileName('');
    setError('');
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Icon name="save" className="h-5 w-5" />
            Save File
          </DialogTitle>
          <DialogDescription>
            Enter a name for your new file. If no extension is provided, .txt will be used.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="name" className="text-right">
              File name
            </Label>
            <div className="col-span-3 space-y-2">
              <Input
                id="name"
                value={fileName}
                onChange={(e) => {
                  setFileName(e.target.value);
                  setError('');
                }}
                placeholder="example.ts"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleSave();
                  }
                }}
              />
              {error && <p className="text-sm text-destructive">{error}</p>}
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={handleCancel}>
            Cancel
          </Button>
          <Button onClick={handleSave}>Save</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}