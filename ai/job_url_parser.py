import json
import re
import requests
from bs4 import BeautifulSoup


def fetch_job_posting(url: str):
    """
    Fetches a job posting URL and extracts real title, company, and
    description -- no invented data at any point. Tries three levels,
    each more honest than the last about what it actually found:

    1. schema.org JobPosting structured data (JSON-LD) -- the standard
       most ATS platforms (Greenhouse, Lever, Workday, iCIMS) and job
       boards embed specifically for search engine indexing. Most
       reliable when present.
    2. Basic meta tags (og:title, og:description, <title>) -- weaker,
       but still real data pulled directly from the page.
    3. Neither found -- returns a clear error. The caller must not
       invent a title/company/description when this happens; the
       candidate pastes the JD manually instead, same as before this
       feature existed.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
    except requests.exceptions.RequestException as e:
        return None, f"Couldn't reach that URL: {e}"

    if response.status_code != 200:
        return None, f"That page returned an error (status {response.status_code}). It may be private, removed, or blocking automated requests."

    soup = BeautifulSoup(response.text, "html.parser")

    job_data = _extract_jobposting_jsonld(soup)
    if job_data:
        return {
            "title": job_data.get("title", ""),
            "company": job_data.get("company", ""),
            "description": job_data.get("description", ""),
            "url": url,
            "extraction_level": "structured",
        }, None

    title = _get_meta(soup, "og:title") or (soup.title.string.strip() if soup.title and soup.title.string else "")
    description = _get_meta(soup, "og:description")

    # Require BOTH a title and real description text before calling this a
    # success. A bare generic title (e.g. a site's wrapper page title like
    # "Opportunities" on JS-rendered job boards) with no description isn't
    # trustworthy enough to present as "we found your job" -- that's worse
    # than a clean failure, since it looks like it worked when it didn't.
    if title and description:
        company = _parse_company_from_title(title)
        return {
            "title": title,
            "company": company,
            "description": description,
            "url": url,
            "extraction_level": "partial",
        }, None

    return None, "Couldn't find job details on that page. Paste the job description directly instead."


def _extract_jobposting_jsonld(soup):
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        candidates = data if isinstance(data, list) else [data]
        for entry in candidates:
            if not isinstance(entry, dict):
                continue
            entry_type = entry.get("@type", "")
            if entry_type == "JobPosting" or (isinstance(entry_type, list) and "JobPosting" in entry_type):
                title = entry.get("title", "")
                company = ""
                org = entry.get("hiringOrganization")
                if isinstance(org, dict):
                    company = org.get("name", "")
                description_html = entry.get("description", "")
                description_text = BeautifulSoup(description_html, "html.parser").get_text(separator="\n").strip() if description_html else ""
                if title:
                    return {"title": title, "company": company, "description": description_text}
    return None


def _get_meta(soup, property_name):
    tag = soup.find("meta", property=property_name) or soup.find("meta", attrs={"name": property_name})
    return tag.get("content", "").strip() if tag else ""


def _parse_company_from_title(title: str) -> str:
    """
    Some sites (LinkedIn's og:title being the clearest example) follow a
    predictable, real pattern: "{Company} hiring {Title} in {Location} |
    LinkedIn". When that pattern is present, the company name is real,
    structured text on the page -- not a guess. Returns "" if no
    recognizable pattern is found, rather than inventing a company name.
    """
    match = re.match(r"^(.+?)\s+hiring\s+.+", title)
    if match:
        return match.group(1).strip()
    return ""
