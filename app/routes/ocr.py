import shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from schemas.ocr import OCRResponse
from services.ocr import ocr_service


router = APIRouter(prefix="/ocr", tags=["ocr"])


@router.post("/parse", response_model=OCRResponse)
async def parse_file(file: UploadFile = File(...)):
    if not file or not file.filename:
        raise HTTPException(
            status_code=400, detail="Invalid file upload or missing filename"
        )

    tmp_path = Path(f"/tmp/{file.filename}")

    with tmp_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = ocr_service.process(str(tmp_path), file)
    tmp_path.unlink()

    return OCRResponse(**result)
