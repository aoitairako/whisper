#!/bin/bash

# batch_transcribe.sh — 汎用バッチ文字起こしスクリプト v1.0
# ~/src/whisper/ standalone app
#
# 使用方法:
#   bash batch_transcribe.sh <meetings_base_dir> [vocabulary_file]
#   bash batch_transcribe.sh --status <meetings_base_dir>
#   bash batch_transcribe.sh --help
#
# 例:
#   bash batch_transcribe.sh \
#     ~/Documents/uranairo/project_management/communication/meetings \
#     ~/Documents/uranairo/whisper/vocabularies/uranairo_vocabulary.txt

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

WHISPER_APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MEMORY_LIMIT="4096m"

function show_help() {
    echo -e "${BOLD}batch_transcribe.sh${NC} — 汎用バッチ文字起こし (whisper standalone app)"
    echo ""
    echo -e "${BOLD}使用方法:${NC}"
    echo "  $0 <meetings_base_dir> [vocabulary_file]"
    echo "  $0 --status <meetings_base_dir>"
    echo "  $0 --help"
    echo ""
    echo -e "${BOLD}引数:${NC}"
    echo "  meetings_base_dir   会議ディレクトリのベースパス"
    echo "                      (YYYYMM/YYYYMMDD_meeting/ 構造を想定)"
    echo "  vocabulary_file     語彙辞書ファイルパス (optional)"
    echo "                      default: ${WHISPER_APP_DIR}/vocabularies/general_vocabulary.txt"
    echo ""
    echo -e "${BOLD}出力:${NC}"
    echo "  各会議ディレクトリの transcripts/ に txt, srt, vtt, json を生成"
}

function find_audio() {
    local dir="$1"
    local audio=""
    if [[ -d "$dir/video" ]]; then
        audio=$(find "$dir/video" -maxdepth 1 -type f \( -name "*.m4a" -o -name "*.mp4" \) 2>/dev/null | head -1)
    fi
    if [[ -z "$audio" ]]; then
        audio=$(find "$dir" -maxdepth 1 -type f \( -name "*.m4a" -o -name "*.mp4" \) 2>/dev/null | head -1)
    fi
    echo "$audio"
}

function is_processed() {
    local dir="$1"
    [[ -d "$dir/transcripts" ]] && [[ $(find "$dir/transcripts" -name "*.txt" 2>/dev/null | wc -l) -gt 0 ]]
}

function show_status() {
    local base_dir="$1"
    echo -e "${BOLD}📊 処理状況: $base_dir${NC}"
    echo ""
    local total=0
    local done_count=0
    local pending_count=0

    for month_dir in "$base_dir"/*/; do
        [[ -d "$month_dir" ]] || continue
        for meeting_dir in "$month_dir"*/; do
            [[ -d "$meeting_dir" ]] || continue
            audio=$(find_audio "$meeting_dir")
            [[ -n "$audio" ]] || continue
            ((total++))
            if is_processed "$meeting_dir"; then
                echo -e "  ${GREEN}✅${NC} $(basename "$meeting_dir")"
                ((done_count++))
            else
                size=$(du -h "$audio" 2>/dev/null | cut -f1)
                echo -e "  ${YELLOW}⏳${NC} $(basename "$meeting_dir") ($size)"
                ((pending_count++))
            fi
        done
    done

    echo ""
    echo -e "  完了: ${GREEN}$done_count件${NC} / 未処理: ${YELLOW}$pending_count件${NC} / 合計: $total件"
}

function process_meeting() {
    local meeting_dir="$1"
    local vocab_file="$2"
    local audio
    audio=$(find_audio "$meeting_dir")

    if [[ -z "$audio" ]]; then
        echo -e "${RED}❌ 音声ファイルが見つかりません: $meeting_dir${NC}"
        return 1
    fi

    local transcripts_dir="$meeting_dir/transcripts"
    mkdir -p "$transcripts_dir"

    echo -e "${CYAN}🎙  $(basename "$meeting_dir") ($(du -h "$audio" | cut -f1))${NC}"

    export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
    export OMP_NUM_THREADS=4

    local cmd="python3 ${WHISPER_APP_DIR}/server.py"

    # Use MCP tool via python directly for now
    python3 -c "
import sys
sys.path.insert(0, '${WHISPER_APP_DIR}')
from whisper_api import WhisperClient
import os

client = WhisperClient()
vocab = '${vocab_file}' if '${vocab_file}' else None
result = client.transcribe(
    audio_path='${audio}',
    output_dir='${transcripts_dir}',
    vocabulary_path=vocab,
    language='ja'
)
if result['success']:
    print('✅ 完了: ' + str(result['output_files']))
else:
    print('❌ エラー: ' + result.get('error', 'unknown'))
    sys.exit(1)
"
}

function batch_process() {
    local base_dir="$1"
    local vocab_file="${2:-${WHISPER_APP_DIR}/vocabularies/general_vocabulary.txt}"

    echo -e "${BOLD}🔄 バッチ文字起こし開始${NC}"
    echo -e "  ベースディレクトリ: ${CYAN}$base_dir${NC}"
    echo -e "  語彙辞書: ${CYAN}$vocab_file${NC}"
    echo ""

    local success=0
    local failed=0

    for month_dir in "$base_dir"/*/; do
        [[ -d "$month_dir" ]] || continue
        for meeting_dir in "$month_dir"*/; do
            [[ -d "$meeting_dir" ]] || continue
            audio=$(find_audio "$meeting_dir")
            [[ -n "$audio" ]] || continue

            if is_processed "$meeting_dir"; then
                echo -e "  ${BLUE}⏭  スキップ (処理済み): $(basename "$meeting_dir")${NC}"
                continue
            fi

            if process_meeting "$meeting_dir" "$vocab_file"; then
                ((success++))
            else
                ((failed++))
            fi
        done
    done

    echo ""
    echo -e "${BOLD}📊 完了: 成功 ${GREEN}${success}件${NC} / 失敗 ${RED}${failed}件${NC}"
}

# メイン処理
case "$1" in
    --help|-h)
        show_help
        ;;
    --status|-s)
        show_status "${2:-$(pwd)}"
        ;;
    "")
        show_help
        exit 1
        ;;
    *)
        batch_process "$1" "$2"
        ;;
esac
