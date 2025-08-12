import asyncio
import json
import logging
import sys
from typing import List, Set

logger = logging.getLogger(__name__)


async def check_email_platforms(email: str, timeout: int = 120) -> List[str]:
    """Return a sorted list of platform/service names where the email appears to exist.

    Tries Holehe's programmatic API if available; otherwise falls back to CLI output parsing.
    """
    # Try programmatic API first
    try:
        from holehe.core import check_email as holehe_check_email  # type: ignore
        logger.info("Using Holehe programmatic API")
        results = await holehe_check_email(email)  # May vary across versions
        platforms: Set[str] = set()
        if isinstance(results, dict):
            for service, info in results.items():
                if isinstance(info, dict):
                    exists = bool(info.get("exists")) or (info.get("status") in ("found", "claimed", True))
                else:
                    exists = bool(info)
                if exists:
                    platforms.add(str(service))
        elif isinstance(results, list):
            for item in results:
                if not isinstance(item, dict):
                    continue
                service = item.get("site") or item.get("service") or item.get("platform") or item.get("name")
                exists = item.get("exists") or (item.get("status") in ("found", "claimed", True))
                if service and exists:
                    platforms.add(str(service))
        if platforms:
            return sorted(platforms)
    except Exception as exc:  # noqa: BLE001
        logger.info("Holehe programmatic API unavailable or failed; falling back to CLI: %s", exc)

    # CLI fallback
    return await _check_email_cli(email, timeout)


async def _check_email_cli(email: str, timeout: int = 120) -> List[str]:
    """Invoke Holehe CLI via `python -m holehe` to avoid PATH issues and parse JSON/JSONL output."""
    cmd = [sys.executable or "python3", "-m", "holehe", email, "--no-color", "--json"]
    logger.info("Running CLI: %s", " ".join(cmd))
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            logger.warning("Holehe CLI timed out")
            return []
        text = (stdout or b"").decode("utf-8", "ignore").strip()
        if not text:
            err_text = (stderr or b"").decode("utf-8", "ignore").strip()
            logger.warning("Holehe CLI produced no output. stderr: %s", err_text)
            return []

        platforms: Set[str] = set()
        # Parse JSON or JSONL
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                # Some versions output prefix or text, skip non-JSON lines
                continue
            _collect_platforms_from_obj(obj, platforms)
        return sorted(platforms)
    except FileNotFoundError:
        logger.error("Holehe CLI not found. Ensure the 'holehe' package is installed.")
        return []


def _collect_platforms_from_obj(obj, platforms: Set[str]) -> None:
    if isinstance(obj, dict):
        data = obj.get("result") if isinstance(obj.get("result"), dict) else obj
        service = data.get("site") or data.get("service") or data.get("platform") or data.get("name")
        exists = data.get("exists") or (data.get("status") in ("found", "claimed", True))
        if service and exists:
            platforms.add(str(service))
    elif isinstance(obj, list):
        for item in obj:
            if not isinstance(item, dict):
                continue
            service = item.get("site") or item.get("service") or item.get("platform") or item.get("name")
            exists = item.get("exists") or (item.get("status") in ("found", "claimed", True))
            if service and exists:
                platforms.add(str(service))
