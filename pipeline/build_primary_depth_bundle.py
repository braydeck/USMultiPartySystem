#!/usr/bin/env python3
"""Bundle the truncated-ballot primary JSONs (depths 3/5/7/10 × 7 turnout stops) into a single
lazy-loaded asset: viz/public/data/primaryDepth.json = {depthKey: {family: {partKey: data}}}.

Reuses prepare_data's exact converters, capturing their output in-memory (monkeypatched write_json)
so no per-file artifacts are written to viz/src/data. 'full' ranking stays in the existing static
imports; this bundle covers only the truncated depths the ballot-depth toggle offers."""
import json
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "viz" / "scripts"))
import prepare_data as pd_mod  # noqa: E402
from prepare_data import (  # noqa: E402
    build_pure_multi_primary,
    build_pure_multi_primary_buckets,
    build_pure_multi_primary_state_shares,
    OUTPUTS,
)

_captured = {}
pd_mod.write_json = lambda data, name: _captured.__setitem__("last", data)

STOPS = [(0, ""), (5, "_l5"), (10, "_l10"), (15, "_l15"), (20, "_l20"), (25, "_l25"), (30, "_l30")]
DEPTHS = [3, 5, 7, 10]


def cap(fn, tree):
    fn(tree, "x")
    return _captured["last"]


bundle = {}
for depth in DEPTHS:
    fam = {"primary": {}, "buckets": {}, "stageShares": {}}
    for lam, suf in STOPS:
        pk = str(lam)
        tree = OUTPUTS / f"pure_multi_turnout{suf}_top{depth}"
        fam["primary"][pk] = cap(build_pure_multi_primary, tree)
        fam["buckets"][pk] = cap(build_pure_multi_primary_buckets, tree)
        fam["stageShares"][pk] = cap(build_pure_multi_primary_state_shares, tree)
    bundle[f"top{depth}"] = fam
    print(f"  top{depth}: 7 stops × 3 families")

out = BASE / "viz" / "public" / "data" / "primaryDepth.json"
out.write_text(json.dumps(bundle, separators=(",", ":")))
print(f"Wrote {out} ({out.stat().st_size / 1e6:.2f} MB)")
