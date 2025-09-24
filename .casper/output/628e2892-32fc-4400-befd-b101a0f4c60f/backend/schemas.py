```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserRegistrationRequest(BaseModel):
    """
    Pydantic model for user registration request payload.
    """
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(
        ..., 
        min_length=8,
        description="User's password (min 8 characters)"
    )
    full_name: str = Field(..., description="User's full name")

class UserResponse(BaseModel):
    """
    Pydantic model for user response data.
    """
    id: int
    email: EmailStr
    full_name: str
    is_active: bool

    class Config:
        orm_mode = True

class ErrorResponse(BaseModel):
    """
    Pydantic model for error responses.
    """
    detail: str
```
