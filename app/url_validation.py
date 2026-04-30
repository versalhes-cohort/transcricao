"""Pure URL validation against an http/https schema-only allowlist (NFR7).

Kept Streamlit-free so it can be unit-tested without import-time side effects.
"""

from urllib.parse import urlparse

from app.errors import InvalidURLError


def validate_url(raw_url: object) -> str:
    """Validate a URL against the http/https schema-only allowlist.

    Returns the trimmed URL on success.
    Raises InvalidURLError with PT-BR message on failure.
    """
    if not isinstance(raw_url, str):
        raise InvalidURLError()

    url = raw_url.strip()
    if not url:
        raise InvalidURLError()

    try:
        parsed = urlparse(url)
    except Exception:
        raise InvalidURLError()

    if parsed.scheme not in ("http", "https"):
        raise InvalidURLError()

    if not parsed.netloc:
        raise InvalidURLError()

    return url
