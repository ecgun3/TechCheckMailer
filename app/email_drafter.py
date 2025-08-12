from typing import Iterable


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