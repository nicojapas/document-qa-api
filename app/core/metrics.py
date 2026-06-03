import logging
import time
from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager

import httpx

from app.core.config import settings
from app.db.session import db

logger = logging.getLogger(__name__)

METRICS_COLLECTION = "llm_metrics"


async def record_llm_metrics(
    model: str,
    method: str,
    latency_ms: float,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
) -> None:
    """Record LLM inference metrics to MongoDB."""
    metric = {
        "timestamp": datetime.now(timezone.utc),
        "model": model,
        "method": method,
        "latency_ms": latency_ms,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }

    try:
        await db[METRICS_COLLECTION].insert_one(metric)
    except Exception as e:
        logger.error(f"Failed to record metrics: {e}")

    logger.info(
        f"LLM metrics: model={model}, method={method}, latency_ms={latency_ms:.1f}, "
        f"tokens={{prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens}}}"
    )

    # Check latency threshold and alert if exceeded
    if latency_ms > settings.LLM_LATENCY_THRESHOLD_MS:
        await _trigger_latency_alert(model, method, latency_ms)


async def _trigger_latency_alert(model: str, method: str, latency_ms: float) -> None:
    """Trigger alert when latency exceeds threshold."""
    alert_msg = (
        f"LATENCY ALERT: {model}/{method} took {latency_ms:.0f}ms "
        f"(threshold: {settings.LLM_LATENCY_THRESHOLD_MS}ms)"
    )
    logger.warning(alert_msg)

    # Send webhook if configured
    if settings.ALERT_WEBHOOK_URL:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    settings.ALERT_WEBHOOK_URL,
                    json={
                        "alert_type": "llm_latency",
                        "model": model,
                        "method": method,
                        "latency_ms": latency_ms,
                        "threshold_ms": settings.LLM_LATENCY_THRESHOLD_MS,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
            logger.info(f"Latency alert webhook sent to {settings.ALERT_WEBHOOK_URL}")
        except Exception as e:
            logger.error(f"Failed to send latency alert webhook: {e}")


async def get_metrics(
    limit: int = 100,
    model: Optional[str] = None,
    method: Optional[str] = None,
) -> list[dict]:
    """Retrieve recent LLM metrics."""
    query = {}
    if model:
        query["model"] = model
    if method:
        query["method"] = method

    cursor = db[METRICS_COLLECTION].find(query).sort("timestamp", -1).limit(limit)
    metrics = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        metrics.append(doc)
    return metrics


async def get_metrics_summary() -> dict:
    """Get aggregated metrics summary."""
    pipeline = [
        {
            "$group": {
                "_id": {"model": "$model", "method": "$method"},
                "count": {"$sum": 1},
                "avg_latency_ms": {"$avg": "$latency_ms"},
                "max_latency_ms": {"$max": "$latency_ms"},
                "min_latency_ms": {"$min": "$latency_ms"},
                "avg_prompt_tokens": {"$avg": "$prompt_tokens"},
                "avg_completion_tokens": {"$avg": "$completion_tokens"},
                "total_prompt_tokens": {"$sum": "$prompt_tokens"},
                "total_completion_tokens": {"$sum": "$completion_tokens"},
            }
        }
    ]

    results = []
    async for doc in db[METRICS_COLLECTION].aggregate(pipeline):
        results.append({
            "model": doc["_id"]["model"],
            "method": doc["_id"]["method"],
            "request_count": doc["count"],
            "latency": {
                "avg_ms": round(doc["avg_latency_ms"], 1) if doc["avg_latency_ms"] else None,
                "max_ms": round(doc["max_latency_ms"], 1) if doc["max_latency_ms"] else None,
                "min_ms": round(doc["min_latency_ms"], 1) if doc["min_latency_ms"] else None,
            },
            "tokens": {
                "avg_prompt": round(doc["avg_prompt_tokens"]) if doc["avg_prompt_tokens"] else None,
                "avg_completion": round(doc["avg_completion_tokens"]) if doc["avg_completion_tokens"] else None,
                "total_prompt": doc["total_prompt_tokens"],
                "total_completion": doc["total_completion_tokens"],
            },
        })

    return {"summaries": results}


@asynccontextmanager
async def track_llm_latency():
    """Context manager to track LLM call latency."""
    start_time = time.perf_counter()
    try:
        yield
    finally:
        pass  # Latency calculated by caller for more flexibility
