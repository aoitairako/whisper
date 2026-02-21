# CONTEXT.md - whisper

> CARE-Pattern: C (Context / Why) layer

## IDENTITY

```yaml
name: whisper
identity: "Whisper transcription MCP Server — audio to text with vocabulary support"
version: v1.0.0
updated: 2026-02-21
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

*whisper CONTEXT.md v1.0.0*
*CARE-Pattern: Context layer*
