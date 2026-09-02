# Backend

The backend will use Python, FastAPI, and SQLite. Its route and response shapes come from `../docs/api-contract.md`.

The first implementation slice contains:

```text
GET  /api/papers/search
POST /api/papers
GET  /api/papers
```

PDF processing and full-text analysis start after this slice works with the frontend.

Formal backend tests will be stored in `tests/` and committed. Local feasibility work stays in the ignored root `experiments/` folder.

