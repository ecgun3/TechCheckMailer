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

from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="Tech & Email Intelligence")

# Static and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(body: AnalyzeRequest):
    api_key = os.getenv("BUILTWITH_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="BUILTWITH_API_KEY is not set")

    technologies_task = asyncio.create_task(fetch_technologies(body.domain, api_key))
    platforms_task = asyncio.create_task(check_email_platforms(body.email))

    technologies, platforms = await asyncio.gather(technologies_task, platforms_task)

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
    )