"""Vocabulary management for Whisper transcription."""

import os
from pathlib import Path

_DEFAULT_VOCAB_DIR = Path(os.environ.get(
    "WHISPER_VOCAB_DIR",
    str(Path(__file__).resolve().parent.parent / "vocabularies")
))


def get_vocab_dirs(extra_dirs: list[Path] | None = None) -> list[Path]:
    """Return list of vocabulary directories to search."""
    dirs = [_DEFAULT_VOCAB_DIR]
    if extra_dirs:
        for d in extra_dirs:
            if d not in dirs:
                dirs.append(d)
    return dirs


def load_vocabulary(vocab_path: str) -> str:
    """Load vocabulary file and return as comma-separated prompt string."""
    p = Path(vocab_path).expanduser()
    if not p.exists():
        return ""
    terms = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(line)
    return ", ".join(terms[:200])


def vocabulary_list(extra_dirs: list[Path] | None = None) -> dict:
    """List available vocabulary files for Whisper transcription."""
    try:
        vocabs = []
        for vdir in get_vocab_dirs(extra_dirs):
            if vdir.exists():
                for f in sorted(vdir.glob("*.txt")):
                    lines = f.read_text(encoding="utf-8").splitlines()
                    terms = [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
                    vocabs.append({
                        "name": f.name,
                        "path": str(f),
                        "term_count": len(terms),
                        "source": str(vdir),
                    })

        return {
            "status": "success",
            "vocabularies": vocabs,
            "vocab_dirs": [str(d) for d in get_vocab_dirs(extra_dirs)],
            "usage": "Pass vocabulary path to whisper_transcribe's vocabulary_path parameter",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def vocabulary_add(vocab_file: str, terms: list[str]) -> dict:
    """Add terms to a vocabulary file. Duplicates are automatically skipped."""
    try:
        p = Path(vocab_file).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)

        existing = set()
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    existing.add(line)

        added = []
        skipped = []
        for term in terms:
            term = term.strip()
            if term and term not in existing:
                existing.add(term)
                added.append(term)
            else:
                skipped.append(term)

        if added:
            with open(p, "a", encoding="utf-8") as f:
                f.write("\n".join(added) + "\n")

        return {
            "status": "success",
            "added": len(added),
            "skipped": len(skipped),
            "added_terms": added,
            "total_terms": len(existing),
            "file": str(p),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
