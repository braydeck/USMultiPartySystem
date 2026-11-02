"""Render the five stable ANES segments as portraits: outputs/clustering/independent/segment_portraits.html.

Inputs: outputs/clustering/independent/segment_descriptors.csv (describe_segments.py) and
outputs/clustering/cluster_profiles.json (describe_clusters.py) for vote and party ID. Every number in the
prose is read from those files. Segment names are working labels defined on the page.
"""
import html
import json

import pandas as pd

import matched_efa as me

SRC = me.OUT / "clustering" / "independent"
D = pd.read_csv(SRC / "segment_descriptors.csv")
P = {c["cluster"]: c for c in json.loads((me.OUT / "clustering" / "cluster_profiles.json").read_text())["independent"]["clusters"]}
ORDER = [2, 4, 1, 0, 3]


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


def view(prefix):
    return D[D.descriptor.str.startswith(prefix)].descriptor.iloc[0]


GAY_ADOPT = view("summary should gay/lesbian couples be allowed to adopt")
ABORT7 = view("7pt scale abortion: self-placement")
TRUST_FED = view("how often trust government in washington")
TRUST_OFF = view("trust election officials")
UKRAINE = view("favor/oppose u.s. giving weapons to help ukraine")
FAMILY = view("fewer problems if there was more emphasis on traditional family")

SEGMENTS = {
    2: ("Secular progressives",
        "Harris voters for whom religion plays little part, the most secular and most urban of the five.",
        lambda k: f"""Religion is very or extremely important to {pct(k, "Religion very or extremely important")} of this segment, against {allv("Religion very or extremely important")} of the sample, and {pct(k, "Atheist, agnostic or nothing in particular")} are atheist, agnostic or nothing in particular. {pct(k, "Bachelor's degree or more")} hold a bachelor's degree and {pct(k, "Gay, lesbian, bisexual or other")} identify as gay, lesbian, bisexual or something else. They rate Donald Trump at {num(k, therm("Donald Trump"))} out of 100, Christian fundamentalists at {num(k, therm("Christian fundamentalists"))} and the Supreme Court at {num(k, therm("US Supreme Court"))}. US democracy ({pct(k, "Rates US democracy extremely or very important")}) and climate change ({pct(k, "Rates climate change extremely or very important")}) top their issue list; illegal immigration is rated very important by {pct(k, "Rates illegal immigration extremely or very important")}, against {allv("Rates illegal immigration extremely or very important")} overall."""),
    4: ("Institution-trusting Democrats",
        "Older, engaged Harris voters who trust the people counting the votes and feel hopeful about the country.",
        lambda k: f"""{pct(k, "Voted for president in 2024")} voted, and {pct(k, "Very or extremely hopeful")} feel very or extremely hopeful about the country, against {allv("Very or extremely hopeful")} overall; {pct(k, "Very or extremely angry")} feel very or extremely angry ({allv("Very or extremely angry")} overall). They trust their local election officials at {num(k, TRUST_OFF, 1)} on a 1 to 5 scale, against {allv(TRUST_OFF, 1)} overall. {pct(k, "Age 65 or older")} are 65 or older and {pct(k, "Women")} are women. They watch the network evening news ({pct(k, "Watches network evening news (ABC, CBS or NBC) regularly")}), MSNBC's evening shows ({pct(k, "Watches MSNBC evening shows (Maddow, O'Donnell, Hayes, Wallace, Ruhle) regularly")}) and PBS NewsHour ({pct(k, "Watches PBS NewsHour regularly")}). Religion is very or extremely important to {pct(k, "Religion very or extremely important")}, against {pct(2, "Religion very or extremely important")} of the secular progressives, the segment they border."""),
    1: ("Multiracial religious traditionalists",
        "A working-class, religious segment split evenly between Harris and Trump, and the most likely of the five to say they haven't thought much about a policy.",
        lambda k: f"""{pct(k, "White, non-Hispanic")} of this segment is white, {pct(k, "Black, non-Hispanic")} Black and {pct(k, "Hispanic")} Hispanic, against {allv("White, non-Hispanic")}, {allv("Black, non-Hispanic")} and {allv("Hispanic")} overall. {pct(k, "No education past high school")} have no education past high school, {pct(k, "Children under 18 at home")} have children at home, and religion is very or extremely important to {pct(k, "Religion very or extremely important")}. They are cooler than the sample toward gay men and lesbians ({num(k, therm("gay men and lesbians"))} vs {allv(therm("gay men and lesbians"), 0)}), transgender people ({num(k, therm("transgender people"))} vs {allv(therm("transgender people"), 0)}) and Jews ({num(k, therm("Jews"))} vs {allv(therm("Jews"), 0)}). {pct(k, "Haven't thought much on at least one 7-point scale")} answered "haven't thought much" on at least one policy scale, and {pct(k, "Voted for president in 2024")} voted."""),
    0: ("Financially squeezed skeptics",
        "The largest segment: Republican-leaning but loosely attached, under financial strain, distrustful of government and elections, and focused on prices.",
        lambda k: f"""{pct(k, "Cut down on spending this year")} cut their spending this year and {pct(k, "Borrowed money to pay bills this year")} borrowed to pay bills, the highest of the five on both. Asked how often they trust the federal government, they average {num(k, TRUST_FED, 2)} on a 1 to 5 scale (5 = never), against {allv(TRUST_FED, 2)} overall. {pct(k, "Pays attention to politics always or most of the time")} follow politics always or most of the time, the lowest of the five, and {pct(k, "Voted for president in 2024")} voted. Cost of living is very important to {pct(k, "Rates cost of living extremely or very important")}; abortion ({pct(k, "Rates abortion extremely or very important")}), gun policy ({pct(k, "Rates gun policy extremely or very important")}) and climate change ({pct(k, "Rates climate change extremely or very important")}) rank lower here than in the sample. They rate the NRA at {num(k, therm("NRA"))}, Donald Trump at {num(k, therm("Donald Trump"))} and Kamala Harris at {num(k, therm("Kamala Harris"))}."""),
    3: ("Religious conservatives",
        "Older, rural, devout Trump voters, the angriest and most afraid about the country of the five.",
        lambda k: f"""Religion is very or extremely important to {pct(k, "Religion very or extremely important")} and {pct(k, "Born-again Christian")} are born-again Christians. {pct(k, "Thinks of self as a small-town or rural person")} think of themselves as small-town or rural people, {pct(k, "Married")} are married and {pct(k, "Age 65 or older")} are 65 or older. {pct(k, "Very or extremely angry")} feel very or extremely angry about the country and {pct(k, "Very or extremely afraid")} very or extremely afraid. They rate MAGA at {num(k, therm("MAGA"))} and Planned Parenthood at {num(k, therm("Planned Parenthood"))}, and place themselves at {num(k, ABORT7, 1)} on the 1 to 7 abortion scale (7 = never permitted), against {allv(ABORT7, 1)} overall. {pct(k, "Watches Fox News shows (Hannity, The Five, Ingraham, Gutfeld!, Watters, Baier, Outnumbered) regularly")} watch Fox News shows regularly. Climate change is very important to {pct(k, "Rates climate change extremely or very important")}."""),
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
<div class="grid"><div><h3>What they rate very important</h3><ul class="pri">{pri_rows}</ul></div>
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
<h1>Five kinds of ANES voters</h1>
<p class="lead">The five stable segments ANES 2024 forms from its own attitude factors (n = 3,614 respondents complete on the 40 clustering items, post-election weights).
Everything below describes the segments on things the clustering never used. Names are working labels for this page.
In the table, violet cells sit clearly above the full sample and orange cells clearly below it, judged by a 1,000-draw bootstrap (P ≥ 0.95); uncolored cells are within the noise.
In the priority lists, ▲ and ▼ mark the same test. The two Harris-voting segments share the least stable border.</p>
{glance()}
{"".join(card(k) for k in ORDER)}
</main></body></html>"""
    (SRC / "segment_portraits.html").write_text(page)
    print(SRC / "segment_portraits.html")


if __name__ == "__main__":
    main()
