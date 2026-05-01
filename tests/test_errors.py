"""PT-BR error message contract tests — must match PRD verbatim.

Final state after Story 1.6: 7 categories, 7 classes.

Story 1.2: InvalidURL, UnsupportedSource, VideoTooLong (3 classes).
Story 1.3: + DownloadError (4 classes total).
Story 1.4: + TranscriptionError (5 classes total).
Story 1.6: + TimeoutError (reserved), + UnexpectedError (7 classes — final).
"""

from app.errors import (
    DownloadError,
    InvalidURLError,
    TranscricaoError,
    TranscriptionError,
    UnexpectedError,
    UnsupportedSourceError,
    VideoTooLongError,
)
# Disambiguate from Python's built-in TimeoutError
from app.errors import TimeoutError as AppTimeoutError


def test_invalid_url_pt_message():
    assert (
        InvalidURLError().user_message_pt
        == "URL inválida. Cole um link começando com http:// ou https://."
    )


def test_unsupported_source_pt_message():
    assert (
        UnsupportedSourceError().user_message_pt
        == "Não foi possível acessar este vídeo. Verifique o link ou tente outra fonte."
    )


def test_video_too_long_pt_message():
    assert (
        VideoTooLongError().user_message_pt
        == "Vídeo excede o limite de 60 minutos. Tente um vídeo mais curto."
    )


def test_download_error_pt_message():
    assert (
        DownloadError().user_message_pt
        == "Falha ao baixar o áudio. Tente novamente ou use outra fonte."
    )


def test_transcription_error_pt_message():
    assert (
        TranscriptionError().user_message_pt
        == "Falha na transcrição. Tente novamente em alguns minutos."
    )


def test_unexpected_error_pt_message():
    # AC5 verbatim
    assert (
        UnexpectedError().user_message_pt
        == "Algo deu errado. Tente novamente em alguns minutos."
    )


def test_timeout_error_message_non_empty():
    # PRD does NOT prescribe a verbatim TIMEOUT message — story chose a sensible
    # default. Just assert it's non-empty and contains "demorou" (key concept).
    msg = AppTimeoutError().user_message_pt
    assert msg
    assert "demorou" in msg.lower()


def test_all_categories_are_unique():
    categories = {
        InvalidURLError.category,
        UnsupportedSourceError.category,
        VideoTooLongError.category,
        DownloadError.category,
        TranscriptionError.category,
        AppTimeoutError.category,
        UnexpectedError.category,
    }
    assert len(categories) == 7


def test_all_categories_match_ac1_vocabulary():
    # AC1 minimum-category list verbatim from PRD.
    expected = {
        "INVALID_URL",
        "UNSUPPORTED_SOURCE",
        "VIDEO_TOO_LONG",
        "DOWNLOAD_FAILED",
        "TRANSCRIPTION_FAILED",
        "TIMEOUT",
        "UNEXPECTED",
    }
    actual = {
        InvalidURLError.category,
        UnsupportedSourceError.category,
        VideoTooLongError.category,
        DownloadError.category,
        TranscriptionError.category,
        AppTimeoutError.category,
        UnexpectedError.category,
    }
    assert actual == expected


def test_all_errors_inherit_from_base():
    for cls in (
        InvalidURLError,
        UnsupportedSourceError,
        VideoTooLongError,
        DownloadError,
        TranscriptionError,
        AppTimeoutError,
        UnexpectedError,
    ):
        assert issubclass(cls, TranscricaoError)


def test_all_errors_have_non_empty_messages():
    for cls in (
        InvalidURLError,
        UnsupportedSourceError,
        VideoTooLongError,
        DownloadError,
        TranscriptionError,
        AppTimeoutError,
        UnexpectedError,
    ):
        assert cls.user_message_pt
        assert cls.category
