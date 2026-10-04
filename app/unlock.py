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


def get_corpus_stats(con, table_name: str = "jobs") -> Tuple[Dict[str, Any], float]:
    """
    Fetches corpus metrics: total jobs, date range from scraped_at, and snapshot share.
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
    elapsed_ms = (time.perf_counter() - t0) * 1000

    if not row or row[0] == 0:
        return {
            "jobs": 0,
            "as_of_min": None,
            "as_of_max": None,
            "snapshot_share": 0.0
        }, elapsed_ms

    return {
        "jobs": row[0],
        "as_of_min": str(row[1]) if row[1] is not None else None,
        "as_of_max": str(row[2]) if row[2] is not None else None,
        "snapshot_share": round(float(row[3] or 0.0), 4)
    }, elapsed_ms


def compute_skill_unlocks(
    con,
    R: List[str],
    threshold: int = 60,
    min_job_skills: int = 3,
    location_type: Optional[str] = None,
    top_n: int = 10,
    table_name: str = "jobs"
) -> Dict[str, Any]:
    """
    Computes baseline matching, candidate skill unlocks and demand in single DuckDB SQL aggregation,
    example unlocked jobs, and greedy unlock path up to 3 steps.
    All skill values and filters are bound as query parameters.
    """
    total_query_ms = 0.0

    loc_clause = ""
    loc_params: List[Any] = []
    if location_type:
        loc_clause = "AND location_type = ?"
        loc_params = [location_type]

    # 1. Baseline matching query
    t0 = time.perf_counter()
    base_query = f"""
        WITH eligible AS (
            SELECT 
                len(list_distinct(skills_required)) AS n,
                len(list_intersect(list_distinct(skills_required), ?::VARCHAR[])) AS m
            FROM {table_name}
            WHERE len(list_distinct(skills_required)) >= ?
              {loc_clause}
        )
        SELECT 
            COUNT(*) AS eligible_jobs,
            COUNT(*) FILTER (WHERE m * 100 >= ? * n) AS matched_jobs
        FROM eligible
    """
    base_params = [R, min_job_skills] + loc_params + [threshold]
    base_row = con.execute(base_query, base_params).fetchone()
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

    # 2. Main UNLOCK and DEMAND single SQL aggregation
    t0 = time.perf_counter()
    unlock_query = f"""
        WITH eligible AS (
            SELECT 
                job_id,
                list_distinct(skills_required) AS skills,
                len(list_distinct(skills_required)) AS n,
                len(list_intersect(list_distinct(skills_required), ?::VARCHAR[])) AS m
            FROM {table_name}
            WHERE len(list_distinct(skills_required)) >= ?
              {loc_clause}
        ),
        classified AS (
            SELECT 
                job_id,
                skills,
                n,
                m,
                (m * 100 >= ? * n) AS is_matched
            FROM eligible
        ),
        unmatched_candidates AS (
            SELECT 
                c.job_id,
                c.n,
                c.m,
                unnest(c.skills) AS skill
            FROM classified c
            WHERE NOT c.is_matched
        ),
        all_eligible_skills AS (
            SELECT 
                c.job_id,
                unnest(c.skills) AS skill
            FROM eligible c
        )
        SELECT 
            d.skill,
            COUNT(DISTINCT CASE WHEN (u.m + 1) * 100 >= ? * u.n THEN u.job_id END) AS unlocks,
            COUNT(DISTINCT d.job_id) AS demand
        FROM all_eligible_skills d
        LEFT JOIN unmatched_candidates u ON d.skill = u.skill
        WHERE NOT list_contains(?::VARCHAR[], d.skill)
        GROUP BY d.skill
        HAVING unlocks > 0
        ORDER BY unlocks DESC, demand DESC, skill ASC
    """
    params_unlock = [R, min_job_skills] + loc_params + [threshold, threshold, R]
    unlock_rows = con.execute(unlock_query, params_unlock).fetchall()
    total_query_ms += (time.perf_counter() - t0) * 1000

    all_unlocks_count = len(unlock_rows)
    top_unlock_rows = unlock_rows[:top_n]

    # 3. Example jobs for top unlocks (max 3 per skill)
    unlock_list = []
    if top_unlock_rows:
        top_skill_names = [r[0] for r in top_unlock_rows]
        t0 = time.perf_counter()
        ex_query = f"""
            WITH eligible AS (
                SELECT 
                    job_id,
                    title,
                    company_name,
                    list_distinct(skills_required) AS skills,
                    len(list_distinct(skills_required)) AS n,
                    len(list_intersect(list_distinct(skills_required), ?::VARCHAR[])) AS m
                FROM {table_name}
                WHERE len(list_distinct(skills_required)) >= ?
                  {loc_clause}
            ),
            unmatched AS (
                SELECT 
                    job_id,
                    title,
                    company_name,
                    skills,
                    n,
                    m,
                    (m * 100) // n AS match_before,
                    ((m + 1) * 100) // n AS match_after
                FROM eligible
                WHERE m * 100 < ? * n AND (m + 1) * 100 >= ? * n
            ),
            unmatched_unnested AS (
                SELECT 
                    u.job_id,
                    u.title,
                    u.company_name,
                    u.match_before,
                    u.match_after,
                    unnest(u.skills) AS skill
                FROM unmatched u
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
                FROM unmatched_unnested
                WHERE list_contains(?::VARCHAR[], skill)
            )
            SELECT skill, job_id, title, company_name, match_before, match_after
            FROM ranked_examples
            WHERE rn <= 3
            ORDER BY skill, match_before DESC, job_id ASC
        """
        params_ex = [R, min_job_skills] + loc_params + [threshold, threshold, top_skill_names]
        ex_rows = con.execute(ex_query, params_ex).fetchall()
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

    # 4. Greedy Path (up to 3 steps)
    path = []
    current_R = list(R)
    for step_num in range(1, 4):
        t0 = time.perf_counter()
        params_step = [current_R, min_job_skills] + loc_params + [threshold, threshold, current_R]
        top_cand_row = con.execute(unlock_query + " LIMIT 1", params_step).fetchone()
        total_query_ms += (time.perf_counter() - t0) * 1000

        if not top_cand_row or top_cand_row[1] <= 0:
            break

        top_s = top_cand_row[0]
        top_u = top_cand_row[1]
        current_R.append(top_s)

        t0 = time.perf_counter()
        matched_curr_row = con.execute(f"""
            WITH eligible AS (
                SELECT 
                    len(list_distinct(skills_required)) AS n,
                    len(list_intersect(list_distinct(skills_required), ?::VARCHAR[])) AS m
                FROM {table_name}
                WHERE len(list_distinct(skills_required)) >= ?
                  {loc_clause}
            )
            SELECT COUNT(*) FROM eligible WHERE m * 100 >= ? * n
        """, [current_R, min_job_skills] + loc_params + [threshold]).fetchone()
        total_query_ms += (time.perf_counter() - t0) * 1000

        cum_gain = (matched_curr_row[0] if matched_curr_row else 0) - matched_jobs
        path.append({
            "step": step_num,
            "skill": top_s,
            "unlocks": top_u,
            "cumulative_gain": cum_gain
        })

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
    limit: int = 500,
    table_name: str = "jobs"
) -> Tuple[List[Dict[str, Any]], float]:
    """
    Scores each eligible job against candidate skills R.
    Sorted by match_pct DESC then title ASC then job_id ASC.
    """
    loc_clause = ""
    loc_params: List[Any] = []
    if location_type:
        loc_clause = "AND location_type = ?"
        loc_params = [location_type]

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
    params = [R, min_job_skills] + loc_params + [R, max(1, min(limit, 500))]
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
    top_n: int = 10
) -> Dict[str, Any]:
    """
    Pure-Python reference implementation of Skill Unlock and Greedy Path.
    Used exclusively in tests to assert SQL parity.
    """
    R_set = set(R)
    eligible = []
    for j in jobs:
        skills = set(j.get("skills_required") or [])
        if len(skills) < min_job_skills:
            continue
        if location_type and j.get("location_type") != location_type:
            continue
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
