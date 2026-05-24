"""Health check endpoints.

Two endpoints serve different purposes:
    - /health:       Always returns 200. Used by load balancers.
    - /health/ready: Returns 200 only when both OCR engines are loaded.
                      Returns 503 + per-engine status when degraded.
"""

from fastapi import APIRouter, HTTPException
from services.ocr import ocr_service

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Liveness check. Always returns 200."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness():
    """Readiness check. Fails if OCR engines haven't loaded yet.

    PaddleOCR takes ~22s to load models on first startup.
    During that window this endpoint returns 503 so orchestrators
    (Docker, k8s) will not route traffic prematurely.
    """
    checks = {
        "ocr_engine": ocr_service.engine.is_ready,
        "structure_engine": ocr_service.structure_engine.is_ready,
    }
    all_ok = all(checks.values())

    result = {
        "status": "ok" if all_ok else "degraded",
        "checks": {k: "ok" if v else "fail" for k, v in checks.items()},
    }

    if not all_ok:
        raise HTTPException(status_code=503, detail=result)

    return result
