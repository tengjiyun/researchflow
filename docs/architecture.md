# System Architecture

ResearchFlow uses a client-server architecture. The MVP processes one full paper at a time and keeps every finding linked to source evidence.

## MVP Boundary

The first implementation accepts legally accessible, machine-readable open-access PDFs. It does not support scanned PDFs, optical character recognition, HTML full text, paywalled access, or multi-paper comparison.

The system must show a clear failure when full text is unavailable or unreadable. It must not use an abstract while presenting the result as full-text analysis.

## Architecture Overview

```text
React Frontend
      |
      | HTTP / REST
      v
FastAPI Backend
      |
      +--> Paper Search Service ------> OpenAlex API
      |
      +--> Full-Text Workflow
      |       |
      |       +--> PDF Retrieval
      |       +--> PDF Parser
      |       +--> Section Detection
      |       +--> Text Splitting
      |       +--> Structured Analysis --> OpenRouter API
      |       +--> Evidence Validation
      |
      +--> SQLite Database
      |
      +--> Local File Cache
```

## Components

### React Frontend

The frontend provides the user interface for paper search, the research library, paper details, processing status, structured findings, and source evidence.

The first interface will focus on one paper at a time. A user must be able to select a finding and inspect its page, section, and source excerpt.

### FastAPI Backend

The backend provides the REST API and coordinates paper retrieval, parsing, analysis, evidence checks, and database operations.

Long-running work must not depend on one HTTP request staying open. The backend records the workflow state so the frontend can request progress updates.

### Paper Search Service

The paper search service uses OpenAlex to retrieve paper metadata, abstracts, and available open-access locations. Search metadata and full-text analysis remain separate. An abstract may help users choose a paper, but it is not accepted as full-text evidence.

### PDF Retrieval Service

The retrieval service accepts a selected open-access PDF location. It downloads the file, records the source location, and checks that the response is a supported PDF.

The service rejects missing, inaccessible, or unsupported sources. It does not bypass access controls.

### PDF Parser

The parser extracts text page by page. It keeps the original page number and text order. It also records parsing errors and basic document information.

A PDF with no useful extractable text is marked as unsupported. Scanned document processing is outside the MVP.

### Section Detector

The section detector groups extracted text into sections such as introduction, methodology, results, discussion, limitations, and conclusion.

Section detection may fail for unusual paper layouts. In this case, the system keeps the page structure and records that the section is unknown. It must not invent a section name.

### Text Splitter

The text splitter divides long sections into smaller chunks. Each chunk keeps its paper, section, page range, sequence number, and source text.

The system does not send the whole paper in one analysis request. Smaller chunks make source limits easier to manage and keep evidence locations clear.

### Structured Analysis Client

The analysis client sends selected chunks to the OpenRouter API. It requests structured findings for the research problem, methodology, key findings, and limitations.

Missing information is recorded as unavailable. The service must not fill missing fields with unsupported assumptions.

### Evidence Validator

The evidence validator checks that every finding has at least one source excerpt. The excerpt must point to a stored chunk, section, and page range.

A finding without source evidence is not presented as a supported result. The system keeps the finding and evidence as separate records so users can inspect the connection.

### SQLite Database

SQLite stores:

- Paper metadata and open-access source information
- Document retrieval and parsing status
- Sections and text chunks
- Analysis runs and their status
- Structured findings
- Evidence links and source excerpts
- Failure reasons and timestamps

The detailed entities and relationships will be defined in `data-model.md`.

### Local File Cache

The local cache stores retrieved PDFs and intermediate parsing results. It also reduces repeated requests to external services.

Cached papers and secret configuration files must not be committed to Git. Cache location, retention, and deletion rules must be set before implementation.

## Full-Text Processing Flow

1. The user searches for a paper.
2. The backend gets paper metadata and available open-access locations from OpenAlex.
3. The user saves the paper and starts full-text processing.
4. The retrieval service downloads the selected PDF.
5. The parser extracts text while keeping page information.
6. The section detector organises the text into sections.
7. The text splitter creates traceable chunks.
8. The analysis client extracts structured findings from relevant chunks.
9. The evidence validator links each supported finding to source excerpts.
10. The frontend displays the findings and lets the user inspect the evidence.

## Processing States

Retrieval, parsing, and analysis use these states:

```text
pending
processing
completed
failed
```

Each failed state stores a clear reason. A failed stage does not silently continue as if the workflow succeeded.

## Failure Handling

| Failure | System Behaviour |
|---|---|
| No open-access PDF is available | Mark full text as unavailable |
| PDF download fails | Record the error and allow a later retry |
| File is not a valid PDF | Reject the file |
| PDF contains no useful extractable text | Mark the document as unsupported |
| Section headings cannot be identified | Keep page-based chunks with an unknown section |
| External analysis request fails | Record the failed analysis and allow a later retry |
| A finding has no source evidence | Do not present it as a supported finding |

## Evidence Traceability

The planned evidence chain is:

```text
Paper
  -> Document
      -> Section
          -> Chunk
              -> Evidence
                  -> Finding
```

Every supported finding must be traceable to stored source text. PDF evidence uses a page number, section when available, and source excerpt.

## Configuration and Access Rules

- Service keys are read from environment variables.
- Secret values are not stored in source files.
- Only legally accessible sources are accepted.
- The system does not bypass paywalls or access controls.
- Cached PDFs and extracted text stay outside version control.

## Future Multi-Paper Comparison

Multi-paper comparison is a later stage. It will use findings and evidence from papers that have already completed single-paper analysis.

The later comparison workflow may select two to five papers, align findings by category, show agreements and differences, and link each comparison result back to the evidence from each paper. This feature must not be added until single-paper analysis is stable and evaluated.
