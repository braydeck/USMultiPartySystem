#!/usr/bin/env python3
"""One-shot rename: party 'Reform'/'REF' -> 'Populist'/'POP'. Run with --apply to write.

Word-boundary safe: only the standalone uppercase code REF (incl. REF_lo_ae, REF_1) and the
capitalized name 'Reform'. Never touches lowercase 'reform', 'useRef', 'href', etc.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROOTS = ["viz/src", "docs", "comms", "pipeline", "data/outputs"]
EXCLUDE_PARTS = {".venv", ".git", "node_modules", "archive", "Archive"}
EXCLUDE_PATH_SUBSTR = ["results/post_recs"]
SKIP_EXT = {".parquet", ".png", ".jpg", ".jpeg", ".pyc", ".ipynb", ".gz", ".zip"}
SELF = Path(__file__).name

CODE = re.compile(r"(?<![A-Za-z0-9])REF(?![A-Za-z0-9])")  # REF, REF_lo_ae, REF_1, pct_REF; not base64/3REF7
NAME = re.compile(r"\bReform\b(?! policing)")             # Reform (party); NOT 'Reform policing' (a verb in AboutTab)

APPLY = "--apply" in sys.argv


def eligible(p: Path) -> bool:
    if p.name == SELF or p.suffix.lower() in SKIP_EXT:
        return False
    if any(part in EXCLUDE_PARTS for part in p.parts):
        return False
    s = str(p)
    return not any(sub in s for sub in EXCLUDE_PATH_SUBSTR)


def main():
    total_files = 0
    total_repl = 0
    name_snippets = set()
    for root in ROOTS:
        for p in (ROOT / root).rglob("*"):
            if not p.is_file() or not eligible(p):
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, IsADirectoryError):
                continue
            n_code = len(CODE.findall(text))
            n_name = len(NAME.findall(text))
            if n_code + n_name == 0:
                continue
            # collect the line context of every 'Reform' match for vetting
            for m in NAME.finditer(text):
                line = text[text.rfind("\n", 0, m.start()) + 1: text.find("\n", m.end())]
                name_snippets.add(line.strip()[:140])
            total_files += 1
            total_repl += n_code + n_name
            print(f"{n_code:4d} REF  {n_name:4d} Reform   {p.relative_to(ROOT)}")
            if APPLY:
                p.write_text(NAME.sub("Populist", CODE.sub("POP", text)), encoding="utf-8")
    print(f"\n{'APPLIED' if APPLY else 'DRY-RUN'}: {total_repl} replacements across {total_files} files")
    if not APPLY:
        print(f"\n--- every distinct line matching \\bReform\\b ({len(name_snippets)}) — vet for non-party use ---")
        for s in sorted(name_snippets):
            print("  |", s)


if __name__ == "__main__":
    main()
