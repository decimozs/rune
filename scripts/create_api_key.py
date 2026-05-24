#!/usr/bin/env python
"""Generate a new API key and store in SQLite."""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from services.db import hash_api_key, key_prefix, generate_raw_key, KeyDB


def main():
    parser = argparse.ArgumentParser(description="Create a new API key")
    parser.add_argument("--name", required=True, help="Key owner name")
    parser.add_argument("--team", default="", help="Team name")
    parser.add_argument(
        "--db-path",
        default=os.environ.get("OCR_DB_PATH", ""),
        help="Path to SQLite DB (default: OCR_DB_PATH env var)",
    )
    args = parser.parse_args()

    if not args.db_path:
        print("Error: --db-path required or set OCR_DB_PATH env var", file=sys.stderr)
        sys.exit(1)

    raw_key = generate_raw_key()
    kh = hash_api_key(raw_key)
    prefix = key_prefix(raw_key)

    import asyncio

    async def run():
        db = KeyDB(args.db_path)
        await db.init()
        await db.add_key(kh, prefix, args.name, args.team)
        await db.close()

    asyncio.run(run())

    print(f"API key: {raw_key}")
    print(f"Name:    {args.name}")
    print(f"Team:    {args.team or '(none)'}")
    print("Save this key now. It will not be shown again.")


if __name__ == "__main__":
    main()
