"""FastAPI application entrypoint.

Wires together all services, middleware, exception handlers, and
background tasks. The lifespan function controls startup and
shutdown ordering (important: KeyDB → PaddleOCR → converters →
processors → cleaners).

Page images and markdown images are served by nginx from the
shared ocr_assets volume.
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager

import services.db as svc_db
from config import settings
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routes.health import router as health_router
from routes.ocr import router as ocr_router
from services.async_job import async_job_processor
from services.cleanup import output_cleaner
from services.converter import converter
from services.db import KeyDB
from services.exceptions import OCRRuntimeError, OCRValidationError
from services.log_ctx import (
    JSONFormatter,
    LogContextFilter,
    identity_var,
    request_id_var,
)
from services.ocr import ocr_service
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
for handler in logging.root.handlers:
    handler.addFilter(LogContextFilter())
    if settings.log_format == "json":
        handler.setFormatter(JSONFormatter())
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Startup/shutdown lifecycle.

    Order matters:
      1. Create output dir
      2. Init KeyDB (if OCR_DB_PATH configured)
      3. Load PaddleOCR models (20-40s on first run)
      4. Start Gotenberg HTTP client
      5. Start batch/background/cleaner tasks
    Shutdown is the reverse order.
    """
    settings.output_dir_path.mkdir(parents=True, exist_ok=True)
    if settings.db_path:
        db = KeyDB(settings.db_path)
        await db.init()
        svc_db.key_db = db
        logger.info("KeyDB initialized at %s", settings.db_path)
    logger.info("Loading PaddleOCR models (may take 20-40s on first run)...")
    await ocr_service.init()
    await converter.start()
    await async_job_processor.start()
    await output_cleaner.start()
    logger.info("OCR service initialized, converters and processors started")
    yield
    await output_cleaner.stop()
    await async_job_processor.stop()
    await converter.stop()
    await ocr_service.shutdown()
    if svc_db.key_db:
        await svc_db.key_db.close()
    logger.info("Shutdown complete")


_prod = settings.cors_origins != "*"
app = FastAPI(
    lifespan=lifespan,
    title="Exist OCR API",
    version="0.2.0",
    description="Self-hosted OCR service using PaddleOCR",
    docs_url=None if _prod else "/docs",
    redoc_url=None if _prod else "/redoc",
    openapi_url=None if _prod else "/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(health_router)
app.include_router(ocr_router)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Set request_id context var and return it as a response header.

    Allows correlating logs across auth, processing, and error handling
    for a single request. Client can pass X-Request-ID to correlate
    client-side; otherwise a UUID is generated.

    Contextvars are reset in finally to prevent leaking across requests.
    Background tasks capture context at creation time, so they retain
    the correct values even after reset.
    """
    req_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    req_id_token = request_id_var.set(req_id)
    identity_token = identity_var.set(identity_var.get())

    start = time.perf_counter()
    try:
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Processing-Time-Ms"] = str(round(elapsed * 1000, 2))
        return response
    finally:
        request_id_var.reset(req_id_token)
        identity_var.reset(identity_token)


# The handler order matters: more specific handlers first, catch-all last.
# FastAPI matches handlers by exception type in registration order.


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle FastAPI-native HTTP errors (401, 404, 413, etc.)."""
    ident = identity_var.get()
    logger.warning(
        "HTTP %d on %s %s (identity=%s): %s",
        exc.status_code,
        request.method,
        request.url.path,
        ident,
        exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": "http_error",
                "message": str(exc.detail),
            },
        },
    )


@app.exception_handler(OCRValidationError)
async def validation_error_handler(request, exc: OCRValidationError):
    """Handle user-correctable input errors (bad type, invalid URL, etc.)."""
    ident = identity_var.get()
    logger.warning(
        "Validation error on %s (identity=%s): %s",
        request.url.path,
        ident,
        exc,
    )
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
    """Handle internal system failures (conversion failure, OCR crash)."""
    ident = identity_var.get()
    logger.error(
        "Runtime error on %s (identity=%s): %s",
        request.url.path,
        ident,
        exc,
    )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "runtime_error",
                "message": "Processing failed",
            },
        },
    )


@app.exception_handler(Exception)
async def global_error_handler(request, exc: Exception):
    """Catch-all for unexpected errors. Returns generic message to client."""
    ident = identity_var.get()
    logger.exception(
        "Unhandled exception on %s (identity=%s)",
        request.url.path,
        ident,
    )
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
