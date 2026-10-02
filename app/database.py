import os
import re
import duckdb
from typing import List, Dict, Any, Optional
from datetime import datetime

DATABASE_FILE = os.getenv("DATABASE_PATH", "radar.duckdb")

TRACKED_SKILLS = [
    "Python", "SQL", "DuckDB", "PostgreSQL", "Next.js", "React", "TypeScript",
    "JavaScript", "FastAPI", "Docker", "Kubernetes", "AWS", "PyTorch", "Git",
    "MongoDB", "Redis", "Kafka", "Linux", "GCP", "GraphQL", "Tailwind"
]


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
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def upsert_jobs(self, jobs: List[Dict[str, Any]]) -> int:
        """
        Inserts new jobs or updates existing ones based on job_id.
        Returns count of processed records.
        """
        if not jobs:
            return 0

        inserted_count = 0
        with self.get_connection() as con:
            for job in jobs:
                job_id = job.get("job_id") or f"{job.get('company_name', '')}_{job.get('title', '')}_{job.get('location', '')}"
                title = job.get("title", "Untitled")
                company_name = job.get("company_name", "Unknown")
                location = job.get("location", "")
                via = job.get("via", "")
                description = job.get("description", "")
                schedule_type = job.get("schedule_type", "Full-time")
                work_from_home = bool(job.get("work_from_home", False))
                salary = job.get("salary", "")
                apply_link = job.get("apply_link", "")
                posted_at = job.get("posted_at", "")

                con.execute("""
                    INSERT INTO jobs (
                        job_id, title, company_name, location, via,
                        description, schedule_type, work_from_home,
                        salary, apply_link, posted_at, scraped_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, now())
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
                        scraped_at = now();
                """, [
                    job_id, title, company_name, location, via,
                    description, schedule_type, work_from_home,
                    salary, apply_link, posted_at
                ])
                inserted_count += 1

        return inserted_count

    def get_jobs(
        self,
        keyword: Optional[str] = None,
        location_type: Optional[str] = None,
        company: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        with self.get_connection() as con:
            query = "SELECT * FROM jobs WHERE 1=1"
            params = []

            if keyword:
                query += " AND (LOWER(title) LIKE ? OR LOWER(description) LIKE ?)"
                kw = f"%{keyword.lower()}%"
                params.extend([kw, kw])

            if location_type:
                loc_lower = location_type.lower()
                if loc_lower == "remote":
                    query += " AND (work_from_home = TRUE OR LOWER(location) LIKE '%remote%')"
                elif loc_lower == "hybrid":
                    query += " AND (LOWER(location) LIKE '%hybrid%' OR LOWER(description) LIKE '%hybrid%')"
                elif loc_lower == "on-site":
                    query += " AND work_from_home = FALSE AND LOWER(location) NOT LIKE '%remote%'"

            if company:
                query += " AND LOWER(company_name) LIKE ?"
                params.append(f"%{company.lower()}%")

            query += " ORDER BY scraped_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor = con.execute(query, params)
            return self._rows_to_dicts(cursor)

    def get_analytics(self) -> Dict[str, Any]:
        with self.get_connection() as con:
            # Total and remote counts
            counts = con.execute("""
                SELECT 
                    COUNT(*) AS total,
                    SUM(CASE WHEN work_from_home = TRUE OR LOWER(location) LIKE '%remote%' THEN 1 ELSE 0 END) AS remote_count
                FROM jobs
            """).fetchone()

            total_jobs = counts[0] if (counts and counts[0] is not None) else 0
            remote_jobs = counts[1] if (counts and counts[1] is not None) else 0
            on_site_jobs = max(0, total_jobs - remote_jobs)

            if total_jobs == 0:
                return {
                    "total_jobs": 0,
                    "remote_jobs": 0,
                    "on_site_jobs": 0,
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

            # Skills frequency analysis across job descriptions and titles
            all_text = con.execute("""
                SELECT string_agg(LOWER(title) || ' ' || LOWER(description), ' ') AS combined
                FROM jobs
            """).fetchone()[0] or ""

            skill_counts = []
            for skill in TRACKED_SKILLS:
                pattern = r'\b' + re.escape(skill.lower()) + r'\b'
                matches = len(re.findall(pattern, all_text))
                if matches > 0:
                    skill_counts.append({"skill": skill, "count": matches})

            skill_counts.sort(key=lambda x: x["count"], reverse=True)

            return {
                "total_jobs": total_jobs,
                "remote_jobs": remote_jobs,
                "on_site_jobs": on_site_jobs,
                "top_skills": skill_counts[:10],
                "top_companies": top_companies,
                "top_platforms": top_platforms
            }

    def match_resume(self, resume_text: str) -> Dict[str, Any]:
        """
        Extracts matched and missing tracked skills against DuckDB job descriptions.
        """
        text_lower = resume_text.lower()
        matched = [s for s in TRACKED_SKILLS if re.search(r'\b' + re.escape(s.lower()) + r'\b', text_lower)]
        missing = [s for s in TRACKED_SKILLS if s not in matched]

        with self.get_connection() as con:
            # Find jobs matching at least one extracted skill
            if not matched:
                return {
                    "matched_skills": [],
                    "missing_skills": TRACKED_SKILLS[:8],
                    "match_score_percentage": 0,
                    "recommended_jobs": []
                }

            skill_conditions = " OR ".join([f"LOWER(description) LIKE '%{s.lower()}%'" for s in matched])
            query = f"""
                SELECT job_id, title, company_name, location, via, apply_link
                FROM jobs
                WHERE {skill_conditions}
                ORDER BY scraped_at DESC
                LIMIT 5
            """
            cursor_rec = con.execute(query)
            recommended = self._rows_to_dicts(cursor_rec)

        score = int((len(matched) / len(TRACKED_SKILLS)) * 100)

        return {
            "matched_skills": matched,
            "missing_skills": missing[:6],
            "match_score_percentage": min(score * 2, 100),
            "recommended_jobs": recommended
        }


# Global database instance
db_manager = DatabaseManager()
