#!/usr/bin/env python3
"""
Whisper MCP Server
Standalone MCP server for audio transcription via OpenAI Whisper API.
Uses lib/ as Single Source of Truth for all business logic.

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
from lib import (
    transcribe as lib_transcribe,
    batch as lib_batch,
    process_voice_memos as lib_process_voice_memos,
    vocabulary_list as lib_vocabulary_list,
    vocabulary_add as lib_vocabulary_add,
    dictionary_list as lib_dictionary_list,
    dictionary_add as lib_dictionary_add,
    get_vocab_dirs,
)

mcp = FastMCP("whisper")

_APP_VOCAB_DIR = _app_dir / "vocabularies"


@mcp.tool()
async def whisper_status() -> dict:
    """Whisper MCP server の状態確認（OpenAI API key 有効性含む）"""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    configured = bool(api_key)

    vocabs = []
    for vdir in get_vocab_dirs():
        if vdir.exists():
            for f in sorted(vdir.glob("*.txt")):
                vocabs.append({
                    "name": f.name,
                    "path": str(f),
                    "lines": sum(1 for line in f.read_text(encoding="utf-8").splitlines()
                                 if line.strip() and not line.strip().startswith("#")),
                })

    return {
        "status": "ready" if configured else "no_api_key",
        "api_key_configured": configured,
        "api_key_preview": f"{api_key[:8]}..." if configured else None,
        "vocabularies": vocabs,
        "vocab_dirs": [str(d) for d in get_vocab_dirs()],
        "version": "2.0.0",
    }


@mcp.tool()
async def whisper_transcribe(
    audio_path: str,
    output_dir: str = "",
    vocabulary_path: str = "",
    vocabulary_prompt: str = "",
    language: str = "ja",
    output_formats: str = "txt,srt,vtt,json",
) -> dict:
    """音声ファイルを文字起こし（後処理辞書による自動修正付き）。
    output_dir 未指定時は audio_path の transcripts/ に保存。
    vocabulary_path で語彙辞書を指定すると固有名詞認識が向上。
    """
    return lib_transcribe(
        audio_path=audio_path,
        output_dir=output_dir,
        vocabulary_path=vocabulary_path,
        vocabulary_prompt=vocabulary_prompt,
        language=language,
        output_formats=output_formats,
    )


@mcp.tool()
async def whisper_batch(
    meetings_base_dir: str,
    vocabulary_path: str = "",
) -> dict:
    """ディレクトリ内の未処理会議を一括文字起こし。
    transcripts/*.txt が存在しない会議が対象。
    """
    return lib_batch(
        meetings_base_dir=meetings_base_dir,
        vocabulary_path=vocabulary_path,
    )


@mcp.tool()
async def whisper_process_voice_memos() -> dict:
    """Meetings ディレクトリのボイスメモを自動スキャン＆文字起こし。
    Docker: /meetings, Local: ~/Library/CloudStorage/SynologyDrive-tds224plus_home/Meetings/
    """
    return lib_process_voice_memos()


@mcp.tool()
async def whisper_vocabulary_list() -> dict:
    """利用可能な語彙ファイル一覧"""
    return lib_vocabulary_list()


@mcp.tool()
async def whisper_vocabulary_add(vocab_file: str, terms: list) -> dict:
    """語彙ファイルにエントリを追加。重複は自動的にスキップ。"""
    return lib_vocabulary_add(vocab_file, terms)


@mcp.tool()
async def whisper_dictionary_list() -> dict:
    """後処理置換辞書 (*.dict.json) の一覧"""
    return lib_dictionary_list()


@mcp.tool()
async def whisper_dictionary_add(dict_file: str, entries: list) -> dict:
    """後処理辞書にエントリを追加。重複はスキップ。"""
    return lib_dictionary_add(dict_file, entries)


if __name__ == "__main__":
    mcp.run()
