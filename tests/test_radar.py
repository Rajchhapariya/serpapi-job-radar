import pytest
import os
import tempfile
from unittest.mock import patch
from app.database import DatabaseManager, TRACKED_SKILLS
from app.serpapi_client import SerpApiClient, MOCK_JOBS


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
    assert records[0]["salary"] == "INR 14,00,000"


def test_query_filtering_location_remote(temp_db):
    temp_db.upsert_jobs(MOCK_JOBS)
    remote_jobs = temp_db.get_jobs(location_type="Remote")
    assert len(remote_jobs) > 0
    for j in remote_jobs:
        assert j["work_from_home"] is True or "remote" in j["location"].lower()


def test_query_filtering_location_onsite(temp_db):
    temp_db.upsert_jobs(MOCK_JOBS)
    onsite_jobs = temp_db.get_jobs(location_type="On-site")
    assert len(onsite_jobs) > 0
    for j in onsite_jobs:
        assert j["work_from_home"] is False
        assert "remote" not in j["location"].lower()


def test_query_filtering_has_salary(temp_db):
    temp_db.upsert_jobs(MOCK_JOBS)
    salary_jobs = temp_db.get_jobs(has_salary=True)
    assert len(salary_jobs) > 0
    for j in salary_jobs:
        assert j["salary"] is not None and j["salary"].strip() != ""


def test_query_sorting_options(temp_db):
    temp_db.upsert_jobs(MOCK_JOBS)

    # Sort by company
    by_company = temp_db.get_jobs(sort_by="company")
    company_names = [j["company_name"].lower() for j in by_company]
    assert company_names == sorted(company_names)

    # Sort by title
    by_title = temp_db.get_jobs(sort_by="title")
    titles = [j["title"].lower() for j in by_title]
    assert titles == sorted(titles)


def test_pagination_limits_and_offsets(temp_db):
    temp_db.upsert_jobs(MOCK_JOBS)
    page_1 = temp_db.get_jobs(limit=2, offset=0)
    page_2 = temp_db.get_jobs(limit=2, offset=2)

    assert len(page_1) == 2
    assert len(page_2) == 2
    assert page_1[0]["job_id"] != page_2[0]["job_id"]

    # Offset beyond total
    empty_page = temp_db.get_jobs(limit=10, offset=100)
    assert len(empty_page) == 0


def test_sql_injection_safety(temp_db):
    temp_db.upsert_jobs(MOCK_JOBS)
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
    temp_db.upsert_jobs(MOCK_JOBS)
    analytics = temp_db.get_analytics()

    assert analytics["total_jobs"] == len(MOCK_JOBS)
    assert len(analytics["top_skills"]) > 0
    assert len(analytics["top_platforms"]) > 0

    platforms = [p["platform"] for p in analytics["top_platforms"]]
    assert any(p in ["LinkedIn", "Greenhouse", "Lever", "Workday", "Indeed"] for p in platforms)


def test_resume_matching_comprehensive(temp_db):
    temp_db.upsert_jobs(MOCK_JOBS)
    resume = "Senior Engineer with strong Python, DuckDB, SQL, Docker, and PostgreSQL expertise."
    match_result = temp_db.match_resume(resume)

    assert "Python" in match_result["matched_skills"]
    assert "DuckDB" in match_result["matched_skills"]
    assert "Docker" in match_result["matched_skills"]
    assert match_result["match_score_percentage"] > 0
    assert len(match_result["recommended_jobs"]) > 0


def test_resume_matching_zero_match(temp_db):
    temp_db.upsert_jobs(MOCK_JOBS)
    resume = "Certified accountant with deep expertise in auditing and tax balance sheets."
    match_result = temp_db.match_resume(resume)

    assert match_result["matched_skills"] == []
    assert match_result["match_score_percentage"] == 0
    assert len(match_result["missing_skills"]) > 0


def test_serpapi_client_unconfigured_fallback():
    client = SerpApiClient(api_key="your_unconfigured_key")
    res = client.fetch_jobs(query="Python", location="India", num_results=5)

    assert res["source"] == "mock_demo"
    assert len(res["jobs"]) > 0


def test_serpapi_client_network_error_graceful_recovery():
    client = SerpApiClient(api_key="actual_secret_token_123")

    with patch("requests.get") as mock_get:
        mock_get.side_effect = Exception("Simulated connection timeout")
        res = client.fetch_jobs(query="Python", location="India", num_results=5)

        assert res["source"] == "fallback_on_error"
        assert len(res["jobs"]) == len(MOCK_JOBS)
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


def test_search_with_recency_filter():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    # Valid date_posted options: today, 3days, week, month
    valid_payload = {
        "query": "Python Engineer",
        "location": "India",
        "date_posted": "week"
    }
    response = client.post("/api/search", json=valid_payload)
    assert response.status_code == 200
    data = response.json()
    assert "retrieved_count" in data

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





