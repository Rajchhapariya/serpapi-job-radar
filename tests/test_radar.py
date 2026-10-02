import pytest
import os
import tempfile
from app.database import DatabaseManager, TRACKED_SKILLS
from app.serpapi_client import SerpApiClient, MOCK_JOBS


@pytest.fixture
def temp_db():
    # Create temporary database file for test isolation
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

    # Query all
    results = temp_db.get_jobs()
    assert len(results) == 2

    # Query with remote filter
    remote_results = temp_db.get_jobs(location_type="Remote")
    assert len(remote_results) == 1
    assert remote_results[0]["job_id"] == "test_01"

    # Query with keyword
    fastapi_results = temp_db.get_jobs(keyword="FastAPI")
    assert len(fastapi_results) == 1
    assert fastapi_results[0]["company_name"] == "Acme Inc"


def test_analytics_computation(temp_db):
    temp_db.upsert_jobs(MOCK_JOBS)
    analytics = temp_db.get_analytics()

    assert analytics["total_jobs"] == len(MOCK_JOBS)
    assert analytics["remote_jobs"] > 0
    assert len(analytics["top_skills"]) > 0
    assert len(analytics["top_platforms"]) > 0

    skills = [s["skill"] for s in analytics["top_skills"]]
    assert "Python" in skills or "DuckDB" in skills or "Docker" in skills


def test_resume_matching(temp_db):
    temp_db.upsert_jobs(MOCK_JOBS)

    # Resume with Python, DuckDB, PostgreSQL, Docker
    resume = "Experienced software engineer specializing in Python, DuckDB, PostgreSQL, and Docker."
    match_result = temp_db.match_resume(resume)

    assert "Python" in match_result["matched_skills"]
    assert "DuckDB" in match_result["matched_skills"]
    assert match_result["match_score_percentage"] > 0
    assert len(match_result["recommended_jobs"]) > 0


def test_serpapi_client_fallback():
    client = SerpApiClient(api_key="your_unconfigured_key")
    res = client.fetch_jobs(query="Python", location="India", num_results=5)

    assert res["source"] == "mock_demo"
    assert len(res["jobs"]) > 0
