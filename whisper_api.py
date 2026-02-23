#!/usr/bin/env python3
"""
Whisper API Client — Backward-compatibility shim.
Delegates to lib/ for all functionality.

Legacy interface preserved for existing callers.
New code should import from lib/ directly.
"""

import sys
from pathlib import Path
from typing import Optional

# Ensure lib/ is importable
_app_dir = Path(__file__).resolve().parent
if str(_app_dir) not in sys.path:
    sys.path.insert(0, str(_app_dir))

from lib.core import transcribe as lib_transcribe
from lib.formats import to_srt, to_vtt
from lib.vocabulary import load_vocabulary


class WhisperClient:
    """OpenAI Whisper API client — backward-compat wrapper around lib/."""

    def __init__(self, api_key: Optional[str] = None):
        import os
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY env var not set")

    def _load_vocabulary(self, vocab_path: str) -> str:
        return load_vocabulary(vocab_path)

    def transcribe(
        self,
        audio_path: str,
        output_dir: Optional[str] = None,
        vocabulary_path: Optional[str] = None,
        language: str = "ja",
        output_formats: Optional[list] = None,
    ) -> dict:
        if output_formats is None:
            output_formats = ["txt", "srt", "vtt", "json"]

        result = lib_transcribe(
            audio_path=str(audio_path),
            output_dir=output_dir or "",
            vocabulary_path=vocabulary_path or "",
            language=language,
            output_formats=",".join(output_formats),
        )

        # Translate status key for backward compat
        if "status" in result:
            result["success"] = result["status"] == "success"

        return result

    def _seconds_to_srt_time(self, seconds: float) -> str:
        from lib.formats import seconds_to_srt_time
        return seconds_to_srt_time(seconds)

    def _seconds_to_vtt_time(self, seconds: float) -> str:
        from lib.formats import seconds_to_vtt_time
        return seconds_to_vtt_time(seconds)

    def _to_srt(self, segments: list) -> str:
        return to_srt(segments)

    def _to_vtt(self, segments: list) -> str:
        return to_vtt(segments)

    def get_unprocessed_meetings(self, meetings_base_dir: str) -> list:
        """Find meeting directories without transcripts/ subdirectory."""
        base = Path(meetings_base_dir).expanduser()
        if not base.exists():
            return []

        unprocessed = []
        for month_dir in sorted(base.iterdir()):
            if not month_dir.is_dir():
                continue
            for meeting_dir in sorted(month_dir.iterdir()):
                if not meeting_dir.is_dir():
                    continue
                transcripts = meeting_dir / "transcripts"
                has_transcripts = transcripts.exists() and any(transcripts.glob("*.txt"))
                if not has_transcripts:
                    audio_files = list(meeting_dir.rglob("*.m4a")) + list(meeting_dir.rglob("*.mp4"))
                    if audio_files:
                        unprocessed.append({
                            "path": str(meeting_dir),
                            "name": meeting_dir.name,
                            "audio_files": [str(f) for f in audio_files],
                        })
        return unprocessed
