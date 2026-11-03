"""Render the four stable ANES segments as portraits: outputs/stage_c/segment_portraits.html.

Inputs: outputs/stage_c/segment_descriptors.csv (describe_segments.py) and
outputs/clustering/cluster_profiles.json (describe_clusters.py) for vote and party ID. Every number in the
prose is read from those files. Segment names are working labels defined on the page.
"""
import html
import json

import pandas as pd

import numpy as np

import matched_efa as me
import recode_matched as rm

SRC = me.OUT / "stage_c"
D = pd.read_csv(SRC / "segment_descriptors.csv")
P = {c["cluster"]: c for c in json.loads((me.OUT / "clustering" / "cluster_profiles.json").read_text())["independent"]["clusters"]}
ORDER = [3, 2, 1, 0]


def val(k, name):
    r = D[(D.segment == k) & (D.descriptor == name)].iloc[0]
    return r.segment_value, r.overall_value, r.signal, r.binary


def pct(k, name):
    return f"{val(k, name)[0]:.0%}"


def num(k, name, nd=0):
    return f"{val(k, name)[0]:.{nd}f}"


def allv(name, nd=None):
    v = D[D.descriptor == name].overall_value.iloc[0]
    return f"{v:.0%}" if nd is None else f"{v:.{nd}f}"


def therm(nm):
    return f"Warmth toward {nm} (0-100)"



# Weighted means of a few clustering items, to state the factor positions in the items' own units
ITEMS = {"V241325": (1, 5), "V241403x": (1, 7), "V241400x": (1, 7), "V241239": (1, 7), "V241579": (1, 5)}
_lab = pd.read_csv(SRC / "independent_clusters.csv")
_raw = pd.read_csv(rm.ANES_CSV, usecols=["V240001", rm.WEIGHT] + list(ITEMS), low_memory=False).apply(pd.to_numeric, errors="coerce")
_raw = _lab[["caseid", "cluster"]].merge(_raw.rename(columns={"V240001": "caseid"}), on="caseid")


def item(k, var, nd=1):
    lo, hi = ITEMS[var]
    x = _raw[var].where(_raw[var].between(lo, hi))
    sel = x.notna() & ((_raw.cluster == k) if k is not None else True)
    return f"{np.average(x[sel], weights=_raw[rm.WEIGHT][sel]):.{nd}f}"


# Plain-language reading of each factor's high end (oriented so high = the end that goes with
# conservative self-placement; directions checked against raw items)
STANCE = {"Immigration and diversity": ("more restrictive on immigration", "more open to immigration"),
          "Democratic norms": ("rates checks and balances, accountability and a free press as less important", "rates checks and balances, accountability and a free press as more important"),
          "Foreign threats": ("sees Russia, Iran and China as bigger threats", "sees Russia, Iran and China as smaller threats"),
          "Religion and social traditionalism": ("more religious and socially traditional", "less religious and more socially liberal"),
          "Rural resentment": ("says rural people get too little influence, help and respect", "says rural people get their due or more"),
          "Government role in the economy": ("wants a smaller government role in the economy", "wants a larger government role in the economy"),
          "Gun policy": ("opposes gun restrictions", "supports gun restrictions"),
          "Ukraine and Israel aid": ("opposes aid to Ukraine and Israel; would rather the US stayed home", "favors aid to Ukraine and Israel"),
          "Trust in institutions (CSES)": ("trusts Congress, the government and the parties less", "trusts Congress, the government and the parties more"),
          "Leave decisions to experts or business (CSES)": ("favors leaving decisions to business leaders or experts and a strong leader", "opposes leaving decisions to business leaders, experts or a strong leader")}
_fac = pd.read_csv(SRC / "factors.csv")
_F = _lab[[f"F_{f}" for f in _fac.factor]].values
assert (_raw.caseid.values == _lab.caseid.values).all()
_w = _raw[rm.WEIGHT].values
_mu = np.average(_F, axis=0, weights=_w)
_F = (_F - _mu) / np.sqrt(np.average((_F - _mu) ** 2, axis=0, weights=_w))


def stances(k, n=4):
    m = np.average(_F[_lab.cluster.values == k], axis=0, weights=_w[_lab.cluster.values == k])
    out = []
    for j in np.argsort(-np.abs(m)):
        f = _fac.factor[j]
        if f in STANCE and _fac.clusters[j] and len(out) < n:
            out.append(f"{STANCE[f][0] if m[j] > 0 else STANCE[f][1]} <span class=muted>({m[j]:+.1f} SD)</span>")
    return out


SEGMENTS = {
    3: ("Secular progressives",
        "Harris voters for whom religion plays little part: the most educated, least rural and most hopeful of the four.",
        lambda k: f"""Religion is very or extremely important to {pct(k, "Religion very or extremely important")} of this segment, against {allv("Religion very or extremely important")} of the sample, and {pct(k, "Atheist, agnostic or nothing in particular")} are atheist, agnostic or nothing in particular. {pct(k, "Bachelor's degree or more")} hold a bachelor's degree, {pct(k, "Gay, lesbian, bisexual or other")} identify as gay, lesbian, bisexual or something else, and {pct(k, "Voted for president in 2024")} voted. They rate Donald Trump at {num(k, therm("Donald Trump"))} out of 100 and Planned Parenthood at {num(k, therm("Planned Parenthood"))}. US democracy ({pct(k, "Rates US democracy extremely or very important")}), climate change ({pct(k, "Rates climate change extremely or very important")}) and abortion ({pct(k, "Rates abortion extremely or very important")}) top their issue list; illegal immigration is rated very important by {pct(k, "Rates illegal immigration extremely or very important")}, against {allv("Rates illegal immigration extremely or very important")} overall. They want more government services ({item(k, "V241239")} on a 1 to 7 scale, against {item(None, "V241239")} overall) and favor weapons for Ukraine ({item(k, "V241400x")} on 1 to 7, 1 = favor a great deal, against {item(None, "V241400x")}). Of the four, they are the most opposed to leaving political decisions to business leaders, experts or a strong leader."""),
    2: ("Center-left moderates",
        "Harris-leaning voters left of the sample on every clustering factor but foreign threats, and the least angry and afraid about the country of the four.",
        lambda k: f"""{P[k]['vote']['Harris']:.0%} voted for Harris, {P[k]['vote']['Trump']:.0%} for Trump and {P[k]['vote']['Did not vote / missing']:.0%} did not vote or have no vote recorded. {P[k]['pid_dem']:.0%} identify as Democrats and {P[k]['pid_rep']:.0%} as Republicans, and they place themselves at {P[k]['ideo_mean']:.1f} on the 1 to 7 ideology scale. They support gun restrictions about as strongly as the secular progressives and sit milder than the progressives on immigration, religion, the economy and democratic norms. {pct(k, "White, non-Hispanic")} are white, {pct(k, "Black, non-Hispanic")} Black and {pct(k, "Hispanic")} Hispanic, {pct(k, "Women")} are women, and religion is very or extremely important to {pct(k, "Religion very or extremely important")}. {pct(k, "Very or extremely angry")} feel very or extremely angry about the country and {pct(k, "Very or extremely afraid")} very or extremely afraid. {pct(k, "Watches network evening news (ABC, CBS or NBC) regularly")} watch the network evening news, the most of the four, and climate change is very important to {pct(k, "Rates climate change extremely or very important")}, against {allv("Rates climate change extremely or very important")} overall. They favor weapons for Ukraine ({item(k, "V241400x")} on 1 to 7, 1 = favor a great deal, against {item(None, "V241400x")}). They rate Kamala Harris at {num(k, therm("Kamala Harris"))} and Donald Trump at {num(k, therm("Donald Trump"))}."""),
    1: ("Young, disaffected working class",
        "The youngest, poorest and least engaged segment: wants a larger government role in the economy, sits right of the sample on guns, rates democratic norms lowest and opposes weapons for Ukraine most.",
        lambda k: f"""{P[k]['vote']['Did not vote / missing'] + P[k]['vote']['No post interview']:.0%} did not vote or have no vote recorded, {P[k]['vote']['Trump']:.0%} voted for Trump and {P[k]['vote']['Harris']:.0%} for Harris. {pct(k, "Age under 35")} are under 35, {pct(k, "No education past high school")} have no education past high school, {pct(k, "Household income under $30k")} have household incomes under $30,000 and {pct(k, "Borrowed money to pay bills this year")} borrowed money to pay bills this year. {pct(k, "White, non-Hispanic")} are white, {pct(k, "Black, non-Hispanic")} Black, {pct(k, "Hispanic")} Hispanic and {pct(k, "Asian American or Pacific Islander")} Asian American, and {pct(k, "Children under 18 at home")} have children under 18 at home. They rate checks and balances at {item(k, "V241325")} on a 1 to 5 importance scale, against {item(None, "V241325")} overall. They oppose weapons for Ukraine ({item(k, "V241400x")} on 1 to 7, 7 = oppose a great deal, against {item(None, "V241400x")}) and want more government services ({item(k, "V241239")} against {item(None, "V241239")}). Asked whether violence to pursue political goals is justified, they average {item(k, "V241579", 2)} on a 1 to 5 scale (1 = not at all), against {item(None, "V241579", 2)} overall. {pct(k, "Very or extremely worried about finances")} are very or extremely worried about their finances, the most of the four."""),
    0: ("Religious conservatives",
        "Older, rural, devout Trump voters, the angriest and most afraid about the country of the four.",
        lambda k: f"""Religion is very or extremely important to {pct(k, "Religion very or extremely important")} and {pct(k, "Born-again Christian")} are born-again Christians. {pct(k, "Thinks of self as a small-town or rural person")} think of themselves as small-town or rural people, {pct(k, "Married")} are married, {pct(k, "Age 65 or older")} are 65 or older and {pct(k, "Women")} are women. {pct(k, "Very or extremely angry")} feel very or extremely angry about the country and {pct(k, "Very or extremely afraid")} very or extremely afraid. They rate the police at {num(k, therm("police"))}, rural Americans at {num(k, therm("rural Americans"))}, MAGA at {num(k, therm("MAGA"))} and Planned Parenthood at {num(k, therm("Planned Parenthood"))}, and {pct(k, "Watches Fox News shows (Hannity, The Five, Ingraham, Gutfeld!, Watters, Baier, Outnumbered) regularly")} watch Fox News shows regularly. Cost of living ({pct(k, "Rates cost of living extremely or very important")}), crime ({pct(k, "Rates crime extremely or very important")}), schools ({pct(k, "Rates what is taught in public schools extremely or very important")}) and illegal immigration ({pct(k, "Rates illegal immigration extremely or very important")}) top their list; climate change is very important to {pct(k, "Rates climate change extremely or very important")}. They favor military aid to Israel ({item(k, "V241403x")} on 1 to 7, 1 = favor a great deal, against {item(None, "V241403x")})."""),
}

GLANCE = ["Women", "Age under 35", "Age 65 or older", "Bachelor's degree or more", "Household income under $30k",
          "White, non-Hispanic", "Black, non-Hispanic", "Hispanic", "Thinks of self as a small-town or rural person",
          "Religion very or extremely important", "Atheist, agnostic or nothing in particular",
          "Cut down on spending this year", "Pays attention to politics always or most of the time",
          "Voted for president in 2024", "Haven't thought much on at least one 7-point scale",
          "Very or extremely hopeful", "Very or extremely angry",
          "Watches Fox News shows (Hannity, The Five, Ingraham, Gutfeld!, Watters, Baier, Outnumbered) regularly",
          "Watches MSNBC evening shows (Maddow, O'Donnell, Hayes, Wallace, Ruhle) regularly"]
SHORT = {"Watches Fox News shows (Hannity, The Five, Ingraham, Gutfeld!, Watters, Baier, Outnumbered) regularly": "Watches Fox News shows",
         "Watches MSNBC evening shows (Maddow, O'Donnell, Hayes, Wallace, Ruhle) regularly": "Watches MSNBC evening shows",
         "Haven't thought much on at least one 7-point scale": "Said \"haven't thought much\" on a policy scale",
         "Thinks of self as a small-town or rural person": "Small-town or rural identity",
         "Pays attention to politics always or most of the time": "Follows politics most of the time"}


def heat(seg, overall, signal):
    d = seg - overall
    a = min(1.0, abs(d) / 0.35) if signal == "Strong" else 0.0
    col = f"rgba(98,80,214,{a:.2f})" if d > 0 else f"rgba(235,104,52,{a:.2f})"
    ink = "#fff" if a > 0.6 else "var(--text-primary)"
    return f'<td class="hc" style="background:{col};color:{ink}" title="{seg:.0%} vs {overall:.0%} overall; {signal}">{seg:.0%}</td>'


def glance():
    head = "".join(f"<th>{html.escape(SEGMENTS[k][0])}<br><span class=muted>{P[k]['share']:.0%} of sample</span></th>" for k in ORDER)
    rows = []
    for name in GLANCE:
        cells = "".join(heat(*val(k, name)[:3]) for k in ORDER)
        rows.append(f'<tr><td class="lab">{html.escape(SHORT.get(name, name))}</td><td class="num muted">{allv(name)}</td>{cells}</tr>')
    return f'<div class="scroll"><table class="glance"><thead><tr><th></th><th>All</th>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def ranked(k, section, n, asc=False):
    s = D[(D.segment == k) & (D.section == section)].sort_values("segment_value", ascending=asc).head(n)
    return s


def card(k):
    name, sub, text = SEGMENTS[k]
    p = P[k]
    v = p["vote"]
    nv = v["Did not vote / missing"] + v["No post interview"]
    pri = ranked(k, "Priorities", 9)
    pri_rows = "".join(
        f'<li><span class="bar" style="width:{r.segment_value * 100:.0f}%"></span><span class="bl">{html.escape(r.descriptor[6:-27])} {r.segment_value:.0%}'
        f'{"" if r.signal != "Strong" else (" ▲" if r.diff > 0 else " ▼")}</span></li>' for r in pri.itertuples())
    th = D[(D.segment == k) & (D.section == "Feelings toward groups and figures")]
    warm = th.sort_values("segment_value", ascending=False).head(4)
    cold = th.sort_values("segment_value").head(4)
    fmt = lambda r: f'{html.escape(r.descriptor[13:-8])} <b>{r.segment_value:.0f}</b>'
    dist = D[(D.segment == k) & (D.signal == "Strong") & (~D.section.isin(["Priorities"]))].copy()
    dist["size"] = dist.effect.abs().where(~dist.binary, dist.effect.abs() / 20)
    dist = dist.sort_values("size", ascending=False).head(6)
    dist_rows = "".join(
        f'<li>{html.escape(SHORT.get(r.descriptor, r.descriptor.split(" (higher")[0]))}: <b>{r.segment_value:.0%}</b> vs {r.overall_value:.0%}</li>' if r.binary
        else f'<li>{html.escape(r.descriptor.split(" (higher")[0][:90])}: <b>{r.segment_value:.1f}</b> vs {r.overall_value:.1f}'
             f'{"" if "(higher" not in r.descriptor else " <span class=muted>(higher = " + html.escape(r.descriptor.split("toward ")[1][:-1]) + ")</span>"}</li>'
        for r in dist.itertuples())
    return f"""<section class="card"><h2>{html.escape(name)}</h2><p class="sub">{html.escape(sub)}</p>
<p class="meta">{p['share']:.0%} of the sample (n = {p['n']:,}) · {v['Harris']:.0%} Harris, {v['Trump']:.0%} Trump, {nv:.0%} did not vote or no data · party ID {p['pid_dem']:.0%} D, {p['pid_rep']:.0%} R</p>
<p class="portrait">{text(k)}</p>
<div class="grid"><div><h3>Where they stand</h3><ul class="dist">{"".join(f"<li>{x}</li>" for x in stances(k))}</ul>
<h3>What they rate very important</h3><ul class="pri">{pri_rows}</ul></div>
<div><h3>Warmest toward</h3><ul class="th">{"".join(f"<li>{fmt(r)}</li>" for r in warm.itertuples())}</ul>
<h3>Coldest toward</h3><ul class="th">{"".join(f"<li>{fmt(r)}</li>" for r in cold.itertuples())}</ul></div>
<div><h3>Furthest from the sample</h3><ul class="dist">{dist_rows}</ul></div></div></section>"""


def main():
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ANES Segment Portraits</title><style>
:root{{--surface:#fcfcfb;--card:#fff;--text-primary:#0b0b0b;--text-secondary:#52514e;--rule:#e4e3df;--accent:#2a78d6;color-scheme:light}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--surface:#1a1a19;--card:#232321;--text-primary:#f0efec;--text-secondary:#c3c2b7;--rule:#383835;--accent:#3987e5;color-scheme:dark}}}}
:root[data-theme="dark"]{{--surface:#1a1a19;--card:#232321;--text-primary:#f0efec;--text-secondary:#c3c2b7;--rule:#383835;--accent:#3987e5;color-scheme:dark}}
body{{margin:0;background:var(--surface);color:var(--text-primary);font:14px/1.5 -apple-system,BlinkMacSystemFont,"Inter",sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:24px 16px 64px}} h1{{font-size:22px;margin:0 0 6px}}
p.lead{{max-width:860px;color:var(--text-secondary)}} .muted{{color:var(--text-secondary);font-weight:400}}
.scroll{{overflow-x:auto}} table.glance{{border-collapse:separate;border-spacing:2px;font-variant-numeric:tabular-nums;margin:12px 0 28px}}
table.glance th{{font-size:12px;text-align:center;padding:4px 6px;vertical-align:bottom;min-width:96px}} td.lab{{font-size:12.5px;padding-right:10px;white-space:nowrap}}
td.num{{text-align:right;padding:4px 8px}} td.hc{{text-align:center;border-radius:4px;padding:5px 6px;font-size:12.5px}}
.card{{background:var(--card);border:1px solid var(--rule);border-radius:10px;padding:18px 20px;margin:16px 0}}
.card h2{{font-size:18px;margin:0}} .sub{{margin:2px 0 8px;color:var(--text-secondary)}} .meta{{font-size:12.5px;color:var(--text-secondary);margin:0 0 10px}}
.portrait{{max-width:900px;margin:0 0 14px}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px}}
h3{{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--text-secondary);margin:6px 0 6px}}
ul{{list-style:none;margin:0 0 8px;padding:0}} ul.pri li{{position:relative;height:20px;margin:3px 0}}
.bar{{position:absolute;left:0;top:2px;bottom:2px;background:var(--accent);opacity:.18;border-radius:3px}} .bl{{position:relative;padding-left:6px;font-size:12.5px}}
ul.th li,ul.dist li{{font-size:12.5px;margin:3px 0}}
</style></head><body><main>
<h1>Four kinds of ANES voters</h1>
<p class="lead">The four stable segments ANES 2024 forms from eight of its own attitude factors (n = {sum(p["n"] for p in P.values()):,} respondents who answered at least half of each of those factors' items, post-election weights). Two more factors, trust in institutions and leaving decisions to business leaders or experts, did not qualify to define segments because each comes from a single question battery; they appear below as descriptions.
"Where they stand" reads the factors the segments were built on; everything else describes them on things the clustering never used. Names are working labels for this page.
In the table, violet cells sit clearly above the full sample and orange cells clearly below it, judged by a 1,000-draw bootstrap (P ≥ 0.95); uncolored cells are within the noise.
In the priority lists, ▲ and ▼ mark the same test. Three of the four segments hold up under resampling (mean overlap of 0.75 or more across 30 resamples); the fourth sits between stable and dissolved.</p>
{glance()}
{"".join(card(k) for k in ORDER)}
</main></body></html>"""
    (SRC / "segment_portraits.html").write_text(page)
    print(SRC / "segment_portraits.html")


if __name__ == "__main__":
    main()
