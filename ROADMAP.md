# ROADMAP.md
## Tender Resume Matching RAG System Implementation Roadmap

Status: execution plan based on the current repository state as of March 13, 2026

## Purpose
This document converts the high-level PRD into an implementation sequence that fits the code already present in this repository.

The roadmap focuses on four improvements that are worth adopting from the stronger reference architecture:
- SHA256 deduplication and file validation
- page-aware extraction
- evidence mapping and persistence
- semantic section chunking

## Delivery Principles
- preserve the current working MVP while upgrading internals
- keep changes incremental and testable
- prefer backward-compatible interfaces first, then remove legacy paths
- do not document a feature as complete until it is wired end-to-end

## Current Baseline
Already implemented:
- FastAPI upload endpoints
- local file persistence
- hybrid PDF extraction with fallbacks
- chunking and FAISS storage
- structured tender and resume extraction
- deterministic candidate scoring
- LangGraph reasoning summary

Current gaps:
- no validation or deduplication layer
- no page metadata in extraction or chunk storage
- no evidence map persistence
- no semantic section model
- database layer exists mostly as placeholder code

## Recommended Execution Order
1. Harden ingestion with validation and deduplication.
2. Make extraction page-aware without breaking existing matching.
3. Add semantic sections and richer chunk metadata.
4. Persist structured outputs and evidence in PostgreSQL.

## Phase 1: File Validation And SHA256 Deduplication

### Goal
Reject bad uploads early and avoid reprocessing duplicate documents.

### Why first
This reduces wasted storage, repeated FAISS writes, and noisy matching results. It is also low-risk compared with schema or storage rewrites.

### Scope
- validate extension, mime type, and file size
- detect unreadable or empty PDFs before vector storage
- compute SHA256 on upload content
- prevent duplicate processing within each document type
- return clear API responses for duplicates and validation failures

### New or updated files
- `app/services/tender_service.py`
- `app/services/resume_service.py`
- `app/utils/file_storage.py`
- `app/models/db_models.py`
- `app/database/connection.py`
- `README.md`
- new file: `app/utils/file_hash.py`
- new file: `app/utils/file_validator.py`

### Implementation notes
- read upload bytes once, then reuse them for hash, validation, save, and extraction
- keep a temporary filesystem-backed dedup fallback if PostgreSQL is not enabled yet
- return a response shape that distinguishes `stored`, `duplicate`, and `invalid`
- centralize validation rules instead of duplicating them in both services

### Suggested data model
Document registry fields:
- `id`
- `document_type`
- `original_filename`
- `stored_filename`
- `file_hash`
- `file_size`
- `status`
- `created_at`

### Acceptance criteria
- duplicate upload of the same PDF does not create a second vector entry
- non-PDF or oversized upload is rejected before save and embedding
- upload response tells the caller why a file was skipped
- tender and resume services use the same validation and hashing helpers

## Phase 2: Page-Aware Extraction And Evidence Foundation

### Goal
Preserve page boundaries during extraction so future evidence mapping is possible.

### Why second
Evidence mapping, citations, and better chunk metadata all depend on page-aware extraction. This phase unlocks the next two phases.

### Scope
- change extraction output from plain text string to page records
- keep a compatibility helper that can still flatten pages into text
- apply cleaning per page
- store page metadata with chunks
- expose page information to extractors and matching code

### New or updated files
- `app/rag/loader.py`
- `app/rag/cleaner.py`
- `app/rag/chunker.py`
- `app/rag/vector_store.py`
- `app/rag/tender_retriever.py`
- `app/rag/resume_retriever.py`
- `app/services/tender_service.py`
- `app/services/resume_service.py`
- `app/services/matching_service.py`
- new file: `app/models/document_pages.py`

### Implementation notes
- introduce a page record shape like `{page: 1, text: "..."}`
- provide `flatten_pages(pages)` so current extraction logic does not break immediately
- chunk metadata should include at least:
  - `document_id`
  - `filename`
  - `page_start`
  - `page_end`
  - `text`
  - `chunk_id`
- retrieval functions should return page metadata alongside text

### Acceptance criteria
- upload path stores chunk metadata with page references
- current `/match/` flow still works after page-aware extraction lands
- extracted context passed to LLM can be traced back to source pages
- cleaner runs inside the upload pipeline, not as dead code

## Phase 3: Semantic Structuring And Better Chunking

### Goal
Chunk by section meaning, not only by raw word windows.

### Why third
Once page boundaries exist, section detection becomes much more reliable. This directly improves retrieval relevance for tender requirements and resume experience sections.

### Scope
- detect common tender sections such as eligibility, scope, qualifications, responsibilities, financial criteria
- detect common resume sections such as summary, skills, experience, projects, education
- chunk within semantic blocks first, then apply overlap only when needed
- store section labels in metadata
- update query-time retrieval to prefer relevant sections

### New or updated files
- `app/rag/chunker.py`
- `app/rag/vector_store.py`
- `app/services/matching_service.py`
- `app/extraction/tender_extractor.py`
- `app/extraction/resume_extractor.py`
- new file: `app/rag/semantic_structurer.py`
- new file: `app/models/vector_metadata.py`

### Implementation notes
- keep section detection heuristic initially; do not block on LLM sectioning
- for tenders, prioritize sections containing experience, eligibility, qualifications, and scope markers
- for resumes, prioritize skills, project history, and professional experience markers
- chunk metadata should grow to include:
  - `section`
  - `document_type`
  - `page_start`
  - `page_end`

### Acceptance criteria
- tender retrieval can prefer requirement-heavy sections over generic preamble text
- resume retrieval can prefer skills and experience sections over headers and declarations
- vector metadata remains backward-compatible enough to reindex without changing API contracts
- matching quality improves on representative sample documents

## Phase 4: Evidence Mapping And PostgreSQL Persistence

### Goal
Persist structured outputs and attach evidence to every extracted field.

### Why fourth
Evidence mapping is only trustworthy after pages and sections exist. Persistence should happen after the metadata model stabilizes.

### Scope
- persist document registry and structured outputs to PostgreSQL
- add JSONB storage for structured data and evidence maps
- save extraction provenance for tender and resume records
- optionally keep FAISS as local default and add PGVector later as an alternate backend

### New or updated files
- `app/models/db_models.py`
- `app/database/connection.py`
- `app/services/tender_service.py`
- `app/services/resume_service.py`
- `app/services/matching_service.py`
- `app/llm/schemas.py`
- new file: `app/services/document_repository.py`
- new file: `app/services/evidence_service.py`

### Target persistence model
Documents table:
- `id`
- `document_type`
- `document_name`
- `stored_path`
- `file_hash`
- `structured_data`
- `evidence_map`
- `created_at`

Document chunks table:
- `id`
- `document_id`
- `chunk_id`
- `chunk_text`
- `section`
- `page_start`
- `page_end`
- `embedding_backend`

### Evidence map shape
Each extracted field should eventually resolve to:
- `value`
- `source_text`
- `page`
- `section`
- `confidence`

### Implementation notes
- start with persistence for extraction outputs before adding write-heavy analytics tables
- keep evidence mapping deterministic where possible by attaching extracted fields to retrieved supporting snippets
- if exact evidence cannot be found, mark confidence lower instead of fabricating a source

### Acceptance criteria
- tender and resume uploads create durable document records
- structured extraction is saved and reloadable without rerunning the LLM
- at least the main extracted fields have source text and page references
- API responses can include evidence payloads without breaking the current UI

## Cross-Cutting Work

### Testing
- add unit tests for validators, hashing, cleaner, and chunk metadata generation
- add fixture-based tests for page-aware extraction
- add integration tests for upload and duplicate detection
- add matching regression tests using a small fixed tender and resume set

### Migration Strategy
- keep old FAISS metadata readable during transition
- add one reindex script instead of mixing old and new metadata formats forever
- gate PostgreSQL writes behind configuration until stable

### Observability
- log validation failures, duplicate skips, extraction fallback selection, and provider fallback events
- include `document_type`, `document_id`, and `file_hash` in structured logs where available

## Suggested Milestones

### Milestone A
Complete Phase 1 only.

Definition of done:
- uploads are validated
- duplicate files are skipped
- no change to UI contracts required

### Milestone B
Complete Phase 2 and reindex local documents.

Definition of done:
- chunk metadata carries page information
- matching still works
- evidence groundwork is in place

### Milestone C
Complete Phase 3 and tune retrieval quality.

Definition of done:
- sections are detected and stored
- retrieval quality is measurably better on test documents

### Milestone D
Complete Phase 4 with PostgreSQL enabled.

Definition of done:
- extraction outputs and evidence maps persist
- uploaded documents no longer depend only on local FAISS artifacts

## Recommended First Sprint
If you want the highest-value short sprint, do this first:

1. Add `file_validator.py` and `file_hash.py`.
2. Refactor upload services to read bytes once and reuse them.
3. Add a small document registry model in PostgreSQL or a local fallback store.
4. Return duplicate and validation statuses from both upload endpoints.
5. Add tests for duplicate rejection and invalid PDF handling.

This gives immediate quality improvement without destabilizing retrieval.
