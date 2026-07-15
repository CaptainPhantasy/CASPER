import jwt
import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.security_config import JWT_SECRET

router = APIRouter()

ALGORITHM = "HS256"


class Token(BaseModel):
    access_token: str
    token_type: str


@router.post("/api/auth/token", response_model=Token)
async def login_for_access_token():
    """
    Generate a JWT for the terminal.
    In a real application, this would involve user authentication.
    """
    to_encode = {
        "user_id": "default_user",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
    }
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return {"access_token": encoded_jwt, "token_type": "bearer"}
