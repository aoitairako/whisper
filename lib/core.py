"""Core transcription functions for Whisper.

Backend strategy:
  WHISPER_BACKEND=auto   (default) — local-first on Mac, API in Docker
  WHISPER_BACKEND=local            — local only (error if unavailable)
  WHISPER_BACKEND=api              — OpenAI API only
  WHISPER_LOCAL_MODEL=large-v3-turbo (default, env override)

Local backend detection priority:
  1. openai-whisper Python package (import whisper)
  2. openai-whisper CLI (/usr/local/bin/whisper or PATH)
  → fallback: OpenAI API
"""

import importlib
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .formats import to_srt, to_vtt
from .vocabulary import get_vocab_dirs, load_vocabulary
from .dictionary import load_dictionaries, apply_dictionary_to_result

_IS_DOCKER = os.environ.get("MCP_TRANSPORT") == "sse"


# ── Unified result object ────────────────────────────────────────────────

@dataclass
class _WhisperResult:
    """Unified transcription result for both local and API backends."""
    text: str
    segments: list = field(default_factory=list)
    language: str = "ja"


# ── Local backend detection ──────────────────────────────────────────────

_local_backend_cache: Optional[str] = None
_local_backend_detected: bool = False


def _detect_local_backend() -> Optional[str]:
    """Detect available local Whisper backend.

    Priority: openai-whisper Python pkg → CLI
    Returns: "openai_whisper" | "cli" | None
    """
    # 1. openai-whisper Python package (best: stays in-process)
    try:
        importlib.import_module("whisper")
        return "openai_whisper"
    except ImportError:
        pass

    # 2. whisper CLI (Python 3.10 install at /usr/local/bin/whisper)
    cli = shutil.which("whisper") or "/usr/local/bin/whisper"
    if Path(cli).exists():
        return "cli"

    return None


def _get_local_backend() -> Optional[str]:
    global _local_backend_cache, _local_backend_detected
    if not _local_backend_detected:
        _local_backend_cache = _detect_local_backend()
        _local_backend_detected = True
    return _local_backend_cache


def _local_model() -> str:
    return os.environ.get("WHISPER_LOCAL_MODEL", "large-v3-turbo")


def _resolve_effective_backend(backend: str) -> str:
    """Return effective backend: "local_first" | "local" | "api"."""
    if backend == "auto":
        return "api" if _IS_DOCKER else "local_first"
    return backend  # "local" | "api"


# ── Local transcription ──────────────────────────────────────────────────

def _transcribe_local_python(audio_path: Path, language: str, prompt: str) -> _WhisperResult:
    """Transcribe using openai-whisper Python package (in-process, no API call)."""
    import whisper as _whisper_pkg
    model = _whisper_pkg.load_model(_local_model())
    kwargs: dict = {"language": language, "verbose": False}
    if prompt:
        kwargs["initial_prompt"] = prompt
    result = model.transcribe(str(audio_path), **kwargs)
    return _WhisperResult(
        text=result.get("text", "").strip(),
        segments=result.get("segments", []),
        language=result.get("language", language),
    )


def _transcribe_local_cli(audio_path: Path, language: str, prompt: str) -> _WhisperResult:
    """Transcribe using openai-whisper CLI subprocess (Python 3.10 install)."""
    cli = shutil.which("whisper") or "/usr/local/bin/whisper"
    model = _local_model()

    with tempfile.TemporaryDirectory() as tmp_dir:
        cmd = [
            cli, str(audio_path),
            "--model", model,
            "--language", language,
            "--output_dir", tmp_dir,
            "--output_format", "json",
            "--fp16", "False",  # Intel Mac: no FP16
        ]
        if prompt:
            cmd += ["--initial_prompt", prompt]

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
        if proc.returncode != 0:
            raise RuntimeError(f"whisper CLI failed (exit {proc.returncode}): {proc.stderr[-500:]}")

        json_file = Path(tmp_dir) / f"{audio_path.stem}.json"
        if not json_file.exists():
            raise RuntimeError(f"whisper CLI did not produce output: {proc.stdout[-300:]}")

        data = json.loads(json_file.read_text(encoding="utf-8"))

    return _WhisperResult(
        text=data.get("text", "").strip(),
        segments=data.get("segments", []),
        language=data.get("language", language),
    )


def _transcribe_local(audio_path: Path, language: str, prompt: str) -> _WhisperResult:
    """Transcribe using the best available local backend."""
    lb = _get_local_backend()
    if lb == "openai_whisper":
        return _transcribe_local_python(audio_path, language, prompt)
    elif lb == "cli":
        return _transcribe_local_cli(audio_path, language, prompt)
    raise RuntimeError(
        "No local Whisper backend found. "
        "Install openai-whisper: pip install openai-whisper"
    )


# ── OpenAI API transcription ─────────────────────────────────────────────

def _get_api_client():
    import openai
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set and no local backend available")
    return openai.OpenAI(api_key=api_key)


def _transcribe_api(audio_path: Path, language: str, prompt: str) -> _WhisperResult:
    """Transcribe using OpenAI Whisper API (cloud, 25MB limit)."""
    client = _get_api_client()
    with open(audio_path, "rb") as f:
        kwargs: dict = {
            "model": "whisper-1",
            "file": f,
            "language": language,
            "response_format": "verbose_json",
        }
        if prompt:
            kwargs["prompt"] = prompt
        result = client.audio.transcriptions.create(**kwargs)

    return _WhisperResult(
        text=result.text,
        segments=getattr(result, "segments", []),
        language=getattr(result, "language", language),
    )


# ── Output writing ───────────────────────────────────────────────────────

def _write_outputs(result: _WhisperResult, stem: str, out_dir: Path, formats: list) -> dict:
    """Write transcription result to output files. Returns {format: path}."""
    output_files = {}

    if "txt" in formats:
        p = out_dir / f"{stem}.txt"
        p.write_text(result.text, encoding="utf-8")
        output_files["txt"] = str(p)

    if "json" in formats:
        p = out_dir / f"{stem}.json"
        p.write_text(
            json.dumps(
                {"text": result.text, "segments": result.segments, "language": result.language},
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )
        output_files["json"] = str(p)

    if "srt" in formats:
        p = out_dir / f"{stem}.srt"
        p.write_text(to_srt(result.segments), encoding="utf-8")
        output_files["srt"] = str(p)

    if "vtt" in formats:
        p = out_dir / f"{stem}.vtt"
        p.write_text(to_vtt(result.segments), encoding="utf-8")
        output_files["vtt"] = str(p)

    return output_files


# ── Status helper ────────────────────────────────────────────────────────

def get_local_status() -> dict:
    """Return local backend availability info for status tools."""
    lb = _get_local_backend()
    model = _local_model()
    cached = []
    cache_dir = Path.home() / ".cache" / "whisper"
    if cache_dir.exists():
        cached = [f.stem for f in sorted(cache_dir.glob("*.pt"))]
    return {
        "local_backend": lb or "none",
        "local_model": model,
        "local_model_cached": model in cached or f"{model}.pt" in [f.name for f in cache_dir.glob("*.pt")] if cache_dir.exists() else False,
        "cached_models": cached,
        "is_docker": _IS_DOCKER,
    }


# ── Main transcribe() ────────────────────────────────────────────────────

def transcribe(
    audio_path: str,
    output_dir: str = "",
    vocabulary_path: str = "",
    vocabulary_prompt: str = "",
    language: str = "ja",
    output_formats: str = "txt,srt,vtt,json",
    extra_vocab_dirs: list[Path] | None = None,
    backend: str = "auto",
) -> dict:
    """Transcribe an audio file.

    Args:
        audio_path: Absolute path to audio file (.m4a, .mp4, .mp3, .wav, etc.)
        output_dir: Output directory (default: audio_path's parent/transcripts/)
        vocabulary_path: Vocabulary file for improved recognition
        vocabulary_prompt: Pre-built prompt string (overrides vocabulary_path)
        language: Language code (default: ja)
        output_formats: Comma-separated: txt, srt, vtt, json (default: all)
        extra_vocab_dirs: Additional vocabulary directories to search
        backend: "auto" | "local" | "api"
            "auto"  — local-first on Mac, API in Docker (default)
            "local" — local model only (no API call, no 25MB limit)
            "api"   — OpenAI API only
    """
    try:
        apath = Path(audio_path).expanduser()
        if not apath.exists():
            return {"status": "error", "message": f"Audio file not found: {audio_path}"}

        out_dir = Path(output_dir).expanduser() if output_dir else apath.parent / "transcripts"
        out_dir.mkdir(parents=True, exist_ok=True)

        prompt = vocabulary_prompt
        if not prompt and vocabulary_path:
            prompt = load_vocabulary(vocabulary_path)

        formats = [f.strip() for f in output_formats.split(",") if f.strip()]
        effective = _resolve_effective_backend(backend)

        result: _WhisperResult
        used_backend: str

        if effective == "local_first":
            try:
                result = _transcribe_local(apath, language, prompt)
                used_backend = f"local:{_get_local_backend()}:{_local_model()}"
            except Exception as e:
                result = _transcribe_api(apath, language, prompt)
                used_backend = f"api (local failed: {e})"
        elif effective == "local":
            result = _transcribe_local(apath, language, prompt)
            used_backend = f"local:{_get_local_backend()}:{_local_model()}"
        else:  # "api"
            result = _transcribe_api(apath, language, prompt)
            used_backend = "api"

        # Post-processing: apply dictionary corrections
        replacements = load_dictionaries(extra_vocab_dirs)
        if replacements:
            apply_dictionary_to_result(result, replacements)

        stem = apath.stem
        if stem.endswith(".compressed"):
            stem = stem[: -len(".compressed")]

        output_files = _write_outputs(result, stem, out_dir, formats)
        preview = result.text[:300] + "..." if len(result.text) > 300 else result.text

        return {
            "status": "success",
            "audio_file": str(apath),
            "output_dir": str(out_dir),
            "output_files": output_files,
            "language": language,
            "vocabulary_used": bool(prompt),
            "backend": used_backend,
            "text_preview": preview,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Batch / process_voice_memos ──────────────────────────────────────────

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
