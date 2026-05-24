from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    """Response model for successful authentication."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str | None = None


class LoginRequest(BaseModel):
    """Request model for login."""

    email: EmailStr
    password: str
