import time
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
from app.services.llm_factory import AVAILABLE_MODELS, get_default_model

# Cache for Modal health status per model (avoids expensive checks on every /health call)
_modal_health_cache: dict[str, dict] = {}
MODAL_HEALTH_CACHE_TTL = 60  # seconds


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION
)


@app.on_event("startup")
async def on_startup():
    from app.db.indexes import ensure_indexes
    await ensure_indexes()

# Register slowapi limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",")],
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
    # Skip rate limiting for health checks, docs, and metrics
    if request.url.path in ["/", "/health", "/docs", "/openapi.json", "/redoc"] or request.url.path.startswith("/api/v1/metrics"):
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
async def health(model: str | None = None):
    """Health check endpoint with LLM status for a specific model."""
    if model is None:
        model = get_default_model()

    if model not in AVAILABLE_MODELS:
        return JSONResponse(
            status_code=400,
            content={"error": f"Unknown model: '{model}'. Available: {list(AVAILABLE_MODELS.keys())}"}
        )

    config = AVAILABLE_MODELS[model]
    provider = config["provider"]

    # Gemini and Deepseek are always ready (external managed services)
    if provider in ("gemini", "deepseek"):
        llm_status = "ready"
    else:
        # Modal: use cached status if fresh enough
        now = time.time()
        cached = _modal_health_cache.get(model)
        if cached and now - cached["timestamp"] < MODAL_HEALTH_CACHE_TTL:
            llm_status = cached["status"]
        else:
            # Cache expired, check Modal
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

            # Update cache
            _modal_health_cache[model] = {"status": llm_status, "timestamp": now}

    return {
        "status": "healthy",
        "model": model,
        "provider": provider,
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
