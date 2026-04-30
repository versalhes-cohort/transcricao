"""yt-dlp wrapper — metadata-only fetch (Story 1.2 scope).

NFR7 enforcement: yt-dlp is invoked EXCLUSIVELY via the Python API
(`yt_dlp.YoutubeDL`). No `subprocess`, no shell calls, no string
interpolation into command-line tools. Story 1.3 will add `download_audio`.
"""

from dataclasses import dataclass
from urllib.parse import urlparse

import yt_dlp
from yt_dlp.utils import DownloadError as YtdlpDownloadError, ExtractorError

from app.errors import UnsupportedSourceError, VideoTooLongError

MAX_DURATION_SECONDS = 60 * 60  # 60-minute hard cap (PRD FR4)


@dataclass(frozen=True)
class VideoMetadata:
    duration_seconds: int
    source_domain: str


def fetch_metadata(url: str) -> VideoMetadata:
    """Fetch video metadata without downloading audio.

    Raises:
        UnsupportedSourceError: yt-dlp cannot resolve the URL or duration is missing.
        VideoTooLongError: video duration > 60 minutes (FR4 hard cap).
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except (YtdlpDownloadError, ExtractorError):
        raise UnsupportedSourceError()
    except Exception:
        raise UnsupportedSourceError()

    if info is None:
        raise UnsupportedSourceError()

    duration = info.get("duration")
    if duration is None or not isinstance(duration, (int, float)):
        raise UnsupportedSourceError()

    duration_seconds = int(duration)
    if duration_seconds > MAX_DURATION_SECONDS:
        raise VideoTooLongError()

    source_domain = urlparse(url).netloc or "unknown"
    return VideoMetadata(
        duration_seconds=duration_seconds,
        source_domain=source_domain,
    )
