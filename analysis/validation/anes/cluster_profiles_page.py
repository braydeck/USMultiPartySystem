"""Render outputs/clustering/cluster_profiles.json (from describe_clusters.py) as a local review page.

Writes outputs/clustering/cluster_profiles.html. Clusters are listed left to right on party ID
(Democratic first); factor cells run blue (liberal end) to red (conservative end), clamped at ±1.5 SD.
"""
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "outputs" / "clustering" / "cluster_profiles.json"
DST = SRC.with_suffix(".html")

BLUE, RED, MID = (42, 120, 214), (227, 73, 72), (240, 239, 236)
BLUE_D, RED_D, MID_D = (57, 135, 229), (230, 103, 103), (56, 56, 53)


def mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def div_color(v, dark=False):
    t = max(-1.0, min(1.0, v / 1.5))
    lo, mid, hi = (BLUE_D, MID_D, RED_D) if dark else (BLUE, MID, RED)
    c = mix(mid, hi, t) if t >= 0 else mix(mid, lo, -t)
    return "#%02x%02x%02x" % c


def cell(v):
    ink = "#fff" if abs(v) > 0.9 else "var(--text-primary)"
    return (f'<td class="heat" style="--bg:{div_color(v)};--bg-d:{div_color(v, True)};color:{ink}" '
            f'title="{v:+.2f} SD">{v:+.1f}</td>')


def stack(parts):
    segs = "".join(f'<span class="seg {cls}" style="width:{p * 100:.1f}%" title="{html.escape(lab)} {p:.0%}"></span>'
                   for lab, cls, p in parts if p > 0)
    return f'<div class="stack">{segs}</div>'


def pct(x):
    return f"{x:.0%}"


def cluster_table(S, prefix, show_party):
    rows = sorted(S["clusters"], key=lambda c: c["pid7_mean"])
    fn = S["fnames"]
    head = "".join(f'<th class="fh" title="{html.escape(" · ".join(S["top_items"][f]))}">{html.escape(f)}</th>' for f in fn)
    party_h = "<th>Nearest CES party</th>" if show_party else ""
    body = []
    for c in rows:
        v = c["vote"]
        nv = v["Did not vote / missing"] + v["No post interview"]
        party = ""
        if show_party:
            alt = c["hungarian_party"]
            note = "" if alt == c["nearest_party"] else f' <span class="muted">({alt} by 1:1 match)</span>'
            party = f'<td class="party">{c["nearest_party"]}{note}</td>'
        body.append(
            f'<tr><td class="id">{prefix}{c["cluster"]}</td><td class="num">{pct(c["share"])}</td>'
            f'<td class="num muted">{c["n"]:,}</td>{party}'
            f'<td>{stack([("Democrat", "d", c["pid_dem"]), ("Independent", "i", c["pid_ind"]), ("Republican", "r", c["pid_rep"])])}'
            f'<div class="cap">{pct(c["pid_dem"])} D · {pct(c["pid_rep"])} R</div></td>'
            f'<td>{stack([("Harris", "d", v["Harris"]), ("Trump", "r", v["Trump"]), ("Other", "i", v["Other"]), ("Did not vote or no data", "nv", nv)])}'
            f'<div class="cap">{pct(v["Harris"])} Harris · {pct(v["Trump"])} Trump · {pct(nv)} no vote</div></td>'
            f'<td class="num">{c["ideo_mean"]:.1f}</td><td class="num">{pct(c["not_thought_any"])}</td>'
            + "".join(cell(c["factors"][f]) for f in fn) + "</tr>")
    return (f'<div class="scroll"><table><thead><tr><th>Cluster</th><th>Share</th><th>n</th>{party_h}<th>Party ID</th>'
            f'<th>2024 vote</th><th>Ideology (1–7)</th><th title="Share answering haven\'t thought much on at least one of six 7-point scales">Haven\'t thought much</th>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>')


def factor_key(S):
    items = "".join(f'<li><b>{html.escape(f)}</b> (r with conservative ideology {r:+.2f}): '
                    f'{html.escape("; ".join(S["top_items"][f]))}</li>' for f, r in zip(S["fnames"], S["r_ideo"]))
    return f'<details><summary>What each factor measures (top three loadings)</summary><ul class="key">{items}</ul></details>'


def item_table(S):
    rows = sorted(S["clusters"], key=lambda c: c["pid7_mean"])
    items = list(rows[0]["items"])
    head = "".join(f'<th>M{c["cluster"]}<br><span class="muted">{c["nearest_party"]}</span></th>' for c in rows)
    body = "".join(f'<tr><td class="lab">{html.escape(i)}</td>' + "".join(cell(c["items"][i]) for c in rows) + "</tr>"
                   for i in items)
    return (f'<details><summary>Matched clusters on each of the 18 items (SD from the ANES mean, high = the conservative answer)</summary>'
            f'<div class="scroll"><table class="items"><thead><tr><th>Item</th>{head}</tr></thead><tbody>{body}</tbody></table></div></details>')


def crosstab(D):
    ct = D["crosstab"]
    M = {c["cluster"]: c for c in D["matched"]["clusters"]}
    I = {c["cluster"]: c for c in D["independent"]["clusters"]}
    rows_order = sorted(ct["rows"], key=lambda r: M[r]["pid7_mean"])
    cols_order = sorted(ct["cols"], key=lambda c: I[c]["pid7_mean"])
    head = "".join(f'<th>I{c}</th>' for c in cols_order)
    body = []
    for r in rows_order:
        vals = ct["row_share"][ct["rows"].index(r)]
        tds = ""
        for c in cols_order:
            v = vals[ct["cols"].index(c)]
            a = min(1.0, v / 0.6)
            tds += (f'<td class="heat" style="--bg:rgba(42,120,214,{a:.2f});--bg-d:rgba(57,135,229,{a:.2f});'
                    f'color:{"#fff" if v > 0.35 else "var(--text-primary)"}" title="M{r} → I{c}: {v:.0%} of M{r}">'
                    f'{"" if v < 0.005 else f"{v:.0%}"}</td>')
        body.append(f'<tr><td class="id">M{r} <span class="muted">{M[r]["nearest_party"]}</span></td>{tds}</tr>')
    return (f'<div class="scroll"><table class="xt"><thead><tr><th>Matched ↓ / Independent →</th>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def main():
    D = json.loads(SRC.read_text())
    M, I = D["matched"], D["independent"]
    nM = sum(c["n"] for c in M["clusters"])
    nI = sum(c["n"] for c in I["clusters"])
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>ANES Cluster Profiles</title>
<style>
:root{{--surface:#fcfcfb;--text-primary:#0b0b0b;--text-secondary:#52514e;--rule:#e4e3df;--d:#2a78d6;--r:#e34948;--i:#a9a8a2;--nv:#dcdbd6;color-scheme:light}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--surface:#1a1a19;--text-primary:#f0efec;--text-secondary:#c3c2b7;--rule:#383835;--d:#3987e5;--r:#e66767;--i:#7a7974;--nv:#45443f;color-scheme:dark}}
:root:not([data-theme="light"]) .heat{{background:var(--bg-d)!important}}}}
:root[data-theme="dark"]{{--surface:#1a1a19;--text-primary:#f0efec;--text-secondary:#c3c2b7;--rule:#383835;--d:#3987e5;--r:#e66767;--i:#7a7974;--nv:#45443f;color-scheme:dark}}
:root[data-theme="dark"] .heat{{background:var(--bg-d)!important}}
body{{margin:0;background:var(--surface);color:var(--text-primary);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Inter",sans-serif}}
main{{max-width:1400px;margin:0 auto;padding:24px 16px 64px}}
h1{{font-size:22px;margin:0 0 6px}} h2{{font-size:17px;margin:36px 0 4px}}
p{{max-width:860px;color:var(--text-secondary);margin:4px 0 12px}}
.scroll{{overflow-x:auto}} table{{border-collapse:separate;border-spacing:2px;font-variant-numeric:tabular-nums}}
th{{font-size:12px;font-weight:600;color:var(--text-secondary);text-align:left;padding:4px 6px;vertical-align:bottom}}
th.fh{{width:64px;font-size:11px;cursor:help}}
td{{padding:5px 6px;vertical-align:middle}} td.num{{text-align:right}} td.id{{font-weight:600;white-space:nowrap}}
td.heat{{background:var(--bg);text-align:center;border-radius:4px;min-width:44px;font-size:12px}}
.muted{{color:var(--text-secondary);font-weight:400}} td.party{{white-space:nowrap}}
.stack{{display:flex;gap:2px;width:170px;height:10px}} .seg{{display:block;border-radius:2px}}
.seg.d{{background:var(--d)}} .seg.r{{background:var(--r)}} .seg.i{{background:var(--i)}} .seg.nv{{background:var(--nv)}}
.cap{{font-size:11px;color:var(--text-secondary);margin-top:3px;white-space:nowrap}}
details{{margin:10px 0}} summary{{cursor:pointer;color:var(--text-secondary);font-size:13px}}
ul.key{{font-size:12.5px;color:var(--text-secondary);max-width:1000px}} ul.key li{{margin:3px 0}}
table.items td.lab{{font-size:12px;max-width:320px}} .legend{{font-size:12px;color:var(--text-secondary);display:flex;gap:14px;flex-wrap:wrap;margin:6px 0}}
.sw{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px;vertical-align:-1px}}
</style></head><body><main>
<h1>ANES 2024 clusters, two ways</h1>
<p>Matched clusters run the production CES chain on the 18 items ANES shares with the CES typology (n = {nM:,}).
Independent clusters use ANES's own factors, refit on 4 items per factor (n = {nI:,}, respondents complete on those 40 items),
with the cluster count chosen on seed and resample stability ({len(I["clusters"])} clusters). Matched clusters use the DPGMM capped at 9; respondents in components holding under 1% of the weight are left unassigned ({D["unassigned"]["matched"]:,} matched, {D["unassigned"]["independent"]:,} independent). Rows are ordered from most Democratic to most Republican party ID.</p>
<div class="legend"><span><span class="sw" style="background:var(--d)"></span>Democrat / Harris</span>
<span><span class="sw" style="background:var(--i)"></span>Independent / other candidate</span>
<span><span class="sw" style="background:var(--r)"></span>Republican / Trump</span>
<span><span class="sw" style="background:var(--nv)"></span>Did not vote or no post-election data</span>
<span>Factor cells: SD from the ANES mean, blue = liberal end, red = conservative end. A factor with almost no ideological lean (|r| under 0.10) follows its top item's direction instead. Hover a factor name for its top items.</span></div>

<h2>Matched: 18 CES items</h2>
<p>"Nearest CES party" is the CES party whose centroid sits closest in the same factor space. On CES subsamples of this size that label names the right party for 69% of respondents.</p>
{cluster_table(M, "M", True)}
{factor_key(M)}
{item_table(M)}

<h2>Independent: ANES's own factors</h2>
<p>These clusters have no CES party label, because their factors are ANES's own. The {", ".join(I["residualized"])} factor is clustered net of {", ".join(I["anchor"])}, the factor most correlated with the others; the cells show scores before that adjustment.</p>
{cluster_table(I, "I", False)}
{factor_key(I)}

<h2>Where matched clusters land in the independent clustering</h2>
<p>Share of each matched cluster's respondents in each independent cluster (rows sum to 100%), n = {D["crosstab"]["n"]:,} respondents in both. Adjusted Rand index {D["ari"]:.2f}.</p>
{crosstab(D)}
</main></body></html>"""
    DST.write_text(page)
    print(DST)


if __name__ == "__main__":
    main()
