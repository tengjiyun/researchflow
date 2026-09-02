# Data Model

The MVP stores one paper's full-text analysis at a time. The model keeps paper metadata, document processing, structured findings, and source evidence separate.

## Design Rules

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

`supported` means the finding has source evidence. `unavailable` means the paper does not provide enough information. `rejected` means a candidate statement failed the evidence check.

The model does not store one large summary field. A category may contain several findings, and each finding may use different evidence.

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
| start_offset | integer or null | | Start position inside the chunk |
| end_offset | integer or null | | End position inside the chunk |
| is_primary | boolean | Default false | Main evidence shown first |
| created_at | datetime | Not null | Record creation time |

One finding may have several evidence records. One chunk may support several findings.

The stored excerpt must match the related chunk text. An excerpt is not valid evidence if it only repeats the finding without linking to the source.

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

Deleting one analysis run removes only its findings and evidence. It does not delete the paper, document, sections, or chunks.

## Future Multi-Paper Comparison

The MVP does not need comparison tables. A later stage can add `ComparisonRun` and `ComparisonPaper` records that refer to completed analysis runs.

Because findings and evidence are stored separately for each paper, later comparison can align findings by category and keep every comparison result linked to the original evidence.
