import os
from typing import List

COMMON_DOMAIN_MAPPING = {
    "gmail.com": ["google", "gmail"],
    "outlook.com": ["microsoft", "outlook"],
    "hotmail.com": ["microsoft", "hotmail"],
    "yahoo.com": ["yahoo"],
    "icloud.com": ["apple", "icloud"],
    "proton.me": ["proton"],
    "protonmail.com": ["proton"],
    "github.com": ["github", "developer"],
}

MOCK_EMAIL_PLATFORMS = {
    "test@gmail.com": ["google", "gmail"],
    "dev@github.com": ["github", "google"],
    "contact@shopify.com": ["corporate", "linkedin", "twitter"],
    "admin@stripe.com": ["github", "linkedin"],
    "info@microsoft.com": ["microsoft", "linkedin"],
}


def detect_platforms_from_email_domain(email: str) -> List[str]:
    if "@" not in email:
        return []
    domain = email.split("@", 1)[1].lower().strip()
    platforms = COMMON_DOMAIN_MAPPING.get(domain, [])
    return list(dict.fromkeys([p.lower() for p in platforms]))


def mock_platforms_for_testing(email: str) -> List[str]:
    platforms = MOCK_EMAIL_PLATFORMS.get(email.lower().strip(), [])
    return list(dict.fromkeys([p.lower() for p in platforms]))


def detect_platforms(email: str, company_domain: str) -> List[str]:
    """Detect platforms without external APIs.

    Strategy:
    1) If USE_MOCK_PLATFORMS=true and email is in mock, return mock platforms
    2) If email domain equals company domain, add corporate/business
    3) Add platforms based on email domain (gmail/outlook/etc.)
    """
    use_mock = os.getenv("USE_MOCK_PLATFORMS", "true").lower() in ("1", "true", "yes")

    platforms: List[str] = []
    email_l = email.lower().strip()
    company_domain_l = company_domain.lower().strip()

    if use_mock:
        platforms.extend(mock_platforms_for_testing(email_l))

    if "@" in email_l:
        edomain = email_l.split("@", 1)[1]
        if edomain == company_domain_l:
            platforms.extend(["corporate", "business"])  # high confidence company email

    platforms.extend(detect_platforms_from_email_domain(email_l))

    # Deduplicate, normalize
    seen = set()
    deduped: List[str] = []
    for p in platforms:
        pl = p.lower()
        if pl not in seen and pl:
            seen.add(pl)
            deduped.append(pl)
    return deduped