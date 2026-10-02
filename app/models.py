from typing import List, Optional
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(
        default="Software Engineer Python",
        min_length=2,
        max_length=100,
        pattern=r"^[a-zA-Z0-9\s\+\#\.\-_/]+$",
        description="Search query with safe alphanumeric, whitespace, and programming character constraints"
    )
    location: str = Field(
        default="India",
        min_length=2,
        max_length=100,
        pattern=r"^[a-zA-Z0-9\s,\.\-_/]+$",
        description="Location or country filter"
    )
    num_results: int = Field(default=20, ge=5, le=100, description="Max jobs to fetch per batch")


class JobFilter(BaseModel):
    keyword: Optional[str] = Field(default=None, max_length=100)
    location_type: Optional[str] = Field(default=None, pattern="^(Remote|On-site|Hybrid)$")
    company: Optional[str] = Field(default=None, max_length=100)
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class JobItem(BaseModel):
    job_id: str
    title: str
    company_name: str
    location: str
    via: str
    description: str
    schedule_type: Optional[str] = None
    work_from_home: bool = False
    salary: Optional[str] = None
    apply_link: Optional[str] = None
    posted_at: Optional[str] = None
    scraped_at: str


class AnalyticsResponse(BaseModel):
    total_jobs: int
    remote_jobs: int
    on_site_jobs: int
    salary_disclosed_jobs: int
    top_skills: List[dict]
    top_companies: List[dict]
    top_platforms: List[dict]


class ResumeMatchRequest(BaseModel):
    resume_text: str = Field(
        ...,
        min_length=5,
        max_length=50000,
        description="Raw resume text or extracted skills with 50KB payload boundary limit"
    )
