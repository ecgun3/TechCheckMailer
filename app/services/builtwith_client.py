import os
import logging
from typing import List, Set

import httpx
import backoff

logger = logging.getLogger(__name__)

API_URL_DEFAULT = "https://api.builtwith.com/free1/api.json"


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status in (429, 500, 502, 503, 504)
    return isinstance(exc, (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.ConnectError))


@backoff.on_exception(
    backoff.expo,
    (httpx.HTTPStatusError, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.ConnectError),
    max_time=30,
    giveup=lambda e: isinstance(e, httpx.HTTPStatusError)
    and e.response is not None
    and e.response.status_code not in (429, 500, 502, 503, 504),
    jitter=backoff.full_jitter,
)
async def _fetch(client: httpx.AsyncClient, url: str, params: dict) -> dict:
    resp = await client.get(url, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


async def fetch_technologies(domain: str, api_key: str) -> List[str]:
    """Fetch technologies used by a domain via BuiltWith.

    Returns a sorted list of technology and category names. Handles multiple
    response schemas (free/paid variants) defensively.
    """
    url = os.getenv("BUILTWITH_API_URL", API_URL_DEFAULT)
    params = {"KEY": api_key, "LOOKUP": domain}

    async with httpx.AsyncClient() as client:
        data = await _fetch(client, url, params)

    technologies = _parse_builtwith_payload(data)
    return sorted(technologies)


def _parse_builtwith_payload(data: dict) -> Set[str]:
    names: Set[str] = set()

    # Common shape: { "Results": [ { "Result": { "Paths": [ { "Technologies": [ {"Name": ... } ] } ] } } ] }
    results = data.get("Results")
    if isinstance(results, list):
        for result_entry in results:
            result_obj = result_entry.get("Result") if isinstance(result_entry, dict) else None
            if not isinstance(result_obj, dict):
                continue
            paths = result_obj.get("Paths", [])
            for path in paths:
                for tech in path.get("Technologies", []):
                    if not isinstance(tech, dict):
                        continue
                    name = tech.get("Name") or tech.get("name") or tech.get("TechnologyName")
                    if name:
                        names.add(name)
                    for cat in tech.get("Categories", []) or []:
                        cat_name = cat.get("Name") or cat.get("name")
                        if cat_name:
                            names.add(cat_name)

    # Alternative shape occasionally seen in examples: { "groups": [ { "categories": [ {"name": ...} ] } ] }
    if not names and isinstance(data.get("groups"), list):
        for group in data.get("groups", []):
            for cat in group.get("categories", []) or []:
                n = cat.get("name")
                if n:
                    names.add(n)

    return names