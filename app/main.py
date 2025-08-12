import os
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.models import AnalyzeRequest, AnalyzeResponse
from app.services.builtwith_client import fetch_technologies
from app.services.holehe_client import check_email_platforms
from app.email_drafter import generate_email_draft
from app.config import get_builtwith_api_key, BUILTWITH_TIMEOUT, HOLEHE_TIMEOUT

from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="Tech & Email Intelligence")

# Static and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
async def validate_env():
    if not get_builtwith_api_key():
        # Log-only; user will see friendly error upon request
        import logging
        logging.getLogger(__name__).warning("BUILTWITH_API_KEY missing. Requests will fail until configured.")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(body: AnalyzeRequest):
    api_key = get_builtwith_api_key()
    if not api_key:
        raise HTTPException(status_code=400, detail="BuiltWith API key missing. Set BUILTWITH_API_KEY in environment.")

    warnings = []
    errors = []

    try:
        technologies_task = asyncio.create_task(fetch_technologies(body.domain, api_key, BUILTWITH_TIMEOUT))
    except Exception as exc:
        technologies_task = None
        warnings.append(f"Skipping BuiltWith due to initialization error: {exc}")

    platforms_task = asyncio.create_task(check_email_platforms(body.email, timeout=HOLEHE_TIMEOUT))

    technologies = []
    platforms = []

    try:
        if technologies_task:
            technologies = await technologies_task
    except Exception as exc:
        warnings.append(f"BuiltWith lookup failed: {exc}")

    try:
        platforms = await platforms_task
    except Exception as exc:
        warnings.append(f"Email check failed: {exc}")

    if not technologies:
        warnings.append("No technologies detected from BuiltWith. The site may block the API or no data is available.")
    if not platforms:
        warnings.append("No platforms found for this email. It may be private or rate-limited.")

    email_draft = generate_email_draft(
        domain=body.domain,
        email=body.email,
        technologies=technologies,
        platforms=platforms,
    )

    return AnalyzeResponse(
        technologies=technologies,
        platforms_found=platforms,
        email_draft=email_draft,
        warnings=warnings or None,
        errors=errors or None,
    )