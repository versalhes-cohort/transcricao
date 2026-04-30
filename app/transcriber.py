"""Whisper API orchestration — single-call dispatch + chunked path + retries.

NFR7 enforcement: OpenAI client is invoked via the Python SDK only; no
subprocess, no shell. pydub handles ffmpeg internally for chunk export.

NFR10 enforcement: caller (main.py) MUST never log transcript content.
This module emits no transcript-bearing log lines either.
"""

import logging
import os
import time
from pathlib import Path

import openai
from pydub import AudioSegment

from app.chunking import plan_chunks, stitch_transcripts
from app.errors import TranscriptionError

logger = logging.getLogger(__name__)

WHISPER_SINGLE_CALL_LIMIT_BYTES = 25 * 1024 * 1024  # OpenAI's 25 MB hard limit
CHUNK_TARGET_BYTES = 24 * 1024 * 1024               # 1 MB safety margin
WHISPER_LANGUAGE = "pt"
WHISPER_MODEL = "whisper-1"
WHISPER_RESPONSE_FORMAT = "text"
RETRY_MAX_ATTEMPTS = 3                              # initial + 2 retries (AC6)
RETRY_BASE_DELAY_S = 1.0                            # exponential: 1, 2, 4...
EMPTY_TRANSCRIPT_THRESHOLD = 10                     # chars (architecture §12 R8)
CHUNK_OVERLAP_MS = 2000                             # 2 s overlap (AC3)


def assert_api_key_configured() -> None:
    """Boot-time check (AC9). Raises RuntimeError if OPENAI_API_KEY is missing.

    Called from main.py at module load — BEFORE any user request can hit
    the pipeline. Failure here causes Streamlit startup to fail loudly,
    which is the desired behavior (fail fast, fail visible).
    """
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is required. "
            "Set it in Railway dashboard → Variables, or in a local .env file."
        )


def transcribe(audio_path: Path, audio_duration_s: int) -> str:
    """Transcribe an audio file in PT-BR via OpenAI Whisper.

    Dispatches to single-call or chunked path based on file size.

    Args:
        audio_path: Path to the mp3/m4a audio file (from Story 1.3).
        audio_duration_s: Total duration in seconds (from fetch_metadata).

    Returns:
        Final transcript as plain string, in chronological order.

    Raises:
        TranscriptionError: Whisper API failed after all retries OR the
            final transcript is suspiciously empty (<10 chars).
    """
    file_size_bytes = audio_path.stat().st_size

    if file_size_bytes <= WHISPER_SINGLE_CALL_LIMIT_BYTES:
        transcript = _transcribe_single(audio_path)
    else:
        transcript = _transcribe_chunked(audio_path, audio_duration_s)

    # Architecture §12 R8: if final transcript is suspiciously empty,
    # surface as TranscriptionError rather than render a blank result.
    if len(transcript.strip()) < EMPTY_TRANSCRIPT_THRESHOLD:
        raise TranscriptionError()

    return transcript


def _transcribe_single(audio_path: Path) -> str:
    """Single-call path (file ≤25 MB). Uses 2-retry exponential backoff."""

    def _call() -> str:
        with audio_path.open("rb") as fh:
            return openai.audio.transcriptions.create(
                model=WHISPER_MODEL,
                file=fh,
                language=WHISPER_LANGUAGE,
                response_format=WHISPER_RESPONSE_FORMAT,
            )

    return _with_retries(_call)


def _transcribe_chunked(audio_path: Path, audio_duration_s: int) -> str:
    """Chunked path (file >25 MB). Architecture §5.2 algorithm."""
    file_size_bytes = audio_path.stat().st_size
    audio_duration_ms = audio_duration_s * 1000
    chunk_specs = plan_chunks(
        file_size_bytes=file_size_bytes,
        audio_duration_ms=audio_duration_ms,
        max_chunk_bytes=CHUNK_TARGET_BYTES,
        overlap_ms=CHUNK_OVERLAP_MS,
    )

    # Caller (main.py) owns audio_dir; cleanup happens in main.py's finally.
    chunk_dir = audio_path.parent
    audio = AudioSegment.from_file(audio_path)
    transcripts: list[str] = []
    for idx, spec in enumerate(chunk_specs):
        chunk_path = chunk_dir / f"chunk_{idx:03d}.mp3"
        audio[spec.start_ms : spec.end_ms].export(
            chunk_path, format="mp3", bitrate="64k"
        )

        def _call(path: Path = chunk_path) -> str:
            with path.open("rb") as fh:
                return openai.audio.transcriptions.create(
                    model=WHISPER_MODEL,
                    file=fh,
                    language=WHISPER_LANGUAGE,
                    response_format=WHISPER_RESPONSE_FORMAT,
                )

        transcripts.append(_with_retries(_call))

    return stitch_transcripts(transcripts)


def _with_retries(call):
    """Execute `call` with up to 2 retries on retryable errors (AC6).

    AuthenticationError fails immediately (not retryable — bad key won't
    fix itself). All other exceptions retry with exponential backoff.
    On exhaustion, raises TranscriptionError with the original cause chained.
    """
    last_exc: Exception | None = None
    for attempt in range(RETRY_MAX_ATTEMPTS):
        try:
            return call()
        except openai.AuthenticationError as e:
            # Auth errors are NOT retryable — fail fast.
            raise TranscriptionError() from e
        except Exception as e:
            last_exc = e
            if attempt < RETRY_MAX_ATTEMPTS - 1:
                time.sleep(RETRY_BASE_DELAY_S * (2 ** attempt))
                continue
            raise TranscriptionError() from last_exc

    # Unreachable: the loop either returns or raises. Defensive fallback for
    # type-checkers and any future control-flow change.
    raise TranscriptionError()
