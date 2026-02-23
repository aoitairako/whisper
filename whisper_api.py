#!/usr/bin/env python3
"""
Whisper API Client
OpenAI Whisper API wrapper with vocabulary support and multi-format output.
"""

import json
import os
from pathlib import Path
from typing import Optional

import openai


class WhisperClient:
    """OpenAI Whisper API client with vocabulary and multi-format output."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY env var not set")
        self.client = openai.OpenAI(api_key=self.api_key)

    def _load_vocabulary(self, vocab_path: str) -> str:
        """Load vocabulary file and return as comma-separated prompt string."""
        p = Path(vocab_path).expanduser()
        if not p.exists():
            return ""
        terms = []
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                terms.append(line)
        return ", ".join(terms[:200])  # Whisper prompt limit ~200 tokens

    def transcribe(
        self,
        audio_path: str,
        output_dir: Optional[str] = None,
        vocabulary_path: Optional[str] = None,
        language: str = "ja",
        output_formats: Optional[list] = None,
    ) -> dict:
        """
        Transcribe audio file using Whisper API.

        Returns dict with output file paths and metadata.
        """
        audio_path = Path(audio_path).expanduser()
        if not audio_path.exists():
            return {"success": False, "error": f"File not found: {audio_path}"}

        # Determine output directory
        if output_dir:
            out_dir = Path(output_dir).expanduser()
        else:
            out_dir = audio_path.parent / "transcripts"
        out_dir.mkdir(parents=True, exist_ok=True)

        # Load vocabulary as prompt
        prompt = ""
        if vocabulary_path:
            prompt = self._load_vocabulary(vocabulary_path)

        if output_formats is None:
            output_formats = ["txt", "srt", "vtt", "json"]

        output_files = {}
        stem = audio_path.stem

        # Transcribe with text format first (plain text)
        with open(audio_path, "rb") as f:
            kwargs = {
                "model": "whisper-1",
                "file": f,
                "language": language,
                "response_format": "verbose_json",
            }
            if prompt:
                kwargs["prompt"] = prompt

            result = self.client.audio.transcriptions.create(**kwargs)

        # Save each requested format
        if "txt" in output_formats:
            txt_path = out_dir / f"{stem}.txt"
            txt_path.write_text(result.text, encoding="utf-8")
            output_files["txt"] = str(txt_path)

        if "json" in output_formats:
            json_path = out_dir / f"{stem}.json"
            json_path.write_text(
                json.dumps(result.model_dump(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            output_files["json"] = str(json_path)

        if "srt" in output_formats or "vtt" in output_formats:
            segments = getattr(result, "segments", [])
            if "srt" in output_formats:
                srt_path = out_dir / f"{stem}.srt"
                srt_path.write_text(
                    self._to_srt(segments), encoding="utf-8"
                )
                output_files["srt"] = str(srt_path)

            if "vtt" in output_formats:
                vtt_path = out_dir / f"{stem}.vtt"
                vtt_path.write_text(
                    self._to_vtt(segments), encoding="utf-8"
                )
                output_files["vtt"] = str(vtt_path)

        return {
            "success": True,
            "audio_file": str(audio_path),
            "output_dir": str(out_dir),
            "output_files": output_files,
            "language": language,
            "vocabulary_used": bool(prompt),
            "text_preview": result.text[:200] + "..." if len(result.text) > 200 else result.text,
        }

    def _seconds_to_srt_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def _seconds_to_vtt_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

    def _to_srt(self, segments: list) -> str:
        lines = []
        for i, seg in enumerate(segments, 1):
            start = self._seconds_to_srt_time(seg.get("start", 0))
            end = self._seconds_to_srt_time(seg.get("end", 0))
            text = seg.get("text", "").strip()
            lines.append(f"{i}\n{start} --> {end}\n{text}\n")
        return "\n".join(lines)

    def _to_vtt(self, segments: list) -> str:
        lines = ["WEBVTT\n"]
        for i, seg in enumerate(segments, 1):
            start = self._seconds_to_vtt_time(seg.get("start", 0))
            end = self._seconds_to_vtt_time(seg.get("end", 0))
            text = seg.get("text", "").strip()
            lines.append(f"{i}\n{start} --> {end}\n{text}\n")
        return "\n".join(lines)

    def get_unprocessed_meetings(self, meetings_base_dir: str) -> list:
        """Find meeting directories without transcripts/ subdirectory."""
        base = Path(meetings_base_dir).expanduser()
        if not base.exists():
            return []

        unprocessed = []
        # Pattern: YYYYMM/YYYYMMDD_meeting/
        for month_dir in sorted(base.iterdir()):
            if not month_dir.is_dir():
                continue
            for meeting_dir in sorted(month_dir.iterdir()):
                if not meeting_dir.is_dir():
                    continue
                transcripts = meeting_dir / "transcripts"
                has_transcripts = transcripts.exists() and any(transcripts.glob("*.txt"))
                if not has_transcripts:
                    # Check for audio files
                    audio_files = list(meeting_dir.rglob("*.m4a")) + list(meeting_dir.rglob("*.mp4"))
                    if audio_files:
                        unprocessed.append({
                            "path": str(meeting_dir),
                            "name": meeting_dir.name,
                            "audio_files": [str(f) for f in audio_files],
                        })
        return unprocessed
