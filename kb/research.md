# Research References

Related studies, benchmarks, and surveys relevant to the Exist OCR system.

## Core OCR Engine

| Reference | Relevance |
|---|---|
| **PP-OCRv4 Technical Report** — PaddleOCR PMC. [PaddleOCR Docs](https://paddlepaddle.github.io/PaddleOCR/v2.9/ppocr/blog/PP-OCRv4_introduction.html) | Primary engine. PP-OCRv4: text detection (DB++ with PFHead, PP-LCNetV3 backbone, CML distillation) + recognition (SVTR- LCNetV3, GTC-NRTR, DKD distillation). Chinese end-to-end Hmean 62.24% (+4.5% vs v3), English ACC 70.1% (+6%), multilingual avg +8%. Exist uses this exact pipeline. |
| **PaddleOCR 3.0 Technical Report** — arXiv:2507.05595. [PDF](https://arxiv.org/pdf/2507.05595) | PP-OCRv5: lightweight OCR matching/exceeding multimodal LLMs (GOT-OCR2.0, Qwen2.5-VL-72B, GPT-4o) on Chinese/English document OCR. 0.07B params vs 7B–78B models. Relevant when upgrading engine. |
| **PaddleX OCR Pipeline Docs** — [PaddleX](https://paddlepaddle.github.io/PaddleX/3.4/en/module_usage/tutorials/ocr_modules/text_recognition.html) | Model zoo: PP-OCRv4_server_rec_doc (86.58% acc, 182MB, 15K+ chars including traditional Chinese/Japanese), mobile_rec (78.74%, 10.5MB). Server detection 82.69% Hmean, mobile 77.79%. Exist uses PaddleOCR Python SDK — same model family. |

## OCR Engine Comparison

| Reference | Relevance |
|---|---|
| **PaddleOCR vs EasyOCR vs Doctr: Memory & Latency Benchmark** — TildAlice, 2026. [Link](https://tildalice.io/paddleocr-easyocr-doctr-memory-latency-benchmark/) | PaddleOCR: 2.1s init, 450MB idle, 340ms/image, 220ms/image batch-8. 1.7× faster than EasyOCR, 1.4× faster than Doctr. Lower memory footprint (450MB vs 800MB EasyOCR). Validates PaddleOCR choice for containerized deployment. |
| **Document Converter Benchmark: Gotenberg vs Carbone vs Jod-converter vs Collabora** — Carbone.io, 2025. [GitHub](https://github.com/carboneio/document-converter-benchmark) | Gotenberg HTML→PDF: 432.60ms avg, 11.52 RPS (single-threaded). Carbone: 9.27ms, 529.62 RPS (4 threads). Gotenberg does not support multi-threading — limitation for high-throughput document conversion. |

## Document Conversion

| Reference | Relevance |
|---|---|
| **Gotenberg Documentation** — [gotenberg.dev](https://gotenberg.dev/) | Docker-based API: Chromium (HTML/URL/MD→PDF), LibreOffice (100+ formats), PDF engines (merge/split/encrypt/watermark). S3 direct-fetch pipelines, webhook events. Exist integrates Gotenberg at `/forms/libreoffice/convert` and `/forms/chromium/convert/url`. |
| **Gotenberg PDF: Setup and Automation Guide** — CodeWords, 2026. [Link](https://www.codewords.ai/blog/gotenberg-pdf) | 7.5K+ GitHub stars, 2M+ Docker pulls/month. 34% of devs use containerized conversion services (up from 19% in 2023). Chromium rendering supports modern CSS/JS — relevant for URL/HTML input sources in Exist. |

## Document Intelligence & Parsing Surveys

| Reference | Relevance |
|---|---|
| **Document Parsing Unveiled: Techniques, Challenges, and Prospects** — arXiv:2410.21169, 2024. [HTML](https://arxiv.org/html/2410.21169v5) | Comprehensive survey: pipeline-based (layout analysis → OCR → table/equation/MER) vs VLM-based unified models. Taxonomy covering modular systems like Exist's architecture. |
| **AI-Driven Approaches for Unstructured Document Analysis** — Journal of Big Data 11, 92, 2024. [Springer](https://link.springer.com/article/10.1186/s40537-024-00948-z) | SLR on AI information extraction from unstructured docs. Identifies pattern/rule-based extraction inadequacy for complex layouts. Advocates hybrid AI approaches. |
| **Deep Learning for Visually Rich Document Content Understanding: A Survey** — Y. Ding et al., 2024. [OpenReview](https://openreview.net/attachment?id=eqU9O7Fxew&name=pdf) | VRDU frameworks: KIE, VQA, entity linking. LayoutLMv2 as first pretrained model integrating text + layout + vision. |
| **Deep Learning for IE from Visually Rich Documents** — IJDAR 28, 121–142, 2025. [Springer](https://link.springer.com/article/10.1007/s10032-024-00493-8) | Survey on IE from VRDs: text recognition, layout analysis, information fusion. Datasets: CORD (receipts), ICDAR. |
| **Document Intelligence in the Era of LLMs: A Survey** — arXiv:2510.13366, 2025. [arXiv](https://arxiv.org/abs/2510.13366v1) | Evolution from encoder-decoder to decoder-only LLMs for DAI. Multimodal, multilingual, retrieval-augmented DAI. Suggests agent-based approaches and document-specific foundation models. |

## Production OCR Architecture

| Reference | Relevance |
|---|---|
| **Operationalizing Document AI: Microservice Architecture for OCR and LLM Pipelines** — arXiv:2605.18818, 2026. [HTML](https://arxiv.org/html/2605.18818) | Production patterns: hybrid classification, GPU inference / CPU orchestration separation, async processing for I/O-bound ops, independent horizontal scaling. **Key finding**: OCR dominates end-to-end latency (2/3 of total), not LLM parsing — same pattern as Exist where PaddleOCR is the bottleneck. System saturates at GPU capacity not worker count. |
| **FastAPI + OCR: BackgroundTasks vs Celery** — DEV Community, 2026. [Link](https://dev.to/chiefmojo79/fastapi-ocr-pipeline-should-you-use-backgroundtasks-or-celery-a-complete-guide-2aec) | CPU-bound OCR blocks async. BackgroundTasks (zero infra, no persistence) vs Celery (persistent queues, retries, scaling). Exist's background job + batch modes follow this trade-off. |
| **Tesseract + Redis in Production: OCR Throughput Up 3×** — Markaicode, 2026. [Link](https://markaicode.com/integrate/tesseract-with-redis/) | Job queue pattern: RQ workers, result caching by document hash, rate limiting. 18 pages/min (queued) vs 5 pages/min (sync) — 3.6× improvement. Cache hits: <5ms vs 3.2s. Same async/queue pattern as Exist's background job + batch endpoints. |
| **Gemini OCR Batch with Prefect** — AnsonDev42, 2025. [GitHub](https://github.com/AnsonDev42/gemini-ocr-batch) | Large-scale batch OCR: SQLite-backed state store, resumable processing, partial failure handling, dead-letter queues. "Wave execution" for page-dependency. Same batch coordination concerns as Exist's `/ocr/parse/batch` endpoint. |

## Standard Benchmarks & Datasets

| Reference | Relevance |
|---|---|
| **OmniDocBench** — L. Ouyang et al., CVPR 2025. | Multi-scenario document parsing benchmark. Used to evaluate PP-StructureV3 (SOTA Chinese/English parsing) and PP-ChatOCRv4. |
| **ICDAR Competitions** — Intl. Conference on Document Analysis and Recognition. | Annual benchmarks for text detection, recognition, layout analysis, table recognition. De facto standard evaluation protocols. |
| **CORD (Consolidated Receipt Dataset)** — S. Park et al., NeurIPS Workshop 2019. | Post-OCR parsing benchmark for receipt information extraction. 1,000+ receipt images with key-value annotations. |

## Domain-Specific OCR

| Reference | Relevance |
|---|---|
| **PP-ChatOCRv4-doc Pipeline** — PaddleX. [GitHub](https://github.com/PaddlePaddle/PaddleX) | Combines OCR + LLM + MLLM for complex document IE: layout analysis, rare characters, tables, seals. Integrated with ERNIE Bot. Relevant if extending Exist with KIE capabilities. |

## How Studies Relate to Exist

| Aspect | Supporting Studies |
|---|---|
| **Engine choice (PaddleOCR)** | PP-OCRv4 tech report + TildAlice benchmark: fastest init (2.1s), lowest memory (450MB), best batch throughput (220ms/image) |
| **3-service architecture** | arXiv:2605.18818 microservice pattern: separate GPU inference (PaddleOCR) from CPU orchestration (FastAPI) from static serving (nginx) |
| **Async background jobs** | Markaicode Tesseract+Redis, FastAPI+OCR guide: queue pattern improves throughput 3.6× vs sync, retry semantics, crash recovery |
| **Batch processing** | AnsonDev42 Gemini batch: SQLite state, partial failures, resume capability — same concerns as Exist's `/ocr/parse/batch` |
| **Document conversion (Gotenberg)** | Carbone benchmark: 432ms avg latency, 11.52 RPS. Gotenberg is single-threaded — limitation to document throughput |
| **3 output formats (JSON/MD/XML)** | arXiv:2410.21169 survey: structured output as goal of document parsing pipeline |
| **URL/HTML input support** | Gotenberg Chromium rendering: modern CSS/JS execution, wait strategies for SPAs |
