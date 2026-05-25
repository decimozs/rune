"""Periodic sweep of stale output files.

Page images and markdown assets accumulate under outputs/pages/ and
outputs/imgs/. This module removes files whose mtime exceeds the
configured TTL (default 3600s, configurable via OCR_OUTPUT_TTL).

The sweep runs every 5 minutes as a background asyncio task managed
in main.py lifespan.
"""

import asyncio
import contextlib
import logging
import time
from pathlib import Path

from config import settings

logger = logging.getLogger(__name__)

_SWEEP_INTERVAL = 300  # 5 min between sweeps


class OutputCleaner:
    """Background task that removes expired OCR output files."""

    def __init__(self):
        self._task: asyncio.Task | None = None

    async def start(self):
        """Start the periodic sweep loop. Called in lifespan."""
        self._task = asyncio.create_task(self._sweep_loop())

    async def stop(self):
        """Cancel the sweep loop. Called in lifespan shutdown."""
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _sweep_loop(self):
        """Sleep then sweep, forever."""
        while True:
            await asyncio.sleep(_SWEEP_INTERVAL)
            self._sweep()

    def _sweep(self):
        """Check both pages/ and imgs/ subdirectories for stale files."""
        now = time.time()
        ttl = settings.output_ttl
        base = settings.output_dir_path
        for sub in ("pages", "imgs"):
            target = base / sub
            if not target.is_dir():
                continue
            if sub == "pages":
                self._sweep_pages(target, now, ttl)
            else:
                self._sweep_imgs(target, now, ttl)

    def _sweep_pages(self, pages_dir: Path, now: float, ttl: int):
        """Remove per-document page image directories older than TTL."""
        for entry in pages_dir.iterdir():
            if not entry.is_dir():
                continue
            try:
                mtime = entry.stat().st_mtime
            except OSError:
                continue
            if now - mtime > ttl:
                _rmtree(entry)
                logger.info("Cleaned expired page dir %s", entry.name)

    def _sweep_imgs(self, imgs_dir: Path, now: float, ttl: int):
        """Remove individual markdown image files older than TTL."""
        for entry in imgs_dir.iterdir():
            if not entry.is_file():
                continue
            try:
                mtime = entry.stat().st_mtime
            except OSError:
                continue
            if now - mtime > ttl:
                entry.unlink(missing_ok=True)
                logger.info("Cleaned expired markdown image %s", entry.name)


def _rmtree(d: Path):
    """Recursive directory deletion. Manual impl avoids shutil.rmtree."""
    for child in d.iterdir():
        if child.is_dir():
            _rmtree(child)
        else:
            child.unlink(missing_ok=True)
    d.rmdir()


output_cleaner = OutputCleaner()
