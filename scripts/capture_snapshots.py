#!/usr/bin/env python3
"""
scripts/capture_snapshots.py

Captures authentic live job market search snapshots directly from SerpApi
and stores them in data/snapshots/<slug>.json.
No mock, fake, or synthetic data.

Operates in 2 batches:
  - Batch 1: queries 1-8, 13-19, 24-30, 35-42 (30 calls)
  - Batch 2: queries 9-12, 20-23, 31-34, 43-45 (15 calls)
"""

import os
import sys
import json
import time
import glob
import argparse
import requests
from datetime import datetime, timezone
from typing import Optional
from dotenv import load_dotenv

# Ensure stdout handles UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Explicitly load .env from project root
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

SERPAPI_SEARCH_URL = "https://serpapi.com/search.json"
SERPAPI_ACCOUNT_URL = "https://serpapi.com/account"
SNAPSHOTS_DIR = os.path.join(ROOT_DIR, "data", "snapshots")

# 45 high-volume technical labor market queries across India tech hubs
ALL_45_QUERIES = [
    # Bengaluru (1-12)
    {"id": 1, "slug": "bengaluru_python_developer", "q": "Python Developer", "location": "Bengaluru, Karnataka, India"},
    {"id": 2, "slug": "bengaluru_java_backend", "q": "Java Backend Developer", "location": "Bengaluru, Karnataka, India"},
    {"id": 3, "slug": "bengaluru_data_analyst_sql", "q": "Data Analyst SQL", "location": "Bengaluru, Karnataka, India"},
    {"id": 4, "slug": "bengaluru_ml_engineer", "q": "ML Engineer", "location": "Bengaluru, Karnataka, India"},
    {"id": 5, "slug": "bengaluru_devops_engineer", "q": "DevOps Engineer", "location": "Bengaluru, Karnataka, India"},
    {"id": 6, "slug": "bengaluru_data_engineer", "q": "Data Engineer Python SQL", "location": "Bengaluru, Karnataka, India"},
    {"id": 7, "slug": "bengaluru_fullstack_react_node", "q": "Full Stack Developer React Node.js", "location": "Bengaluru, Karnataka, India"},
    {"id": 8, "slug": "bengaluru_backend_fastapi", "q": "Backend Developer FastAPI Python", "location": "Bengaluru, Karnataka, India"},
    {"id": 9, "slug": "bengaluru_cloud_aws", "q": "Cloud Engineer AWS Docker", "location": "Bengaluru, Karnataka, India"},
    {"id": 10, "slug": "bengaluru_frontend_react_ts", "q": "Frontend Developer React TypeScript", "location": "Bengaluru, Karnataka, India"},
    {"id": 11, "slug": "bengaluru_ai_llm_engineer", "q": "AI Engineer LLM RAG", "location": "Bengaluru, Karnataka, India"},
    {"id": 12, "slug": "bengaluru_sre_infra", "q": "Site Reliability Engineer Kubernetes", "location": "Bengaluru, Karnataka, India"},

    # Hyderabad (13-23)
    {"id": 13, "slug": "hyderabad_python_developer", "q": "Python Developer", "location": "Hyderabad, Telangana, India"},
    {"id": 14, "slug": "hyderabad_java_backend", "q": "Java Backend Developer", "location": "Hyderabad, Telangana, India"},
    {"id": 15, "slug": "hyderabad_data_analyst_sql", "q": "Data Analyst SQL", "location": "Hyderabad, Telangana, India"},
    {"id": 16, "slug": "hyderabad_ml_engineer", "q": "ML Engineer", "location": "Hyderabad, Telangana, India"},
    {"id": 17, "slug": "hyderabad_devops_engineer", "q": "DevOps Engineer", "location": "Hyderabad, Telangana, India"},
    {"id": 18, "slug": "hyderabad_data_engineer", "q": "Data Engineer SQL Python", "location": "Hyderabad, Telangana, India"},
    {"id": 19, "slug": "hyderabad_fullstack_react_ts", "q": "Full Stack Developer React TypeScript", "location": "Hyderabad, Telangana, India"},
    {"id": 20, "slug": "hyderabad_software_engineer_python", "q": "Software Engineer Python", "location": "Hyderabad, Telangana, India"},
    {"id": 21, "slug": "hyderabad_cloud_aws_gcp", "q": "Cloud Architect AWS", "location": "Hyderabad, Telangana, India"},
    {"id": 22, "slug": "hyderabad_backend_microservices", "q": "Backend Engineer Microservices SQL", "location": "Hyderabad, Telangana, India"},
    {"id": 23, "slug": "hyderabad_qa_automation_python", "q": "QA Automation Engineer Python", "location": "Hyderabad, Telangana, India"},

    # Pune (24-34)
    {"id": 24, "slug": "pune_python_developer", "q": "Python Developer", "location": "Pune, Maharashtra, India"},
    {"id": 25, "slug": "pune_java_backend", "q": "Java Backend Developer", "location": "Pune, Maharashtra, India"},
    {"id": 26, "slug": "pune_data_analyst_sql", "q": "Data Analyst SQL", "location": "Pune, Maharashtra, India"},
    {"id": 27, "slug": "pune_ml_engineer", "q": "ML Engineer", "location": "Pune, Maharashtra, India"},
    {"id": 28, "slug": "pune_devops_engineer", "q": "DevOps Engineer Kubernetes Docker", "location": "Pune, Maharashtra, India"},
    {"id": 29, "slug": "pune_data_engineer", "q": "Data Engineer SQL", "location": "Pune, Maharashtra, India"},
    {"id": 30, "slug": "pune_fullstack_developer", "q": "Full Stack Developer React TypeScript", "location": "Pune, Maharashtra, India"},
    {"id": 31, "slug": "pune_backend_engineer_python", "q": "Backend Engineer Python", "location": "Pune, Maharashtra, India"},
    {"id": 32, "slug": "pune_cloud_aws_infra", "q": "Cloud Infrastructure Engineer AWS", "location": "Pune, Maharashtra, India"},
    {"id": 33, "slug": "pune_frontend_react", "q": "Frontend Engineer React Next.js", "location": "Pune, Maharashtra, India"},
    {"id": 34, "slug": "pune_software_engineer_fastapi", "q": "Software Engineer FastAPI PostgreSQL", "location": "Pune, Maharashtra, India"},

    # Remote (35-45) - Using ltype=1 as per SerpApi Google Jobs parameter docs
    {"id": 35, "slug": "remote_python_developer", "q": "Python Developer", "location": "India", "ltype": "1"},
    {"id": 36, "slug": "remote_java_backend", "q": "Java Backend Developer", "location": "India", "ltype": "1"},
    {"id": 37, "slug": "remote_data_analyst_sql", "q": "Data Analyst SQL", "location": "India", "ltype": "1"},
    {"id": 38, "slug": "remote_ml_engineer", "q": "Machine Learning Engineer PyTorch", "location": "India", "ltype": "1"},
    {"id": 39, "slug": "remote_devops_engineer", "q": "DevOps Engineer Kubernetes Docker", "location": "India", "ltype": "1"},
    {"id": 40, "slug": "remote_backend_fastapi", "q": "Backend Developer FastAPI Python", "location": "India", "ltype": "1"},
    {"id": 41, "slug": "remote_fullstack_react_ts", "q": "Full Stack Developer React TypeScript", "location": "India", "ltype": "1"},
    {"id": 42, "slug": "remote_ai_rag_llm", "q": "AI Engineer LLM RAG", "location": "India", "ltype": "1"},
    {"id": 43, "slug": "remote_data_engineer_python", "q": "Data Engineer Python SQL", "location": "India", "ltype": "1"},
    {"id": 44, "slug": "remote_frontend_nextjs", "q": "Frontend Engineer Next.js React", "location": "India", "ltype": "1"},
    {"id": 45, "slug": "remote_software_engineer_backend", "q": "Backend Software Engineer", "location": "India", "ltype": "1"}
]

BATCH_1_IDS = set(list(range(1, 9)) + list(range(13, 20)) + list(range(24, 31)) + list(range(35, 43)))
# Batch 2 approved reduced: queries 9-12, 20-23, 31-34 only (12 calls). Queries 43-45 omitted.
BATCH_2_IDS = set(list(range(9, 13)) + list(range(20, 24)) + list(range(31, 35)))


def get_plan_searches_left(api_key: str) -> Optional[int]:
    try:
        resp = requests.get(SERPAPI_ACCOUNT_URL, params={"api_key": api_key}, timeout=5)
        if resp.status_code == 200:
            return resp.json().get("plan_searches_left")
    except Exception as e:
        print(f"Warning: could not fetch quota: {e}")
    return None


def check_snapshot_keys() -> bool:
    """
    Audits all snapshot files in data/snapshots/ for credential leakage.
    Prints only 'found'/'not found'. Never displays any part of the API key.
    """
    api_key = os.getenv("SERPAPI_API_KEY", "")
    key_prefix = api_key[:6] if len(api_key) >= 6 else None
    files = glob.glob(os.path.join(SNAPSHOTS_DIR, "*.json"))
    print(f"\n--- CREDENTIAL SANITIZATION AUDIT ({len(files)} files) ---")
    all_clean = True
    for fpath in sorted(files):
        fname = os.path.basename(fpath)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        has_api_key_literal = "api_key" in content
        has_env_key = (api_key in content) if api_key else False
        has_prefix = (key_prefix in content) if key_prefix else False

        status_key = "found" if (has_env_key or has_prefix) else "not found"
        status_literal = "found" if has_api_key_literal else "not found"

        if status_key == "found" or status_literal == "found":
            all_clean = False
            print(f"{fname}: EXPOSURE WARNING (api_key: {status_literal}, env key: {status_key})")
        else:
            print(f"{fname}: clean (api_key: not found, env key: not found)")
    return all_clean


def capture_snapshots(batch: str = "1", max_searches: int = 45):
    api_key = os.getenv("SERPAPI_API_KEY", "")
    if not api_key or api_key.startswith("your_"):
        print("ERROR: SERPAPI_API_KEY is not set or invalid in .env.")
        sys.exit(1)

    os.makedirs(SNAPSHOTS_DIR, exist_ok=True)

    if batch == "1":
        active_queries = [q for q in ALL_45_QUERIES if q["id"] in BATCH_1_IDS]
    elif batch == "2":
        active_queries = [q for q in ALL_45_QUERIES if q["id"] in BATCH_2_IDS]
    else:
        active_queries = ALL_45_QUERIES

    searches_left_before = get_plan_searches_left(api_key)
    print(f"plan_searches_left BEFORE batch {batch}: {searches_left_before}")

    searches_used = 0
    total_jobs_captured = 0

    print(f"Starting snapshot capture [Batch: {batch}] with {len(active_queries)} planned queries...")
    print(f"Output directory: {SNAPSHOTS_DIR}")

    for idx, item in enumerate(active_queries):
        if searches_used >= max_searches:
            print(f"Hard cap of {max_searches} reached. Halting capture.")
            break

        slug = item["slug"]
        q = item["q"]
        loc = item["location"]
        print(f"[{idx+1}/{len(active_queries)}] Querying: '{q}' in '{loc}'...")

        params = {
            "engine": "google_jobs",
            "q": q,
            "location": loc,
            "gl": "in",
            "hl": "en",
            "api_key": api_key
        }
        if item.get("ltype"):
            params["ltype"] = item["ltype"]

        try:
            searches_used += 1
            t0 = time.time()
            resp = requests.get(SERPAPI_SEARCH_URL, params=params, timeout=25)
            duration_ms = int((time.time() - t0) * 1000)

            if resp.status_code != 200:
                print(f"  HTTP error {resp.status_code}: {resp.text[:120]}")
                continue

            data = resp.json()
            if "error" in data:
                print(f"  SerpApi returned error: {data['error']}")
                continue

            raw_jobs = data.get("jobs_results", [])
            captured_at = datetime.now(timezone.utc).isoformat()
            total_jobs_captured += len(raw_jobs)

            # Strip api_key from query_params and pagination before persisting
            pagination_clean = data.get("serpapi_pagination", {})

            q_params = {
                "q": q,
                "location": loc,
                "gl": "in",
                "hl": "en",
                "engine": "google_jobs"
            }
            if item.get("ltype"):
                q_params["ltype"] = item["ltype"]

            snapshot_payload = {
                "slug": slug,
                "captured_at": captured_at,
                "latency_ms": duration_ms,
                "query_params": q_params,
                "jobs_count": len(raw_jobs),
                "jobs": raw_jobs,
                "serpapi_pagination": pagination_clean
            }

            out_file = os.path.join(SNAPSHOTS_DIR, f"{slug}.json")
            out_str = json.dumps(snapshot_payload, indent=2, ensure_ascii=False)
            # Extra safety: strip any stray occurrence of API key
            if api_key in out_str:
                out_str = out_str.replace(api_key, "[REDACTED]")

            with open(out_file, "w", encoding="utf-8") as f:
                f.write(out_str)

            print(f"  Saved {len(raw_jobs)} jobs to {slug}.json in {duration_ms}ms.")

            # Brief courtesy delay between calls
            time.sleep(1.0)

        except Exception as e:
            print(f"  Connection exception during capture: {e}")

    searches_left_after = get_plan_searches_left(api_key)

    print("\n================ BATCH CAPTURE COMPLETED ================")
    print(f"Batch:                    {batch}")
    print(f"Searches Used:            {searches_used} / {len(active_queries)}")
    print(f"plan_searches_left AFTER: {searches_left_after}")
    print(f"Total Jobs Captured:      {total_jobs_captured}")
    print(f"Stored In:                {SNAPSHOTS_DIR}")
    print("=========================================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture live SerpApi job market snapshots.")
    parser.add_argument(
        "--batch",
        type=str,
        default="1",
        choices=["1", "2", "all", "check"],
        help="Batch to capture: '1' (30 calls), '2' (15 calls), 'all' (45 calls), or 'check' (credential audit)"
    )
    parser.add_argument(
        "--max-searches",
        type=int,
        default=45,
        help="Hard cap on maximum SerpApi search calls (default 45)"
    )
    args = parser.parse_args()

    if args.batch == "check":
        check_snapshot_keys()
    else:
        capture_snapshots(batch=args.batch, max_searches=args.max_searches)
        check_snapshot_keys()
