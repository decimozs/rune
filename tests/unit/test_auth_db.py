import hashlib
import pytest
from unittest.mock import patch, AsyncMock

from services.auth import verify_api_key
from services.db import KeyDB, hash_api_key, key_prefix, generate_raw_key


@pytest.fixture
async def db(tmp_path):
    path = str(tmp_path / "test.db")
    db = KeyDB(path)
    with patch("config.settings.api_keys", "#"):
        await db.init()
    yield db
    await db.close()


@pytest.fixture
def settings_with_db(db):
    with patch("services.auth.settings.db_path", db.db_path), \
         patch("services.db.key_db", db):
        yield


class TestDbAuth:
    async def _call(self, key=None):
        return await verify_api_key(key)

    async def test_db_disabled_no_auth(self):
        with patch("services.auth.settings.db_path", ""), \
             patch("services.auth.settings.api_keys", "#"):
            assert await self._call(None) is None
            assert await self._call("any-key") is None

    async def test_db_mode_missing_key(self, db, settings_with_db):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await self._call(None)
        assert exc.value.status_code == 401

    async def test_db_mode_valid_key(self, db, settings_with_db):
        raw = generate_raw_key()
        kh = hash_api_key(raw)
        prefix = key_prefix(raw)
        await db.add_key(kh, prefix, "test-user", "eng")
        name = await self._call(raw)
        assert name == "test-user"

    async def test_db_mode_wrong_key(self, db, settings_with_db):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await self._call("sk_live_wrongkey1234567890abcdefghijklmnopqrs")
        assert exc.value.status_code == 401

    async def test_db_mode_revoked_key_fails(self, db, settings_with_db):
        raw = generate_raw_key()
        kh = hash_api_key(raw)
        prefix = key_prefix(raw)
        await db.add_key(kh, prefix, "test-user", "eng")
        await db.revoke_key(kh)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await self._call(raw)
        assert exc.value.status_code == 401

    async def test_db_mode_update_last_used(self, db, settings_with_db):
        raw = generate_raw_key()
        kh = hash_api_key(raw)
        prefix = key_prefix(raw)
        await db.add_key(kh, prefix, "test-user", "eng")
        await self._call(raw)
        keys = await db.list_keys()
        assert keys[0]["last_used_at"] is not None

    async def test_env_fallback_when_db_path_empty(self, db, settings_with_db):
        with patch("services.auth.settings.db_path", ""), \
             patch("services.auth.settings.api_keys", "sk-fallback=admin"):
            assert await self._call("sk-fallback") == "admin"

    async def test_env_fallback_disabled(self, db, settings_with_db):
        with patch("services.auth.settings.db_path", ""), \
             patch("services.auth.settings.api_keys", "#"):
            assert await self._call(None) is None


class TestKeyDB:
    async def test_init_creates_tables(self, tmp_path):
        path = str(tmp_path / "test.db")
        db = KeyDB(path)
        with patch("config.settings.api_keys", "#"):
            await db.init()
        keys = await db.list_keys()
        assert keys == []
        await db.close()

    async def test_add_and_list_key(self, db):
        raw = generate_raw_key()
        kh = hash_api_key(raw)
        prefix = key_prefix(raw)
        await db.add_key(kh, prefix, "alice", "engineering")
        keys = await db.list_keys()
        assert len(keys) == 1
        assert keys[0]["name"] == "alice"
        assert keys[0]["team"] == "engineering"
        assert keys[0]["is_active"] == 1

    async def test_get_key(self, db):
        raw = generate_raw_key()
        kh = hash_api_key(raw)
        prefix = key_prefix(raw)
        await db.add_key(kh, prefix, "bob", "ops")
        key = await db.get_key(kh)
        assert key is not None
        assert key["name"] == "bob"
        assert key["is_active"] is True

    async def test_get_key_not_found(self, db):
        key = await db.get_key("nonexistent_hash")
        assert key is None

    async def test_revoke_key(self, db):
        raw = generate_raw_key()
        kh = hash_api_key(raw)
        prefix = key_prefix(raw)
        await db.add_key(kh, prefix, "charlie", "qa")
        ok = await db.revoke_key(kh)
        assert ok is True
        key = await db.get_key(kh)
        assert key["is_active"] is False
        assert key["name"] == "charlie"

    async def test_revoke_by_prefix(self, db):
        raw = generate_raw_key()
        kh = hash_api_key(raw)
        prefix = key_prefix(raw)
        await db.add_key(kh, prefix, "dave", "devops")
        ok = await db.revoke_by_prefix(prefix)
        assert ok is True
        key = await db.get_key(kh)
        assert key["is_active"] is False

    async def test_revoke_by_prefix_not_found(self, db):
        ok = await db.revoke_by_prefix("nonexistent_prefix")
        assert ok is False

    async def test_double_revoke_idempotent(self, db):
        raw = generate_raw_key()
        kh = hash_api_key(raw)
        prefix = key_prefix(raw)
        await db.add_key(kh, prefix, "eve", "sec")
        await db.revoke_key(kh)
        ok = await db.revoke_key(kh)
        assert ok is False

    async def test_multiple_keys(self, db):
        for i in range(5):
            raw = generate_raw_key()
            kh = hash_api_key(raw)
            prefix = key_prefix(raw)
            await db.add_key(kh, prefix, f"user{i}", f"team{i}")
        keys = await db.list_keys()
        assert len(keys) == 5

    async def test_add_duplicate_key_hash(self, db):
        raw = generate_raw_key()
        kh = hash_api_key(raw)
        prefix = key_prefix(raw)
        await db.add_key(kh, prefix, "first", "team")
        with pytest.raises(Exception):
            await db.add_key(kh, prefix, "second", "team")


class TestKeyHelpers:
    def test_hash_api_key(self):
        h = hash_api_key("sk_live_test")
        expected = hashlib.sha256(b"sk_live_test").hexdigest()
        assert h == expected

    def test_key_prefix(self):
        assert key_prefix("sk_live_AbCdEf1234567890") == "sk_live_AbCdEf12"

    def test_generate_raw_key_starts_with_prefix(self):
        raw = generate_raw_key()
        assert raw.startswith("sk_live_")
        assert len(raw) > 40

    def test_hash_is_deterministic(self):
        assert hash_api_key("abc") == hash_api_key("abc")

    def test_hash_differs_for_diff_keys(self):
        assert hash_api_key("key1") != hash_api_key("key2")
