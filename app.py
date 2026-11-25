import io, re, zipfile
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import fitz
from docx import Document
import csv

app = FastAPI(title="SmartHire AI", version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Demo extraction only. Production use requires authentication, encrypted storage,
# retention controls, audit logs, malware scanning and a validated parsing service.
records = []

def read_pdf(data: bytes) -> str:
    doc = fitz.open(stream=data, filetype="pdf")
    return "\n".join(page.get_text() for page in doc)

def read_docx(data: bytes) -> str:
    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs) + "\n" + "\n".join(
        " | ".join(c.text for c in row.cells) for table in doc.tables for row in table.rows
    )

def extract_text(name: str, data: bytes) -> str:
    low = name.lower()
    try:
        if low.endswith(".pdf"):
            return read_pdf(data)
        if low.endswith(".docx"):
            return read_docx(data)
        if low.endswith(".txt"):
            return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""
    return ""

def first_match(patterns, text):
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            return m.group(1).strip()
    return ""

def parse_resume(name: str, text: str):
    email = first_match([r'([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})'], text)
    phone = first_match([r'(\+?\d[\d\s().-]{8,}\d)'], text)
    # Extracted values are tentative; never treat missing data as a failed qualification.
    tenth = first_match([
        r'(?:10th|class\s*x|secondary)[^\d]{0,35}(\d{2,3}(?:\.\d+)?)\s*%?',
        r'(\d{2,3}(?:\.\d+)?)\s*%\s*(?:in\s*)?(?:10th|class\s*x)'
    ], text)
    twelfth = first_match([
        r'(?:12th|class\s*xii|higher secondary|intermediate)[^\d]{0,35}(\d{2,3}(?:\.\d+)?)\s*%?',
        r'(\d{2,3}(?:\.\d+)?)\s*%\s*(?:in\s*)?(?:12th|class\s*xii)'
    ], text)
    cgpa = first_match([
        r'(?:cgpa|c\.g\.p\.a\.?|grade point)[^\d]{0,20}(\d(?:\.\d{1,2})?)',
        r'(\d(?:\.\d{1,2})?)\s*(?:cgpa|c\.g\.p\.a\.?)'
    ], text)
    skills_vocab = ["AutoCAD", "SolidWorks", "CATIA", "Creo", "ANSYS", "Excel",
                    "CNC", "3D modelling", "machine design", "manufacturing",
                    "HVAC", "quality control", "CMM", "welding"]
    skills = [s for s in skills_vocab if re.search(re.escape(s), text, re.I)]
    langs_vocab = ["Hindi", "English"]
    languages = [s for s in langs_vocab if re.search(r"\b" + s + r"\b", text, re.I)]
    return {
        "filename": name, "email": email, "phone": phone,
        "tenth_percent": tenth, "twelfth_percent": twelfth,
        "graduation_cgpa": cgpa, "skills": ", ".join(skills),
        "languages": ", ".join(languages), "review_status": "Needs human review",
        "notes": "Extracted fields may be incomplete or incorrect; verify against the original resume."
    }

@app.get("/", response_class=HTMLResponse)
def home():
    with open("static/index.html", encoding="utf-8") as f:
        return f.read()

@app.post("/api/upload")
async def upload(files: List[UploadFile] = File(...)):
    added = []
    for f in files:
        name = f.filename or "unnamed"
        data = await f.read()
        if name.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    for item in z.infolist():
                        if item.is_dir() or item.file_size > 8_000_000:
                            continue
                        inner = item.filename
                        if inner.lower().endswith((".pdf", ".docx", ".txt")):
                            raw = z.read(item)
                            txt = extract_text(inner, raw)
                            if txt.strip():
                                rec = parse_resume(inner, txt)
                                records.append(rec); added.append(rec)
            except zipfile.BadZipFile:
                raise HTTPException(400, f"{name} is not a valid ZIP file")
        elif name.lower().endswith((".pdf", ".docx", ".txt")):
            txt = extract_text(name, data)
            if not txt.strip():
                raise HTTPException(422, f"Could not read text from {name}. Scanned PDFs need OCR, which is not included.")
            rec = parse_resume(name, txt)
            records.append(rec); added.append(rec)
        else:
            raise HTTPException(400, f"Unsupported file type: {name}")
    return {"processed": len(added), "candidates": added}

@app.get("/api/candidates")
def candidates():
    return {"candidates": records}

@app.delete("/api/candidates")
def clear_candidates():
    count = len(records)
    records.clear()
    return {"deleted": count}

@app.get("/api/export.csv")
def export_csv():
    out = io.StringIO()
    fields = ["filename", "email", "phone", "tenth_percent", "twelfth_percent",
              "graduation_cgpa", "skills", "languages", "review_status", "notes"]
    writer = csv.DictWriter(out, fieldnames=fields)
    writer.writeheader()
    writer.writerows(records)
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=smarthire_candidates.csv"})

@app.get("/health")
def health():
    return {"status": "ok"}
