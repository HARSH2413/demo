# DocIntel

DocIntel is a robust, performant document ingestion and processing system. It extracts, chunks, embeds, and indexes text from files (PDFs, DOCX, etc.) to enable semantic search and AI-driven workflows.

## Recent Pipeline Enhancements (v1.1)

The system recently received massive resilience and concurrency upgrades (SP1-SP6):
- **Unblocked Event Loops:** Supabase database calls in `FastAPI` endpoints were migrated to Starlette threadpools, drastically reducing latency during high-concurrency uploads.
- **Batched Persistence & Resilience:** Partial batch failures are intelligently caught; successfully embedded chunks are kept, and bounded retries prevent complete document drops.
- **Smart Retries:** Extended `tenacity` retries against Supabase/PostgREST to intelligently differentiate transient errors (429, 50x) from permanent faults (400, 401).
- **Zero Handle Leaks:** Deep `PyMuPDF` context manager integrations guarantee secure memory allocation and file-handle de-allocation, resolving silent resource leaks.

## Local Setup

### Backend (FastAPI)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev
```
