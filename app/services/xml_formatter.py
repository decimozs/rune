"""Convert OCR results to pretty-printed XML using stdlib only.

Element structure::

    <ocrResult>
      <page number="1">
        <words>
          <word confidence="0.98">
            <text>Hello</text>
            <bbox>
              <point x="10" y="20"/>
              ...
            </bbox>
          </word>
        </words>
        <extractedText>Hello world</extractedText>
      </page>
    </ocrResult>

Uses ElementTree for structure and minidom for pretty-printing.
No third-party dependencies.
"""

from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from typing import Any
from schemas.ocr import OCRResult


def to_xml(result: dict[str, Any]) -> str:
    """Build pretty-printed XML string from an OCR result dict."""
    ocr = OCRResult(**result)
    root = Element("ocrResult")

    for page in ocr.pages:
        page_el = SubElement(root, "page", number=str(page.page))
        words_el = SubElement(page_el, "words")

        for w in page.words:
            word_el = SubElement(words_el, "word", confidence=str(round(w.confidence, 4)))
            text_el = SubElement(word_el, "text")
            text_el.text = w.text
            _build_bbox(word_el, w.bbox.points)

        extracted_el = SubElement(page_el, "extractedText")
        extracted_el.text = page.extracted_text

    rough = tostring(root, encoding="unicode")
    dom = minidom.parseString(rough)
    return dom.toprettyxml(indent="  ")


def _build_bbox(parent: Element, points: list[list[float | int]]) -> None:
    """Append ``<bbox>`` child with one ``<point>`` per corner."""
    bbox_el = SubElement(parent, "bbox")
    for pt in points:
        SubElement(bbox_el, "point", x=str(int(pt[0])), y=str(int(pt[1])))
