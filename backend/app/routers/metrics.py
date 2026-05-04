"""
Prometheus Metrics Endpoint for ScholarLab

Exposes Prometheus metrics at /metrics for Grafana ingestion.
"""

from fastapi import APIRouter, Response
from app.metrics.prometheus_metrics import scholarlab_registry
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

router = APIRouter(tags=["monitoring"])


@router.get("/metrics", response_class=Response, include_in_schema=False)
async def metrics():
    """
    Prometheus metrics endpoint.
    
    Exposes all ScholarLab metrics in Prometheus text format.
    
    Returns:
        Prometheus metrics in text format
    """
    return Response(
        content=generate_latest(scholarlab_registry),
        media_type=CONTENT_TYPE_LATEST,
    )
