from fastapi import APIRouter, HTTPException, status

from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, Token
from app.services.auth import authenticate_user

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(request: LoginRequest) -> Token:
    """
    Authenticate with email and password to receive a JWT token.

    Use the token in subsequent requests via the Authorization header:
    `Authorization: Bearer <token>`
    """
    user = authenticate_user(request.email, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=user.email)

    return Token(access_token=access_token)
