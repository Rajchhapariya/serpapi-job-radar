import os
import time
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse, Response
from typing import Optional

from app.models import SearchRequest, ResumeMatchRequest
from app.database import db_manager
from app.serpapi_client import serpapi_client

START_TIME = time.time()

from contextlib import asynccontextmanager

# Sliding-window in-memory rate limiter for expensive search operations
# Allows max 15 search queries per minute per client IP
SEARCH_RATE_LIMIT = 15
SEARCH_WINDOW_SECONDS = 60
ip_request_history = defaultdict(list)


@asynccontextmanager
async def lifespan(app: FastAPI):
    analytics = db_manager.get_analytics()
    if analytics["total_jobs"] == 0:
        result = serpapi_client.fetch_jobs(query="Software Engineer Python", location="India", num_results=10)
        db_manager.upsert_jobs(result["jobs"])
    yield


app = FastAPI(
    title="SerpApi Job & Market Radar",
    description="Real-time job intelligence engine using SerpApi and DuckDB in-memory analytics",
    version="1.2.0",
    lifespan=lifespan
)

# Static directory path
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Security Headers & Rate-Limiting Middleware
@app.middleware("http")
async def security_and_rate_limit_middleware(request: Request, call_next):
    # 1. Rate Limiting on Search Endpoint
    if request.url.path == "/api/search" and request.method == "POST":
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        # Clean timestamps older than 60s
        ip_request_history[client_ip] = [
            ts for ts in ip_request_history[client_ip] if now - ts < SEARCH_WINDOW_SECONDS
        ]
        if len(ip_request_history[client_ip]) >= SEARCH_RATE_LIMIT:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Maximum 15 searches allowed per minute to protect API quota."
            )
        ip_request_history[client_ip].append(now)

    # 2. Process Request
    response: Response = await call_next(request)

    # 3. Inject Defensive Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self';"
    )
    return response





# ==================== SEO & STATIC ROUTES ====================

@app.get("/")
def serve_dashboard():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "SerpApi Job Radar Backend Active. Static dashboard not found."}


@app.get("/robots.txt", response_class=PlainTextResponse)
def serve_robots():
    return """User-agent: *
Allow: /
Allow: /static/
Disallow: /api/
Sitemap: http://127.0.0.1:8000/sitemap.xml
"""


@app.get("/sitemap.xml")
def serve_sitemap():
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>http://127.0.0.1:8000/</loc>
    <lastmod>2026-10-02</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>"""
    return Response(content=xml_content, media_type="application/xml")


# ==================== API ROUTES ====================

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
    keyword: Optional[str] = Query(default=None, max_length=100),
    location_type: Optional[str] = Query(default=None, pattern="^(Remote|On-site|Hybrid)$"),
    company: Optional[str] = Query(default=None, max_length=100),
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
    return db_manager.match_resume(req.resume_text)
