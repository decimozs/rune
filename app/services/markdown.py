from pathlib import Path


class MarkdownConverter:
    OUTPUT_DIR = Path("app/outputs")

    def __init__(self, structure_engine):
        self.engine = structure_engine

    def convert(self, result, image_path: str, filename: str, content_type: str) -> str:
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        if content_type == "application/pdf":
            return self._handle_pdf(result, filename)

        return self._handle_image(result, image_path)

    def _handle_pdf(self, result, filename: str) -> str:
        markdown_list = []
        markdown_images = []

        for res in result:
            md_info = res.markdown
            markdown_list.append(md_info)
            markdown_images.append(md_info.get("markdown_images", {}))

        markdown_result_obj = self.engine.concatenate_pages(markdown_list)

        if isinstance(markdown_result_obj, dict):
            raw_markdown_text = markdown_result_obj.get("markdown_texts", "")
        else:
            raw_markdown_text = getattr(
                markdown_result_obj, "text", str(markdown_result_obj)
            )

        if not raw_markdown_text:
            raw_markdown_text = "\n\n---\n\n".join(
                [
                    item.get("markdown_texts", "") if isinstance(item, dict) else ""
                    for item in markdown_list
                ]
            )

        mkd_file_path = self.OUTPUT_DIR / f"{filename}.md"
        with open(mkd_file_path, "w", encoding="utf-8") as f:
            f.write(raw_markdown_text)

        for item in markdown_images:
            if item:
                for path, image in item.items():
                    if path and image:
                        file_path = self.OUTPUT_DIR / path
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        image.save(file_path)

        return raw_markdown_text

    def _handle_image(self, result, image_path: str) -> str:
        for res in result:
            res.save_to_markdown(save_path=str(self.OUTPUT_DIR))

        img_stem = Path(image_path).stem
        saved_md_path = self.OUTPUT_DIR / img_stem / f"{img_stem}_saved.md"

        if not saved_md_path.exists():
            saved_md_path = self.OUTPUT_DIR / f"{img_stem}.md"

        if saved_md_path.exists():
            with open(saved_md_path, "r", encoding="utf-8") as f:
                return f.read()

        return ""
