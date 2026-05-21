from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    # OCR Engine
    enable_mkldnn: bool = False
    lang: str = "en"
    version: str = "PP-OCRv4"
    use_textline_orientation: bool = True

    # File Upload
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    upload_dir: str = "/tmp"
    allowed_content_types: str = "image/jpeg,image/png,image/bmp,image/tiff,image/webp,application/pdf"

    # Output
    output_dir: str = "app/outputs"

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_prefix="OCR_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def allowed_types_list(self) -> list[str]:
        return [t.strip() for t in self.allowed_content_types.split(",")]

    @property
    def upload_dir_path(self) -> Path:
        return Path(self.upload_dir)

    @property
    def output_dir_path(self) -> Path:
        return Path(self.output_dir)


settings = Settings()
