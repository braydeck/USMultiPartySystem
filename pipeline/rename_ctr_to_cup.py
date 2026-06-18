#!/usr/bin/env python3
"""One-shot rename: party 'Center'/'CTR' -> 'Civic Union Party'/'CUP'. Run with --apply.

'Center' is a heavily overloaded word, so the NAME rule is guarded:
  - 'Center Party'/'Center party'  -> 'Civic Union Party'   (avoids 'Civic Union Party Party')
  - bare 'Center'                  -> 'Civic Union Party'    EXCEPT 'Center-left/-right' and 'Center cell'
The CODE rule (CTR, CTR_hi_pc, CTR_1) is word-boundary safe and won't touch 'CTRL'.
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

CODE = re.compile(r"(?<![A-Za-z0-9])CTR(?![A-Za-z0-9])")          # CTR, CTR_hi_pc, CTR_1; not CTRL
NAME_PARTY = re.compile(r"\bCenter [Pp]arty\b")                    # 'Center Party' / 'Center party'
NAME_BARE = re.compile(r"\bCenter\b(?!-(?:[Ll]eft|[Rr]ight))(?! cell)(?! [Pp]arty)")

APPLY = "--apply" in sys.argv


def eligible(p: Path) -> bool:
    if p.name == SELF or p.suffix.lower() in SKIP_EXT:
        return False
    if any(part in EXCLUDE_PARTS for part in p.parts):
        return False
    s = str(p)
    return not any(sub in s for sub in EXCLUDE_PATH_SUBSTR)


def transform(text: str) -> tuple[str, int]:
    n = len(CODE.findall(text)) + len(NAME_PARTY.findall(text)) + len(NAME_BARE.findall(text))
    text = CODE.sub("CUP", text)
    text = NAME_PARTY.sub("Civic Union Party", text)
    text = NAME_BARE.sub("Civic Union Party", text)
    return text, n


def main():
    total_files = total_repl = 0
    skipped_ctx = set()
    for root in ROOTS:
        for p in (ROOT / root).rglob("*"):
            if not p.is_file() or not eligible(p):
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, IsADirectoryError):
                continue
            # record any 'Center' we are deliberately NOT renaming (for transparency)
            for m in re.finditer(r"\bCenter\b(?:-(?:[Ll]eft|[Rr]ight)| cell)", text):
                line = text[text.rfind("\n", 0, m.start()) + 1: text.find("\n", m.end())]
                skipped_ctx.add(f"{p.relative_to(ROOT)} :: {line.strip()[:90]}")
            new, n = transform(text)
            if n == 0:
                continue
            total_files += 1
            total_repl += n
            print(f"{n:5d}  {p.relative_to(ROOT)}")
            if APPLY:
                p.write_text(new, encoding="utf-8")
    print(f"\n{'APPLIED' if APPLY else 'DRY-RUN'}: {total_repl} replacements across {total_files} files")
    if skipped_ctx:
        print("\n--- intentionally PRESERVED (generic 'Center'), not renamed ---")
        for s in sorted(skipped_ctx):
            print("  |", s)


if __name__ == "__main__":
    main()
