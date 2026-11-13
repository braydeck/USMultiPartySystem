#!/usr/bin/env python3
"""One-shot party rename across the live code and data. Dry run by default; --apply writes.

    python3 pipeline/rename_party.py POP LP Populist Libertarian            # dry run
    python3 pipeline/rename_party.py POP LP Populist Libertarian --apply

Used for Reform/REF -> Populist/POP (b7b5637d) and Populist/POP -> Libertarian/LP.

Word-boundary safe: only the standalone uppercase code (POP, POP_1, pct_POP, CON-POP-NAT; never
POPULATION or 3POP7) and the capitalized name with an optional plural s. The name is left alone
where it names an old factor or a direction rather than the party. Also renames files and
folders whose name holds the code, and rewrites the gzip-encoded dissolve store in place
(folders like CON-POP-NAT, then every payload inside).

Historical records (analysis/efa/exploration, analysis/validation, archive folders) are not
touched: they describe earlier typologies under the names those typologies used.
"""
import gzip
import re
import sys
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROOTS = ["viz/src", "viz/public", "viz/scripts", "viz/functions", "docs", "comms", "pipeline",
         "data/outputs", "data/processed", "analysis/coalitions", "analysis/bootstrap"]
ROOT_FILES = ["CLAUDE.md", "README.md", "PARTY_PROFILES.md"]
STORE = ROOT / "data/dissolve_store"
EXCLUDE_PARTS = {".venv", ".git", "node_modules", "archive", "Archive", "dist", "dissolve_store",
                 "bootstrap_cache"}
SKIP_EXT = {".parquet", ".png", ".jpg", ".jpeg", ".pyc", ".ipynb", ".gz", ".zip", ".pkl", ".npz", ".npy"}
SELF = Path(__file__).name

args = [a for a in sys.argv[1:] if not a.startswith("--")]
if len(args) != 4:
    sys.exit(__doc__)
OLD, NEW, OLD_NAME, NEW_NAME = args
APPLY = "--apply" in sys.argv
CODE = re.compile(rf"(?<![A-Za-z0-9]){re.escape(OLD)}(?![A-Za-z0-9])")
# Not a party where it names an old factor ("Populist Conservatism", "F5 Populist") or a direction
# ("Populist right", "Populist-immigration center").
NAME = re.compile(rf"(?<!F5 )\b{re.escape(OLD_NAME)}(s?)\b(?!\s+Conservatism|[- ]right|-immigration)")


def swap(text: str) -> str:
    return NAME.sub(lambda m: NEW_NAME + m.group(1), CODE.sub(NEW, text))


def eligible(p: Path) -> bool:
    if p.name == SELF or p.suffix.lower() in SKIP_EXT:
        return False
    return not any(part in EXCLUDE_PARTS for part in p.relative_to(ROOT).parts)


def text_files():
    for f in ROOT_FILES:
        yield ROOT / f
    for root in ROOTS:
        for p in sorted((ROOT / root).rglob("*")):
            if p.is_file() and eligible(p):
                yield p


def rename_paths(base: Path, apply: bool) -> int:
    """Rename files and folders under `base` whose own name holds the code, deepest first."""
    hits = sorted((p for p in base.rglob("*") if CODE.search(p.name)
                   and not any(part in EXCLUDE_PARTS for part in p.relative_to(ROOT).parts[:-1])),
                  key=lambda p: len(p.parts), reverse=True)
    for p in hits:
        target = p.with_name(CODE.sub(NEW, p.name))
        print(f"  rename {p.relative_to(ROOT)} -> {target.name}")
        if apply:
            if target.exists():
                sys.exit(f"refusing to overwrite {target.relative_to(ROOT)}")
            p.rename(target)
    return len(hits)


def store_file(p: Path):
    raw = p.read_bytes()
    gz = raw[:2] == b"\x1f\x8b"
    text = (gzip.decompress(raw) if gz else raw).decode("utf-8")
    n = len(CODE.findall(text)) + len(NAME.findall(text))
    if n and APPLY:
        out = swap(text).encode("utf-8")
        p.write_bytes(gzip.compress(out, compresslevel=9, mtime=0) if gz else out)
    return n


def main():
    files = repl = 0
    name_lines = set()
    for p in text_files():
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
            continue
        n_code, n_name = len(CODE.findall(text)), len(NAME.findall(text))
        if n_code + n_name == 0:
            continue
        for m in NAME.finditer(text):
            line = text[text.rfind("\n", 0, m.start()) + 1: text.find("\n", m.end())]
            name_lines.add(line.strip()[:140])
        files += 1
        repl += n_code + n_name
        print(f"{n_code:5d} {OLD}  {n_name:4d} {OLD_NAME}   {p.relative_to(ROOT)}")
        if APPLY:
            p.write_text(swap(text), encoding="utf-8")

    print("\npaths:")
    moved = sum(rename_paths(ROOT / r, APPLY) for r in ROOTS if r != "pipeline")

    store_hits = 0
    if STORE.exists():
        dirs = [d for d in STORE.iterdir() if d.is_dir() and CODE.search(d.name)]
        print(f"\ndissolve store: {len(dirs)} combination folders to rename")
        if APPLY:
            for d in dirs:
                target = d.with_name(CODE.sub(NEW, d.name))
                if target.exists():
                    sys.exit(f"refusing to overwrite {target.relative_to(ROOT)}")
                d.rename(target)
        payloads = [p for p in STORE.rglob("*.json") if "_work" not in p.parts]
        with Pool(11) as pool:
            counts = pool.map(store_file, payloads, chunksize=64)
        store_hits = sum(counts)
        print(f"dissolve store: {store_hits} replacements across {sum(1 for c in counts if c)} of {len(payloads)} files")

    print(f"\n{'APPLIED' if APPLY else 'DRY RUN'}: {repl} replacements across {files} files, "
          f"{moved} paths renamed, {store_hits} in the dissolve store")
    if not APPLY:
        print(f"\nevery distinct line matching the name ({len(name_lines)}); vet for non-party use:")
        for s in sorted(name_lines):
            print("  |", s)


if __name__ == "__main__":
    main()
