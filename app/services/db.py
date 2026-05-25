"""SQLite-backed API key registry with schema versioning.

Keys are stored as SHA-256 hashes (never plaintext). The module-level
key_db singleton is None at import time and wired in main.py lifespan
when OCR_DB_PATH is configured.

Schema migrations are incremental: new numbered functions added to
MIGRATIONS dict run in order on startup. The _schema_version table
tracks which have been applied.
"""

import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1


def hash_api_key(raw: str) -> str:
    """Return SHA-256 hex digest of a raw API key string."""
    return hashlib.sha256(raw.encode()).hexdigest()


def key_prefix(raw: str) -> str:
    """First 16 chars of the raw key. Used for display and revocation."""
    return raw[:16]


def generate_raw_key() -> str:
    """Generate a high-entropy API key with sk_live_ prefix.

    The raw key is returned once at creation time and cannot be
    recovered later. The SHA-256 hash is what gets stored.
    """
    import secrets

    return "sk_live_" + secrets.token_urlsafe(32)


class KeyDB:
    """Async SQLite wrapper for API key CRUD operations."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    @property
    def is_initialized(self) -> bool:
        """True after init() completes successfully."""
        return self._conn is not None

    async def init(self) -> None:
        """Open the DB connection, create parent dirs, run pending migrations."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._migrate()
        logger.info(
            "KeyDB initialized at %s (schema v%d)", self.db_path, SCHEMA_VERSION
        )

    async def _migrate(self) -> None:
        """Apply any pending schema migrations in order."""
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
                    (v, datetime.now(UTC).isoformat()),
                )
        await self._conn.commit()

    async def get_key(self, key_hash: str) -> dict | None:
        """Look up a key by its SHA-256 hash. Returns None if not found."""
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
        """Record the current timestamp as last_used_at for audit."""
        if not self._conn:
            return
        await self._conn.execute(
            "UPDATE api_keys SET last_used_at = ? WHERE key_hash = ?",
            (datetime.now(UTC).isoformat(), key_hash),
        )
        await self._conn.commit()

    async def add_key(
        self, key_hash: str, prefix: str, name: str, team: str = ""
    ) -> None:
        """Insert a new key. Raises IntegrityError if key_hash already exists."""
        if not self._conn:
            raise RuntimeError("KeyDB not initialized")
        now = datetime.now(UTC).isoformat()
        await self._conn.execute(
            "INSERT INTO api_keys (key_prefix, key_hash, name, team, created_at) VALUES (?, ?, ?, ?, ?)",
            (prefix, key_hash, name, team, now),
        )
        await self._conn.commit()

    async def revoke_key(self, key_hash: str) -> bool:
        """Soft-delete a key by hash. Returns True if a key was actually revoked."""
        if not self._conn:
            return False
        now = datetime.now(UTC).isoformat()
        cur = await self._conn.execute(
            "UPDATE api_keys SET is_active = 0, revoked_at = ? WHERE key_hash = ? AND is_active = 1",
            (now, key_hash),
        )
        await self._conn.commit()
        return cur.rowcount > 0

    async def revoke_by_prefix(self, prefix: str) -> bool:
        """Soft-delete keys by prefix. Returns True if at least one revoked."""
        if not self._conn:
            return False
        now = datetime.now(UTC).isoformat()
        cur = await self._conn.execute(
            "UPDATE api_keys SET is_active = 0, revoked_at = ? WHERE key_prefix = ? AND is_active = 1",
            (now, prefix),
        )
        await self._conn.commit()
        return cur.rowcount > 0

    async def list_keys(self) -> list[dict]:
        """Return all keys ordered by creation date (newest first)."""
        if not self._conn:
            return []
        cur = await self._conn.execute(
            "SELECT id, key_prefix, name, team, is_active, created_at, last_used_at, revoked_at "
            "FROM api_keys ORDER BY created_at DESC"
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def close(self) -> None:
        """Close the DB connection. Called in lifespan shutdown."""
        if self._conn:
            await self._conn.close()
            self._conn = None


async def _migrate_from_env(db: aiosqlite.Connection) -> None:
    """Bootstrap: copy hashed entries from OCR_API_KEYS env var into DB.

    Only runs when the api_keys table is empty (first startup with DB mode).
    After migration, the env var is no longer needed — the DB is the source
    of truth.
    """
    from config import settings

    if settings.api_keys == "#":
        return
    cur = await db.execute("SELECT COUNT(*) FROM api_keys")
    row = await cur.fetchone()
    if row and row[0] > 0:
        return
    now = datetime.now(UTC).isoformat()
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
    """Schema v1: create api_keys table and bootstrap from env vars."""
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

# Module-level singleton. None at import time; set in main.py lifespan
# when OCR_DB_PATH is configured. Consumers must guard against None.
key_db: KeyDB | None = None
