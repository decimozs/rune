"""Convert PPStructureV3 output to markdown text.

PPStructureV3 returns a per-page result object with a .markdown
attribute containing markdown text and embedded image references.
This module merges per-page results, saves images to disk, and
rewrites image paths so they serve from the /assets/ static mount.

PDF and image inputs share the same logic. The only difference is
that PDF markdown is also written to {output_dir}/{filename}.md
on disk for direct file access.
"""

import logging
import re
from typing import TYPE_CHECKING

from config import settings

if TYPE_CHECKING:
    from services.engine import StructureEngineProtocol

logger = logging.getLogger(__name__)


class MarkdownConverter:
    """Converts PPStructureV3 results into markdown with served image URLs."""

    def __init__(self, structure_engine: "StructureEngineProtocol"):
        self.engine = structure_engine

    def convert(
        self,
        result,
        image_path: str,
        filename: str,
        content_type: str,
    ) -> str:
        """Convert structure engine result to markdown string.

        Args:
            result: PPStructureV3 output (list of page result objects).
            image_path: Unused (kept for consistent interface with OCRService).
            filename: Stem used for .md file when input is a PDF.
            content_type: Determines whether to write .md to disk.

        Returns:
            Markdown string with /assets/imgs/ paths for images.
        """
        settings.output_dir_path.mkdir(parents=True, exist_ok=True)

        if content_type == "application/pdf":
            return self._handle_pdf(result, filename).lstrip("\n")
        return self._handle_image(result).lstrip("\n")

    def _handle_pdf(self, result, filename: str) -> str:
        """Process PDF: concatenate pages, save .md and images to disk."""
        markdown_list = []
        markdown_images = []

        for res in result:
            md_info = res.markdown
            markdown_list.append(md_info)
            markdown_images.append(md_info.get("markdown_images", {}))

        markdown_result = self.engine.concatenate_pages(markdown_list)

        # PPStructureV3 returns either a dict or an object depending on version
        if isinstance(markdown_result, dict):
            raw_text = markdown_result.get("markdown_texts", "")
        else:
            raw_text = getattr(markdown_result, "text", str(markdown_result))

        # Fallback if concatenate_pages returns nothing (defensive)
        if not raw_text:
            raw_text = "\n\n---\n\n".join(
                item.get("markdown_texts", "") if isinstance(item, dict) else ""
                for item in markdown_list
            )

        raw_text = raw_text.lstrip("\n")

        # Write .md to disk for direct file access
        mkd_file_path = settings.output_dir_path / f"{filename}.md"
        with open(mkd_file_path, "w", encoding="utf-8") as f:
            f.write(raw_text)

        # Save embedded images to disk
        for item in markdown_images:
            if item:
                for path, image in item.items():
                    if path and image:
                        file_path = settings.output_dir_path / path
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        image.save(file_path)

        # Rewrite relative imgs/ paths to absolute /assets/imgs/ URLs
        raw_text = re.sub(r"(!\[.*?\]\()imgs/", r"\1/assets/imgs/", raw_text)
        raw_text = re.sub(r'(<img[^>]*src=")imgs/', r"\1/assets/imgs/", raw_text)
        return raw_text

    def _handle_image(self, result) -> str:
        """Process single image: concatenate pages, save images, return text.

        Unlike _handle_pdf, does NOT write a .md file to disk.
        """
        markdown_list = []
        markdown_images = []

        for res in result:
            md_info = res.markdown
            markdown_list.append(md_info)
            markdown_images.append(md_info.get("markdown_images", {}))

        markdown_result = self.engine.concatenate_pages(markdown_list)

        if isinstance(markdown_result, dict):
            raw_text = markdown_result.get("markdown_texts", "")
        else:
            raw_text = getattr(markdown_result, "text", str(markdown_result))

        raw_text = raw_text.lstrip("\n")

        for item in markdown_images:
            if item:
                for path, image in item.items():
                    if path and image:
                        file_path = settings.output_dir_path / path
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        image.save(file_path)

        # Rewrite relative imgs/ paths to absolute /assets/imgs/ URLs
        raw_text = re.sub(r"(!\[.*?\]\()imgs/", r"\1/assets/imgs/", raw_text)
        raw_text = re.sub(r'(<img[^>]*src=")imgs/', r"\1/assets/imgs/", raw_text)
        return raw_text
