"""Production nine parties vs the ten four-dimension clusters: factor positions, policy views, demographics.

Data: CES 2024 Common Content (efa_update.CES_PATH), weight commonpostweight.
  Production: data/processed/typology_cluster_assignments.csv (cluster per row) joined to
    data/processed/efa_factor_scores.csv (same row order, caseid, FS_F1..FS_F5), n = 45,214; party codes from
    rescore_refit.pc.CLUSTER_TO_PARTY.
  New: outputs/four_dim/scores.csv (n = 49,431) and the cap-10 modal seed solution in outputs/four_dim/labels.npz
    (best lower bound within the modal solution), the clusters tested in four_dim_draws.py.
Each group is profiled on its own members. Factor means are in weighted SD units of everyone holding that score,
each factor oriented so high = its name (more pro-order, more distrust, more religious, more conservative); the
orientation is set from item correlations and printed. Policy cells are the weighted share giving the stated answer
among members who answered. Party ID and vote come last, as context.
Closest production party per new cluster: Euclidean distance between centroids on the four new dimensions.
Writes outputs/compare_typologies/{factors,policy,demographics,pairs,crosswalk_rows,crosswalk_cols}.csv and index.html.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import leaves_list, linkage, optimal_leaf_ordering
from scipy.spatial.distance import pdist

import item_pool as ip
import loading_draws as ld
import reestimate_loadings as rl
import rescore_refit as rr

# `compare_typologies.py` = the four_dim ten (2026-11-02); `compare_typologies.py v2 9` = the adopted nine of the revised
# rule (outputs/stage_c_v2, plain scores), lettered A-I in production order of their largest source party.
SRC, CAP = (sys.argv[1], int(sys.argv[2])) if len(sys.argv) > 2 else ("four_dim", 10)
V2 = SRC == "v2"
OUT = rl.OUT / ("compare_typologies" if not V2 else f"compare_typologies_k{CAP}")
TOKENS = Path.home() / ".claude/skills/html-research-artifacts/assets/tokens.css"
PROD_ORDER = ["CON", "CUP", "NAT", "POP", "STY", "LBR", "DAL", "PRG", "DSA"]

AGREE = ["Strongly agree", "Somewhat agree"]
TOPICS = [
    ("Guns and police", [
        ("CC24_321a", "Ban assault rifles", ["Support"]),
        ("CC24_321b", "Make concealed-carry permits easier to get", ["Support"]),
        ("CC24_321c", "Background checks on all gun sales", ["Support"]),
        ("CC24_321f", "Mental health and school safety, red-flag and domestic-violence gun rules", ["Support"]),
        ("CC24_321d", "10% more police, even with fewer other services", ["Support"]),
        ("CC24_321e", "10% fewer police, more for other services", ["Support"])]),
    ("Immigration", [
        ("CC24_323a", "Legal status for undocumented workers (3+ years, taxes, no felonies)", ["Support"]),
        ("CC24_323b", "More border patrols on the US-Mexico border", ["Support"]),
        ("CC24_323c", "Build a wall on the US-Mexico border", ["Support"]),
        ("CC24_323d", "Permanent residency and a citizenship path for Dreamers", ["Support"]),
        ("CC24_340f", "Deny asylum to people who cross the border illegally", ["Support"])]),
    ("Abortion and contraception", [
        ("CC24_324a", "Always allow abortion as a matter of choice", ["Support"]),
        ("CC24_324b", "Abortion only for rape, incest or the woman's life", ["Support"]),
        ("CC24_324c", "Make abortion illegal in all circumstances", ["Support"]),
        ("CC24_324d", "Expand abortion access and affordability", ["Support"]),
        ("CC24_340b", "Bar government restrictions on abortion services", ["Support"]),
        ("CC24_340a", "Bar government restrictions on contraceptives", ["Support"]),
        ("CC24_444c", "State: ban abortion pills by mail", ["Support"]),
        ("CC24_444d", "State: bar travel out of state for an abortion", ["Support"]),
        ("CC24_445b", "Agree Roe was rightly overturned", ["Agree"]),
        ("CC24_325", "Week limit: abortion legal at no point (0 weeks)", ["0.0"]),
        ("CC24_325", "Week limit: 15 weeks or earlier (includes 0)", [f"{i}.0" for i in range(16)]),
        ("CC24_325", "Week limit: none (40 weeks)", ["40.0"])]),
    ("Environment and energy", [
        ("CC24_326a", "EPA power to regulate carbon dioxide", ["Support"]),
        ("CC24_326b", "Require 20% renewable electricity", ["Support"]),
        ("CC24_326c", "Stronger Clean Air and Water Act enforcement, even at a cost in jobs", ["Support"]),
        ("CC24_326d", "Increase US fossil fuel production", ["Support"]),
        ("CC24_326e", "Halt new oil and gas leases on federal land", ["Support"]),
        ("CC24_326f", "Prevent bans on gas stoves", ["Support"])]),
    ("Housing, health care, student debt", [
        ("CC24_328a", "Relax local zoning to allow more apartments", ["Support"]),
        ("CC24_328b", "Tax incentives for low-income housing", ["Support"]),
        ("CC24_328c", "Medicaid work requirement for childless adults", ["Support"]),
        ("CC24_328d", "Repeal the Affordable Care Act", ["Support"]),
        ("CC24_328e", "Expand Medicaid to low-income adults and families", ["Support"]),
        ("CC24_323f", "Forgive up to $20,000 of student debt", ["Support"])]),
    ("Taxes and federal spending", [
        ("CC24_341a", "Extend the 2017 tax cuts", ["Support"]),
        ("CC24_341b", "Raise the corporate tax rate to 28%", ["Support"]),
        ("CC24_341c", "Raise taxes on $400k+ earners to 35%", ["Support"]),
        ("CC24_341d", "$150B a year on infrastructure for 8 years", ["Support"])]),
    ("State spending (share wanting an increase)", [
        ("CC24_443_1", "Welfare", ["Greatly increase", "Slightly increase"]),
        ("CC24_443_2", "Health care", ["Greatly increase", "Slightly increase"]),
        ("CC24_443_3", "Education", ["Greatly increase", "Slightly increase"]),
        ("CC24_443_4", "Law enforcement", ["Greatly increase", "Slightly increase"]),
        ("CC24_443_5", "Transportation and infrastructure", ["Greatly increase", "Slightly increase"])]),
    ("Other bills in Congress", [
        ("CC24_340c", "Federal recognition of same-sex and interracial marriage", ["Support"]),
        ("CC24_340d", "Ban TikTok unless sold to a US company", ["Support"]),
        ("CC24_340e", "Renew warrantless surveillance programs", ["Support"])]),
    ("Elections and trust in government", [
        ("CC24_421_1", "Agree US elections are fair", AGREE),
        ("CC24_421_2", "Agree my state ran a fair, accurate 2024 election", AGREE),
        ("CC24_423", "Little or no trust in the federal government", ["Not very much", "None at all"]),
        ("CC24_424", "Little or no trust in the state government", ["Not very much", "None at all"])]),
    ("Race and gender attitudes (share agreeing)", [
        ("CC24_440a", "White people have advantages because of their skin color", AGREE),
        ("CC24_440b", "Racial problems are rare, isolated situations", AGREE),
        ("CC24_440c", "Women seek power by getting control over men", AGREE),
        ("CC24_440d", "Women are too easily offended", AGREE),
        ("CC24_441a", "Blacks should work their way up without special favors", AGREE),
        ("CC24_441b", "Slavery and discrimination make it hard for Blacks to rise", AGREE),
        ("CC24_441e", "I resent when Whites deny racial discrimination exists", AGREE),
        ("CC24_441f", "Whites get away with offenses Blacks would not", AGREE),
        ("CC24_441g", "Whites don't try hard to understand Black Americans' problems", AGREE),
        ("CC24_445a", "Agree race in college admissions is unconstitutional", ["Agree"])]),
    ("State culture and schooling policies", [
        ("CC24_444a", "Ban gender-transition surgery for minors", ["Support"]),
        ("CC24_444b", "Parental consent before teachers use a new name or pronoun", ["Support"]),
        ("CC24_444e", "Age verification for adult websites", ["Support"]),
        ("CC24_444f", "School vouchers for private or charter schools", ["Support"])]),
    ("Religion", [
        ("pew_churatd", "Attend services weekly or more", ["More than once a week", "Once a week"]),
        ("pew_religimp", "Religion very important", ["Very important"]),
        ("pew_prayer", "Pray daily or more", ["Several times a day", "Once a day"]),
        ("pew_bornagain", "Born-again or evangelical", ["Yes"])]),
    ("Personal economy, past year", [
        ("CC24_302", "Household income decreased", ["Decreased somewhat", "Decreased a lot"]),
        ("CC24_303", "Prices increased a lot", ["Increased a lot"])]),
    ("Use of US troops (share selecting)", [
        ("CC24_420_1", "To ensure the oil supply", ["selected"]),
        ("CC24_420_2", "To destroy a terrorist camp", ["selected"]),
        ("CC24_420_3", "To intervene in genocide or civil war", ["selected"]),
        ("CC24_420_4", "To spread democracy", ["selected"]),
        ("CC24_420_5", "To protect allies under attack", ["selected"]),
        ("CC24_420_6", "To help the UN uphold international law", ["selected"])]),
    ("Ukraine (share selecting)", [
        ("CC24_308a_2", "Humanitarian aid", ["selected"]),
        ("CC24_308a_3", "Sanctions on Russia", ["selected"]),
        ("CC24_308a_4", "Arms to Ukraine", ["selected"]),
        ("CC24_308a_5", "Non-combat military staff", ["selected"]),
        ("CC24_308a_6", "Significant force to fight Russia", ["selected"]),
        ("CC24_308a_7", "Negotiate a peace accord", ["selected"]),
        ("CC24_308a_8", "Rebuilding aid after the war", ["selected"])]),
    ("Israel and Gaza (share selecting)", [
        ("CC24_308b_2", "Food, medicine and aid to affected communities", ["selected"]),
        ("CC24_308b_3", "Arms to Israel", ["selected"]),
        ("CC24_308b_4", "Arms to Hamas", ["selected"]),
        ("CC24_308b_5", "Navy and troops to prevent escalation", ["selected"]),
        ("CC24_308b_6", "Non-combat military staff to Israel", ["selected"]),
        ("CC24_308b_7", "Non-combat military staff to Gaza", ["selected"]),
        ("CC24_308b_8", "Negotiate a peace settlement", ["selected"]),
        ("CC24_308b_9", "Rebuilding aid after the war", ["selected"])]),
]

LOW_INC = ['Less than $10,000', '$10,000 - $19,999', '$20,000 - $29,999', '$30,000 - $39,999', '$40,000 - $49,999']
HIGH_INC = ['$100,000 - $119,999', '$120,000 - $149,999', '$150,000 - $199,999', '$200,000 - $249,999',
            '$250,000 - $349,999', '$350,000 - $499,999', '$500,000 or more']


def demo_rows(m):
    """(section, label, indicator, answered) per demographic row; indicator/answered are boolean Series."""
    s = {c: m[c].astype(str) for c in m.columns}
    age = 2024 - m.birthyr.astype(float)
    has = lambda c, drop=("nan",): ~s[c].isin(drop)
    inc_ok = has("faminc_new", ("nan", "Prefer not to say"))
    sex_ok = has("sexuality", ("nan", "Prefer not to say"))
    inv_ok = has("investor", ("nan", "Not asked"))
    rows = [
        ("Age and gender", "Under 30", age < 30, age.notna()),
        ("Age and gender", "30 to 44", (age >= 30) & (age < 45), age.notna()),
        ("Age and gender", "45 to 64", (age >= 45) & (age < 65), age.notna()),
        ("Age and gender", "65 and over", age >= 65, age.notna()),
        ("Age and gender", "Women", s["gender4"] == "Woman", has("gender4")),
        ("Age and gender", "LGBT (of those answering)", ~s["sexuality"].isin(["Heterosexual / straight"]) & sex_ok, sex_ok),
        ("Race", "White", s["race"] == "White", has("race")),
        ("Race", "Black", s["race"] == "Black", has("race")),
        ("Race", "Hispanic", s["race"] == "Hispanic", has("race")),
        ("Race", "Asian", s["race"] == "Asian", has("race")),
        ("Race", "Other or multiracial", s["race"].isin(["Native American", "Two or more races", "Other", "Middle Eastern"]), has("race")),
        ("Education and income", "High school or less", s["educ"].isin(["No HS", "High school graduate"]), has("educ")),
        ("Education and income", "Bachelor's degree or more", s["educ"].isin(["4-year", "Post-grad"]), has("educ")),
        ("Education and income", "Family income under $50k", s["faminc_new"].isin(LOW_INC), inc_ok),
        ("Education and income", "Family income $100k or more", s["faminc_new"].isin(HIGH_INC), inc_ok),
        ("Education and income", "Owns stock", s["investor"] == "Yes", inv_ok),
        ("Household and work", "Children under 18 at home", s["child18"] == "Yes", has("child18")),
        ("Household and work", "Married or partnered", s["marstat"].isin(["Married", "Domestic / civil partnership"]), has("marstat")),
        ("Household and work", "Never married", s["marstat"] == "Never married", has("marstat")),
        ("Household and work", "Works full-time", s["employ"] == "Full-time", has("employ")),
        ("Household and work", "Retired", s["employ"] == "Retired", has("employ")),
        ("Household and work", "Unemployed or laid off", s["employ"].isin(["Unemployed", "Temporarily laid off"]), has("employ")),
        ("Household and work", "Union member now", s["union"].str.startswith("Yes"), has("union")),
        ("Household and work", "Owns home", s["ownhome"] == "Own", has("ownhome")),
        ("Place", "City", s["urbancity"] == "City", has("urbancity")),
        ("Place", "Suburb", s["urbancity"] == "Suburb", has("urbancity")),
        ("Place", "Town", s["urbancity"] == "Town", has("urbancity")),
        ("Place", "Rural area", s["urbancity"] == "Rural area", has("urbancity")),
        ("Place", "City, family income under $50k", (s["urbancity"] == "City") & s["faminc_new"].isin(LOW_INC), inc_ok & has("urbancity")),
        ("Place", "Northeast", s["region"] == "Northeast", has("region")),
        ("Place", "Midwest", s["region"] == "Midwest", has("region")),
        ("Place", "South", s["region"] == "South", has("region")),
        ("Place", "West", s["region"] == "West", has("region")),
        ("Religious tradition", "Protestant", s["religpew"] == "Protestant", has("religpew")),
        ("Religious tradition", "Catholic", s["religpew"] == "Roman Catholic", has("religpew")),
        ("Religious tradition", "Mormon", s["religpew"] == "Mormon", has("religpew")),
        ("Religious tradition", "Jewish", s["religpew"] == "Jewish", has("religpew")),
        ("Religious tradition", "Muslim, Buddhist or Hindu", s["religpew"].isin(["Muslim", "Buddhist", "Hindu"]), has("religpew")),
        ("Religious tradition", "Atheist or agnostic", s["religpew"].isin(["Atheist", "Agnostic"]), has("religpew")),
        ("Religious tradition", "Nothing in particular", s["religpew"] == "Nothing in particular", has("religpew")),
        ("Party and vote (context)", "Democrat", s["pid3"] == "Democrat", has("pid3", ("nan", "Not sure"))),
        ("Party and vote (context)", "Republican", s["pid3"] == "Republican", has("pid3", ("nan", "Not sure"))),
        ("Party and vote (context)", "Independent or other", s["pid3"].isin(["Independent", "Other"]), has("pid3", ("nan", "Not sure"))),
        ("Party and vote (context)", "Liberal or very liberal", s["ideo5"].isin(["Very liberal", "Liberal"]), has("ideo5", ("nan", "Not sure"))),
        ("Party and vote (context)", "Moderate", s["ideo5"] == "Moderate", has("ideo5", ("nan", "Not sure"))),
        ("Party and vote (context)", "Conservative or very conservative", s["ideo5"].isin(["Conservative", "Very conservative"]), has("ideo5", ("nan", "Not sure"))),
        ("Party and vote (context)", "Voted Harris", s["CC24_410"] == "Kamala Harris", has("CC24_410")),
        ("Party and vote (context)", "Voted Trump", s["CC24_410"] == "Donald Trump", has("CC24_410")),
        ("Party and vote (context)", "Voted third party", s["CC24_410"].isin(["Robert F. Kennedy, Jr.", "Jill Stein", "Cornel West", "Chase Oliver", "Other"]), has("CC24_410")),
        ("Party and vote (context)", "Did not vote for president", s["CC24_410"] == "Did not vote for President", has("CC24_410")),
    ]
    return rows


def seriate(M, metric):
    """Order rows of M so similar rows sit together: average linkage, optimal leaf ordering."""
    if len(M) < 3:
        return list(range(len(M)))
    d = np.nan_to_num(pdist(M, metric), nan=1.0)
    return leaves_list(optimal_leaf_ordering(linkage(d, "average"), d)).tolist()


def wshare(ind, ok, gm, w):
    m = gm & ok
    return float(np.average(ind[m].astype(float), weights=w[m]) * 100) if m.any() else np.nan


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # new clusters
    src = rl.OUT / ("stage_c_v2" if V2 else "four_dim")
    S = pd.read_csv(src / "scores.csv")
    z = np.load(src / "labels.npz")
    lab, _, _ = ld.modal_solution(list(zip(range(42, 62), z[f"{CAP}_seed"], z[f"{CAP}_seed_bounds"])))
    new = pd.Series([f"C{k}" for k in lab], index=S.caseid.values)
    # production parties
    fs = pd.read_csv(rl.ROOT / "data/processed/efa_factor_scores.csv")
    typ = pd.read_csv(rl.ROOT / "data/processed/typology_cluster_assignments.csv", usecols=["cluster"])
    assert len(fs) == len(typ)
    prod = pd.Series(typ.cluster.map(rr.pc.CLUSTER_TO_PARTY).values, index=fs.caseid.values)

    items = list(dict.fromkeys(it for _, rows in TOPICS for it, _, _ in rows))
    demo_cols = ["birthyr", "gender4", "sexuality", "race", "educ", "faminc_new", "investor", "child18", "marstat",
                 "employ", "union", "ownhome", "urbancity", "region", "religpew", "pid3", "ideo5", "CC24_410"]
    meta = pd.read_stata(rl.eu.CES_PATH, columns=["caseid", "commonpostweight"], convert_categoricals=False)
    lab_df = pd.read_stata(rl.eu.CES_PATH, columns=items + demo_cols, convert_categoricals=True)
    lab_df.insert(0, "caseid", meta.caseid.values)
    lab_df["w"] = pd.to_numeric(meta.commonpostweight, errors="coerce").values
    keep = lab_df.caseid.isin(set(new.index) | set(prod.index))
    D = lab_df[keep].set_index("caseid")
    D["prod"] = prod.reindex(D.index).values
    D["new"] = new.reindex(D.index).values
    w = D.w.values
    print(f"union of both samples: {len(D):,}; production {D['prod'].notna().sum():,}, new {D['new'].notna().sum():,}, "
          f"both {(D['prod'].notna() & D['new'].notna()).sum():,}")

    # factors, oriented so high = the name
    F = pd.DataFrame(index=D.index)
    for c, name in [("FS_F1", "P: Security & Order"), ("FS_F2", "P: Institutional Distrust (elections)"),
                    ("FS_F3", "P: Government Distrust"), ("FS_F4", "P: Religious Traditionalism"),
                    ("FS_F5", "P: Populist Conservatism")]:
        F[name] = fs.set_index("caseid")[c].reindex(D.index).values
    new_names = ([("SO", "N: Security & Order"), ("TR", "N: Distrust of government"), ("RT", "N: Cultural conservatism"),
                  ("PC", "N: Economic right")] if V2 else
                 [("SO", "N: Security & Order"), ("TR", "N: Distrust of elections and government"),
                  ("RT", "N: Religious Traditionalism"), ("PC", "N: Populist Conservatism")])
    for c, name in new_names:
        F[name] = S.set_index("caseid")[c].reindex(D.index).values
    anchor = {"Security & Order": ("CC24_323b", ["Support"]), "Distrust": ("CC24_423", ["Not very much", "None at all"]), "Distrust of elections": ("CC24_423", ["Not very much", "None at all"]),
              "Institutional Distrust": ("CC24_421_1", ["Somewhat disagree", "Strongly disagree"]),
              "Religious": ("pew_churatd", ["More than once a week", "Once a week"]),
              "Populist": ("CC24_321b", ["Support"]),
              "Cultural": ("CC24_445b", ["Agree", "Strongly agree", "Somewhat agree"]), "Economic right": ("CC24_328e", ["Oppose"])}
    for col in F.columns:
        key = next(k for k in ["Institutional Distrust", "Security & Order", "Religious", "Populist", "Cultural", "Economic right", "Distrust of elections", "Distrust"] if k in col)
        it, ans = anchor[key]
        x = D[it].astype(str)
        ok = (D[it].notna() & F[col].notna()).values
        r = np.corrcoef(F[col].values[ok], x.isin(ans).values[ok].astype(float))[0, 1]
        if r < 0:
            F[col] = -F[col]
        v = F[col].values
        okv = ~np.isnan(v)
        mu = np.average(v[okv], weights=w[okv])
        sd = np.sqrt(np.average((v[okv] - mu) ** 2, weights=w[okv]))
        F[col] = (v - mu) / sd
        print(f"{col}: r with {it} {r:+.2f} -> {'flipped' if r < 0 else 'kept'}")

    prod_groups = [p for p in PROD_ORDER if (D["prod"] == p).any()]
    xw = pd.crosstab(D["new"], D["prod"], values=D.w, aggfunc="sum").fillna(0)
    lead = {c: xw.loc[c].idxmax() for c in xw.index}
    new_groups = sorted(xw.index, key=lambda c: (PROD_ORDER.index(lead[c]), -xw.loc[c].max() / xw.loc[c].sum()))
    if V2:
        letter = {c: "ABCDEFGHIJ"[i] for i, c in enumerate(new_groups)}
        # researcher's names (listwise_check DECISIONS.md 2026-11-04); the letter keeps ids distinct from production codes
        if CAP == 9:
            NAME9 = dict(zip("ABCDEFGHI", ["CON", "NAT", "POP", "STY", "LBR", "CUP", "OAO", "PRG", "DSA"]))
            letter = {c: f"{NAME9[l]} ({l})" for c, l in letter.items()}
        D["new"] = D["new"].map(letter)
        xw = xw.rename(index=letter)
        new_groups = [letter[c] for c in new_groups]
        inv = {v: k for k, v in letter.items()}
        pd.DataFrame([{"letter": l[-2] if l.endswith(")") else l, "label": l, "cluster": int(inv[l][1:])} for l in new_groups]).to_csv(OUT / "letters.csv", index=False)
    groups = [("prod", g) for g in prod_groups] + [("new", g) for g in new_groups] + [("all", "Everyone")]
    masks = {g: (D[k] == g).values if k != "all" else np.ones(len(D), bool) for k, g in groups}

    def size(k, g):
        base = D[k].notna().values if k != "all" else np.ones(len(D), bool)
        return float(w[masks[g] & base].sum() / w[base].sum() * 100)

    gmeta = [{"key": k, "id": g, "share": round(size(k, g) if k != "all" else 100, 1),
              "n": int(masks[g].sum()),
              "lead": (", ".join(f"{p} {v:.0f}%" for p, v in (xw.loc[g] / xw.loc[g].sum() * 100).sort_values(ascending=False).items() if v >= 15)
                       if k == "new" else "")} for k, g in groups]

    fac = pd.DataFrame({g: [float(np.average(F[c].values[masks[g] & F[c].notna().values],
                                             weights=w[masks[g] & F[c].notna().values])) for c in F.columns]
                        for _, g in groups}, index=F.columns)
    fac.round(3).to_csv(OUT / "factors.csv")

    # closest production party by position on the four new dimensions (Euclidean, SD units)
    ndims = [c for c in F.columns if c.startswith("N: ")]
    for gm in gmeta:
        if gm["key"] != "new":
            continue
        g = gm["id"]
        d = sorted((float(np.sqrt(((fac.loc[ndims, g] - fac.loc[ndims, q]) ** 2).sum())), q) for q in prod_groups)
        tot = xw.loc[g].sum()
        gm["near"] = [{"id": q, "dist": round(dd, 2), "from": round(float(xw.loc[g, q] / tot * 100), 1)} for dd, q in d[:3]]
    pd.DataFrame([{"new": gm["id"], "share": gm["share"], **{f"near{i + 1}": n["id"] for i, n in enumerate(gm["near"])},
                   "dist1": gm["near"][0]["dist"], "dist2": gm["near"][1]["dist"], "from_near1": gm["near"][0]["from"]}
                  for gm in gmeta if gm["key"] == "new"]).to_csv(OUT / "pairs.csv", index=False)

    new_items = set(pd.read_csv((src / "loadings.csv") if V2 else (rl.OUT / "stage_c" / "pool69_loadings_k5.csv"), index_col=0).index)
    pool = pd.read_csv(rl.ROOT / "analysis/efa/ces_item_pool.csv").set_index("item_id")
    pol_rows = []
    for topic, rows in TOPICS:
        for it, label, ans in rows:
            x = D[it].astype(str)
            ok = D[it].notna().values
            ind = x.isin(ans).values
            pol_rows.append({"topic": topic, "item": it, "label": label,
                             "prod24": bool(pool.production_24.get(it, False)), "new30": it in new_items,
                             **{g: round(wshare(ind, ok, masks[g], w), 1) for _, g in groups}})
    pol = pd.DataFrame(pol_rows)
    pol.to_csv(OUT / "policy.csv", index=False)

    dem_rows = []
    for sec, label, ind, ok in demo_rows(D[demo_cols]):
        ind, ok = ind.fillna(False).values.astype(bool), ok.values.astype(bool)
        dem_rows.append({"section": sec, "label": label, **{g: round(wshare(ind, ok, masks[g], w), 1) for _, g in groups}})
    age = 2024 - D.birthyr.astype(float).values
    dem_rows.insert(0, {"section": "Age and gender", "label": "Median age", "median": True,
                        **{g: float(pd.Series(age[masks[g]]).repeat(1).median()) for _, g in groups}})
    dem = pd.DataFrame(dem_rows)
    dem.drop(columns="median").to_csv(OUT / "demographics.csv", index=False)

    rows_pct = (xw.div(xw.sum(axis=1), axis=0) * 100).loc[new_groups, prod_groups]
    both = D["prod"].notna() & D["new"].notna()
    cols_pct = (xw.div(xw.sum(axis=0), axis=1) * 100).loc[new_groups, prod_groups]
    outside = D[D["new"].notna() & D["prod"].isna()].groupby("new").w.sum() / D[D["new"].notna()].groupby("new").w.sum() * 100
    rows_pct.round(1).to_csv(OUT / "crosswalk_rows.csv")
    cols_pct.round(1).to_csv(OUT / "crosswalk_cols.csv")
    print(f"crosswalk on {both.sum():,} respondents in both samples")

    # similarity order. Columns: groups by their policy profile (each item z-scored across groups), one order for
    # every table. Rows: measures by the shape of their gaps from everyone (correlation distance); party and vote
    # rows stay last, outside the sort.
    gids = [g for k, g in groups if k != "all"]
    P = pol[gids].values
    Pz = (P - np.nanmean(P, axis=1, keepdims=True)) / (np.nanstd(P, axis=1, keepdims=True) + 1e-9)
    col_order = [gids[i] for i in seriate(np.nan_to_num(Pz.T), "euclidean")]
    right = "N: Economic right" if V2 else "N: Populist Conservatism"
    if fac.loc[right, col_order[0]] < fac.loc[right, col_order[-1]]:
        col_order = col_order[::-1]
    pol_order = seriate(np.nan_to_num(P - pol["Everyone"].values[:, None]), "correlation")
    ctx = (dem.section == "Party and vote (context)").values
    main_idx = np.where(~ctx)[0]
    Dm = dem[gids].values[main_idx].astype(float)
    dem_order = [int(main_idx[i]) for i in seriate(np.nan_to_num(Dm - dem["Everyone"].values[main_idx, None]), "correlation")] \
        + [int(i) for i in np.where(ctx)[0]]
    fac_order = seriate(fac[gids].values, "correlation")
    print("column order by similarity:", " ".join(col_order))
    Zc = pd.DataFrame(np.nan_to_num(Pz), columns=gids)
    for gm in gmeta:
        if gm["key"] == "new":
            d = {q: float(np.sqrt(((Zc[gm["id"]] - Zc[q]) ** 2).mean())) for q in prod_groups}
            gm["near_pol"] = min(d, key=d.get)
            tot = xw.loc[gm["id"]].sum()
            fd_ = {q: float(np.sqrt(((fac.loc[ndims, gm["id"]] - fac.loc[ndims, q]) ** 2).sum())) for q in prod_groups}
            gm["cousins"] = [{"id": q, "pol": round(d[q], 2), "fac": round(fd_[q], 2), "from": round(float(xw.loc[gm["id"], q] / tot * 100), 1)}
                             for q in sorted(d, key=d.get)[:3]]
    pairs = pd.read_csv(OUT / "pairs.csv")
    pairs["nearest_by_policy"] = pairs.new.map({gm["id"]: gm.get("near_pol") for gm in gmeta})
    pairs.to_csv(OUT / "pairs.csv", index=False)
    print(pairs[["new", "near1", "nearest_by_policy"]].to_string(index=False))

    data = {
        "col_order": col_order, "row_order": {"policy": pol_order, "demo": dem_order, "factors": fac_order},
        "groups": gmeta,
        "factors": [{"label": c, "values": {g: round(fac.loc[c, g], 2) for _, g in groups}} for c in F.columns],
        "policy": pol.to_dict(orient="records"),
        "demo": [{k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in r.items()} for r in dem.to_dict(orient="records")],
        "xrows": {"rows": new_groups, "cols": prod_groups, "v": rows_pct.round(1).values.tolist(),
                  "outside": [round(float(outside.get(g, 0)), 1) for g in new_groups]},
        "xcols": {"rows": new_groups, "cols": prod_groups, "v": cols_pct.round(1).values.tolist()},
        "meta": {"new_n": len(new_groups), "word": {9: "nine", 10: "ten"}.get(len(new_groups), str(len(new_groups))),
                 "n_items": len(new_items), "v2": V2},
        "n": {"union": int(len(D)), "prod": int(D["prod"].notna().sum()), "new": int(D["new"].notna().sum()),
              "both": int(both.sum())},
    }
    html = (Path(__file__).with_name("compare_typologies_template.html").read_text()
            .replace("/*TOKENS*/", TOKENS.read_text())
            .replace("/*DATA*/", json.dumps(data, allow_nan=False)))
    (OUT / "index.html").write_text(html)
    print(f"wrote {OUT / 'index.html'}")


if __name__ == "__main__":
    main()
