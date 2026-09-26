# Backend

The backend uses Python, FastAPI, and SQLite. Route and response shapes come from `../docs/api-contract.md`.

The current implementation contains:

```text
GET  /api/papers/search
POST /api/papers
GET  /api/papers
GET  /api/papers/{paper_id}
DELETE /api/papers/{paper_id}
```

PDF retrieval, parsing, structured full-text analysis, and source evidence queries are available.

Existing tests in `tests/` cover paper search. Local feasibility work stays in the ignored root `experiments/` folder.

## Local Setup

Run these commands from the `backend` folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000`. Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

Run tests with:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Configuration

The frontend origins default to:

```text
http://localhost:5173
http://127.0.0.1:5173
```

Set `FRONTEND_ORIGINS` to a comma-separated list when the frontend uses other origins.

Casual OpenAlex requests can run without a key. Set `OPENALEX_API_KEY` in the local environment when the project needs its own allowance. Never store the key in a source file.

## Paper Search

```text
GET /api/papers/search?q={query}&page={page}
```

The endpoint trims the search text, uses 25 results per page, and returns the shared error shape for invalid parameters or an external search failure.

## Paper Library

The backend creates `data/researchflow.sqlite3` on startup. Saved papers remain available after a restart. SQLite uses Python's standard library, so no database server or extra package is needed.

Set `DATABASE_PATH` to use a different file. Relative paths are resolved from the `backend` directory, regardless of the shell's current directory. Parent folders are created on startup. Database files and their journal files are ignored by Git.

Send a search result to `POST /api/papers` to save it. The response returns the saved metadata, an integer ID, and UTC timestamps. An existing OpenAlex ID returns `409` with `paper_already_saved`; it does not replace the saved record.

`GET /api/papers` returns the library with the newest saved records first. `GET /api/papers/{paper_id}` returns one paper's metadata. `DELETE /api/papers/{paper_id}` removes that record and returns `204` with no body. A missing record returns `404` with `paper_not_found`.

The library reports the latest document's processing state. It returns `null` when no document exists. Paper details include document IDs and their retrieval and parsing states. `latest_analysis_status` reports the newest analysis across the paper's documents, or `null` when no run exists. Earlier completed analyses remain available.

Deleting a paper removes its documents, stored pages, sections, chunks, analyses, findings, evidence, and cached files. Deletion returns `409` while a document or analysis is queued or processing. Cache files are staged before database deletion and restored if the transaction fails. Interrupted cache cleanup is recovered at startup.

The database enables foreign key checks on each connection. Writes use transactions, and the unique OpenAlex ID prevents concurrent requests from saving duplicates. A database operation that remains blocked after five seconds returns `503` with `database_unavailable`. The client can retry later.

Startup creates the initial table if it is missing. Future table changes need a schema migration; startup does not alter an existing table.

## Full-Text PDFs

```text
GET  /api/papers/{paper_id}/full-text-sources
POST /api/papers/{paper_id}/documents
GET  /api/documents/{document_id}
POST /api/documents/{document_id}/retry
GET  /api/documents/{document_id}/sections
GET  /api/documents/{document_id}/chunks
GET  /api/sections/{section_id}/chunks
```

Save the paper first, then query its full-text sources. The source list contains direct PDF URLs from OpenAlex locations marked as open access. It may be empty. Posting `{"source_url": "..."}` starts retrieval only when the URL is in that paper's current source list.

The start endpoint returns `202` with a document ID. Poll the document endpoint until parsing is `completed` or `failed`. A failure includes an error code and a short reason. A duplicate paper/source pair returns `409`; use the retry endpoint for a failed document. Retry downloads the source again and replaces any partial parsing records.

The database stores the queue. One background worker processes one document at a time in a separate process. Run one backend process per database; multiple application workers are not supported. A file lock prevents a second worker from using the same database. A running child process also holds a job lock. After an abrupt stop, wait up to 90 seconds for that job to exit before restarting. Queued documents resume on startup; interrupted active documents become failed and can be retried.

Downloads have a 25 MiB limit, a 45-second time budget, and at most five redirects. Each destination must resolve only to public addresses. The connection uses the checked address and verifies HTTPS certificates against the original hostname. Local addresses, credentials in URLs, and ports other than 80 or 443 are rejected. The downloaded bytes must begin with the PDF signature. Each complete job has a 90-second process limit.

The parser accepts up to 300 pages and two million extracted characters. It rejects encrypted PDFs and documents with fewer than 100 alphanumeric characters. It does not perform OCR. Blank pages keep their page numbers. A mixed scanned/text document may have pages without extracted text, so inspect the source before treating the extraction as complete.

Sections use common English headings, including numbered headings. Heading comparison normalises spacing and compatibility characters without changing source text. Short numbered titles separated from body text by blank lines can start an `unknown` section when their names are not recognised. A following blank line is optional when the two preceding accepted headings establish a consecutive top-level numbering sequence. The original heading is retained instead of assigning the text to the previous section. This fallback excludes reference sections and rejects common sentence and numeric table patterns. It can still miss unnumbered or wrapped titles, or mistake an isolated list label for a heading. Uncertain lines remain body text. Review extracted text and section labels for each evaluation paper.

Text chunks contain at most 2,000 characters and never cross a page or section boundary. Their character positions are zero-based, end-exclusive offsets into the stored page text. The source text is not rewritten. No chunk overlap is added. Page numbers start at 1.

Cached PDFs use `data/pdfs/{document_id}.pdf`. Set `PDF_CACHE_PATH` to change the cache folder; relative paths use the backend directory. Keep custom caches outside version control. Files remain until their paper is deleted or the document is retried. Temporary downloads use `.part`; interrupted deletion uses `.deleting`. Paths and checksums are internal and are not returned by the API.

Startup adds the document tables and `analysis_runs`, `findings`, and `evidence` without replacing existing paper records or extracted text. A document with analysis history cannot be retried to replace its source. A different PDF version needs a different document record.

## Full-Text Analysis

```text
POST /api/documents/{document_id}/analyses
GET  /api/documents/{document_id}/analyses
GET  /api/analyses/{analysis_id}
POST /api/analyses/{analysis_id}/retry
GET  /api/analyses/{analysis_id}/findings
GET  /api/findings/{finding_id}
```

Set `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` in the backend process environment before starting the server. The model must support structured JSON-schema output. No model is selected automatically. The app does not load `.env` files itself. Missing configuration returns `503` with `analysis_not_configured`; search, saving, and PDF processing still work without these settings. Keep keys out of source files, requests from the frontend, and Git.

The client uses OpenRouter's [structured output format](https://openrouter.ai/docs/guides/features/structured-outputs), requests compatible provider routing, and validates the response locally. Unsupported models fail instead of falling back to another model or unstructured text. Extracted paper text is sent to OpenRouter and the selected provider. Each run and explicit retry can incur charges.

The provider-facing schema expands local references and omits the 64-bit upper bound on `chunk_id`, which some providers reject. It still requests strict JSON Schema output with required fields, closed objects, and the remaining bounds. Local Pydantic validation continues to enforce every original constraint, including the identifier range from 1 to 9,223,372,036,854,775,807. Evidence must still match a chunk in the current batch and document.

After a document finishes parsing, post `{"analysis_version":"full-text-v1"}` to its analysis endpoint. An empty object uses the same version. The response returns `202` and an analysis ID. Poll the status endpoint until it returns `completed` or `failed`, then fetch findings. Only one pending or processing analysis is allowed per document; a duplicate start returns `409`.

When opening or refreshing a paper, get its document IDs from paper details, then request `GET /api/documents/{document_id}/analyses?page=1&page_size=20`. The response contains `analyses`, `page`, `page_size`, and `has_more`. Records use the same fields as analysis status and are ordered by descending creation ID, including pending, processing, completed, and failed runs. An existing document without history returns an empty list, even before parsing completes; a missing document returns `404`. Reading history needs no analysis service configuration.

Page numbers start at 1 and cannot exceed 2,147,483,647. Page size defaults to 20 and accepts 1 to 100 records. Continue while `has_more` is true. New runs can shift page boundaries; restart at page 1 after creating a run and deduplicate by ID when combining pages. Retrying keeps the run's original ID and position. Use an active run's ID to resume polling, or a completed run's ID to fetch findings. A newer failed run does not hide older completed results.

Findings use four categories: `research_problem`, `methodology`, `key_finding`, and `limitation`. Use `?finding_type=methodology` to filter the list. A missing category contains an `unavailable` row with null content and no evidence. This means the run found no validated result, not that the paper certainly lacks that information.

The prompt defines these categories as the paper's current question or objective, the methods used, reported results, and explicitly stated constraints. Future plans alone are neither a current research problem nor proof of a limitation. Each finding must name its subject and preserve its scope and conditions. If the supplied batch does not identify the subject, the model is instructed to omit the finding. These are model instructions, not a guarantee of semantic accuracy; evidence checks still verify source binding only.

Open a finding to inspect its source excerpts, chunk IDs, sections, PDF pages, and character offsets. Offsets are zero-based and end-exclusive within the chunk. For locating a model quotation, the backend collapses each whitespace run to one space and ignores surrounding whitespace. It requires a unique match in the referenced chunk, then saves the unchanged source substring and its original offsets. Repeated matches, paraphrases, changed punctuation, joined hyphenated words, and changed ligatures are rejected. Stored excerpts still match source text exactly; source text is never rewritten. The backend derives locations rather than trusting model-generated page numbers. `supported` confirms a source link, not that the excerpt logically proves the statement. Check the quote and surrounding text yourself.

All extracted chunks enter ordered batches of at most 12,000 characters. A run accepts at most 200,000 source characters and 100 batches. Larger inputs fail before queueing; they are not truncated. New runs use a 600-second request timeout and a 100,000-token output limit for model reasoning and final JSON. Reasoning is not disabled. The whole run has a 30-minute timeout, not 10 minutes multiplied by the batch count. Responses have an 8 MiB byte limit. Every response still allows at most 20 candidates, each with one to five exact quotes; the larger budget does not request longer findings. Context-limit errors, truncated output, invalid responses, and service failures fail the run without publishing partial results. Parsed content missing from figures, tables, or scanned pages cannot be analysed by this text-only workflow. Existing runs and retries keep their saved token and time limits; create a new run to use the updated budget.

On 26 September 2026, the [selected Dots free endpoint](https://openrouter.ai/api/v1/models/dots-studio/dots-3-note-preview:free/endpoints) listed a 512,000-token context and a 460,800-token maximum completion, above the requested 100,000-token budget. These limits can change. Check the selected model's limits before changing models; a large context window alone does not establish its output limit. Longer allowed responses may increase latency and cost. The backend does not silently lower the budget or switch models when a provider rejects it.

The SQLite queue has one analysis worker alongside the document worker. Keep one backend process per database. Pending runs survive restart; interrupted active runs become failed. Retry reuses a failed run's ID, original model, settings, and creation time and processes all batches again. Changing models needs a new run. Completed runs are not overwritten. There are no automatic repeat service requests.

The implementation was checked with isolated databases, a previous-schema upgrade, API requests, and simulated provider responses. A fresh live run completed the full-paper analysis, evidence storage, and result retrieval after application restart for one paper. Content quality issues remain, and evaluation across a small paper sample is still outstanding. The checks below distinguish successful processing and source binding from semantic accuracy.

### End-to-end verification

1. Start the backend with a separate `DATABASE_PATH` and `PDF_CACHE_PATH` for validation. Configure the analysis key and explicit model in that process, without putting credentials in Git.
2. Search for a machine-readable open-access paper, save it, query its full-text sources, and create a document using one of the returned PDF URLs.
3. Poll document status until parsing completes. Check sections and chunks against the downloaded PDF, including page numbers and character positions.
4. Start an analysis and retrieve its history. Poll its ID until it completes or fails. If it fails, inspect the error before retrying; do not retry service requests automatically.
5. For a completed run, inspect all four finding categories and open supported findings to check their quotes, page locations, and meaning. An exact quote alone does not prove that the conclusion is correct.
6. Restart the backend with the same validation paths. Retrieve paper details, document history, findings, and evidence again. An interrupted processing run should be failed with `analysis_interrupted`; pending work should resume. Keep the observed results for evaluation.

An initial live retrieval check used *Scikit-learn: Machine Learning in Python* (`https://openalex.org/W2101234009`) and its OpenAlex-listed PDF at `https://arxiv.org/pdf/1201.0490`. Search, saving, source lookup, download, and parsing succeeded: 6 pages, 5 sections, and 14 chunks. Every stored chunk matched its page-text offsets. The check used a separate temporary database and cache. At that point, the key and model were not configured; starting analysis correctly returned `503` with `analysis_not_configured`. This retrieval check does not establish extraction quality for other layouts or model accuracy.

A subsequent live check with `dots-studio/dots-3-note-preview:free` accepted the compatible schema but exhausted the 4,096-token output budget on the first batch, including 3,762 reasoning tokens. The response ended with `finish_reason: length`. The backend rejected it as `analysis_invalid_response`, published no findings, and retained the failed run across restart. At that stage, a completed full-paper analysis and semantic quality evaluation were still outstanding.

On 26 September 2026, checks with the 8,192-token budget and 180-second request timeout retained reasoning and received complete responses for both batches. In the diagnostic run, the requests took 73.55 and 70.89 seconds; both returned HTTP 200 and `finish_reason: stop`. The provider reported zero cost for these requests. These observations do not guarantee future availability, latency, or pricing.

The diagnostic run returned 17 candidates with 32 excerpts. Only one excerpt matched its referenced chunk exactly, and no candidate had all its excerpts pass validation. The run therefore failed with `evidence_missing`, published no findings, and retained its failed history across restart. Eighteen excerpts matched after whitespace normalisation in a separate diagnostic comparison, but production validation had not yet changed. Other differences included joined hyphenated words, changed ligatures, and incorrect chunk boundaries. Complete JSON responses alone did not establish valid evidence or correct finding categories.

A subsequent local replay of those saved responses checked the whitespace-only locator without another provider call. Seven of the 17 candidates passed every evidence check and were saved in an isolated database; the remaining candidates were rejected. Stored excerpts matched their original chunk substrings and offsets. History, findings, and evidence remained available through the API after application restart. This replay verifies the binding and storage path for recorded responses, not a new live run or semantic accuracy. Existing completed results are not rewritten.

### Live result before the quality changes

A fresh live run on 26 September 2026 used the same paper and `dots-studio/dots-3-note-preview:free`, with reasoning retained, an 8,192-token output limit, and a 180-second request timeout. The PDF was downloaded and parsed again into 6 pages, 5 sections, and 14 chunks. Both model requests returned HTTP 200 and `finish_reason: stop`; analysis completed in 108.44 seconds without an automatic retry or model fallback.

Of 27 candidates, 7 passed all evidence checks and were saved with 7 evidence records; 20 were rejected. Every saved excerpt matched its original chunk substring, page, and character offsets. Analysis history, findings, and evidence were unchanged after application restart. The provider reported zero cost for this run, which does not guarantee future pricing or availability. The check used a separate temporary database and PDF cache, both removed afterwards; existing project data was not changed.

Review of the saved findings identified three limitations:

- A sentence about future work was classified as `research_problem`.
- A limitation began with 'Its performance' without naming the subject. The surrounding source referred specifically to the k-means implementation, not the whole library.
- Some later technical sections retained an `introduction` label. Page numbers and character offsets were valid, but those section labels were inaccurate.

This run verifies the processing and persistence path for one paper, not content acceptance or reliability across different layouts. The next checks should address category definitions, self-contained findings, and section recognition, then evaluate a small sample of papers. A `supported` result confirms source binding, not that its category or interpretation is correct.

### Quality changes and verification

The prompt now defines the four categories and asks for explicit subjects and supporting context. A subsequent live run on 26 September 2026 used the 100,000-token limit, 600-second request timeout, and 30-minute run timeout. Both requests completed without truncation, taking 142.53 seconds in total for analysis. Five findings passed source checks and were saved with five evidence records. Research problems and limitations had no accepted findings and remained `unavailable`. Retrieval after application restart matched the saved results. This was a fresh service call, not a replay.

The model no longer classified the future-work sentence as a research problem in this sample. Its k-means limitation candidate named the component explicitly, but did not pass the quotation checks, so it was not published. This shows improvement in the targeted wording, not complete coverage or semantic accuracy. The rejection of useful candidates still needs evaluation.

That run used an intermediate detector which found eight sections. It exposed a title without a following blank line. After adding the consecutive-numbering rule, a separate reparse found nine sections and 16 chunks. Sections 2 to 5 kept their original titles under `unknown`. Every new chunk matched its original page-text slice at the recorded offsets. The final parser adjustment passed local regression checks but was not followed by another live model run. No existing document or analysis was rewritten.

Verification passed 28 temporary regression checks and the eight existing backend tests. Temporary tests and data were removed after checking. The PDF library also reported that optional `fontTools` support was missing for some embedded fonts. No dependency was installed as part of this change; text extraction around these fonts still needs review. Further papers are needed to assess category quality, rejected evidence, and heading detection across layouts.
