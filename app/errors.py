"""PT-BR error catalog and exception hierarchy — FINAL (after Story 1.6).

The 7 categories enumerated in Story 1.6 AC1 (PRD verbatim):
    INVALID_URL, UNSUPPORTED_SOURCE, VIDEO_TOO_LONG, DOWNLOAD_FAILED,
    TRANSCRIPTION_FAILED, TIMEOUT, UNEXPECTED.

Story-of-origin per class:
    Story 1.2 → InvalidURLError, UnsupportedSourceError, VideoTooLongError
    Story 1.3 → DownloadError
    Story 1.4 → TranscriptionError
    Story 1.6 → TimeoutError (reserved for Phase 2), UnexpectedError

Source: docs/architecture.md §6.1 — exception hierarchy (final state).
"""


class TranscricaoError(Exception):
    """Base class for all user-facing application errors. Never instantiated directly."""

    category: str = ""
    user_message_pt: str = ""


class InvalidURLError(TranscricaoError):
    category = "INVALID_URL"
    user_message_pt = "URL inválida. Cole um link começando com http:// ou https://."


class UnsupportedSourceError(TranscricaoError):
    category = "UNSUPPORTED_SOURCE"
    user_message_pt = "Não foi possível acessar este vídeo. Verifique o link ou tente outra fonte."


class VideoTooLongError(TranscricaoError):
    category = "VIDEO_TOO_LONG"
    user_message_pt = "Vídeo excede o limite de 60 minutos. Tente um vídeo mais curto."


class DownloadError(TranscricaoError):
    category = "DOWNLOAD_FAILED"
    user_message_pt = "Falha ao baixar o áudio. Tente novamente ou use outra fonte."


class TranscriptionError(TranscricaoError):
    category = "TRANSCRIPTION_FAILED"
    user_message_pt = "Falha na transcrição. Tente novamente em alguns minutos."


class TimeoutError(TranscricaoError):
    """Reserved category for AC1 catalog completeness.

    MVP architecture (§6.1) does NOT actively raise this — wall-clock
    timeouts surface as DOWNLOAD_FAILED or TRANSCRIPTION_FAILED depending
    on which stage stalls. Reserved here so the catalog is complete and a
    future Phase 2 timeout layer can raise it without schema migration.

    Note: shadows Python's built-in `TimeoutError` inside this module.
    Intentional — matches the AC1 category vocabulary. Harmless because
    the rest of the app imports specific symbols by name.
    """

    category = "TIMEOUT"
    user_message_pt = "A operação demorou mais que o esperado. Tente novamente."


class UnexpectedError(TranscricaoError):
    category = "UNEXPECTED"
    user_message_pt = "Algo deu errado. Tente novamente em alguns minutos."
