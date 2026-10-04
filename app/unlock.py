"""
app/unlock.py

Deterministic Skill Unlock Engine and Per-Job Fit Scoring using DuckDB SQL list functions.
Enforces integer math only (no float division). No LLM.
"""

import time
import re
from typing import List, Dict, Any, Optional, Tuple
from fastapi import HTTPException
from app.database import TRACKED_SKILLS, SKILL_PATTERNS, extract_skills_from_text


def resolve_skill(name: str) -> Optional[str]:
    """
    Resolves a raw or aliased skill string to a canonical skill in TRACKED_SKILLS.
    Returns canonical skill name if recognized, or None if unknown.
    """
    name_clean = str(name).strip()
    if not name_clean:
        return None

    # 'rag' lowercase must NOT match 'RAG'
    if name_clean.lower() == "rag" and name_clean != "RAG":
        return None

    # Direct canonical match (case-insensitive)
    for c in TRACKED_SKILLS:
        if c == "RAG":
            if name_clean == "RAG":
                return "RAG"
        elif name_clean.lower() == c.lower():
            return c

    # Pattern and alias map match
    for c, pat in SKILL_PATTERNS.items():
        if c == "RAG":
            if name_clean == "RAG" or re.fullmatch(r"retrieval[ -]augmented generation", name_clean, re.IGNORECASE):
                return "RAG"
        else:
            if pat.fullmatch(name_clean) or pat.search(f" {name_clean} "):
                return c

    return None


def parse_and_validate_skills_input(
    resume_text: Optional[str] = None,
    skills: Optional[List[str]] = None
) -> Tuple[List[str], List[str]]:
    """
    Enforces XOR on resume_text vs skills, extracts or resolves canonical skills,
    and returns (canonical_resume_skills, ignored_skills).
    """
    if (resume_text is None and skills is None) or (resume_text is not None and skills is not None):
        raise HTTPException(
            status_code=422,
            detail="Provide either 'resume_text' or 'skills', not both or neither."
        )

    if resume_text is not None:
        if len(resume_text) > 50000:
            raise HTTPException(
                status_code=422,
                detail="resume_text exceeds maximum permitted length of 50000 characters."
            )
        extracted = extract_skills_from_text(resume_text)
        if not extracted:
            raise HTTPException(
                status_code=422,
                detail="No recognized skills found in resume_text."
            )
        return extracted, []

    if skills is not None:
        if len(skills) > 100:
            raise HTTPException(
                status_code=422,
                detail="skills list exceeds maximum limit of 100 items."
            )
        r_skills = []
        ignored = []
        seen = set()
        for s in skills:
            resolved = resolve_skill(s)
            if resolved:
                if resolved not in seen:
                    seen.add(resolved)
                    r_skills.append(resolved)
            else:
                ignored.append(str(s))

        if not r_skills:
            raise HTTPException(
                status_code=422,
                detail="No recognized skills found in skills list."
            )
        return r_skills, ignored


ROLE_PATTERNS = {
    "backend": r"backend|back-end|python developer|java developer|software engineer|\bapis?\b",
    "data": r"data (engineer|analyst|scientist)|analytics|\betl\b|snowflake|\bbi\b",
    "ml_ai": r"machine learning|\bml\b|\bai\b|llm|nlp|deep learning|gen ?ai|\brag\b",
    "devops_cloud": r"devops|\bsre\b|site reliability|cloud|infrastructure|platform engineer",
    "frontend_fullstack": r"front-?end|full[ -]?stack|\breact(js)?\b|\bui\b"
}

ROLE_LABELS = {
    "backend": "Backend",
    "data": "Data",
    "ml_ai": "ML / AI",
    "devops_cloud": "DevOps & Cloud",
    "frontend_fullstack": "Frontend & Fullstack"
}

ALLOWED_ROLES = set(ROLE_PATTERNS.keys())


def get_roles_summary(con, table_name: str = "jobs") -> Dict[str, Any]:
    """
    Computes job counts per role over eligible-by-default jobs (min_job_skills=3),
    plus 'any_role_unmatched': count of eligible jobs matching none of the roles.
    """
    query = f"""
        SELECT 
            COUNT(*) FILTER (WHERE regexp_matches(title, ?, 'i')) AS cnt_backend,
            COUNT(*) FILTER (WHERE regexp_matches(title, ?, 'i')) AS cnt_data,
            COUNT(*) FILTER (WHERE regexp_matches(title, ?, 'i')) AS cnt_ml_ai,
            COUNT(*) FILTER (WHERE regexp_matches(title, ?, 'i')) AS cnt_devops_cloud,
            COUNT(*) FILTER (WHERE regexp_matches(title, ?, 'i')) AS cnt_frontend_fullstack,
            COUNT(*) FILTER (WHERE NOT (
                regexp_matches(title, ?, 'i') OR 
                regexp_matches(title, ?, 'i') OR 
                regexp_matches(title, ?, 'i') OR 
                regexp_matches(title, ?, 'i') OR 
                regexp_matches(title, ?, 'i')
            )) AS any_role_unmatched
        FROM {table_name}
        WHERE len(list_distinct(skills_required)) >= 3
    """
    pats = [
        ROLE_PATTERNS["backend"],
        ROLE_PATTERNS["data"],
        ROLE_PATTERNS["ml_ai"],
        ROLE_PATTERNS["devops_cloud"],
        ROLE_PATTERNS["frontend_fullstack"]
    ]
    params = pats + pats
    row = con.execute(query, params).fetchone()
    if not row:
        return {
            "roles": [{"role": r, "label": ROLE_LABELS[r], "jobs": 0} for r in ROLE_PATTERNS],
            "any_role_unmatched": 0
        }

    return {
        "roles": [
            {"role": "backend", "label": ROLE_LABELS["backend"], "jobs": row[0] or 0},
            {"role": "data", "label": ROLE_LABELS["data"], "jobs": row[1] or 0},
            {"role": "ml_ai", "label": ROLE_LABELS["ml_ai"], "jobs": row[2] or 0},
            {"role": "devops_cloud", "label": ROLE_LABELS["devops_cloud"], "jobs": row[3] or 0},
            {"role": "frontend_fullstack", "label": ROLE_LABELS["frontend_fullstack"], "jobs": row[4] or 0}
        ],
        "any_role_unmatched": row[5] or 0
    }


def get_corpus_stats(con, table_name: str = "jobs") -> Tuple[Dict[str, Any], float]:
    """
    Fetches corpus metrics: total jobs, date range from scraped_at, snapshot share,
    distinct_queries count, and sample_note.
    """
    t0 = time.perf_counter()
    row = con.execute(f"""
        SELECT 
            COUNT(*) AS total_jobs,
            MIN(scraped_at) AS as_of_min,
            MAX(scraped_at) AS as_of_max,
            AVG(CASE WHEN is_snapshot = TRUE THEN 1.0 ELSE 0.0 END) AS snapshot_share
        FROM {table_name}
    """).fetchone()

    distinct_queries = 0
    try:
        sq_row = con.execute(f"""
            SELECT count(DISTINCT sq) 
            FROM (SELECT unnest(source_queries) AS sq FROM {table_name})
        """).fetchone()
        if sq_row and sq_row[0] is not None:
            distinct_queries = int(sq_row[0])
    except Exception:
        distinct_queries = 0

    elapsed_ms = (time.perf_counter() - t0) * 1000

    if not row or row[0] == 0:
        return {
            "jobs": 0,
            "as_of_min": None,
            "as_of_max": None,
            "snapshot_share": 0.0,
            "distinct_queries": distinct_queries,
            "sample_note": f"Jobs captured from Google Jobs searches in India using {distinct_queries} distinct query phrases across several cities and remote. Not a random sample of the market."
        }, elapsed_ms

    return {
        "jobs": row[0],
        "as_of_min": str(row[1]) if row[1] is not None else None,
        "as_of_max": str(row[2]) if row[2] is not None else None,
        "snapshot_share": round(float(row[3] or 0.0), 4),
        "distinct_queries": distinct_queries,
        "sample_note": f"Jobs captured from Google Jobs searches in India using {distinct_queries} distinct query phrases across several cities and remote. Not a random sample of the market."
    }, elapsed_ms


def compute_skill_unlocks(
    con,
    R: List[str],
    threshold: int = 60,
    min_job_skills: int = 3,
    location_type: Optional[str] = None,
    role: Optional[str] = None,
    top_n: int = 10,
    table_name: str = "jobs"
) -> Dict[str, Any]:
    """
    Computes baseline matching, candidate skill unlocks and demand in single DuckDB SQL aggregation,
    example unlocked jobs, and greedy unlock path up to 3 steps.
    All skill values and filters are bound as query parameters.
    """
    if role is not None and role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid role '{role}'. Allowed values: {sorted(list(ALLOWED_ROLES))}"
        )

    loc_clause = ""
    loc_params: List[Any] = []
    if location_type:
        loc_clause = "AND location_type = ?"
        loc_params = [location_type]

    role_clause = ""
    role_params: List[Any] = []
    if role:
        role_clause = "AND regexp_matches(title, ?, 'i')"
        role_params = [ROLE_PATTERNS[role]]

    total_query_ms = 0.0

    # 1. Materialize eligible set in temp table with precomputed n and initial m
    t0 = time.perf_counter()
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE _req_eligible AS
        SELECT 
            job_id,
            title,
            company_name,
            location_type,
            list_distinct(skills_required) AS skills,
            len(list_distinct(skills_required)) AS n,
            len(list_intersect(list_distinct(skills_required), ?::VARCHAR[])) AS m
        FROM {table_name}
        WHERE len(list_distinct(skills_required)) >= ?
          {loc_clause}
          {role_clause}
    """, [R, min_job_skills] + loc_params + role_params)
    total_query_ms += (time.perf_counter() - t0) * 1000

    # 2. Baseline matching query
    t0 = time.perf_counter()
    base_row = con.execute("""
        SELECT 
            COUNT(*) AS eligible_jobs,
            COUNT(*) FILTER (WHERE m * 100 >= ? * n) AS matched_jobs
        FROM _req_eligible
    """, [threshold]).fetchone()
    total_query_ms += (time.perf_counter() - t0) * 1000

    eligible_jobs = base_row[0] if base_row else 0
    matched_jobs = base_row[1] if base_row else 0

    if eligible_jobs == 0:
        return {
            "baseline": {"eligible_jobs": 0, "matched_jobs": 0},
            "unlocks": [],
            "path": [],
            "all_unlocks_count": 0,
            "query_ms": round(total_query_ms, 2)
        }

    # 3. Main UNLOCK and DEMAND single SQL aggregation
    t0 = time.perf_counter()
    unlock_query = """
        SELECT 
            skill,
            COUNT(*) FILTER (WHERE m * 100 < ? * n AND (m + 1) * 100 >= ? * n) AS unlocks,
            COUNT(*) AS demand
        FROM (
            SELECT m, n, unnest(skills) AS skill FROM _req_eligible
        )
        WHERE NOT list_contains(?::VARCHAR[], skill)
        GROUP BY skill
        HAVING unlocks > 0
        ORDER BY unlocks DESC, demand DESC, skill ASC
    """
    unlock_rows = con.execute(unlock_query, [threshold, threshold, R]).fetchall()
    total_query_ms += (time.perf_counter() - t0) * 1000

    all_unlocks_count = len(unlock_rows)
    top_unlock_rows = unlock_rows[:top_n]
    demand_map = {r[0]: r[2] for r in unlock_rows}

    # 4. Example jobs for top unlocks (max 3 per skill, single ROW_NUMBER window query)
    unlock_list = []
    top_skill_names = [r[0] for r in top_unlock_rows]
    if top_skill_names:
        t0 = time.perf_counter()
        ex_query = """
            WITH unmatched AS (
                SELECT 
                    job_id,
                    title,
                    company_name,
                    skills,
                    (m * 100) // n AS match_before,
                    ((m + 1) * 100) // n AS match_after,
                    unnest(skills) AS skill
                FROM _req_eligible
                WHERE m * 100 < ? * n AND (m + 1) * 100 >= ? * n
            ),
            ranked_examples AS (
                SELECT 
                    skill,
                    job_id,
                    title,
                    company_name,
                    match_before,
                    match_after,
                    ROW_NUMBER() OVER (PARTITION BY skill ORDER BY match_before DESC, job_id ASC) AS rn
                FROM unmatched
                WHERE list_contains(?::VARCHAR[], skill)
            )
            SELECT skill, job_id, title, company_name, match_before, match_after
            FROM ranked_examples
            WHERE rn <= 3
            ORDER BY skill, match_before DESC, job_id ASC
        """
        ex_rows = con.execute(ex_query, [threshold, threshold, top_skill_names]).fetchall()
        total_query_ms += (time.perf_counter() - t0) * 1000

        examples_by_skill: Dict[str, List[Dict[str, Any]]] = {}
        for row in ex_rows:
            s_name, j_id, title, comp, mb, ma = row
            if s_name not in examples_by_skill:
                examples_by_skill[s_name] = []
            examples_by_skill[s_name].append({
                "job_id": j_id,
                "title": title,
                "company_name": comp,
                "match_before": mb,
                "match_after": ma
            })

        for s_name, unl, dem in top_unlock_rows:
            unlock_list.append({
                "skill": s_name,
                "unlocks": unl,
                "demand": dem,
                "example_jobs": examples_by_skill.get(s_name, [])
            })

    # 5. Greedy Path (up to 3 steps, avoiding redundant rescans)
    path = []
    current_R = list(R)
    running_gain = 0
    for step_num in range(1, 4):
        if step_num == 1:
            if not unlock_rows or unlock_rows[0][1] <= 0:
                break
            top_s, top_u = unlock_rows[0][0], unlock_rows[0][1]
            current_R.append(top_s)
            running_gain += top_u
            path.append({
                "step": 1,
                "skill": top_s,
                "unlocks": top_u,
                "cumulative_gain": running_gain
            })
            t0 = time.perf_counter()
            con.execute("UPDATE _req_eligible SET m = m + 1 WHERE list_contains(skills, ?)", [top_s])
            total_query_ms += (time.perf_counter() - t0) * 1000
        else:
            t0 = time.perf_counter()
            step_rows = con.execute(unlock_query + " LIMIT 1", [threshold, threshold, current_R]).fetchall()
            total_query_ms += (time.perf_counter() - t0) * 1000

            if not step_rows or step_rows[0][1] <= 0:
                break

            top_s, top_u = step_rows[0][0], step_rows[0][1]
            current_R.append(top_s)
            running_gain += top_u
            path.append({
                "step": step_num,
                "skill": top_s,
                "unlocks": top_u,
                "cumulative_gain": running_gain
            })
            if step_num < 3:
                t0 = time.perf_counter()
                con.execute("UPDATE _req_eligible SET m = m + 1 WHERE list_contains(skills, ?)", [top_s])
                total_query_ms += (time.perf_counter() - t0) * 1000

    return {
        "baseline": {"eligible_jobs": eligible_jobs, "matched_jobs": matched_jobs},
        "unlocks": unlock_list,
        "path": path,
        "all_unlocks_count": all_unlocks_count,
        "query_ms": round(total_query_ms, 2)
    }


def compute_job_fit(
    con,
    R: List[str],
    threshold: int = 60,
    min_job_skills: int = 3,
    location_type: Optional[str] = None,
    role: Optional[str] = None,
    limit: int = 500,
    table_name: str = "jobs"
) -> Tuple[List[Dict[str, Any]], float]:
    """
    Scores each eligible job against candidate skills R.
    Sorted by match_pct DESC then title ASC then job_id ASC.
    """
    if role is not None and role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid role '{role}'. Allowed values: {sorted(list(ALLOWED_ROLES))}"
        )

    loc_clause = ""
    loc_params: List[Any] = []
    if location_type:
        loc_clause = "AND location_type = ?"
        loc_params = [location_type]

    role_clause = ""
    role_params: List[Any] = []
    if role:
        role_clause = "AND regexp_matches(title, ?, 'i')"
        role_params = [ROLE_PATTERNS[role]]

    t0 = time.perf_counter()
    query = f"""
        WITH eligible AS (
            SELECT 
                job_id,
                title,
                company_name,
                location,
                location_type,
                portal_count,
                list_distinct(skills_required) AS skills,
                len(list_distinct(skills_required)) AS n,
                list_intersect(list_distinct(skills_required), ?::VARCHAR[]) AS matched_skills
            FROM {table_name}
            WHERE len(list_distinct(skills_required)) >= ?
              {loc_clause}
              {role_clause}
        )
        SELECT 
            job_id,
            title,
            company_name,
            location,
            location_type,
            portal_count,
            (len(matched_skills) * 100) // n AS match_pct,
            list_sort(matched_skills) AS matched,
            list_sort(list_filter(skills, x -> NOT list_contains(?::VARCHAR[], x))) AS missing
        FROM eligible
        ORDER BY match_pct DESC, title ASC, job_id ASC
        LIMIT ?
    """
    params = [R, min_job_skills] + loc_params + role_params + [R, max(1, min(limit, 500))]
    rows = con.execute(query, params).fetchall()
    elapsed_ms = (time.perf_counter() - t0) * 1000

    results = []
    for r in rows:
        results.append({
            "job_id": r[0],
            "title": r[1],
            "company_name": r[2],
            "location": r[3] or "",
            "location_type": r[4] or "On-site",
            "portal_count": r[5] or 1,
            "match_pct": r[6],
            "matched": r[7] or [],
            "missing": r[8] or []
        })

    return results, round(elapsed_ms, 2)


# ==================== PURE-PYTHON REFERENCE IMPLEMENTATION ====================

def python_reference_unlock(
    jobs: List[Dict[str, Any]],
    R: List[str],
    threshold: int = 60,
    min_job_skills: int = 3,
    location_type: Optional[str] = None,
    role: Optional[str] = None,
    top_n: int = 10
) -> Dict[str, Any]:
    """
    Pure-Python reference implementation of Skill Unlock and Greedy Path.
    Used exclusively in tests to assert SQL parity.
    """
    if role is not None and role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid role '{role}'. Allowed values: {sorted(list(ALLOWED_ROLES))}"
        )
    role_pat = re.compile(ROLE_PATTERNS[role], re.IGNORECASE) if role else None

    R_set = set(R)
    eligible = []
    for j in jobs:
        if location_type and j.get("location_type") != location_type:
            continue
        if role_pat and not role_pat.search(j.get("title") or ""):
            continue
        # Set of distinct skills
        raw_skills = j.get("skills_required") or []
        distinct_skills = list(dict.fromkeys(raw_skills))
        if len(distinct_skills) < min_job_skills:
            continue
        skills = set(distinct_skills)
        n = len(skills)
        m = len(R_set & skills)
        is_matched = (m * 100 >= threshold * n)
        eligible.append({
            "job_id": j["job_id"],
            "title": j.get("title", ""),
            "company_name": j.get("company_name", ""),
            "skills": skills,
            "n": n,
            "m": m,
            "is_matched": is_matched,
            "match_before": (m * 100) // n,
            "match_after": ((m + 1) * 100) // n
        })

    eligible_jobs = len(eligible)
    matched_jobs = sum(1 for e in eligible if e["is_matched"])

    candidate_skills = set()
    for e in eligible:
        candidate_skills.update(e["skills"] - R_set)

    unlock_list = []
    for s in candidate_skills:
        demand = 0
        unlocks = 0
        unlocked_jobs = []
        for e in eligible:
            if s in e["skills"]:
                demand += 1
                if not e["is_matched"] and ((e["m"] + 1) * 100 >= threshold * e["n"]):
                    unlocks += 1
                    unlocked_jobs.append(e)
        if unlocks > 0:
            unlocked_jobs.sort(key=lambda x: (-x["match_before"], x["job_id"]))
            example_jobs = [
                {
                    "job_id": x["job_id"],
                    "title": x["title"],
                    "company_name": x["company_name"],
                    "match_before": x["match_before"],
                    "match_after": x["match_after"]
                }
                for x in unlocked_jobs[:3]
            ]
            unlock_list.append({
                "skill": s,
                "unlocks": unlocks,
                "demand": demand,
                "example_jobs": example_jobs
            })

    unlock_list.sort(key=lambda x: (-x["unlocks"], -x["demand"], x["skill"]))

    # Greedy Path
    path = []
    current_R = set(R)
    for step_num in range(1, 4):
        cand_list = []
        all_skills_in_eligible = set().union(*(e["skills"] for e in eligible)) if eligible else set()
        for s in all_skills_in_eligible - current_R:
            u_count = 0
            d_count = 0
            for e in eligible:
                m_curr = len(current_R & e["skills"])
                is_m_curr = (m_curr * 100 >= threshold * e["n"])
                if s in e["skills"]:
                    d_count += 1
                    if not is_m_curr and ((m_curr + 1) * 100 >= threshold * e["n"]):
                        u_count += 1
            if u_count > 0:
                cand_list.append((u_count, d_count, s))
        if not cand_list:
            break
        cand_list.sort(key=lambda x: (-x[0], -x[1], x[2]))
        top_u, top_d, top_s = cand_list[0]
        current_R.add(top_s)
        curr_matched = sum(1 for e in eligible if (len(current_R & e["skills"]) * 100 >= threshold * e["n"]))
        cum_gain = curr_matched - matched_jobs
        path.append({
            "step": step_num,
            "skill": top_s,
            "unlocks": top_u,
            "cumulative_gain": cum_gain
        })

    return {
        "baseline": {"eligible_jobs": eligible_jobs, "matched_jobs": matched_jobs},
        "unlocks": unlock_list[:top_n],
        "path": path,
        "all_unlocks_count": len(unlock_list)
    }
