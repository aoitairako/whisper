"""Core transcription functions for Whisper."""

import json
import os
from pathlib import Path

from .formats import to_srt, to_vtt
from .vocabulary import get_vocab_dirs, load_vocabulary
from .dictionary import load_dictionaries, apply_dictionary_to_result

_IS_DOCKER = os.environ.get("MCP_TRANSPORT") == "sse"


def _get_client():
    """Create OpenAI client (lazy import)."""
    import openai
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return openai.OpenAI(api_key=api_key)


def transcribe(
    audio_path: str,
    output_dir: str = "",
    vocabulary_path: str = "",
    vocabulary_prompt: str = "",
    language: str = "ja",
    output_formats: str = "txt,srt,vtt,json",
    extra_vocab_dirs: list[Path] | None = None,
) -> dict:
    """Transcribe an audio file using OpenAI Whisper API.

    Args:
        audio_path: Absolute path to audio file (.m4a, .mp4, .mp3, .wav, etc.)
        output_dir: Output directory (default: audio_path's parent/transcripts/)
        vocabulary_path: Path to vocabulary file for improved recognition
        vocabulary_prompt: Pre-built prompt string (takes precedence over vocabulary_path)
        language: Language code (default: ja)
        output_formats: Comma-separated formats: txt, srt, vtt, json (default: all)
        extra_vocab_dirs: Additional vocabulary directories to search
    """
    try:
        client = _get_client()
        apath = Path(audio_path).expanduser()
        if not apath.exists():
            return {"status": "error", "message": f"Audio file not found: {audio_path}"}

        if output_dir:
            out_dir = Path(output_dir).expanduser()
        else:
            out_dir = apath.parent / "transcripts"
        out_dir.mkdir(parents=True, exist_ok=True)

        prompt = vocabulary_prompt
        if not prompt and vocabulary_path:
            prompt = load_vocabulary(vocabulary_path)

        formats = [f.strip() for f in output_formats.split(",") if f.strip()]

        with open(apath, "rb") as f:
            kwargs = {
                "model": "whisper-1",
                "file": f,
                "language": language,
                "response_format": "verbose_json",
            }
            if prompt:
                kwargs["prompt"] = prompt
            result = client.audio.transcriptions.create(**kwargs)

        replacements = load_dictionaries(extra_vocab_dirs)
        result = apply_dictionary_to_result(result, replacements)

        stem = apath.stem
        if stem.endswith(".compressed"):
            stem = stem[: -len(".compressed")]
        output_files = {}

        if "txt" in formats:
            txt_path = out_dir / f"{stem}.txt"
            txt_path.write_text(result.text, encoding="utf-8")
            output_files["txt"] = str(txt_path)

        if "json" in formats:
            json_path = out_dir / f"{stem}.json"
            json_path.write_text(
                json.dumps(result.model_dump(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            output_files["json"] = str(json_path)

        segments = getattr(result, "segments", [])
        if "srt" in formats:
            srt_path = out_dir / f"{stem}.srt"
            srt_path.write_text(to_srt(segments), encoding="utf-8")
            output_files["srt"] = str(srt_path)

        if "vtt" in formats:
            vtt_path = out_dir / f"{stem}.vtt"
            vtt_path.write_text(to_vtt(segments), encoding="utf-8")
            output_files["vtt"] = str(vtt_path)

        preview = result.text[:300] + "..." if len(result.text) > 300 else result.text

        return {
            "status": "success",
            "audio_file": str(apath),
            "output_dir": str(out_dir),
            "output_files": output_files,
            "language": language,
            "vocabulary_used": bool(prompt),
            "text_preview": preview,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def batch(
    meetings_base_dir: str,
    vocabulary_path: str = "",
    extra_vocab_dirs: list[Path] | None = None,
) -> dict:
    """Batch transcribe unprocessed meetings in a directory."""
    try:
        base = Path(meetings_base_dir).expanduser()
        if not base.exists():
            return {"status": "error", "message": f"Directory not found: {meetings_base_dir}"}

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
                    audio_files = (
                        list(meeting_dir.rglob("*.m4a"))
                        + list(meeting_dir.rglob("*.mp4"))
                        + list(meeting_dir.rglob("*.mp3"))
                        + list(meeting_dir.rglob("*.wav"))
                    )
                    if audio_files:
                        unprocessed.append({
                            "path": str(meeting_dir),
                            "name": meeting_dir.name,
                            "audio_files": [str(f) for f in audio_files],
                        })

        if not unprocessed:
            return {"status": "success", "message": "No unprocessed meetings found", "total": 0}

        results = []
        success = 0
        failed = 0

        for meeting in unprocessed:
            audio_path = meeting["audio_files"][0]
            result = transcribe(
                audio_path=audio_path,
                vocabulary_path=vocabulary_path,
                extra_vocab_dirs=extra_vocab_dirs,
            )
            result["meeting"] = meeting["name"]
            results.append(result)
            if result.get("status") == "success":
                success += 1
            else:
                failed += 1

        return {
            "status": "success",
            "total": len(unprocessed),
            "processed": success,
            "failed": failed,
            "results": results,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def process_voice_memos(
    meetings_dir: str | Path | None = None,
    extra_vocab_dirs: list[Path] | None = None,
) -> dict:
    """Scan and transcribe unprocessed voice memos in the Meetings directory."""
    try:
        if meetings_dir:
            meetings_dir = Path(meetings_dir)
        else:
            meetings_dir = (
                Path("/meetings") if _IS_DOCKER
                else Path.home() / "Library" / "CloudStorage" / "SynologyDrive-tds224plus_home" / "Meetings"
            )
        if not meetings_dir.exists():
            return {
                "status": "error",
                "message": f"Meetings directory not found: {meetings_dir}",
                "hint": "Create the directory or check Synology Drive sync",
            }

        processed_file = meetings_dir / ".processed"
        processed = set()
        if processed_file.exists():
            processed = set(processed_file.read_text(encoding="utf-8").splitlines())

        audio_exts = {".m4a", ".mp4", ".mp3", ".wav"}
        audio_files = []
        for ext in audio_exts:
            for f in meetings_dir.rglob(f"*{ext}"):
                if "@eaDir" not in f.parts:
                    audio_files.append(f)
        audio_files.sort()

        # Auto-detect vocabulary from default vocab dir
        vocab_path = ""
        vocab_dirs = get_vocab_dirs(extra_vocab_dirs)
        for vdir in vocab_dirs:
            general_vocab = vdir / "general_vocabulary.txt"
            if general_vocab.exists():
                vocab_path = str(general_vocab)
                break

        results = []
        for af in audio_files:
            af_str = str(af)
            if af_str in processed:
                continue

            transcripts_dir = af.parent / "transcripts"
            if transcripts_dir.exists() and (transcripts_dir / f"{af.stem}.txt").exists():
                with open(processed_file, "a", encoding="utf-8") as pf:
                    pf.write(af_str + "\n")
                continue

            result = transcribe(
                audio_path=af_str,
                vocabulary_path=vocab_path,
                extra_vocab_dirs=extra_vocab_dirs,
            )
            if result.get("status") == "success":
                with open(processed_file, "a", encoding="utf-8") as pf:
                    pf.write(af_str + "\n")
            results.append(result)

        if not results:
            return {
                "status": "success",
                "message": "No unprocessed voice memos found",
                "meetings_dir": str(meetings_dir),
                "total_audio_files": len(audio_files),
            }

        success = sum(1 for r in results if r.get("status") == "success")
        return {
            "status": "success",
            "total": len(results),
            "processed": success,
            "failed": len(results) - success,
            "meetings_dir": str(meetings_dir),
            "results": results,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
