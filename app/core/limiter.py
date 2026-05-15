from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize per-IP rate limiter
# This is in a separate module to avoid circular imports
limiter = Limiter(key_func=get_remote_address)
