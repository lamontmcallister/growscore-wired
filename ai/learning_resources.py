from urllib.parse import quote


def coursera_search_link(skill: str) -> str:
    """
    Builds a real, working Coursera search URL for a given skill.
    We deliberately link to Coursera's own live search results rather than
    naming specific courses -- Coursera's public course-search API requires
    a registered/approved app (see dev.coursera.com), which isn't something
    we can wire up tonight. A verified search link is honest; a guessed
    course title or fabricated URL is not.
    """
    return f"https://www.coursera.org/search?query={quote(skill)}"
