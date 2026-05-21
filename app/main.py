from fastapi import FastAPI
from contextlib import asynccontextmanager
from routes.ocr import router
from services.ocr import ocr_service


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await ocr_service.init()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(router)
