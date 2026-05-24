import hashlib
import services.db as svc_db

from fastapi import Header, HTTPException

from config import settings


async def verify_api_key(x_api_key: str | None = Header(None)) -> str | None:
    db = svc_db.key_db
    if settings.db_path and db and db.is_initialized:
        if not x_api_key:
            raise HTTPException(401, "Missing API key")
        key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
        key = await db.get_key(key_hash)
        if not key or not key["is_active"]:
            raise HTTPException(401, "Invalid API key")
        await db.update_last_used(key_hash)
        return key["name"]

    if settings.api_keys == "#":
        return None
    if not x_api_key:
        raise HTTPException(401, "Missing API key")
    key_name = settings.api_key_map.get(x_api_key)
    if key_name is None:
        raise HTTPException(401, "Invalid API key")
    return key_name
