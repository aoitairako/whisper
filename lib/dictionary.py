"""Post-processing dictionary management for Whisper transcription."""

import json
from pathlib import Path

from .vocabulary import get_vocab_dirs


def load_dictionaries(extra_dirs: list[Path] | None = None) -> list[dict]:
    """Load all *.dict.json files from vocab dirs, merge and sort by 'from' length (longest first)."""
    replacements = []
    for vdir in get_vocab_dirs(extra_dirs):
        if not vdir.exists():
            continue
        for f in sorted(vdir.glob("*.dict.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                for entry in data.get("replacements", []):
                    if "from" in entry and "to" in entry:
                        replacements.append(entry)
            except (json.JSONDecodeError, OSError):
                continue
    replacements.sort(key=lambda e: len(e["from"]), reverse=True)
    return replacements


def apply_dictionary(text: str, replacements: list[dict]) -> str:
    """Apply dictionary replacements to a text string."""
    for entry in replacements:
        text = text.replace(entry["from"], entry["to"])
    return text


def apply_dictionary_to_result(result, replacements: list[dict]):
    """Apply dictionary replacements to result.text and each segment.text."""
    if not replacements:
        return result
    result.text = apply_dictionary(result.text, replacements)
    for seg in getattr(result, "segments", []):
        if isinstance(seg, dict):
            seg["text"] = apply_dictionary(seg.get("text", ""), replacements)
        else:
            seg.text = apply_dictionary(getattr(seg, "text", ""), replacements)
    return result


def dictionary_list(extra_dirs: list[Path] | None = None) -> dict:
    """List post-processing replacement dictionaries (*.dict.json)."""
    try:
        dicts = []
        for vdir in get_vocab_dirs(extra_dirs):
            if not vdir.exists():
                continue
            for f in sorted(vdir.glob("*.dict.json")):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    dicts.append({
                        "name": data.get("name", f.stem),
                        "description": data.get("description", ""),
                        "entries": len(data.get("replacements", [])),
                        "path": str(f),
                    })
                except (json.JSONDecodeError, OSError):
                    dicts.append({"name": f.stem, "path": str(f), "error": "invalid JSON"})

        return {
            "status": "success",
            "dictionaries": dicts,
            "total_entries": sum(d.get("entries", 0) for d in dicts),
            "vocab_dirs": [str(d) for d in get_vocab_dirs(extra_dirs)],
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def dictionary_add(dict_file: str, entries: list[dict]) -> dict:
    """Add replacement entries to a dictionary file. Duplicates are skipped."""
    try:
        p = Path(dict_file).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)

        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
        else:
            data = {"name": p.stem.replace(".dict", ""), "description": "", "replacements": []}

        existing_froms = {e["from"] for e in data.get("replacements", [])}

        added = []
        skipped = []
        for entry in entries:
            fr = entry.get("from", "").strip()
            to = entry.get("to", "").strip()
            if not fr or not to:
                skipped.append(entry)
                continue
            if fr in existing_froms:
                skipped.append(entry)
                continue
            data["replacements"].append({"from": fr, "to": to})
            existing_froms.add(fr)
            added.append(entry)

        p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        return {
            "status": "success",
            "added": len(added),
            "skipped": len(skipped),
            "total_entries": len(data["replacements"]),
            "file": str(p),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
