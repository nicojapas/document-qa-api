from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import httpx

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.limiter import limiter
from app.services.rate_limiter import GlobalRateLimiter


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION
)

# Register slowapi limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://nicojapas.github.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def global_rate_limit_middleware(request: Request, call_next):
    """
    Global rate limiting middleware that enforces a daily request cap.
    This protects against IP rotation attacks.
    """
    # Skip rate limiting for health checks and docs
    if request.url.path in ["/", "/health", "/docs", "/openapi.json", "/redoc"]:
        return await call_next(request)

    # Check global daily limit
    is_allowed, current_count, max_limit = await GlobalRateLimiter.check_and_increment(
        request_type=request.url.path
    )

    if not is_allowed:
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Daily request limit exceeded. API is temporarily unavailable.",
                "message": "This is a portfolio demo with limited daily requests. Please try again tomorrow.",
                "requests_today": current_count,
                "daily_limit": max_limit
            }
        )

    # Add rate limit headers to response
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(max_limit)
    response.headers["X-RateLimit-Remaining"] = str(max(0, max_limit - current_count))

    return response


# Include the aggregate router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Welcome to Document QA API. Visit /docs for Swagger."}


@app.get("/health")
async def health():
    """Health check endpoint with LLM status."""
    llm_status = "ready"

    if settings.LLM_PROVIDER == "modal":
        # Check Modal's /v1/models endpoint (part of OpenAI API spec)
        models_url = f"{settings.MODAL_LLM_URL}/models"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    models_url,
                    headers={
                        "Modal-Key": settings.MODAL_KEY,
                        "Modal-Secret": settings.MODAL_SECRET,
                    }
                )
                if response.status_code == 200:
                    llm_status = "ready"
                else:
                    llm_status = "unavailable"
        except httpx.TimeoutException:
            llm_status = "warming_up"
        except httpx.RequestError:
            llm_status = "unavailable"

    return {
        "status": "healthy",
        "llm_provider": settings.LLM_PROVIDER,
        "llm_status": llm_status
    }


@app.get("/api/v1/usage")
async def get_usage():
    """Get current API usage stats for the day."""
    usage = await GlobalRateLimiter.get_daily_usage()
    remaining = await GlobalRateLimiter.get_remaining_requests()
    return {
        "date": usage["date"],
        "requests_today": usage["requests"],
        "daily_limit": settings.GLOBAL_DAILY_REQUEST_LIMIT,
        "remaining": remaining
    }
