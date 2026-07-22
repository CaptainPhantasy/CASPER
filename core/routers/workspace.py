
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.services.codebase import codebase_service

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

class WorkspaceRequest(BaseModel):
    path: str

class FileRequest(BaseModel):
    path: str

class FileWriteRequest(BaseModel):
    path: str
    content: str

class FileRenameRequest(BaseModel):
    old_path: str
    new_path: str

# Codebase Management Endpoints
@router.post("/api/workspace/open")
async def open_workspace(request: WorkspaceRequest):
    """Open a workspace/codebase for editing."""
    try:
        result = codebase_service.open_workspace(request.path)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/workspace/filetree")
@limiter.limit("60/minute")
async def get_file_tree(request: Request):
    """Get the current workspace file tree."""
    try:
        file_tree = codebase_service.get_file_tree()
        return {"file_tree": file_tree, "files": file_tree}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/workspace/file")
@limiter.limit("120/minute")
async def read_file(request_obj: Request, request: FileRequest):
    """Read a file from the current workspace."""
    try:
        file_data = codebase_service.read_file(request.path)
        return file_data
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/workspace/file")
async def read_file_get(path: str = Query(..., description="Path to file relative to workspace root")):
    """Support GET variant for compatibility."""
    try:
        return codebase_service.read_file(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/workspace/file/write")
async def write_file(request: FileWriteRequest):
    """Write content to a file in the workspace."""
    try:
        result = codebase_service.write_file(request.path, request.content)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/workspace/file/rename")
async def rename_file(request: FileRenameRequest):
    """Rename a file in the workspace."""
    try:
        result = codebase_service.rename_file(request.old_path, request.new_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/api/workspace/file")
async def delete_file(request: FileRequest):
    """Delete a file from the workspace."""
    try:
        result = codebase_service.delete_file(request.path)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/workspace/info")
async def get_workspace_info():
    """Get current workspace information."""
    if not codebase_service.current_workspace:
        raise HTTPException(status_code=400, detail="No workspace opened")

    return codebase_service.get_workspace_info()

@router.get("/api/workspace/recent")
async def get_recent_workspaces():
    """List recently opened workspaces."""
    return {"recent": codebase_service.get_recent_workspaces()}

@router.get("/api/workspace/search")
async def search_workspace(query: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=100)):
    """Search for files within the active workspace."""
    if not codebase_service.current_workspace:
        raise HTTPException(status_code=400, detail="No workspace opened")
    return {"results": codebase_service.search_files(query, limit)}
