import os
import re
import json
import glob
import hashlib
from datetime import datetime, timezone, timedelta
import duckdb
from typing import List, Dict, Any, Optional, Tuple

DATABASE_FILE = os.getenv("DUCKDB_PATH") or os.getenv("DATABASE_PATH", "radar.duckdb")

TRACKED_SKILLS = [
    # Languages & Core
    "Python", "Java", "Spring Boot", "JavaScript", "TypeScript", "React", "Next.js",
    "Node.js", "Angular", "Vue.js", "FastAPI", "Django", "Flask", "C++", "C#",
    ".NET", "Golang", "Rust", "PHP", "Ruby", "HTML", "CSS", "Tailwind",
    # Data & Analytics
    "SQL", "PostgreSQL", "MySQL", "DuckDB", "MongoDB", "Redis", "Kafka",
    "Snowflake", "Databricks", "Spark", "Hadoop", "Airflow", "Pandas", "NumPy",
    "Tableau", "Power BI", "Excel", "dbt", "BigQuery",
    # AI & ML
    "PyTorch", "TensorFlow", "scikit-learn", "Keras", "LangChain", "LlamaIndex",
    "RAG", "OpenCV", "Hugging Face", "NLP", "LLM",
    # Cloud & DevOps
    "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform", "Ansible",
    "Jenkins", "CI/CD", "Linux", "Git", "Prometheus", "Grafana", "SRE",
    # API & Architecture & Testing
    "REST API", "GraphQL", "Microservices", "Elasticsearch", "RabbitMQ", "Selenium"
]

SKILL_PATTERNS = {
    # Special character and alias mapping with boundary lookarounds
    "RAG": re.compile(r'(?<![a-zA-Z0-9_#+])RAG(?![a-zA-Z0-9_#+])|retrieval[ -]augmented generation', re.IGNORECASE),
    "C++": re.compile(r'(?<![a-zA-Z0-9_#+])(C\+\+|cpp)(?![a-zA-Z0-9_#+])', re.IGNORECASE),
    "C#": re.compile(r'(?<![a-zA-Z0-9_#+])(C#|csharp|c[ -]sharp)(?![a-zA-Z0-9_#+])', re.IGNORECASE),
    ".NET": re.compile(r'(?<![a-zA-Z0-9_#+])(\.NET|dotnet)(?![a-zA-Z0-9_#+])', re.IGNORECASE),
    "Node.js": re.compile(r'(?<![a-zA-Z0-9_#+])(node\.?js|node)(?![a-zA-Z0-9_#+])', re.IGNORECASE),
    "React": re.compile(r'(?<![a-zA-Z0-9_#+])(react\.?js|react)(?![a-zA-Z0-9_#+])', re.IGNORECASE),
    "Next.js": re.compile(r'(?<![a-zA-Z0-9_#+])(next\.?js|next)(?![a-zA-Z0-9_#+])', re.IGNORECASE),
    "PostgreSQL": re.compile(r'(?<![a-zA-Z0-9_#+])(postgresql|postgres)(?![a-zA-Z0-9_#+])', re.IGNORECASE),
    "Kubernetes": re.compile(r'(?<![a-zA-Z0-9_#+])(kubernetes|k8s)(?![a-zA-Z0-9_#+])', re.IGNORECASE),
    "AWS": re.compile(r'(?<![a-zA-Z0-9_#+])(AWS|Amazon Web Services)(?![a-zA-Z0-9_#+])', re.IGNORECASE),
    "GCP": re.compile(r'(?<![a-zA-Z0-9_#+])(GCP|Google Cloud( Platform)?)(?![a-zA-Z0-9_#+])', re.IGNORECASE),
    "scikit-learn": re.compile(r'(?<![a-zA-Z0-9_#+])(scikit[ -]learn|sklearn)(?![a-zA-Z0-9_#+])', re.IGNORECASE),
    "Power BI": re.compile(r'(?<![a-zA-Z0-9_#+])(power\s*bi)(?![a-zA-Z0-9_#+])', re.IGNORECASE),
    "Spring Boot": re.compile(r'(?<![a-zA-Z0-9_#+])(spring\s*boot)(?![a-zA-Z0-9_#+])', re.IGNORECASE),
    "Golang": re.compile(r'(?<![a-zA-Z0-9_#+])(golang|go\s+language)(?![a-zA-Z0-9_#+])', re.IGNORECASE),
    "CI/CD": re.compile(r'(?<![a-zA-Z0-9_#+])(CI[/-]CD|cicd)(?![a-zA-Z0-9_#+])', re.IGNORECASE),
    "Excel": re.compile(r'(?<![a-zA-Z0-9_#+])(ms\s*excel|microsoft\s*excel|excel)(?![a-zA-Z0-9_#+])', re.IGNORECASE),
    "Microservices": re.compile(r'(?<![a-zA-Z0-9_#+])microservices?(?![a-zA-Z0-9_#+])', re.IGNORECASE),
    "REST API": re.compile(r'(?<![a-zA-Z0-9_#+])(REST(\s*APIs?)?|RESTful(\s*APIs?)?)(?![a-zA-Z0-9_#+])', re.IGNORECASE),
    "LLM": re.compile(r'(?<![a-zA-Z0-9_#+])LLMs?(?![a-zA-Z0-9_#+])', re.IGNORECASE)
}

# Compile standard lookaround patterns for all remaining canonical skills
for s in TRACKED_SKILLS:
    if s not in SKILL_PATTERNS:
        escaped = re.escape(s)
        escaped = re.sub(r'\\ ', r'\\s+', escaped)
        SKILL_PATTERNS[s] = re.compile(r'(?<![a-zA-Z0-9_#+])' + escaped + r'(?![a-zA-Z0-9_#+])', re.IGNORECASE)


def normalize_text(s: Any) -> str:
    """
    Normalizes text by converting to lowercase, collapsing whitespace, and stripping.
    """
    if not s:
        return ""
    return " ".join(str(s).lower().split()).strip()


def generate_canonical_job_id(title: str, company_name: str, location: str, description: str) -> str:
    """
    Computes deterministic canonical job_id using:
    md5(title | company_name | location | first 300 normalized description chars)
    with each component lowercased, whitespace collapsed, and trimmed.
    """
    norm_title = normalize_text(title)
    norm_comp = normalize_text(company_name)
    norm_loc = normalize_text(location)
    norm_desc = normalize_text(description)[:300]
    raw_key = f"{norm_title}|{norm_comp}|{norm_loc}|{norm_desc}"
    return hashlib.md5(raw_key.encode("utf-8")).hexdigest()


def merge_apply_options(existing_opts: Any, incoming_opts: Any) -> Tuple[List[Dict[str, Any]], int]:
    """
    Unions apply options by publisher title, keeping the first link per publisher.
    Returns (merged_options, length_of_union).
    """
    def to_list(opts):
        if not opts:
            return []
        if isinstance(opts, str):
            try:
                opts = json.loads(opts)
            except Exception:
                return []
        return [o for o in opts if isinstance(o, dict)] if isinstance(opts, list) else []

    list1 = to_list(existing_opts)
    list2 = to_list(incoming_opts)

    merged = []
    seen = set()

    for opt in list1 + list2:
        pub = (opt.get("title") or opt.get("link") or "").strip().lower()
        if not pub:
            continue
        if pub not in seen:
            seen.add(pub)
            merged.append(opt)

    return merged, len(merged) if merged else 1


def parse_timestamp(val: Any) -> float:
    """
    Parses datetime, float, or ISO string to timestamp float for time comparison.
    """
    if not val:
        return float("inf")
    if isinstance(val, (int, float)):
        return float(val)
    if hasattr(val, "timestamp"):
        return val.timestamp()
    try:
        s = str(val).replace("Z", "+00:00")
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return float("inf")


def extract_skills_from_text(text: str) -> List[str]:
    """
    Extracts canonical skills using strict lookarounds and alias expansion.
    Enforces negative boundary lookarounds so:
      - 'JavaScript' does NOT match 'Java'
      - 'GitHub' does NOT match 'Git'
      - 'go to market' does NOT match 'Golang'
      - 'rag' lowercase does NOT match 'RAG'
      - 'C++' and 'C#' correctly match
      - 'Spring Boot' and 'Power BI' match
    """
    if not text or not isinstance(text, str):
        return []
    matched = set()
    for canonical, pattern in SKILL_PATTERNS.items():
        if canonical == "RAG":
            if re.search(r'(?<![a-zA-Z0-9_#+])RAG(?![a-zA-Z0-9_#+])', text) or re.search(r'retrieval[ -]augmented generation', text, re.IGNORECASE):
                matched.add("RAG")
        else:
            if pattern.search(text):
                matched.add(canonical)
    return sorted(list(matched))


class DatabaseManager:
    def __init__(self, db_path: str = DATABASE_FILE):
        self.db_path = db_path
        self._init_schema()

    @staticmethod
    def _rows_to_dicts(cursor) -> List[Dict[str, Any]]:
        if not cursor.description:
            return []
        cols = [desc[0] for desc in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def get_connection(self):
        return duckdb.connect(self.db_path)

    def _init_schema(self):
        with self.get_connection() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
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
                    skills_required VARCHAR[],
                    apply_options JSON,
                    portal_count INTEGER DEFAULT 1,
                    salary_min_lpa DOUBLE,
                    salary_max_lpa DOUBLE,
                    source_query VARCHAR,
                    source_gl VARCHAR,
                    is_snapshot BOOLEAN DEFAULT FALSE,
                    serpapi_token VARCHAR,
                    source_queries VARCHAR[],
                    posted_days_ago INTEGER
                );
            """)
            # Non-destructive migrations for existing database files
            self._run_migrations(con)
            
            # Cache table for SerpApi queries
            con.execute("""
                CREATE TABLE IF NOT EXISTS search_cache (
                    cache_key VARCHAR PRIMARY KEY,
                    query VARCHAR,
                    location VARCHAR,
                    gl VARCHAR,
                    hl VARCHAR,
                    date_posted VARCHAR,
                    response_json TEXT,
                    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def _run_migrations(self, con=None):
        should_close = False
        if con is None:
            con = self.get_connection()
            should_close = True
        try:
            new_columns = [
                ("via_platform", "VARCHAR"),
                ("salary_raw", "VARCHAR"),
                ("location_type", "VARCHAR"),
                ("skills_required", "VARCHAR[]"),
                ("apply_options", "JSON"),
                ("portal_count", "INTEGER DEFAULT 1"),
                ("salary_min_lpa", "DOUBLE"),
                ("salary_max_lpa", "DOUBLE"),
                ("source_query", "VARCHAR"),
                ("source_gl", "VARCHAR"),
                ("is_snapshot", "BOOLEAN DEFAULT FALSE"),
                ("serpapi_token", "VARCHAR"),
                ("source_queries", "VARCHAR[]"),
                ("posted_days_ago", "INTEGER")
            ]
            for col, ctype in new_columns:
                try:
                    con.execute(f"ALTER TABLE jobs ADD COLUMN IF NOT EXISTS {col} {ctype};")
                except Exception:
                    # Fallback for environments with strict ALTER syntax
                    try:
                        con.execute(f"ALTER TABLE jobs ADD COLUMN {col} {ctype};")
                    except Exception:
                        pass

            # Backfill source_queries from source_query on existing rows
            try:
                con.execute("""
                    UPDATE jobs
                    SET source_queries = [source_query]
                    WHERE source_queries IS NULL AND source_query IS NOT NULL;
                """)
            except Exception:
                pass

            # Strict relative-time cleanup migration
            try:
                con.execute("""
                    UPDATE jobs
                    SET salary_raw = NULL, salary = NULL
                    WHERE (salary_raw IS NOT NULL AND (
                        regexp_matches(lower(trim(salary_raw)), '^\\d+\\s+(minute|hour|day|week|month)s?\\s+ago$')
                        OR lower(trim(salary_raw)) IN ('just now', 'yesterday', 'today')
                        OR trim(salary_raw) = ''
                    )) OR (salary IS NOT NULL AND (
                        regexp_matches(lower(trim(salary)), '^\\d+\\s+(minute|hour|day|week|month)s?\\s+ago$')
                        OR lower(trim(salary)) IN ('just now', 'yesterday', 'today')
                        OR trim(salary) = ''
                    ));
                """)
            except Exception:
                pass

            # Backfill posted_days_ago from scraped_at if null
            try:
                con.execute("""
                    UPDATE jobs
                    SET posted_days_ago = CASE
                        WHEN posted_days_ago IS NOT NULL THEN posted_days_ago
                        WHEN scraped_at IS NOT NULL THEN GREATEST(0, CAST(date_diff('day', scraped_at, CURRENT_TIMESTAMP) AS INTEGER))
                        ELSE 0
                    END
                    WHERE posted_days_ago IS NULL;
                """)
            except Exception:
                pass
        finally:
            if should_close:
                con.close()

    @staticmethod
    def _merge_job_records(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merges existing and incoming job records per Phase 1.7 deduplication rules:
        - source_queries: distinct union
        - apply_options: union by publisher title, keeping first link per publisher; portal_count = length of union
        - salary_raw, salary_min_lpa, salary_max_lpa: keep existing non-null, else take incoming
        - scraped_at: earliest
        - is_snapshot: existing AND incoming (false if any live source)
        - serpapi_token: keep existing non-null, else take incoming
        """
        merged = dict(existing)

        # 1. source_queries: distinct union
        def to_q_list(rec):
            qs = rec.get("source_queries")
            if qs is not None and isinstance(qs, list):
                res = [str(q).strip() for q in qs if q and str(q).strip()]
            else:
                res = []
            sq = rec.get("source_query")
            if sq and str(sq).strip() and str(sq).strip() not in res:
                res.append(str(sq).strip())
            return res

        ex_qs = to_q_list(existing)
        in_qs = to_q_list(incoming)
        merged_queries = []
        for q in ex_qs + in_qs:
            if q not in merged_queries:
                merged_queries.append(q)
        merged["source_queries"] = merged_queries
        merged["source_query"] = existing.get("source_query") or (merged_queries[0] if merged_queries else None)

        # 2. apply_options & portal_count
        opts, p_count = merge_apply_options(existing.get("apply_options"), incoming.get("apply_options"))
        merged["apply_options"] = opts
        merged["portal_count"] = p_count
        if not merged.get("apply_link") and opts:
            merged["apply_link"] = opts[0].get("link", "")

        # 3. salary_raw, salary_min_lpa, salary_max_lpa = keep existing non-null, else take new
        ex_salary_raw = existing.get("salary_raw") or existing.get("salary")
        in_salary_raw = incoming.get("salary_raw") or incoming.get("salary")
        if ex_salary_raw and str(ex_salary_raw).strip():
            merged["salary_raw"] = ex_salary_raw
            merged["salary"] = ex_salary_raw
            merged["salary_min_lpa"] = existing.get("salary_min_lpa") if existing.get("salary_min_lpa") is not None else incoming.get("salary_min_lpa")
            merged["salary_max_lpa"] = existing.get("salary_max_lpa") if existing.get("salary_max_lpa") is not None else incoming.get("salary_max_lpa")
        else:
            merged["salary_raw"] = in_salary_raw
            merged["salary"] = in_salary_raw
            merged["salary_min_lpa"] = incoming.get("salary_min_lpa")
            merged["salary_max_lpa"] = incoming.get("salary_max_lpa")

        # 4. scraped_at = earliest
        ts_ex = parse_timestamp(existing.get("scraped_at"))
        ts_in = parse_timestamp(incoming.get("scraped_at") or incoming.get("captured_at"))
        if ts_in < ts_ex:
            merged["scraped_at"] = incoming.get("scraped_at") or incoming.get("captured_at")
        else:
            merged["scraped_at"] = existing.get("scraped_at")

        # 5. is_snapshot = existing AND new (false if any live source)
        merged["is_snapshot"] = bool(existing.get("is_snapshot", False)) and bool(incoming.get("is_snapshot", False))

        # 6. serpapi_token
        merged["serpapi_token"] = existing.get("serpapi_token") or incoming.get("serpapi_token")

        # 7. skills_required: distinct union
        ex_skills = existing.get("skills_required") or []
        in_skills = incoming.get("skills_required") or []
        merged["skills_required"] = sorted(list(set(ex_skills + in_skills)))

        # 8. location_type & work_from_home
        wfh = bool(existing.get("work_from_home") or incoming.get("work_from_home"))
        merged["work_from_home"] = wfh
        if wfh or existing.get("location_type") == "Remote" or incoming.get("location_type") == "Remote":
            merged["location_type"] = "Remote"
        else:
            merged["location_type"] = existing.get("location_type") or incoming.get("location_type") or "On-site"

        # Update non-protected metadata fields from incoming if present
        for field in ["title", "company_name", "location", "via", "description", "schedule_type", "posted_at", "posted_days_ago", "via_platform", "source_gl"]:
            if incoming.get(field) is not None:
                merged[field] = incoming[field]

        return merged

    def upsert_jobs(
        self,
        jobs: List[Dict[str, Any]],
        is_snapshot: bool = False,
        source_query: Optional[str] = None,
        source_gl: Optional[str] = None
    ) -> int:
        if not jobs:
            return 0

        # Import sanitization utility
        from app.serpapi_client import sanitize_salary_raw, parse_indian_salary_to_lpa

        prepared_jobs = []
        for job in jobs:
            title = job.get("title", "Untitled Role")
            company_name = job.get("company_name", "Unknown Company")
            location = job.get("location", "")
            description = job.get("description", "")
            via = job.get("via", "Direct")
            schedule_type = job.get("schedule_type", "Full-time")

            raw_token = job.get("serpapi_token")
            incoming_job_id = job.get("job_id")

            if raw_token:
                final_job_id = generate_canonical_job_id(title, company_name, location, description)
                final_serp_token = raw_token
            elif incoming_job_id:
                final_job_id = incoming_job_id
                final_serp_token = None
            else:
                final_job_id = generate_canonical_job_id(title, company_name, location, description)
                final_serp_token = None

            salary_str = sanitize_salary_raw(job.get("salary"))
            salary_raw = sanitize_salary_raw(job.get("salary_raw") or salary_str)
            salary_min_lpa = job.get("salary_min_lpa")
            salary_max_lpa = job.get("salary_max_lpa")
            if salary_raw and salary_min_lpa is None and salary_max_lpa is None:
                salary_min_lpa, salary_max_lpa = parse_indian_salary_to_lpa(salary_raw)

            loc_lower = str(location or "").lower()
            extensions_list = job.get("extensions") or []
            wfh_from_ext = any("work from home" in str(e).lower() for e in extensions_list)
            is_remote_loc = bool(
                job.get("work_from_home", False) or
                wfh_from_ext or
                "remote" in loc_lower or
                loc_lower == "anywhere" or
                "anywhere" in loc_lower
            )
            location_type = job.get("location_type") or ("Remote" if is_remote_loc else "On-site")
            work_from_home = bool(is_remote_loc or (location_type == "Remote"))

            combined_text = f"{title} {description} {job.get('highlights_text', '')}"
            skills_required = job.get("skills_required") or extract_skills_from_text(combined_text)

            apply_options = job.get("apply_options")
            if isinstance(apply_options, str):
                try:
                    apply_options = json.loads(apply_options)
                except Exception:
                    apply_options = []
            elif apply_options is None:
                apply_options = []

            apply_link = job.get("apply_link") or (apply_options[0].get("link") if apply_options else "")
            portal_count = int(job.get("portal_count", len(apply_options) if apply_options else 1))

            job_source_query = job.get("source_query") or source_query or ""
            sq_list = job.get("source_queries")
            if sq_list is None:
                source_queries = [job_source_query] if job_source_query else []
            else:
                source_queries = [str(x).strip() for x in sq_list if x and str(x).strip()]
                if job_source_query and job_source_query not in source_queries:
                    source_queries.append(job_source_query)

            scraped_at = job.get("scraped_at") or job.get("captured_at") or datetime.now(timezone.utc).replace(tzinfo=None)
            job_is_snap = job.get("is_snapshot", is_snapshot)

            prepared_jobs.append({
                "job_id": final_job_id,
                "title": title,
                "company_name": company_name,
                "location": location,
                "via": via,
                "description": description,
                "schedule_type": schedule_type,
                "work_from_home": work_from_home,
                "salary": salary_raw,
                "apply_link": apply_link,
                "posted_at": job.get("posted_at", ""),
                "posted_days_ago": job.get("posted_days_ago"),
                "scraped_at": scraped_at,
                "via_platform": job.get("via_platform") or via,
                "salary_raw": salary_raw,
                "location_type": location_type,
                "skills_required": skills_required,
                "apply_options": apply_options,
                "portal_count": portal_count,
                "salary_min_lpa": salary_min_lpa,
                "salary_max_lpa": salary_max_lpa,
                "source_query": job_source_query,
                "source_gl": job.get("source_gl") or source_gl or "in",
                "is_snapshot": bool(job_is_snap),
                "serpapi_token": final_serp_token,
                "source_queries": source_queries
            })

        upsert_sql = """
            INSERT INTO jobs (
                job_id, title, company_name, location, via,
                description, schedule_type, work_from_home,
                salary, apply_link, posted_at, scraped_at,
                via_platform, salary_raw, location_type, skills_required,
                apply_options, portal_count, salary_min_lpa, salary_max_lpa,
                source_query, source_gl, is_snapshot, serpapi_token, source_queries,
                posted_days_ago
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?
            )
            ON CONFLICT (job_id) DO UPDATE SET
                title = excluded.title,
                company_name = excluded.company_name,
                location = excluded.location,
                via = excluded.via,
                description = excluded.description,
                schedule_type = excluded.schedule_type,
                work_from_home = excluded.work_from_home,
                salary = excluded.salary,
                apply_link = excluded.apply_link,
                posted_at = excluded.posted_at,
                scraped_at = excluded.scraped_at,
                via_platform = excluded.via_platform,
                salary_raw = excluded.salary_raw,
                location_type = excluded.location_type,
                skills_required = excluded.skills_required,
                apply_options = excluded.apply_options,
                portal_count = excluded.portal_count,
                salary_min_lpa = excluded.salary_min_lpa,
                salary_max_lpa = excluded.salary_max_lpa,
                source_query = excluded.source_query,
                source_gl = excluded.source_gl,
                is_snapshot = excluded.is_snapshot,
                serpapi_token = excluded.serpapi_token,
                source_queries = excluded.source_queries,
                posted_days_ago = excluded.posted_days_ago;
        """

        with self.get_connection() as con:
            con.execute("BEGIN TRANSACTION;")
            try:
                unique_ids = list({p["job_id"] for p in prepared_jobs})
                placeholders = ", ".join(["?"] * len(unique_ids))
                cur = con.execute(f"SELECT * FROM jobs WHERE job_id IN ({placeholders})", unique_ids)
                existing_records = self._rows_to_dicts(cur)
                merged_map = {r["job_id"]: r for r in existing_records}

                for p in prepared_jobs:
                    jid = p["job_id"]
                    if jid in merged_map:
                        merged_map[jid] = self._merge_job_records(merged_map[jid], p)
                    else:
                        merged_map[jid] = p

                for jid, rec in merged_map.items():
                    opts = rec.get("apply_options")
                    opts_json = json.dumps(opts) if opts is not None else None
                    params = [
                        rec["job_id"], rec.get("title", ""), rec.get("company_name", ""), rec.get("location", ""), rec.get("via", ""),
                        rec.get("description", ""), rec.get("schedule_type", "Full-time"), bool(rec.get("work_from_home", False)),
                        rec.get("salary"), rec.get("apply_link", ""), rec.get("posted_at", ""), rec.get("scraped_at") or datetime.now(timezone.utc).replace(tzinfo=None),
                        rec.get("via_platform", ""), rec.get("salary_raw"), rec.get("location_type", "On-site"), rec.get("skills_required", []),
                        opts_json, rec.get("portal_count", 1), rec.get("salary_min_lpa"), rec.get("salary_max_lpa"),
                        rec.get("source_query"), rec.get("source_gl", "in"), bool(rec.get("is_snapshot", False)),
                        rec.get("serpapi_token"), rec.get("source_queries", []), rec.get("posted_days_ago")
                    ]
                    con.execute(upsert_sql, params)

                con.execute("COMMIT;")
                return len(merged_map)
            except Exception:
                con.execute("ROLLBACK;")
                raise

    def load_snapshots_if_empty(self, snapshots_dir: Optional[str] = None, force: bool = False) -> int:
        """
        Loads snapshots from data/snapshots/*.json if the jobs table is empty, or refreshes
        metadata if force=True.
        Uses snapshot captured_at as scraped_at and sets is_snapshot=True.
        """
        with self.get_connection() as con:
            count = con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            if count > 0 and not force:
                return 0

        if not snapshots_dir:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            snapshots_dir = os.path.join(base_dir, "data", "snapshots")

        if not os.path.exists(snapshots_dir):
            return 0

        snapshot_files = glob.glob(os.path.join(snapshots_dir, "*.json"))
        if not snapshot_files:
            return 0

        total_seeded = 0
        all_normalized = []
        for s_file in snapshot_files:
            try:
                with open(s_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                captured_at = data.get("captured_at")
                raw_jobs = data.get("jobs") or data.get("jobs_results", [])
                q_meta = data.get("query_params", {})
                
                # Import parser dynamically to avoid circular import
                from app.serpapi_client import (
                    parse_indian_salary_to_lpa,
                    extract_salary_from_extensions,
                    extract_posted_at_from_extensions,
                    parse_posted_days_ago
                )

                for item in raw_jobs:
                    # Detected extensions & raw extensions
                    ext = item.get("detected_extensions") or {}
                    extensions_list = item.get("extensions") or []
                    wfh_from_ext = any("work from home" in str(e).lower() for e in extensions_list)
                    loc_str = str(item.get("location") or "")
                    wfh = bool(ext.get("work_from_home", False) or wfh_from_ext or "remote" in loc_str.lower() or "anywhere" in loc_str.lower())
                    sched = ext.get("schedule_type", "Full-time")
                    posted = extract_posted_at_from_extensions(item)
                    posted_days = parse_posted_days_ago(posted)
                    if posted_days is None and captured_at:
                        try:
                            dt_cap = datetime.fromisoformat(str(captured_at).replace("Z", "+00:00"))
                            posted_days = max(0, (datetime.now(timezone.utc) - dt_cap).days)
                        except Exception:
                            posted_days = 0
                    
                    # Extract salary string strictly without relative-time leakage
                    salary_str = extract_salary_from_extensions(item)
                    salary_min, salary_max = parse_indian_salary_to_lpa(salary_str)

                    # Apply options
                    apply_opts = item.get("apply_options", [])
                    apply_link = item.get("apply_link") or (apply_opts[0].get("link") if apply_opts else "")
                    portals = len({opt.get("link") or opt.get("title") for opt in apply_opts}) if apply_opts else 1

                    # Extract highlights if available
                    highlights_parts = []
                    job_highlights = item.get("job_highlights") or []
                    if isinstance(job_highlights, list):
                        for h in job_highlights:
                            if isinstance(h, dict):
                                items = h.get("items") or []
                                if isinstance(items, list):
                                    highlights_parts.extend([str(i) for i in items])
                    highlights_text = " ".join(highlights_parts)
                    combined_text = f"{item.get('title', '')} {item.get('description', '')} {highlights_text}"
                    skills = extract_skills_from_text(combined_text)

                    raw_token = item.get("job_id")
                    title = item.get("title", "Untitled Role")
                    company_name = item.get("company_name", "Unknown Company")
                    loc = item.get("location", "")
                    desc = item.get("description", "")
                    canonical_id = generate_canonical_job_id(title, company_name, loc, desc)
                    q_str = q_meta.get("q", "")

                    all_normalized.append({
                        "job_id": canonical_id,
                        "serpapi_token": raw_token,
                        "title": title,
                        "company_name": company_name,
                        "location": loc,
                        "via": item.get("via", "Direct"),
                        "description": desc,
                        "schedule_type": sched,
                        "work_from_home": bool(wfh),
                        "location_type": "Remote" if wfh else "On-site",
                        "salary": salary_str,
                        "salary_raw": salary_str,
                        "apply_link": apply_link,
                        "posted_at": posted,
                        "posted_days_ago": posted_days,
                        "captured_at": captured_at,
                        "scraped_at": captured_at,
                        "apply_options": apply_opts,
                        "portal_count": portals,
                        "salary_min_lpa": salary_min,
                        "salary_max_lpa": salary_max,
                        "source_query": q_str,
                        "source_queries": [q_str] if q_str else [],
                        "source_gl": q_meta.get("gl", "in"),
                        "is_snapshot": True,
                        "skills_required": skills,
                        "highlights_text": highlights_text
                    })

            except Exception as e:
                print(f"Error loading snapshot {s_file}: {e}")

        if all_normalized:
            total_seeded = self.upsert_jobs(all_normalized, is_snapshot=True)
        return total_seeded

    def get_cached_search(self, cache_key: str, ttl_hours: int = 24, con=None) -> Optional[Dict[str, Any]]:
        should_close = False
        if con is None:
            con = self.get_connection()
            should_close = True
        try:
            cutoff_utc = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=ttl_hours)
            row = con.execute("""
                SELECT response_json, fetched_at FROM search_cache
                WHERE cache_key = ?
                  AND fetched_at >= ?
                ORDER BY fetched_at DESC LIMIT 1;
            """, [cache_key, cutoff_utc]).fetchone()
            if row and row[0]:
                try:
                    data = json.loads(row[0])
                    fetched_at = row[1]
                    if fetched_at:
                        if hasattr(fetched_at, "isoformat"):
                            iso_str = fetched_at.isoformat()
                            if not iso_str.endswith("Z") and "+" not in iso_str:
                                iso_str += "Z"
                            data["fetched_at"] = iso_str
                        else:
                            data["fetched_at"] = str(fetched_at)
                    else:
                        data["fetched_at"] = None
                    return data
                except Exception:
                    return None
            return None
        finally:
            if should_close:
                con.close()

    def set_cached_search(self, cache_key: str, query_meta: Dict[str, Any], response_data: Dict[str, Any], con=None):
        should_close = False
        if con is None:
            con = self.get_connection()
            should_close = True
        try:
            response_json = json.dumps(response_data)
            now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
            con.execute("""
                INSERT INTO search_cache (
                    cache_key, query, location, gl, hl, date_posted, response_json, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (cache_key) DO UPDATE SET
                    response_json = excluded.response_json,
                    fetched_at = excluded.fetched_at;
            """, [
                cache_key,
                query_meta.get("query", ""),
                query_meta.get("location", ""),
                query_meta.get("gl", ""),
                query_meta.get("hl", ""),
                query_meta.get("date_posted", ""),
                response_json,
                now_utc
            ])
        finally:
            if should_close:
                con.close()

    def get_jobs(
        self,
        keyword: Optional[str] = None,
        location_type: Optional[str] = None,
        company: Optional[str] = None,
        has_salary: Optional[bool] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        sort_by: str = "newest",
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        with self.get_connection() as con:
            query = "SELECT * FROM jobs WHERE 1=1"
            params = []

            if keyword and keyword.strip():
                kw = f"%{keyword.strip().lower()}%"
                query += " AND (LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(company_name) LIKE ?)"
                params.extend([kw, kw, kw])

            if location_type and location_type.strip():
                loc_lower = location_type.strip().lower()
                if loc_lower == "remote":
                    query += " AND (work_from_home = TRUE OR LOWER(location) LIKE '%remote%')"
                elif loc_lower == "hybrid":
                    query += " AND (LOWER(location) LIKE '%hybrid%' OR LOWER(description) LIKE '%hybrid%')"
                elif loc_lower == "on-site":
                    query += " AND work_from_home = FALSE AND LOWER(location) NOT LIKE '%remote%' AND LOWER(location) NOT LIKE '%hybrid%'"

            if company and company.strip():
                query += " AND LOWER(company_name) LIKE ?"
                params.append(f"%{company.strip().lower()}%")

            if has_salary is True:
                query += " AND salary IS NOT NULL AND salary != ''"

            if from_date and from_date.strip():
                query += " AND CAST(scraped_at AS DATE) >= ?"
                params.append(from_date.strip())

            if to_date and to_date.strip():
                query += " AND CAST(scraped_at AS DATE) <= ?"
                params.append(to_date.strip())

            if sort_by == "company":
                query += " ORDER BY company_name ASC, scraped_at DESC, job_id ASC"
            elif sort_by == "title":
                query += " ORDER BY title ASC, scraped_at DESC, job_id ASC"
            else:
                query += " ORDER BY scraped_at DESC, job_id ASC"

            query += " LIMIT ? OFFSET ?"
            params.extend([max(1, limit), max(0, offset)])

            cursor = con.execute(query, params)
            return self._rows_to_dicts(cursor)

    def get_analytics(self) -> Dict[str, Any]:
        with self.get_connection() as con:
            counts = con.execute("""
                SELECT 
                    COUNT(*) AS total,
                    SUM(CASE WHEN work_from_home = TRUE OR LOWER(location) LIKE '%remote%' THEN 1 ELSE 0 END) AS remote_count,
                    SUM(CASE WHEN salary IS NOT NULL AND salary != '' THEN 1 ELSE 0 END) AS salary_count
                FROM jobs
            """).fetchone()

            total_jobs = counts[0] if (counts and counts[0] is not None) else 0
            remote_jobs = counts[1] if (counts and counts[1] is not None) else 0
            salary_disclosed = counts[2] if (counts and counts[2] is not None) else 0
            on_site_jobs = max(0, total_jobs - remote_jobs)

            if total_jobs == 0:
                return {
                    "total_jobs": 0,
                    "remote_jobs": 0,
                    "on_site_jobs": 0,
                    "salary_disclosed_jobs": 0,
                    "top_skills": [],
                    "top_companies": [],
                    "top_platforms": []
                }

            # Top hiring companies
            cursor_companies = con.execute("""
                SELECT company_name, COUNT(*) AS count
                FROM jobs
                GROUP BY company_name
                ORDER BY count DESC
                LIMIT 8
            """)
            top_companies = self._rows_to_dicts(cursor_companies)

            # Top platforms (parsed from 'via')
            cursor_platforms = con.execute("""
                SELECT 
                    CASE 
                        WHEN via LIKE '%LinkedIn%' THEN 'LinkedIn'
                        WHEN via LIKE '%Greenhouse%' THEN 'Greenhouse'
                        WHEN via LIKE '%Lever%' THEN 'Lever'
                        WHEN via LIKE '%Workday%' THEN 'Workday'
                        WHEN via LIKE '%Indeed%' THEN 'Indeed'
                        WHEN via LIKE '%Naukri%' THEN 'Naukri'
                        ELSE COALESCE(NULLIF(REPLACE(via, 'via ', ''), ''), 'Direct Portal')
                    END AS platform,
                    COUNT(*) AS count
                FROM jobs
                GROUP BY platform
                ORDER BY count DESC
                LIMIT 6
            """)
            top_platforms = self._rows_to_dicts(cursor_platforms)

            # Skills frequency analysis across job records
            cursor_skills = con.execute("""
                SELECT skill, COUNT(*) AS count
                FROM (
                    SELECT unnest(skills_required) AS skill
                    FROM jobs
                    WHERE skills_required IS NOT NULL
                ) sub
                GROUP BY skill
                ORDER BY count DESC
                LIMIT 15
            """)
            skill_counts = self._rows_to_dicts(cursor_skills)
            if not skill_counts:
                # Fallback if skills_required not yet populated
                all_text = con.execute("""
                    SELECT string_agg(COALESCE(title, '') || ' ' || COALESCE(description, ''), ' ') AS combined
                    FROM jobs
                """).fetchone()[0] or ""

                for skill in TRACKED_SKILLS:
                    pat = SKILL_PATTERNS.get(skill)
                    if pat:
                        if skill == "RAG":
                            m_cnt = len(re.findall(r'(?<![a-zA-Z0-9_#+])RAG(?![a-zA-Z0-9_#+])', all_text)) + len(re.findall(r'retrieval[ -]augmented generation', all_text, re.IGNORECASE))
                        else:
                            m_cnt = len(pat.findall(all_text))
                        if m_cnt > 0:
                            skill_counts.append({"skill": skill, "count": m_cnt})
                skill_counts.sort(key=lambda x: x["count"], reverse=True)

            return {
                "total_jobs": total_jobs,
                "remote_jobs": remote_jobs,
                "on_site_jobs": on_site_jobs,
                "salary_disclosed_jobs": salary_disclosed,
                "top_skills": skill_counts[:12],
                "top_companies": top_companies,
                "top_platforms": top_platforms
            }

    def match_resume(self, resume_text: str) -> Dict[str, Any]:
        matched = extract_skills_from_text(resume_text)
        missing = [s for s in TRACKED_SKILLS if s not in matched]

        with self.get_connection() as con:
            if not matched:
                return {
                    "matched_skills": [],
                    "missing_skills": TRACKED_SKILLS[:8],
                    "match_score_percentage": 0,
                    "recommended_jobs": []
                }

            skill_conditions = " OR ".join(["LOWER(description) LIKE ?" for _ in matched])
            query = f"""
                SELECT job_id, title, company_name, location, via, apply_link, salary, schedule_type
                FROM jobs
                WHERE {skill_conditions}
                ORDER BY scraped_at DESC, job_id ASC
                LIMIT 6
            """
            params = [f"%{s.lower()}%" for s in matched]
            cursor_rec = con.execute(query, params)
            recommended = self._rows_to_dicts(cursor_rec)

        score = int((len(matched) / len(TRACKED_SKILLS)) * 100)

        return {
            "matched_skills": matched,
            "missing_skills": missing[:8],
            "match_score_percentage": min(score * 2, 100),
            "recommended_jobs": recommended
        }

    def execute_readonly_query(self, sql_query: str) -> Dict[str, Any]:
        cleaned = sql_query.strip().rstrip(";")
        if not re.match(r"^SELECT\b", cleaned, re.IGNORECASE):
            raise ValueError("Restricted execution: Only read-only SELECT queries are allowed.")

        forbidden = [
            "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
            "ATTACH", "COPY", "PRAGMA", "EXPORT", "IMPORT", "SHOW",
            "LOAD", "INSTALL", "SET", "CALL", "EXECUTE"
        ]
        for word in forbidden:
            if re.search(r"\b" + word + r"\b", cleaned, re.IGNORECASE):
                raise ValueError(f"Restricted keyword: '{word}' is not permitted in the analytical console.")

        # Rewrite unnest grouping query if needed for DuckDB binder compatibility
        if re.search(r"SELECT\s+unnest\(skills_required\)\s+AS\s+skill,\s+COUNT\(\*\)\s+AS\s+demand_count\s+FROM\s+jobs\s+GROUP\s+BY\s+skill", cleaned, re.IGNORECASE):
            cleaned = re.sub(
                r"SELECT\s+unnest\(skills_required\)\s+AS\s+skill,\s+COUNT\(\*\)\s+AS\s+demand_count\s+FROM\s+jobs\s+GROUP\s+BY\s+skill",
                "SELECT skill, COUNT(*) AS demand_count FROM (SELECT unnest(skills_required) AS skill FROM jobs) _sub GROUP BY skill",
                cleaned,
                flags=re.IGNORECASE
            )

        limit_match = re.search(r"\bLIMIT\s+(\d+)", cleaned, re.IGNORECASE)
        if not limit_match:
            executable_query = f"{cleaned} LIMIT 50"
        else:
            limit_val = int(limit_match.group(1))
            if limit_val > 50:
                executable_query = re.sub(r"\bLIMIT\s+\d+", "LIMIT 50", cleaned, flags=re.IGNORECASE)
            else:
                executable_query = cleaned

        import time
        with self.get_connection() as con:
            t0 = time.perf_counter()
            cursor = con.execute(executable_query)
            cols = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

            # Convert rows to serializable primitive types
            serialized_rows = []
            for row in rows:
                serialized_rows.append([str(v) if v is not None else "" for v in row])

            return {
                "columns": cols,
                "rows": serialized_rows,
                "row_count": len(serialized_rows),
                "latency_ms": elapsed_ms
            }


# Global database instance
db_manager = DatabaseManager()

