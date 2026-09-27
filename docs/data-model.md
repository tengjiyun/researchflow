# Data Model

The MVP stores one paper's full-text analysis at a time. The model keeps paper metadata, document processing, structured findings, and source evidence separate.

## Design Rules

Implemented tables cover Paper, Document, DocumentPage, Section, Chunk, AnalysisRun, Finding, and Evidence.

- Every supported finding must link to at least one evidence record.
- Every evidence record must link to stored source text.
- Full-text results must stay separate from abstract metadata.
- Retrieval, parsing, and analysis failures must be stored.
- Raw PDF files stay in the local file cache, not in SQLite.
- The model must support later comparison without adding comparison features to the MVP.

## Relationship Overview

```text
Paper
  1
  |
  | many
  v
Document
  |
  +---- many ----> Section
  |                  |
  |                  +---- many ----> Chunk
  |
  +---- many ----> AnalysisRun
                        |
                        +---- many ----> Finding
                                            |
                                            +---- many ----> Evidence
                                                                  |
                                                                  +---- one ----> Chunk
```

A document may have several analysis runs. This allows the system to repeat an analysis after rules or service settings change without overwriting earlier results.

## Paper

Represents an academic paper found through OpenAlex and saved in the research library.

| Field | Type | Rules | Description |
|---|---|---|---|
| id | integer | Primary key | Internal paper ID |
| openalex_id | string | Unique, not null | OpenAlex work ID |
| title | string | Not null | Paper title |
| authors_json | JSON string | Not null | Ordered author names |
| publication_year | integer or null | | Publication year |
| abstract | text or null | | Reconstructed abstract used for discovery only |
| doi | string or null | | DOI |
| venue | string or null | | Journal or conference name |
| citation_count | integer | Default 0 | Citation count from the latest metadata retrieval |
| landing_page_url | string or null | | Main paper page |
| created_at | datetime | Not null | Record creation time |
| updated_at | datetime | Not null | Last metadata update time |

The abstract is not accepted as evidence for a full-text finding.

## Document

Represents one retrieved full-text version of a paper.

| Field | Type | Rules | Description |
|---|---|---|---|
| id | integer | Primary key | Internal document ID |
| paper_id | integer | Foreign key, not null | Related paper |
| source_url | string | Not null | Open-access PDF location |
| source_format | string | Must be `pdf` in the MVP | Source format |
| access_type | string | Must be `open_access` in the MVP | Access classification |
| licence | string or null | | Licence supplied by the source, when available |
| local_file_path | string or null | | Path inside the local file cache |
| file_sha256 | string or null | | File checksum used to detect duplicate content |
| file_size_bytes | integer or null | | Retrieved file size |
| page_count | integer or null | | Number of PDF pages after parsing |
| retrieval_status | string | Not null | Retrieval state |
| parsing_status | string | Not null | Parsing state |
| error_code | string or null | | Stable failure code |
| error_message | text or null | | Clear failure reason |
| retrieved_at | datetime or null | | Successful retrieval time |
| parsed_at | datetime or null | | Successful parsing time |
| created_at | datetime | Not null | Record creation time |
| updated_at | datetime | Not null | Last state change time |

A paper may have more than one document because an open-access location or file version may change. Only a successfully parsed document can start full-text analysis.

The current implementation allows one document per `(paper_id, source_url)` pair. Retry reuses the same document ID and downloads that source again. New source URLs may create another document. Failed processing records remain available for inspection.

## DocumentPage

The `document_pages` table stores each extracted page before section splitting. Its composite primary key is `(document_id, page_number)`. `document_id` references Document, `page_number` starts at 1, and `source_text` contains the unchanged extracted page text. Blank pages have an empty string. Deleting a document removes its pages.

## Section

Represents a detected section in a parsed document.

| Field | Type | Rules | Description |
|---|---|---|---|
| id | integer | Primary key | Internal section ID |
| document_id | integer | Foreign key, not null | Related document |
| section_type | string | Not null | Normalised section category |
| original_heading | string or null | | Heading found in the paper |
| sequence_number | integer | Not null | Section order in the document |
| start_page | integer | Not null | First PDF page |
| end_page | integer | Not null | Last PDF page |
| created_at | datetime | Not null | Record creation time |

Suggested `section_type` values are:

```text
abstract
introduction
methodology
results
discussion
limitations
conclusion
references
other
unknown
```

The system keeps the original heading. It uses `unknown` when it cannot identify the section type.

## Chunk

Represents a traceable piece of extracted text used for analysis.

| Field | Type | Rules | Description |
|---|---|---|---|
| id | integer | Primary key | Internal chunk ID |
| document_id | integer | Foreign key, not null | Related document |
| section_id | integer or null | Foreign key | Related section, when known |
| sequence_number | integer | Not null | Chunk order in the document |
| source_text | text | Not null | Extracted source text |
| start_page | integer | Not null | First PDF page |
| end_page | integer | Not null | Last PDF page |
| start_character | integer or null | | Start position in the parsed section or page text |
| end_character | integer or null | | End position in the parsed section or page text |
| created_at | datetime | Not null | Record creation time |

Chunks must keep the original text. Cleaned text may be stored separately later, but it must not replace the source used for evidence.

The current implementation always assigns a section, using `unknown` when needed. Each chunk stays on one page and within one section, with at most 2,000 characters. Character offsets are zero-based and end-exclusive within DocumentPage.source_text. The chunk text must equal that page substring. Section and chunk sequence numbers start at 1. Composite foreign keys keep chunks in the same document as their section and page.

## AnalysisRun

Represents one full-text analysis attempt for a parsed document.

| Field | Type | Rules | Description |
|---|---|---|---|
| id | integer | Primary key | Internal analysis ID |
| document_id | integer | Foreign key, not null | Analysed document |
| status | string | Not null | Analysis state |
| analysis_version | string | Not null | Version of the extraction rules |
| service_name | string | Not null | External analysis service |
| service_model | string | Not null | Selected service model |
| settings_json | JSON string or null | | Non-secret settings needed to repeat the analysis |
| error_code | string or null | | Stable failure code |
| error_message | text or null | | Clear failure reason |
| started_at | datetime or null | | Processing start time |
| completed_at | datetime or null | | Successful finish time |
| created_at | datetime | Not null | Record creation time |

Secret keys must never be stored in `settings_json`.

For `full-text-v1`, `analysis_runs` has a foreign key to Document with cascading deletion. A partial unique index on `document_id` for `pending` and `processing` rows prevents concurrent active runs for the same document. A queue index on `(status, id)` supports oldest-first processing. Status values and `analysis_version = 'full-text-v1'` have database checks.

`settings_json` stores the input file checksum, ordered chunk IDs, a SHA-256 digest of their ordered IDs and text, and the batch, input, output, and timeout limits specified in `architecture.md`. The digest uses UTF-8 JSON pairs of ID and source text, with no extra separator whitespace. It detects stored text changes even when the PDF checksum has not changed. The service name is `OpenRouter`; the model comes from configuration and is fixed for the run. These settings describe an attempt but cannot guarantee identical model output on repetition.

Retry reuses a failed run, keeps its model and settings, clears errors and processing timestamps, and returns it to pending. `created_at` does not change. A completed run cannot be retried or overwritten; another analysis creates another row. `completed_at` is set only on success. Pending work survives restart, while interrupted processing becomes failed.

## Finding

Represents one structured statement from an analysis run.

| Field | Type | Rules | Description |
|---|---|---|---|
| id | integer | Primary key | Internal finding ID |
| analysis_run_id | integer | Foreign key, not null | Related analysis run |
| finding_type | string | Not null | Finding category |
| content | text or null | | Structured statement |
| support_status | string | Not null | Evidence support state |
| sequence_number | integer | Not null | Display order within its category |
| created_at | datetime | Not null | Record creation time |

Allowed `finding_type` values for the MVP are:

```text
research_problem
methodology
key_finding
limitation
```

Allowed `support_status` values are:

```text
supported
unavailable
rejected
```

`supported` means the finding has source evidence that passed the location and exact-text checks. It does not certify that the statement follows from that evidence. `unavailable` means this run found no validated finding for the category; it is not proof that the paper lacks that information. `rejected` is reserved for a candidate that failed the evidence check. The first implementation discards rejected candidates rather than storing their text.

The model does not store one large summary field. A category may contain several findings, and each finding may use different evidence.

The `findings` table cascades from AnalysisRun. `(analysis_run_id, finding_type, sequence_number)` is unique, with sequence numbers starting at 1 within each category. Database checks restrict categories and support states. Supported content must be non-empty; unavailable content must be null. Each category either has supported findings or one unavailable row, never both. Unavailable rows have no evidence.

The backend inserts findings and evidence and marks the run completed in the same transaction. An incomplete or failed run exposes no findings. An all-empty response across every batch can produce four unavailable rows. A run with candidates but no valid candidate fails with `evidence_missing` instead.

## Evidence

Links a finding to an exact source excerpt.

| Field | Type | Rules | Description |
|---|---|---|---|
| id | integer | Primary key | Internal evidence ID |
| finding_id | integer | Foreign key, not null | Supported finding |
| chunk_id | integer | Foreign key, not null | Source chunk |
| source_excerpt | text | Not null | Exact supporting text |
| start_page | integer | Not null | First source page |
| end_page | integer | Not null | Last source page |
| start_offset | integer | Not null, at least 0 | Start position inside the chunk |
| end_offset | integer | Not null, greater than start_offset | End-exclusive position inside the chunk |
| is_primary | boolean | Default false | Main evidence shown first |
| created_at | datetime | Not null | Record creation time |

One finding may have several evidence records. One chunk may support several findings.

The stored excerpt must match the related chunk text. An excerpt is not valid evidence if it only repeats the finding without linking to the source.

The `evidence` table cascades from Finding and references Chunk. Each `(finding_id, chunk_id, start_offset, end_offset)` tuple is unique. Page checks require `start_page >= 1` and `end_page = start_page`, matching the current single-page chunk design. `is_primary` is stored as 0 or 1, with at most one primary row per finding enforced by a partial unique index.

Before insertion, the backend verifies that the chunk belongs to both the analysed document and the submitted batch. It locates the model quotation using whitespace-only normalisation and rejects multiple matches. The unique match maps back to original offsets; the stored excerpt is taken from the unchanged chunk, not from the model response. `chunk.source_text[start_offset:end_offset]` must equal `source_excerpt`. Deduplication uses chunk ID and both offsets. No schema migration or rewriting of existing evidence is needed. Page numbers come from the chunk. Section names come from its related section at query time, not from model output. Page-relative evidence positions are `chunk.start_character + start_offset` and `chunk.start_character + end_offset`.

Transaction checks enforce same-document links, excerpt equality, exactly one primary evidence row per supported finding, and the presence of evidence. Foreign keys alone do not enforce all these rules. Existing parsed source text is immutable while analysis history refers to it.

## Processing Status Values

`retrieval_status`, `parsing_status`, and `AnalysisRun.status` use:

```text
pending
processing
completed
failed
```

A failed status must include an `error_code` and an `error_message`. A completed parsing status needs a valid page count and at least one chunk.

## Integrity Rules

- `Paper.openalex_id` is unique.
- Section sequence numbers are unique within one document.
- Chunk sequence numbers are unique within one document.
- Page numbers start at 1.
- A start page cannot be greater than an end page.
- Evidence pages must fall inside the related document page range.
- A supported finding must have at least one evidence record.
- An unavailable finding must not contain invented replacement content.
- Evidence offsets must fall inside the related chunk.
- Timestamps use UTC.
- Foreign key checks must be enabled in SQLite.

Some rules, such as requiring evidence for a supported finding, need transaction checks in the backend because a normal database check cannot count related rows.

## Deletion Rules

Deleting a paper removes its documents, sections, chunks, analysis runs, findings, and evidence in one controlled transaction. The related cached PDF and parsing files must also be removed.

Deletion is blocked while any document for the paper is queued or processing. The implemented cascade covers documents, pages, sections, chunks, analysis runs, findings, and evidence. Cached PDFs are staged before the database transaction commits; a failed transaction restores them. Startup recovers any interrupted file cleanup.

Deletion is also blocked while any related analysis is pending or processing. The check and deletion share a write transaction so a new analysis cannot enter the queue between them. Finding lists and evidence details use read transactions so concurrent deletion cannot produce a supported finding without its evidence.

Deleting one analysis run removes only its findings and evidence. It does not delete the paper, document, sections, or chunks.

## Future Multi-Paper Comparison

The MVP does not need comparison tables. A later stage can add `ComparisonRun` and `ComparisonPaper` records that refer to completed analysis runs.

Because findings and evidence are stored separately for each paper, later comparison can align findings by category and keep every comparison result linked to the original evidence.
