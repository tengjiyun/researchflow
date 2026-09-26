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

The document workflow now uses a SQLite-backed queue and one local worker. Each document runs in a separate process with a 90-second limit. Run one backend process per database. File locks prevent competing workers. Queued work resumes after a restart; interrupted active work is marked failed for an explicit retry.

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

The detector compares common English headings after normalising spacing and compatibility characters. It keeps source text unchanged. A short numbered title with blank-line boundaries can start an `unknown` section even when its name is not recognised. The following blank line is optional when the two preceding accepted headings and the new title form a consecutive top-level numbering sequence. The original title is retained. This conservative fallback excludes reference sections and rejects common sentence and numeric table patterns. It does not infer sections from fonts or visual layout. Wrapped or unnumbered titles may be missed, and isolated list labels may be mistaken for headings. Every chunk belongs to a section, including unknown sections.

### Text Splitter

The text splitter divides long sections into smaller chunks. Each chunk keeps its paper, section, page range, sequence number, and source text.

The system does not send the whole paper in one analysis request. Smaller chunks make source limits easier to manage and keep evidence locations clear.

The current splitter stores chunks of at most 2,000 characters without overlap. Each chunk stays within one section and page. Offsets point into separately stored, unchanged page text.

### Structured Analysis Client

The analysis client, analysis worker, and evidence validator are implemented. The related API and storage contracts are in `api-contract.md` and `data-model.md`. Live model output quality remains an evaluation task.

The client sends stored chunks to OpenRouter and requests four finding types: `research_problem`, `methodology`, `key_finding`, and `limitation`. It uses `OPENROUTER_API_KEY` and an explicitly configured `OPENROUTER_MODEL`. There is no default paid model and no automatic model fallback. Missing configuration prevents a run from being queued.

For `full-text-v1`, all stored chunks enter ordered batches, including unknown sections. The client does not replace full text with search metadata or silently omit later pages. References and quoted studies may provide context, but the prompt must not describe their claims as findings of the current paper. Text that the PDF parser cannot extract, including some figures and tables, remains outside the analysis input.

Each batch contains at most 12,000 source characters and keeps whole chunks. A run accepts at most 200,000 source characters and 100 batches. These are application limits, not guarantees about a model's context window. The backend checks them before the first service request. It rejects larger inputs rather than truncating them. A model context error fails the run without reducing its input.

New runs use a 600-second request timeout, a maximum output of 100,000 tokens, and a schema allowing at most 20 candidates. The output budget covers model reasoning and final JSON; reasoning is not disabled. The whole run has a 30-minute timeout across all batches. Responses also have an 8 MiB byte limit. Invalid, oversized, or truncated responses fail the run. The worker makes no automatic repeat requests; users explicitly retry failed runs. Existing runs and their retries retain their saved token and time limits. These limits bound requests and output size, not monetary cost. Check the configured model's context and output limits before use.

The prompt distinguishes current research questions, methods used, reported results, and explicit limitations. It excludes future plans as current research problems and does not infer limitations from future work alone. Findings must name their subject, retain conditions and comparisons, and avoid broadening a component-specific claim to the whole system. An unclear subject or category should lead to omission. Source matching cannot enforce these semantic instructions, so manual evaluation remains necessary.

The response schema contains a `findings` list. Each candidate contains only `finding_type`, `content` of 1 to 2,000 characters, and one to five `evidence` pairs. Each pair contains a positive integer `chunk_id` and a `source_excerpt` of 1 to 2,000 characters. Whitespace-only content or quotations are invalid. The client checks types, allowed fields, length limits, and the four finding types. Paper text is untrusted input, not an instruction to change the task. The model cannot invoke tools, choose source URLs, or supply database commands.

The worker combines validated candidates in batch order without a second free-text summary request. It removes exact duplicates of type, content, and evidence, but does not merge statements based on an assumed similarity. Missing categories receive one `unavailable` record with no replacement statement. This means the run found no validated finding in that category, not that the paper certainly contains none.

### Analysis Worker

The worker uses a persistent SQLite queue within the existing single-process backend. No separate queue server is needed. It claims one analysis at a time in a short transaction, then releases the database connection before external requests. The existing process lock prevents two backend instances from recovering or claiming the same work.

Only parsed documents with stored chunks can enter the queue. One document may have only one pending or processing analysis. Completed runs remain available when a user starts a new run. Each run records its selected model, analysis version, file checksum, ordered chunk IDs, a digest of the ordered chunk IDs and text, and non-secret request settings.

Validated findings remain private until all batches finish. One transaction writes the findings and evidence and marks the run completed. A request, validation, timeout, or storage failure leaves no public partial result. If every candidate fails its evidence check, the run fails with `evidence_missing`. If every valid service response contains an empty list, the run may complete with four unavailable categories.

Queued work survives a restart. Active work interrupted by shutdown or restart becomes failed and needs an explicit retry. Retry reuses the failed run ID and its original model and settings, clears old errors and timestamps, and processes all batches again. It uses the current environment key. Changing models needs a new run. The worker never holds a write transaction while waiting for OpenRouter.

Paper deletion is blocked while a related analysis is pending or processing. A completed document's source pages and chunks must not be replaced while analysis history refers to them. A different PDF version needs another document record.

### Evidence Validator

The validator accepts evidence only from chunks included in the candidate's request batch and belonging to the analysed document. For matching only, it collapses each run of Unicode whitespace to one space and ignores surrounding quotation whitespace. Every other character must remain unchanged. Each normalised source character maps back to its original character span. The match must be unique within the referenced chunk, including overlapping matches; an exact spelling does not take priority over another whitespace-equivalent occurrence. Paraphrases, punctuation changes, joined hyphenated words, and ligature substitutions are not accepted.

The backend derives the page, section, and zero-based, end-exclusive chunk offsets from stored text. It saves the unchanged source substring at those offsets, not the model's whitespace-adjusted quotation. It ignores no invalid evidence: a candidate with any invalid evidence pair is rejected as a whole. It removes duplicate evidence by chunk ID and source offsets and marks the first remaining pair as primary. Rejected candidates are not stored or exposed in this version. Existing completed results are not rewritten.

Before committing results, the backend checks the document and chunks again. Every supported finding needs at least one valid evidence record. A changed or missing source fails the run. The system keeps the finding and evidence as separate records so users can inspect the connection.

Exact matching establishes a source location, not whether the excerpt logically supports the statement. The interface and evaluation must keep this distinction clear. Manual checks are still needed for unsupported inference, incorrect attribution, missed content, and extraction errors.

### SQLite Database

SQLite stores:

- Paper metadata and open-access source information
- Document retrieval and parsing status
- Sections and text chunks
- Analysis runs and their status
- Structured findings
- Evidence links and source excerpts
- Failure reasons and timestamps

The detailed entities and relationships are defined in `data-model.md`.

### Local File Cache

The local cache stores retrieved PDFs and intermediate parsing results. It also reduces repeated requests to external services.

Cached papers and secret configuration files must not be committed to Git. Cache location, retention, and deletion rules must be set before implementation.

PDFs currently use `backend/data/pdfs/{document_id}.pdf`, with `PDF_CACHE_PATH` available as an override. They remain until the paper is deleted or its document is retried. File cleanup is coordinated with database deletion and recovered on startup after an interruption. The default cache is ignored by Git.

## Full-Text Processing Flow

1. The user searches for a paper.
2. The backend gets paper metadata and available open-access locations from OpenAlex.
3. The user saves the paper and starts full-text processing.
4. The retrieval service downloads the selected PDF.
5. The parser extracts text while keeping page information.
6. The section detector organises the text into sections.
7. The text splitter creates traceable chunks.
8. The user starts analysis, and the analysis client processes all stored chunks in ordered batches.
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

The evidence chain is:

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

Analysis sends extracted open-access paper text to OpenRouter and its selected model provider. Only the required chunk text and source identifiers are sent. Keys, local paths, and raw service error bodies must not appear in API responses, database settings, or logs. Public deployment, user accounts, and access controls remain outside this local MVP.

## Analysis Acceptance Checks

The backend verification covers:

- A parsed multi-page document produces findings whose evidence matches the stored text, page, section, and offsets.
- Every input chunk appears in a request, including the last batch and unknown sections. Input limits fail before any request.
- Foreign-document IDs, IDs outside the current batch, empty quotes, non-whitespace alterations, ambiguous matches, and missing evidence cannot create supported findings.
- Whitespace-only differences map uniquely to unchanged source text and original offsets, including after storage and application restart.
- Missing categories contain no invented content. Rejected candidates are hidden, and an all-rejected run fails.
- Invalid responses, service failures, timeouts, cancellation, and restart never expose partial results. Retry clears failure state and preserves earlier completed runs.
- Duplicate starts are blocked atomically. Active analysis blocks paper deletion; deletion after completion removes related findings and evidence.
- The five analysis routes follow the API contract, and existing search, library, and document behaviour still works.
- Service keys and internal file paths do not appear in public responses or recorded settings.

Use isolated databases and cached files for automated checks. Mock external service responses for repeatable failure cases. Remove only the new temporary test files and data after verification; leave existing tests unchanged. A live model check needs configured credentials and must be reported separately from mocked checks. A small manual paper sample must assess statement accuracy and missing findings before the feature is described as evaluated.

## Future Multi-Paper Comparison

Multi-paper comparison is a later stage. It will use findings and evidence from papers that have already completed single-paper analysis.

The later comparison workflow may select two to five papers, align findings by category, show agreements and differences, and link each comparison result back to the evidence from each paper. This feature must not be added until single-paper analysis is stable and evaluated.
