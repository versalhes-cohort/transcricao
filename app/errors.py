"""PT-BR error catalog and exception hierarchy.

Story 1.2 scope: base + the 3 errors used in URL validation and metadata fetch.
Story 1.3, 1.4, 1.6 will extend this module with DownloadError, TranscriptionError,
UnexpectedError as those stages are implemented.

Source: docs/architecture.md §6.1 — exception hierarchy.
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
