# AGENTS.md
## Tender Resume Matching RAG System

Version: 2.0
Status: MVP implemented, architecture still evolving

## System Philosophy
- Deterministic preprocessing before LLM extraction
- Retrieve before reason
- Store once, reuse across matching queries
- Prefer schema-validated structured output over free-form text
- Document current behavior separately from planned architecture

## Current Product Scope
This repository currently supports:
- uploading one tender PDF
- uploading one or many resume PDFs
- extracting text from PDFs with fallback strategies
- chunking and embedding documents
- storing chunk vectors in local FAISS indexes
- extracting structured tender and resume fields using heuristics plus LLM
- ranking resumes against the uploaded tender
- returning explainable reasoning summaries

## Active Pipeline
Tender upload or resume upload
-> timestamped local file save
-> PDF text extraction
-> chunking
-> embedding generation
-> FAISS vector storage
-> tender or resume structured extraction
-> retrieval-driven matching
-> deterministic scoring
-> LangGraph reasoning summary

## Implemented Agents

### 1. Tender Upload Agent
Responsibility: accept tender PDFs and trigger processing.

Code:
- `app/api/tender_routes.py`
- `app/services/tender_service.py`

API:
- `POST /tenders/upload`

### 2. Resume Upload Agent
Responsibility: accept one or many resume PDFs and trigger processing.

Code:
- `app/api/resume_routes.py`
- `app/services/resume_service.py`

API:
- `POST /resumes/upload`
- `POST /resumes/upload-multiple`

### 3. File Persistence Agent
Responsibility: save uploaded files into local folders using timestamp-prefixed filenames.

Storage paths:
- `uploads/tenders/`
- `uploads/resumes/`

Current behavior:
- no SHA256 deduplication
- no extension or corruption validation layer beyond FastAPI upload handling

### 4. Document Extraction Agent
Responsibility: extract readable text from PDFs with multiple fallbacks.

Code:
- `app/rag/loader.py`

Extraction order:
1. PyMuPDF
2. pdfplumber
3. Docling
4. OCR via PyMuPDF rasterization + Tesseract

Current output:
- plain document text string

Note:
- extraction is not page-aware yet
- page number evidence is not persisted yet

### 5. Cleaning Agent
Responsibility: normalize whitespace.

Code:
- `app/rag/cleaner.py`

Current status:
- very lightweight
- not a full header/footer/page-number cleanup stage

### 6. Chunking Agent
Responsibility: split extracted text into reusable chunks for vector search.

Code:
- `app/rag/chunker.py`

Current settings:
- `chunk_size = 800` words
- `overlap = 150` words

### 7. Embedding Agent
Responsibility: convert chunks and queries into vectors.

Code:
- `app/rag/embeddings.py`

Model:
- `BAAI/bge-small-en`

Vector size:
- `384`

Fallback:
- deterministic SHA256-based hashed embedding if the local transformer model is unavailable

### 8. Vector Storage Agent
Responsibility: persist embeddings and chunk metadata for retrieval.

Code:
- `app/rag/vector_store.py`
- `app/rag/tender_retriever.py`
- `app/rag/resume_retriever.py`

Current storage:
- local FAISS only

Artifacts:
- `vector_store/tender.faiss`
- `vector_store/tender_metadata.pkl`
- `vector_store/resume.faiss`
- `vector_store/resume_metadata.pkl`

Metadata per chunk:
- `filename`
- `text`
- `chunk_id`

### 9. Tender Extraction Agent
Responsibility: turn tender text into structured requirements.

Code:
- `app/extraction/tender_extractor.py`
- `app/llm/tender_llm_extractor.py`
- `app/llm/schemas.py`

Method:
- heuristic extraction first
- LLM extraction second
- merged final schema result

Current structured fields:
- `role`
- `domain`
- `skills_required`
- `preferred_skills`
- `experience_required`
- `qualifications`
- `responsibilities`

### 10. Resume Extraction Agent
Responsibility: turn resume text into structured candidate profiles.

Code:
- `app/extraction/resume_extractor.py`
- `app/llm/resume_llm_extractor.py`
- `app/llm/schemas.py`

Method:
- heuristic extraction first
- LLM extraction second
- merged final schema result

Current structured fields:
- `candidate_name`
- `role`
- `domain`
- `skills`
- `experience_years`
- `qualifications`
- `projects`

### 11. Matching Agent
Responsibility: derive tender requirements, retrieve likely resumes, score candidates, and prepare match results.

Code:
- `app/services/matching_service.py`

API:
- `POST /match/`

Current matching flow:
1. search tender vectors with the user query
2. rebuild tender context from the matched tender filename
3. extract tender requirements
4. generate a better resume search query from extracted tender data
5. search resume vectors
6. rebuild resume context from each matched resume filename
7. extract structured resume profile
8. compute deterministic score and verdict
9. deduplicate by filename
10. pass results through LangGraph reasoning

Current retrieval settings:
- tender `top_k = 5`
- resume `top_k = 10`

### 12. Scoring Agent
Responsibility: rank candidates using deterministic business logic.

Implemented inside:
- `app/services/matching_service.py`

Current scoring logic:
- required skill match contributes up to 70
- preferred skill match contributes up to 10
- role match contributes 10
- domain match contributes 10
- experience match contributes 10
- final score is capped at 100

Verdicts:
- `Highly Suitable`
- `Partially Suitable`
- `Low Suitable`

### 13. Reasoning Agent
Responsibility: generate human-readable explanations and shortlist summary.

Code:
- `app/agents/reasoning_agent.py`
- `app/graph/matching_graph.py`

Current behavior:
- enrich each match with a textual explanation
- summarize top candidate, shortlisted candidates, and low-suitability candidates

## LLM Provider Layer
Code:
- `app/llm/provider.py`

Supported providers:
- Ollama
- Gemini

Behavior:
- provider priority depends on `.env`
- if both providers fail, schema-shaped fallback JSON is returned

## Frontend Surface
Code:
- `tender-ui/src/App.jsx`
- `tender-ui/src/components/TenderUpload.jsx`
- `tender-ui/src/components/ResumeUpload.jsx`
- `tender-ui/src/components/AskAgent.jsx`

Current UI supports:
- tender upload
- single or bulk resume upload
- match query submission
- viewing extracted tender requirements and ranked resumes

## Technology Stack
- Python
- FastAPI
- React + Vite
- PyMuPDF
- pdfplumber
- Docling
- pytesseract
- sentence-transformers
- FAISS
- LangGraph
- Pydantic
- Ollama
- Gemini

## Current Gaps
These items are not fully implemented and should not be treated as active architecture:
- PostgreSQL persistence for documents or structured outputs
- PGVector storage
- SHA256 deduplication
- file validation and corruption checks
- page-level evidence mapping
- semantic block extraction
- full query agent orchestration

Modules that appear present but are currently placeholders or minimally used:
- `app/models/db_models.py`
- `app/database/connection.py`
- `app/agents/query_agent.py`
- `app/agents/resume_agent.py`
- `app/agents/scoring_agent.py`
- `app/agents/tender_agent.py`

## Recommended Next Architecture
This is the optimized direction for this repository, adapted from the current codebase rather than copied blindly:

Upload
-> file validation
-> SHA256 deduplication
-> page-aware extraction
-> cleanup of headers, footers, and page numbers
-> semantic structuring by section
-> chunking
-> embeddings
-> FAISS or PGVector storage
-> structured extraction
-> evidence mapping
-> PostgreSQL JSONB persistence
-> retrieval and reasoning

## Engineering Guardrails
- Keep API routes thin and orchestration in `app/services/`
- Preserve the hybrid extractor fallback order unless there is a measured reason to change it
- If schema fields change, update both extractors and UI renderers together
- Do not claim PostgreSQL or evidence-traceability features are implemented unless they are wired end-to-end
- Prefer deterministic logic for scoring and validation, and reserve LLM calls for structured extraction and reasoning only
