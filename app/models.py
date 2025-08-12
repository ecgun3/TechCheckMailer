from pydantic import BaseModel, Field
from typing import List, Optional


class AnalyzeRequest(BaseModel):
    domain: str = Field(..., description="Domain name to analyze (e.g., example.com)")
    email: str = Field(..., description="Email address to check")


class AnalyzeResponse(BaseModel):
    technologies: List[str]
    platforms_found: List[str]
    email_draft: str
    meta: Optional[dict] = None