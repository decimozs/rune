#!/usr/bin/env python
"""List all API keys stored in SQLite with their metadata.

Shows key prefix (first 16 chars), owner name, team, active status,
creation date, last-used timestamp, and revocation date.
Key hashes are never displayed — only the prefix is shown.
"""

import argparse
import os
import sys
from pathlib import Path

# Add app/ to path so we can import services.db. Scripts run from
# the project root or scripts/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from services.db import KeyDB


def main():
    parser = argparse.ArgumentParser(description="List API keys")
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
        keys = await db.list_keys()
        await db.close()
        return keys

    keys = asyncio.run(run())

    if not keys:
        print("No API keys found.")
        return

    print(f"{'ID':<4} {'Prefix':<20} {'Name':<20} {'Team':<20} {'Active':<8} {'Created':<24} {'Last Used':<24} {'Revoked':<24}")
    print("-" * 144)
    for k in keys:
        active = "yes" if k["is_active"] else "no"
        lu = k.get("last_used_at") or ""
        rv = k.get("revoked_at") or ""
        print(f"{k['id']:<4} {k['key_prefix']:<20} {k['name']:<20} {k['team']:<20} {active:<8} {k['created_at']:<24} {lu:<24} {rv:<24}")


if __name__ == "__main__":
    main()
