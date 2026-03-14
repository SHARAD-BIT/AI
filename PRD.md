# PRD.md
## Tender Resume Matching RAG System

Version: 1.0
Status: MVP with a defined optimization roadmap

## Vision
Build an AI system that converts tender and resume PDFs into structured, searchable knowledge and produces explainable candidate shortlists for a tender requirement.

## Problem Statement
Tender staffing and compliance teams often review large tender PDFs manually, then compare them against many resumes by hand. This is slow, inconsistent, and difficult to audit. The system should reduce that effort by extracting requirements, retrieving relevant resumes, and ranking candidates with transparent reasoning.

## Primary Users
- tender and bid management teams
- recruitment and resource allocation teams
- operations teams preparing staffing plans for project submissions

## Goals
1. Upload tender PDFs and resume PDFs from a simple UI or API.
2. Extract usable text from mixed-quality PDF documents.
3. Convert documents into vector-searchable chunks.
4. Extract structured requirements from tenders and structured candidate profiles from resumes.
5. Match resumes against the uploaded tender with deterministic scoring and readable reasoning.
6. Keep the system local-first where possible, with controlled LLM usage.

## Non-Goals for the Current MVP
- multi-user auth and roles
- approval workflows
- enterprise-grade audit logs
- fully persistent PostgreSQL-backed document history
- page-level evidence traceability
- general-purpose multi-document chat over all uploaded content

## Current User Flows

### 1. Upload Tender
User selects one tender PDF.

System behavior:
- saves the file to `uploads/tenders/`
- extracts text using hybrid PDF extraction
- chunks the text
- embeds the chunks
- stores tender chunks in FAISS

API:
- `POST /tenders/upload`

### 2. Upload Resumes
User selects one or many resume PDFs.

System behavior:
- saves files to `uploads/resumes/`
- extracts text using the same hybrid PDF extraction path
- chunks the text
- embeds the chunks
- stores resume chunks in FAISS

API:
- `POST /resumes/upload`
- `POST /resumes/upload-multiple`

### 3. Run Matching Query
User enters a query such as `Find best resumes for this tender`.

System behavior:
- searches tender vectors
- reconstructs tender context
- extracts tender requirements
- builds a better resume search query from those requirements
- searches resume vectors
- reconstructs resume context per file
- extracts candidate profiles
- computes scores and verdicts
- runs reasoning summary through LangGraph

API:
- `POST /match/`

## Current Architecture
Upload
-> local file save
-> PDF text extraction
-> chunking
-> embeddings
-> FAISS vector store
-> heuristic + LLM structured extraction
-> resume retrieval
-> deterministic scoring
-> reasoning summary

## Document Processing Requirements

### File Ingestion
Current:
- accepts uploaded PDFs through FastAPI
- stores files locally with timestamp-prefixed names

Missing but recommended:
- extension validation
- file size limit enforcement
- corruption checks before processing
- SHA256 deduplication

### Text Extraction
Current implementation:
- PyMuPDF first
- pdfplumber fallback
- Docling fallback
- OCR fallback using Tesseract

Output today:
- single plain-text document string

Target improvement:
- page-aware extraction to support evidence mapping and citations

### Cleaning
Current implementation:
- whitespace normalization only

Target improvement:
- remove headers
- remove footers
- remove page numbers
- normalize Unicode artifacts

### Chunking
Current implementation:
- `chunk_size = 800`
- `overlap = 150`
- word-based chunking

Target improvement:
- section-aware chunking
- configurable chunk sizes by document type

## Embedding Requirements
Current model:
- `BAAI/bge-small-en`

Dimension:
- `384`

Fallback:
- deterministic hashed embedding when the transformer model is unavailable locally

Requirement:
- embeddings must remain deterministic for the same input within a given environment

## Vector Storage Requirements
Current implementation:
- local FAISS indexes with pickle metadata

Stored metadata today:
- `filename`
- `text`
- `chunk_id`

Target improvement:
- stable `document_id`
- page numbers
- section labels
- source type such as `tender` or `resume`
- optional PGVector for persistent shared deployment

## Structured Extraction Requirements

### Tender Schema
Current extracted fields:
- `role`
- `domain`
- `skills_required`
- `preferred_skills`
- `experience_required`
- `qualifications`
- `responsibilities`

### Resume Schema
Current extracted fields:
- `candidate_name`
- `role`
- `domain`
- `skills`
- `experience_years`
- `qualifications`
- `projects`

Validation:
- Pydantic schemas validate both structured outputs

Extraction strategy:
- heuristics first for determinism and low cost
- LLM second for schema completion and normalization

## Matching and Ranking Requirements
Current ranking logic:
- required skills: up to 70 points
- preferred skills: up to 10 points
- role match: 10 points
- domain match: 10 points
- experience match: 10 points
- final score capped at 100

Current verdicts:
- `Highly Suitable`
- `Partially Suitable`
- `Low Suitable`

Reasoning output:
- per-candidate explanation
- shortlist summary
- low-suitability summary

## LLM Requirements
Supported providers today:
- Ollama
- Gemini

Expected behavior:
- choose provider priority from environment configuration
- keep temperature near zero
- require JSON-shaped outputs for structured extraction
- fall back to schema-default JSON if providers fail

## Frontend Scope
Current UI covers:
- tender upload
- resume upload
- match query submission
- rendering extracted requirements
- rendering ranked resume matches and reasoning

Tech stack:
- React
- Vite
- Axios

## Data Persistence
Current state:
- uploads stored on local filesystem
- vectors stored in local FAISS artifacts
- structured outputs are returned in API responses but not stored in a real database

Target state:
- PostgreSQL for document registry and structured outputs
- JSONB for tender and resume structured data
- evidence maps stored with extracted fields
- optional PGVector for shared retrieval infrastructure

## Evidence and Traceability
Current state:
- not implemented end-to-end

Target requirement:
Each extracted field should eventually store:
- `value`
- `source_text`
- `page`
- `confidence`

This should only be documented as complete after page-aware extraction and persistence are added.

## Success Metrics
- process text-based PDFs with a high success rate
- return meaningful shortlist results after tender and resume upload
- keep most candidate ranking logic deterministic and explainable
- minimize LLM calls to extraction and reasoning stages

## Risks and Constraints
- scanned PDFs may still fail or degrade extraction quality
- local embedding model may be unavailable, forcing lower-quality hash fallback
- Ollama may be offline locally
- Gemini may return quota or rate-limit errors
- current filename-based metadata is weaker than document-id-based persistence
- lack of page evidence makes extraction harder to audit

## Optimization Roadmap
Detailed execution plan:
- see `ROADMAP.md`

### Phase 1: Harden the Current MVP
- add file validation
- add SHA256 deduplication
- add structured logging
- store page metadata during extraction
- wire the cleaner into the ingestion flow

### Phase 2: Improve Retrieval Quality
- introduce semantic sectioning before chunking
- add stable document IDs and richer metadata
- support configurable `top_k`
- support hybrid ranking with vector plus metadata filters

### Phase 3: Add Persistence and Evidence
- persist documents and structured outputs in PostgreSQL
- store evidence maps for every extracted field
- add PGVector as an optional persistent vector backend

### Phase 4: Expand Product Scope
- tender compliance analysis
- shortlist export and reporting
- multi-tender comparison
- richer candidate recommendation workflows

## Final Product Direction
The optimized end-state for this project is:

Upload
-> validation
-> deduplication
-> page-aware extraction
-> cleaning
-> semantic structuring
-> chunking
-> embeddings
-> vector storage
-> structured extraction
-> evidence mapping
-> PostgreSQL persistence
-> retrieval
-> reasoning

That flow is the target architecture. The current repository already implements the core MVP path up to retrieval, structured extraction, scoring, and reasoning, but not the full evidence and persistence stack yet.
