# AGENTS.md - whisper

> path: ~/Applications/whisper/
> role: whisper_transcription_mcp_server
> version: v1.0.0
> CARE-Pattern: A (Agents / Machine interface) layer

## WHISPER_IDENTITY

```python
WHISPER_MCP = {
    'role': 'whisper_transcription_mcp_server',
    'version': 'v1.0.0',
    'updated': '2026-02-21',
    'api': 'OpenAI Whisper API',
    'model': 'whisper-1',
    'transport': 'stdio (FastMCP)',
    'auth': 'OPENAI_API_KEY env',
    'default_language': 'ja'
}
```

## MCP_TOOLS

```python
MCP_TOOLS = {

    'whisper_status': {
        'description': 'Whisper MCP server の状態確認（API key 有効性含む）',
        'params': {},
        'returns': {
            'api_key_configured': bool,
            'vocabularies_available': list,
            'server_version': str
        }
    },

    'whisper_transcribe': {
        'description': '音声ファイルを文字起こし',
        'params': {
            'audio_path': 'str — 音声ファイルの絶対パス (.m4a, .mp4, .mp3, .wav 等)',
            'output_dir': 'str | None — 出力先ディレクトリ (default: audio_path の transcripts/)',
            'vocabulary_path': 'str | None — 語彙辞書ファイルパス',
            'language': 'str — 言語コード (default: "ja")',
            'output_formats': 'list — ["txt", "srt", "vtt", "json"] のサブセット'
        },
        'returns': {
            'success': bool,
            'output_files': 'dict — {format: file_path}',
            'duration_seconds': float
        }
    },

    'whisper_batch': {
        'description': 'ディレクトリ内の未処理会議を一括文字起こし (transcripts/ がないもの)',
        'params': {
            'meetings_base_dir': 'str — 会議ディレクトリのベースパス',
            'vocabulary_path': 'str | None — 語彙辞書ファイルパス'
        },
        'returns': {
            'total': int,
            'processed': int,
            'skipped': int,
            'failed': int,
            'results': list
        }
    },

    'whisper_vocabulary_list': {
        'description': '利用可能な語彙ファイル一覧',
        'params': {},
        'returns': {
            'app_vocabularies': 'list — ~/Applications/whisper/vocabularies/ 内',
            'found_in_cwd': 'list — カレントディレクトリの whisper/vocabularies/'
        }
    },

    'whisper_vocabulary_add': {
        'description': '語彙ファイルにエントリを追加',
        'params': {
            'vocab_file': 'str — 語彙ファイルのパス',
            'terms': 'list[str] — 追加する語彙リスト'
        },
        'returns': {
            'added': int,
            'skipped': int,
            'total_lines': int
        }
    }
}
```

## VOCABULARY_MANAGEMENT

```python
VOCABULARY = {
    'format': '1行1語彙（#コメント行可）',
    'prompt_usage': 'Whisper API の prompt パラメータに渡す（カンマ区切りテキスト）',
    'app_vocabularies': {
        'general': '~/Applications/whisper/vocabularies/general_vocabulary.txt'
    },
    'project_vocabularies': {
        'pattern': '{project}/whisper/vocabularies/{project}_vocabulary.txt',
        'uranairo': '~/Documents/uranairo/whisper/vocabularies/uranairo_vocabulary.txt'
    },
    'how_to_use': [
        'vocabulary_path に辞書ファイルを指定',
        '辞書内容が Whisper の prompt に渡され固有名詞認識が向上',
        'プロジェクト固有辞書 + general 辞書を組み合わせ可能'
    ]
}
```

## OUTPUT_FORMATS

```python
OUTPUT = {
    'formats': {
        'txt': 'プレーンテキスト（最もシンプル）',
        'srt': '字幕ファイル（タイムスタンプ付き）',
        'vtt': 'Web字幕（WebVTT形式）',
        'json': '詳細データ（segments, timestamps, confidence等）'
    },
    'location': '{input_dir}/transcripts/{audio_filename}.{ext}',
    'default_formats': ['txt', 'srt', 'vtt', 'json']
}
```

---

*whisper AGENTS.md v1.0.0*
*CARE-Pattern: Agents (Machine interface) layer*
