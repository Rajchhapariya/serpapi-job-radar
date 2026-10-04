"""
tests/test_unlock.py

Comprehensive tests for Skill Unlock Engine and Per-Job Fit scoring:
- Test A: Manual Fixture verification (baseline, unlocks exact order, path exact order)
- Test B: Parity check: SQL implementation == Python reference on fixture and real corpus
- Test C: Validation boundaries, 422 errors, ignored_skills, location_type, SQL injection safety, deterministic example_jobs
- Test D: Fit scoring endpoint and sample resume endpoint
"""

import os
import duckdb
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import db_manager, extract_skills_from_text
from app.unlock import (
    compute_skill_unlocks,
    compute_job_fit,
    python_reference_unlock,
    parse_and_validate_skills_input,
    get_corpus_stats
)

client = TestClient(app)

FIXTURE_JOBS = [
    {
        "job_id": "J1",
        "title": "Backend Dev 1",
        "company_name": "Company A",
        "location": "Bengaluru",
        "location_type": "On-site",
        "portal_count": 2,
        "skills_required": ["Python", "SQL", "Docker"],
        "scraped_at": "2026-10-01 10:00:00",
        "is_snapshot": True
    },
    {
        "job_id": "J2",
        "title": "Cloud Dev 2",
        "company_name": "Company B",
        "location": "Remote",
        "location_type": "Remote",
        "portal_count": 1,
        "skills_required": ["Python", "Docker", "AWS"],
        "scraped_at": "2026-10-01 10:00:00",
        "is_snapshot": True
    },
    {
        "job_id": "J3",
        "title": "Platform Dev 3",
        "company_name": "Company C",
        "location": "Remote",
        "location_type": "Remote",
        "portal_count": 3,
        "skills_required": ["Python", "Docker", "Kubernetes", "AWS"],
        "scraped_at": "2026-10-01 10:00:00",
        "is_snapshot": True
    },
    {
        "job_id": "J4",
        "title": "Data Analyst 4",
        "company_name": "Company D",
        "location": "Bengaluru",
        "location_type": "On-site",
        "portal_count": 1,
        "skills_required": ["SQL", "Tableau", "Excel"],
        "scraped_at": "2026-10-01 10:00:00",
        "is_snapshot": True
    },
    {
        "job_id": "J5",
        "title": "Enterprise Dev 5",
        "company_name": "Company E",
        "location": "Hyderabad",
        "location_type": "On-site",
        "portal_count": 4,
        "skills_required": ["Java", "Spring Boot", "SQL", "AWS"],
        "scraped_at": "2026-10-01 10:00:00",
        "is_snapshot": True
    },
    {
        "job_id": "J6",
        "title": "Fullstack Dev 6",
        "company_name": "Company F",
        "location": "Remote",
        "location_type": "Remote",
        "portal_count": 2,
        "skills_required": ["Python", "SQL", "Git", "Docker", "AWS"],
        "scraped_at": "2026-10-01 10:00:00",
        "is_snapshot": True
    },
    {
        "job_id": "J7",
        "title": "Junior Dev 7",
        "company_name": "Company G",
        "location": "Pune",
        "location_type": "On-site",
        "portal_count": 1,
        "skills_required": ["Python", "Docker"],
        "scraped_at": "2026-10-01 10:00:00",
        "is_snapshot": True
    }
]


@pytest.fixture
def temp_unlock_con():
    """In-memory DuckDB connection pre-populated with FIXTURE_JOBS."""
    con = duckdb.connect(":memory:")
    con.execute("""
        CREATE TABLE jobs (
            job_id VARCHAR,
            title VARCHAR,
            company_name VARCHAR,
            location VARCHAR,
            location_type VARCHAR,
            portal_count INTEGER,
            skills_required VARCHAR[],
            scraped_at TIMESTAMP,
            is_snapshot BOOLEAN
        );
    """)
    for j in FIXTURE_JOBS:
        con.execute("""
            INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?::TIMESTAMP, ?);
        """, [
            j["job_id"],
            j["title"],
            j["company_name"],
            j["location"],
            j["location_type"],
            j["portal_count"],
            j["skills_required"],
            j["scraped_at"],
            j["is_snapshot"]
        ])
    yield con
    con.close()


# ==================== TEST A: EXACT SPECIFICATION VERIFICATION ====================

def test_a_fixture_exact_specification(temp_unlock_con):
    R = ["Python", "SQL"]
    threshold = 60
    min_job_skills = 3

    res = compute_skill_unlocks(
        con=temp_unlock_con,
        R=R,
        threshold=threshold,
        min_job_skills=min_job_skills,
        top_n=10,
        table_name="jobs"
    )

    # 1. Baseline
    assert res["baseline"]["eligible_jobs"] == 6
    assert res["baseline"]["matched_jobs"] == 1

    # 2. Unlocks in exact order
    expected_unlocks = [
        ("AWS", 2, 4),
        ("Docker", 2, 4),
        ("Excel", 1, 1),
        ("Git", 1, 1),
        ("Tableau", 1, 1)
    ]
    actual_unlocks = [(u["skill"], u["unlocks"], u["demand"]) for u in res["unlocks"]]
    assert actual_unlocks == expected_unlocks

    # Assert absent skills (unlocks == 0)
    returned_skills = {u["skill"] for u in res["unlocks"]}
    assert "Kubernetes" not in returned_skills
    assert "Java" not in returned_skills
    assert "Spring Boot" not in returned_skills

    # 3. Path in exact order
    expected_path = [
        {"step": 1, "skill": "AWS", "unlocks": 2, "cumulative_gain": 2},
        {"step": 2, "skill": "Docker", "unlocks": 1, "cumulative_gain": 3},
        {"step": 3, "skill": "Excel", "unlocks": 1, "cumulative_gain": 4}
    ]
    assert res["path"] == expected_path


# ==================== TEST B: SQL VS PYTHON REFERENCE EQUALITY ====================

def test_b_sql_vs_python_reference_fixture(temp_unlock_con):
    R_cases = [
        ["Python", "SQL"],
        ["Java", "Spring Boot", "SQL"],
        ["Excel", "SQL", "Tableau"]
    ]
    for R in R_cases:
        sql_res = compute_skill_unlocks(temp_unlock_con, R, threshold=60, min_job_skills=3, top_n=10)
        py_res = python_reference_unlock(FIXTURE_JOBS, R, threshold=60, min_job_skills=3, top_n=10)

        assert sql_res["baseline"] == py_res["baseline"]
        sql_tuples = [(u["skill"], u["unlocks"], u["demand"]) for u in sql_res["unlocks"]]
        py_tuples = [(u["skill"], u["unlocks"], u["demand"]) for u in py_res["unlocks"]]
        assert sql_tuples == py_tuples
        assert sql_res["path"] == py_res["path"]

        # Check example_jobs parity
        for s_u, p_u in zip(sql_res["unlocks"], py_res["unlocks"]):
            assert s_u["example_jobs"] == p_u["example_jobs"]


def test_b_sql_vs_python_reference_real_corpus():
    with open("data/sample_resume.txt", "r", encoding="utf-8") as f:
        sample_text = f.read()
    sample_skills = extract_skills_from_text(sample_text)

    test_cases = [
        ("sample_resume", sample_skills),
        ("java_skills", ["Java", "Spring Boot", "SQL"]),
        ("analyst_skills", ["Excel", "SQL", "Tableau"])
    ]

    with db_manager.get_connection() as con:
        all_jobs_raw = con.execute("SELECT job_id, title, company_name, location_type, skills_required FROM jobs").fetchall()
        jobs_dicts = [
            {"job_id": r[0], "title": r[1], "company_name": r[2], "location_type": r[3], "skills_required": r[4]}
            for r in all_jobs_raw
        ]

        for name, R in test_cases:
            sql_res = compute_skill_unlocks(con, R, threshold=60, min_job_skills=3, top_n=10)
            py_res = python_reference_unlock(jobs_dicts, R, threshold=60, min_job_skills=3, top_n=10)

            assert sql_res["baseline"] == py_res["baseline"], f"Baseline mismatch on {name}"
            sql_tuples = [(u["skill"], u["unlocks"], u["demand"]) for u in sql_res["unlocks"]]
            py_tuples = [(u["skill"], u["unlocks"], u["demand"]) for u in py_res["unlocks"]]
            assert sql_tuples == py_tuples, f"Unlocks mismatch on {name}"
            assert sql_res["path"] == py_res["path"], f"Path mismatch on {name}"
            assert sql_res["all_unlocks_count"] == py_res["all_unlocks_count"]


# ==================== TEST C: VALIDATION BOUNDARIES & SAFETY ====================

def test_c_validation_boundaries():
    # 1. Neither resume_text nor skills -> 422
    res1 = client.post("/api/unlock", json={"threshold": 60})
    assert res1.status_code == 422

    # 2. Both resume_text and skills -> 422
    res2 = client.post("/api/unlock", json={"resume_text": "Python SQL developer", "skills": ["Python"]})
    assert res2.status_code == 422

    # 3. No recognized skills -> 422 with clear message
    res3 = client.post("/api/unlock", json={"skills": ["UnknownSkillOne", "NonexistentFramework"]})
    assert res3.status_code == 422
    assert "No recognized skills found" in res3.json()["detail"]

    res3b = client.post("/api/unlock", json={"resume_text": "Hello world this text contains zero tech skills"})
    assert res3b.status_code == 422
    assert "No recognized skills found" in res3b.json()["detail"]

    # 4. Threshold boundaries (0 and 101 -> 422)
    res4a = client.post("/api/unlock", json={"skills": ["Python"], "threshold": 0})
    assert res4a.status_code == 422

    res4b = client.post("/api/unlock", json={"skills": ["Python"], "threshold": 101})
    assert res4b.status_code == 422

    # 5. Ignored skills echo
    res5 = client.post("/api/unlock", json={"skills": ["Python", "FakeSkill", "K8s", "AnotherFake"]})
    assert res5.status_code == 200
    data5 = res5.json()
    assert "Python" in data5["resume_skills"]
    assert "Kubernetes" in data5["resume_skills"]
    assert "FakeSkill" in data5["ignored_skills"]
    assert "AnotherFake" in data5["ignored_skills"]

    # 6. Location type filter changes eligible jobs
    res_all = client.post("/api/unlock", json={"skills": ["Python", "SQL"]})
    res_remote = client.post("/api/unlock", json={"skills": ["Python", "SQL"], "location_type": "Remote"})
    res_onsite = client.post("/api/unlock", json={"skills": ["Python", "SQL"], "location_type": "On-site"})
    assert res_all.status_code == 200
    assert res_remote.status_code == 200
    assert res_onsite.status_code == 200
    assert res_remote.json()["baseline"]["eligible_jobs"] < res_all.json()["baseline"]["eligible_jobs"]
    assert res_onsite.json()["baseline"]["eligible_jobs"] < res_all.json()["baseline"]["eligible_jobs"]

    # 7. Skill name with quotes or SQL fragment handled safely
    malicious = ["Python", "'; DROP TABLE jobs; --", "SQL' OR '1'='1", "Docker') UNION SELECT 1--"]
    res_safe = client.post("/api/unlock", json={"skills": malicious})
    assert res_safe.status_code == 200
    data_safe = res_safe.json()
    assert "Python" in data_safe["resume_skills"]
    assert "'; DROP TABLE jobs; --" in data_safe["ignored_skills"]

    # 8. Example jobs ordering is deterministic
    res_ex = client.post("/api/unlock", json={"skills": ["Python", "SQL"]})
    assert res_ex.status_code == 200
    for u in res_ex.json()["unlocks"]:
        ex_jobs = u["example_jobs"]
        assert len(ex_jobs) <= 3
        for i in range(len(ex_jobs) - 1):
            curr = ex_jobs[i]
            nxt = ex_jobs[i + 1]
            assert (curr["match_before"] > nxt["match_before"]) or (
                curr["match_before"] == nxt["match_before"] and curr["job_id"] <= nxt["job_id"]
            )


# ==================== TEST D: FIT ENDPOINT & SAMPLE RESUME ====================

def test_d_fit_and_sample_resume():
    # 1. Sample resume endpoint
    res_sr = client.get("/api/sample-resume")
    assert res_sr.status_code == 200
    content = res_sr.json().get("text", "")
    assert content.startswith("SAMPLE RESUME")
    assert len(content.split()) >= 100

    # 2. Fit endpoint scoring and sorting
    res_fit = client.post("/api/fit", json={"skills": ["Python", "SQL", "FastAPI"], "limit": 20})
    assert res_fit.status_code == 200
    fit_data = res_fit.json()
    assert "jobs" in fit_data
    assert "corpus" in fit_data
    assert len(fit_data["jobs"]) <= 20

    jobs = fit_data["jobs"]
    for j in jobs:
        assert "description" not in j  # No descriptions in payload
        assert "match_pct" in j
        assert "matched" in j
        assert "missing" in j
        assert isinstance(j["match_pct"], int)

    # Assert sorted by match_pct DESC, title ASC, job_id ASC
    for i in range(len(jobs) - 1):
        j1 = jobs[i]
        j2 = jobs[i + 1]
        k1 = (-j1["match_pct"], j1["title"], j1["job_id"])
        k2 = (-j2["match_pct"], j2["title"], j2["job_id"])
        assert k1 <= k2
