from fastapi import Header, HTTPException

from config import settings


def verify_api_key(x_api_key: str | None = Header(None)) -> str | None:
    if settings.api_keys == "#":
        return None

    if not x_api_key:
        raise HTTPException(401, "Missing API key")

    key_name = settings.api_key_map.get(x_api_key)
    if key_name is None:
        raise HTTPException(401, "Invalid API key")

    return key_name
