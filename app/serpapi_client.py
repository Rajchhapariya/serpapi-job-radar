import os
import requests
from typing import List, Dict, Any, Optional

SERPAPI_URL = "https://serpapi.com/search.json"


# Reliable fallback dataset used when API key is missing or for demo preview
MOCK_JOBS = [
    {
        "job_id": "mock_01_applied_ai",
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
        "job_id": "mock_02_data_engineer",
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
        "job_id": "mock_03_backend_fastapi",
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
        "job_id": "mock_04_fullstack_nextjs",
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
        "job_id": "mock_05_mlops_pytorch",
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


class SerpApiClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY", "")

    def fetch_jobs(
        self,
        query: str = "Software Engineer",
        location: str = "India",
        num_results: int = 20,
        date_posted: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calls SerpApi's google_jobs engine.
        Falls back to curated demo dataset if API key is unconfigured.
        """
        if not self.api_key or self.api_key.startswith("your_"):
            return {
                "source": "mock_demo",
                "jobs": MOCK_JOBS,
                "message": "SerpApi API key not configured. Using preloaded demonstration dataset."
            }

        params = {
            "engine": "google_jobs",
            "q": query,
            "location": location,
            "hl": "en",
            "gl": "in" if "india" in location.lower() else "us",
            "api_key": self.api_key,
        }
        if date_posted and date_posted in ["today", "3days", "week", "month"]:
            params["chips"] = f"date_posted:{date_posted}"

        try:
            response = requests.get(SERPAPI_URL, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()

            raw_jobs = data.get("jobs_results", [])
            normalized = []

            for item in raw_jobs[:num_results]:
                # Extract detected extensions
                extensions = item.get("detected_extensions", {})
                work_from_home = extensions.get("work_from_home", False)
                schedule_type = extensions.get("schedule_type", "Full-time")
                posted_at = extensions.get("posted_at", "")
                salary = extensions.get("salary", "")

                # Extract primary application link
                apply_options = item.get("apply_options", [])
                apply_link = apply_options[0].get("link", "") if apply_options else ""

                normalized.append({
                    "job_id": item.get("job_id") or f"{item.get('company_name')}_{item.get('title')}",
                    "title": item.get("title", "Untitled Role"),
                    "company_name": item.get("company_name", "Unknown Company"),
                    "location": item.get("location", location),
                    "via": item.get("via", "Direct"),
                    "description": item.get("description", ""),
                    "schedule_type": schedule_type,
                    "work_from_home": bool(work_from_home),
                    "salary": salary,
                    "apply_link": apply_link,
                    "posted_at": posted_at
                })

            return {
                "source": "live_serpapi",
                "jobs": normalized,
                "message": f"Successfully retrieved {len(normalized)} live jobs from SerpApi."
            }

        except Exception as e:
            return {
                "source": "fallback_on_error",
                "jobs": MOCK_JOBS,
                "message": f"SerpApi request failed: {str(e)}. Returned fallback dataset."
            }


# Global client instance
serpapi_client = SerpApiClient()
