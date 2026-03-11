"""Format conversion utilities for Whisper transcription output."""


def seconds_to_srt_time(seconds: float) -> str:
    """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def seconds_to_vtt_time(seconds: float) -> str:
    """Convert seconds to VTT time format (HH:MM:SS.mmm)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def seg_val(seg, key: str, default=None):
    """Get segment value — supports both dict and Pydantic model."""
    if isinstance(seg, dict):
        return seg.get(key, default)
    return getattr(seg, key, default)


def to_srt(segments: list) -> str:
    """Convert segments to SRT subtitle format."""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = seconds_to_srt_time(seg_val(seg, "start", 0))
        end = seconds_to_srt_time(seg_val(seg, "end", 0))
        text = (seg_val(seg, "text", "") or "").strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines)


def to_vtt(segments: list) -> str:
    """Convert segments to WebVTT subtitle format."""
    lines = ["WEBVTT\n"]
    for i, seg in enumerate(segments, 1):
        start = seconds_to_vtt_time(seg_val(seg, "start", 0))
        end = seconds_to_vtt_time(seg_val(seg, "end", 0))
        text = (seg_val(seg, "text", "") or "").strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines)
