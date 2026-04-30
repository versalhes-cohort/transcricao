"""Unit tests for app.url_validation.validate_url (Story 1.2 AC8)."""

import pytest

from app.errors import InvalidURLError
from app.url_validation import validate_url


class TestValidateUrlHappyPaths:
    def test_valid_https_youtube(self):
        assert validate_url("https://youtube.com/watch?v=abc") == "https://youtube.com/watch?v=abc"

    def test_valid_http_example(self):
        assert validate_url("http://example.com/video") == "http://example.com/video"

    def test_valid_https_with_subdomain(self):
        assert validate_url("https://www.instagram.com/reel/xyz") == "https://www.instagram.com/reel/xyz"

    def test_valid_https_with_query_and_fragment(self):
        url = "https://example.com/path?q=1&v=2#frag"
        assert validate_url(url) == url

    def test_trims_surrounding_whitespace(self):
        assert validate_url("  https://example.com  ") == "https://example.com"

    def test_trims_tabs_and_newlines(self):
        assert validate_url("\thttps://example.com\n") == "https://example.com"


class TestValidateUrlInvalidScheme:
    def test_rejects_ftp(self):
        with pytest.raises(InvalidURLError):
            validate_url("ftp://example.com")

    def test_rejects_javascript_uri(self):
        with pytest.raises(InvalidURLError):
            validate_url("javascript:alert(1)")

    def test_rejects_file_uri(self):
        with pytest.raises(InvalidURLError):
            validate_url("file:///etc/passwd")

    def test_rejects_data_uri(self):
        with pytest.raises(InvalidURLError):
            validate_url("data:text/html,<script>alert(1)</script>")

    def test_rejects_ssh_uri(self):
        with pytest.raises(InvalidURLError):
            validate_url("ssh://user@host:22")


class TestValidateUrlEmptyOrWhitespace:
    def test_rejects_empty_string(self):
        with pytest.raises(InvalidURLError):
            validate_url("")

    def test_rejects_whitespace_only(self):
        with pytest.raises(InvalidURLError):
            validate_url("   ")

    def test_rejects_tab_only(self):
        with pytest.raises(InvalidURLError):
            validate_url("\t\t")

    def test_rejects_none_input(self):
        with pytest.raises(InvalidURLError):
            validate_url(None)  # type: ignore[arg-type]

    def test_rejects_non_string_input(self):
        with pytest.raises(InvalidURLError):
            validate_url(12345)  # type: ignore[arg-type]


class TestValidateUrlMalformed:
    def test_rejects_bare_domain_without_scheme(self):
        with pytest.raises(InvalidURLError):
            validate_url("example.com")

    def test_rejects_scheme_only_https(self):
        with pytest.raises(InvalidURLError):
            validate_url("https://")

    def test_rejects_scheme_only_http(self):
        with pytest.raises(InvalidURLError):
            validate_url("http://")
