# Tender Resume Matching RAG System

FastAPI backend plus React UI for:
- uploading tender PDFs
- uploading one or many resume PDFs
- storing chunk embeddings in FAISS
- extracting structured tender and resume data with Ollama or Gemini
- matching resumes against the latest uploaded tender
- persisting document registry, structured outputs, and evidence maps in SQLAlchemy-backed storage

## Current Status

This project is working as an MVP:
- backend app starts successfully
- resume and tender upload routes are wired
- vector search is working
- Ollama and Gemini extraction are both wired
- `/match/` returns a full response payload

Known limitations:
- local Ollama must be installed, running, and have the model pulled
- Gemini free-tier quota can still return `429 RESOURCE_EXHAUSTED` when used as fallback
- semantic sectioning and evidence mapping are heuristic-first and can still be improved
- runtime artifacts in `uploads/` and `vector_store/` are local-only and should not be committed

## Requirements

- Python 3.11+ or newer
- Node.js 18+ for the UI
- Ollama for local LLM inference
- optional Gemini API key from Google AI Studio for fallback

## Environment Setup

Create a local `.env` from `.env.example` and set your key:

```env
LLM_PROVIDER=ollama
USE_OLLAMA=true
OLLAMA_MODEL=llama3.2
OLLAMA_EXTRACTION_MODEL=phi3
OLLAMA_REASONING_MODEL=mistral
OLLAMA_FALLBACK_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT_SECONDS=90
GEMINI_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_URL=sqlite:///./tender_rag.db
MAX_UPLOAD_FILE_SIZE_MB=25
```

## Ollama Setup

Install Ollama, then pull the model:

```bash
ollama pull qwen3:0.6b
```

Start Ollama if it is not already running:

```bash
ollama serve
```

With the default `.env`, the backend uses:
- `phi3` for JSON extraction
- `mistral` for Q&A reasoning
- `llama3.2` as the Ollama fallback model
- Gemini after Ollama fallback models fail

## Backend Setup

Install dependencies:

```bash
cd /Users/ramjeetsingh/Desktop/AI/tender-rag-system
python3 -m pip install -r requirements.txt
```

Run the backend:

```bash
uvicorn app.main:app --reload
```

Backend URL:

```text
http://127.0.0.1:8000
```

## Frontend Setup

Standalone UI:

```bash
cd /Users/ramjeetsingh/Desktop/AI/tender-ui
npm install
npm run dev
```

Frontend URL:

```text
http://127.0.0.1:5173
```

## Main API Routes

- `GET /`
- `POST /resumes/upload`
- `POST /resumes/upload-multiple`
- `POST /tenders/upload`
- `POST /match/`

## Upgraded Processing Flow

Uploads now follow this path:

1. file validation
2. SHA256 deduplication
3. page-aware PDF extraction
4. text cleaning
5. semantic sectioning
6. chunking with page metadata
7. embeddings + FAISS storage
8. structured extraction
9. evidence mapping
10. document persistence

## Expected Flow

1. Start backend.
2. Start frontend.
3. Upload one tender PDF.
4. Upload one or more resume PDFs.
5. Run match query from UI or call `/match/`.

## Security Note

Do not commit real API keys in `.env`.

If a Gemini key is ever exposed:

1. revoke it in Google AI Studio
2. create a new key
3. update local `.env`

Google AI Studio key page:

```text
https://aistudio.google.com/app/apikey
```
