import hashlib
import services.db as svc_db

from fastapi import Header, HTTPException

from config import settings


async def verify_api_key(x_api_key: str | None = Header(None)) -> str | None:
    """Authenticate request using X-API-Key header.

    Two auth modes exist. DB-backed is preferred. Env-var mode is legacy.
    When OCR_API_KEYS is set to #, auth is disabled entirely.
    """
    # key_db is None at import time. It gets wired in main.py lifespan
    # when OCR_DB_PATH is configured. Must read the module attribute
    # dynamically (not via value-copy import) to pick up the runtime
    # KeyDB instance after init() completes.
    db = svc_db.key_db

    # DB-backed auth path
    #
    # When OCR_DB_PATH is configured but the KeyDB singleton is missing
    # or failed to initialize, fail closed with 503. Falling through to
    # the env-var path below would silently degrade to disabled auth if
    # OCR_API_KEYS happens to be set to #.
    if settings.db_path:
        if not db or not db.is_initialized:
            raise HTTPException(503, "Auth database not initialized")

        if not x_api_key:
            raise HTTPException(401, "Missing API key")

        key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
        key = await db.get_key(key_hash)

        if not key or not key["is_active"]:
            raise HTTPException(401, "Invalid API key")

        await db.update_last_used(key_hash)
        return key["name"]

    # Legacy env-var auth path
    #
    # Keys are defined as key=name pairs in OCR_API_KEYS. A value of #
    # means no auth configured. Unlike DB mode, changes require a server
    # restart since settings are read once at startup.
    if settings.api_keys == "#":
        return None

    if not x_api_key:
        raise HTTPException(401, "Missing API key")

    key_name = settings.api_key_map.get(x_api_key)
    if key_name is None:
        raise HTTPException(401, "Invalid API key")
    return key_name
