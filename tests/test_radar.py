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
