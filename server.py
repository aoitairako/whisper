#!/usr/bin/env python3
"""
Whisper MCP Server
Standalone MCP server for audio transcription via OpenAI Whisper API.

Usage:
    python3 server.py
"""

import os
import sys
from pathlib import Path

# Add app directory to path
_app_dir = Path(__file__).resolve().parent
if str(_app_dir) not in sys.path:
    sys.path.insert(0, str(_app_dir))

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(_app_dir / ".env")
except ImportError:
    pass

from fastmcp import FastMCP

mcp = FastMCP("whisper")

_client = None
_APP_VOCAB_DIR = _app_dir / "vocabularies"


def _get_client():
    global _client
    if _client is None:
        from whisper_api import WhisperClient
        _client = WhisperClient()
    return _client


@mcp.tool()
async def whisper_status() -> dict:
    """Whisper MCP server の状態確認（OpenAI API key 有効性含む）"""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    configured = bool(api_key)

    vocabs = []
    if _APP_VOCAB_DIR.exists():
        vocabs = [f.name for f in _APP_VOCAB_DIR.glob("*.txt")]

    return {
        "api_key_configured": configured,
        "api_key_preview": f"{api_key[:8]}..." if configured else None,
        "vocabularies_available": vocabs,
        "app_vocab_dir": str(_APP_VOCAB_DIR),
        "server_version": "v1.0.0",
    }


@mcp.tool()
async def whisper_transcribe(
    audio_path: str,
    output_dir: str = None,
    vocabulary_path: str = None,
    language: str = "ja",
    output_formats: list = None,
) -> dict:
    """
    音声ファイルを文字起こし。
    output_dir 未指定時は audio_path の transcripts/ に保存。
    vocabulary_path で語彙辞書を指定すると固有名詞認識が向上。
    """
    if output_formats is None:
        output_formats = ["txt", "srt", "vtt", "json"]

    client = _get_client()
    return client.transcribe(
        audio_path=audio_path,
        output_dir=output_dir,
        vocabulary_path=vocabulary_path,
        language=language,
        output_formats=output_formats,
    )


@mcp.tool()
async def whisper_batch(
    meetings_base_dir: str,
    vocabulary_path: str = None,
) -> dict:
    """
    ディレクトリ内の未処理会議を一括文字起こし。
    transcripts/*.txt が存在しない会議が対象。
    """
    client = _get_client()
    unprocessed = client.get_unprocessed_meetings(meetings_base_dir)

    if not unprocessed:
        return {"message": "未処理の会議はありません", "total": 0}

    results = []
    success = 0
    failed = 0

    for meeting in unprocessed:
        audio_path = meeting["audio_files"][0]
        result = client.transcribe(
            audio_path=audio_path,
            vocabulary_path=vocabulary_path,
        )
        result["meeting"] = meeting["name"]
        results.append(result)
        if result.get("success"):
            success += 1
        else:
            failed += 1

    return {
        "total": len(unprocessed),
        "processed": success,
        "failed": failed,
        "results": results,
    }


@mcp.tool()
async def whisper_vocabulary_list() -> dict:
    """利用可能な語彙ファイル一覧"""
    app_vocabs = []
    if _APP_VOCAB_DIR.exists():
        app_vocabs = [
            {"name": f.name, "path": str(f), "lines": len(f.read_text().splitlines())}
            for f in sorted(_APP_VOCAB_DIR.glob("*.txt"))
        ]

    return {
        "app_vocabularies": app_vocabs,
        "app_vocab_dir": str(_APP_VOCAB_DIR),
        "usage": "vocabulary_path パラメータに絶対パスを指定してください",
    }


@mcp.tool()
async def whisper_vocabulary_add(vocab_file: str, terms: list) -> dict:
    """語彙ファイルにエントリを追加。重複は自動的にスキップ。"""
    p = Path(vocab_file).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)

    existing = set()
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                existing.add(line)

    added = []
    skipped = []
    for term in terms:
        term = term.strip()
        if term and term not in existing:
            existing.add(term)
            added.append(term)
        else:
            skipped.append(term)

    if added:
        with open(p, "a", encoding="utf-8") as f:
            f.write("\n".join(added) + "\n")

    return {
        "added": len(added),
        "skipped": len(skipped),
        "added_terms": added,
        "total_lines": len(existing),
        "file": str(p),
    }


if __name__ == "__main__":
    mcp.run()
