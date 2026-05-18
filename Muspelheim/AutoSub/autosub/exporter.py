"""AutoSub subtitle export module — SRT, VTT, TXT formats."""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from autosub.transcriber import Segment


def _format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp format: HH:MM:SS,mmm."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _format_vtt_time(seconds: float) -> str:
    """Convert seconds to WebVTT timestamp format: HH:MM:SS.mmm."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def export_srt(segments: list[Segment]) -> str:
    """Convert segments to SRT subtitle format.

    Args:
        segments: List of Segment objects with text and timing.

    Returns:
        SRT-formatted string.
    """
    lines: list[str] = []
    for i, seg in enumerate(segments, start=1):
        lines.append(str(i))
        lines.append(f"{_format_srt_time(seg.start)} --> {_format_srt_time(seg.end)}")
        lines.append(seg.text)
        lines.append("")  # blank line between entries
    return "\n".join(lines)


def export_vtt(segments: list[Segment]) -> str:
    """Convert segments to WebVTT subtitle format.

    Args:
        segments: List of Segment objects with text and timing.

    Returns:
        WebVTT-formatted string.
    """
    lines: list[str] = ["WEBVTT", ""]
    for _i, seg in enumerate(segments, start=1):
        lines.append(f"{_format_vtt_time(seg.start)} --> {_format_vtt_time(seg.end)}")
        lines.append(seg.text)
        lines.append("")  # blank line between entries
    return "\n".join(lines)


def export_txt(segments: list[Segment]) -> str:
    """Convert segments to plain text.

    Args:
        segments: List of Segment objects.

    Returns:
        Plain text with one segment per line.
    """
    return "\n".join(seg.text for seg in segments)


def export_segments(segments: list[Segment], fmt: str = "srt") -> str:
    """Export segments in the specified format.

    Args:
        segments: List of Segment objects.
        fmt: Output format — 'srt', 'vtt', or 'txt'.

    Returns:
        Formatted subtitle string.
    """
    exporters = {
        "srt": export_srt,
        "vtt": export_vtt,
        "txt": export_txt,
    }
    if fmt not in exporters:
        raise ValueError(f"Unsupported format: {fmt}. Supported: {list(exporters.keys())}")
    return exporters[fmt](segments)
