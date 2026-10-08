# SerpApi Job & Market Radar

Paste a resume. Find the one skill that moves you closest to the most open roles, computed from Google Jobs data by deterministic SQL. No LLM.

## Live Demo

{DEPLOY_URL}

Free Render instances sleep after about 15 minutes idle; the first request can take 30 to 60 seconds.

## How the Unlock Engine Works

The engine evaluates technical skill coverage through exact set arithmetic without semantic estimation:

- **Eligible job:** A listing specifying at least 3 recognizable skills (`min_job_skills >= 3`).
- **Match:** A candidate resume covers at least T% of an eligible job's required skills, evaluated strictly using integer math: `m * 100 >= T * n`.
- **Unlock:** A skill not yet in the candidate's resume that lifts an unmet eligible job over the threshold: `(m + 1) * 100 >= T * n`.
- **Greedy path:** A sequential progression of up to 3 skills where each step selects the single skill that maximizes net-new job unlocks.
- **Integer math only:** Zero floating-point rounding errors across all match comparisons.
- **Single DuckDB aggregation:** All single-skill unlock counts and greedy sequences are computed in one analytical query over indexed skill arrays.
- **Python reference equivalence:** A pure-Python implementation executes alongside DuckDB; full mathematical parity is verified by `test_b_sql_vs_python_reference_fixture` on fixture data and `test_b_sql_vs_python_reference_real_corpus` across all eligible corpus jobs.

## SerpApi Integration

- **Engine:** Google Jobs via SerpApi (`google_jobs`).
- **Pagination:** Traversal via `next_page_token` (2 calls, 10 + 9 jobs, 0 duplicates, verified on upstream call).
- **Portal extraction:** Multi-portal job postings from `apply_options` mapped directly to `portal_count`.
- **Regional targeting:** Configured with `gl=in` and `hl=en`.
- **Remote listings:** Filtered with `ltype=1`. SerpApi documentation states Google deprecated this parameter. Across the 8 raw remote capture snapshots (`data/snapshots/remote_*.json`), all 74 returned job listings carried the "Work from home" extension tag. In the deduplicated snapshot corpus, 76 jobs have `location_type = 'Remote'` and 76 have `work_from_home = TRUE`.
- **Caching & quota protection:** In-database search caching with configurable TTL (`CACHE_TTL_HOURS`). Account API quota guard reserves 15 searches before rejecting upstream calls, complemented by a per-run execution budget (`SEARCH_BUDGET_PER_RUN`).
- **Telemetry split:** Response headers and payload isolate `serpapi_ms`, `ingest_ms`, and `query_ms`.

## Data

The baseline corpus contains 392 deduplicated jobs (consolidated from 418 raw records across 43 snapshot files), captured 2 Oct 2026 across 25 distinct search phrases in Bengaluru, Hyderabad, Pune, and remote India. Snapshots are stored in `data/snapshots/` with full provenance documented in `data/snapshots/PROVENANCE.md`.

At server launch, DuckDB automatically seeds itself from snapshot files if the database table is empty, allowing immediate local execution without an active API key. The web interface includes a live panel to fetch fresh listings from Google Jobs through SerpApi; live-fetched rows are lost when the free instance restarts.

Job listings are third-party content retrieved through SerpApi and included for demonstration.

## Measured Numbers

Measured locally, Windows, Python 3.11.9, 392-job corpus (20 runs of `/api/unlock`, sample resume, T=60, default parameters):

- **Returned query_ms:** p50 = 31.68 ms, p95 = 37.11 ms
- **Wall-clock latency:** p50 = 46.72 ms, p95 = 52.57 ms
- **Test suite:** 65 automated unit and integration tests; all 65 pass.

## Run Locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate | Unix: source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -v
python run.py
```

### Environment Variables

- `SERPAPI_API_KEY`: API key for upstream Google Jobs search queries.
- `DUCKDB_PATH`: Storage path for the DuckDB analytical database file.
- `HOST`: Server interface binding (default `127.0.0.1`, production `0.0.0.0`).
- `PORT`: HTTP port binding (default `8000`).
- `CACHE_TTL_HOURS`: Cache retention lifespan for upstream query responses.
- `SEARCH_BUDGET_PER_RUN`: Maximum upstream searches allowed per server process.
- `UNLOCK_RATE_LIMIT`: Sliding-window rate limit for analytical endpoints.
- `ENABLE_SQL_CONSOLE`: Enables the raw read-only SQL endpoint when true (default false; off in production).
- `ENABLE_QUOTA_ENDPOINT`: Enables upstream SerpApi quota inspection when true (default false; off in production).

Deployed on Render via `render.yaml`.

## API Endpoints

- `GET /`: Serves the primary Skill Unlock web application.
- `GET /legacy`: Serves the legacy dashboard view.
- `GET /robots.txt`: Crawler policy directives and sitemap URL declaration.
- `GET /sitemap.xml`: XML sitemap with daily update frequency.
- `GET /api/health`: Service health status, total indexed job count, uptime, and SerpApi connectivity status.
- `GET /api/quota`: Upstream account quota state and process search budget telemetry (disabled unless enabled by environment variable).
- `POST /api/search`: Query Google Jobs via SerpApi or retrieve cached query results.
- `GET /api/jobs`: Filter, paginate, and sort indexed job records.
- `GET /api/analytics`: Aggregate corpus metrics including remote ratios and top skill distributions.
- `POST /api/match-resume`: Calculate coverage and matched skills for raw resume text.
- `POST /api/unlock`: Compute deterministic single-skill unlock gains and greedy 3-skill unlock path.
- `POST /api/fit`: Retrieve individual job fit statuses, roles, and missing skills against threshold.
- `GET /api/roles`: Role taxonomy list with display labels and indexed job counts.
- `GET /api/sample-resume`: Default sample resume text for testing.
- `POST /api/sql`: Read-only SQL query interface over the DuckDB jobs table (disabled unless enabled by environment variable).
- `GET /api/export`: Export filtered job listings to CSV or JSON.

## Known Limitations

- **Corpus scope:** The snapshot corpus represents specific search terms and is not a random sample of the market.
- **Skill taxonomy:** Skill identification uses exact regex matching over a fixed dictionary of 73 tracked skills; unlisted skills are not captured.
- **Role classification:** Roles are categorized via regular expressions on job titles across 5 predefined tracks.
- **Near-duplicates:** Two known near-duplicate clusters (Jitterbit, Tricon) remain unmerged due to minor title variations.
- **Salary disclosure:** Salary was parsed into LPA for only 35 of 392 snapshot jobs (with 42 disclosing text salaries), meaning salary-conditioned unlock modeling is omitted.
- **Path algorithm:** The 3-step greedy progression uses step-wise heuristics rather than a global combinatorial optimum.
- **Match threshold:** Job matching relies on a user-selected integer percentage bar.
- **Rate limiting:** API rate limiters operate in-memory per worker process.
