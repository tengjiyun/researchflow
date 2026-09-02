# Two-Person Development Workflow

This workflow lets the frontend and backend move at the same time. Both sides use `docs/api-contract.md` as the shared contract.

## Responsibilities

| Area | Main owner | Shared check |
|---|---|---|
| React pages, components, page states, and API client | Frontend developer | Response fields and user flow |
| FastAPI routes, database work, external services, and processing jobs | Backend developer | Request fields and error behaviour |
| API contract, mock data, and integration checks | Both developers | Both developers agree before a breaking change |

Ownership shows who leads the work. It does not stop either developer from reviewing or helping with the other area.

## Repository Layout

```text
researchflow/
├── backend/                 FastAPI application
├── frontend/                React application
├── docs/
│   ├── api-contract.md      Shared API contract
│   ├── development-workflow.md
│   └── mock-data/           Fixed responses for frontend work
└── experiments/             Local feasibility work, ignored by Git
```

Formal tests belong inside `backend/tests/` or the frontend test folders. They must be committed. The ignored `experiments/` folder is only for local feasibility work.

## First Development Slice

The first slice covers paper discovery and saving:

1. Search papers with `GET /api/papers/search`.
2. Save one result with `POST /api/papers`.
3. Show saved papers with `GET /api/papers`.

This slice does not include PDF retrieval, parsing, or full-text analysis. It must work through the frontend and backend before the next slice starts.

The frontend uses `docs/mock-data/first-slice.json` until these three backend endpoints are ready. The backend responses must match the same shapes.

## Contract Rules

- The API contract is the shared source for routes, fields, status codes, and errors.
- A response field cannot change after frontend work starts unless both developers agree.
- Additive changes are allowed when old frontend code can still work.
- For a breaking change, update the contract and mock data before changing either application.
- The frontend must handle documented empty, loading, success, and error states.
- The backend must return documented errors and must not expose local paths or secret values.

FastAPI will provide the machine-readable API schema after the backend starts. Do not maintain a second hand-written full schema because it can drift from the application.

## Frontend Work

- Keep all HTTP calls in one API client area.
- Read the backend base URL from local configuration.
- Use the fixed mock data while the matching endpoint is unfinished.
- Do not copy response conversion logic into page components.
- Treat nullable status fields as `null`, not as an empty string.

## Backend Work

- Implement only the three first-slice endpoints at the start.
- Validate query parameters and request bodies.
- Keep response field names equal to the contract.
- Allow the local frontend origin through backend configuration.
- Add committed endpoint tests before the first slice is merged.

## Git Workflow

The `main` branch must stay runnable. Each developer uses a short branch for one small change.

Example branch names:

```text
backend/paper-search
backend/save-paper
frontend/paper-search
frontend/saved-papers
docs/paper-contract
```

Before a merge:

1. Update the branch from `main`.
2. Run the checks for the changed area.
3. Check the first-slice contract if an API field changed.
4. Ask the other developer to review shared contract changes.
5. Merge the small change before starting a large new branch.

Do not keep one long-running `backend` branch and one long-running `frontend` branch. They will drift and delay integration.

## First Integration Check

The first slice is ready only when:

- The frontend can search through the real backend.
- A user can save one search result.
- The saved paper appears in the library response.
- An empty search result is shown without an error.
- An already saved paper shows the documented conflict message.
- A failed external search shows a retryable error.
- The same behaviour has committed backend tests.

