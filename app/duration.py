"""MM:SS formatter for video duration display.

Pure module — no side effects, no external imports beyond stdlib.
Per architecture §4.3, this is the canonical formatter for the
`Duração total: MM:SS` line in the rendered output (PRD AC3 / Story 1.5).
"""


def format_duration(seconds: int) -> str:
    """Format an integer number of seconds as MM:SS with zero-padding.

    Examples:
        0     → "00:00"
        30    → "00:30"
        60    → "01:00"
        61    → "01:01"
        599   → "09:59"
        600   → "10:00"
        3599  → "59:59"
        3600  → "60:00"   (60-min cap edge)

    Args:
        seconds: Non-negative integer number of seconds.

    Returns:
        MM:SS string with zero-padded minutes and seconds.

    Raises:
        ValueError: If `seconds` is negative.
    """
    if seconds < 0:
        raise ValueError(f"seconds must be non-negative, got {seconds}")
    minutes, remainder = divmod(int(seconds), 60)
    return f"{minutes:02d}:{remainder:02d}"
