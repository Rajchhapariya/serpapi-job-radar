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


@pytest.fixture(autouse=True)
def clear_rate_limit_histories():
    """Autouse fixture to ensure rate limit state does not leak between tests."""
    from app.main import ip_unlock_history, ip_request_history
    ip_unlock_history.clear()
    ip_request_history.clear()
    yield
    ip_unlock_history.clear()
    ip_request_history.clear()


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


# ==================== TEST E: ROLE FILTER, CORPUS DISCLOSURE & RATE LIMIT ====================

def test_role_filter_on_fixture(temp_unlock_con):
    # Test on fixture jobs:
    # J1: "Backend Dev 1" -> backend
    # J2: "Cloud Dev 2" -> devops_cloud
    # J3: "Platform Dev 3" -> no match (platform dev != platform engineer)
    # J4: "Data Analyst 4" -> data
    # J5: "Enterprise Dev 5" -> no match
    # J6: "Fullstack Dev 6" -> frontend_fullstack
    # J7: "Junior Dev 7" -> ineligible (2 skills)
    # Unfiltered eligible = 6

    # 1. Unfiltered eligible_jobs = 6
    res_default = compute_skill_unlocks(temp_unlock_con, ["Python", "SQL"], threshold=60, min_job_skills=3)
    assert res_default["baseline"]["eligible_jobs"] == 6

    # 2. Role filter reduces eligible_jobs on the fixture
    res_backend = compute_skill_unlocks(temp_unlock_con, ["Python", "SQL"], threshold=60, min_job_skills=3, role="backend")
    assert res_backend["baseline"]["eligible_jobs"] == 1

    res_data = compute_skill_unlocks(temp_unlock_con, ["Python", "SQL"], threshold=60, min_job_skills=3, role="data")
    assert res_data["baseline"]["eligible_jobs"] == 1

    res_devops = compute_skill_unlocks(temp_unlock_con, ["Python", "SQL"], threshold=60, min_job_skills=3, role="devops_cloud")
    assert res_devops["baseline"]["eligible_jobs"] == 1

    res_fe = compute_skill_unlocks(temp_unlock_con, ["Python", "SQL"], threshold=60, min_job_skills=3, role="frontend_fullstack")
    assert res_fe["baseline"]["eligible_jobs"] == 1


def test_role_filter_api_validation_and_behavior():
    # 1. Invalid role -> 422 on /api/unlock
    res_inv_unlock = client.post("/api/unlock", json={"skills": ["Python", "SQL"], "role": "cybersecurity"})
    assert res_inv_unlock.status_code == 422

    # 2. Invalid role -> 422 on /api/fit
    res_inv_fit = client.post("/api/fit", json={"skills": ["Python", "SQL"], "role": "invalid_role"})
    assert res_inv_fit.status_code == 422

    # 3. Valid role filters work on live API
    res_be = client.post("/api/unlock", json={"skills": ["Python", "SQL"], "role": "backend"})
    res_all = client.post("/api/unlock", json={"skills": ["Python", "SQL"]})
    assert res_be.status_code == 200
    assert res_all.status_code == 200
    assert res_be.json()["baseline"]["eligible_jobs"] < res_all.json()["baseline"]["eligible_jobs"]

    # 4. Roles endpoint GET /api/roles
    res_roles = client.get("/api/roles")
    assert res_roles.status_code == 200
    data_roles = res_roles.json()
    assert "roles" in data_roles
    assert "any_role_unmatched" in data_roles
    assert isinstance(data_roles["any_role_unmatched"], int)
    role_keys = [r["role"] for r in data_roles["roles"]]
    assert set(role_keys) == {"backend", "data", "ml_ai", "devops_cloud", "frontend_fullstack"}
    for r in data_roles["roles"]:
        assert "label" in r
        assert "jobs" in r
        assert isinstance(r["jobs"], int)


def test_corpus_disclosure_fields():
    # Verify distinct_queries and sample_note are present and correctly formatted
    res_u = client.post("/api/unlock", json={"skills": ["Python", "SQL"]})
    assert res_u.status_code == 200
    corpus_u = res_u.json()["corpus"]
    assert "distinct_queries" in corpus_u
    assert "sample_note" in corpus_u
    assert isinstance(corpus_u["distinct_queries"], int)
    expected_note = f"Jobs captured from Google Jobs searches in India using {corpus_u['distinct_queries']} distinct query phrases across several cities and remote. Not a random sample of the market."
    assert corpus_u["sample_note"] == expected_note

    res_f = client.post("/api/fit", json={"skills": ["Python", "SQL"]})
    assert res_f.status_code == 200
    corpus_f = res_f.json()["corpus"]
    assert "distinct_queries" in corpus_f
    assert "sample_note" in corpus_f
    assert corpus_f["sample_note"] == expected_note


def test_role_regex_tightening_boundary_titles():
    """
    Verifies regex tightening on boundary titles:
    - 'Rapid Prototyping Engineer' does NOT match backend
    - 'Cloud Storage Engineer' does NOT match ml_ai
    - 'ETL Developer' matches data
    - 'RAG Engineer' matches ml_ai
    - 'REST API Developer' matches backend
    - 'Reactive Systems Engineer' does NOT match frontend_fullstack
    - 'ReactJS Developer' matches frontend_fullstack
    Both in Python re and DuckDB regexp_matches.
    """
    import re
    from app.unlock import ROLE_PATTERNS

    boundary_cases = [
        ("Rapid Prototyping Engineer", "backend", False),
        ("Cloud Storage Engineer", "ml_ai", False),
        ("ETL Developer", "data", True),
        ("RAG Engineer", "ml_ai", True),
        ("REST API Developer", "backend", True),
        ("Reactive Systems Engineer", "frontend_fullstack", False),
        ("ReactJS Developer", "frontend_fullstack", True),
    ]

    con = duckdb.connect()
    for title, role, expected in boundary_cases:
        pat = ROLE_PATTERNS[role]
        py_match = bool(re.search(pat, title, re.IGNORECASE))
        assert py_match is expected, f"Python match failed for '{title}' on {role}: expected {expected}, got {py_match}"
        duck_match = bool(con.execute("SELECT regexp_matches(?, ?, 'i')", [title, pat]).fetchone()[0])
        assert duck_match is expected, f"DuckDB match failed for '{title}' on {role}: expected {expected}, got {duck_match}"


def test_rate_limiter_for_unlock_endpoints(monkeypatch):
    import app.main as main_mod
    monkeypatch.setattr(main_mod, "UNLOCK_RATE_LIMIT", 5)
    main_mod.ip_unlock_history.clear()

    # Requests 1 to 5 should succeed
    for _ in range(5):
        resp = client.post("/api/unlock", json={"skills": ["Python", "SQL"]})
        assert resp.status_code == 200

    # Request 6 (N+1) should return 429
    resp_blocked = client.post("/api/unlock", json={"skills": ["Python", "SQL"]})
    assert resp_blocked.status_code == 429
    assert "Rate limit exceeded" in resp_blocked.json()["detail"]

