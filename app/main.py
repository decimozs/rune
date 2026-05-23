import time
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from config import settings
from routes.ocr import router as ocr_router
from routes.health import router as health_router
from services.ocr import ocr_service
from services.batch import batch_processor
from services.background import background_processor
from services.converter import converter
from services.exceptions import OCRValidationError, OCRRuntimeError

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await ocr_service.init()
    await converter.start()
    await batch_processor.start()
    await background_processor.start()
    logger.info("OCR service initialized, converters and processors started")
    yield
    await background_processor.stop()
    await batch_processor.stop()
    await converter.stop()
    logger.info("Shutdown complete")


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(ocr_router)
settings.output_dir_path.mkdir(parents=True, exist_ok=True)
app.mount("/assets", StaticFiles(directory=str(settings.output_dir_path)), name="assets")


@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    response.headers["X-Processing-Time-Ms"] = str(round(elapsed * 1000, 2))
    return response


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
