"""Structural enforcement of NFR10 (no transcripts/URLs in logs).

Three responsibilities:
1. SafeLogFilter — defense-in-depth regex redaction of `https?://...` patterns
   in log records, in case a developer accidentally logs a URL string.
2. hash_url — 8-char SHA-256 prefix for cross-event correlation without
   exposing the URL itself.
3. setup_logging — idempotent wiring of stdout logging with the SafeLogFilter
   attached. Idempotency matters because Streamlit reruns main.py on every
   user interaction.

Source: docs/architecture.md §6.4 — safe logging implementation.
"""

import hashlib
import logging
import re

URL_PATTERN = re.compile(r'https?://[^\s<>"]+')


class SafeLogFilter(logging.Filter):
    """Redact full URLs in log records to prevent leakage (NFR10 defense-in-depth)."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = URL_PATTERN.sub("[URL]", record.msg)
        if record.args:
            record.args = tuple(
                URL_PATTERN.sub("[URL]", str(a)) if isinstance(a, str) else a
                for a in record.args
            )
        return True


def hash_url(url: str) -> str:
    """8-char SHA-256 hash for cross-event correlation without exposing the URL."""
    return hashlib.sha256(url.encode()).hexdigest()[:8]


def setup_logging() -> None:
    """Wire stdout logging with the SafeLogFilter. Idempotent — safe to call
    multiple times across Streamlit reruns.

    Idempotency check: detect our own handler by looking for an attached
    SafeLogFilter, not just any StreamHandler. This prevents double-attachment
    when pytest (or other frameworks) has already added a StreamHandler that
    is NOT ours.
    """
    root = logging.getLogger()
    for handler in root.handlers:
        if any(isinstance(f, SafeLogFilter) for f in handler.filters):
            return  # Already configured (our handler is present)

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s | %(message)s")
    )
    handler.addFilter(SafeLogFilter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)
