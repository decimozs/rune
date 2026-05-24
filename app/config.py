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
    allowed_content_types: str = (
        "image/jpeg,image/png,image/bmp,image/tiff,image/webp,"
        "application/pdf,"
        "application/msword,"
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
        "application/vnd.ms-powerpoint,"
        "application/vnd.openxmlformats-officedocument.presentationml.presentation,"
        "text/rtf,"
        "text/csv,"
        "application/vnd.ms-excel,"
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Output
    output_dir: str = "app/outputs"
    output_ttl: int = 3600  # old page images / markdown assets cleaned after this

    # Concurrency
    max_concurrent_jobs: int = 2

    # Gotenberg
    gotenberg_url: str = "http://localhost:3000"

    # Auth
    api_keys: str = "#"  # comma-separated. "#" disables auth

    # URL safety
    url_max_length: int = 2048
    url_blocked_domains: str = ""
    url_allowed_domains: str = ""
    company_domains_only: bool = False

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

    @property
    def api_keys_list(self) -> list[str]:
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]

    @property
    def api_key_map(self) -> dict[str, str]:
        result = {}
        for item in self.api_keys.split(","):
            item = item.strip()
            if not item:
                continue
            if "=" in item:
                k, v = item.split("=", 1)
                result[k.strip()] = v.strip()
            else:
                result[item] = "unknown"
        return result

    @property
    def url_blocked_domain_list(self) -> list[str]:
        return [d.strip() for d in self.url_blocked_domains.split(",") if d.strip()]

    @property
    def url_allowed_domain_list(self) -> list[str]:
        return [d.strip() for d in self.url_allowed_domains.split(",") if d.strip()]


settings = Settings()
