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

PDF processing and full-text analysis start after this slice works with the frontend.

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

Document processing is not implemented yet. Both processing status fields in the library are `null`, and paper details contain an empty `documents` list. Only the `papers` table exists at this stage. Related document tables and cache cleanup must be added with the full-text workflow.

The database enables foreign key checks on each connection. Writes use transactions, and the unique OpenAlex ID prevents concurrent requests from saving duplicates. A database operation that remains blocked after five seconds returns `503` with `database_unavailable`. The client can retry later.

Startup creates the initial table if it is missing. Future table changes need a schema migration; startup does not alter an existing table.
