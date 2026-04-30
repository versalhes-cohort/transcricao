"""PT-BR error message contract tests — must match PRD verbatim.

Story 1.2 covered ACs 2/4/5 (InvalidURL, UnsupportedSource, VideoTooLong).
Story 1.3 added DownloadError (AC5 of Story 1.3).
"""

from app.errors import (
    DownloadError,
    InvalidURLError,
    TranscricaoError,
    UnsupportedSourceError,
    VideoTooLongError,
)


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


def test_all_categories_are_unique():
    categories = {
        InvalidURLError.category,
        UnsupportedSourceError.category,
        VideoTooLongError.category,
        DownloadError.category,
    }
    assert len(categories) == 4


def test_all_errors_inherit_from_base():
    for cls in (InvalidURLError, UnsupportedSourceError, VideoTooLongError, DownloadError):
        assert issubclass(cls, TranscricaoError)


def test_all_errors_have_non_empty_messages():
    for cls in (InvalidURLError, UnsupportedSourceError, VideoTooLongError, DownloadError):
        assert cls.user_message_pt
        assert cls.category
