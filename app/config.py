import os
from typing import Optional


def get_builtwith_api_key() -> Optional[str]:
    return os.getenv("BUILTWITH_API_KEY")


def get_builtwith_api_url() -> str:
    return os.getenv("BUILTWITH_API_URL", "https://api.builtwith.com/free1/api.json")


# Timeouts (seconds)
BUILTWITH_TIMEOUT = int(os.getenv("BUILTWITH_TIMEOUT", "20"))
HOLEHE_TIMEOUT = int(os.getenv("HOLEHE_TIMEOUT", "120"))

# Feature flags
USE_HOLEHE = os.getenv("USE_HOLEHE", "true").lower() in ("1", "true", "yes")
USE_MOCK_PLATFORMS = os.getenv("USE_MOCK_PLATFORMS", "true").lower() in ("1", "true", "yes")

# App server config (for reference when using programmatic run)
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))