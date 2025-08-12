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
async def _fetch(client: httpx.AsyncClient, url: str, params: dict, timeout_s: int) -> dict:
    resp = await client.get(url, params=params, timeout=timeout_s)
    logger.info(
        "BuiltWith response: status=%s url=%s",
        resp.status_code,
        resp.request.url if resp.request else url,
    )
    resp.raise_for_status()
    return resp.json()


async def fetch_technologies(domain: str, api_key: str, timeout_s: int = None) -> List[str]:
    """Fetch technologies used by a domain via BuiltWith.

    Returns a sorted list of technology and category names. Handles multiple
    response schemas (free/paid variants) defensively.
    """
    url = os.getenv("BUILTWITH_API_URL", API_URL_DEFAULT)
    params = {"KEY": api_key, "LOOKUP": domain}

    if timeout_s is None:
        from app.config import BUILTWITH_TIMEOUT as timeout_default
        timeout_s = timeout_default

    masked_key = (api_key[:4] + "…") if api_key else "(none)"
    logger.info("Making BuiltWith API call for domain=%s url=%s key=%s", domain, url, masked_key)

    async with httpx.AsyncClient() as client:
        data = await _fetch(client, url, params, timeout_s)

    technologies = _parse_builtwith_payload(data)
    logger.info("Parsed %d technologies/categories from BuiltWith for %s", len(technologies), domain)
    logger.debug("BuiltWith raw keys: %s", list(data.keys()) if isinstance(data, dict) else type(data))
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

    # Alternative example: { "groups": [ { "categories": [ {"name": ...} ] } ] }
    if not names and isinstance(data.get("groups"), list):
        for group in data.get("groups", []):
            for cat in group.get("categories", []) or []:
                n = cat.get("name")
                if n:
                    names.add(n)

    # Fallback: recursively search any nested "Technologies" arrays or tech-like objects
    if not names:
        names |= _recursive_collect_technology_names(data)

    return names


def _recursive_collect_technology_names(node) -> Set[str]:
    collected: Set[str] = set()
    try:
        if isinstance(node, dict):
            # Collect from common keys
            for key in ("Technologies", "technologies", "Technology", "technology"):
                if key in node and isinstance(node[key], list):
                    for tech in node[key]:
                        if isinstance(tech, dict):
                            n = tech.get("Name") or tech.get("name") or tech.get("TechnologyName")
                            if n:
                                collected.add(n)
                            for cat_key in ("Categories", "categories"):
                                for cat in (tech.get(cat_key) or []):
                                    if isinstance(cat, dict):
                                        cn = cat.get("Name") or cat.get("name")
                                        if cn:
                                            collected.add(cn)
            # Recurse
            for v in node.values():
                collected |= _recursive_collect_technology_names(v)
        elif isinstance(node, list):
            for item in node:
                collected |= _recursive_collect_technology_names(item)
    except Exception:
        pass
    return collected