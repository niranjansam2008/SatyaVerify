from __future__ import annotations
import pytesseract
import hashlib
import json
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz
import pytesseract
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
import shutil

tesseract_path = shutil.which("tesseract")
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR.parent / "data"
REGULATION_FILE = DATA_DIR / "regulations" / "sample_rules.json"
MAX_FILE_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt"}

app = FastAPI(title="SatyaVerify API", version="0.1.0",
              description="Hackathon MVP for explainable document screening.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://satyaverify-frontend.onrender.com",
],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def load_rules() -> list[dict[str, Any]]:
    try:
        return json.loads(REGULATION_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def extract_text(path: Path, extension: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    if extension == ".txt":
        return path.read_text(encoding="utf-8", errors="replace"), warnings
    if extension == ".pdf":
        text_parts = []
        with fitz.open(path) as doc:
            for page in doc:
                text_parts.append(page.get_text("text"))
        text = "\n".join(text_parts).strip()
        if not text:
            warnings.append("No embedded PDF text found; trying OCR on rendered pages.")
            try:
                with fitz.open(path) as doc:
                    for page in doc:
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                            tmp_path = Path(tmp.name)
                        try:
                            pix.save(tmp_path)
                            text_parts.append(pytesseract.image_to_string(Image.open(tmp_path)))
                        finally:
                            tmp_path.unlink(missing_ok=True)
                text = "\n".join(text_parts).strip()
            except Exception as exc:
                warnings.append(f"PDF OCR unavailable: {type(exc).__name__}. Install Tesseract to enable it.")
        return text, warnings
    try:
        return pytesseract.image_to_string(Image.open(path)), warnings
    except pytesseract.TesseractNotFoundError:
        raise HTTPException(status_code=422, detail="Tesseract is not installed. Install it or upload a text-based PDF/TXT.")
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="The image could not be read.")


def extract_fields(text: str) -> dict[str, str | None]:
    patterns = {
        "name": r"(?im)^\s*(?:applicant\s+)?name\s*[:\-]\s*(.+?)\s*$",
        "date_of_birth": r"(?im)^\s*(?:date of birth|dob)\s*[:\-]\s*(.+?)\s*$",
        "address": r"(?im)^\s*address\s*[:\-]\s*(.+?)\s*$",
        "application_id": r"(?im)^\s*application(?:\s+id| number| no\.?)\s*[:\-]\s*(.+?)\s*$",
        "document_id": r"(?im)^\s*document(?:\s+id| number| no\.?)\s*[:\-]\s*(.+?)\s*$",
        "issue_date": r"(?im)^\s*issue date\s*[:\-]\s*(.+?)\s*$",
    }
    result: dict[str, str | None] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        result[key] = match.group(1).strip() if match else None
    return result


def regulation_matches(text: str) -> list[dict[str, str]]:
    text_lower = text.lower()
    matches = []
    for rule in load_rules():
        hits = [term for term in rule.get("keywords", []) if term.lower() in text_lower]
        if hits:
            matches.append({
                "rule_id": str(rule.get("id", "SAMPLE")),
                "title": str(rule.get("title", "Sample rule")),
                "reference": str(rule.get("reference", "Demo reference")),
                "matched_keywords": ", ".join(hits),
                "note": str(rule.get("note", "")),
            })
    return matches


def score_document(text: str, fields: dict[str, str | None], warnings: list[str],
                   filename: str, file_hash: str, regulation_hits: list[dict[str, str]]) -> dict[str, Any]:
    flags: list[dict[str, str]] = []
    score = 100

    required = ["name", "date_of_birth", "address", "application_id", "document_id"]
    missing = [key for key in required if not fields.get(key)]
    if missing:
        score -= min(35, 7 * len(missing))
        for key in missing:
            flags.append({"severity": "medium", "code": "MISSING_FIELD",
                          "message": f"Could not extract required field: {key.replace('_', ' ')}."})

    if len(text.strip()) < 40:
        score -= 20
        flags.append({"severity": "high", "code": "LOW_TEXT",
                      "message": "Very little readable text was extracted; request a clearer document."})

    # These are only indicators for review, not proof of fraud.
    if re.search(r"(?i)\b(sample|dummy|test document|not valid)\b", text):
        score -= 10
        flags.append({"severity": "low", "code": "DEMO_MARKER",
                      "message": "Document contains a sample/demo marker."})

    if re.search(r"(?i)\b(edited|photoshopped|altered)\b", text):
        score -= 20
        flags.append({"severity": "medium", "code": "ALTERATION_TERMS",
                      "message": "Text mentions editing/alteration; this keyword heuristic is not forensic proof."})

    if warnings:
        flags.append({"severity": "low", "code": "EXTRACTION_WARNING",
                      "message": "Extraction warning: " + " ".join(warnings)})

    for hit in regulation_hits:
        flags.append({"severity": "info", "code": "RULE_KEYWORD_MATCH",
                      "message": f"{hit['title']} ({hit['reference']}) matched: {hit['matched_keywords']}."})

    score = max(0, min(100, score))
    if score >= 85 and not missing:
        decision = "APPROVE"
    elif score >= 55:
        decision = "REVIEW"
    else:
        decision = "REJECT"

    return {
        "trust_score": score,
        "decision": decision,
        "fields": fields,
        "missing_fields": missing,
        "flags": flags,
        "regulation_matches": regulation_hits,
        "file_sha256": file_hash,
        "filename": filename,
        "disclaimer": "Prototype screening only. This score is not proof of authenticity or legal compliance; a qualified officer must review decisions.",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "SatyaVerify API"}


@app.post("/api/verify")
async def verify_documents(files: list[UploadFile] = File(...)) -> dict[str, Any]:
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one document.")
    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Upload up to 5 documents per request.")

    results = []
    aggregate_flags: list[dict[str, str]] = []
    cross_document_checks: list[dict[str, str]] = []
    seen_fields: dict[str, dict[str, str]] = {}
    total_score = 0

    for upload in files:
        filename = Path(upload.filename or "upload.bin").name
        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=415, detail=f"Unsupported file type: {extension or '(no extension)'}")
        content = await upload.read()
        if not content:
            raise HTTPException(status_code=400, detail=f"{filename} is empty.")
        if len(content) > MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail=f"{filename} exceeds 10 MB.")
        file_hash = hashlib.sha256(content).hexdigest()

        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
            temp_path = Path(tmp.name)
            tmp.write(content)
        try:
            text, warnings = extract_text(temp_path, extension)
        finally:
            temp_path.unlink(missing_ok=True)

        fields = extract_fields(text)
        hits = regulation_matches(text)
        result = score_document(text, fields, warnings, filename, file_hash, hits)
        result["extracted_text_preview"] = text[:1200]
        results.append(result)
        total_score += result["trust_score"]
        aggregate_flags.extend([{**flag, "filename": filename} for flag in result["flags"]])

        for key in ("name", "date_of_birth", "address"):
            value = fields.get(key)
            if value:
                normalized = re.sub(r"\s+", " ", value).strip().casefold()
                if key in seen_fields and seen_fields[key]["normalized"] != normalized:
                    cross_document_checks.append({
                        "field": key,
                        "status": "MISMATCH",
                        "message": f"{key.replace('_', ' ').title()} differs between {seen_fields[key]['filename']} and {filename}.",
                    })
                else:
                    seen_fields.setdefault(key, {"normalized": normalized, "filename": filename})

    if cross_document_checks:
        aggregate_flags.extend({"severity": "high", "code": "CROSS_DOCUMENT_MISMATCH",
                                "message": check["message"]} for check in cross_document_checks)

    average = round(total_score / max(1, len(results)))
    if any(check["status"] == "MISMATCH" for check in cross_document_checks):
        overall_decision = "REVIEW"
        average = min(average, 70)
    elif average >= 85 and all(not r["missing_fields"] for r in results):
        overall_decision = "APPROVE"
    elif average >= 55:
        overall_decision = "REVIEW"
    else:
        overall_decision = "REJECT"

    return {
        "request_id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "overall_trust_score": average,
        "overall_decision": overall_decision,
        "documents": results,
        "cross_document_checks": cross_document_checks,
        "flags": aggregate_flags,
        "audit_event": {
            "event": "DOCUMENT_SCREENED",
            "request_id": "generated-per-request",
            "document_count": len(results),
            "note": "Demo-only in-memory response; persistent tamper-evident audit storage is not configured.",
        },
        "disclaimer": "SatyaVerify MVP is a screening aid, not a final legal decision or a guarantee that a document is genuine.",
    }
