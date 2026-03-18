"""Tests for lib/vocabulary.py — no network or subprocess calls."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.vocabulary import get_vocab_dirs, load_vocabulary, vocabulary_add


def test_get_vocab_dirs_default():
    dirs = get_vocab_dirs()
    assert len(dirs) >= 1
    assert all(isinstance(d, Path) for d in dirs)


def test_get_vocab_dirs_extra():
    extra = Path("/tmp/extra_vocab")
    dirs = get_vocab_dirs([extra])
    assert extra in dirs


def test_load_vocabulary_nonexistent():
    result = load_vocabulary("/nonexistent/path/vocab.txt")
    assert result == ""


def test_load_vocabulary_real(tmp_path):
    vocab_file = tmp_path / "test.txt"
    vocab_file.write_text("word1\n# comment\nword2\n\nword3\n", encoding="utf-8")
    result = load_vocabulary(str(vocab_file))
    assert "word1" in result
    assert "word2" in result
    assert "word3" in result
    assert "comment" not in result


def test_vocabulary_add_new_terms(tmp_path):
    vocab_file = tmp_path / "vocab.txt"
    result = vocabulary_add(str(vocab_file), ["termA", "termB"])
    assert result["status"] == "success"
    assert result["added"] == 2
    assert result["skipped"] == 0


def test_vocabulary_add_deduplication(tmp_path):
    vocab_file = tmp_path / "vocab.txt"
    vocabulary_add(str(vocab_file), ["termA"])
    result = vocabulary_add(str(vocab_file), ["termA", "termB"])
    assert result["added"] == 1
    assert result["skipped"] == 1
