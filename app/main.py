import os
import time
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional

from app.models import SearchRequest, ResumeMatchRequest
from app.database import db_manager
from app.serpapi_client import serpapi_client

START_TIME = time.time()

app = FastAPI(
    title="SerpApi Job & Market Radar",
    description="Real-time job intelligence engine using SerpApi and DuckDB in-memory analytics",
    version="1.1.0"
)

# Path to static assets
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def startup_event():
    # Preload demonstration dataset if database is empty
    analytics = db_manager.get_analytics()
    if analytics["total_jobs"] == 0:
        result = serpapi_client.fetch_jobs(query="Software Engineer Python", location="India", num_results=10)
        db_manager.upsert_jobs(result["jobs"])


@app.get("/")
def serve_dashboard():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "SerpApi Job Radar Backend Active. Static dashboard not found."}


@app.get("/api/health")
def health_check():
    uptime_seconds = int(time.time() - START_TIME)
    analytics = db_manager.get_analytics()
    return {
        "status": "healthy",
        "serpapi_configured": bool(serpapi_client.api_key and not serpapi_client.api_key.startswith("your_")),
        "database": db_manager.db_path,
        "indexed_jobs_count": analytics["total_jobs"],
        "uptime_seconds": uptime_seconds
    }


@app.post("/api/search")
def search_jobs(req: SearchRequest):
    result = serpapi_client.fetch_jobs(query=req.query, location=req.location, num_results=req.num_results)
    inserted = db_manager.upsert_jobs(result["jobs"])
    return {
        "source": result["source"],
        "message": result["message"],
        "retrieved_count": len(result["jobs"]),
        "stored_count": inserted
    }


@app.get("/api/jobs")
def get_jobs(
    keyword: Optional[str] = None,
    location_type: Optional[str] = None,
    company: Optional[str] = None,
    has_salary: Optional[bool] = None,
    sort_by: str = Query(default="newest", pattern="^(newest|company|title)$"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    records = db_manager.get_jobs(
        keyword=keyword,
        location_type=location_type,
        company=company,
        has_salary=has_salary,
        sort_by=sort_by,
        limit=limit,
        offset=offset
    )
    return {"jobs": records, "count": len(records)}


@app.get("/api/analytics")
def get_analytics():
    return db_manager.get_analytics()


@app.post("/api/match-resume")
def match_resume(req: ResumeMatchRequest):
    if not req.resume_text.strip():
        raise HTTPException(status_code=400, detail="Resume text cannot be empty.")
    return db_manager.match_resume(req.resume_text)
