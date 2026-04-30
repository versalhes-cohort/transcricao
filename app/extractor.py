"""yt-dlp wrapper — metadata fetch + audio download.

NFR7 enforcement: yt-dlp is invoked EXCLUSIVELY via the Python API
(`yt_dlp.YoutubeDL`). No `subprocess`, no shell calls, no string
interpolation into command-line tools.

Story 1.2 added fetch_metadata. Story 1.3 added download_audio.
"""

import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp
from yt_dlp.utils import DownloadError as YtdlpDownloadError, ExtractorError

from app.errors import DownloadError, UnsupportedSourceError, VideoTooLongError

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


def download_audio(url: str, target_dir: Path | None = None) -> Path:
    """Download audio-only stream of a video to an ephemeral location.

    Args:
        url: Video URL (already validated by url_validation.validate_url).
        target_dir: Optional pre-created tempdir. If None, mkdtemp is used.
            Caller is responsible for cleaning up the directory containing
            the returned file.

    Returns:
        Absolute Path to the downloaded audio file (mp3 preferred,
        m4a fallback).

    Raises:
        DownloadError: yt-dlp failed (DRM, geo-block, partial download
            cleaned up before re-raising).
    """
    if target_dir is None:
        target_dir = Path(tempfile.mkdtemp(prefix="transcricao_"))

    outtmpl = str(target_dir / "audio.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "64",
            }
        ],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except (YtdlpDownloadError, ExtractorError):
        _cleanup_partials(target_dir)
        raise DownloadError()
    except Exception:
        _cleanup_partials(target_dir)
        raise DownloadError()

    # AC2: prefer mp3 (FFmpegExtractAudio target), fallback to m4a only.
    # Other extensions are NOT accepted — narrowed per @po Should-Fix #2.
    candidates = list(target_dir.glob("audio.mp3"))
    if not candidates:
        candidates = list(target_dir.glob("audio.m4a"))
    if not candidates:
        _cleanup_partials(target_dir)
        raise DownloadError()

    return candidates[0]


def _cleanup_partials(target_dir: Path) -> None:
    """Best-effort cleanup of partial download artifacts. Never raises."""
    try:
        for entry in target_dir.iterdir():
            try:
                entry.unlink()
            except OSError:
                pass
    except OSError:
        pass
