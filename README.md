# ResearchFlow

ResearchFlow is a web-based AI-assisted research information management system.

The system supports academic paper search, paper management, and structured AI-assisted information extraction from paper abstracts.

## Main Features

- Search academic papers using OpenAlex
- View paper metadata and abstracts
- Save papers to a research library
- Manage saved papers
- Generate structured AI summaries from paper abstracts
- Extract:
  - Research Problem
  - Methodology
  - Key Findings
  - Limitations

## Technology Stack

### Frontend

- React

### Backend

- Python
- FastAPI

### Database

- SQLite

### External Services

- OpenAlex API
- OpenRouter API

## Project Structure

```text
researchflow/
├── docs/
│   ├── architecture.md
│   ├── data-model.md
│   └── api-contract.md
├── experiments/
│   ├── openalex_test.py
│   └── llm_test.py
├── .gitignore
└── README.md
```

## Current Status

Phase 1 initial design and feasibility testing.

Completed:

- OpenAlex API feasibility test
- LLM API feasibility test
- Initial system architecture
- Initial data model
- Initial frontend/backend API contract

## Planned Workflow

```text
Search
  ↓
Retrieve
  ↓
Save
  ↓
Organise
  ↓
Generate AI Summary
```

## Notes

The current prototype focuses on metadata and abstracts.
