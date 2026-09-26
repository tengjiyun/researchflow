# Backend

The backend uses Python, FastAPI, and SQLite. Route and response shapes come from `../docs/api-contract.md`.

The current implementation contains:

```text
GET  /api/papers/search
POST /api/papers
GET  /api/papers
GET  /api/papers/{paper_id}
DELETE /api/papers/{paper_id}
```

PDF retrieval, parsing, structured full-text analysis, and source evidence queries are available.

Existing tests in `tests/` cover paper search. Local feasibility work stays in the ignored root `experiments/` folder.

## Local Setup

Run these commands from the `backend` folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000`. Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

Run tests with:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Configuration

The frontend origins default to:

```text
http://localhost:5173
http://127.0.0.1:5173
```

Set `FRONTEND_ORIGINS` to a comma-separated list when the frontend uses other origins.

Casual OpenAlex requests can run without a key. Set `OPENALEX_API_KEY` in the local environment when the project needs its own allowance. Never store the key in a source file.

## Paper Search

```text
GET /api/papers/search?q={query}&page={page}
```

The endpoint trims the search text, uses 25 results per page, and returns the shared error shape for invalid parameters or an external search failure.

## Paper Library

The backend creates `data/researchflow.sqlite3` on startup. Saved papers remain available after a restart. SQLite uses Python's standard library, so no database server or extra package is needed.

Set `DATABASE_PATH` to use a different file. Relative paths are resolved from the `backend` directory, regardless of the shell's current directory. Parent folders are created on startup. Database files and their journal files are ignored by Git.

Send a search result to `POST /api/papers` to save it. The response returns the saved metadata, an integer ID, and UTC timestamps. An existing OpenAlex ID returns `409` with `paper_already_saved`; it does not replace the saved record.

`GET /api/papers` returns the library with the newest saved records first. `GET /api/papers/{paper_id}` returns one paper's metadata. `DELETE /api/papers/{paper_id}` removes that record and returns `204` with no body. A missing record returns `404` with `paper_not_found`.

The library reports the latest document's processing state. It returns `null` when no document exists. Paper details include document IDs and their retrieval and parsing states. `latest_analysis_status` reports the newest analysis across the paper's documents, or `null` when no run exists. Earlier completed analyses remain available.

Deleting a paper removes its documents, stored pages, sections, chunks, analyses, findings, evidence, and cached files. Deletion returns `409` while a document or analysis is queued or processing. Cache files are staged before database deletion and restored if the transaction fails. Interrupted cache cleanup is recovered at startup.

The database enables foreign key checks on each connection. Writes use transactions, and the unique OpenAlex ID prevents concurrent requests from saving duplicates. A database operation that remains blocked after five seconds returns `503` with `database_unavailable`. The client can retry later.

Startup creates the initial table if it is missing. Future table changes need a schema migration; startup does not alter an existing table.

## Full-Text PDFs

```text
GET  /api/papers/{paper_id}/full-text-sources
POST /api/papers/{paper_id}/documents
GET  /api/documents/{document_id}
POST /api/documents/{document_id}/retry
GET  /api/documents/{document_id}/sections
GET  /api/documents/{document_id}/chunks
GET  /api/sections/{section_id}/chunks
```

Save the paper first, then query its full-text sources. The source list contains direct PDF URLs from OpenAlex locations marked as open access. It may be empty. Posting `{"source_url": "..."}` starts retrieval only when the URL is in that paper's current source list.

The start endpoint returns `202` with a document ID. Poll the document endpoint until parsing is `completed` or `failed`. A failure includes an error code and a short reason. A duplicate paper/source pair returns `409`; use the retry endpoint for a failed document. Retry downloads the source again and replaces any partial parsing records.

The database stores the queue. One background worker processes one document at a time in a separate process. Run one backend process per database; multiple application workers are not supported. A file lock prevents a second worker from using the same database. A running child process also holds a job lock. After an abrupt stop, wait up to 90 seconds for that job to exit before restarting. Queued documents resume on startup; interrupted active documents become failed and can be retried.

Downloads have a 25 MiB limit, a 45-second time budget, and at most five redirects. Each destination must resolve only to public addresses. The connection uses the checked address and verifies HTTPS certificates against the original hostname. Local addresses, credentials in URLs, and ports other than 80 or 443 are rejected. The downloaded bytes must begin with the PDF signature. Each complete job has a 90-second process limit.

The parser accepts up to 300 pages and two million extracted characters. It rejects encrypted PDFs and documents with fewer than 100 alphanumeric characters. It does not perform OCR. Blank pages keep their page numbers. A mixed scanned/text document may have pages without extracted text, so inspect the source before treating the extraction as complete.

Sections use common English headings, including numbered headings. Text before a known heading belongs to an `unknown` section. Unusual headings, tables, columns, and formulas may not retain their intended reading order. Review extracted text for each evaluation paper.

Text chunks contain at most 2,000 characters and never cross a page or section boundary. Their character positions are zero-based, end-exclusive offsets into the stored page text. The source text is not rewritten. No chunk overlap is added. Page numbers start at 1.

Cached PDFs use `data/pdfs/{document_id}.pdf`. Set `PDF_CACHE_PATH` to change the cache folder; relative paths use the backend directory. Keep custom caches outside version control. Files remain until their paper is deleted or the document is retried. Temporary downloads use `.part`; interrupted deletion uses `.deleting`. Paths and checksums are internal and are not returned by the API.

Startup adds the document tables and `analysis_runs`, `findings`, and `evidence` without replacing existing paper records or extracted text. A document with analysis history cannot be retried to replace its source. A different PDF version needs a different document record.

## Full-Text Analysis

```text
POST /api/documents/{document_id}/analyses
GET  /api/analyses/{analysis_id}
POST /api/analyses/{analysis_id}/retry
GET  /api/analyses/{analysis_id}/findings
GET  /api/findings/{finding_id}
```

Set `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` in the backend process environment before starting the server. The model must support structured JSON-schema output. No model is selected automatically. The app does not load `.env` files itself. Missing configuration returns `503` with `analysis_not_configured`; search, saving, and PDF processing still work without these settings. Keep keys out of source files, requests from the frontend, and Git.

The client uses OpenRouter's [structured output format](https://openrouter.ai/docs/guides/features/structured-outputs), requests compatible provider routing, and validates the response locally. Unsupported models fail instead of falling back to another model or unstructured text. Extracted paper text is sent to OpenRouter and the selected provider. Each run and explicit retry can incur charges.

After a document finishes parsing, post `{"analysis_version":"full-text-v1"}` to its analysis endpoint. An empty object uses the same version. The response returns `202` and an analysis ID. Poll the status endpoint until it returns `completed` or `failed`, then fetch findings. Only one pending or processing analysis is allowed per document; a duplicate start returns `409`.

Findings use four categories: `research_problem`, `methodology`, `key_finding`, and `limitation`. Use `?finding_type=methodology` to filter the list. A missing category contains an `unavailable` row with null content and no evidence. This means the run found no validated result, not that the paper certainly lacks that information.

Open a finding to inspect its source excerpts, chunk IDs, sections, PDF pages, and character offsets. Offsets are zero-based and end-exclusive within the chunk. Quotes must exactly match stored text; the backend derives locations rather than trusting model-generated page numbers. `supported` confirms a source link, not that the excerpt logically proves the statement. Check the quote and surrounding text yourself.

All extracted chunks enter ordered batches of at most 12,000 characters. A run accepts at most 200,000 source characters and 100 batches. Larger inputs fail before queueing; they are not truncated. Each request has a 60-second timeout and a 4,096-token output limit. The run has a 15-minute timeout. Every response allows up to 20 candidates, each with one to five exact quotes. Context-limit errors, truncated output, invalid responses, and service failures fail the run without publishing partial results. Parsed content missing from figures, tables, or scanned pages cannot be analysed by this text-only workflow.

The SQLite queue has one analysis worker alongside the document worker. Keep one backend process per database. Pending runs survive restart; interrupted active runs become failed. Retry reuses a failed run's ID, original model, settings, and creation time and processes all batches again. Changing models needs a new run. Completed runs are not overwritten. There are no automatic repeat service requests.

The implementation was checked with isolated databases, a previous-schema upgrade, API requests, and simulated provider responses. Live model compatibility, output quality, cost, and latency still need evaluation with configured credentials and a small paper sample. No live model result is implied by these checks.
