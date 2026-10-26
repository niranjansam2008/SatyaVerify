# SatyaVerify — SIH 2026 MVP Starter

A runnable prototype for the idea in the supplied presentation: upload an application document, extract text with OCR, check required fields and cross-field consistency, run simple tamper heuristics, search a small local regulation knowledge base, and produce an explainable 0–100 trust score with `APPROVE`, `REVIEW`, or `REJECT` recommendations.

> This is a hackathon MVP scaffold, not a legally reliable verification system. It does not authenticate documents against government issuer APIs, prove a signature is valid, or replace a human officer. The sample rules are illustrative and must be replaced with verified, jurisdiction-specific rules.

## Stack

- **Frontend:** React + Vite
- **Backend/API:** Python + FastAPI
- **Document extraction:** PyMuPDF for PDFs, Pillow + pytesseract for scanned/image files (Tesseract must be installed separately)
- **Validation:** Pydantic + deterministic Python rules
- **Regulation search (MVP):** local JSON knowledge base + keyword retrieval; later replace/extend with FAISS or pgvector and an LLM/RAG pipeline
- **Storage:** local temporary upload folder for demo; production should use encrypted object storage + PostgreSQL
- **Security basics:** file size/type checks, temporary files, no external upload, configurable CORS

## Requirements

- Python 3.10+
- Node.js 18+
- (Optional, for image/scanned OCR) Tesseract OCR installed and available on PATH

## Run locally

### 1. Backend

Windows PowerShell:
```powershell
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

If PowerShell blocks activation, use:
```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Backend runs at http://127.0.0.1:8000  
Interactive API docs: http://127.0.0.1:8000/docs

### 2. Frontend (open a second terminal)

```powershell
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite (usually http://localhost:5173).

## Demo flow

1. Open the web app.
2. Upload a PDF, PNG, JPG, JPEG, or TXT file.
3. The backend extracts available text.
4. It checks for fields such as name, date of birth, address, application ID, and document ID.
5. It runs basic duplicate/metadata/tamper heuristics and sample regulation keyword retrieval.
6. It returns a trust score, recommendation, field checklist, flags, and clause references.

## What is implemented vs. future work

### Included in this starter
- Upload API and size/type validation
- PDF text extraction; optional OCR for image/scanned files
- Basic field extraction using regex/labels
- Required-field and cross-document consistency checks for multiple uploads
- Explainable rule-based score and decision
- Keyword search against a sample regulation JSON file
- React dashboard for upload and results
- Audit-style event record in API response

### Still required for a serious deployment
- Verified DigiLocker/API Setu/issuer integrations and consent flows
- Real document authenticity/signature/QR validation
- Trained tamper detection model and evaluated datasets
- Reliable multilingual OCR and form layout model
- Curated legal/regulatory corpus with versioning and expert review
- RAG with source citations, tests against hallucinations, human approval workflow
- Authentication, role-based access, encrypted storage, retention/deletion policy, audit persistence
- PostgreSQL/object storage, background jobs (Celery/Redis), monitoring, deployment hardening
- DPIA/legal review and security testing

## Safe demo guidance

Use synthetic/fake sample documents only. Do not upload Aadhaar, PAN, bank statements, or other real sensitive documents into a student demo. A high score means “few prototype checks failed”, not that a document is genuine.
