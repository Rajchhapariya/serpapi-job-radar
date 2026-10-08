import io
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from app.main import app

client = TestClient(app)


def build_test_pdf(text_content: str) -> bytes:
    """Helper that creates an in-memory single-page PDF containing given text."""
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, NameObject, DictionaryObject
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    
    lines = text_content.strip().split("\n")
    stream_parts = ["BT /F1 12 Tf 50 720 Td 14 TL"]
    for idx, line in enumerate(lines):
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if idx == 0:
            stream_parts.append(f"({escaped}) Tj")
        else:
            stream_parts.append(f"T* ({escaped}) Tj")
    stream_parts.append("ET")
    
    stream_obj = DecodedStreamObject()
    stream_obj.set_data("\n".join(stream_parts).encode("latin-1", "replace"))
    
    font_dict = DictionaryObject()
    font_dict[NameObject("/Type")] = NameObject("/Font")
    font_dict[NameObject("/Subtype")] = NameObject("/Type1")
    font_dict[NameObject("/BaseFont")] = NameObject("/Helvetica")
    
    fonts = DictionaryObject()
    fonts[NameObject("/F1")] = font_dict
    
    resources = DictionaryObject()
    resources[NameObject("/Font")] = fonts
    page[NameObject("/Resources")] = resources
    page[NameObject("/Contents")] = stream_obj
    
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


# ==================== PRIORITY 1: JOB DETAIL & APPLY METADATA ====================

def test_job_fit_returns_apply_metadata():
    """Validates that POST /api/fit returns apply_link, apply_options, salary, and description_snippet."""
    res = client.post("/api/fit", json={"skills": ["Python", "SQL"], "limit": 10})
    assert res.status_code == 200
    data = res.json()
    assert "jobs" in data
    assert len(data["jobs"]) > 0

    for j in data["jobs"]:
        # Verify backward compatibility (no full description field in top-level payload)
        assert "description" not in j
        # Verify new metadata fields
        assert "apply_link" in j
        assert "apply_options" in j
        assert "salary" in j
        assert "posted_at" in j
        assert "description_snippet" in j
        assert isinstance(j["description_snippet"], str)

        if j["apply_options"] is not None:
            assert isinstance(j["apply_options"], list)
            for opt in j["apply_options"]:
                assert isinstance(opt, dict)
                assert "link" in opt or "title" in opt


# ==================== PRIORITY 2: SALARY BENCHMARK & UPLIFT ====================

def test_salary_benchmark_in_unlock_response():
    """Validates that POST /api/unlock calculates salary benchmark statistics across matched vs unlocked jobs."""
    res = client.post("/api/unlock", json={"skills": ["Python", "SQL"], "threshold": 60})
    assert res.status_code == 200
    data = res.json()
    assert "salary_benchmark" in data
    bench = data["salary_benchmark"]
    assert "disclosed_count" in bench
    assert "matched_min_lpa" in bench
    assert "matched_max_lpa" in bench
    assert "unlocked_max_lpa" in bench
    assert "ceiling_boost_pct" in bench
    assert isinstance(bench["disclosed_count"], int)
    assert bench["disclosed_count"] >= 0


# ==================== PRIORITY 3: STRICT RESUME PDF INGESTION ====================

def test_pdf_upload_valid_resume():
    """Validates ingestion of a legitimate resume PDF with standard sections and technical skills."""
    resume_text = (
        "Jane Doe - Software Engineer\n"
        "Email: jane.doe@example.com\n"
        "EDUCATION: Bachelor of Technology in Information Technology, AKTU\n"
        "EXPERIENCE: 2 years building backend data pipelines at Tech Labs\n"
        "SKILLS: Proficient in Python, SQL, Docker, FastAPI, and Git."
    )
    pdf_bytes = build_test_pdf(resume_text)
    assert pdf_bytes.startswith(b"%PDF-")

    res = client.post(
        "/api/resume/parse-pdf",
        content=pdf_bytes,
        headers={"Content-Type": "application/pdf"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "text" in data
    assert "skills" in data
    assert "page_count" in data
    assert "Python" in data["skills"]
    assert "SQL" in data["skills"]
    assert data["page_count"] >= 1


def test_pdf_upload_reject_non_pdf():
    """Asserts that non-PDF payloads without %PDF- magic bytes return HTTP 422."""
    res = client.post(
        "/api/resume/parse-pdf",
        content=b"This is just a text file, not a PDF document.",
        headers={"Content-Type": "application/pdf"}
    )
    assert res.status_code == 422
    assert "not a valid PDF" in res.json()["detail"]


def test_pdf_upload_reject_blank_or_scanned_pdf():
    """Asserts that PDFs with 0 extractable text (e.g. blank or pure image scan) return HTTP 422."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    blank_bytes = buf.getvalue()

    res = client.post(
        "/api/resume/parse-pdf",
        content=blank_bytes,
        headers={"Content-Type": "application/pdf"}
    )
    assert res.status_code == 422
    assert "no extractable text" in res.json()["detail"]


def test_pdf_upload_reject_non_resume_invoice():
    """Asserts that non-resume PDF documents (such as invoices or bills) return HTTP 422."""
    invoice_text = (
        "INVOICE #INV-2026-9042\n"
        "Billed To: Acme Corporation\n"
        "Date: 2026-10-05\n"
        "Payment Terms: Due Upon Receipt\n"
        "Total Balance: USD $4,250.00\n"
        "Thank you for your business!"
    )
    pdf_bytes = build_test_pdf(invoice_text)

    res = client.post(
        "/api/resume/parse-pdf",
        content=pdf_bytes,
        headers={"Content-Type": "application/pdf"}
    )
    assert res.status_code == 422
    assert "does not match resume structure" in res.json()["detail"]


def test_pdf_upload_reject_oversized():
    """Asserts that payloads exceeding 5MB are rejected with HTTP 413."""
    oversized_bytes = b"%PDF-1.4\n" + (b"0" * (5 * 1024 * 1024 + 100))
    res = client.post(
        "/api/resume/parse-pdf",
        content=oversized_bytes,
        headers={"Content-Type": "application/pdf"}
    )
    assert res.status_code == 413
    assert "exceeds 5MB" in res.json()["detail"]


def test_pdf_upload_reject_empty_payload():
    """Asserts that empty body returns HTTP 422."""
    res = client.post(
        "/api/resume/parse-pdf",
        content=b"",
        headers={"Content-Type": "application/pdf"}
    )
    assert res.status_code == 422
    assert "empty" in res.json()["detail"]
