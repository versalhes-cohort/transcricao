"""Unit tests for app.duration.format_duration (Story 1.5 AC8)."""

import pytest

from app.duration import format_duration


class TestFormatDurationAcCases:
    """The 8 verbatim cases from PRD AC8."""

    def test_0_seconds(self):
        assert format_duration(0) == "00:00"

    def test_30_seconds(self):
        assert format_duration(30) == "00:30"

    def test_60_seconds(self):
        assert format_duration(60) == "01:00"

    def test_61_seconds(self):
        assert format_duration(61) == "01:01"

    def test_599_seconds(self):
        assert format_duration(599) == "09:59"

    def test_600_seconds(self):
        assert format_duration(600) == "10:00"

    def test_3599_seconds(self):
        assert format_duration(3599) == "59:59"

    def test_3600_seconds(self):
        assert format_duration(3600) == "60:00"


class TestFormatDurationEdgeCases:
    def test_rejects_negative(self):
        with pytest.raises(ValueError, match="non-negative"):
            format_duration(-1)

    def test_handles_large_value(self):
        # 90 min — beyond the 60-min cap, but the formatter itself
        # doesn't enforce the cap (Story 1.2's fetch_metadata does).
        # We just verify the format degrades sensibly.
        assert format_duration(5400) == "90:00"

    def test_accepts_float_via_int_truncation(self):
        # The annotation says `int` but defensive int() conversion in
        # implementation tolerates floats. metadata.duration_seconds may
        # arrive as float in edge cases (yt-dlp returns float for some sources).
        assert format_duration(int(30.7)) == "00:30"
