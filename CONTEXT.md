# CONTEXT.md - whisper

> CARE-Pattern: C (Context / Why) layer

## IDENTITY

```yaml
name: whisper
identity: "Whisper transcription MCP Server — audio to text with vocabulary support"
version: v1.1.0
updated: 2026-02-23
```

## WHY

```yaml
why: |
  会議録音・音声ファイルを高精度でテキスト化し、AI が「過去の会議で何が話されたか」を
  把握できる状態を作る。プロジェクト固有の語彙辞書で精度を向上させ、
  文字起こし→議事録→意思決定のフローを自動化する。

aims: |
  - OpenAI Whisper API で音声ファイルをテキスト化
  - プロジェクト固有の語彙辞書で認識精度を向上
  - 複数出力形式: txt, srt, vtt, json
  - 未処理ファイルの一括処理 (batch)
  - MCP 互換クライアントから透過的にアクセス
```

## ECOSYSTEM

```yaml
the_i:
  integration: "app-gateway 経由で自動マウント"
  registry: "~/Applications/the_i/config/mcp-registry.yaml"

project_vocabularies:
  pattern: "各プロジェクトの whisper/vocabularies/ にプロジェクト固有辞書を保持"
  example:
    uranairo: "~/Documents/uranairo/whisper/vocabularies/uranairo_vocabulary.txt"
  app_vocabulary: "~/Applications/whisper/vocabularies/general_vocabulary.txt"

output_location:
  pattern: "処理元ディレクトリの transcripts/ サブディレクトリに保存"
  example: "meetings/202602/20260209_meeting/transcripts/"

credentials:
  openai_api_key: "OPENAI_API_KEY 環境変数 または ~/.env"
```

---

## QUALITY_PHILOSOPHY

### 文字起こし品質の3段階

1. **基本品質**: vocabulary prompt + single-pass（現行の標準）
2. **強化品質**: agenda-enhanced prompt + post-processing（推奨）
3. **最高品質**: 2-pass transcription + agenda + post-processing（将来）

### プロジェクト間の品質基準共有

各プロジェクトの品質向上で得られた知見（誤認識パターン、effective prompt patterns）は
汎用vocabulary（general_vocabulary.txt）にフィードバックし、全プロジェクトの品質を底上げする。

---

## LESSONS_LEARNED

### 2-Layer品質モデルの発見（2026-02-23 uranairo実証）

文字起こしパイプラインには**2つの独立した品質レイヤー**がある:

| Layer | 処理 | 品質の鍵 | 問題の兆候 |
|-------|------|---------|-----------|
| **Layer 1** | 音声→テキスト | vocabulary, initial_prompt, post-processing | 固有名詞の誤り、hallucination |
| **Layer 2** | テキスト→構造化ドキュメント | ゴールドスタンダード, コンテキスト付与, 品質基準 | 薄い議事録、WHY不在、帰属不明 |

**最も重要な教訓**: Layer 2の品質問題をLayer 1の再実行で解決しようとしてはいけない。
uranairoプロジェクトでは、Layer 1（turboモデル+vocabulary+post-processing）は十分だったが、
Layer 2（バッチ生成の議事録品質）が不足していた。解決策は文字起こしの再実行ではなく、
**既存transcriptからの品質基準付き再生成**だった。

### ドキュメント品質は「暗黙知」から「コード」へ

品質基準が人の頭の中にしかない状態（暗黙知）では:
- バッチ生成時に品質が落ちる（1件ずつ対話的に作る時だけ高品質）
- 品質のばらつきが大きい
- 検証基準が曖昧

品質基準をAGENTS.mdに機械可読で定義することで:
- AIエージェントがプロンプトとして直接利用
- 自動検証が可能（構造チェック・チェックリスト）
- プロジェクト間で知見を共有可能

### ゴールドスタンダードのパワー

1つの模範ドキュメントが全体の品質を牽引する。
「この品質を全件で」と示せることが、AIにとっても人間にとっても最も分かりやすい品質定義。

---

## FOUNDATION

```yaml
foundation:
  project: "The Context Foundation"
  path: "~/context/"
  domain: "thecontextfoundation.org"
  relationship: "Audio to text — turning spoken Content into searchable Context"
```

---

*whisper CONTEXT.md v1.2.0*
*The Context Foundation: ~/context/CONTEXT.md v5.0.0*
