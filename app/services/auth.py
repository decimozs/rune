import hashlib
import logging

import services.db as svc_db
from config import settings
from fastapi import Header, HTTPException
from services.log_ctx import identity_var

logger = logging.getLogger(__name__)


async def verify_api_key(x_api_key: str | None = Header(None)) -> str | None:
    """Authenticate request using X-API-Key header.

    Two auth modes exist. DB-backed is preferred. Env-var mode is legacy.
    When OCR_API_KEYS is set to #, auth is disabled entirely.

    On success, sets identity_var contextvar so downstream logs carry
    the authenticated identity.
    """
    db = svc_db.key_db

    if settings.db_path:
        if not db or not db.is_initialized:
            logger.warning("Auth DB not initialized")
            raise HTTPException(503, "Auth database not initialized")

        if not x_api_key:
            logger.warning("Missing API key (DB mode)")
            raise HTTPException(401, "Missing API key")

        key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
        key = await db.get_key(key_hash)

        if not key or not key["is_active"]:
            logger.warning("Invalid API key (DB mode)")
            raise HTTPException(401, "Invalid API key")

        await db.update_last_used(key_hash)
        identity_var.set(key["name"])
        logger.info("Auth OK: identity=%s", key["name"])
        return key["name"]

    if settings.api_keys == "#":
        return None

    if not x_api_key:
        logger.warning("Missing API key (env mode)")
        raise HTTPException(401, "Missing API key")

    key_name = settings.api_key_map.get(x_api_key)
    if key_name is None:
        logger.warning("Invalid API key (env mode)")
        raise HTTPException(401, "Invalid API key")

    identity_var.set(key_name)
    logger.info("Auth OK: identity=%s", key_name)
    return key_name
