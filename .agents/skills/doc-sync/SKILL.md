---
name: doc-sync
description: Keep kb/ documentation in sync with code changes. Maps source changes to affected docs, updates them, and stages for commit. Use when committing code changes or when user asks to update documentation.
---

# Doc Sync

Keep the `kb/` documentation accurate when code changes. Run this before every commit that touches application code.

## Workflow

### 1. Analyze the Diff

Get the staged diff (pre-commit) or latest commit diff (post-commit):

```bash
# Pre-commit: staged changes
git diff --staged --stat

# Post-commit: latest commit
git diff HEAD~1 --stat
```

Read the full diff for changed files to understand what actually changed:

```bash
git diff --staged -- app/routes/ app/config.py docker-compose.yml
```

### 2. Map Changes to Documentation

| Changed Files | Affected Docs | What to Update |
|---|---|---|
| `app/routes/ocr.py`, `app/routes/health.py` | `kb/tech/03-api.md` | New/removed endpoints, changed params, response schema |
| `app/config.py` | `kb/tech/04-configuration.md` | New/removed/changed settings. Add rows to table, update defaults |
| `docker-compose.yml`, `Dockerfile`, `nginx/*`, `docker-entrypoint.sh` | `kb/tech/02-quickstart.md`, `kb/tech/05-deployment.md` | Changed ports, services, volumes, environment variables |
| `app/services/*.py`, `app/schemas/*.py` | `kb/tech/08-structure.md` | New/renamed/removed files. Update directory tree |
| `scripts/*` | `kb/tech/07-scripts.md` | New/removed scripts, changed args |
| `app/main.py` | `kb/tech/08-structure.md` | Lifespan changes, middleware changes |
| Any public API behavior | `kb/user-guide/02-getting-started.md`, `kb/user-guide/03-understanding-results.md` | Changed inputs, outputs, or workflows |
| Any public feature change | `kb/user-guide/01-what-is-this.md`, `kb/user-guide/04-faq.md` | Changed capabilities, new questions |
| `index.html`, `Makefile`, `README.md` | `README.md` | Updated links, changed targets, demo UI changes |
| Any deployment change | `kb/tech/05-deployment.md` | Changed setup steps, ports, volumes, env config |
| Any dependency/library change | `kb/tech/01-overview.md`, `kb/tech/06-prerequisites.md` | Changed system deps, Python version, services |

### 3. Read Existing Docs Before Editing

Always read the full doc before making changes. Maintain the existing tone and structure:

```bash
cat kb/tech/03-api.md
```

### 4. Update Each Affected Doc

Apply targeted edits — do not rewrite entire docs unless the changes are pervasive.

**For API docs (`kb/tech/03-api.md`):**
- Endpoint added → add new section following existing pattern (curl example, response JSON, error codes)
- Endpoint removed → remove section, update "Processing Modes" table in README
- Parameter changed → update query param table, curl examples
- Response changed → update example JSON

**For config docs (`kb/tech/04-configuration.md`):**
- New setting → add row to the appropriate table
- Removed setting → delete row
- Default changed → update default column

**For structure docs (`kb/tech/08-structure.md`):**
- New/renamed file → update directory tree
- Deleted file → remove from tree

**For deployment docs (`kb/tech/05-deployment.md`):**
- Port changes → update port tables
- Volume changes → update volume descriptions
- New setup steps → add steps

### 5. Update the User Guide if Public Behavior Changed

If the change affects what end users see or do, update the corresponding user-guide doc:

| User Doc | When to Update |
|---|---|
| `01-what-is-this.md` | New feature, changed capability, new file types |
| `02-getting-started.md` | Changed API key setup, new endpoints, changed curl examples |
| `03-understanding-results.md` | Changed output format, new fields, removed fields |
| `04-faq.md` | Common questions about new features |

### 6. Stage the Updated Docs

```bash
git add kb/tech/ kb/user-guide/
```

### 7. Verify with Pre-commit

```bash
uv run pre-commit run --all-files
```

## Source-to-Doc Mapping Examples

```
# Config change
app/config.py: new field "ocr_asset_base_url"
→ kb/tech/04-configuration.md: add row to "Output" table

# API route change
app/routes/ocr.py: new endpoint POST /ocr/parse/url/batch
→ kb/tech/03-api.md: add new section following existing URL batch pattern

# Service rename
app/services/batch.py → app/services/async_job.py
→ kb/tech/08-structure.md: update directory tree, remove batch.py, add async_job.py

# Docker change
docker-compose.yml: add nginx service
→ kb/tech/02-quickstart.md: update port table, add nginx entry
→ kb/tech/05-deployment.md: update service descriptions, add nginx port info

# New script
scripts/create_api_key.py
→ kb/tech/07-scripts.md: add row to key management scripts table
```

## Rules

- Read the existing doc before editing — do not overwrite content blindly
- Preserve the doc's existing tone and audience (tech docs = precise, user-guide = plain English)
- Only update sections that are directly affected by the code change
- If no docs are affected by the change, do nothing
- Stage updated docs so they are included in the same commit as the code change
- Run pre-commit after updating to ensure formatting is clean
