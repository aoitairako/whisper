"""Tests for lib/formats.py — no network or subprocess calls."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.formats import seconds_to_srt_time, seconds_to_vtt_time, seg_val, to_srt, to_vtt


def test_srt_time_zero():
    assert seconds_to_srt_time(0.0) == "00:00:00,000"


def test_srt_time_one_hour():
    assert seconds_to_srt_time(3600.0) == "01:00:00,000"


def test_srt_time_with_ms():
    assert seconds_to_srt_time(1.5) == "00:00:01,500"


def test_vtt_time_zero():
    assert seconds_to_vtt_time(0.0) == "00:00:00.000"


def test_vtt_time_separator():
    srt = seconds_to_srt_time(1.5)
    vtt = seconds_to_vtt_time(1.5)
    assert "," in srt
    assert "." in vtt


def test_seg_val_dict():
    seg = {"start": 1.0, "end": 2.0, "text": "hello"}
    assert seg_val(seg, "start") == 1.0
    assert seg_val(seg, "text") == "hello"
    assert seg_val(seg, "missing", "default") == "default"


def test_seg_val_object():
    class FakeSeg:
        start = 5.0
        text = "world"

    seg = FakeSeg()
    assert seg_val(seg, "start") == 5.0
    assert seg_val(seg, "missing", "x") == "x"


def test_to_srt_empty():
    result = to_srt([])
    assert result == ""


def test_to_srt_single_segment():
    segs = [{"start": 0.0, "end": 1.5, "text": "Hello world"}]
    result = to_srt(segs)
    assert "1\n" in result
    assert "00:00:00,000 --> 00:00:01,500" in result
    assert "Hello world" in result


def test_to_vtt_header():
    result = to_vtt([])
    assert result.startswith("WEBVTT")


def test_to_vtt_single_segment():
    segs = [{"start": 0.0, "end": 2.0, "text": "Test"}]
    result = to_vtt(segs)
    assert "00:00:00.000 --> 00:00:02.000" in result
    assert "Test" in result
