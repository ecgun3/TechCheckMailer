from typing import Iterable, Dict, List, Set, Tuple
import re


def generate_email_draft(domain: str, email: str, technologies: Iterable[str], platforms: Iterable[str]) -> str:
    tech_list = ", ".join(sorted(set(technologies))) if technologies else "your current stack"
    platform_list = ", ".join(sorted(set(platforms))) if platforms else "several platforms"

    return (
        f"Hello,\n\n"
        f"I was reviewing {domain} and noticed you're leveraging {tech_list}."
        f" I also saw that {email} has a footprint on {platform_list}.\n\n"
        f"Given this setup, I believe we can help you get more out of your stack — whether it's improving performance, reducing costs, or shipping faster."
        f" If you're open to it, I'd love to share a few ideas tailored to your current tools.\n\n"
        f"Would you be available for a quick chat this week?\n\n"
        f"Best regards,\n"
        f"[Your Name]"
    )


# --- Smart Email Drafter ---

TECH_CATEGORIES: Dict[str, List[str]] = {
    "development": ["react", "vue", "angular", "node.js", "nodejs", "python", "ruby", "javascript", "typescript", "next.js", "nextjs", "nuxt", "django", "flask"],
    "enterprise": ["salesforce", "microsoft-365", "office-365", "sharepoint", "sap", "dynamics", "oracle"],
    "marketing": ["hubspot", "mailchimp", "google-analytics", "ga4", "facebook-pixel", "mixpanel", "segment"],
    "ecommerce": ["shopify", "woocommerce", "magento", "bigcommerce", "stripe", "paypal", "braintree"],
    "cloud": ["aws", "amazon-web-services", "google-cloud", "gcp", "azure", "cloudflare", "vercel", "netlify"],
}

PLATFORM_TECH_CORRELATION: Dict[str, List[str]] = {
    "github": ["development"],
    "gitlab": ["development"],
    "bitbucket": ["development"],
    "linkedin": ["enterprise", "marketing"],
    "google": ["marketing", "cloud"],
    "microsoft": ["enterprise", "cloud"],
    "twitter": ["marketing", "development"],
    "x": ["marketing", "development"],
}

NORMALIZATION_ALIASES: Dict[str, str] = {
    # common variants
    "nodejs": "node.js",
    "nextjs": "next.js",
    "ga4": "google-analytics",
    "office 365": "office-365",
    "microsoft 365": "microsoft-365",
    "amazon web services": "amazon-web-services",
    "gcp": "google-cloud",
}


def normalize_tech_name(name: str) -> str:
    n = name.strip().lower()
    n = re.sub(r"[ _]+", "-", n)
    n = re.sub(r"[^a-z0-9\-\.]+", "", n)
    return NORMALIZATION_ALIASES.get(n, n)


def domain_to_company(domain: str) -> str:
    # crude derivation: take first label and title-case
    root = domain.split(".")[0]
    return re.sub(r"[^a-zA-Z0-9]", " ", root).strip().title() or domain


class SmartEmailDrafter:
    def __init__(self):
        self.tech_categories = TECH_CATEGORIES
        self.platform_correlations = PLATFORM_TECH_CORRELATION

    def categorize_technologies(self, technologies: Iterable[str]) -> Dict[str, List[str]]:
        normalized = [normalize_tech_name(t) for t in technologies]
        by_category: Dict[str, Set[str]] = {k: set() for k in self.tech_categories.keys()}
        for tech in normalized:
            for cat, aliases in self.tech_categories.items():
                if any(alias in tech for alias in aliases):
                    by_category[cat].add(tech)
        # remove empty
        return {cat: sorted(list(vals)) for cat, vals in by_category.items() if vals}

    def match_platform_contexts(self, platforms: Iterable[str], tech_categories: Dict[str, List[str]]) -> List[str]:
        platform_set = {p.strip().lower() for p in platforms}
        matched: Set[str] = set()
        for platform in platform_set:
            if platform not in self.platform_correlations:
                continue
            for cat in self.platform_correlations[platform]:
                if cat in tech_categories and tech_categories[cat]:
                    if cat == "development":
                        matched.add("developer")
                    elif cat in ("enterprise", "cloud") and platform in ("linkedin", "microsoft"):
                        matched.add("business")
                    elif cat == "marketing" and platform in ("linkedin", "google", "twitter", "x"):
                        matched.add("marketing")
        # Ensure uniqueness and stable order
        order = ["developer", "business", "marketing"]
        return [m for m in order if m in matched]

    def _select_specifics(self, tech_categories: Dict[str, List[str]]) -> Dict[str, List[str]]:
        return {k: tech_categories.get(k, [])[:3] for k in self.tech_categories.keys()}

    def generate_templates(self, domain: str, email: str, technologies: Iterable[str], platforms: Iterable[str]) -> Tuple[List[Dict], List[str]]:
        company = domain_to_company(domain)
        cats = self.categorize_technologies(technologies)
        contexts = self.match_platform_contexts(platforms, cats)
        specifics = self._select_specifics(cats)

        templates: List[Dict] = []

        # Developer template
        if "developer" in contexts:
            dev_list = specifics.get("development") or []
            specific_tech = ", ".join(dev_list) if dev_list else "modern frameworks"
            subject = f"Quick question about your {dev_list[0] if dev_list else 'frontend'} at {company}"
            body = (
                f"Hi there,\n\n"
                f"I noticed {company} is actively using {specific_tech} in your stack."
                f" Given your presence on GitHub and focus on developer tooling, I wanted to share a few ideas to improve DX and velocity — from CI speedups to observability built for {specific_tech}.\n\n"
                f"Would a brief technical chat make sense?"
            )
            templates.append({"context": "developer", "subject": subject, "body": body})

        # Business/Enterprise template
        if "business" in contexts:
            ent_list = specifics.get("enterprise") or []
            ent_tech = ", ".join(ent_list) if ent_list else "your enterprise tooling"
            subject = f"Helping {company} optimize your {ent_list[0] if ent_list else 'operations'} workflows"
            body = (
                f"Hi there,\n\n"
                f"I see {company} is leveraging {ent_tech}. Teams with a similar footprint have reduced costs and improved time-to-value by standardizing on best practices across integrations and governance.\n\n"
                f"If you're exploring optimization this quarter, I can share a brief plan aligned to your tooling."
            )
            templates.append({"context": "business", "subject": subject, "body": body})

        # Marketing template
        if "marketing" in contexts:
            mkt_list = specifics.get("marketing") or []
            mkt_tech = ", ".join(mkt_list) if mkt_list else "your marketing stack"
            subject = f"Ideas to improve funnel visibility with {mkt_list[0] if mkt_list else 'your stack'}"
            body = (
                f"Hi there,\n\n"
                f"Noticed {company} runs {mkt_tech}. I've seen quick wins by tightening tracking, attribution, and experimentation workflows — especially when teams use Google/LinkedIn ecosystems.\n\n"
                f"Open to a quick walkthrough tailored to your current setup?"
            )
            templates.append({"context": "marketing", "subject": subject, "body": body})

        # Fallback comprehensive template if none matched
        if not templates:
            all_list = ", ".join(sorted({normalize_tech_name(t) for t in technologies})) or "your current stack"
            subject = f"A few ideas tailored to {company}'s stack"
            body = (
                f"Hi there,\n\n"
                f"I reviewed {domain} and saw you're using {all_list}. Based on this, I put together a few ways to improve performance, reduce costs, and speed up delivery.\n\n"
                f"Happy to share the concise notes if helpful."
            )
            templates.append({"context": "general", "subject": subject, "body": body})

        return templates, contexts