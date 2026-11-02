"""Who is in each stable ANES segment: every independent cluster against the rest of the sample.

Data: ANES 2024 Time Series CSV and codebook (2025-08-08 release), post weight V240108a. Segments from
outputs/clustering/independent_available/independent_clusters.csv (independent_clustering.py --available,
n = 4,673, 4 clusters).
Descriptors are variables the clustering never saw: demographics, religion, finances, engagement,
emotions about the country, issue importance, group and candidate thermometers, news and social media,
and the attitude-pool items the independent screen excluded (in the pool, not among the 99 factored items).

Each descriptor is a weighted share (binary) or weighted mean. Segment vs rest is compared by a
respondent bootstrap (1,000 draws, seed 42): the difference, its 95% interval, and P(segment > rest),
labeled with the research-statistics group-comparison table (>= 0.95 Strong, 0.90-0.95 Moderate,
0.80-0.90 Directional, else Inconclusive; mirrored for "lower"). The bootstrap ignores the ANES PSU and
strata, so intervals run somewhat narrow; ~120 descriptors x 4 segments are compared, so expect a few
Strong labels by chance among the small differences. Effect size for ranking: percentage points for
shares, difference in weighted SDs for means.

Writes outputs/clustering/independent_available/segment_descriptors.csv.
"""
import re

import numpy as np
import pandas as pd

import describe_clusters as dc
import independent_efa as ie
import matched_efa as me
import recode_matched as rm

SRC = me.OUT / "clustering" / "independent_available"
CODEBOOK = rm.ANES_CSV.parent / "anes_timeseries_2024_userguidecodebook_20250808.pdf"
N_BOOT, SEED = 1000, 42

THERMS = {"V241156": "Kamala Harris", "V241157": "Donald Trump", "V241166": "Democratic Party", "V241167": "Republican Party",
          "V242137": "Christian fundamentalists", "V242138": "feminists", "V242139": "liberals", "V242140": "labor unions",
          "V242141": "big business", "V242142": "conservatives", "V242143": "US Supreme Court", "V242144": "gay men and lesbians",
          "V242145": "Congress", "V242146": "Muslims", "V242147": "Christians", "V242148": "MAGA", "V242149": "Jews",
          "V242150": "police", "V242151": "transgender people", "V242152": "Black Lives Matter", "V242153": "NRA",
          "V242154": "FBI", "V242155": "rural Americans", "V242156": "Planned Parenthood", "V242514": "Asian Americans",
          "V242515": "Hispanics", "V242516": "Blacks", "V242517": "illegal immigrants", "V242518": "whites"}
ISSUES = {"V242172": "illegal immigration", "V242173": "cost of living", "V242174": "climate change", "V242175": "gun policy",
          "V242176": "abortion", "V242177": "crime", "V242178": "war in Gaza", "V242179": "what is taught in public schools",
          "V242180": "US democracy"}


TV = {"Fox News shows (Hannity, The Five, Ingraham, Gutfeld!, Watters, Baier, Outnumbered)":
          ["V241601b", "V241601c", "V241601f", "V241601g", "V241601h", "V241601k", "V241602k"],
      "MSNBC evening shows (Maddow, O'Donnell, Hayes, Wallace, Ruhle)": ["V241601d", "V241601e", "V241602m", "V241602n", "V241602p"],
      "network evening news (ABC, CBS or NBC)": ["V241601m", "V241601n", "V241601p"],
      "PBS NewsHour": ["V241602q"]}


def any_of(raw, cols):
    X = raw[cols].apply(pd.to_numeric, errors="coerce")
    return pd.Series(np.where((X >= 0).all(axis=1), (X == 1).any(axis=1).astype(float), np.nan), index=raw.index)


def share(s, yes, valid=None):
    s = pd.to_numeric(s, errors="coerce")
    ok = s.isin(valid) if valid is not None else s > 0
    return pd.Series(np.where(ok, s.isin(yes).astype(float), np.nan), index=s.index)


def build(raw):
    v = lambda c: pd.to_numeric(raw[c], errors="coerce")
    age = v("V241458x").where(lambda x: x >= 18)
    D = {
        ("Who they are", "Women"): share(raw.V241550, [2]),
        ("Who they are", "Age under 35"): (age < 35).astype(float).where(age.notna()),
        ("Who they are", "Age 65 or older"): (age >= 65).astype(float).where(age.notna()),
        ("Who they are", "Bachelor's degree or more"): share(raw.V241465x, [4, 5]),
        ("Who they are", "No education past high school"): share(raw.V241465x, [1, 2]),
        ("Who they are", "Household income under $30k"): share(raw.V241567x, [1, 2]),
        ("Who they are", "Household income $100k or more"): share(raw.V241567x, [5, 6]),
        ("Who they are", "White, non-Hispanic"): share(raw.V241501x, [1]),
        ("Who they are", "Black, non-Hispanic"): share(raw.V241501x, [2]),
        ("Who they are", "Hispanic"): share(raw.V241501x, [3]),
        ("Who they are", "Asian American or Pacific Islander"): share(raw.V241501x, [4]),
        ("Who they are", "Married"): share(raw.V241461x, [1]),
        ("Who they are", "Never married"): share(raw.V241461x, [5]),
        ("Who they are", "Children under 18 at home"): (v("V241521") > 0).astype(float).where(v("V241521") >= 0),
        ("Who they are", "Union household"): share(raw.V241497, [1]),
        ("Who they are", "Gay, lesbian, bisexual or other"): share(raw.V241553, [2, 3, 4]),
        ("Who they are", "Lives in the South"): share(raw.V243007, [3]),
        ("Who they are", "Thinks of self as a small-town or rural person"): share(raw.V242341, [3, 4]),
        ("Who they are", "Thinks of self as a city person"): share(raw.V242341, [1]),
        ("Faith", "Religion very or extremely important"): share(raw.V241420, [1, 2]),
        ("Faith", "Born-again Christian"): pd.Series(np.where(v("V241442") == 1, 1.0, np.where(v("V241422") > 0, 0.0, np.nan))),
        ("Faith", "Catholic"): share(raw.V241422, [2]),
        ("Faith", "Atheist, agnostic or nothing in particular"): share(raw.V241422, [9, 10, 12]),
        ("Money", "Very or extremely worried about finances"): share(raw.V241539, [1, 2]),
        ("Money", "Borrowed money to pay bills this year"): share(raw.V241568a, [1], [0, 1]),
        ("Money", "Cut down on spending this year"): share(raw.V241568b, [1], [0, 1]),
        ("Engagement", "Pays attention to politics always or most of the time"): share(raw.V241004, [1, 2]),
        ("Engagement", "Very interested in the campaign"): share(raw.V241005, [1]),
        ("Engagement", "Voted for president in 2024"): pd.Series(np.where(v("V242096x") > 0, 1.0, np.where(v("V242096x") == -2, 0.0, np.nan))),
        ("Engagement", "Haven't thought much on at least one 7-point scale"): (raw[dc.SCALES_7PT].apply(pd.to_numeric, errors="coerce") == 99).any(axis=1).astype(float),
        ("Mood about the country", "Very or extremely hopeful"): share(raw.V241118, [4, 5]),
        ("Mood about the country", "Very or extremely afraid"): share(raw.V241119, [4, 5]),
        ("Mood about the country", "Very or extremely angry"): share(raw.V241121, [4, 5]),
        **{("News and media", f"Watches {nm} regularly"): any_of(raw, cs) for nm, cs in TV.items()},
        ("News and media", "Uses TikTok"): share(raw.V242577g, [1], [0, 1]),
        ("News and media", "Uses Facebook"): share(raw.V242577a, [1], [0, 1]),
        ("News and media", "Uses YouTube"): share(raw.V242577e, [1], [0, 1]),
        ("News and media", "Days a week getting news from social media (0-7)"): v("V242406").where(lambda x: x.between(0, 7)),
    }
    for c, nm in ISSUES.items():
        D[("Priorities", f"Rates {nm} extremely or very important")] = share(raw[c], [1, 2])
    for c, nm in THERMS.items():
        D[("Feelings toward groups and figures", f"Warmth toward {nm} (0-100)")] = v(c).where(lambda x: x.between(0, 100))
    return pd.DataFrame(D)


def top_label(var, anes_map):
    """Codebook label of the raw code that recodes highest, for 'higher = toward ...' phrasing."""
    try:
        pairs = dict(tuple(map(int, p.split("="))) for p in anes_map.split(","))
    except ValueError:
        return None
    raw_top = max(pairs, key=pairs.get)
    return CODE_LABELS.get(var, {}).get(raw_top)


def codebook_labels():
    import subprocess
    txt = subprocess.run(["pdftotext", "-layout", str(CODEBOOK), "-"], capture_output=True, text=True).stdout.split("\n")
    out, cur = {}, None
    for line in txt:
        m = re.match(r"^(V24\d{4}[a-z0-9]*)\b", line)
        if m:
            cur = m.group(1)
            out.setdefault(cur, {})
            continue
        m = re.search(r"(?<![\d-])(\d{1,3})\.\s+(\S.*)", line)
        if cur and m and int(m.group(1)) not in out[cur]:
            out[cur][int(m.group(1))] = m.group(2).strip()
    return out


def main():
    global CODE_LABELS
    seg = pd.read_csv(SRC / "independent_clusters.csv")[["caseid", "cluster"]]
    cols = (["V240001", rm.WEIGHT, "V241550", "V241458x", "V241465x", "V241567x", "V241501x", "V241461x", "V241521",
             "V241497", "V241553", "V243007", "V242341", "V241420", "V241442", "V241422", "V241539", "V241568a", "V241568b",
             "V241004", "V241005", "V242096x", "V241118", "V241119", "V241121", "V242577g", "V242577a",
             "V242577e", "V242406"] + [c for cs in TV.values() for c in cs] + dc.SCALES_7PT + list(ISSUES) + list(THERMS))
    raw = pd.read_csv(rm.ANES_CSV, usecols=cols, low_memory=False)
    D = build(raw)
    D.index = raw.V240001.values

    # attitude-pool items the independent screen excluded from the 99 factored items
    CODE_LABELS = codebook_labels()
    items, w_pool, _, cw = ie.load_pool()
    desc_all, keep_w = dc.descriptors()
    items.index = desc_all.caseid[keep_w].values
    factored = set(pd.read_csv(me.OUT / "independent_loadings.csv", index_col=0).index)
    for c in items.columns:
        if c in factored or "|" in cw.loc[c, "anes_sources"]:
            continue
        top = top_label(cw.loc[c, "anes_sources"], cw.loc[c, "anes_map"])
        if top is None:
            continue
        x = items[c]
        D[("Views the clustering didn't use", f"{cw.label[c][:80]} (higher = toward '{top[:40]}')")] = x.reindex(D.index)

    D = D.loc[seg.caseid.values]
    w = pd.to_numeric(raw.set_index("V240001").loc[seg.caseid.values, rm.WEIGHT]).values
    cl = seg.cluster.values
    X = D.values.astype(float)
    M = ~np.isnan(X)
    X0 = np.where(M, X, 0.0)
    binary = np.array([set(np.unique(X[M[:, j], j])) <= {0.0, 1.0} for j in range(X.shape[1])])
    K = cl.max() + 1

    def means(c):
        out = np.zeros((K, 2, X.shape[1]))
        for k in range(K):
            for side, sel in ((0, cl == k), (1, cl != k)):
                ww = c * sel
                out[k, side] = (ww @ X0) / (ww @ M)
        return out

    est = means(w)
    overall = (w @ X0) / (w @ M)
    rng = np.random.default_rng(SEED)
    boots = np.stack([means(w * np.bincount(rng.integers(0, len(w), len(w)), minlength=len(w))) for _ in range(N_BOOT)])
    diff = boots[:, :, 0] - boots[:, :, 1]
    p_gt = (diff > 0).mean(axis=0)
    sd = np.sqrt(np.array([np.average((X[M[:, j], j] - np.average(X[M[:, j], j], weights=w[M[:, j]])) ** 2,
                                      weights=w[M[:, j]]) for j in range(X.shape[1])]))
    rows = []
    for k in range(K):
        for j, (section, name) in enumerate(D.columns):
            p = p_gt[k, j]
            d = est[k, 0, j] - est[k, 1, j]
            label = ("Strong" if max(p, 1 - p) >= 0.95 else "Moderate" if max(p, 1 - p) >= 0.90
                     else "Directional" if max(p, 1 - p) >= 0.80 else "Inconclusive")
            rows.append({"segment": k, "section": section, "descriptor": name, "binary": bool(binary[j]),
                         "segment_value": est[k, 0, j], "rest_value": est[k, 1, j], "overall_value": overall[j], "diff": d,
                         "diff_lo": np.quantile(diff[:, k, j], 0.025), "diff_hi": np.quantile(diff[:, k, j], 0.975),
                         "p_segment_higher": p, "signal": label,
                         "effect": d * 100 if binary[j] else d / sd[j],
                         "n_valid": int(M[cl == k, j].sum())})
    out = pd.DataFrame(rows)
    out.to_csv(SRC / "segment_descriptors.csv", index=False)
    print(f"{D.shape[1]} descriptors x {K} segments; n = {len(seg):,}")
    for k in range(K):
        s = out[(out.segment == k) & (out.signal == "Strong")].copy()
        s["size"] = np.where(s.binary, s.effect.abs() / 10, s.effect.abs())  # 10pp ~ 1 SD for ranking
        s = s.sort_values("size", ascending=False).head(14)
        print(f"\n== segment {k} ==")
        for r in s.itertuples():
            unit = f"{r.segment_value:.0%} vs {r.rest_value:.0%}" if r.binary else f"{r.segment_value:.2f} vs {r.rest_value:.2f} ({r.effect:+.2f} SD)"
            print(f"  [{r.section[:18]}] {r.descriptor[:95]}: {unit}")


if __name__ == "__main__":
    main()
