# whisper — Whisper Transcription MCP Server

OpenAI Whisper API を MCP プロトコルで提供する standalone server。
会議録音・音声ファイルをテキスト化し、プロジェクト固有の語彙辞書で精度を向上させる。

## セットアップ

```bash
cd ~/Applications/whisper

# 依存パッケージのインストール
pip3 install -r requirements.txt

# 環境変数の設定
cp .env.example .env
# .env を編集して OPENAI_API_KEY を設定
```

## 起動

```bash
# 直接起動（テスト用）
python3 server.py

# The I / app-gateway 経由（通常）
# mcp-registry.yaml に登録済みであれば自動マウント
```

## MCP ツール一覧

| ツール | 説明 |
|-------|------|
| `whisper_status` | サーバー状態・API key 有効性確認 |
| `whisper_transcribe` | 単一ファイルの文字起こし |
| `whisper_batch` | ディレクトリ内の未処理会議を一括処理 |
| `whisper_vocabulary_list` | 利用可能な語彙ファイル一覧 |
| `whisper_vocabulary_add` | 語彙ファイルへのエントリ追加 |

## 語彙辞書の使い方

語彙辞書を指定することで、固有名詞・専門用語の認識精度が向上する。

```
# 語彙ファイルの形式（1行1語彙）
ウラナイロ
モフモフ
占い師
...
```

- **汎用辞書**: `~/Applications/whisper/vocabularies/general_vocabulary.txt`
- **プロジェクト固有**: 各プロジェクトの `whisper/vocabularies/` に配置

## バッチ処理スクリプト

```bash
# 特定ディレクトリの未処理会議をすべて処理
bash scripts/batch_transcribe.sh <meetings_base_dir> [vocabulary_file]

# 例
bash scripts/batch_transcribe.sh \
  ~/Documents/uranairo/project_management/communication/meetings \
  ~/Documents/uranairo/whisper/vocabularies/uranairo_vocabulary.txt
```

## 出力形式

各音声ファイルに対して `transcripts/` ディレクトリに以下を生成:

| 形式 | 説明 |
|-----|------|
| `.txt` | プレーンテキスト |
| `.srt` | 字幕ファイル（タイムスタンプ付き）|
| `.vtt` | Web字幕 |
| `.json` | 詳細データ（segments・timestamps 等）|

## 品質向上

### 2つの品質レイヤー

Whisperパイプラインの品質は2つのレイヤーで構成される:

| Layer | 処理 | 品質の鍵 |
|-------|------|---------|
| **Layer 1: 文字起こし** | 音声→テキスト | vocabulary, initial_prompt, post-processing |
| **Layer 2: ドキュメント生成** | テキスト→議事録等 | ゴールドスタンダード, コンテキスト, 品質基準 |

Layer 2の品質問題はLayer 1の再実行では解決しない。詳細: CONTEXT.md `LESSONS_LEARNED`

### Layer 1: 文字起こし品質

#### vocabulary連携
- アプリ汎用: `vocabularies/general_vocabulary.txt`
- プロジェクト固有: 各プロジェクトの `whisper/vocabularies/{project}_vocabulary.txt`

#### 推奨ワークフロー
1. 事前アジェンダがあれば、initial_promptに追加
2. vocabulary付きで文字起こし実行
3. post-processing（固有名詞修正スクリプト）で精度向上

#### 将来: 2-pass transcription
1回目のDraftをcontextとして2回目に渡し、認識精度をさらに向上させる計画。
詳細: AGENTS.md `QUALITY_IMPROVEMENT_STRATEGIES`

### Layer 2: ドキュメント生成品質

#### ゴールドスタンダードアプローチ
1. プロジェクトのAGENTS.mdに品質基準を定義（golden_rules, quality_checklist, anti_patterns）
2. 最も品質の高い既存ドキュメントをゴールドスタンダードとして指定
3. 生成時にtranscript + チーム情報 + 事前経緯 + 品質基準を渡す
4. 生成後にチェックリストで検証

#### バッチ再生成
既存のtranscriptから品質基準付きで一括再生成が可能:
- 品質基準を事後的に改善したとき
- バッチ生成で品質が不足したとき
- 並列サブエージェントでスケーラブルに処理

詳細: AGENTS.md `DOCUMENT_GENERATION_FRAMEWORK`

---

*whisper README.md v1.1.0*
*CARE-Pattern: R (README) layer*
