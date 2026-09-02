# ResearchFlow

ResearchFlow is a web-based research information management system. It aims to extract and organise evidence from full academic papers while keeping each finding linked to its source.

## Research Question

How effectively can a web-based system extract, organise, and synthesise evidence from full academic papers while keeping the results accurate and traceable?

## MVP Goal

The MVP will process one paper at a time. It will accept a legally accessible, machine-readable open-access PDF, analyse its full text, and return structured findings with supporting evidence.

### In Scope

- Search academic papers using OpenAlex
- View paper metadata and abstracts
- Save and manage papers in a research library
- Process one machine-readable open-access PDF at a time
- Extract text while keeping page and section information
- Identify the research problem, methodology, key findings, and limitations
- Link every finding to a page, section, and source excerpt
- Show clear processing states and failure reasons

### Out of Scope for the MVP

- Scanned PDFs and optical character recognition
- HTML full-text processing
- Access to papers behind a paywall
- Multi-paper comparison and synthesis
- Research gap discovery
- Automatic production of a complete literature review

## Planned Workflow

```text
Search for a paper
  ↓
Find an open-access PDF
  ↓
Save the paper record
  ↓
Retrieve and parse the full text
  ↓
Identify sections and split the text
  ↓
Extract structured findings
  ↓
Link findings to source evidence
  ↓
Review the findings and evidence
```

## MVP Success Criteria

- A suitable PDF can pass through the complete workflow
- The system keeps page and section information during text extraction
- Every finding has at least one supporting source excerpt
- Unsupported information is marked as unavailable
- Retrieval, parsing, and analysis failures are shown clearly
- The first workflow is checked with three to five suitable papers
- The completed MVP is later evaluated with about 10 to 15 papers

## Future Work

Multi-paper comparison will start only after single-paper analysis is stable and evaluated. A later version may let users select two to five analysed papers, compare their research problems, methods, findings, and limitations, and trace each comparison result back to its evidence.

HTML processing and scanned document support may be considered later. They are not part of the first implementation.

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

The project is in Phase 1: scope, design, and feasibility testing.

Completed:

- OpenAlex search and abstract retrieval feasibility test
- OpenRouter structured analysis feasibility test using an abstract
- Initial system architecture
- Initial data model
- Initial frontend and backend API contract

Still needed before implementation:

- Align the architecture with full-text PDF processing
- Update the data model to store documents, sections, text chunks, findings, and evidence
- Update the API contract for retrieval, parsing, analysis status, and evidence access
- Test PDF text extraction, section detection, text splitting, and evidence locations
