# API Contract

Base URL:

```text
/api
```

The API uses JSON. Timestamps use UTC in ISO 8601 format. Database IDs are integers.

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
- `page`: optional page number, default `1`

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

## 5. Delete Saved Paper

```http
DELETE /api/papers/{paper_id}
```

Successful response: `204 No Content`

Deleting a paper also removes its documents, sections, chunks, analyses, findings, evidence, and related cache files.

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
  "completed_at": "2026-09-02T01:21:10Z"
}
```

## 14. Retry Failed Analysis

```http
POST /api/analyses/{analysis_id}/retry
```

This endpoint is valid only when the analysis has failed.

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
      "is_primary": true
    }
  ]
}
```

A supported finding must return at least one evidence record. A rejected candidate is not returned by this public endpoint.

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

## Error Codes

| Code | Retryable | Meaning |
|---|---|---|
| `paper_already_saved` | No | OpenAlex paper already exists |
| `full_text_source_not_found` | No | No supported open-access PDF was found |
| `unsupported_source_url` | No | Source URL is not supported |
| `pdf_download_failed` | Yes | PDF retrieval failed |
| `invalid_pdf` | No | Retrieved file is not a valid PDF |
| `pdf_text_unavailable` | No | PDF contains no useful extractable text |
| `pdf_parse_failed` | Yes | PDF parsing failed |
| `analysis_failed` | Yes | External analysis failed |
| `evidence_missing` | No | A candidate finding has no source evidence |
| `invalid_resource_state` | No | Operation is not valid for the current state |

## MVP Access Boundary

The MVP does not include user accounts or public sharing. It accepts only supported open-access PDFs and does not bypass paywalls or access controls.

Multi-paper comparison endpoints are outside this contract. They will be added only after single-paper analysis is stable and evaluated.
