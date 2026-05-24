from pydantic import BaseModel, EmailStr


class User(BaseModel):
    """User model for authentication."""

    email: EmailStr
    hashed_password: str
    is_active: bool = True
