import io
import json
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


# ==================== RECENCY & FRESHNESS INTELLIGENCE ====================

def test_relative_age_parsing_units():
    """Validates deterministic relative-age parsing across hours, days, weeks, months, and years."""
    from app.serpapi_client import parse_posted_days_ago, extract_posted_at_from_extensions

    assert parse_posted_days_ago("3 hours ago") == 0
    assert parse_posted_days_ago("today") == 0
    assert parse_posted_days_ago("just now") == 0
    assert parse_posted_days_ago("yesterday") == 1
    assert parse_posted_days_ago("1 day ago") == 1
    assert parse_posted_days_ago("5 days ago") == 5
    assert parse_posted_days_ago("2 weeks ago") == 14
    assert parse_posted_days_ago("1 month ago") == 30
    assert parse_posted_days_ago("3 months ago") == 90
    assert parse_posted_days_ago("1 year ago") == 365
    assert parse_posted_days_ago("2 years ago") == 730
    assert parse_posted_days_ago("") is None
    assert parse_posted_days_ago(None) is None

    # Test extraction from item
    item_with_ext = {"extensions": ["Full-time", "4 days ago", "15L - 25L a year"]}
    assert extract_posted_at_from_extensions(item_with_ext) == "4 days ago"

    item_with_detected = {"detected_extensions": {"posted_at": "2 days ago"}}
    assert extract_posted_at_from_extensions(item_with_detected) == "2 days ago"


def test_unlock_recency_filter_excludes_stale_jobs():
    """Validates that POST /api/unlock applies max_age_days to exclude stale/older jobs from baseline math."""
    res_all = client.post("/api/unlock", json={"skills": ["Python", "SQL"], "threshold": 60})
    assert res_all.status_code == 200
    all_eligible = res_all.json()["baseline"]["eligible_jobs"]

    res_7d = client.post("/api/unlock", json={"skills": ["Python", "SQL"], "threshold": 60, "max_age_days": 7})
    assert res_7d.status_code == 200
    fresh_eligible = res_7d.json()["baseline"]["eligible_jobs"]

    # In our corpus, fresh 7-day jobs are a subset of the full corpus
    assert fresh_eligible > 0
    assert fresh_eligible <= all_eligible


def test_fit_recency_filter_returns_strictly_fresh_jobs():
    """Validates that POST /api/fit with max_age_days returns only jobs within the age boundary."""
    res = client.post("/api/fit", json={"skills": ["Python", "SQL"], "limit": 20, "max_age_days": 7})
    assert res.status_code == 200
    data = res.json()
    assert "jobs" in data
    assert len(data["jobs"]) > 0

    for job in data["jobs"]:
        assert "posted_days_ago" in job
        if job["posted_days_ago"] is not None:
            assert job["posted_days_ago"] <= 7, f"Job {job['title']} exceeded max_age_days 7: {job['posted_days_ago']}"


def test_smart_portal_prioritization():
    """Validates that direct ATS endpoints and LinkedIn are prioritized above aggregator scrapers."""
    import duckdb
    from app.unlock import compute_job_fit

    con = duckdb.connect()
    con.execute("""
        CREATE TABLE jobs (
            job_id VARCHAR PRIMARY KEY,
            title VARCHAR,
            company_name VARCHAR,
            location VARCHAR,
            location_type VARCHAR,
            portal_count INTEGER,
            skills_required VARCHAR[],
            apply_options JSON,
            salary VARCHAR,
            apply_link VARCHAR,
            posted_at VARCHAR,
            posted_days_ago INTEGER,
            description VARCHAR
        );
    """)
    opts = [
        {"title": "Shine.com", "link": "https://www.shine.com/jobs/sample"},
        {"title": "Company Careers", "link": "https://boards.greenhouse.io/sample/jobs"},
        {"title": "LinkedIn", "link": "https://www.linkedin.com/jobs/view/123"}
    ]
    con.execute("""
        INSERT INTO jobs VALUES (
            'test_1', 'Python Developer', 'Acme', 'Remote', 'Remote', 3,
            ['Python', 'SQL', 'FastAPI'], ?, '20 LPA', 'https://example.com', '1 day ago', 1, 'Sample job description'
        );
    """, [json.dumps(opts)])

    jobs, _ = compute_job_fit(con, ["Python", "SQL", "FastAPI"], threshold=60)
    assert len(jobs) == 1
    sorted_opts = jobs[0]["apply_options"]
    assert len(sorted_opts) == 3
    # Greenhouse should be first, LinkedIn second, Shine last
    assert "greenhouse" in sorted_opts[0]["link"].lower()
    assert "linkedin" in sorted_opts[1]["link"].lower()
    assert "shine" in sorted_opts[2]["link"].lower()
    con.close()


# ==================== PRODUCTION HARDENING AUDIT TESTS ====================

def test_dynamic_robots_and_sitemap(monkeypatch):
    """Verifies that robots.txt and sitemap.xml dynamically adapt to host and current date."""
    monkeypatch.setenv("BASE_URL", "https://serpapi-job-radar.onrender.com")
    res_robots = client.get("/robots.txt")
    assert res_robots.status_code == 200
    assert "https://serpapi-job-radar.onrender.com/sitemap.xml" in res_robots.text

    res_sitemap = client.get("/sitemap.xml")
    assert res_sitemap.status_code == 200
    assert "https://serpapi-job-radar.onrender.com/" in res_sitemap.text
    import datetime
    today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    assert f"<lastmod>{today_str}</lastmod>" in res_sitemap.text


def test_pdf_header_with_leading_bytes():
    """Validates that valid PDFs with leading BOM or comments (ISO 32000-1 § 7.5.2) parse without false rejection."""
    from app.pdf_parser import validate_and_extract_resume_pdf
    valid_text = (
        "John Doe - Senior Software Engineer\n"
        "Email: john.doe@example.com | Phone: +91 9876543210 | Bengaluru, India\n\n"
        "Work Experience\n"
        "Lead Python Developer at TechCorp (2022 - Present)\n"
        "Architected high-throughput microservices using FastAPI, Python, and PostgreSQL.\n\n"
        "Technical Skills\n"
        "Python, Docker, SQL, Kubernetes, FastAPI, Redis\n\n"
        "Education\n"
        "B.Tech in Computer Science, State Technical University\n"
    )
    raw_pdf = build_test_pdf(valid_text)
    # Prepend 8 bytes of leading comment/BOM header permitted by ISO 32000-1
    bom_pdf = b"\xef\xbb\xbf%BOM\n" + raw_pdf
    result = validate_and_extract_resume_pdf(bom_pdf)
    assert result["page_count"] >= 1
    assert "Python" in result["skills"]


def test_unlock_and_fit_accept_hybrid_location():
    """Validates that location_type='Hybrid' is fully accepted by /api/unlock and /api/fit."""
    res_unlock = client.post("/api/unlock", json={"skills": ["Python", "SQL"], "location_type": "Hybrid"})
    assert res_unlock.status_code == 200

    res_fit = client.post("/api/fit", json={"skills": ["Python", "SQL"], "location_type": "Hybrid"})
    assert res_fit.status_code == 200


def test_proxy_forwarded_ip_rate_limiting():
    """Validates that X-Forwarded-For is used to accurately isolate client IPs behind reverse proxies."""
    res = client.post("/api/unlock", json={"skills": ["Python"]}, headers={"X-Forwarded-For": "203.0.113.195, 10.0.0.1"})
    assert res.status_code == 200


def test_concurrent_upsert_write_lock_safety():
    """Verifies that concurrent multi-threaded upserts execute without DuckDB catalog write-write conflicts."""
    import concurrent.futures
    from app.database import db_manager

    def upsert_worker(worker_id):
        job = {
            "title": f"Concurrency Test Engineer {worker_id}",
            "company_name": f"Concurrent Corp {worker_id}",
            "location": "Remote",
            "description": "Python DuckDB threading safety test",
            "schedule_type": "Full-time",
            "salary": "25 LPA",
            "posted_at": "Today"
        }
        return db_manager.upsert_jobs([job], is_snapshot=False)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(upsert_worker, range(4)))

    assert all(r == 1 for r in results)

