from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.services.approval import approval_service

router = APIRouter()


class ApprovalModeRequest(BaseModel):
    mode: str


@router.get("/api/approvals/mode")
async def get_approval_mode():
    """Get the current approval mode."""
    return {"mode": approval_service.mode}


@router.post("/api/approvals/mode")
async def set_approval_mode(request: ApprovalModeRequest):
    """Set the approval mode for the HIL service."""
    try:
        approval_service.set_approval_mode(request.mode)
        return {"status": "success", "mode": request.mode.upper()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
