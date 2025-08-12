import os
import asyncio
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

import httpx

from app.models import AnalyzeRequest, AnalyzeResponse
from app.services.builtwith_client import fetch_technologies
from app.services.holehe_client import check_email_platforms, debug_holehe
from app.email_drafter import generate_email_draft, SmartEmailDrafter
from app.config import get_builtwith_api_key, BUILTWITH_TIMEOUT, HOLEHE_TIMEOUT, get_builtwith_api_url

from dotenv import load_dotenv
load_dotenv()

# Basic logging (can be tuned via env LOG_LEVEL)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(title="Tech & Email Intelligence")

# CORS (open for debugging; restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

smart_drafter = SmartEmailDrafter()


@app.on_event("startup")
async def validate_env():
    api_key = get_builtwith_api_key()
    if not api_key:
        logger.warning("BUILTWITH_API_KEY missing. Requests will fail until configured.")
    else:
        logger.info("API Key loaded: %s… (len=%d)", api_key[:6], len(api_key))
        logger.info("API URL: %s", get_builtwith_api_url())


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/test-api")
async def test_api():
    api_key = get_builtwith_api_key()
    url = get_builtwith_api_url()
    if not api_key:
        return {"error": "BUILTWITH_API_KEY missing", "api_key_present": False, "api_key_length": 0}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params={"KEY": api_key, "LOOKUP": "google.com"}, timeout=30.0)
        return {
            "status_code": response.status_code,
            "response": response.json(),
            "api_key_present": True,
            "api_key_length": len(api_key),
            "url": str(response.request.url) if response.request else url,
        }
    except Exception as e:  # noqa: BLE001
        return {"error": str(e), "api_key_present": True, "api_key_length": len(api_key)}


@app.get("/test-holehe")
async def test_holehe(email: str = "test@gmail.com"):
    try:
        details = await debug_holehe(email)
        return details
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


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

    categorized = smart_drafter.categorize_technologies(technologies)
    matched_contexts = smart_drafter.match_platform_contexts(platforms, categorized)
    generated_templates, _ = smart_drafter.generate_templates(
        domain=body.domain,
        email=body.email,
        technologies=technologies,
        platforms=platforms,
    )

    email_draft = generated_templates[0]["body"] if generated_templates else generate_email_draft(
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
        meta={
            "company_technologies": categorized,
            "email_platforms": platforms,
            "matched_contexts": matched_contexts,
            "generated_templates": generated_templates,
            "technologies_count": len(technologies),
        },
    )