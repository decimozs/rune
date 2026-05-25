# Understanding Your Results

## JSON Output (Most Detailed)

JSON output gives you a structured breakdown of every word found on every page. Here is what a typical response looks like:

```json
{
  "success": true,
  "metadata": {
    "model": "PP-OCRv4",
    "processing_time_ms": 123.45,
    "file_name": "receipt.png",
    "file_type": "image/png"
  },
  "data": {
    "pages": [
      {
        "page": 1,
        "words": [
          {
            "text": "Total:",
            "confidence": 0.9876,
            "bbox": {
              "points": [[10, 20], [100, 20], [100, 40], [10, 40]]
            }
          },
          {
            "text": "$42.00",
            "confidence": 0.9543,
            "bbox": {
              "points": [[110, 20], [200, 20], [200, 40], [110, 40]]
            }
          }
        ],
        "extracted_text": "Total: $42.00",
        "page_image_url": "http://localhost:8080/assets/pages/a1b2c3d4/page_1.png",
        "ocr_width": 1200,
        "ocr_height": 1600
      }
    ]
  }
}
```

### Fields Explained

| Field | Meaning |
|---|---|
| `success` | `true` if everything worked, `false` if there was an error |
| `processing_time_ms` | How long the server took to process your file (in milliseconds). 1000 ms = 1 second |
| `pages` | One entry per page in your document |
| `page` | The page number (1 = first page) |
| `words` | Every word or text fragment found on this page |
| `text` | The actual word that was read |
| `confidence` | How sure the system is it read this word correctly. 1.0 = 100% sure, 0.5 = 50% sure. Think of it like a test score — higher is better |
| `bbox` (bounding box) | Where the word is on the page, as coordinates. The four points are: top-left, top-right, bottom-right, bottom-left |
| `extracted_text` | All words on this page combined into one block of text |
| `page_image_url` | A link to the page image with detected text regions visible. Open this in your browser to see what the system "saw" |

### Understanding Confidence Scores

- **0.95 - 1.00:** Excellent. The system is very confident this is correct
- **0.80 - 0.94:** Good. The text is likely correct, but double-check if it is important
- **0.50 - 0.79:** Fair. The system is less sure — the text might have errors
- **Below 0.50:** Low confidence. Manually verify the text, or check the original image

Think of confidence like autocorrect on your phone. When it is confident, it changes words without asking. When it is less confident, it suggests alternatives. With OCR, you can check the low-confidence words against the page image.

### Understanding Coordinates (bbox)

The bounding box tells you WHERE on the page the word appears. The coordinates use the format `[x, y]` where:

- `x` = how far from the left edge of the page (in pixels)
- `y` = how far from the top edge of the page (in pixels)

If you see:
```json
"bbox": {
  "points": [[10, 20], [100, 20], [100, 40], [10, 40]]
}
```

This means the word starts 10 pixels from the left and 20 pixels from the top, and is 90 pixels wide and 20 pixels tall.

## Markdown Output (Formatted Text)

Markdown output is better for documents with structure — tables, headings, lists. It looks similar to the original document's layout.

```markdown
# Annual Report 2025

## Executive Summary

Revenue increased by 15% compared to the previous year.

| Quarter | Revenue | Growth |
|---|---|---|
| Q1 | $1.2M | +12% |
| Q2 | $1.4M | +18% |
```

Images found in the document are saved separately and linked in the markdown:

```markdown
![Chart](http://localhost:8080/assets/imgs/img_in_image_box_0_0_400_300.jpg)
```

You can combine markdown output with page images to get the best of both: the formatted text structure plus the visual context.

## XML Output (Technical Format)

XML is a structured format often used for integration with other software systems. It contains the same information as JSON, but in a different structure:

```xml
<?xml version="1.0" ?>
<ocrResult>
  <page number="1">
    <words>
      <word confidence="0.9876">
        <text>Total:</text>
        <bbox>
          <point x="10" y="20"/>
          <point x="100" y="20"/>
          <point x="100" y="40"/>
          <point x="10" y="40"/>
        </bbox>
      </word>
    </words>
  </page>
</ocrResult>
```

## Comparison Table

| Format | Best For | Includes Positions? | Includes Images? |
|---|---|---|---|
| JSON | Developers, data analysis | Yes | Yes (if requested) |
| Markdown | Documents with tables/layout | No | Yes (linked inline) |
| XML | Integration with other tools | Yes | No |

## Viewing Page Images

When you use JSON output with `include_page_image=true` (the default), the response includes a URL for each page's image. Open that URL in your browser to see what the system analyzed.

The page image shows the document page as the system "saw" it — useful for comparing the extracted text against the original image to catch any errors.

## Next Steps

- If the extracted text has errors, try using a higher quality image (higher resolution, better lighting)
- For documents with complex tables, try the Markdown format — it handles table structure better
- If you only need the text without positions, set `include_bbox=false&include_confidence=false&include_page_image=false` for a lighter response
