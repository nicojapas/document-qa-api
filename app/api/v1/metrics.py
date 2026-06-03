from typing import Optional

from fastapi import APIRouter, Query

from app.core.metrics import get_metrics, get_metrics_summary

router = APIRouter()


@router.get("/")
async def list_metrics(
    limit: int = Query(default=100, le=1000),
    model: Optional[str] = Query(default=None),
    method: Optional[str] = Query(default=None),
):
    """
    Get recent LLM inference metrics.

    Returns raw metrics records with latency and token usage.
    """
    metrics = await get_metrics(limit=limit, model=model, method=method)
    return {"metrics": metrics, "count": len(metrics)}


@router.get("/summary")
async def metrics_summary():
    """
    Get aggregated metrics summary.

    Returns averages and totals grouped by model and method.
    """
    return await get_metrics_summary()
