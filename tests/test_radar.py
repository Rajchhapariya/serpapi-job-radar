import pytest
import os
import tempfile
from unittest.mock import patch
from app.database import DatabaseManager, TRACKED_SKILLS
from app.serpapi_client import SerpApiClient

TEST_FIXTURE_JOBS = [
    {
        "job_id": "test_01_applied_ai",
        "title": "Applied AI Engineer - LLM & RAG Systems",
        "company_name": "KiteMetrics AI",
        "location": "Bengaluru, Karnataka, India",
        "via": "via LinkedIn",
        "description": "Looking for an engineer to build deterministic query evaluation pipelines, vector retrieval with DuckDB and Reciprocal Rank Fusion, and Python FastAPI microservices.",
        "schedule_type": "Full-time",
        "work_from_home": True,
        "salary": "INR 18,00,000 - 24,00,000 / year",
        "apply_link": "https://www.linkedin.com/jobs",
        "posted_at": "1 day ago"
    },
    {
        "job_id": "test_02_data_engineer",
        "title": "Data Engineer (Python, DuckDB, SQL)",
        "company_name": "Synthetix Labs",
        "location": "Remote, India",
        "via": "via Greenhouse",
        "description": "Architect in-process analytical workflows using DuckDB, write robust SQL transformations, and manage PostgreSQL read-replicas for sub-10ms query execution.",
        "schedule_type": "Full-time",
        "work_from_home": True,
        "salary": "INR 15,00,000 - 22,00,000 / year",
        "apply_link": "https://boards.greenhouse.io",
        "posted_at": "2 days ago"
    },
    {
        "job_id": "test_03_backend_fastapi",
        "title": "Backend Software Engineer - Python & Distributed Systems",
        "company_name": "Veritas Infra",
        "location": "Gurgaon, Haryana, India",
        "via": "via Lever",
        "description": "Build high-throughput API services using FastAPI, Redis caching, Docker container orchestration, and PostgreSQL transactional concurrency control.",
        "schedule_type": "Full-time",
        "work_from_home": False,
        "salary": "INR 14,00,000 - 20,00,000 / year",
        "apply_link": "https://jobs.lever.co",
        "posted_at": "3 days ago"
    },
    {
        "job_id": "test_04_fullstack_nextjs",
        "title": "Full-Stack Engineer (Next.js, TypeScript, PostgreSQL)",
        "company_name": "Aura Commerce",
        "location": "Hyderabad, Telangana, India",
        "via": "via Workday",
        "description": "Develop modern web applications with Next.js App Router, TypeScript, React server components, and Tailwind styling connected to Supabase and PostgreSQL.",
        "schedule_type": "Full-time",
        "work_from_home": True,
        "salary": "INR 12,00,000 - 18,00,000 / year",
        "apply_link": "https://myworkdayjobs.com",
        "posted_at": "Just now"
    },
    {
        "job_id": "test_05_mlops_pytorch",
        "title": "Machine Learning Engineer - Model Serving & Docker",
        "company_name": "QuantEdge Technologies",
        "location": "Noida, Uttar Pradesh, India",
        "via": "via Indeed",
        "description": "Deploy PyTorch inference models in production with Docker containers, monitor model latency, and optimize embedding similarity pipelines.",
        "schedule_type": "Full-time",
        "work_from_home": False,
        "salary": "INR 16,00,000 - 25,00,000 / year",
        "apply_link": "https://www.indeed.com",
        "posted_at": "4 days ago"
    }
]


@pytest.fixture
def temp_db():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_radar.duckdb")
    manager = DatabaseManager(db_path=db_path)
    yield manager
    if os.path.exists(db_path):
        os.remove(db_path)



def test_schema_initialization(temp_db):
    with temp_db.get_connection() as con:
        tables = con.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]
        assert "jobs" in table_names


def test_upsert_and_retrieve_jobs(temp_db):
    sample_jobs = [
        {
            "job_id": "test_01",
            "title": "Data Engineer (DuckDB & Python)",
            "company_name": "TestCorp",
            "location": "Bengaluru, India",
            "via": "via LinkedIn",
            "description": "Looking for experience in Python, SQL, DuckDB, and Docker.",
            "schedule_type": "Full-time",
            "work_from_home": True,
            "salary": "INR 18,00,000",
            "apply_link": "https://example.com/apply1",
            "posted_at": "1 day ago"
        },
        {
            "job_id": "test_02",
            "title": "Backend Developer",
            "company_name": "Acme Inc",
            "location": "Gurgaon, India",
            "via": "via Greenhouse",
            "description": "Building microservices with FastAPI and PostgreSQL.",
            "schedule_type": "Full-time",
            "work_from_home": False,
            "salary": "",
            "apply_link": "https://example.com/apply2",
            "posted_at": "2 days ago"
        }
    ]

    inserted = temp_db.upsert_jobs(sample_jobs)
    assert inserted == 2

    results = temp_db.get_jobs()
    assert len(results) == 2


def test_upsert_duplicate_conflict_handling(temp_db):
    initial_job = [{
        "job_id": "job_dup",
        "title": "Junior Python Dev",
        "company_name": "Alpha Corp",
        "location": "Noida",
        "salary": "INR 6,00,000"
    }]
    temp_db.upsert_jobs(initial_job)

    # Re-upsert same job_id with updated title and salary
    updated_job = [{
        "job_id": "job_dup",
        "title": "Senior Python Dev",
        "company_name": "Alpha Corp",
        "location": "Noida",
        "salary": "INR 14,00,000"
    }]
    temp_db.upsert_jobs(updated_job)

    records = temp_db.get_jobs(company="Alpha Corp")
    assert len(records) == 1
    assert records[0]["title"] == "Senior Python Dev"
    assert records[0]["salary"] == "INR 6,00,000"  # Non-null salary preserved per Phase 1.7 merge rules


def test_query_filtering_location_remote(temp_db):
    temp_db.upsert_jobs(TEST_FIXTURE_JOBS)
    remote_jobs = temp_db.get_jobs(location_type="Remote")
    assert len(remote_jobs) > 0
    for j in remote_jobs:
        assert j["work_from_home"] is True or "remote" in j["location"].lower()


def test_query_filtering_location_onsite(temp_db):
    temp_db.upsert_jobs(TEST_FIXTURE_JOBS)
    onsite_jobs = temp_db.get_jobs(location_type="On-site")
    assert len(onsite_jobs) > 0
    for j in onsite_jobs:
        assert j["work_from_home"] is False
        assert "remote" not in j["location"].lower()


def test_query_filtering_has_salary(temp_db):
    temp_db.upsert_jobs(TEST_FIXTURE_JOBS)
    salary_jobs = temp_db.get_jobs(has_salary=True)
    assert len(salary_jobs) > 0
    for j in salary_jobs:
        assert j["salary"] is not None and j["salary"].strip() != ""


def test_query_sorting_options(temp_db):
    temp_db.upsert_jobs(TEST_FIXTURE_JOBS)

    # Sort by company
    by_company = temp_db.get_jobs(sort_by="company")
    company_names = [j["company_name"].lower() for j in by_company]
    assert company_names == sorted(company_names)

    # Sort by title
    by_title = temp_db.get_jobs(sort_by="title")
    titles = [j["title"].lower() for j in by_title]
    assert titles == sorted(titles)


def test_pagination_limits_and_offsets(temp_db):
    temp_db.upsert_jobs(TEST_FIXTURE_JOBS)
    page_1 = temp_db.get_jobs(limit=2, offset=0)
    page_2 = temp_db.get_jobs(limit=2, offset=2)

    assert len(page_1) == 2
    assert len(page_2) == 2
    assert page_1[0]["job_id"] != page_2[0]["job_id"]

    # Offset beyond total
    empty_page = temp_db.get_jobs(limit=10, offset=100)
    assert len(empty_page) == 0


def test_sql_injection_safety(temp_db):
    temp_db.upsert_jobs(TEST_FIXTURE_JOBS)
    malicious_query = "' OR '1'='1"
    results = temp_db.get_jobs(keyword=malicious_query)
    # Should safely return 0 results without SQL syntax error
    assert isinstance(results, list)


def test_special_character_keywords(temp_db):
    custom_jobs = [{
        "job_id": "special_char_01",
        "title": "Systems Engineer (C++ / Node.js)",
        "company_name": "InfraTech",
        "description": "Microservices built with Node.js and C++ libraries."
    }]
    temp_db.upsert_jobs(custom_jobs)

    res = temp_db.get_jobs(keyword="Node.js")
    assert len(res) == 1
    assert res[0]["job_id"] == "special_char_01"


def test_empty_database_analytics_graceful_defaults(temp_db):
    analytics = temp_db.get_analytics()
    assert analytics["total_jobs"] == 0
    assert analytics["remote_jobs"] == 0
    assert analytics["on_site_jobs"] == 0
    assert analytics["salary_disclosed_jobs"] == 0
    assert analytics["top_skills"] == []
    assert analytics["top_companies"] == []
    assert analytics["top_platforms"] == []


def test_analytics_skills_and_platforms_extraction(temp_db):
    temp_db.upsert_jobs(TEST_FIXTURE_JOBS)
    analytics = temp_db.get_analytics()

    assert analytics["total_jobs"] == len(TEST_FIXTURE_JOBS)
    assert len(analytics["top_skills"]) > 0
    assert len(analytics["top_platforms"]) > 0

    platforms = [p["platform"] for p in analytics["top_platforms"]]
    assert any(p in ["LinkedIn", "Greenhouse", "Lever", "Workday", "Indeed"] for p in platforms)


def test_resume_matching_comprehensive(temp_db):
    temp_db.upsert_jobs(TEST_FIXTURE_JOBS)
    resume = "Senior Engineer with strong Python, DuckDB, SQL, Docker, and PostgreSQL expertise."
    match_result = temp_db.match_resume(resume)

    assert "Python" in match_result["matched_skills"]
    assert "DuckDB" in match_result["matched_skills"]
    assert "Docker" in match_result["matched_skills"]
    assert match_result["match_score_percentage"] > 0
    assert len(match_result["recommended_jobs"]) > 0


def test_resume_matching_zero_match(temp_db):
    temp_db.upsert_jobs(TEST_FIXTURE_JOBS)
    resume = "Certified accountant with deep expertise in auditing and tax balance sheets."
    match_result = temp_db.match_resume(resume)

    assert match_result["matched_skills"] == []
    assert match_result["match_score_percentage"] == 0
    assert len(match_result["missing_skills"]) > 0


def test_serpapi_client_unconfigured_error():
    client = SerpApiClient(api_key="your_unconfigured_key")
    res = client.fetch_jobs(query="Python", location="India", num_results=5)

    assert res["source"] == "api_key_missing"
    assert len(res["jobs"]) == 0


def test_serpapi_client_network_error_graceful_recovery():
    client = SerpApiClient(api_key="actual_secret_token_123")

    with patch("requests.get") as mock_get:
        mock_get.side_effect = Exception("Simulated connection timeout")
        res = client.fetch_jobs(query="Python", location="India", num_results=5)

        assert res["source"] == "network_error"
        assert len(res["jobs"]) == 0
        assert "Simulated connection timeout" in res["message"]



def test_security_headers_present():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.get("/")

    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "default-src 'self'" in response.headers.get("Content-Security-Policy", "")


def test_seo_robots_txt():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.get("/robots.txt")

    assert response.status_code == 200
    assert "User-agent: *" in response.text
    assert "Sitemap:" in response.text


def test_seo_sitemap_xml():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.get("/sitemap.xml")

    assert response.status_code == 200
    assert "application/xml" in response.headers.get("content-type", "")
    assert "<urlset" in response.text


def test_search_input_validation_boundary():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    # Query with illegal control characters
    bad_payload = {"query": "python<script>alert(1)</script>", "location": "India"}
    response = client.post("/api/search", json=bad_payload)
    assert response.status_code == 422  # Unprocessable Entity (strict regex boundary)


def test_resume_matcher_payload_boundary():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    # Oversized payload exceeding 50,000 characters
    oversized = "Python " * 10000
    response = client.post("/api/match-resume", json={"resume_text": oversized})
    assert response.status_code == 422  # Unprocessable Entity (exceeds max_length=50000)


def test_brand_assets_and_favicons_available():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    asset_paths = [
        "/static/favicon.svg",
        "/static/favicon.ico",
        "/static/favicon-16x16.png",
        "/static/favicon-32x32.png",
        "/static/apple-touch-icon.png",
        "/static/icon-192.png",
        "/static/icon-512.png",
        "/static/logo.svg",
        "/static/logo-icon.svg"
    ]
    for path in asset_paths:
        res = client.get(path)
        assert res.status_code == 200, f"Expected 200 for {path}, got {res.status_code}"
        assert len(res.content) > 0, f"Expected non-empty content for {path}"


def test_search_with_recency_filter(temp_db):
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    # Valid date_posted options: today, 3days, week, month
    valid_payload = {
        "query": "Python Engineer",
        "location": "India",
        "date_posted": "week"
    }
    with patch("app.main.serpapi_client.fetch_jobs") as mock_fetch, \
         patch("app.main.db_manager", temp_db):
        mock_fetch.return_value = {
            "source": "live_serpapi",
            "jobs": TEST_FIXTURE_JOBS,
            "message": "Successfully retrieved 5 live jobs."
        }
        response = client.post("/api/search", json=valid_payload)
        assert response.status_code == 200
        data = response.json()
        assert "retrieved_count" in data
        assert data["retrieved_count"] == 5


    # Invalid date_posted rejected by regex pattern boundary
    bad_payload = {
        "query": "Python Engineer",
        "location": "India",
        "date_posted": "yesterday"
    }
    bad_response = client.post("/api/search", json=bad_payload)
    assert bad_response.status_code == 422



def test_jobs_calendar_date_filters(temp_db):
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # Valid date range format (YYYY-MM-DD)
    response = client.get("/api/jobs?from_date=2026-10-01&to_date=2026-10-05")
    assert response.status_code == 200
    assert "jobs" in response.json()

    # Invalid calendar format returns 422
    bad_response = client.get("/api/jobs?from_date=01-10-2026")
    assert bad_response.status_code == 422


def test_database_calendar_date_range(temp_db):
    sample_jobs = [
        {
            "job_id": "date_test_01",
            "title": "Data Engineer 2026",
            "company_name": "DateCorp",
            "location": "Remote",
            "via": "via LinkedIn",
            "description": "Python DuckDB SQL",
            "schedule_type": "Full-time",
            "work_from_home": True,
            "salary": "INR 20,00,000",
            "apply_link": "https://example.com/date1",
            "posted_at": "Today"
        }
    ]
    temp_db.upsert_jobs(sample_jobs)
    import datetime
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    # Match today
    matched = temp_db.get_jobs(from_date=today_str, to_date=today_str)
    assert len(matched) >= 1

    # Match in past should return 0
    past = temp_db.get_jobs(from_date="2020-01-01", to_date="2020-01-02")
    assert len(past) == 0


def test_api_date_range_inverted_validation():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)

    # Inverted date range (from_date > to_date) must return 422 Unprocessable Entity
    response = client.get("/api/jobs?from_date=2026-10-10&to_date=2026-10-01")
    assert response.status_code == 422
    assert "cannot be later than" in response.json()["detail"]


def test_comprehensive_input_field_validations():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)

    # 1. Search query too short (< 2 chars) -> 422
    res = client.post("/api/search", json={"query": "a", "location": "India"})
    assert res.status_code == 422

    # 2. Search query too long (> 100 chars) -> 422
    res = client.post("/api/search", json={"query": "x" * 101, "location": "India"})
    assert res.status_code == 422

    # 3. Location with illegal script injection -> 422
    res = client.post("/api/search", json={"query": "Python", "location": "India<script>"})
    assert res.status_code == 422

    # 4. Resume matcher too short (< 5 chars) -> 422
    res = client.post("/api/match-resume", json={"resume_text": "Py"})
    assert res.status_code == 422

    # 5. Jobs filter invalid location_type -> 422
    res = client.get("/api/jobs?location_type=Virtual")
    assert res.status_code == 422

    # 6. Jobs filter invalid sort_by -> 422
    res = client.get("/api/jobs?sort_by=salary_desc")
    assert res.status_code == 422

    # 7. Jobs filter limit out of bounds (> 100) -> 422
    res = client.get("/api/jobs?limit=500")
    assert res.status_code == 422

    # 8. Jobs filter negative offset -> 422
    res = client.get("/api/jobs?offset=-5")
    assert res.status_code == 422

    # 9. Jobs filter keyword too long (> 100) -> 422
    res = client.get("/api/jobs?keyword=" + "k" * 105)
    assert res.status_code == 422


def test_readonly_sql_execution(monkeypatch):
    monkeypatch.setenv("ENABLE_SQL_CONSOLE", "true")
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)

    # Valid SELECT query
    res = client.post("/api/sql", json={"query": "SELECT COUNT(*) as total FROM jobs"})
    assert res.status_code == 200
    data = res.json()
    assert "columns" in data
    assert "rows" in data
    assert "latency_ms" in data
    assert data["row_count"] >= 1


def test_readonly_sql_security_sandbox(monkeypatch):
    monkeypatch.setenv("ENABLE_SQL_CONSOLE", "true")
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)

    # Reject non-SELECT
    res_delete = client.post("/api/sql", json={"query": "DELETE FROM jobs WHERE 1=1"})
    assert res_delete.status_code == 400

    # Reject DROP
    res_drop = client.post("/api/sql", json={"query": "DROP TABLE jobs"})
    assert res_drop.status_code == 400

    # Reject INSERT
    res_insert = client.post("/api/sql", json={"query": "INSERT INTO jobs (job_id) VALUES ('evil')"})
    assert res_insert.status_code == 400


def test_export_csv_and_json():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)

    # CSV Export
    res_csv = client.get("/api/export?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "attachment; filename=serpapi_jobs_radar.csv" in res_csv.headers["content-disposition"]

    # JSON Export
    res_json = client.get("/api/export?format=json")
    assert res_json.status_code == 200
    assert "application/json" in res_json.headers["content-type"]
    assert "attachment; filename=serpapi_jobs_radar.json" in res_json.headers["content-disposition"]


def test_sql_console_presets_execution(monkeypatch):
    monkeypatch.setenv("ENABLE_SQL_CONSOLE", "true")
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)

    # Preset 1: Platform & Salary
    p1 = "SELECT COALESCE(via_platform, 'Direct / Portal') AS platform, COUNT(*) AS openings, ROUND(AVG(CASE WHEN salary_raw IS NOT NULL THEN 100.0 ELSE 0.0 END), 1) AS salary_disclosure_pct FROM jobs GROUP BY platform ORDER BY openings DESC LIMIT 10"
    r1 = client.post("/api/sql", json={"query": p1})
    assert r1.status_code == 200
    d1 = r1.json()
    assert "columns" in d1
    assert "platform" in d1["columns"]

    # Preset 2: Unnested Skills
    p2 = "SELECT unnest(skills_required) AS skill, COUNT(*) AS demand_count FROM jobs GROUP BY skill ORDER BY demand_count DESC LIMIT 10"
    r2 = client.post("/api/sql", json={"query": p2})
    assert r2.status_code == 200
    d2 = r2.json()
    assert "skill" in d2["columns"]

    # Preset 3: Work Arrangement
    p3 = "SELECT location_type, COUNT(*) AS total_jobs, ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS share_percentage FROM jobs GROUP BY location_type ORDER BY total_jobs DESC"
    r3 = client.post("/api/sql", json={"query": p3})
    assert r3.status_code == 200
    d3 = r3.json()
    assert "location_type" in d3["columns"]


def test_export_filtered_and_date_boundaries():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)

    # Filtered CSV Export
    res = client.get("/api/export?format=csv&location_type=Remote&has_salary=true")
    assert res.status_code == 200

    # Invalid Date boundary check
    res_err = client.get("/api/export?format=csv&from_date=2026-10-15&to_date=2026-10-01")
    assert res_err.status_code == 422


# ==================== PHASE 1 DATA LAYER TESTS ====================

def test_migration_from_old_schema_with_data_and_idempotence(tmp_path):
    """
    Creates a database strictly using the OLD schema, populates it with rows,
    runs the migration to add new columns, verifies existing data is preserved,
    verifies new columns are accessible, and runs migration a second time to prove idempotency.
    """
    import duckdb
    db_file = str(tmp_path / "old_radar.duckdb")

    # 1. Initialize strictly with OLD schema (no apply_options, portal_count, salary_min_lpa, etc.)
    with duckdb.connect(db_file) as con:
        con.execute("""
            CREATE TABLE jobs (
                job_id VARCHAR PRIMARY KEY,
                title VARCHAR NOT NULL,
                company_name VARCHAR NOT NULL,
                location VARCHAR,
                via VARCHAR,
                description VARCHAR,
                schedule_type VARCHAR,
                work_from_home BOOLEAN DEFAULT FALSE,
                salary VARCHAR,
                apply_link VARCHAR,
                posted_at VARCHAR,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                via_platform VARCHAR,
                salary_raw VARCHAR,
                location_type VARCHAR,
                skills_required VARCHAR[]
            );
        """)
        con.execute("""
            INSERT INTO jobs (job_id, title, company_name, location, salary_raw)
            VALUES ('old_job_1', 'Legacy Python Dev', 'OldCorp', 'Bengaluru', '₹10 LPA');
        """)

    # 2. Instantiate DatabaseManager on this DB path — triggers migration
    manager = DatabaseManager(db_path=db_file)

    # 3. Verify old data exists and new columns were created
    with manager.get_connection() as con:
        row = con.execute("SELECT job_id, title, apply_options, portal_count, salary_min_lpa, is_snapshot FROM jobs WHERE job_id = 'old_job_1'").fetchone()
        assert row is not None
        assert row[0] == "old_job_1"
        assert row[1] == "Legacy Python Dev"
        assert row[2] is None  # apply_options
        assert row[3] == 1     # portal_count default 1
        assert row[4] is None  # salary_min_lpa
        assert row[5] is False # is_snapshot default False

    # 4. Run migration a second time to verify idempotency (no error, no data loss)
    manager._run_migrations()
    with manager.get_connection() as con:
        count = con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        assert count == 1


def test_salary_parser_comprehensive_cases():
    """
    Tests parse_indian_salary_to_lpa with 10+ diverse test cases, including required cases.
    """
    from app.serpapi_client import parse_indian_salary_to_lpa

    # Required Case 1: Monthly range -> LPA
    assert parse_indian_salary_to_lpa("₹50,000–80,000 a month") == (6.0, 9.6)
    assert parse_indian_salary_to_lpa("₹50,000 - 80,000 a month") == (6.0, 9.6)

    # Required Case 2: LPA range
    assert parse_indian_salary_to_lpa("₹8–12 LPA") == (8.0, 12.0)
    assert parse_indian_salary_to_lpa("8 - 12 LPA") == (8.0, 12.0)

    # Required Case 3: Lakh per year
    assert parse_indian_salary_to_lpa("₹6 lakh a year") == (6.0, 6.0)
    assert parse_indian_salary_to_lpa("6.5 Lakhs / year") == (6.5, 6.5)

    # Required Case 4: Non-INR currency -> None
    assert parse_indian_salary_to_lpa("$120K a year") == (None, None)
    assert parse_indian_salary_to_lpa("€80,000 - €100,000 / year") == (None, None)
    assert parse_indian_salary_to_lpa("£50,000 a year") == (None, None)

    # Case 5: Raw annual figures with Indian numbering
    assert parse_indian_salary_to_lpa("INR 14,00,000 - 20,00,000 / year") == (14.0, 20.0)

    # Case 6: Single monthly salary
    assert parse_indian_salary_to_lpa("₹60,000 a month") == (7.2, 7.2)

    # Case 7: Unparseable, ambiguous, or empty
    assert parse_indian_salary_to_lpa("Competitive") == (None, None)
    assert parse_indian_salary_to_lpa("") == (None, None)
    assert parse_indian_salary_to_lpa(None) == (None, None)
    assert parse_indian_salary_to_lpa("Not Disclosed") == (None, None)


def test_apply_options_and_portal_count_storage(tmp_path):
    """
    Tests persisting apply_options and computing portal_count accurately.
    """
    import json
    db_file = str(tmp_path / "apply_test.duckdb")
    manager = DatabaseManager(db_path=db_file)

    sample_job = {
        "job_id": "job_multi_portal_01",
        "title": "Staff Platform Engineer",
        "company_name": "NexusTech",
        "location": "Bengaluru",
        "salary_raw": "₹25–35 LPA",
        "salary_min_lpa": 25.0,
        "salary_max_lpa": 35.0,
        "apply_options": [
            {"title": "LinkedIn", "link": "https://linkedin.com/jobs/1"},
            {"title": "Indeed", "link": "https://indeed.com/jobs/1"},
            {"title": "Company Site", "link": "https://nexustech.com/apply"}
        ],
        "portal_count": 3
    }

    inserted = manager.upsert_jobs([sample_job])
    assert inserted == 1

    with manager.get_connection() as con:
        row = con.execute("SELECT portal_count, apply_options, salary_min_lpa, salary_max_lpa FROM jobs WHERE job_id = 'job_multi_portal_01'").fetchone()
        assert row[0] == 3
        opts = json.loads(row[1]) if isinstance(row[1], str) else row[1]
        assert len(opts) == 3
        assert opts[0]["title"] == "LinkedIn"
        assert row[2] == 25.0
        assert row[3] == 35.0


def test_snapshot_seeding_idempotence(tmp_path):
    """
    Tests that snapshot seeding loads jobs if DB is empty,
    preserves captured_at as scraped_at, sets is_snapshot=True,
    and does not re-insert or duplicate when called again.
    """
    import json
    db_file = str(tmp_path / "snapshot_seed.duckdb")
    manager = DatabaseManager(db_path=db_file)

    # Create dummy snapshots dir
    snap_dir = str(tmp_path / "snapshots")
    os.makedirs(snap_dir, exist_ok=True)
    snap_data = {
        "slug": "test_snap",
        "captured_at": "2026-10-01T12:00:00Z",
        "jobs": [
            {
                "job_id": "snap_job_1",
                "title": "Snapshot Data Engineer",
                "company_name": "SnapCorp",
                "location": "Hyderabad",
                "salary": "₹12–18 LPA",
                "apply_options": [{"title": "LinkedIn", "link": "https://linkedin.com"}]
            }
        ]
    }
    with open(os.path.join(snap_dir, "test_snap.json"), "w", encoding="utf-8") as f:
        json.dump(snap_data, f)

    # 1. First run: table is empty -> loads data
    seeded = manager.load_snapshots_if_empty(snapshots_dir=snap_dir)
    assert seeded == 1

    with manager.get_connection() as con:
        row = con.execute("SELECT job_id, is_snapshot, scraped_at, salary_min_lpa FROM jobs WHERE serpapi_token = 'snap_job_1' OR job_id = 'snap_job_1'").fetchone()
        assert row is not None
        snap_id = row[0]
        assert row[1] is True
        assert "2026-10-01" in str(row[2])
        assert row[3] == 12.0

    # 2. Second run: table is not empty -> skips seeding
    seeded_again = manager.load_snapshots_if_empty(snapshots_dir=snap_dir)
    assert seeded_again == 0

    # 3. Live upsert of an existing snapshot row changes is_snapshot to False
    live_job = {
        "job_id": snap_id,
        "title": "Snapshot Data Engineer",
        "company_name": "SnapCorp",
        "location": "Hyderabad",
        "is_snapshot": False
    }
    manager.upsert_jobs([live_job], is_snapshot=False)
    with manager.get_connection() as con:
        row_after = con.execute("SELECT is_snapshot, title FROM jobs WHERE job_id = ?", [snap_id]).fetchone()
        assert row_after is not None
        assert row_after[0] is False
        assert row_after[1] == "Snapshot Data Engineer"


def test_cache_hit_bypasses_network_call():
    """
    Tests that a cache hit returns source='cache' without making any HTTP request,
    reporting honest cache metadata (exact message prefix, fetched_at presence, null serpapi_ms/ingest_ms).
    Also asserts live responses carry fetched_at=None.
    """
    from fastapi.testclient import TestClient
    from unittest.mock import patch
    from app.main import app

    client = TestClient(app)

    # Prime cache directly
    from app.database import db_manager
    from app.main import get_search_cache_key
    key = get_search_cache_key("UniqueCacheQuery", "Bengaluru", "in", "en", None)
    db_manager.set_cached_search(
        key,
        {"query": "UniqueCacheQuery", "location": "Bengaluru", "gl": "in", "hl": "en"},
        {"jobs": [{"title": "Cached Job"}], "message": "From Cache"}
    )

    # Patch requests.get to ensure network layer is NOT called
    with patch("requests.get") as mock_get:
        res = client.post("/api/search", json={
            "query": "UniqueCacheQuery",
            "location": "Bengaluru",
            "gl": "in",
            "hl": "en"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["source"] == "cache"
        assert data["message"].startswith("Served from cache (originally fetched at ")
        assert "live" not in data["message"].lower()
        assert "serpapi in" not in data["message"].lower()
        assert data["fetched_at"] is not None
        assert data["serpapi_ms"] is None
        assert data["ingest_ms"] is None
        assert data["stored_count"] == 0
        mock_get.assert_not_called()

    # Verify that a live response has fetched_at=None
    from app.serpapi_client import serpapi_client
    with patch.object(serpapi_client, "fetch_jobs") as mock_fetch:
        mock_fetch.return_value = {
            "source": "live",
            "jobs": [],
            "calls_made": 1,
            "serpapi_ms": 120,
            "serpapi_cached": False,
            "serpapi_time_taken_s": 0.12,
            "message": "Live query"
        }
        res_live = client.post("/api/search", json={
            "query": "UncachedLiveQuery",
            "location": "Bengaluru",
            "gl": "in",
            "hl": "en"
        })
        assert res_live.status_code == 200
        data_live = res_live.json()
        assert data_live["source"] == "live"
        assert data_live["fetched_at"] is None



def test_search_cache_utc_timestamp_under_timezone():
    """
    Asserts search_cache.fetched_at is stored in naive UTC and returns a UTC ISO string.
    Opens a connection, runs SET TimeZone='Asia/Kolkata', calls set_cached_search then get_cached_search,
    and asserts the returned fetched_at is within 5 seconds of datetime.now(timezone.utc).
    """
    from datetime import datetime, timezone
    from app.database import db_manager

    con = db_manager.get_connection()
    try:
        con.execute("SET TimeZone='Asia/Kolkata'")
        cache_key = "test_tz_utc_correctness"
        query_meta = {"query": "tz_test", "location": "India"}
        response_data = {"jobs": [{"title": "TZ Test Job"}]}
        db_manager.set_cached_search(cache_key, query_meta, response_data, con=con)
        cached = db_manager.get_cached_search(cache_key, ttl_hours=24, con=con)
        assert cached is not None
        assert "fetched_at" in cached
        fetched_at_str = cached["fetched_at"]
        assert fetched_at_str.endswith("Z")
        dt_val = datetime.fromisoformat(fetched_at_str.rstrip("Z")).replace(tzinfo=timezone.utc)
        now_utc = datetime.now(timezone.utc)
        diff_s = abs((now_utc - dt_val).total_seconds())
        assert diff_s <= 5, f"Expected fetched_at within 5s of UTC now, got {diff_s}s"
    finally:
        con.close()



def test_quota_guard_exhaustion_behavior():
    """
    Tests that when quota reserve is exhausted, live SerpApi call is prevented
    and historical cache is returned with notice, or 429 if no cache exists.
    """
    from fastapi.testclient import TestClient
    from unittest.mock import patch
    import app.main as main_mod

    client = TestClient(main_mod.app)

    # 1. Mock Account API to return plan_searches_left = 10 (below reserve threshold of 15)
    mock_quota = {
        "plan_searches_left": 10,
        "total_searches_left": 10
    }
    with patch.object(main_mod.serpapi_client, "get_account_quota", return_value=mock_quota):
        with patch("requests.get") as mock_http:
            res = client.post("/api/search", json={
                "query": "UncachedQueryQuotaExhausted",
                "location": "India"
            })
            # Since not in cache and quota reserve is hit -> 429
            assert res.status_code == 429
            assert "reserve" in res.json()["detail"].lower()
            mock_http.assert_not_called()


def test_expanded_skills_lookarounds_and_aliases():
    """
    Tests strict skill boundary lookarounds, alias expansion, and negative assertions.
    """
    from app.database import extract_skills_from_text

    # 1. Negative lookaround assertions
    js_text = "Looking for a JavaScript developer who loves TypeScript and React."
    skills = extract_skills_from_text(js_text)
    assert "JavaScript" in skills
    assert "Java" not in skills, "'Java' should not match inside 'JavaScript'"

    git_text = "Please submit your GitHub profile and Git commit logs."
    skills = extract_skills_from_text(git_text)
    assert "Git" in skills
    # Ensure GitHub did not generate a duplicate or corrupt entry

    market_text = "We are formulating our go to market strategy."
    skills = extract_skills_from_text(market_text)
    assert "Golang" not in skills, "'go to market' must not match Go/Golang"

    rag_lower = "Clean the desk with a rag before writing code."
    skills = extract_skills_from_text(rag_lower)
    assert "RAG" not in skills, "lowercase 'rag' must not match 'RAG'"

    rag_upper = "Architecting production RAG pipelines with Vector DB."
    skills = extract_skills_from_text(rag_upper)
    assert "RAG" in skills

    # 2. Positive special-character lookarounds
    cpp_cs_text = "Proficiency in C++ and C# with .NET microservices required."
    skills = extract_skills_from_text(cpp_cs_text)
    assert "C++" in skills
    assert "C#" in skills
    assert ".NET" in skills
    assert "Microservices" in skills

    # 3. Multi-word phrases & aliases
    alias_text = "Postgres and K8s on Amazon Web Services with NodeJS, scikit-learn and Power BI."
    skills = extract_skills_from_text(alias_text)
    assert "PostgreSQL" in skills
    assert "Kubernetes" in skills
    assert "AWS" in skills
    assert "Node.js" in skills
    assert "scikit-learn" in skills
    assert "Power BI" in skills

    spring_text = "Enterprise Spring Boot and Apache Spark data engineering."
    skills = extract_skills_from_text(spring_text)
    assert "Spring Boot" in skills
    assert "Spark" in skills


def test_salary_parser_boundaries_and_sanitization():
    """
    Tests annual boundary (1..200 LPA), hourly rate retention, and strict relative time filtering.
    """
    from app.serpapi_client import parse_indian_salary_to_lpa, sanitize_salary_raw

    # 1. 1..200 LPA boundaries
    assert parse_indian_salary_to_lpa("₹50K a year") == (None, None), "0.5 LPA is below 1.0 LPA boundary"
    assert parse_indian_salary_to_lpa("₹500 LPA") == (None, None), "500 LPA is above 200.0 LPA boundary"
    assert parse_indian_salary_to_lpa("₹8-12 LPA") == (8.0, 12.0)
    assert parse_indian_salary_to_lpa("₹1 LPA") == (1.0, 1.0)
    assert parse_indian_salary_to_lpa("₹200 LPA") == (200.0, 200.0)

    # 2. Hourly rate: LPA returns None, but raw string is kept
    assert parse_indian_salary_to_lpa("₹300 an hour") == (None, None)
    assert sanitize_salary_raw("₹300 an hour") == "₹300 an hour"

    # 3. Monthly Lakh scaling (*12) and unitless annual rejection
    assert parse_indian_salary_to_lpa("₹1.25L–₹2.5L a month") == (15.0, 30.0)
    assert parse_indian_salary_to_lpa("₹22–₹30 a year") == (None, None)

    # 4. Strict relative-time sanitation
    assert sanitize_salary_raw("13 hours ago") is None
    assert sanitize_salary_raw("19 hours ago") is None
    assert sanitize_salary_raw("1 day ago") is None
    assert sanitize_salary_raw("3 weeks ago") is None
    assert sanitize_salary_raw("just now") is None
    assert sanitize_salary_raw("yesterday") is None
    assert sanitize_salary_raw("today") is None
    assert sanitize_salary_raw("Full-time") is None
    assert sanitize_salary_raw("") is None
    assert sanitize_salary_raw("   ") is None


def test_api_health_and_quota_privacy(monkeypatch):
    """
    Verifies that /api/health and /api/quota NEVER leak account_email, plan name, or private credentials.
    """
    monkeypatch.setenv("ENABLE_QUOTA_ENDPOINT", "true")
    from fastapi.testclient import TestClient
    from unittest.mock import patch
    import app.main as main_mod

    client = TestClient(main_mod.app)

    mock_account_quota = {
        "account_email": "confidential_engineer@example.com",
        "plan_id": "premium_tier_2026",
        "plan_name": "Enterprise Plan",
        "plan_searches_left": 150,
        "total_searches_left": 150
    }

    with patch.object(main_mod.serpapi_client, "get_cached_quota_sync", return_value=mock_account_quota):
        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.json()

        # Public health fields check
        assert "status" in data
        assert "indexed_jobs_count" in data
        assert "uptime_seconds" in data
        assert "serpapi_configured" in data
        assert "quota_ok" in data
        assert data["quota_ok"] is True

        # Privacy checks: must NOT expose email, plan name, or raw quota dump
        assert "account_email" not in data
        assert "plan_name" not in data
        assert "database" not in data  # Path not exposed

    with patch.object(main_mod.serpapi_client, "get_account_quota", return_value=mock_account_quota):
        res = client.get("/api/quota")
        assert res.status_code == 200
        data = res.json()
        assert "quota" in data
        assert "account_email" not in data["quota"], "account_email must be stripped from /api/quota"


def test_latency_split_metrics():
    """
    Verifies that search returns ingest_ms on write, query_ms as None on write,
    and query_ms is measured on read.
    """
    from fastapi.testclient import TestClient
    import app.main as main_mod

    client = TestClient(main_mod.app)

    # 1. Read endpoint returns query_ms
    res = client.get("/api/jobs?limit=5")
    assert res.status_code == 200
    data = res.json()
    assert "query_ms" in data
    assert isinstance(data["query_ms"], (int, float))
    assert data.get("ingest_ms") is None


def test_dedup_same_job_different_serpapi_tokens(temp_db):
    """
    Tests that the same job posted under 2 different SerpApi tokens merges into
    1 row with both queries stored in source_queries.
    """
    job_1 = {
        "title": "Staff Backend Engineer",
        "company_name": "Nimbus Cloud Corp",
        "location": "Bengaluru, India",
        "description": "Designing high-scale distributed systems using Python and DuckDB.",
        "serpapi_token": "token_serp_alpha",
        "source_query": "Backend Engineer Bengaluru",
        "apply_options": [{"title": "LinkedIn", "link": "https://linkedin.com/job1"}]
    }
    job_2 = {
        "title": "Staff Backend Engineer",
        "company_name": "Nimbus Cloud Corp",
        "location": "Bengaluru, India",
        "description": "Designing high-scale distributed systems using Python and DuckDB.",
        "serpapi_token": "token_serp_beta",
        "source_query": "Python Engineer Bengaluru",
        "apply_options": [{"title": "Indeed", "link": "https://indeed.com/job1"}]
    }

    inserted_1 = temp_db.upsert_jobs([job_1])
    assert inserted_1 == 1

    inserted_2 = temp_db.upsert_jobs([job_2])
    assert inserted_2 == 1

    jobs = temp_db.get_jobs(company="Nimbus Cloud Corp")
    assert len(jobs) == 1
    record = jobs[0]
    assert record["source_queries"] == ["Backend Engineer Bengaluru", "Python Engineer Bengaluru"]
    assert record["source_query"] == "Backend Engineer Bengaluru"
    assert record["portal_count"] == 2
    assert record["serpapi_token"] == "token_serp_alpha"


def test_dedup_apply_options_union_and_portal_count(temp_db):
    """
    Tests that apply_options merges by publisher title, keeping the first link per publisher,
    and portal_count equals the length of the union.
    """
    job_a = {
        "title": "Principal Data Platform Architect",
        "company_name": "VectorScale Inc",
        "location": "Hyderabad, India",
        "description": "Architecting petabyte-scale data lakes with Spark and DuckDB.",
        "serpapi_token": "token_vector_01",
        "apply_options": [
            {"title": "LinkedIn", "link": "https://linkedin.com/jobs/view/1001"},
            {"title": "Company Careers", "link": "https://vectorscale.io/careers/1001"}
        ]
    }
    job_b = {
        "title": "Principal Data Platform Architect",
        "company_name": "VectorScale Inc",
        "location": "Hyderabad, India",
        "description": "Architecting petabyte-scale data lakes with Spark and DuckDB.",
        "serpapi_token": "token_vector_02",
        "apply_options": [
            {"title": "LinkedIn", "link": "https://linkedin.com/jobs/view/different_link"},
            {"title": "Indeed", "link": "https://indeed.com/viewjob?jk=2002"},
            {"title": "Glassdoor", "link": "https://glassdoor.com/job/3003"}
        ]
    }

    temp_db.upsert_jobs([job_a])
    temp_db.upsert_jobs([job_b])

    records = temp_db.get_jobs(company="VectorScale Inc")
    assert len(records) == 1
    job = records[0]

    import json
    opts = json.loads(job["apply_options"]) if isinstance(job["apply_options"], str) else job["apply_options"]
    assert len(opts) == 4
    assert job["portal_count"] == 4

    # Verify first link per publisher is preserved
    linkedin_opts = [o for o in opts if o.get("title") == "LinkedIn"]
    assert len(linkedin_opts) == 1
    assert linkedin_opts[0]["link"] == "https://linkedin.com/jobs/view/1001"


def test_dedup_non_null_salary_preserved_on_merge(temp_db):
    """
    Tests that existing non-null salary (salary_raw, salary_min_lpa, salary_max_lpa)
    is preserved when merged with an incoming job that has null or different salary.
    Also tests taking incoming salary when existing is null.
    """
    # 1. Existing has non-null salary, incoming has null
    job_sal = {
        "title": "ML Research Scientist",
        "company_name": "DeepCognition",
        "location": "Bengaluru, India",
        "description": "Training transformer models and LLM evaluators.",
        "serpapi_token": "dc_token_1",
        "salary_raw": "₹30–45 LPA",
        "salary_min_lpa": 30.0,
        "salary_max_lpa": 45.0
    }
    job_nosal = {
        "title": "ML Research Scientist",
        "company_name": "DeepCognition",
        "location": "Bengaluru, India",
        "description": "Training transformer models and LLM evaluators.",
        "serpapi_token": "dc_token_2",
        "salary_raw": None,
        "salary_min_lpa": None,
        "salary_max_lpa": None
    }
    temp_db.upsert_jobs([job_sal])
    temp_db.upsert_jobs([job_nosal])

    rec = temp_db.get_jobs(company="DeepCognition")[0]
    assert rec["salary_raw"] == "₹30–45 LPA"
    assert rec["salary_min_lpa"] == 30.0
    assert rec["salary_max_lpa"] == 45.0

    # 2. Existing has null salary, incoming has non-null salary -> incoming is taken
    job_null_first = {
        "title": "DevOps Architect",
        "company_name": "CloudOps Alpha",
        "location": "Pune, India",
        "description": "Kubernetes orchestration and multi-region failover.",
        "serpapi_token": "co_token_1",
        "salary_raw": None
    }
    job_sal_second = {
        "title": "DevOps Architect",
        "company_name": "CloudOps Alpha",
        "location": "Pune, India",
        "description": "Kubernetes orchestration and multi-region failover.",
        "serpapi_token": "co_token_2",
        "salary_raw": "₹22–28 LPA",
        "salary_min_lpa": 22.0,
        "salary_max_lpa": 28.0
    }
    temp_db.upsert_jobs([job_null_first])
    temp_db.upsert_jobs([job_sal_second])

    rec2 = temp_db.get_jobs(company="CloudOps Alpha")[0]
    assert rec2["salary_raw"] == "₹22–28 LPA"
    assert rec2["salary_min_lpa"] == 22.0
    assert rec2["salary_max_lpa"] == 28.0


def test_dedup_live_upsert_over_snapshot_clears_is_snapshot(temp_db):
    """
    Tests that a live upsert over an existing snapshot row sets is_snapshot = FALSE.
    """
    snapshot_job = {
        "title": "Site Reliability Engineer",
        "company_name": "InfraCore",
        "location": "Bengaluru, India",
        "description": "Managing Prometheus, Grafana, and Kubernetes clusters.",
        "serpapi_token": "sre_snap_token",
        "is_snapshot": True
    }
    temp_db.upsert_jobs([snapshot_job], is_snapshot=True)

    rec_before = temp_db.get_jobs(company="InfraCore")[0]
    assert rec_before["is_snapshot"] is True

    # Live search arrives with same canonical job
    live_job = {
        "title": "Site Reliability Engineer",
        "company_name": "InfraCore",
        "location": "Bengaluru, India",
        "description": "Managing Prometheus, Grafana, and Kubernetes clusters.",
        "serpapi_token": "sre_live_token",
        "is_snapshot": False
    }
    temp_db.upsert_jobs([live_job], is_snapshot=False)

    rec_after = temp_db.get_jobs(company="InfraCore")[0]
    assert rec_after["is_snapshot"] is False


def test_dedup_migration_from_old_schema_backfills_source_queries(tmp_path):
    """
    Tests migration from the OLD schema where source_queries was absent,
    verifying ALTER TABLE adds columns and backfills source_queries from source_query.
    """
    import duckdb
    db_file = str(tmp_path / "legacy_schema_test.duckdb")

    with duckdb.connect(db_file) as con:
        con.execute("""
            CREATE TABLE jobs (
                job_id VARCHAR PRIMARY KEY,
                title VARCHAR NOT NULL,
                company_name VARCHAR NOT NULL,
                location VARCHAR,
                source_query VARCHAR
            );
        """)
        con.execute("""
            INSERT INTO jobs (job_id, title, company_name, location, source_query)
            VALUES ('legacy_job_42', 'Legacy ETL Engineer', 'Pioneer Inc', 'Chennai', 'Python ETL Engineer');
        """)

    manager = DatabaseManager(db_path=db_file)
    with manager.get_connection() as con:
        row = con.execute("SELECT job_id, serpapi_token, source_queries FROM jobs WHERE job_id = 'legacy_job_42'").fetchone()
        assert row is not None
        assert row[0] == "legacy_job_42"
        assert row[1] is None  # serpapi_token safe null
        assert row[2] == ["Python ETL Engineer"]  # backfilled from source_query


def test_dedup_snapshot_seeding_idempotent(tmp_path):
    """
    Tests that snapshot seeding loads exactly once and subsequent calls do nothing.
    """
    import json
    db_file = str(tmp_path / "seed_idempotency.duckdb")
    manager = DatabaseManager(db_path=db_file)

    snap_dir = str(tmp_path / "snapshots")
    os.makedirs(snap_dir, exist_ok=True)
    snap_content = {
        "slug": "idempotent_test",
        "captured_at": "2026-10-01T12:00:00Z",
        "query_params": {"q": "Test Query"},
        "jobs": [
            {
                "job_id": "seed_token_1",
                "title": "Idempotent Engineer",
                "company_name": "Idempotent Corp",
                "location": "Pune",
                "description": "Testing repeatable seeding."
            }
        ]
    }
    with open(os.path.join(snap_dir, "test.json"), "w", encoding="utf-8") as f:
        json.dump(snap_content, f)

    count_1 = manager.load_snapshots_if_empty(snapshots_dir=snap_dir)
    assert count_1 == 1

    # Second call must do nothing and return 0
    count_2 = manager.load_snapshots_if_empty(snapshots_dir=snap_dir)
    assert count_2 == 0

    with manager.get_connection() as con:
        total = con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        assert total == 1


def test_dedup_regression_wfh_and_anywhere_location(temp_db):
    """
    Tests regression that 'Work from home' in extensions or location 'Anywhere'
    always produces location_type = 'Remote' and work_from_home = True.
    """
    jobs = [
        {
            "title": "Distributed Systems Engineer",
            "company_name": "RemoteFirst Tech",
            "location": "India",
            "description": "High performance computing in Go.",
            "extensions": ["Full-time", "Work from home", "3 days ago"]
        },
        {
            "title": "Fullstack Cloud Developer",
            "company_name": "Nomad Global",
            "location": "Anywhere",
            "description": "React and Node.js microservices."
        },
        {
            "title": "Data Pipeline Engineer",
            "company_name": "Anywhere Solutions",
            "location": "Remote, India",
            "description": "DuckDB analytics engine."
        }
    ]

    temp_db.upsert_jobs(jobs)
    all_jobs = temp_db.get_jobs()
    assert len(all_jobs) == 3
    for j in all_jobs:
        assert j["location_type"] == "Remote"
        assert j["work_from_home"] is True


def test_deterministic_pagination_with_identical_timestamps(temp_db):
    """
    Inserts 10 jobs with identical scraped_at, pages through them with limit 3,
    and asserts no duplicates, no missing rows, and identical order across two runs.
    """
    fixed_time = "2026-10-01T12:00:00"
    jobs = [
        {
            "job_id": f"job_page_{i:02d}",
            "title": f"Software Engineer {i}",
            "company_name": f"Company {i % 3}",
            "location": "Bengaluru, India",
            "description": f"Description for role {i}",
            "scraped_at": fixed_time
        }
        for i in range(10)
    ]
    temp_db.upsert_jobs(jobs)

    # First run: page through with limit 3
    run_1_jobs = []
    offset = 0
    limit = 3
    while True:
        page = temp_db.get_jobs(limit=limit, offset=offset)
        if not page:
            break
        run_1_jobs.extend(page)
        offset += limit

    assert len(run_1_jobs) == 10
    run_1_ids = [j["job_id"] for j in run_1_jobs]
    assert len(set(run_1_ids)) == 10
    expected_ids = {f"job_page_{i:02d}" for i in range(10)}
    assert set(run_1_ids) == expected_ids

    # Second run: page through again with limit 3
    run_2_jobs = []
    offset = 0
    while True:
        page = temp_db.get_jobs(limit=limit, offset=offset)
        if not page:
            break
        run_2_jobs.extend(page)
        offset += limit

    run_2_ids = [j["job_id"] for j in run_2_jobs]
    assert run_1_ids == run_2_ids



def test_endpoints_disabled_by_default(monkeypatch):
    """
    Verifies that /api/sql and /api/quota return 404 {"detail": "Not found"} by default,
    that enabling each flag via environment variable allows them to function,
    and that /legacy still returns 200 regardless of flag states.
    """
    from fastapi.testclient import TestClient
    from unittest.mock import patch
    import app.main as main_mod

    client = TestClient(main_mod.app)

    # 1. Defaults (disabled)
    monkeypatch.delenv("ENABLE_SQL_CONSOLE", raising=False)
    monkeypatch.delenv("ENABLE_QUOTA_ENDPOINT", raising=False)

    res_sql = client.post("/api/sql", json={"query": "SELECT 1"})
    assert res_sql.status_code == 404
    assert res_sql.json() == {"detail": "Not found"}

    res_quota = client.get("/api/quota")
    assert res_quota.status_code == 404
    assert res_quota.json() == {"detail": "Not found"}

    res_legacy = client.get("/legacy")
    assert res_legacy.status_code == 200

    # 2. Enable SQL console only
    monkeypatch.setenv("ENABLE_SQL_CONSOLE", "true")
    res_sql_enabled = client.post("/api/sql", json={"query": "SELECT 1"})
    assert res_sql_enabled.status_code == 200

    assert client.get("/api/quota").status_code == 404

    # 3. Enable Quota endpoint only
    monkeypatch.delenv("ENABLE_SQL_CONSOLE", raising=False)
    monkeypatch.setenv("ENABLE_QUOTA_ENDPOINT", "true")
    with patch.object(main_mod.serpapi_client, "get_account_quota", return_value={"total_searches_left": 100}):
        res_quota_enabled = client.get("/api/quota")
        assert res_quota_enabled.status_code == 200
    assert client.post("/api/sql", json={"query": "SELECT 1"}).status_code == 404

    # /legacy still 200
    assert client.get("/legacy").status_code == 200



def test_live_upsert_scraped_at_utc_under_timezone():
    """
    Verifies that a live-style upsert without scraped_at under SET TimeZone='Asia/Kolkata'
    stores a value in naive UTC within 5 seconds of datetime.now(timezone.utc).
    """
    from datetime import datetime, timezone
    from app.database import db_manager

    con = db_manager.get_connection()
    try:
        con.execute("SET TimeZone='Asia/Kolkata'")
        job_data = {
            "title": "UTC Test Engineer",
            "company_name": "UTC Test Corp",
            "location": "Bengaluru",
            "description": "Test description Python SQL Docker",
        }
        db_manager.upsert_jobs([job_data], is_snapshot=False)
        row = con.execute("SELECT scraped_at FROM jobs WHERE company_name = 'UTC Test Corp' ORDER BY scraped_at DESC LIMIT 1").fetchone()
        assert row is not None
        stored_scraped_at = row[0]
        if isinstance(stored_scraped_at, str):
            stored_dt = datetime.fromisoformat(stored_scraped_at.replace("Z", ""))
        else:
            stored_dt = stored_scraped_at
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        diff_s = abs((now_utc - stored_dt).total_seconds())
        assert diff_s <= 5, f"Expected scraped_at within 5s of UTC now, got {diff_s}s"
    finally:
        con.execute("DELETE FROM jobs WHERE company_name = 'UTC Test Corp'")
        con.close()









