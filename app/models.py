from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import re

DOMAIN_REGEX = re.compile(r"^(?:[a-zA-Z0-9-]{1,63}\.)+[a-zA-Z]{2,63}$")


class AnalyzeRequest(BaseModel):
    domain: str = Field(..., description="Domain name to analyze (e.g., example.com)")
    email: EmailStr = Field(..., description="Email address to check")

    @classmethod
    def validate_domain(cls, v: str) -> str:
        if not v or not DOMAIN_REGEX.match(v):
            raise ValueError("Invalid domain format. Use e.g. example.com")
        return v

    # Pydantic v1 style custom validator
    def __init__(self, **data):
        super().__init__(**data)
        object.__setattr__(self, "domain", self.validate_domain(self.domain))


class AnalyzeResponse(BaseModel):
    technologies: List[str]
    platforms_found: List[str]
    email_draft: str
    warnings: Optional[List[str]] = None
    errors: Optional[List[str]] = None
    meta: Optional[dict] = None