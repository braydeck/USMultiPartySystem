"""Signature view of the nine parties (with production's nine for reference): the app's Parties-tab vocabulary on the
new typology, as a temporary local page for writing the party descriptions.

Marks (same rules and defaults as viz/src/lib/signature.ts and components/shared/IntensityBar.itemSignature):
  C cohesive   the party's share is >= consPct (70) or <= 100 - consPct, i.e. its members mostly agree
  D deviant    |party share - everyone| >= deviantPp (25 points)
  M mainstream |party share - everyone| <= mainstreamPp (10 points)
  ◆ diverge    the selected parties' shares span >= minGap (15 points)
All four thresholds are sliders on the page; everything is recomputed in the browser.

Data: outputs/compare_typologies_k9/{policy,factors,demographics,letters}.csv (compare_typologies.py v2 9; CES 2024,
weighted; "Everyone" = all respondents in either sample) and the draft descriptions in
analysis/efa/rebuild_nine_parties/party_descriptions.md (read-only here; edit the .md and rerun).
Writes outputs/signature_k9/index.html.
"""
import json
import re
from pathlib import Path

import pandas as pd

import compare_typologies as ct
import reestimate_loadings as rl

SRC = rl.OUT / "compare_typologies_k9"
OUT = rl.OUT / "signature_k9"
DESC = rl.ROOT / "analysis/efa/rebuild_nine_parties/party_descriptions.md"
# viz/src/constants/parties.ts PARTY_COLORS; OAO takes the retired DAL's azure for this page only
COLORS = {"PRG": "#15803d", "DSA": "#22c55e", "DAL": "#0284c7", "LBR": "#38bdf8", "STY": "#8a70b8", "CUP": "#825a27",
          "CON": "#e68c2c", "POP": "#d34812", "NAT": "#a01d2a", "OAO": "#0284c7"}
NEW_ORDER = ["DSA", "PRG", "LBR", "OAO", "CUP", "STY", "POP", "CON", "NAT"]   # left to right on economic right
PROD_ORDER = ["PRG", "DSA", "DAL", "LBR", "STY", "CUP", "CON", "POP", "NAT"]   # production F5_ORDER


def descriptions():
    """{code: {letter, name, tagline, paragraph}} from the .md; a field's text runs until the next blank line."""
    out, cur, field = {}, None, None
    for line in DESC.read_text().splitlines():
        m = re.match(r"## (\w+) \(cluster (\w), ([0-9.]+)%\)", line)
        f = re.match(r"\*\*(Name|Tagline|Paragraph):\*\* (.*)", line)
        if m:
            cur, field = m.group(1), None
            out[cur] = {"letter": m.group(2)}
        elif cur and f:
            field = f.group(1).lower()
            out[cur][field] = f.group(2).strip()
        elif cur and field and line.strip() and not line.startswith((">", "#", "---")):
            out[cur][field] += " " + line.strip()
        else:
            field = None if not line.strip() else field
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pol = pd.read_csv(SRC / "policy.csv")
    fac = pd.read_csv(SRC / "factors.csv", index_col=0)
    dem = pd.read_csv(SRC / "demographics.csv")
    let = pd.read_csv(SRC / "letters.csv")
    new_cols = {lab: lab.split(" (")[0] for lab in let.label}          # "CON (A)" -> "CON"
    shares = {}
    html_src = (SRC / "index.html").read_text()
    m = re.search(r"const DATA = (\{.*?\});\n", html_src, re.S)
    for g in json.loads(m.group(1))["groups"]:
        shares[("new:" + new_cols[g["id"]]) if g["key"] == "new" else ("prod:" + g["id"]) if g["key"] == "prod" else "us"] = g["share"]

    def cols(df):
        rename = {**{c: "new:" + new_cols[c] for c in new_cols}, **{p: "prod:" + p for p in PROD_ORDER}, "Everyone": "us"}
        return df.rename(columns=rename)

    pol, fac, dem = cols(pol), cols(fac), cols(dem)
    keys = [f"new:{p}" for p in NEW_ORDER] + [f"prod:{p}" for p in PROD_ORDER] + ["us"]
    rec = lambda r: {k: (None if pd.isna(r[k]) else round(float(r[k]), 1)) for k in keys}
    data = {
        "parties": [{"key": f"new:{p}", "code": p, "set": "new", "color": COLORS[p], "share": shares.get(f"new:{p}")} for p in NEW_ORDER]
                   + [{"key": f"prod:{p}", "code": p, "set": "prod", "color": COLORS[p], "share": shares.get(f"prod:{p}")} for p in PROD_ORDER],
        "factors": [{"label": i, **{k: round(float(fac.loc[i, k]), 2) for k in keys}} for i in fac.index if i.startswith("N: ")]
                   + [{"label": i, **{k: round(float(fac.loc[i, k]), 2) for k in keys}} for i in fac.index if i.startswith("P: ")],
        "policy": [{"topic": r.topic, "item": r["item"], "label": r["label"], "input": bool(r["new30"]), **rec(r)} for _, r in pol.iterrows()],
        "demo": [{"section": r.section, "label": r["label"], "median": r["label"] == "Median age", **rec(r)} for _, r in dem.iterrows()],
        "desc": descriptions(),
    }
    html = (Path(__file__).with_name("signature_app_template.html").read_text()
            .replace("/*TOKENS*/", ct.TOKENS.read_text()).replace("/*DATA*/", json.dumps(data, allow_nan=False)))
    (OUT / "index.html").write_text(html)
    print(f"{len(data['policy'])} policy items, {len(data['demo'])} demographic rows, descriptions for {sorted(data['desc'])}")
    print(f"wrote {OUT / 'index.html'}")


if __name__ == "__main__":
    main()
