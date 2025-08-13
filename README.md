# Tech & Email Intelligence (BuiltWith + Holehe)

A minimal web app that:
- Fetches technologies used by a domain via the BuiltWith API
- Checks whether an email exists on popular platforms via Holehe
- Generates a personalized email draft referencing discovered technologies and platforms

## Features
- FastAPI backend (async)
- Simple HTML frontend
- Async calls for BuiltWith and Holehe (CLI fallback)
- Graceful error handling and rate-limits with exponential backoff
- Modular, commented code

## Project Structure
```
.
├── app/
│   ├── email_drafter.py
│   ├── main.py
│   ├── models.py
│   └── services/
│       ├── builtwith_client.py
│       └── holehe_client.py
├── templates/
│   └── index.html
├── static/
│   └── style.css
├── requirements.txt
├── Dockerfile
├── Procfile
├── .env.example
└── README.md
```

## Prerequisites
- Python 3.10+
- A BuiltWith API key (free tier works). Sign up at `https://api.builtwith.com/free-api`.

## Setup
1. Clone and enter the project directory.
2. Create a virtual environment and install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
3. Copy `.env.example` to `.env` and set your key:
```bash
cp .env.example .env
# Edit .env and set BUILTWITH_API_KEY
```

## Run locally
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Open `http://localhost:8000`.

## Environment variables
- `BUILTWITH_API_KEY` (required): Your BuiltWith API key
- `BUILTWITH_API_URL` (optional): Override BuiltWith endpoint (defaults to free API)

## Notes on Holehe integration
- The app attempts to use Holehe as a Python module. If the programmatic API is unavailable, it falls back to calling `python -m holehe ... --json` and parses the output.
- Some platforms may rate-limit; the app is resilient and will return partial results when possible.

## Deployment
- This project is a Python backend. Cloudflare Pages is for static sites, so deploy the backend to a Python-friendly host (Render, Railway, Fly.io, Heroku) and optionally host the static frontend on Cloudflare Pages pointing to your backend URL.
- Alternatively, deploy the full app via Docker to any container host.

### Docker
Build and run:
```bash
docker build -t tech-email-intel .
docker run -p 8000:8000 --env BUILTWITH_API_KEY=YOUR_KEY tech-email-intel
```

### Heroku/Render
- Heroku: `Procfile` provided. Set `BUILTWITH_API_KEY` as a config var.
- Render/Railway/Fly.io: Create a service from this repo, set `BUILTWITH_API_KEY`, command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

## Using a local Holehe clone
If you prefer using a local clone instead of PyPI:
```bash
git clone https://github.com/megadose/holehe.git
cd holehe
python3 setup.py install  # installs console script 'holehe' into your active venv
```
If the console script is not on PATH or you want to point explicitly, set:
```bash
export HOLEHE_BIN=/absolute/path/to/holehe   # e.g., /Users/you/holehe/venv/bin/holehe or venv/bin/holehe
export USE_HOLEHE=true
```
Then run the server and test the endpoint:
```bash
uvicorn app.main:app --reload
open http://localhost:8000/test-holehe?email=test%40gmail.com
```

## Disclaimer
- Use responsibly. Respect terms of service and rate limits of all services.
