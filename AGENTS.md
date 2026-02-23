# AGENTS.md - whisper

> path: ~/Applications/whisper/
> role: whisper_transcription_mcp_server
> version: v1.1.0
> CARE-Pattern: A (Agents / Machine interface) layer

## WHISPER_IDENTITY

```python
WHISPER_MCP = {
    'role': 'whisper_transcription_mcp_server',
    'version': 'v1.1.0',
    'updated': '2026-02-23',
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

## QUALITY_IMPROVEMENT_STRATEGIES

```python
QUALITY_STRATEGIES = {
    'vocabulary_prompt': {
        'description': 'プロジェクト固有語彙をpromptパラメータに渡し、認識精度を向上',
        'implementation': 'whisper_api.py _load_vocabulary() → comma-separated → prompt kwarg',
        'limit': '200 tokens (200行上限)',
        'status': 'implemented',
    },
    'initial_prompt_context': {
        'description': '会議の事前コンテキスト（参加者名、議題、専門用語）をpromptに含める',
        'effect': 'Whisperが文脈を理解し、同音異義語の判定精度が向上',
        'best_practice': '参加者名+主要議題+専門用語を含む200語以内のプロンプト',
        'status': 'implemented (uranairo project tools)',
    },
    'post_processing': {
        'description': '文字起こし後の固有名詞自動修正',
        'implementation': 'プロジェクトごとの修正スクリプト（例: optimize_transcripts.py）',
        'pattern': '誤認識パターン辞書 → 一括置換 → .bakバックアップ',
        'status': 'implemented (uranairo)',
    },
    'two_pass_transcription': {
        'description': '1回目Draft → 固有名詞修正 → 修正テキストをpromptに付与して2回目実行',
        'effect': '1回目の文脈を2回目に引き継ぎ、認識精度がさらに向上',
        'implementation_plan': [
            'Pass 1: 通常のvocabulary promptで文字起こし',
            'Post-process: optimize_transcripts.py等で固有名詞修正',
            'Pass 2: 修正済みテキストの冒頭部分をpromptに追加して再文字起こし',
            'Compare: Pass 1 vs Pass 2 の差分を検証',
        ],
        'status': 'planned (future enhancement)',
    },
    'agenda_enhanced_prompt': {
        'description': '事前アジェンダをpromptに含めることで、議題固有の用語認識を強化',
        'effect': 'アジェンダに記載された固有名詞・議題キーワードの認識精度が向上',
        'workflow': [
            'MTG前: アジェンダをMarkdownで作成',
            'prompt生成: アジェンダからキーワードを抽出してinitial_promptに追加',
            '文字起こし: enhanced promptで実行',
        ],
        'status': 'planned (future enhancement)',
    },
}
```

## DOCUMENT_GENERATION_FRAMEWORK

```python
# 文字起こし→ドキュメント生成パイプラインの汎用品質フレームワーク
# 2026-02-23: uranairo 議事録再生成プロジェクトで実証・体系化

TWO_LAYER_QUALITY_MODEL = {
    'concept': '文字起こし品質（Layer 1）とドキュメント生成品質（Layer 2）は独立した品質基準を持つ',
    'layer_1_transcription': {
        'scope': '音声 → テキスト変換の正確性',
        'levers': ['vocabulary_prompt', 'initial_prompt_context', 'post_processing', 'two_pass'],
        'reference': 'QUALITY_IMPROVEMENT_STRATEGIES セクション',
    },
    'layer_2_document_generation': {
        'scope': 'テキスト → 構造化ドキュメント（議事録・要約・レポート等）の品質',
        'levers': ['gold_standard_template', 'quality_as_code', 'context_enhanced_generation'],
        'key_insight': 'Layer 1 が十分でも Layer 2 が不足すればドキュメント品質は低い。逆も然り。',
    },
    'anti_pattern': 'Layer 2 の品質問題を Layer 1 の再実行で解決しようとすること',
}

GOLD_STANDARD_TEMPLATE_PATTERN = {
    'concept': '1つの模範ドキュメントを「ゴールドスタンダード」として定義し、全生成の品質錨とする',
    'workflow': [
        '1. 最も品質の高い既存ドキュメントを選定（または手動で理想形を作成）',
        '2. そのドキュメントの構造・セクション・粒度を分析',
        '3. golden_rules / quality_checklist / anti_patterns として機械可読で定義',
        '4. 全ドキュメント生成時にゴールドスタンダードの構造を参照',
    ],
    'project_config': {
        'gold_standard_path': 'プロジェクトの AGENTS.md に定義',
        'example': "MEETING_NOTES_QUALITY['gold_standard'] = 'meetings/202602/20260217_meeting/...'",
    },
}

QUALITY_AS_CODE = {
    'concept': '品質基準を自然言語の暗黙知でなく、機械可読な構造体として AGENTS.md に定義',
    'components': {
        'golden_rules': '必ず守るべき原則（5-7個が適正）',
        'quality_checklist': '生成後に確認する具体的チェック項目',
        'anti_patterns': '避けるべきパターン（具体例付き）',
        'template_structure': '必須セクションの順序と内容',
    },
    'benefit': 'AI エージェントが品質基準をプロンプトとして直接利用できる',
}

CONTEXT_ENHANCED_GENERATION = {
    'concept': 'ドキュメント生成時に、transcript 以外のコンテキストを付与して品質を向上',
    'context_sources': {
        'team_info': 'チームメンバーの名前・役割・表記（漢字含む）',
        'prior_decisions': '前回MTGの決定事項、事前Chatwork等の経緯',
        'quality_standards': 'golden_rules + checklist + anti_patterns',
        'gold_standard': 'テンプレートの構造と粒度',
        'supplementary_docs': 'documents/ フォルダ内の関連資料',
    },
    'effect': 'transcript のみからの生成と比較して、背景・帰属・WHY の記録が飛躍的に向上',
}

BATCH_REGENERATION_PATTERN = {
    'concept': '既存 transcript を再利用し、改善されたプロンプト・コンテキストでドキュメントを再生成',
    'when_to_use': [
        '品質基準が事後的に定義・改善されたとき',
        'バッチ生成で品質が不足したドキュメントを回収するとき',
        '新しいコンテキスト（チーム情報・前回経緯）が判明したとき',
    ],
    'implementation': {
        'parallel_agents': 'N 件を M 並列サブエージェントで処理（例: 13件を4バッチ×2-4並列）',
        'agent_context': [
            'transcript 全文',
            'ゴールドスタンダードテンプレート構造',
            'チーム情報（AGENTS.md TEAM_STRUCTURE）',
            '品質基準（golden_rules + quality_checklist）',
            '補足資料（documents/ 内）',
        ],
        'verification': '全件に対して構造チェック + 品質チェック + 行数チェックを実施',
    },
    'proven_results': {
        'uranairo_2026_02_23': '13件の議事録を4バッチ並列で再生成、12/13件が全項目PASS',
    },
}
```

---

*whisper AGENTS.md v1.1.0*
*CARE-Pattern: Agents (Machine interface) layer*
