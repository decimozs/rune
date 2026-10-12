# What Is This? A Tool That Reads Text From Images

## In Plain English

Have you ever taken a photo of a document and wished you could copy the text from it? Or received a scanned PDF and needed to edit the words inside?

This tool does exactly that. It looks at images and documents, finds the text inside them, and gives you back the words in a format you can use.

Think of it like:

- **Google Docs** — when you upload a scanned PDF and it offers to "Open with Google Docs" to extract the text
- **Adobe Acrobat** — when you use "Export PDF" to turn a scanned document into editable text
- **iPhone/Android** — when you take a photo of a business card and your phone offers to save the contact details

The difference: this tool runs on your own company's infrastructure. Your documents never leave your network.

## What Can You Feed It?

| File Type | Examples |
|---|---|
| Images | PNG, JPG, BMP, TIFF, WebP — photos of documents, screenshots, scanned pages |
| PDFs | Scanned documents, digital PDFs, forms |
| Office documents | Word (DOCX), Excel (XLSX), PowerPoint (PPTX), CSV files |
| Web pages | Any public URL — the tool visits the page and reads the text |
| HTML | A webpage file you upload, plus any images or stylesheets it needs |

## What Do You Get Back?

**JSON (most detailed):** A structured list of every word found, where it was on the page (position coordinates), and how confident the system is that it read it correctly.

**Markdown:** A formatted document that looks similar to the original — useful for documents with tables, headings, and layouts.

**XML:** A technical format often used for integrating with other software systems.

## Who Should Use This?

- **Marketing teams** — extract text from brochures, competitor materials, or printed reports
- **Operations teams** — digitize paper forms, invoices, shipping documents
- **Engineering teams** — automate document processing in their applications
- **Legal teams** — search through scanned contracts and agreements

## How Accurate Is It?

On clear, well-scanned documents, accuracy is typically over 95%. Performance depends on:

- **Image quality** — clear, well-lit scans work best. Blurry photos or low-resolution images reduce accuracy
- **Language** — the system is optimized for English but supports many languages
- **Handwriting** — printed text works well. Handwriting recognition is less reliable
- **Layout complexity** — simple documents with clear text regions work best. Dense tables or unusual layouts may have errors

For reference, Google Cloud Vision reports similar accuracy ranges of 95-99% for printed text on clear documents.

## How Is This Different From Cloud Services?

| | This Tool | Google Cloud Vision | AWS Textract | Adobe Acrobat |
|---|---|---|---|---|
| **Runs on your network** | Yes | No | No | No |
| **Per-document cost** | Free (internal) | Per-page fee | Per-page fee | Subscription fee |
| **Privacy** | Data stays in-house | Data sent to Google | Data sent to AWS | Data sent to Adobe |
| **Requires internet** | No | Yes | Yes | Yes |
| **Office documents** | Yes | No | No | Yes |

## Where Does the Text Go?

The extracted text is returned to you as a response from the API. It is not stored permanently.

The images generated during processing (page snapshots) are temporary — they are automatically deleted after one hour. The original files you uploaded are deleted immediately after processing.

This is the same approach used by Gmail's "View as HTML" feature for email attachments — process the file, return the result, delete the original.
