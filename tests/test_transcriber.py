"""Unit tests for app.transcriber — boot-check + retry logic (Story 1.4 AC6/AC9).

Real OpenAI API is NEVER invoked in these tests. All client interactions are
mocked via pytest-mock. The chunking math itself is covered by test_chunking.py.
"""

import openai
import pytest

from app.errors import TranscriptionError
from app.transcriber import _with_retries, assert_api_key_configured


# ----------------------------------------------------------------------------
# AC9 — Boot-time API key check
# ----------------------------------------------------------------------------


class TestAssertApiKeyConfigured:
    def test_raises_when_unset(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            assert_api_key_configured()

    def test_raises_when_empty_string(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "")
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            assert_api_key_configured()

    def test_passes_when_set(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake-value-not-real")
        # No raise = pass
        result = assert_api_key_configured()
        assert result is None

    def test_message_mentions_railway_and_env(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(RuntimeError) as exc_info:
            assert_api_key_configured()
        message = str(exc_info.value)
        assert "Railway" in message or "env" in message.lower()


# ----------------------------------------------------------------------------
# AC6 — Retry behavior (mocks, no real API)
# ----------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _no_sleep(mocker):
    """Patch time.sleep so retry tests run instantly."""
    mocker.patch("app.transcriber.time.sleep")


class TestWithRetries:
    def test_success_on_first_attempt_no_retry(self, mocker):
        call = mocker.Mock(return_value="ok")
        assert _with_retries(call) == "ok"
        assert call.call_count == 1

    def test_retries_on_api_error_then_succeeds(self, mocker):
        # First call raises a generic Exception (covers the broad-except path);
        # second call succeeds.
        call = mocker.Mock(side_effect=[
            RuntimeError("transient failure"),
            "second-attempt-ok",
        ])
        assert _with_retries(call) == "second-attempt-ok"
        assert call.call_count == 2

    def test_raises_transcription_error_after_two_retries(self, mocker):
        call = mocker.Mock(side_effect=RuntimeError("persistent error"))
        with pytest.raises(TranscriptionError):
            _with_retries(call)
        assert call.call_count == 3  # initial + 2 retries

    def test_auth_error_fails_immediately_no_retry(self, mocker):
        # AuthenticationError needs a response object for OpenAI's constructor.
        # We mock the whole exception with a synthetic instance.
        auth_exc = openai.AuthenticationError(
            message="bad key",
            response=mocker.Mock(),
            body={},
        )
        call = mocker.Mock(side_effect=auth_exc)
        with pytest.raises(TranscriptionError) as exc_info:
            _with_retries(call)
        # Cause chain preserved (INFO-2 applied).
        assert exc_info.value.__cause__ is auth_exc
        assert call.call_count == 1  # NO retry for auth errors

    def test_persistent_failure_chains_cause(self, mocker):
        underlying = RuntimeError("api down")
        call = mocker.Mock(side_effect=underlying)
        with pytest.raises(TranscriptionError) as exc_info:
            _with_retries(call)
        # INFO-2 applied: TranscriptionError chains the underlying cause.
        assert exc_info.value.__cause__ is underlying
