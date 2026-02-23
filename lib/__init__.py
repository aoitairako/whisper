"""Whisper transcription library — Single Source of Truth."""

from .core import transcribe, batch, process_voice_memos
from .vocabulary import load_vocabulary, vocabulary_list, vocabulary_add, get_vocab_dirs
from .dictionary import (
    load_dictionaries, apply_dictionary, apply_dictionary_to_result,
    dictionary_list, dictionary_add,
)
from .formats import to_srt, to_vtt

__all__ = [
    "transcribe", "batch", "process_voice_memos",
    "load_vocabulary", "vocabulary_list", "vocabulary_add", "get_vocab_dirs",
    "load_dictionaries", "apply_dictionary", "apply_dictionary_to_result",
    "dictionary_list", "dictionary_add",
    "to_srt", "to_vtt",
]
