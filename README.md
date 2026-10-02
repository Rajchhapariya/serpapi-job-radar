# SerpApi Job & Market Radar

An automated technical job search and labor-market intelligence pipeline powered by SerpApi's `google_jobs` engine and DuckDB in-memory analytical querying. Built for the SerpApi India Hackathon 2026.

---

## 1. Overview & Problem Solved

Software developers and data engineers frequently spend hours manually browsing fragmented hiring portals (LinkedIn, Greenhouse, Lever, Workday, Indeed, Naukri). Traditional scrapers face IP blocks, TLS fingerprinting, and dynamic CAPTCHAs.

**SerpApi Job & Market Radar** solves this through a decoupled data pipeline:

1. **Live Extraction:** Direct programmatic ingestion from SerpApi's normalized `google_jobs` engine.
2. **Columnar In-Memory Processing:** Automatic upsert into an embedded DuckDB database (`radar.duckdb`), achieving sub-10ms SQL aggregations across titles, locations, salaries, and technical keywords.
3. **Deterministic ATS Matcher:** Instant keyword comparison between candidate resumes and active job postings to identify technical skill gaps without hallucinated scoring.
4. **Obsidian Agency Interface:** A high-precision tactile command center inspired by Linear and Raycast, featuring an asymmetric Bento Grid, 60-FPS HTML5 Sonar Radar sweep, and interactive 3D spotlight cards.

---

## 2. Technical Architecture

```text
+-----------------------+        +---------------------------+
|  Client Dashboard     | <----> |  FastAPI Backend (run.py) |
|  (Vanilla JS / CSS)   |        +---------------------------+
+-----------------------+                      |
                                               v
                                 +---------------------------+
                                 |  Embedded DuckDB Engine   |
                                 |  (radar.duckdb / in-proc) |
                                 +---------------------------+
                                               ^
                                               | (Ingestion)
                                 +---------------------------+
                                 |   SerpApiClient           |
                                 |   (https://serpapi.com)   |
                                 +---------------------------+
                                               ^
                                               |
                                 +---------------------------+
                                 |  Google Jobs API Surface  |
                                 +---------------------------+
```

---

## 3. Technology Stack

- **Backend Runtime:** Python 3.11
- **API Framework:** FastAPI, Uvicorn, Starlette
- **Data Engine:** DuckDB (In-process SQL, regex-based keyword extraction, transactional upserts)
- **Data Source:** SerpApi (`engine=google_jobs`, `https://serpapi.com/search.json`)
- **Frontend Architecture:**
  - Obsidian Depth Design System (`#050608` cosmic space base, `#0c0e16` elevated glass surface).
  - Procedural zero-byte SVG film grain overlay eliminating OLED color banding.
  - Dual volumetric respiratory bloom lighting pools.
  - Interactive HTML5 Canvas Sonar Radar sweep (44.1 Hz / 60 FPS).
  - Specular interior micro-hairlines (`box-shadow: inset 0 1px 1px rgba(255,255,255,0.06)`).
  - Slide-over job inspection drawer.
  - Dual-font typography: Inter (tight headline tracking) + JetBrains Mono (telemetry).
- **Testing:** Pytest unit and regression suite with mock isolation (16 passing tests).

---

## 4. Local Setup & Execution

### Prerequisites

- Python 3.11+
- SerpApi API Key ([serpapi.com/manage-api-key](https://serpapi.com/manage-api-key))

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/Rajchhapariya/serpapi-job-radar.git
   cd serpapi-job-radar
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your SerpApi key:

   ```env
   SERPAPI_API_KEY=your_actual_serpapi_key_here
   HOST=127.0.0.1
   PORT=8000
   DATABASE_PATH=radar.duckdb
   ```

   _(Note: Running without an API key automatically falls back to the preloaded demonstration dataset for immediate local testing)._

4. Run the application:
   ```bash
   python run.py
   ```
   Open your browser to: `http://127.0.0.1:8000`

---

## 5. API Endpoints Reference

| Method | Endpoint            | Description                                                          |
| :----- | :------------------ | :------------------------------------------------------------------- |
| `GET`  | `/`                 | Serves the web dashboard interface                                   |
| `GET`  | `/api/health`       | Returns backend status, uptime, and SerpApi connection state         |
| `POST` | `/api/search`       | Ingests live jobs from SerpApi into DuckDB                           |
| `GET`  | `/api/jobs`         | Queries stored jobs with keyword, location, salary, and sort options |
| `GET`  | `/api/analytics`    | Returns aggregated metrics (top skills, platforms, remote ratio)     |
| `POST` | `/api/match-resume` | Computes keyword overlap, missing technical skills, and matches      |

---

## 6. Automated Test Suite

Run unit and regression tests via Pytest:

```bash
python -m pytest tests/test_radar.py -v
```

All 16 core tests verify:

- Table schema initialization and primary key constraints.
- Ingestion and conflict resolution (`ON CONFLICT DO UPDATE`).
- Regex-based skills frequency calculation in SQL.
- Candidate resume skill extraction and gap matching.
- Empty database zero-division safeguards.
- Pagination boundaries and SQL injection safety.
- Client fallback behavior on unconfigured keys or network timeouts.

---

## 7. SerpApi India Hackathon 2026 Submission Details

- **Event:** SerpApi India Hackathon 2026
- **Submission Deadline:** 10 October 2026 at 23:59 IST
- **Category / Track:** AI Agents & Developer Tools / Market Intelligence
- **Author / Participant:** SerpApi Hackathon Participant
- **Repository:** `https://github.com/Rajchhapariya/serpapi-job-radar`
- **Demo Video Script (Under 3 Minutes):**
  1. **Intro (0:00 - 0:30):** State problem (portal fragmentation, anti-scraping blocks) and show the unified dashboard.
  2. **Live SerpApi Search (0:30 - 1:15):** Trigger a search for _"Software Engineer Python"_ in _"India"_. Show real-time data ingestion and the latency metric.
  3. **DuckDB Analytics (1:15 - 2:00):** Show the Top Demanded Technologies chart and the platform breakdown (LinkedIn vs Greenhouse vs Lever).
  4. **Resume Gap Matcher (2:00 - 2:45):** Paste technical skills into the ATS matcher. Show detected skill overlap percentage, missing keywords, and recommended jobs.
  5. **Conclusion (2:45 - 3:00):** Highlight clean architecture, sub-10ms query latency, and practical utility.
