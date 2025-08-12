import asyncio
import json
import logging
import sys
from typing import List, Set, Dict, Any, Tuple

logger = logging.getLogger(__name__)


async def check_email_platforms(email: str, timeout: int = 120) -> List[str]:
    try:
        from holehe.core import check_email as holehe_check_email  # type: ignore
        logger.info("[Holehe] Using programmatic API for %s", email)
        results = await holehe_check_email(email)
        return _extract_platforms(results)
    except Exception as exc:  # noqa: BLE001
        logger.info("[Holehe] Programmatic API failed; trying CLI: %s", exc)
        platforms, _ = await _check_email_cli(email, timeout)
        return sorted(platforms)


def _extract_platforms(results: Any) -> List[str]:
    platforms: Set[str] = set()
    if isinstance(results, dict):
        for service, info in results.items():
            if _exists_from_info(info):
                platforms.add(str(service).lower())
    elif isinstance(results, list):
        for item in results:
            service, exists = _service_exists_from_item(item)
            if service and exists:
                platforms.add(service.lower())
    return sorted(platforms)


def _exists_from_info(info: Any) -> bool:
    if isinstance(info, dict):
        status = str(info.get("status", "")).lower()
        return bool(info.get("exists") or status in {"found", "claimed", "exists", "active"} or info.get("result") is True)
    return bool(info)


def _service_exists_from_item(item: Any) -> Tuple[str, bool]:
    if not isinstance(item, dict):
        return "", False
    service = item.get("site") or item.get("service") or item.get("platform") or item.get("name") or ""
    exists = _exists_from_info(item)
    return str(service), exists


async def _check_email_cli(email: str, timeout: int = 120) -> Tuple[Set[str], Dict[str, Any]]:
    import shutil

    which_path = shutil.which("holehe")
    commands = []
    if which_path:
        commands += [[which_path, email, "--no-color", "--json"], [which_path, "-j", email]]
    commands += [
        ["holehe", email, "--no-color", "--json"],
        ["holehe", "-j", email],
        [sys.executable or "python3", "-m", "holehe", email, "--no-color", "--json"],
        [sys.executable or "python3", "-m", "holehe", "-j", email],
    ]

    last_error: Dict[str, Any] | None = None
    tried: List[List[str]] = []
    for cmd in commands:
        tried.append(cmd)
        logger.info("[Holehe] Running CLI: %s", " ".join(cmd))
        try:
            proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                logger.warning("[Holehe] CLI timed out for: %s", " ".join(cmd))
                last_error = {"error": "timeout", "cmd": cmd}
                continue
            text_out = (stdout or b"").decode("utf-8", "ignore").strip()
            text_err = (stderr or b"").decode("utf-8", "ignore").strip()
            logger.debug("[Holehe] CLI stdout (first 500): %s", text_out[:500])
            if text_err:
                logger.debug("[Holehe] CLI stderr: %s", text_err)

            platforms: Set[str] = set()
            raw_items: List[Any] = []
            for line in text_out.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                raw_items.append(obj)
                _collect_platforms_from_obj(obj, platforms)
            if platforms or raw_items:
                return platforms, {"cmd": cmd, "num_lines": len(raw_items), "stderr": text_err[:300], "tried": tried}
            else:
                last_error = {"error": "no_json_output", "cmd": cmd, "stderr": text_err[:300]}
        except FileNotFoundError as e:
            last_error = {"error": str(e), "cmd": cmd}
            logger.info("[Holehe] CLI not found for cmd: %s", " ".join(cmd))
        except Exception as e:  # noqa: BLE001
            last_error = {"error": str(e), "cmd": cmd}
            logger.warning("[Holehe] CLI failed for cmd %s: %s", " ".join(cmd), e)
    logger.error("[Holehe] All CLI attempts failed: %s", last_error)
    return set(), (last_error or {"tried": tried})


def _collect_platforms_from_obj(obj, platforms: Set[str]) -> None:
    if isinstance(obj, dict):
        data = obj.get("result") if isinstance(obj.get("result"), dict) else obj
        service = data.get("site") or data.get("service") or data.get("platform") or data.get("name")
        status = str(data.get("status", "")).lower()
        exists = data.get("exists") or (status in {"found", "claimed", "exists", "active"})
        if service and exists:
            platforms.add(str(service).lower())
    elif isinstance(obj, list):
        for item in obj:
            s, ex = _service_exists_from_item(item)
            if s and ex:
                platforms.add(s.lower())


async def debug_holehe(email: str) -> Dict[str, Any]:
    """Run Holehe and return detailed debug info for troubleshooting."""
    platforms, info = await _check_email_cli(email, timeout=60)
    return {"platforms": sorted(list(platforms)), "info": info}
