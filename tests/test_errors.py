"""PT-BR error message contract tests — must match PRD verbatim.

Story 1.2: InvalidURL, UnsupportedSource, VideoTooLong (3 classes).
Story 1.3: + DownloadError (4 classes total).
Story 1.4: + TranscriptionError (5 classes total).
Story 1.6 will add UnexpectedError (6 classes — final).
"""

from app.errors import (
    DownloadError,
    InvalidURLError,
    TranscricaoError,
    TranscriptionError,
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


def test_transcription_error_pt_message():
    assert (
        TranscriptionError().user_message_pt
        == "Falha na transcrição. Tente novamente em alguns minutos."
    )


def test_all_categories_are_unique():
    categories = {
        InvalidURLError.category,
        UnsupportedSourceError.category,
        VideoTooLongError.category,
        DownloadError.category,
        TranscriptionError.category,
    }
    assert len(categories) == 5


def test_all_errors_inherit_from_base():
    for cls in (
        InvalidURLError,
        UnsupportedSourceError,
        VideoTooLongError,
        DownloadError,
        TranscriptionError,
    ):
        assert issubclass(cls, TranscricaoError)


def test_all_errors_have_non_empty_messages():
    for cls in (
        InvalidURLError,
        UnsupportedSourceError,
        VideoTooLongError,
        DownloadError,
        TranscriptionError,
    ):
        assert cls.user_message_pt
        assert cls.category
