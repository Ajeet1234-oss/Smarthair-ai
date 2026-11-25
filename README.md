# SmartHire AI — deployable starter

This is a small, runnable web application for resume intake and structured human review.

## Included
- Multiple PDF, DOCX and TXT uploads
- ZIP upload containing PDF, DOCX or TXT resumes
- Basic text extraction and tentative field extraction (email, phone, 10th/12th marks, CGPA, selected skills and Hindi/English mentions)
- Candidate table and CSV export
- Clear current-session records

## Not included / not production-ready
- No login, company tenancy, database, encryption at rest, audit log, malware scanning, OCR for scanned PDFs, verified AI model, online assessments, voice assessment, email sending or live hosting.
- Extracted fields are heuristic and can be wrong. Missing fields are not proof that a candidate lacks a qualification.
- This app does not rank, reject or select applicants. A qualified human reviewer must verify evidence and make decisions.
- Do not upload real applicant data until privacy/security controls, lawful basis, applicant notice, access controls, retention and deletion procedures have been implemented.

## Run locally
Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```
Open http://127.0.0.1:8000

## Deploy
A hosting provider account is required. This project includes a `Procfile` for common Python web hosts. Configure the start command:
`uvicorn app:app --host 0.0.0.0 --port $PORT`

For production, replace in-memory records with a secured database and private object storage; add authentication/authorization, encryption, rate limits, malware scanning, OCR, monitoring, audit logs, retention/deletion workflows and a reviewed privacy notice before processing real resumes.
