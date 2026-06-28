#!/usr/bin/env python3
"""One-shot rename: factor-deviation axis 'ae' -> 'es' (F2 Electoral Skepticism). Run with --apply to write.

Renames variant codes (X_hi_ae -> X_hi_es, X_lo_ae -> X_lo_es) and the bare lowercase
axis token 'ae' used as a key/value. Word-boundary safe: the bare-token pattern treats
'_' as a boundary too, and never touches 'ae' embedded in other words (e.g. 'value', 'Michael').
Uppercase 'AE'/'Anti-Estab' display labels are handled separately by hand.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROOTS = ["viz/src", "pipeline", "data/outputs", "docs", "comms"]
EXCLUDE_PARTS = {".venv", ".git", "node_modules", "archive", "Archive"}
# Skip binaries and bundled/rendered HTML reports (minified JS uses 'ae' as a variable name).
SKIP_EXT = {".parquet", ".png", ".jpg", ".jpeg", ".pyc", ".ipynb", ".gz", ".zip", ".html"}
SELF = Path(__file__).name
SKIP_NAMES = {SELF, "rename_ref_to_pop.py"}  # don't rewrite historical one-shot rename scripts

# Precise, context-anchored patterns — never matches 'ae' embedded in a word or minified JS.
PATTERNS = [
    (re.compile(r"(?<![A-Za-z0-9])(hi|lo)_ae(?![A-Za-z0-9])"), lambda m: f"{m.group(1)}_es"),  # variant codes: SD_hi_ae, X_lo_ae
    (re.compile(r'("[A-Za-z]*[Aa]xis"\s*:\s*")ae(")'), lambda m: f"{m.group(1)}es{m.group(2)}"),  # JSON: "axis":"ae", "senatorAxis":"ae"
    (re.compile(r"(?<=,)ae(?=,)"), lambda m: "es"),                       # CSV axis column: ,ae,
]

APPLY = "--apply" in sys.argv


def eligible(p: Path) -> bool:
    if p.name in SKIP_NAMES or p.suffix.lower() in SKIP_EXT:
        return False
    return not any(part in EXCLUDE_PARTS for part in p.parts)


def main():
    total_files = 0
    total_repl = 0
    for root in ROOTS:
        base = ROOT / root
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or not eligible(p):
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, IsADirectoryError):
                continue
            new = text
            n = 0
            for rx, repl in PATTERNS:
                n += len(rx.findall(new))
                new = rx.sub(repl, new)
            if n == 0:
                continue
            total_files += 1
            total_repl += n
            print(f"{n:5d}  {p.relative_to(ROOT)}")
            if APPLY:
                p.write_text(new, encoding="utf-8")
    print(f"\n{'APPLIED' if APPLY else 'DRY-RUN'}: {total_repl} replacements across {total_files} files")


if __name__ == "__main__":
    main()
