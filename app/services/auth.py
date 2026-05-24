from app.core.config import settings
from app.core.security import verify_password
from app.models.user import User


def get_demo_user() -> User | None:
    """Get the demo user from environment configuration."""
    if not settings.DEMO_USER_PASSWORD_HASH:
        return None

    return User(
        email=settings.DEMO_USER_EMAIL,
        hashed_password=settings.DEMO_USER_PASSWORD_HASH,
        is_active=True,
    )


def authenticate_user(email: str, password: str) -> User | None:
    """Authenticate a user by email and password."""
    user = get_demo_user()

    if user is None:
        return None

    if user.email != email:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user
