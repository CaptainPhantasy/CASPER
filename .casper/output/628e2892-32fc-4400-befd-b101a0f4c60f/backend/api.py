```python
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional
from .schemas import UserRegistrationRequest, UserResponse, ErrorResponse
from .database import get_db  # Assuming you have database.py with connection logic
from .models import User  # Assuming you have SQLAlchemy models defined
from .security import get_password_hash  # Assuming you have security.py with password hashing

app = FastAPI(title="User Registration API")

@app.post(
    "/api/users/register",
    response_model=UserResponse,
    responses={
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse}
    },
    tags=["users"],
    summary="Register a new user"
)
async def register_user(
    user_data: UserRegistrationRequest,
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Register a new user with email validation.

    Args:
        user_data: User registration data including email, password, and full name
        db: Database session dependency

    Returns:
        UserResponse: Created user information

    Raises:
        HTTPException: 409 if email already exists
        HTTPException: 400 if validation fails
    """
    # Check if user with email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="User with this email already exists"
        )

    # Create new user instance
    try:
        new_user = User(
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            is_active=True
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return UserResponse.from_orm(new_user)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create user: {str(e)}"
        )

# Example usage:
"""
curl -X POST "http://localhost:8000/api/users/register" \
    -H "Content-Type: application/json" \
    -d '{
        "email": "user@example.com",
        "password": "securepass123",
        "full_name": "John Doe"
    }'
"""
```

This implementation includes:

1. Schemas:
- Pydantic models for request/response validation
- Email validation using EmailStr
- Password length validation
- Proper response models including error cases

2. API Endpoint:
- Clear route specification with OpenAPI documentation
- Email uniqueness check
- Password hashing (assuming implementation in security.py)
- Proper error handling with specific status codes
- Database transaction management
- Response serialization using Pydantic

Key features:
- Input validation using Pydantic
- Email format validation
- Password requirements enforcement
- Proper error responses
- Transaction handling
- OpenAPI documentation support

Note: This implementation assumes you have:
1. A database.py file with SQLAlchemy setup
2. A models.py file with SQLAlchemy models
3. A security.py file with password hashing utilities

Would you like me to provide implementations for any of these assumed dependencies as well?
