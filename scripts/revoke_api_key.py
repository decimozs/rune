#!/usr/bin/env python
"""Revoke an API key by key prefix."""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from services.db import KeyDB


def main():
    parser = argparse.ArgumentParser(description="Revoke an API key")
    parser.add_argument("--prefix", required=True, help="Key prefix to revoke (first 16 chars)")
    parser.add_argument(
        "--db-path",
        default=os.environ.get("OCR_DB_PATH", ""),
        help="Path to SQLite DB (default: OCR_DB_PATH env var)",
    )
    args = parser.parse_args()

    if not args.db_path:
        print("Error: --db-path required or set OCR_DB_PATH env var", file=sys.stderr)
        sys.exit(1)

    import asyncio

    async def run():
        db = KeyDB(args.db_path)
        await db.init()
        ok = await db.revoke_by_prefix(args.prefix)
        await db.close()
        return ok

    ok = asyncio.run(run())
    if ok:
        print(f"Key '{args.prefix}' revoked.")
    else:
        print(f"No active key with prefix '{args.prefix}' found.")
        sys.exit(1)


if __name__ == "__main__":
    main()
