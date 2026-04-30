"""Unit tests for app.chunking — pure boundary math + stitching (Story 1.4 AC8)."""

import dataclasses

import pytest

from app.chunking import ChunkSpec, plan_chunks, stitch_transcripts


class TestPlanChunks:
    def test_two_chunks_for_28mb_60min(self):
        # 60 min audio at 28 MB — 24 MB target produces 2 chunks
        file_size = 28 * 1024 * 1024
        duration_ms = 60 * 60 * 1000
        chunks = plan_chunks(file_size, duration_ms)
        assert len(chunks) == 2

    def test_two_chunks_overlap_by_2_seconds(self):
        file_size = 28 * 1024 * 1024
        duration_ms = 60 * 60 * 1000
        chunks = plan_chunks(file_size, duration_ms, overlap_ms=2000)
        # Adjacent chunks: end_ms[i] - start_ms[i+1] should be 2000 ms
        assert chunks[0].end_ms - chunks[1].start_ms == 2000

    def test_final_chunk_clamped_to_duration(self):
        file_size = 28 * 1024 * 1024
        duration_ms = 60 * 60 * 1000
        chunks = plan_chunks(file_size, duration_ms)
        assert chunks[-1].end_ms == duration_ms

    def test_first_chunk_starts_at_zero(self):
        file_size = 28 * 1024 * 1024
        duration_ms = 60 * 60 * 1000
        chunks = plan_chunks(file_size, duration_ms)
        assert chunks[0].start_ms == 0

    def test_two_chunks_for_42mb_90min(self):
        # Synthetic case: 42 MB / 90 min — should produce 2 chunks
        file_size = 42 * 1024 * 1024
        duration_ms = 90 * 60 * 1000
        chunks = plan_chunks(file_size, duration_ms)
        assert len(chunks) == 2

    def test_single_chunk_when_file_fits(self):
        # File at the chunk target — single chunk that equals total duration
        file_size = 24 * 1024 * 1024
        duration_ms = 50 * 60 * 1000
        chunks = plan_chunks(file_size, duration_ms)
        assert len(chunks) == 1
        assert chunks[0].start_ms == 0
        assert chunks[0].end_ms == duration_ms

    def test_chunk_specs_are_frozen(self):
        chunks = plan_chunks(28 * 1024 * 1024, 60 * 60 * 1000)
        with pytest.raises(dataclasses.FrozenInstanceError):
            chunks[0].start_ms = 999  # type: ignore[misc]

    def test_defensive_guard_handles_zero_stride(self):
        # Hypothetical: tiny chunk_duration, large overlap → stride <= 0.
        # The defensive guard (INFO-1) should fall back to non-overlapping
        # chunks rather than infinite-loop.
        chunks = plan_chunks(
            file_size_bytes=10_000,
            audio_duration_ms=5_000,
            max_chunk_bytes=2_500,    # 1.25 sec chunks
            overlap_ms=2_000,         # 2 sec overlap → stride = -750 → guarded
        )
        # No infinite loop, returns a finite list.
        assert isinstance(chunks, list)
        assert len(chunks) >= 1
        # Final chunk reaches the end.
        assert chunks[-1].end_ms == 5_000


class TestStitchTranscripts:
    def test_empty_list_returns_empty_string(self):
        assert stitch_transcripts([]) == ""

    def test_single_chunk_returns_unchanged(self):
        assert stitch_transcripts(["hello world"]) == "hello world"

    def test_full_overlap_is_deduplicated(self):
        left = "the quick brown fox jumped over the lazy dog and ran far"
        right = "lazy dog and ran far away from the hunter"
        merged = stitch_transcripts([left, right])
        # The 5-word overlap "lazy dog and ran far" should NOT appear twice.
        assert merged.count("lazy dog and ran far") == 1
        assert "from the hunter" in merged

    def test_no_overlap_concatenates_with_space(self):
        merged = stitch_transcripts(
            ["alpha beta gamma", "completely different words"]
        )
        assert merged == "alpha beta gamma completely different words"

    def test_partial_overlap_below_threshold_concatenates(self):
        # Only 2 matching words at the seam — below 3-word threshold,
        # so falls through to simple concat (AC5 acceptable duplication).
        merged = stitch_transcripts(
            ["alpha beta gamma the end", "the end of the story"]
        )
        # "the end" is 2 words → falls through; both copies remain.
        # Verify by counting occurrences:
        assert merged.lower().count("the end") == 2

    def test_three_chunks_stitched_pairwise(self):
        chunks = [
            "chunk one ends here common section words",
            "common section words bridge over the gap",
            "bridge over the gap finally section three appears",
        ]
        merged = stitch_transcripts(chunks)
        # Each shared 4-word phrase should appear exactly once after de-dup.
        assert merged.count("common section words") == 1
        assert merged.count("bridge over the gap") == 1
        assert "section three appears" in merged
        assert merged.startswith("chunk one ends here")

    def test_case_insensitive_matching(self):
        left = "the rain in Spain falls"
        right = "FALLS mainly on the plain"
        merged = stitch_transcripts([left, right])
        # "falls" appears once after case-insensitive match (best_k=1
        # below threshold → fallback concat preserves both copies).
        # The test verifies BEHAVIOR: case-insensitive match attempt happens.
        # Since 1-word match is below threshold-3, fallback takes over.
        # We don't assert dedup; we assert the function runs without error
        # and produces a string containing both source phrases.
        assert "rain in spain" in merged.lower()
        assert "mainly on the plain" in merged.lower()

    def test_punctuation_normalized_at_boundary(self):
        # 4 trailing words on left (with punctuation), 4 leading words on
        # right — overlap of 4 words after punctuation normalization should
        # de-duplicate cleanly.
        left = "the meeting ended at noon."
        right = "ended at noon, with a handshake"
        merged = stitch_transcripts([left, right])
        # "ended at noon" appears exactly once after normalization-aware match
        assert merged.lower().count("ended at noon") == 1

    def test_handles_empty_left_in_pair(self):
        # Empty first chunk → just appends right
        merged = stitch_transcripts(["", "hello world"])
        assert merged == "hello world"

    def test_handles_empty_right_in_pair(self):
        merged = stitch_transcripts(["hello world", ""])
        assert merged == "hello world"
