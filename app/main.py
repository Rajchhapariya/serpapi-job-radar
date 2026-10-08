from contextlib import asynccontextmanager
from app.serpapi_client import serpapi_client
from app.database import db_manager
from app.models import SearchRequest, ResumeMatchRequest, SQLQueryRequest, UnlockRequest, FitRequest
from app.unlock import (
    parse_and_validate_skills_input,
    get_corpus_stats,
    compute_skill_unlocks,
    compute_job_fit,
    get_roles_summary
)
from app.pdf_parser import validate_and_extract_resume_pdf
import os
import io
import csv
import json
import time
import hashlib
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse, Response, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Optional, Tuple
from dotenv import load_dotenv

# Explicitly load .env from project root
ENV_PATH = os.path.join(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(ENV_PATH)


START_TIME = time.time()

# Quota Guard and Budget configuration
try:
    _budget_val = os.getenv("SEARCH_BUDGET_PER_RUN", "50")
    SEARCH_BUDGET_PER_RUN = int(_budget_val) if _budget_val.lower() not in [
        "unknown", "unlimited", "0"] else 0
except Exception:
    SEARCH_BUDGET_PER_RUN = 50

CACHE_TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", "24"))
process_searches_made = 0


# Sliding-window in-memory rate limiter for expensive search operations
# Allows max 15 search queries per minute per client IP
SEARCH_RATE_LIMIT = 15
SEARCH_WINDOW_SECONDS = 60
ip_request_history = defaultdict(list)

# Sliding-window in-memory rate limiter for matching & unlock operations
UNLOCK_RATE_LIMIT = int(os.getenv("UNLOCK_RATE_LIMIT", "60"))
UNLOCK_WINDOW_SECONDS = 60
ip_unlock_history = defaultdict(list)


def get_search_cache_key(query: str, location: str, gl: str, hl: str, date_posted: Optional[str]) -> str:
    raw = f"{query.strip().lower()}|{location.strip().lower()}|{(gl or 'in').strip().lower()}|{(hl or 'en').strip().lower()}|{date_posted or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def check_quota_guard() -> Tuple[bool, Optional[str]]:
    """
    Checks Account API plan_searches_left with a reserve of 15 searches.
    The per-process search budget is used as secondary guard.
    """
    quota = serpapi_client.get_account_quota()
    if quota and quota.get("plan_searches_left") is not None:
        plan_left = quota["plan_searches_left"]
        if plan_left <= 15:
            return False, f"SerpApi account reserve limit reached ({plan_left} searches remaining on plan, reserve threshold is 15)."

    if SEARCH_BUDGET_PER_RUN > 0 and process_searches_made >= SEARCH_BUDGET_PER_RUN:
        return False, f"Process search budget exhausted ({process_searches_made}/{SEARCH_BUDGET_PER_RUN} calls executed in this run)."

    return True, None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Load snapshots if table is empty (idempotent)
    db_manager.load_snapshots_if_empty()

    # 2. Pre-cache account quota in background for fast health checks
    serpapi_client.get_account_quota()

    # 3. If table is still empty, fallback to seed
    analytics = db_manager.get_analytics()
    if analytics["total_jobs"] == 0:
        result = serpapi_client.fetch_jobs(
            query="Software Engineer Python", location="India", num_results=10)
        if result.get("jobs"):
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
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Maximum 15 searches allowed per minute to protect API quota."}
            )
        ip_request_history[client_ip].append(now)

    # 2. Rate Limiting on Unlock, Fit, and Sample-Resume Endpoints
    if request.url.path in ("/api/unlock", "/api/fit", "/api/sample-resume"):
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        ip_unlock_history[client_ip] = [
            ts for ts in ip_unlock_history[client_ip] if now - ts < UNLOCK_WINDOW_SECONDS
        ]
        if len(ip_unlock_history[client_ip]) >= UNLOCK_RATE_LIMIT:
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded. Maximum {UNLOCK_RATE_LIMIT} requests allowed per minute."}
            )
        ip_unlock_history[client_ip].append(now)

    # 3. Process Request
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


# ==================== ERROR HANDLERS (404 & 500) ====================

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    accept = request.headers.get("accept", "")
    if exc.status_code == 404:
        if request.url.path.startswith("/api/") or "application/json" in accept:
            return JSONResponse(
                status_code=404,
                content={"detail": exc.detail}
            )
        page_404 = os.path.join(STATIC_DIR, "404.html")
        if os.path.exists(page_404):
            return FileResponse(page_404, status_code=404)
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    if request.url.path.startswith("/api/") or "application/json" in accept:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def custom_500_exception_handler(request: Request, exc: Exception):
    accept = request.headers.get("accept", "")
    if request.url.path.startswith("/api/") or "application/json" in accept:
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error",
                     "detail": str(exc), "path": request.url.path}
        )
    page_500 = os.path.join(STATIC_DIR, "500.html")
    if os.path.exists(page_500):
        return FileResponse(page_500, status_code=500)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": str(exc)}
    )


# ==================== SEO & STATIC ROUTES ====================

@app.get("/")
def serve_dashboard():
    new_index = os.path.join(STATIC_DIR, "app", "index.html")
    if os.path.exists(new_index):
        return FileResponse(new_index)
    return {"message": "Skill Unlock Dashboard not found."}


@app.get("/legacy")
def serve_legacy_dashboard():
    new_index = os.path.join(STATIC_DIR, "app", "index.html")
    if os.path.exists(new_index):
        return FileResponse(new_index)
    return {"message": "Skill Unlock Dashboard not found."}


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
    cached_quota = serpapi_client.get_cached_quota_sync()
    
    quota_ok = None
    if cached_quota and "plan_searches_left" in cached_quota and cached_quota["plan_searches_left"] is not None:
        quota_ok = cached_quota["plan_searches_left"] > 15
    elif not serpapi_client.api_key or serpapi_client.api_key.startswith("your_"):
        quota_ok = None

    return {
        "status": "healthy",
        "indexed_jobs_count": analytics["total_jobs"],
        "uptime_seconds": uptime_seconds,
        "serpapi_configured": bool(serpapi_client.api_key and not serpapi_client.api_key.startswith("your_")),
        "quota_ok": quota_ok
    }


@app.get("/api/quota")
def get_quota():
    if not os.getenv("ENABLE_QUOTA_ENDPOINT", "false").lower() in ("true", "1", "yes"):
        raise HTTPException(status_code=404, detail="Not found")
    quota = serpapi_client.get_account_quota()
    cleaned_quota = None
    if quota:
        cleaned_quota = dict(quota)
        cleaned_quota.pop("account_email", None)
    return {
        "quota": cleaned_quota,
        "process_searches_made": process_searches_made,
        "search_budget_per_run": SEARCH_BUDGET_PER_RUN
    }


@app.post("/api/search")
def search_jobs(req: SearchRequest):
    global process_searches_made
    cache_key = get_search_cache_key(
        req.query, req.location, req.gl or "in", req.hl or "en", req.date_posted)

    # 1. Check cache first
    t_read = time.perf_counter()
    cached = db_manager.get_cached_search(cache_key, ttl_hours=CACHE_TTL_HOURS)
    read_ms = round((time.perf_counter() - t_read) * 1000, 2)
    if cached:
        fetched_at_str = cached.get("fetched_at")
        return {
            "source": "cache",
            "message": f"Served from cache (originally fetched at {fetched_at_str}).",
            "retrieved_count": len(cached.get("jobs", [])),
            "stored_count": 0,
            "serpapi_ms": None,
            "serpapi_cached": None,
            "serpapi_time_taken_s": None,
            "ingest_ms": None,
            "query_ms": read_ms,
            "notice": cached.get("notice"),
            "fetched_at": fetched_at_str
        }

    # 2. Check quota guard before live call
    allowed, notice = check_quota_guard()
    if not allowed:
        t_stale = time.perf_counter()
        stale = db_manager.get_cached_search(cache_key, ttl_hours=999999)
        stale_ms = round((time.perf_counter() - t_stale) * 1000, 2)
        if stale:
            stale_fetched_at = stale.get("fetched_at")
            return {
                "source": "cache",
                "message": f"Served from cache (originally fetched at {stale_fetched_at}).",
                "notice": notice,
                "retrieved_count": len(stale.get("jobs", [])),
                "stored_count": 0,
                "serpapi_ms": None,
                "serpapi_cached": None,
                "serpapi_time_taken_s": None,
                "ingest_ms": None,
                "query_ms": stale_ms,
                "fetched_at": stale_fetched_at
            }
        raise HTTPException(
            status_code=429,
            detail=f"Search quota budget reached: {notice}"
        )

    # 3. Live SerpApi Call
    result = serpapi_client.fetch_jobs(
        query=req.query,
        location=req.location,
        gl=req.gl or "in",
        hl=req.hl or "en",
        num_results=req.num_results,
        max_pages=req.max_pages or 2,
        date_posted=req.date_posted
    )
    calls = result.get("calls_made", 1)
    process_searches_made += calls
    serpapi_ms = result.get("serpapi_ms", 0)
    serpapi_cached = result.get("serpapi_cached")
    serpapi_time_taken_s = result.get("serpapi_time_taken_s")

    if result.get("jobs"):
        t_ingest = time.perf_counter()
        inserted = db_manager.upsert_jobs(
            result["jobs"],
            is_snapshot=False,
            source_query=req.query,
            source_gl=req.gl or "in"
        )
        ingest_ms = round((time.perf_counter() - t_ingest) * 1000, 2)

        # Store in cache
        db_manager.set_cached_search(
            cache_key,
            {
                "query": req.query,
                "location": req.location,
                "gl": req.gl or "in",
                "hl": req.hl or "en",
                "date_posted": req.date_posted
            },
            {
                "jobs": result["jobs"],
                "message": result["message"]
            }
        )

        return {
            "source": "live",
            "message": result["message"],
            "retrieved_count": len(result["jobs"]),
            "stored_count": inserted,
            "serpapi_ms": serpapi_ms,
            "serpapi_cached": serpapi_cached,
            "serpapi_time_taken_s": serpapi_time_taken_s,
            "ingest_ms": ingest_ms,
            "query_ms": None,
            "fetched_at": None
        }
    else:
        if result.get("source") in ["live", "live_serpapi"]:
            return {
                "source": "live",
                "message": "No job listings matched your search criteria on Google Jobs.",
                "retrieved_count": 0,
                "stored_count": 0,
                "serpapi_ms": serpapi_ms,
                "serpapi_cached": serpapi_cached,
                "serpapi_time_taken_s": serpapi_time_taken_s,
                "ingest_ms": None,
                "query_ms": None,
                "fetched_at": None
            }
        raise HTTPException(
            status_code=502,
            detail=result.get(
                "message", "Upstream SerpApi query failed. Please verify API key and network connectivity.")
        )


@app.get("/api/jobs")
def get_jobs(
    keyword: Optional[str] = Query(default=None, max_length=100),
    location_type: Optional[str] = Query(
        default=None, pattern="^(Remote|On-site|Hybrid)$"),
    company: Optional[str] = Query(default=None, max_length=100),
    has_salary: Optional[bool] = None,
    from_date: Optional[str] = Query(
        default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    to_date: Optional[str] = Query(
        default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    sort_by: str = Query(default="newest", pattern="^(newest|company|title)$"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    if from_date and to_date and from_date > to_date:
        raise HTTPException(
            status_code=422,
            detail="Invalid date range: from_date cannot be later than to_date"
        )

    t_read = time.perf_counter()
    records = db_manager.get_jobs(
        keyword=keyword,
        location_type=location_type,
        company=company,
        has_salary=has_salary,
        from_date=from_date,
        to_date=to_date,
        sort_by=sort_by,
        limit=limit,
        offset=offset
    )
    query_ms = round((time.perf_counter() - t_read) * 1000, 2)
    return {"jobs": records, "count": len(records), "query_ms": query_ms, "ingest_ms": None}


@app.get("/api/analytics")
def get_analytics():
    t_read = time.perf_counter()
    res = db_manager.get_analytics()
    query_ms = round((time.perf_counter() - t_read) * 1000, 2)
    res["query_ms"] = query_ms
    res["ingest_ms"] = None
    return res


@app.post("/api/match-resume")
def match_resume(req: ResumeMatchRequest):
    return db_manager.match_resume(req.resume_text)


@app.post("/api/unlock")
def unlock_skills(req: UnlockRequest):
    r_skills, ignored_skills = parse_and_validate_skills_input(
        resume_text=req.resume_text,
        skills=req.skills
    )
    with db_manager.get_connection() as con:
        corpus_data, corpus_ms = get_corpus_stats(con)
        unlock_res = compute_skill_unlocks(
            con=con,
            R=r_skills,
            threshold=req.threshold,
            min_job_skills=req.min_job_skills,
            location_type=req.location_type,
            role=req.role,
            top_n=req.top_n,
            max_age_days=req.max_age_days
        )

    total_query_ms = round(corpus_ms + unlock_res["query_ms"], 2)
    return {
        "resume_skills": r_skills,
        "ignored_skills": ignored_skills,
        "threshold": req.threshold,
        "min_job_skills": req.min_job_skills,
        "baseline": unlock_res["baseline"],
        "salary_benchmark": unlock_res.get("salary_benchmark"),
        "unlocks": unlock_res["unlocks"],
        "path": unlock_res["path"],
        "corpus": corpus_data,
        "query_ms": total_query_ms
    }


@app.post("/api/fit")
def fit_jobs(req: FitRequest):
    r_skills, _ignored = parse_and_validate_skills_input(
        resume_text=req.resume_text,
        skills=req.skills
    )
    with db_manager.get_connection() as con:
        corpus_data, corpus_ms = get_corpus_stats(con)
        jobs, fit_ms = compute_job_fit(
            con=con,
            R=r_skills,
            threshold=req.threshold,
            min_job_skills=req.min_job_skills,
            location_type=req.location_type,
            role=req.role,
            limit=req.limit,
            max_age_days=req.max_age_days
        )

    total_query_ms = round(corpus_ms + fit_ms, 2)
    return {
        "jobs": jobs,
        "corpus": corpus_data,
        "query_ms": total_query_ms
    }


@app.get("/api/roles")
def get_roles():
    with db_manager.get_connection() as con:
        return get_roles_summary(con)


@app.get("/api/sample-resume")
def get_sample_resume():
    sample_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "sample_resume.txt"
    )
    if not os.path.exists(sample_file):
        raise HTTPException(status_code=404, detail="sample_resume.txt not found.")
    with open(sample_file, "r", encoding="utf-8") as f:
        content = f.read()
    return {"text": content}


@app.post("/api/resume/parse-pdf")
async def parse_resume_pdf(request: Request):
    content_len = request.headers.get("content-length")
    if content_len and int(content_len) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File size exceeds 5MB limit.")

    body = await request.body()
    if len(body) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File size exceeds 5MB limit.")

    try:
        result = validate_and_extract_resume_pdf(body)
        return result
    except ValueError as ve:
        msg = str(ve)
        if "exceeds 5MB" in msg:
            raise HTTPException(status_code=413, detail=msg)
        raise HTTPException(status_code=422, detail=msg)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to process PDF: {str(e)}")



@app.post("/api/sql")
def execute_sql(req: SQLQueryRequest):
    if not os.getenv("ENABLE_SQL_CONSOLE", "false").lower() in ("true", "1", "yes"):
        raise HTTPException(status_code=404, detail="Not found")
    try:
        return db_manager.execute_readonly_query(req.query)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"DuckDB SQL Execution Error: {str(e)}")


@app.get("/api/export")
def export_jobs(
    format: str = Query(default="csv", pattern="^(csv|json)$"),
    keyword: Optional[str] = Query(default=None, max_length=100),
    location_type: Optional[str] = Query(
        default=None, pattern="^(Remote|On-site|Hybrid)$"),
    from_date: Optional[str] = Query(
        default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    to_date: Optional[str] = Query(
        default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    has_salary: Optional[bool] = None,
    limit: int = Query(default=500, ge=1, le=1000)
):
    if from_date and to_date and from_date > to_date:
        raise HTTPException(
            status_code=422, detail="from_date cannot be later than to_date")

    records = db_manager.get_jobs(
        keyword=keyword,
        location_type=location_type,
        from_date=from_date,
        to_date=to_date,
        has_salary=has_salary,
        limit=limit
    )

    if format == "json":
        return Response(
            content=json.dumps(records, indent=2, default=str),
            media_type="application/json",
            headers={
                "Content-Disposition": "attachment; filename=serpapi_jobs_radar.json"}
        )

    # CSV Export
    output = io.StringIO()
    if records:
        writer = csv.DictWriter(output, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)
    else:
        writer = csv.writer(output)
        writer.writerow(["message"])
        writer.writerow(["No records found matching filters."])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=serpapi_jobs_radar.csv"}
    )
