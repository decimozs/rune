import logging
from config import settings

logger = logging.getLogger(__name__)


class MarkdownConverter:
    def __init__(self, structure_engine):
        self.engine = structure_engine

    def convert(
        self,
        result,
        image_path: str,
        filename: str,
        content_type: str,
    ) -> str:
        settings.output_dir_path.mkdir(parents=True, exist_ok=True)

        if content_type == "application/pdf":
            return self._handle_pdf(result, filename).lstrip("\n")
        return self._handle_image(result).lstrip("\n")

    def _handle_pdf(self, result, filename: str) -> str:
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

        if not raw_text:
            raw_text = "\n\n---\n\n".join(
                item.get("markdown_texts", "") if isinstance(item, dict) else ""
                for item in markdown_list
            )

        raw_text = raw_text.lstrip("\n")

        mkd_file_path = settings.output_dir_path / f"{filename}.md"
        with open(mkd_file_path, "w", encoding="utf-8") as f:
            f.write(raw_text)

        for item in markdown_images:
            if item:
                for path, image in item.items():
                    if path and image:
                        file_path = settings.output_dir_path / path
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        image.save(file_path)

        return raw_text

    def _handle_image(self, result) -> str:
        # use res.markdown directly — no disk roundtrip
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

        return raw_text
