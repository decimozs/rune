from fastapi import FastAPI
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from routes.ocr import router
from services.ocr import ocr_service
from services.exceptions import OCRValidationError, OCRRuntimeError


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await ocr_service.init()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(router)


@app.exception_handler(OCRValidationError)
async def validation_error_handler(request, exc: OCRValidationError):
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
