from typing import List, Optional
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(default="Software Engineer Python", description="Search query")
    location: str = Field(default="India", description="Location or country filter")
    num_results: int = Field(default=20, ge=10, le=100, description="Max jobs to fetch")


class JobFilter(BaseModel):
    keyword: Optional[str] = None
    location_type: Optional[str] = None  # "Remote", "On-site", "Hybrid"
    company: Optional[str] = None
    limit: int = 50
    offset: int = 0


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
    top_skills: List[dict]
    top_companies: List[dict]
    top_platforms: List[dict]


class ResumeMatchRequest(BaseModel):
    resume_text: str = Field(..., description="Raw resume text or extracted skills")
