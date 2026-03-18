"""Tests for lib/dictionary.py — no network or subprocess calls."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.dictionary import apply_dictionary, dictionary_add, load_dictionaries


def test_apply_dictionary_basic():
    replacements = [{"from": "foo", "to": "bar"}]
    assert apply_dictionary("foo baz foo", replacements) == "bar baz bar"


def test_apply_dictionary_longest_first():
    """Longer patterns must be matched first."""
    replacements = [
        {"from": "AB", "to": "long"},
        {"from": "A", "to": "short"},
    ]
    # AB is longer so it matches first
    assert apply_dictionary("AB", replacements) == "long"


def test_load_dictionaries_empty(tmp_path, monkeypatch):
    import lib.vocabulary as vocab_mod

    monkeypatch.setattr(vocab_mod, "_DEFAULT_VOCAB_DIR", tmp_path)
    result = load_dictionaries()
    assert result == []


def test_load_dictionaries_valid_file(tmp_path, monkeypatch):
    import lib.vocabulary as vocab_mod

    monkeypatch.setattr(vocab_mod, "_DEFAULT_VOCAB_DIR", tmp_path)
    dict_file = tmp_path / "test.dict.json"
    dict_file.write_text(
        json.dumps({"replacements": [{"from": "x", "to": "y"}]}),
        encoding="utf-8",
    )
    result = load_dictionaries()
    assert len(result) == 1
    assert result[0]["from"] == "x"


def test_dictionary_add_new_entries(tmp_path):
    dict_file = tmp_path / "test.dict.json"
    result = dictionary_add(str(dict_file), [{"from": "aaa", "to": "bbb"}])
    assert result["status"] == "success"
    assert result["added"] == 1
    assert result["total_entries"] == 1


def test_dictionary_add_deduplication(tmp_path):
    dict_file = tmp_path / "test.dict.json"
    dictionary_add(str(dict_file), [{"from": "aaa", "to": "bbb"}])
    result = dictionary_add(str(dict_file), [{"from": "aaa", "to": "bbb"}])
    assert result["added"] == 0
    assert result["skipped"] == 1


def test_dictionary_add_invalid_entry(tmp_path):
    dict_file = tmp_path / "test.dict.json"
    result = dictionary_add(str(dict_file), [{"from": "", "to": "bbb"}])
    assert result["skipped"] == 1
    assert result["added"] == 0
