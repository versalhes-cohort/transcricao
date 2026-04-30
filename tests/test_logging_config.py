"""Unit tests for app.logging_config (Story 1.3 AC8 + NFR10 enforcement)."""

import logging
import re

from app.logging_config import URL_PATTERN, SafeLogFilter, hash_url, setup_logging


class TestUrlPattern:
    def test_matches_https_url(self):
        assert URL_PATTERN.search("Accessing https://example.com/path now") is not None

    def test_matches_http_url(self):
        assert URL_PATTERN.search("http://example.com") is not None

    def test_does_not_match_relative_path(self):
        assert URL_PATTERN.search("/etc/passwd") is None

    def test_does_not_match_ftp(self):
        assert URL_PATTERN.search("ftp://example.com") is None


class TestSafeLogFilter:
    def setup_method(self, method):
        self.filter = SafeLogFilter()

    @staticmethod
    def _make_record(msg, args=None):
        return logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=msg,
            args=args,
            exc_info=None,
        )

    def test_redacts_url_in_msg(self):
        record = self._make_record("downloading https://youtube.com/abc")
        self.filter.filter(record)
        assert record.msg == "downloading [URL]"

    def test_redacts_multiple_urls(self):
        record = self._make_record("from https://a.com to http://b.com")
        self.filter.filter(record)
        assert record.msg == "from [URL] to [URL]"

    def test_passes_through_message_without_url(self):
        record = self._make_record("plain log line, size=1234")
        self.filter.filter(record)
        assert record.msg == "plain log line, size=1234"

    def test_redacts_url_in_string_args(self):
        record = self._make_record("got %s", args=("https://example.com/path",))
        self.filter.filter(record)
        assert record.args == ("[URL]",)

    def test_filter_returns_true(self):
        record = self._make_record("anything")
        assert self.filter.filter(record) is True

    def test_passes_through_non_string_args(self):
        record = self._make_record("count=%d size=%d", args=(42, 1024))
        self.filter.filter(record)
        assert record.args == (42, 1024)


class TestHashUrl:
    def test_returns_8_chars(self):
        assert len(hash_url("https://example.com")) == 8

    def test_is_deterministic(self):
        assert hash_url("https://example.com") == hash_url("https://example.com")

    def test_different_urls_different_hashes(self):
        assert hash_url("https://a.com") != hash_url("https://b.com")

    def test_handles_unicode(self):
        h = hash_url("https://example.com/áéíóú")
        assert len(h) == 8

    def test_uses_lowercase_hex(self):
        h = hash_url("https://example.com")
        assert re.fullmatch(r"[0-9a-f]{8}", h)


class TestSetupLogging:
    def test_is_idempotent(self):
        # Calling twice should not duplicate handlers.
        root = logging.getLogger()
        setup_logging()
        first_count = len(root.handlers)
        setup_logging()
        second_count = len(root.handlers)
        assert second_count == first_count, "setup_logging is not idempotent"

    def test_filter_is_attached(self):
        """After setup_logging(), at least ONE root handler has SafeLogFilter.

        Note: in test environments (pytest), there may be other handlers
        present (e.g., pytest's LogCaptureHandler). We only need to verify
        that OUR handler (with SafeLogFilter attached) exists somewhere.
        """
        setup_logging()
        root = logging.getLogger()
        has_safe_filter = any(
            any(isinstance(f, SafeLogFilter) for f in handler.filters)
            for handler in root.handlers
        )
        assert has_safe_filter, "No handler with SafeLogFilter attached after setup_logging()"
