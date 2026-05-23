from fastapi import APIRouter, HTTPException
from services.ocr import ocr_service

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness():
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
