# API Contract

Base URL:

```text
/api
```

The API uses JSON. Timestamps use UTC in ISO 8601 format. Database IDs are integers.

## Contract Change Rules

This file is the shared contract between the frontend and backend. The first development slice uses sections 1 to 3. Its fixed frontend responses are stored in `mock-data/first-slice.json`.

After frontend work starts, a breaking field or status change needs agreement from both developers. Update this contract and the mock data before changing the applications. FastAPI will provide the machine-readable API schema after backend implementation starts.

## Workflow States

Full-text retrieval, parsing, and analysis use:

```text
pending
processing
completed
failed
```

A long-running operation returns `202 Accepted`. The client then requests the related status endpoint until the operation reaches `completed` or `failed`.

## Error Format

```json
{
  "error": {
    "code": "full_text_source_not_found",
    "message": "No supported open-access PDF is available.",
    "retryable": false
  }
}
```

The API must not expose service keys, local stack traces, or internal file paths.

## 1. Search Papers

```http
GET /api/papers/search?q={query}&page={page}
```

Query parameters:

- `q`: required search text
- `page`: optional positive integer, default `1`

The backend trims `q`. An empty value or a page below `1` returns `422 Unprocessable Content`.

Successful response: `200 OK`

```json
{
  "papers": [
    {
      "openalex_id": "https://openalex.org/W123456789",
      "title": "Example Open-Access Paper",
      "authors": [
        "Author One",
        "Author Two"
      ],
      "publication_year": 2025,
      "abstract": "Example abstract.",
      "doi": "https://doi.org/10.xxxx/example",
      "venue": "Example Journal",
      "citation_count": 120,
      "landing_page_url": "https://doi.org/10.xxxx/example"
    }
  ],
  "page": 1,
  "has_more": false
}
```

The abstract is discovery metadata. It is not full-text evidence.

If the external paper search fails, the API returns `502 Bad Gateway` with the `paper_search_failed` error code.

## 2. Save Paper

```http
POST /api/papers
```

Request:

```json
{
  "openalex_id": "https://openalex.org/W123456789",
  "title": "Example Open-Access Paper",
  "authors": [
    "Author One",
    "Author Two"
  ],
  "publication_year": 2025,
  "abstract": "Example abstract.",
  "doi": "https://doi.org/10.xxxx/example",
  "venue": "Example Journal",
  "citation_count": 120,
  "landing_page_url": "https://doi.org/10.xxxx/example"
}
```

Successful response: `201 Created`

```json
{
  "id": 1,
  "openalex_id": "https://openalex.org/W123456789",
  "title": "Example Open-Access Paper",
  "authors": [
    "Author One",
    "Author Two"
  ],
  "publication_year": 2025,
  "abstract": "Example abstract.",
  "doi": "https://doi.org/10.xxxx/example",
  "venue": "Example Journal",
  "citation_count": 120,
  "landing_page_url": "https://doi.org/10.xxxx/example",
  "created_at": "2026-09-02T01:00:00Z",
  "updated_at": "2026-09-02T01:00:00Z"
}
```

If the OpenAlex ID already exists, the API returns `409 Conflict`.

The backend trims the OpenAlex ID and title. The ID must use the full form `https://openalex.org/W123456789`, and the title must not be blank. Citation counts must be non-negative integers. A publication year may be `null` or an integer from 1 to 9999. Invalid fields return `422` with `invalid_request`.

Saving a duplicate does not change the existing record. Successful saves include UTC creation and update timestamps.

## 3. List Saved Papers

```http
GET /api/papers
```

Successful response: `200 OK`

```json
{
  "papers": [
    {
      "id": 1,
      "openalex_id": "https://openalex.org/W123456789",
      "title": "Example Open-Access Paper",
      "publication_year": 2025,
      "venue": "Example Journal",
      "document_status": "completed",
      "latest_analysis_status": "completed"
    }
  ]
}
```

`document_status` is `null` before document processing starts. `latest_analysis_status` is `null` before an analysis exists. The frontend must not treat either value as an empty string.

The list contains all saved papers, ordered by descending internal ID (newest saved first). An empty library returns `{"papers": []}`. `document_status` follows the newest document: either failed stage means `failed`, completed parsing means `completed`, queued retrieval means `pending`, and other active work means `processing`. Analysis status remains `null` until analysis is implemented.

## 4. Get Saved Paper

```http
GET /api/papers/{paper_id}
```

Successful response: `200 OK`

```json
{
  "id": 1,
  "openalex_id": "https://openalex.org/W123456789",
  "title": "Example Open-Access Paper",
  "authors": [
    "Author One",
    "Author Two"
  ],
  "publication_year": 2025,
  "abstract": "Example abstract.",
  "doi": "https://doi.org/10.xxxx/example",
  "venue": "Example Journal",
  "citation_count": 120,
  "landing_page_url": "https://doi.org/10.xxxx/example",
  "documents": [
    {
      "id": 10,
      "retrieval_status": "completed",
      "parsing_status": "completed"
    }
  ]
}
```

A paper with no documents returns `"documents": []`. A missing paper returns `404` with `paper_not_found`.

## 5. Delete Saved Paper

```http
DELETE /api/papers/{paper_id}
```

Successful response: `204 No Content`

Deleting a paper also removes its documents, sections, chunks, analyses, findings, evidence, and related cache files.

Deletion currently removes paper, document, page, section, and chunk records and their cached files. Analysis records are not implemented yet. A queued or processing document prevents deletion with `409` and `invalid_resource_state` (`retryable: true`). A missing or already deleted paper returns `404` with `paper_not_found`.

Paper IDs for detail and deletion must be positive integers within SQLite's signed 64-bit range. Invalid IDs return `422` with `invalid_request`.

## 6. Find Full-Text Sources

```http
GET /api/papers/{paper_id}/full-text-sources
```

The backend checks OpenAlex locations and returns supported open-access PDFs.

Successful response: `200 OK`

```json
{
  "sources": [
    {
      "source_url": "https://example.org/paper.pdf",
      "source_format": "pdf",
      "access_type": "open_access",
      "licence": "cc-by"
    }
  ]
}
```

An empty `sources` array means no supported source was found.

Only locations with `is_oa: true` and a direct `pdf_url` are returned. URLs are deduplicated. A source lookup failure returns `502` with `full_text_source_lookup_failed`; it is not reported as an empty source list.

## 7. Start Full-Text Retrieval and Parsing

```http
POST /api/papers/{paper_id}/documents
```

Request:

```json
{
  "source_url": "https://example.org/paper.pdf"
}
```

Accepted response: `202 Accepted`

```json
{
  "id": 10,
  "paper_id": 1,
  "source_url": "https://example.org/paper.pdf",
  "source_format": "pdf",
  "access_type": "open_access",
  "retrieval_status": "pending",
  "parsing_status": "pending",
  "error_code": null,
  "error_message": null,
  "created_at": "2026-09-02T01:10:00Z",
  "updated_at": "2026-09-02T01:10:00Z"
}
```

The backend validates the source before retrieval. It rejects unsupported formats and locations that do not use HTTP or HTTPS.

The submitted URL must match a current source returned by OpenAlex for this saved paper. An unlisted URL returns `400` with `full_text_source_not_found`. Local addresses, credentials in URLs, and unsupported ports return `400` with `unsupported_source_url`, or a failed document if discovered during DNS resolution or a redirect.

The same paper/source pair cannot be started twice (`409`). Failed documents use the retry endpoint. The response is a document status object; the worker continues after the request ends. It processes one document at a time.

## 8. Get Document Status

```http
GET /api/documents/{document_id}
```

Successful response: `200 OK`

```json
{
  "id": 10,
  "paper_id": 1,
  "source_url": "https://example.org/paper.pdf",
  "source_format": "pdf",
  "access_type": "open_access",
  "licence": "cc-by",
  "file_size_bytes": 2450000,
  "page_count": 14,
  "retrieval_status": "completed",
  "parsing_status": "completed",
  "error_code": null,
  "error_message": null,
  "retrieved_at": "2026-09-02T01:10:10Z",
  "parsed_at": "2026-09-02T01:10:18Z"
}
```

Local file paths and checksums are internal and are not returned to the client.

The status response also includes `created_at` and `updated_at`. Retrieval failures set both stages to `failed`; parsing failures keep retrieval `completed`. Queued work survives a restart. Interrupted active work returns `processing_interrupted` and needs a retry. Missing documents return `404` with `document_not_found`.

## 9. Retry Failed Document Processing

```http
POST /api/documents/{document_id}/retry
```

This endpoint is valid only when retrieval or parsing has failed.

Accepted response: `202 Accepted`

```json
{
  "id": 10,
  "retrieval_status": "pending",
  "parsing_status": "pending",
  "error_code": null,
  "error_message": null
}
```

If the document is already processing or completed, the API returns `409 Conflict`.

Retry returns the full document status object with both stages set to `pending`. It removes the previous cached download and partial text, then downloads the same source again.

## 10. List Document Sections

```http
GET /api/documents/{document_id}/sections
```

Successful response: `200 OK`

```json
{
  "sections": [
    {
      "id": 20,
      "document_id": 10,
      "section_type": "methodology",
      "original_heading": "Methods",
      "sequence_number": 3,
      "start_page": 4,
      "end_page": 7
    }
  ]
}
```

This endpoint returns `409 Conflict` if document parsing is not complete.

Unknown headings use `section_type: "unknown"`; their text is still stored and queryable. Section numbers follow document order.

## 11. List Section Chunks

```http
GET /api/sections/{section_id}/chunks
```

Successful response: `200 OK`

```json
{
  "chunks": [
    {
      "id": 30,
      "section_id": 20,
      "sequence_number": 5,
      "source_text": "Example source text from the paper.",
      "start_page": 5,
      "end_page": 5
    }
  ]
}
```

The response contains source text because users need to inspect evidence. It must not contain local file paths.

Each chunk also returns `document_id`, `start_character`, and `end_character`. The character offsets are zero-based and end-exclusive within the extracted page text. Chunks contain at most 2,000 characters, do not overlap, and never cross a page boundary, so `start_page` equals `end_page`.

`GET /api/documents/{document_id}/chunks` returns the same `chunks` wrapper for all sections, ordered by document-wide sequence number. It returns `409` before parsing completes. Missing sections return `404` with `section_not_found`.

Sections 12 to 16 describe the implemented analysis endpoints. Starting or retrying analysis needs a configured OpenRouter key and model. Reading existing results does not.

## 12. Start Full-Text Analysis

```http
POST /api/documents/{document_id}/analyses
```

Request:

```json
{
  "analysis_version": "full-text-v1"
}
```

Accepted response: `202 Accepted`

```json
{
  "id": 40,
  "document_id": 10,
  "status": "pending",
  "analysis_version": "full-text-v1",
  "error_code": null,
  "error_message": null,
  "created_at": "2026-09-02T01:20:00Z"
}
```

Analysis can start only after document parsing is complete. Otherwise, the API returns `409 Conflict`.

`analysis_version` defaults to `full-text-v1`; other versions and unknown request fields return `422` with `invalid_request`. A missing document returns `404` with `document_not_found`. A parsed document without chunks returns `409` with `invalid_resource_state`.

Only one pending or processing run is allowed per document. A duplicate start returns `409` with `invalid_resource_state`, without creating another run or making another service request. A new run after completion keeps the previous results. Missing `OPENROUTER_API_KEY` or `OPENROUTER_MODEL` returns `503` with `analysis_not_configured` before queueing.

The backend checks the limits in `architecture.md` before queueing: at most 200,000 source characters and 100 whole-chunk batches, each containing at most 12,000 source characters. Exceeding a limit returns `422` with `analysis_input_limit`; it never queues a truncated input. Accepted work runs in the background. `202` confirms queue acceptance, not successful analysis.

## 13. Get Analysis Status

```http
GET /api/analyses/{analysis_id}
```

Successful response: `200 OK`

```json
{
  "id": 40,
  "document_id": 10,
  "status": "completed",
  "analysis_version": "full-text-v1",
  "service_name": "OpenRouter",
  "service_model": "configured-model",
  "error_code": null,
  "error_message": null,
  "started_at": "2026-09-02T01:20:02Z",
  "completed_at": "2026-09-02T01:21:10Z",
  "created_at": "2026-09-02T01:20:00Z"
}
```

Status responses also include `created_at`. Pending timestamps are null, processing sets `started_at`, and completion sets `completed_at`. Failures set `error_code` and `error_message` and leave `completed_at` null. A missing analysis returns `404` with `analysis_not_found`. Status responses do not expose service keys, local paths, raw provider responses, or internal settings.

The library's `latest_analysis_status` field reports the most recently created analysis across the paper's documents, or null when no run exists. It does not mean that earlier completed results have been replaced.

## 14. Retry Failed Analysis

```http
POST /api/analyses/{analysis_id}/retry
```

This endpoint is valid only when the analysis has failed.

Retry uses the same run ID, original model, settings, and creation time. It clears errors and processing timestamps and processes the full input again. Changing models needs a new run. Missing configuration returns `503`; a missing run returns `404`. A non-failed run or another active run for the document returns `409` with `invalid_resource_state`. Source changes return `409` with `analysis_source_changed` and need a new analysis. Retrying may incur another service charge.

Accepted response: `202 Accepted`

```json
{
  "id": 40,
  "status": "pending",
  "error_code": null,
  "error_message": null
}
```

## 15. List Findings

```http
GET /api/analyses/{analysis_id}/findings?finding_type={type}
```

`finding_type` is optional. Supported values are:

```text
research_problem
methodology
key_finding
limitation
```

Successful response: `200 OK`

```json
{
  "findings": [
    {
      "id": 50,
      "analysis_run_id": 40,
      "finding_type": "methodology",
      "content": "The study used a controlled experiment.",
      "support_status": "supported",
      "sequence_number": 1,
      "evidence_count": 1
    }
  ]
}
```

Only completed analyses expose supported findings. Unavailable categories may return a finding with `content` set to `null` and `support_status` set to `unavailable`.

Pending, processing, or failed runs return `409` with `invalid_resource_state`, not partial results. Missing runs return `404` with `analysis_not_found`. An invalid `finding_type` returns `422` with `invalid_request`.

Every completed run represents all four categories. A category without a validated finding contains exactly one unavailable row with null content and `evidence_count: 0`. Unavailable means no validated result was found, not that the paper certainly lacks that information. Results are ordered by the category order above and then by `sequence_number`. Filtering keeps this order. Rejected candidates are never returned.

## 16. Get Finding and Evidence

```http
GET /api/findings/{finding_id}
```

Successful response: `200 OK`

```json
{
  "id": 50,
  "analysis_run_id": 40,
  "finding_type": "methodology",
  "content": "The study used a controlled experiment.",
  "support_status": "supported",
  "sequence_number": 1,
  "evidence": [
    {
      "id": 60,
      "chunk_id": 30,
      "section_type": "methodology",
      "original_heading": "Methods",
      "source_excerpt": "Participants were assigned to two groups under controlled conditions.",
      "start_page": 5,
      "end_page": 5,
      "start_offset": 0,
      "end_offset": 69,
      "is_primary": true
    }
  ]
}
```

A supported finding must return at least one evidence record. A rejected candidate is not returned by this public endpoint.

Missing or non-public findings return `404` with `finding_not_found`. Unavailable findings return null content and an empty `evidence` list. Evidence is ordered with the primary record first, then by ID.

`start_offset` and `end_offset` are zero-based, end-exclusive character offsets within the stored chunk. The backend derives them, along with the page and section, from the source text. A source excerpt must match that chunk substring exactly. The example assumes the excerpt begins at the start of its chunk. PDF page numbers start at 1; they are not the paper's printed page labels.

The frontend can use the chunk and existing document/section chunk endpoints to show surrounding text. The `supported` label confirms source binding, not semantic correctness. Users must still be able to inspect the quote and judge whether it supports the statement.

## Common HTTP Responses

| Status | Meaning |
|---|---|
| `200 OK` | Request succeeded |
| `201 Created` | A saved record was created |
| `202 Accepted` | Long-running work was accepted |
| `204 No Content` | Deletion succeeded |
| `400 Bad Request` | Request content is invalid |
| `404 Not Found` | Resource does not exist |
| `409 Conflict` | Resource state does not allow the operation |
| `422 Unprocessable Content` | Request fields failed validation |
| `502 Bad Gateway` | An external service failed |
| `503 Service Unavailable` | The paper library is temporarily unavailable |

## Error Codes

| Code | Retryable | Meaning |
|---|---|---|
| `invalid_request` | No | Request parameters failed validation |
| `paper_already_saved` | No | OpenAlex paper already exists |
| `paper_not_found` | No | Saved paper does not exist |
| `database_unavailable` | Yes | A library database operation could not finish; retry later |
| `paper_search_failed` | Yes | External paper search failed |
| `full_text_source_not_found` | No | No supported open-access PDF was found |
| `full_text_source_lookup_failed` | Yes | External source lookup failed |
| `document_not_found` | No | Document does not exist |
| `section_not_found` | No | Section does not exist |
| `unsupported_source_url` | No | Source URL is not supported |
| `pdf_download_failed` | Yes | PDF retrieval failed |
| `invalid_pdf` | No | Retrieved file is not a valid PDF |
| `pdf_text_unavailable` | No | PDF contains no useful extractable text |
| `pdf_parse_failed` | Yes | PDF parsing failed |
| `pdf_too_large` | No | PDF exceeds 25 MiB |
| `pdf_page_limit` | No | PDF has no pages or more than 300 pages |
| `pdf_text_limit` | No | Extracted text exceeds two million characters |
| `pdf_encrypted` | No | Encrypted PDFs are not supported |
| `processing_timeout` | Yes | Processing exceeded 90 seconds |
| `processing_interrupted` | Yes | Processing stopped before it finished |
| `processing_failed` | Yes | The document worker could not finish |
| `cache_cleanup_failed` | Yes | A cached file could not be removed |
| `analysis_failed` | Yes | External analysis failed |
| `analysis_not_configured` | No | A service key or explicit model is missing; configure before retrying |
| `analysis_not_found` | No | Analysis run does not exist |
| `finding_not_found` | No | Finding does not exist or is not public |
| `analysis_input_limit` | No | Full input exceeds the analysis limits |
| `analysis_invalid_response` | Yes | Service output is invalid, truncated, or does not match the schema |
| `analysis_timeout` | Yes | A request exceeded 60 seconds or the run exceeded 15 minutes |
| `analysis_interrupted` | Yes | Active analysis stopped before completion |
| `analysis_source_changed` | No | Stored input no longer matches the run; start a new analysis |
| `evidence_missing` | Yes | Candidates were returned but none passed evidence validation |
| `invalid_resource_state` | No | Operation is not valid for the current state |

The retryability column describes whether another attempt may help, not whether retry is automatic or free. Document and analysis status objects store `error_code` and `error_message`; the shared HTTP error object also includes `retryable`. Deletion blocked by active processing is the retryable exception to `invalid_resource_state`.

Errors encountered after analysis is accepted appear in its status, not as a later HTTP response to the start request. The worker stops at the failed batch, publishes no partial findings, and makes no automatic repeat requests. If some candidates pass evidence checks, rejected candidates are discarded. If all candidates fail those checks, the run fails with `evidence_missing`. Valid empty responses from every batch instead produce four unavailable categories.

## MVP Access Boundary

The MVP does not include user accounts or public sharing. It accepts only supported open-access PDFs and does not bypass paywalls or access controls.

Multi-paper comparison endpoints are outside this contract. They will be added only after single-paper analysis is stable and evaluated.
