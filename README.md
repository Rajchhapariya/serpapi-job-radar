# Job & Market Radar

> **Which skill unlocks the most jobs?**
> Paste a resume or drop a PDF. Find the exact skills that move you closest to the most open roles, computed from Google Jobs data by deterministic DuckDB SQL. Zero LLM hallucinations.

---

## Live Demo & Deployment

- **Live URL:** `https://serpapi-job-radar.onrender.com`
- **Deployment Specification:** Automated blueprint via [`render.yaml`](file:///c:/Users/Rajch/Desktop/Research/serpapi-job-radar/render.yaml) & [`Dockerfile`](file:///c:/Users/Rajch/Desktop/Research/serpapi-job-radar/Dockerfile).
- _Note on Free Instances:_ Free Render web services sleep after 15 minutes of inactivity; initial cold boots take approximately 30 to 45 seconds while DuckDB auto-seeds snapshot data.

---

## Architecture & How the Unlock Engine Works

The analytical engine evaluates technical skill coverage through exact integer set arithmetic without probabilistic language model estimation:

1. **Eligible Job Definition:** A job posting specifying at least 3 recognizable technical skills (`min_job_skills >= 3`).
2. **Match Evaluation:** A candidate resume covers at least $T\%$ of an eligible job's required skills, evaluated strictly using integer math:
   $$\text{matched} \iff m \times 100 \ge T \times n$$
   where $m$ is the number of intersecting skills, $n$ is total distinct skills on the job, and $T$ is the user match threshold (default 60%).
3. **Marginal Skill Unlock:** A skill not yet in the candidate's profile that lifts an unmet eligible job over the threshold:
   $$\text{unlocked} \iff (m + 1) \times 100 \ge T \times n$$
4. **Greedy 3-Skill Path:** A sequential progression of up to 3 skills where each step selects the single skill maximizing cumulative net-new job unlocks.
5. **Integer Math Only:** Zero floating-point rounding errors across all match comparisons.
6. **Single DuckDB Aggregation:** All single-skill unlock counts and greedy sequences are computed in one analytical query over indexed skill arrays.
7. **Python Reference Equivalence:** A pure-Python reference implementation executes alongside DuckDB; mathematical parity is verified by `test_b_sql_vs_python_reference_fixture` on test fixtures and `test_b_sql_vs_python_reference_real_corpus` across all eligible corpus jobs.

---

## Freshness & Recency Intelligence

To solve the issue of stale listings (e.g., job aggregator postings from 6 months or 1 year ago that linger on Google Jobs), the platform implements a 4-pillar freshness system:

1. **Deterministic Age Parsing:** Converts relative posting strings (`"3 hours ago"`, `"2 days ago"`, `"3 weeks ago"`, `"1 month ago"`, `"1 year ago"`) into an exact integer column: `posted_days_ago`.
2. **SQL Recency Boundary Filtering:** Analytical queries filter on `posted_days_ago <= ?` supporting 4 distinct recency tiers:
   - `7d` (Past Week - Ultra Fresh)
   - `14d` (Past Two Weeks)
   - `30d (Active)` (Past Month - Default)
   - `Any` (Entire Historical Corpus)
3. **Visual Freshness Telemetry:** Job cards display visual freshness badges (`Today`, `2d ago`, `1w ago`, `3w ago`).
4. **Smart ATS Portal Prioritization:** Multi-portal job listings prioritize direct company ATS endpoints (`Greenhouse`, `Lever`, `Workday`, `Careers`) and professional networks (`LinkedIn`) ahead of secondary scraper aggregators (`Shine`, `JobMapp`, `ClickJobs`).

---

## Validated PDF Resume Ingestion

- **In-Memory Streaming:** Secure PDF extraction via `pypdf` with strict 5 MB payload boundary protection.
- **Anti-Invoice Structural Verification:** Heuristic content validation ensures uploaded files contain genuine resume sections (`experience`, `education`, `skills`, `projects`) and rejects non-resume PDFs (e.g. invoices, bank statements, receipts).
- **Blank / Scanned Detection:** Rejects non-OCR scanned documents or empty PDFs with descriptive 422 validation diagnostics.

---

## SerpApi Google Jobs Integration

- **Engine:** Google Jobs via SerpApi (`google_jobs`).
- **Automated Pagination:** Traversal via `next_page_token` (2 calls, 10 + 9 jobs, 0 duplicates, verified on upstream call).
- **Multi-Portal Extraction:** Comprehensive job application options captured from `apply_options` mapped directly to `portal_count`.
- **Regional & Language Targeting:** Configured for high-intent technical markets with `gl=in` and `hl=en`.
- **Remote Listings:** Filtered via `ltype=1` and `work_from_home` extension tag extraction.
- **Caching & Quota Guard:** In-database search caching with configurable TTL (`CACHE_TTL_HOURS`). Account API quota guard reserves 15 searches before rejecting upstream calls, complemented by a per-run execution budget (`SEARCH_BUDGET_PER_RUN`).
- **Latency Split Telemetry:** Isolates `serpapi_ms`, `ingest_ms`, and `query_ms` in API responses.

---

## Analytical Corpus & Provenance

The baseline snapshot corpus contains **392 deduplicated jobs** (consolidated from 418 raw records across 43 snapshot files), captured across 25 distinct search phrases in Bengaluru, Hyderabad, Pune, and remote India. Snapshots are stored in `data/snapshots/` with provenance documented in [`data/snapshots/PROVENANCE.md`](file:///c:/Users/Rajch/Desktop/Research/serpapi-job-radar/data/snapshots/PROVENANCE.md).

At server launch, DuckDB automatically seeds itself from snapshot files if the database table is empty, allowing immediate local execution without an active API key. The web interface includes a live panel to fetch fresh listings from Google Jobs through SerpApi in real time.

---

## Performance & Test Metrics

Measured on Python 3.11.9, Windows, 392-job DuckDB corpus (20 iterations of `/api/unlock`, sample resume, $T=60$, default parameters):

- **Analytical Query Latency (`query_ms`):** p50 = 31.68 ms, p95 = 37.11 ms
- **Wall-Clock Response Time:** p50 = 46.72 ms, p95 = 52.57 ms
- **Automated Test Suite:** **77 / 77 automated unit and integration tests passing.**

---

## Local Development Setup

```bash
# 1. Clone repository
git clone https://github.com/Rajchhapariya/serpapi-job-radar.git
cd serpapi-job-radar

# 2. Set up virtual environment
python -m venv .venv
# Windows: .venv\Scripts\activate | Unix: source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements-dev.txt

# 4. Run test suite
pytest -v

# 5. Launch application
python run.py
```

The application will be available at `http://127.0.0.1:8000/`.

---

## Environment Variables

| Variable                | Default        | Description                                                         |
| :---------------------- | :------------- | :------------------------------------------------------------------ |
| `SERPAPI_API_KEY`       | `""`           | Upstream API key for live Google Jobs queries.                      |
| `DUCKDB_PATH`           | `radar.duckdb` | Storage path for the embedded DuckDB database file.                 |
| `HOST`                  | `127.0.0.1`    | Host interface binding (`0.0.0.0` for production).                  |
| `PORT`                  | `8000`         | HTTP port binding (assigned automatically by Render).               |
| `CACHE_TTL_HOURS`       | `24`           | Cache lifespan for upstream search query results.                   |
| `SEARCH_BUDGET_PER_RUN` | `20`           | Maximum upstream searches allowed per server process.               |
| `UNLOCK_RATE_LIMIT`     | `60`           | Sliding-window requests/minute rate limit for analytical endpoints. |
| `ENABLE_SQL_CONSOLE`    | `false`        | Enables read-only DuckDB SQL query endpoint.                        |
| `ENABLE_QUOTA_ENDPOINT` | `false`        | Enables upstream account quota telemetry endpoint.                  |

---

## API Endpoints Reference

- `GET /`: Primary Skill Unlock web application interface.
- `POST /api/resume/parse-pdf`: Ingest and validate PDF resumes (with anti-invoice checks) and extract technical skills.
- `POST /api/unlock`: Compute deterministic single-skill unlock gains, salary benchmarks, and greedy 3-skill unlock path with recency filtering.
- `POST /api/fit`: Retrieve individual job fit statuses, roles, missing skills, verified posting ages, and prioritized direct ATS portals.
- `POST /api/search`: Query Google Jobs via SerpApi or retrieve cached query results.
- `GET /api/jobs`: Filter, paginate, and sort indexed job records with calendar date boundaries.
- `GET /api/analytics`: Aggregate corpus metrics including remote ratios and top skill distributions.
- `POST /api/match-resume`: Calculate coverage and matched skills for raw resume text.
- `GET /api/roles`: Role taxonomy list with display labels and indexed job counts.
- `GET /api/sample-resume`: Default sample resume text for testing.
- `GET /api/health`: Health status, indexed job count, uptime, and SerpApi connectivity state.
- `GET /api/quota`: Upstream account quota state (disabled unless enabled by environment variable).
- `POST /api/sql`: Read-only SQL query interface over DuckDB table (disabled unless enabled by environment variable).
- `GET /api/export`: Export filtered job listings to CSV or JSON.
- `GET /robots.txt`: Crawler policy directives and sitemap URL declaration.
- `GET /sitemap.xml`: XML sitemap with daily update frequency.
