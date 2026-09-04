# Backend

The backend uses Python and FastAPI. SQLite will be added when paper saving starts. Route and response shapes come from `../docs/api-contract.md`.

The first implementation slice contains:

```text
GET  /api/papers/search
POST /api/papers
GET  /api/papers
```

PDF processing and full-text analysis start after this slice works with the frontend.

Formal backend tests will be stored in `tests/` and committed. Local feasibility work stays in the ignored root `experiments/` folder.

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

## Current Endpoint

```text
GET /api/papers/search?q={query}&page={page}
```

The endpoint trims the search text, uses 25 results per page, and returns the shared error shape for invalid parameters or an external search failure.
