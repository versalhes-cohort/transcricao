"""Pure boundary math + stitching for Whisper API chunked transcription.

This module is INTENTIONALLY pure — no `pydub`, no `openai`, no `streamlit`
imports. The audio I/O lives in `transcriber.py`; the orchestration lives in
`main.py`. Keeping the math here means it's fully unit-testable in isolation.

Architecture: docs/architecture.md §5.2 (chunk planning), §5.3 (stitching),
§4.2 + §10 ADR-006 (rationale for the module split).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkSpec:
    """Time range for one audio chunk, in milliseconds."""

    start_ms: int
    end_ms: int


def plan_chunks(
    file_size_bytes: int,
    audio_duration_ms: int,
    max_chunk_bytes: int = 24 * 1024 * 1024,
    overlap_ms: int = 2000,
) -> list[ChunkSpec]:
    """Compute chunk boundaries (in ms) for chunked Whisper transcription.

    Algorithm (architecture §5.2):
    1. Approximate ms-per-byte assuming uniform CBR encoding.
    2. Compute target chunk duration in ms.
    3. Effective stride = chunk_duration - overlap.
    4. Slide forward, clamping the final chunk to audio_duration_ms.

    Args:
        file_size_bytes: Total bytes on disk (caller already verified > 25 MB
            before invoking this function).
        audio_duration_ms: Total duration in milliseconds (from yt-dlp metadata).
        max_chunk_bytes: Target bytes per chunk (default 24 MB = 1 MB safety
            margin under Whisper's 25 MB single-request limit).
        overlap_ms: Forward overlap at chunk boundaries to preserve word
            integrity at seams (default 2 s per AC3).

    Returns:
        Ordered list of ChunkSpec entries. Adjacent chunks overlap by
        exactly `overlap_ms` (except possibly the final pair if clamping
        shortens the last chunk).
    """
    ms_per_byte = audio_duration_ms / file_size_bytes
    chunk_duration_ms = int(max_chunk_bytes * ms_per_byte)
    stride_ms = chunk_duration_ms - overlap_ms

    # INFO-1 defensive guard: if stride would be ≤0 (mathematically impossible
    # with default params + realistic audio bitrates, but defensive against
    # future param changes), fall back to non-overlapping chunks.
    if stride_ms <= 0:
        stride_ms = chunk_duration_ms

    chunks: list[ChunkSpec] = []
    cursor_ms = 0
    while cursor_ms < audio_duration_ms:
        end_ms = min(cursor_ms + chunk_duration_ms, audio_duration_ms)
        chunks.append(ChunkSpec(start_ms=cursor_ms, end_ms=end_ms))
        if end_ms >= audio_duration_ms:
            break
        cursor_ms += stride_ms
    return chunks


def stitch_transcripts(chunks: list[str], max_overlap_words: int = 25) -> str:
    """Concatenate chunk transcripts with simple boundary de-duplication.

    Strategy (architecture §5.3):
    - For each adjacent pair, find the longest suffix-of-tail / prefix-of-head
      n-gram match (case-insensitive, normalized punctuation).
    - If overlap >= 3 words → elide; else concat with a single space (AC5
      acceptable duplication when no clean boundary).
    """
    if not chunks:
        return ""
    if len(chunks) == 1:
        return chunks[0]
    result = chunks[0]
    for next_chunk in chunks[1:]:
        result = _merge_at_boundary(result, next_chunk, max_overlap_words)
    return result


def _merge_at_boundary(left: str, right: str, max_overlap_words: int) -> str:
    """Find the longest matching word-sequence at the seam and elide.

    Returns the merged string. If no overlap of >=3 words is found,
    returns ``left + ' ' + right`` (per AC5: minor duplication acceptable).
    """
    tail_words = left.split()[-max_overlap_words:]
    head_words = right.split()[:max_overlap_words]

    def _norm(word: str) -> str:
        return word.strip(".,;:!?\"'").lower()

    tail_norm = [_norm(w) for w in tail_words]
    head_norm = [_norm(w) for w in head_words]

    # Find longest k where tail_norm[-k:] == head_norm[:k].
    best_k = 0
    for k in range(min(len(tail_norm), len(head_norm)), 0, -1):
        if tail_norm[-k:] == head_norm[:k]:
            best_k = k
            break

    if best_k >= 3:
        # Elide overlap: keep `left`, append `right` from after the overlap.
        remainder = " ".join(right.split()[best_k:])
        return f"{left} {remainder}".strip() if remainder else left

    # Fallback: simple concat with a single space (AC5 allows minor duplication).
    if not left:
        return right
    if not right:
        return left
    return f"{left} {right}"
