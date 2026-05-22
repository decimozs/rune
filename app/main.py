import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from config import settings
from routes.ocr import router
from services.ocr import ocr_service
from services.batch import batch_processor
from services.background import background_processor
from services.exceptions import OCRValidationError, OCRRuntimeError

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await ocr_service.init()
    await batch_processor.start()
    await background_processor.start()
    logger.info("OCR service initialized, batch and background processors started")
    yield
    await background_processor.stop()
    await batch_processor.stop()
    logger.info("Shutdown complete")


app = FastAPI(lifespan=lifespan)
app.include_router(router)


@app.exception_handler(OCRValidationError)
async def validation_error_handler(request, exc: OCRValidationError):
    logger.warning("Validation error: %s", exc)
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": {
                "code": "validation_error",
                "message": str(exc),
            },
        },
    )


@app.exception_handler(OCRRuntimeError)
async def runtime_error_handler(request, exc: OCRRuntimeError):
    logger.error("Runtime error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "runtime_error",
                "message": str(exc),
            },
        },
    )


@app.exception_handler(Exception)
async def global_error_handler(request, exc: Exception):
    logger.exception("Unhandled exception in request")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "internal_error",
                "message": "Internal server error",
            },
        },
    )
