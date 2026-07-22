#!/usr/bin/env python3
"""Bundle the House bill-simulator vote model across ballot depth × turnout into a single lazy asset:
viz/public/data/houseVoteModelDepth.json = {depthKey: {partKey: rows}}.

The House tab's Bill Simulator reads the Raw-Multi double/triple pass-probability columns, which are
functions of the STV seat counts — so they move with both the depth toggle and the turnout slider.
'full' ranking uses the base full-depth trees; the truncated depths use the _topN trees."""
import json
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "viz" / "scripts"))
import prepare_data as pd_mod  # noqa: E402
from prepare_data import build_house_vote_model_wfp, OUTPUTS  # noqa: E402

_captured = {}
pd_mod.write_json = lambda data, name: _captured.__setitem__("last", data)

STOPS = [(0, ""), (5, "_l5"), (10, "_l10"), (15, "_l15"), (20, "_l20"), (25, "_l25"), (30, "_l30")]
# depthKey -> tree suffix ('' = full-ranking base trees)
DEPTHS = {"top3": "_top3", "top5": "_top5", "top7": "_top7", "top10": "_top10", "full": ""}

bundle = {}
for dk, dsuf in DEPTHS.items():
    by_part = {}
    for lam, lsuf in STOPS:
        dbl = OUTPUTS / f"pure_multi_turnout{lsuf}{dsuf}"
        tri = OUTPUTS / f"pure_multi_triple_turnout{lsuf}{dsuf}"
        build_house_vote_model_wfp(dbl, "x", triple_src=tri)
        by_part[str(lam)] = _captured["last"]
    bundle[dk] = by_part
    print(f"  {dk}: 7 turnout stops (double + triple)")

out = BASE / "viz" / "public" / "data" / "houseVoteModelDepth.json"
out.write_text(json.dumps(bundle, separators=(",", ":")))
print(f"Wrote {out} ({out.stat().st_size / 1e6:.2f} MB)")
