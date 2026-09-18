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

PDF retrieval and parsing are available. Structured analysis is the next backend stage.

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

The library reports the latest document's processing state. It returns `null` when no document exists. Paper details include document IDs and their retrieval and parsing states. Analysis status remains `null` because structured analysis is not implemented yet.

Deleting a paper removes its documents, stored pages, sections, chunks, and cached files. Deletion returns `409` while a document is queued or processing. Cache files are staged before database deletion and restored if the transaction fails. Interrupted cache cleanup is recovered at startup.

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

Startup adds `documents`, `document_pages`, `sections`, and `chunks` without replacing existing paper records. Analysis tables are not created at this stage.
