import os
import re
import time
import requests
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

# Explicitly load .env from the project root
ENV_PATH = os.path.join(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(ENV_PATH)

SERPAPI_SEARCH_URL = "https://serpapi.com/search.json"
SERPAPI_ACCOUNT_URL = "https://serpapi.com/account"


def parse_indian_salary_to_lpa(salary_str: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    """
    Parses Indian salary strings into Lakhs Per Annum (LPA).
    Examples:
      - '₹8–12 LPA' -> (8.0, 12.0)
      - '₹50,000–80,000 a month' -> (6.0, 9.6)
      - '₹6 lakh a year' -> (6.0, 6.0)
      - 'INR 14,00,000 - 20,00,000 / year' -> (14.0, 20.0)
      - '$120K a year' -> (None, None)  # Non-INR currencies rejected
      - 'Competitive' -> (None, None)
    Returns (min_lpa, max_lpa). If single value or unable to parse confidently, returns (None, None).
    """
    if not salary_str or not isinstance(salary_str, str):
        return (None, None)

    s = salary_str.strip()

    # Reject hourly or daily rates (keep raw, return None for LPA)
    if re.search(r'\b(hour|hr|day|daily)\b', s, re.IGNORECASE):
        return (None, None)

    # Reject non-INR currencies
    if any(c in s for c in ["$", "€", "£", "USD", "EUR", "GBP", "PLN"]):
        return (None, None)

    # Must contain an Indian currency or scale marker
    has_inr_marker = any(m in s.lower()
                         for m in ["₹", "inr", "rs", "lpa", "lakh", "lac", "l", "k"])
    if not has_inr_marker:
        return (None, None)

    # Normalize unicode dashes, non-breaking spaces, and commas
    s_norm = s.replace("\u2013", "-").replace("\u2014",
                                              "-").replace("\xa0", " ").replace(",", "").strip()

    # Case 0a: Explicit check for 'k' scale annual e.g. '₹50K a year' or '50k / year'
    m_k = re.search(
        r"(?:₹|INR|Rs\.?)?\s*(\d+(?:\.\d+)?)\s*k\s*(?:-\s*(?:(?:₹|INR|Rs\.?)?\s*)?(\d+(?:\.\d+)?)\s*k)?\s*(?:a\s+year|/\s*year|per\s+annum|per\s+year|\bannually\b)",
        s_norm,
        re.IGNORECASE
    )
    if m_k:
        min_k = float(m_k.group(1)) * 1000
        max_k = float(m_k.group(2)) * 1000 if m_k.group(2) else min_k
        min_lpa = round(min_k / 100000.0, 2)
        max_lpa = round(max_k / 100000.0, 2)
        if min_lpa < 1.0 or min_lpa > 200.0 or max_lpa < 1.0 or max_lpa > 200.0:
            return (None, None)
        return (min_lpa, max_lpa)

    # Case 0b: Check for 'k' scale monthly e.g. '₹16K–₹22K a month'
    m_km = re.search(
        r"(?:₹|INR|Rs\.?)?\s*(\d+(?:\.\d+)?)\s*k\s*(?:-\s*(?:(?:₹|INR|Rs\.?)?\s*)?(\d+(?:\.\d+)?)\s*k)?\s*(?:a\s+month|/\s*month|per\s+month|\bmonthly\b)",
        s_norm,
        re.IGNORECASE
    )
    if m_km:
        min_km = float(m_km.group(1)) * 1000
        max_km = float(m_km.group(2)) * 1000 if m_km.group(2) else min_km
        min_lpa = round((min_km * 12) / 100000.0, 2)
        max_lpa = round((max_km * 12) / 100000.0, 2)
        if min_lpa < 1.0 or min_lpa > 200.0 or max_lpa < 1.0 or max_lpa > 200.0:
            return (None, None)
        return (min_lpa, max_lpa)

    # Case 0c: Lakh amounts per month e.g. '₹1.25L–₹2.5L a month' -> must be multiplied by 12 (15.0-30.0 LPA)
    m_lm = re.search(
        r"(?:₹|INR|Rs\.?)?\s*(\d+(?:\.\d+)?)\s*(?:LPA|lakhs?|lacs?|lac|L)\s*(?:-\s*(?:(?:₹|INR|Rs\.?)?\s*)?(\d+(?:\.\d+)?)\s*(?:LPA|lakhs?|lacs?|lac|L)?)?\s*(?:a\s+month|/\s*month|per\s+month|\bmonthly\b)",
        s_norm,
        re.IGNORECASE
    )
    if m_lm:
        min_lm = float(m_lm.group(1)) * 12.0
        max_lm = float(m_lm.group(2)) * 12.0 if m_lm.group(2) else min_lm
        min_lpa = round(min_lm, 2)
        max_lpa = round(max_lm, 2)
        if min_lpa < 1.0 or min_lpa > 200.0 or max_lpa < 1.0 or max_lpa > 200.0:
            return (None, None)
        return (min_lpa, max_lpa)

    # Case 1: LPA / Lakhs / L shorthand annual: e.g. '₹8-12 LPA', '₹15L–₹21L a year', '₹6 lakh a year'
    if not re.search(r'\b(?:a\s+month|/\s*month|per\s+month|\bmonthly\b)', s_norm):
        m_lpa = re.search(
            r"(?:₹|INR|Rs\.?)?\s*(\d+(?:\.\d+)?)\s*(?:LPA|lakhs?|lacs?|lac|L)?\s*(?:-\s*(?:(?:₹|INR|Rs\.?)?\s*)?(\d+(?:\.\d+)?))?\s*(?:LPA|lakhs?|lacs?|lac|L)\b",
            s_norm,
            re.IGNORECASE
        )
        if m_lpa:
            min_v = float(m_lpa.group(1))
            max_v = float(m_lpa.group(2)) if m_lpa.group(2) else min_v
            if min_v < 1.0 or min_v > 200.0 or max_v < 1.0 or max_v > 200.0:
                return (None, None)
            return (round(min_v, 2), round(max_v, 2))

    # Case 2: Monthly salary: e.g. '₹50,000–80,000 a month'
    m_month = re.search(
        r"(?:₹|INR|Rs\.?)\s*(\d+(?:\.\d+)?)\s*(?:-\s*(?:(?:₹|INR|Rs\.?)?\s*)?(\d+(?:\.\d+)?))?\s*(?:a\s+month|/\s*month|per\s+month|\bmonthly\b)",
        s_norm,
        re.IGNORECASE
    )
    if m_month:
        min_mo = float(m_month.group(1))
        max_mo = float(m_month.group(2)) if m_month.group(2) else min_mo
        min_lpa = round((min_mo * 12) / 100000.0, 2)
        max_lpa = round((max_mo * 12) / 100000.0, 2)
        if min_lpa < 1.0 or min_lpa > 200.0 or max_lpa < 1.0 or max_lpa > 200.0:
            return (None, None)
        return (min_lpa, max_lpa)

    # Case 3: Raw annual numbers e.g. 'INR 14,00,000 - 20,00,000 / year'
    m_yr = re.search(
        r"(?:₹|INR|Rs\.?)\s*(\d+(?:\.\d+)?)\s*(?:-\s*(?:(?:₹|INR|Rs\.?)?\s*)?(\d+(?:\.\d+)?))?\s*(?:a\s+year|/\s*year|per\s+annum|per\s+year|\bannually\b)",
        s_norm,
        re.IGNORECASE
    )
    if m_yr:
        min_yr = float(m_yr.group(1))
        max_yr = float(m_yr.group(2)) if m_yr.group(2) else min_yr
        # Only parse if full rupee count >= 100,000. If unitless small numbers like '₹22-₹30 a year', do not guess.
        if min_yr >= 100000:
            min_lpa = round(min_yr / 100000.0, 2)
            max_lpa = round(max_yr / 100000.0, 2)
            if min_lpa < 1.0 or min_lpa > 200.0 or max_lpa < 1.0 or max_lpa > 200.0:
                return (None, None)
            return (min_lpa, max_lpa)
        return (None, None)

    return (None, None)


RELATIVE_TIME_REGEX = re.compile(
    r'^\d+\s+(minute|hour|day|week|month)s?\s+ago$', re.IGNORECASE)
RELATIVE_TIME_KEYWORDS = {"just now", "yesterday", "today"}
NON_SALARY_PATTERNS = {
    "full-time", "full–time", "part-time", "contract", "internship",
    "work from home", "onsite", "hybrid"
}


def sanitize_salary_raw(val: Optional[str]) -> Optional[str]:
    """
    Cleans raw salary values. If the string represents a relative timestamp,
    schedule type, or empty string, strictly returns None (SQL NULL).
    """
    if not val or not isinstance(val, str):
        return None
    trimmed = val.strip()
    if not trimmed:
        return None
    lower = trimmed.lower()
    if lower in RELATIVE_TIME_KEYWORDS or RELATIVE_TIME_REGEX.match(lower):
        return None
    if lower in NON_SALARY_PATTERNS:
        return None
    return trimmed


def extract_salary_from_extensions(item: Dict[str, Any]) -> Optional[str]:
    """
    Extracts salary string from detected_extensions or extensions list.
    Enforces strict currency / compensation markers to prevent false positives
    like '13 hours ago' matching 'rs '.
    """
    ext = item.get("detected_extensions") or {}
    cand = sanitize_salary_raw(ext.get("salary") or item.get("salary"))
    if cand:
        return cand

    for e in (item.get("extensions") or []):
        if not isinstance(e, str):
            continue
        cleaned = sanitize_salary_raw(e)
        if not cleaned:
            continue
        # Strict currency or pay rate check: ₹, INR, Rs., Rs followed by digit, LPA, Lakh, or rate intervals
        if re.search(r'(?:₹|INR|\bRs\.?\s*\d|\bLPA\b|\blakhs?\b|\b(a|per|/)\s*(year|annum|month|hour)\b)', cleaned, re.IGNORECASE):
            return cleaned

    return None


class SerpApiClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY", "")
        self._cached_quota: Optional[Dict[str, Any]] = None
        self._quota_cached_at: float = 0.0
        self.QUOTA_CACHE_TTL_SECONDS = 60.0

    def get_account_quota(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Retrieves remaining search quota from SerpApi Account API.
        Caches response for ~60s to prevent spamming the endpoint.
        Returns dictionary with total_searches_left, plan_searches_left, etc.
        Never raises exceptions; returns None on failure.
        """
        now = time.time()
        if not force_refresh and self._cached_quota and (now - self._quota_cached_at < self.QUOTA_CACHE_TTL_SECONDS):
            return self._cached_quota

        api_key = self.api_key or os.getenv("SERPAPI_API_KEY", "")
        if not api_key or api_key.startswith("your_"):
            return None

        try:
            resp = requests.get(SERPAPI_ACCOUNT_URL, params={
                                "api_key": api_key}, timeout=3.5)
            if resp.status_code == 200:
                data = resp.json()
                self._cached_quota = {
                    "account_email": data.get("account_email"),
                    "plan_id": data.get("plan_id"),
                    "plan_name": data.get("plan_name"),
                    "searches_per_month": data.get("searches_per_month"),
                    "plan_searches_left": data.get("plan_searches_left"),
                    "total_searches_left": data.get("total_searches_left"),
                    "this_month_usage": data.get("this_month_usage"),
                    "extra_credits": data.get("extra_credits")
                }
                self._quota_cached_at = now
                return self._cached_quota
        except Exception:
            pass

        return self._cached_quota

    def get_cached_quota_sync(self) -> Optional[Dict[str, Any]]:
        """
        Non-blocking local read of cached quota for fast /api/health checks.
        """
        return self._cached_quota

    def fetch_jobs(
        self,
        query: str = "Software Engineer",
        location: str = "India",
        gl: str = "in",
        hl: str = "en",
        num_results: int = 20,
        max_pages: int = 2,
        date_posted: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calls SerpApi's live google_jobs engine with pagination and error handling.
        Counts each HTTP call toward quota.
        """
        api_key = self.api_key or os.getenv("SERPAPI_API_KEY", "")
        if not api_key or api_key.startswith("your_"):
            return {
                "source": "api_key_missing",
                "jobs": [],
                "calls_made": 0,
                "serpapi_ms": 0,
                "message": "SERPAPI_API_KEY is not configured. Provide a valid SerpApi key in .env for live ingestion."
            }

        start_time = time.time()
        calls_made = 0
        normalized_jobs = []
        raw_responses = []

        params = {
            "engine": "google_jobs",
            "q": query,
            "location": location,
            "hl": hl,
            "gl": gl,
            "api_key": api_key,
        }
        if date_posted and date_posted in ["today", "3days", "week", "month"]:
            params["chips"] = f"date_posted:{date_posted}"

        current_token: Optional[str] = None
        pages_fetched = 0

        while pages_fetched < max_pages and len(normalized_jobs) < num_results:
            req_params = dict(params)
            if current_token:
                req_params["next_page_token"] = current_token

            try:
                calls_made += 1
                response = requests.get(
                    SERPAPI_SEARCH_URL, params=req_params, timeout=25)
                if response.status_code != 200:
                    serpapi_ms = int((time.time() - start_time) * 1000)
                    return {
                        "source": "serpapi_error",
                        "jobs": normalized_jobs,
                        "calls_made": calls_made,
                        "serpapi_ms": serpapi_ms,
                        "message": f"SerpApi HTTP {response.status_code}: {response.text}"
                    }

                data = response.json()
                raw_responses.append(data)

                if "error" in data:
                    serpapi_ms = int((time.time() - start_time) * 1000)
                    return {
                        "source": "serpapi_error",
                        "jobs": normalized_jobs,
                        "calls_made": calls_made,
                        "serpapi_ms": serpapi_ms,
                        "message": f"SerpApi Error: {data['error']}"
                    }

                raw_jobs = data.get("jobs_results", [])
                if not raw_jobs:
                    break

                for item in raw_jobs:
                    if len(normalized_jobs) >= num_results:
                        break

                    extensions = item.get("detected_extensions") or {}
                    extensions_list = item.get("extensions") or []
                    wfh_from_ext = any("work from home" in str(e).lower() for e in extensions_list)
                    loc_str = str(item.get("location") or location or "")
                    work_from_home = bool(extensions.get("work_from_home", False) or wfh_from_ext or "remote" in loc_str.lower() or "anywhere" in loc_str.lower())
                    schedule_type = extensions.get(
                        "schedule_type", "Full-time")
                    posted_at = extensions.get("posted_at", "")

                    # Extract salary string strictly without false positives
                    salary_raw = extract_salary_from_extensions(item)

                    # Deterministic LPA calculation (1..200 LPA boundary enforced)
                    salary_min_lpa, salary_max_lpa = parse_indian_salary_to_lpa(
                        salary_raw)

                    # Extract apply options and portal count
                    apply_options = item.get("apply_options", [])
                    apply_link = item.get("apply_link") or (
                        apply_options[0].get("link") if apply_options else "")
                    portal_count = len({opt.get("link") or opt.get(
                        "title") for opt in apply_options}) if apply_options else 1

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

                    from app.database import generate_canonical_job_id
                    raw_token = item.get("job_id")
                    title = item.get("title", "Untitled Role")
                    company_name = item.get("company_name", "Unknown Company")
                    loc = item.get("location", location)
                    desc = item.get("description", "")
                    canonical_id = generate_canonical_job_id(title, company_name, loc, desc)

                    normalized_jobs.append({
                        "job_id": canonical_id,
                        "serpapi_token": raw_token,
                        "title": title,
                        "company_name": company_name,
                        "location": loc,
                        "via": item.get("via", "Direct"),
                        "description": desc,
                        "schedule_type": schedule_type,
                        "work_from_home": bool(work_from_home),
                        "location_type": "Remote" if work_from_home else "On-site",
                        "salary": salary_raw,
                        "salary_raw": salary_raw,
                        "salary_min_lpa": salary_min_lpa,
                        "salary_max_lpa": salary_max_lpa,
                        "apply_link": apply_link,
                        "apply_options": apply_options,
                        "portal_count": portal_count,
                        "posted_at": posted_at,
                        "source_query": query,
                        "source_queries": [query] if query else [],
                        "source_gl": gl,
                        "is_snapshot": False,
                        "highlights_text": highlights_text
                    })

                pages_fetched += 1
                # Check for next page token
                next_token = data.get(
                    "serpapi_pagination", {}).get("next_page_token")
                if not next_token or next_token == current_token:
                    break
                current_token = next_token

            except Exception as e:
                serpapi_ms = int((time.time() - start_time) * 1000)
                return {
                    "source": "network_error",
                    "jobs": normalized_jobs,
                    "calls_made": calls_made,
                    "serpapi_ms": serpapi_ms,
                    "serpapi_cached": None,
                    "serpapi_time_taken_s": None,
                    "message": f"SerpApi connection failure: {str(e)}"
                }

        serpapi_ms = int((time.time() - start_time) * 1000)
        first_meta = raw_responses[0].get("search_metadata", {}) if raw_responses else {}
        serpapi_cached = None
        if "cached" in first_meta or "preemptively_cached" in first_meta:
            serpapi_cached = bool(first_meta.get("cached") or first_meta.get("preemptively_cached"))
        serpapi_time_taken_s = first_meta.get("total_time_taken")

        return {
            "source": "live",
            "jobs": normalized_jobs,
            "calls_made": calls_made,
            "serpapi_ms": serpapi_ms,
            "serpapi_cached": serpapi_cached,
            "serpapi_time_taken_s": serpapi_time_taken_s,
            "raw_responses": raw_responses,
            "message": f"Successfully retrieved {len(normalized_jobs)} live jobs from SerpApi in {calls_made} call(s)."
        }


# Global client instance
serpapi_client = SerpApiClient()
