import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1


def hash_api_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def key_prefix(raw: str) -> str:
    return raw[:16]


def generate_raw_key() -> str:
    import secrets
    return "sk_live_" + secrets.token_urlsafe(32)


class KeyDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    @property
    def is_initialized(self) -> bool:
        return self._conn is not None

    async def init(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._migrate()
        logger.info("KeyDB initialized at %s (schema v%d)", self.db_path, SCHEMA_VERSION)

    async def _migrate(self) -> None:
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS _schema_version (
                version    INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)
        cur = await self._conn.execute(
            "SELECT COALESCE(MAX(version), 0) FROM _schema_version"
        )
        row = await cur.fetchone()
        current_version = row[0] if row else 0

        for v in range(current_version + 1, SCHEMA_VERSION + 1):
            migration = MIGRATIONS.get(v)
            if migration:
                logger.info("Running DB migration v%d", v)
                await migration(self._conn)
                await self._conn.execute(
                    "INSERT INTO _schema_version (version, applied_at) VALUES (?, ?)",
                    (v, datetime.now(timezone.utc).isoformat()),
                )
        await self._conn.commit()

    async def get_key(self, key_hash: str) -> Optional[dict]:
        if not self._conn:
            return None
        cur = await self._conn.execute(
            "SELECT name, team, is_active FROM api_keys WHERE key_hash = ?",
            (key_hash,),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        return {
            "name": row["name"],
            "team": row["team"] or "",
            "is_active": bool(row["is_active"]),
        }

    async def update_last_used(self, key_hash: str) -> None:
        if not self._conn:
            return
        await self._conn.execute(
            "UPDATE api_keys SET last_used_at = ? WHERE key_hash = ?",
            (datetime.now(timezone.utc).isoformat(), key_hash),
        )
        await self._conn.commit()

    async def add_key(self, key_hash: str, prefix: str, name: str, team: str = "") -> None:
        if not self._conn:
            raise RuntimeError("KeyDB not initialized")
        now = datetime.now(timezone.utc).isoformat()
        await self._conn.execute(
            "INSERT INTO api_keys (key_prefix, key_hash, name, team, created_at) VALUES (?, ?, ?, ?, ?)",
            (prefix, key_hash, name, team, now),
        )
        await self._conn.commit()

    async def revoke_key(self, key_hash: str) -> bool:
        if not self._conn:
            return False
        now = datetime.now(timezone.utc).isoformat()
        cur = await self._conn.execute(
            "UPDATE api_keys SET is_active = 0, revoked_at = ? WHERE key_hash = ? AND is_active = 1",
            (now, key_hash),
        )
        await self._conn.commit()
        return cur.rowcount > 0

    async def revoke_by_prefix(self, prefix: str) -> bool:
        if not self._conn:
            return False
        now = datetime.now(timezone.utc).isoformat()
        cur = await self._conn.execute(
            "UPDATE api_keys SET is_active = 0, revoked_at = ? WHERE key_prefix = ? AND is_active = 1",
            (now, prefix),
        )
        await self._conn.commit()
        return cur.rowcount > 0

    async def list_keys(self) -> list[dict]:
        if not self._conn:
            return []
        cur = await self._conn.execute(
            "SELECT id, key_prefix, name, team, is_active, created_at, last_used_at, revoked_at "
            "FROM api_keys ORDER BY created_at DESC"
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None


async def _migrate_from_env(db: aiosqlite.Connection) -> None:
    from config import settings
    if settings.api_keys == "#":
        return
    cur = await db.execute("SELECT COUNT(*) FROM api_keys")
    row = await cur.fetchone()
    if row and row[0] > 0:
        return
    now = datetime.now(timezone.utc).isoformat()
    for item in settings.api_keys_list:
        if "=" in item:
            key, name = item.split("=", 1)
        else:
            key, name = item, "unknown"
        kh = hash_api_key(key)
        prefix = key_prefix(key)
        await db.execute(
            "INSERT OR IGNORE INTO api_keys (key_prefix, key_hash, name, team, created_at) VALUES (?, ?, ?, ?, ?)",
            (prefix, kh, name, "", now),
        )
    await db.commit()
    logger.info("Migrated %d API keys from env to DB", len(settings.api_keys_list))


async def _v1(db: aiosqlite.Connection) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            key_prefix   TEXT NOT NULL,
            key_hash     TEXT NOT NULL UNIQUE,
            name         TEXT NOT NULL,
            team         TEXT DEFAULT '',
            is_active    INTEGER DEFAULT 1,
            created_at   TEXT NOT NULL,
            last_used_at TEXT,
            revoked_at   TEXT
        )
    """)
    await _migrate_from_env(db)


MIGRATIONS = {1: _v1}

key_db: Optional[KeyDB] = None
