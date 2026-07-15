# Electoral systems and polarization — a pressure test

**Question.** Do proportional systems produce less political polarization than first-past-the-post,
especially in the English-speaking world?

**One-paragraph answer.** It depends almost entirely on *which polarization you measure*, and the
expert and citizen measures are only weakly correlated (r ≈ +0.37 for expert vs citizen coldness;
+0.21 for expert vs the in/out gap), so the honest headline is **measurement-dependent**:
- On **expert-coded** societal polarization (V-Dem), PR/consensus institutions are associated with
  **less** polarization — the thesis holds, and matches the peer-reviewed literature.
- On **citizen-survey** affective polarization (CSES), it depends on the sub-measure: the standard
  **in/out gap shows nothing**, but **out-group coldness** — the better match for "do voters dislike
  the other side" — shows FPTP **consistently colder** (up to **+0.56, 97% posterior probability**,
  strengthening as the sample broadens). Specific **mechanisms** (winner–loser satisfaction gap,
  party-size concentration) also support the consensus-democracy story.
- Everywhere, the effect is **confounded** with anglophone/common-law heritage and country size,
  and rests on **few FPTP countries** — so it is directional evidence, not proof.

---

## 0. Measures and universes (definitions — stated once, used throughout)

**Outcome measures.**
- **Expert measure (primary for the expert layer):** V-Dem `v2cacamps` — country experts rate how
  far society is split into antagonistic camps that avoid each other in everyday life.
- **Citizen measure (primary for the citizen layer): out-group coldness** = 10 − (vote-share-
  weighted mean like/dislike a partisan gives to *other* parties), from CSES; higher = colder.
  Reported "all targets" and "middle clusters" (raters and targets both left-right ∈ [2,8],
  excluding far-left/far-right); for anglophone countries the two are near-identical.
- **Secondary/contrast citizen measures:** the in/out affect gap (in-party minus out-party warmth,
  the Reiljan/Gidron standard) and the Wagner spread. These are reported for contrast; the in/out
  gap is *null*, which is why coldness is the primary citizen measure here.

**Universes (V-Dem Regimes of the World).**
- **All democracies** = electoral or liberal democracy (`v2x_regime` ≥ 2).
- **Established non-micro** = **liberal democracy** (`v2x_regime` = 3) with population ≥ 1M. This is
  the primary comparable universe (development + shared ties control the composition).
- **Anglosphere non-micro** = US, UK, Canada, Australia, New Zealand, Ireland, South Africa (+ India,
  see below); Malta excluded as a micro-state.

**India — status (a recurring source of confusion, pinned down here).** India was an **electoral
democracy** (`v2x_regime` = 2) 1947–2016, then **electoral autocracy** (= 2) from 2017. It was
**never a liberal democracy**, so it was **never in the established non-micro universe** — it sat in
"all democracies" until 2016 and then dropped out of the democracy samples entirely. It is shown on
the anglophone/quadrant charts (as an anglophone FPTP case) but is excluded from the democracy-
filtered regressions; including it changes nothing.

---

## 1. The crux: two families of measurement

| | Expert-coded (V-Dem) | Citizen survey (CSES) |
|---|---|---|
| What | Experts judge whether "society is split into antagonistic camps" (`v2cacamps`) | Voters' own party like/dislike ratings (0–10) |
| Source | ~3,500 country experts, measurement model | 395,797 respondents, 229 elections, 59 countries, 1996–2021 |
| Measures | societal / "identity-based" polarization | affective: **out-group coldness (primary)** + in/out gap; ideological (L-R spread); satisfaction; efficacy |

**They barely agree.** Across democracies, corr(V-Dem `v2cacamps`, citizen out-group coldness) ≈
**+0.37**; with the in/out gap it is only **+0.21**. Expert coders appear to read elite rhetoric,
media tone and country reputation, so the
expert measure behaves more like *visible/elite* polarization; the survey measure is what voters
actually report feeling. `fig_anglophone_compare.png` ranks the anglophone countries by each measure
(expert vs citizen out-group coldness): Ireland is calmest to experts but middling among its own
voters; New Zealand is low on both; the US and India rank high on both; the UK is middling to experts
but cold among voters. (On the *in/out gap*, by contrast, India would look low — because Indians rate
both their own and other parties coolly; that gap-vs-coldness split is exactly the §3c point.)

## 2. Expert measure: PR → less polarization (holds)

Frequentist and Bayesian, primary universe = established liberal democracies ≥1M people:

| Model | FPTP effect on `v2cacamps` |
|---|---|
| Bivariate (established non-micro) | +0.70 (CI touches 0) |
| Hierarchical Bayesian, adjusted | **+0.22, P(>0) = 0.93** (likely, moderate) |
| Broadened to all democracies | **−0.19 to −0.29 (reverses: FPTP *less* polarized)** |

FPTP is associated with more expert-coded polarization among comparable/established democracies
(~+0.2, 90–93% posterior probability) — but the sign **reverses across all democracies** (FPTP
−0.19 to −0.29 SD, negative even without controls; the raw country-level gap is small, ≈ −0.10, so
this is a modest reversal, not a large effect). The developing democracies that use FPTP are
mostly British-colonial (Africa, Caribbean, South Asia) and score *lower* on V-Dem's "antagonistic
camps," while many high-polarization developing democracies are PR/presidential (Brazil, Latin
America, parts of Eastern Europe). So the expert-measure thesis is **scope-conditional**: it holds
in the established/Western world and flips in the global pool — matching the project's founding
intuition that the relationship muddles once you leave the rich-democracy sphere. The established-
democracy result **agrees with Bernaerts et al. (2023)**, who use the
*same* V-Dem variables (`v2cacamps` + `v2smpolsoc`) and find PR electoral systems, multiparty
coalitions, and federalism → lower polarization. So on this measure, the thesis is well-supported
and in line with the literature. Democracy quality is the single strongest predictor; country size
is a real confounder (larger countries more polarized, and FPTP democracies skew large).

**Presidential/parliamentary control (M_primary, `analyze_bayes.py`).** The primary model also
carries a `presidential` term (V-Dem `v2ex_elechos` × `v2exhoshog`; correctly treats Ireland's and
Germany's ceremonial presidents as non-presidential). Its coefficient is **+0.337, 94% CI
[−0.49, +1.18], P(>0) = 0.775 (inconclusive)** — directionally "presidential systems more
polarized," consistent with the duopoly mechanism, but not decisive. **Identification caveat:** in
this universe the United States is essentially the *only* established liberal democracy that is both
FPTP *and* presidential (UK/Canada/India are FPTP-parliamentary; the presidential PR cases are
Latin American). So FPTP and presidentialism cannot be statistically separated here — the US is the
single cell where they coincide. Treat the "FPTP + presidential → complete two-party duopoly" claim
as mechanism/logic plus the UK/Canada contrast, not as a cleanly-identified coefficient.

## 3. Citizen affective measure: null on the standard gap, positive on coldness (the primary here)

The primary citizen measure is **out-group coldness** (§3c); the in/out affect gap is the standard
literature measure and is reported here as a contrast. They disagree, and the disagreement is the
point — so read 3a (the null contrast) as setup for 3c (the primary result).

**3a. The standard in/out gap is null.** Party in/out affective gap (Reiljan/Gidron measure): FPTP
effect ≈ 0 (P ≈ 0.5) under hierarchical pooling, in both the established and all-democracy universes.
Validity check passes — the measure puts the **US in the upper-middle of the distribution (24th of
59; Turkey, Bulgaria, Ukraine, Hungary, Slovakia, Greece and others score higher)** and reproduces
the canonical Reiljan/Wagner ranking (Southern/Eastern Europe high; NW Europe and East Asia low), so
this is a real null, not a broken pipeline. The US is exceptional in *trend*, **not level** — many
PR democracies are as or more affectively polarized. (Correction on audit: an earlier draft claimed
the measure put the "US clearly highest"; it does not — the US is mid-pack on the in/out gap.)

**3b. Out-group hostility is distance-driven, not fringe-stigma.** In the dyadic (rater→target)
data, ideological **distance** dominates (−1.13, tight CI) while target **extremeness** is null net
of distance (−0.04). Extreme parties get colder ratings only because they sit far from everyone —
genuine polarization, not irrational fringe-hatred. But shared dislike of fringe parties is partly
*consensus* (a cordon sanitaire), which dilutes the electoral-system signal in the raw measure.

**3c. The choice of affective sub-measure is decisive — and out-group *coldness* supports the
thesis.** The in/out gap subtracts in-party warmth, which hides real hostility where in-party
attachment is also low (e.g. India: cold to opponents *and* lukewarm to its own party → low gap
but high coldness). Out-group **coldness** (10 − out-party warmth) directly measures "how much do I
dislike the other side" — the better match for the thesis. Hierarchical Bayesian, FPTP effect
(positive = FPTP colder):

| Outcome | Established non-micro | All democracies |
|---|---|---|
| in/out gap | ≈0.00 (P 0.51) — null | ≈0.01 (P 0.53) — null |
| **coldness, all targets** | +0.27 (P 0.84) | +0.36 (P 0.91) |
| **coldness, middle clusters** | +0.43 (P 0.88) | **+0.56 (P 0.97)** |

On coldness, FPTP is colder in **every** specification (vs a flat null on the gap), the effect
**strengthens** slightly as the sample broadens (the FPTP country actually added going from the
established to the all-democracy universe is **Kenya**, which is high-coldness — **India is *not* in
either citizen regression**: its only CSES wave was 2019, when it was an electoral autocracy and so
sits outside both democracy tiers; see §0), and the strongest raw-scale estimate (middle clusters,
all democracies) is **+0.56 points, 97% posterior probability colder** (94% CI grazes zero). This is
the clearest citizen-level signal for the thesis in the project — on the sub-measure that best
matches "do voters dislike the other side." For anglophone countries the all-targets and middle-
cluster versions are near-identical (they have almost no fringe parties); the middle filter only
bites in the broader sample.

Caveat: it remains measure-dependent (the equally-standard in/out gap gave nothing), rests on 5–6
FPTP countries, and the CIs graze zero — so "likely/clearly" is by posterior probability, not a
clean interval.

**Robustness (added on audit — `analyze_coldness_robustness.py`).** Two problems in the headline:
(1) "FPTP" was V-Dem *majoritarian* (`v2elparlel==0`), which mis-labels Australia's AV and France's
two-round runoff as FPTP; (2) the models omit a heritage control despite FPTP ↔ common-law r ≈ 0.6.
Re-running with a `common_law` covariate **and** the treatment restricted to genuine single-member-
plurality FPTP (US/UK/Canada/Kenya) gives **+0.30 to +0.44 points, P(colder) ≈ 0.84–0.87
("possibly/likely," not "clearly")**, dropping to *inconclusive* in the established-only universe.
The heritage control does **not** erase the effect — it slightly *raises* the point estimate,
because the anglophone PR cases (Ireland STV, NZ MMP) are themselves cold. But the honest citizen-
level headline is **directional, not decisive**. Note the discordant internal control: **Canada**
has the same FPTP + common-law heritage as the US yet is as cold-neutral as PR Ireland/NZ (6.48 vs
US 6.96), pointing at US-specific two-party *completeness* rather than FPTP per se — consistent with
the "duopoly" mechanism (§4), not a blanket electoral-rule effect.

**Party count vs duopoly concentration (added on audit — `analyze_enp_mediation.py`).** The two-party
mechanism must be operationalized as *duopoly concentration* (top-2 vote share), **not** the raw
effective number of parties (ENP). ENP conflates a *balanced* two-party system (US, top-2 ≈ 0.99)
with a *dominant-party* system (South Africa, ANC ≈ 64%) — structurally different animals. Two
consequences: (1) **South Africa is affectively polarized** (coldness 7.04; in/out gap 8th of 59)
*despite* not being a balanced duopoly, so affective polarization has more than one structural route;
(2) in mediation, "FPTP → fewer parties → polarization" does **not** hold via raw ENP (on the expert
measure, more parties = more 'antagonistic camps', so ENP runs the *wrong* way), but **FPTP → higher
top-2 concentration → citizen coldness** runs the right way (a = +0.72 P0.96, b = +0.11 P0.87,
indirect +0.08 P0.84) — a small but correctly-signed indirect effect. Most of the FPTP–coldness link
is still direct/US-specific. Hudde-style **affective fractionalization** (out-group coldness weighted
by encounter probability, `analyze_affective_fractionalization.py`) puts the US at the extreme on the
*combination* that matters: near-total duopoly (top-2 ≈ 0.99, lowest ENP) × among the coldest
per-cross-party-encounter ratings in the sample (≈ 8/10, 4th of 48).

## 4. Mechanisms that hold at the citizen level

- **Winner–loser satisfaction gap** (Anderson & Guillory's mechanism, cited by Bernaerts et al.):
  **likely higher under FPTP** (Bayesian +0.17, P = 0.93). Majoritarian systems leave electoral
  *losers* relatively less satisfied — the inclusion channel — even though overall satisfaction is
  *higher* under FPTP (clear-winner effect).
- **Party-size mediation (party level):** FPTP → bigger parties (a = +0.42) → bigger-party supporters
  are colder to opponents (b = −0.28, the tightest relationship in the project) → small indirect
  effect (−0.12). So at the party level, FPTP relates to hostility weakly and *indirectly*, by
  concentrating votes into large parties.
- **Duopoly concentration (country level):** FPTP concentrates the vote into two big parties
  (a = +0.72, P 0.96); higher top-2 concentration relates to colder voters (b = +0.11, P 0.87), a
  small positive indirect effect (+0.08). Raw *party count* (ENP) does **not** mediate — the
  *balanced-duopoly* structure does, which is why the US (top-2 ≈ 0.99) is distinctive while
  dominant-party South Africa reaches high coldness by a different route (§3c).
- **Elite quasi-experiment (New Zealand 1996):** the one within-country natural experiment. Nemoto &
  Franco de Campos Pinto (2018) sentiment-code all NZ parliamentary speeches 1987–2016 and find
  hostility fell after the FPTP→MMP switch, with a structural break near 1996 and cohort evidence
  that *incumbent* MPs moderated (institutional, not compositional). Suggestive, not dispositive —
  but direct evidence that changing the electoral architecture lowered elite hostility.
- **Ideological extremity → out-group hostility** (robust): extreme parties' supporters are colder,
  and left parties slightly colder than right (net of extremity).

## 5. What you can and cannot say

**Defensible:**
- "On expert assessments of societal polarization, proportional/consensus democracies are less
  polarized — and the English-speaking PR cases (Ireland, NZ) fit that clearly." (§2, matches
  Bernaerts et al.)
- "On the measure that best matches the thesis — how coldly voters rate opposing parties (out-group
  coldness) — FPTP systems are directionally colder (**+0.3 to +0.44, ~85% posterior**, after a
  common-law control and restricting to genuine single-member-plurality FPTP — directional, not
  decisive). The operative channel is *balanced-duopoly concentration*, not party count, so the
  effect is largely US-specific; majoritarian systems also leave electoral losers less satisfied."
  (§3c, §4)

**Not defensible:**
- That FPTP *causes* polarization (this is cross-country association, few FPTP cases); that the
  finding is measure-robust (the standard in/out gap is null even though coldness is positive); that
  the US is uniquely polarized in level; or that any of this is cleanly separable from
  anglophone/common-law heritage and country size.

**Bottom line:** the thesis is strongest as a claim about *institutional/elite* polarization and
about *mechanisms* (loser inclusion, party concentration), and weakest as a blunt claim about mass
mutual dislike. State which polarization you mean, and the argument is defensible.

## 6. Caveats

- Few FPTP democracies — **4** in the established non-micro universe, **5** in the anglosphere, **19**
  across all democracies (vs 22 / 3 / 66 PR-or-other). The imbalance doesn't *bias* the coefficient
  (a group-mean difference is unbiased regardless of ratio); it limits *precision*, which is why the
  effects are directional with wide, zero-grazing intervals. Country random intercepts prevent
  pseudo-replication, so uncertainty honestly reflects the country count, not the row count.
- Confounding: FPTP ↔ anglophone (r ≈ 0.8 in the established set) ↔ common-law heritage ↔ large
  population are inseparable in the real-world sample.
- Expert vs survey measures correlate only +0.24 — pick the construct deliberately.
- Electoral systems are near time-invariant → identification is cross-country; country fixed effects
  are unusable.
- CSES: gated behind free registration (`polarization/cses/`, not auto-downloaded); the winner–loser
  gap can't be computed for the US (presidential cabinet not coded as party portfolios).

## 7. Reproduce

```
python polarization/src/acquire.py           # V-Dem + QoG (idempotent)
python polarization/src/build_panel.py        # country-year panel
python polarization/src/analyze.py            # expert-measure freq. tiered analysis + figures
python polarization/src/analyze_bayes.py      # expert-measure hierarchical Bayesian
python polarization/src/build_affpol.py        # CSES affective polarization (in/out API + spread)
python polarization/src/analyze_affpol.py      # affective vs expert + electoral system
python polarization/src/analyze_cses_bayes.py  # Bayesian across all CSES outcomes
python polarization/src/build_party_affect.py  # party-level out-group sentiment + ideology
python polarization/src/analyze_party_mediation.py  # broaden FPTP N + size mediation
python polarization/src/build_dyadic.py        # rater->target decomposition (distance vs fringe)
python polarization/src/analyze_middle_clusters.py  # middle-cluster hostility
python polarization/src/analyze_coldness_bayes.py   # out-group COLDNESS (all + middle) Bayesian
python polarization/src/analyze_coldness_robustness.py  # coldness + common-law control + strict FPTP
python polarization/src/analyze_enp_mediation.py    # FPTP -> ENP / top-2 concentration -> polarization
python polarization/src/analyze_affective_fractionalization.py  # Hudde-style AF (encounter-weighted)
python polarization/src/viz_anglophone.py      # fig_anglophone_compare.png
python polarization/src/viz_fptp_forest.py     # fig_fptp_across_measures.png
python polarization/src/viz_quadrants.py       # fig_polarization_quadrants.png
python polarization/src/viz_essay_panels.py    # fig_essay_panels.png (primary essay figure)
```

See `outputs/README.md` for a full index of which script writes which figure/table, and
`outputs/archive/` for superseded early outputs. Key figures in `outputs/`:
- `fig_essay_panels.png` — **primary essay figure.** (A) US is the lone polarized case among
  English-speaking democracies; (B) duopoly concentration tracks V-Dem polarization within the
  anglosphere (r=0.88) but not across all democracies (r=0.08).
- `fig_anglophone_compare.png` — anglophone countries, expert (V-Dem) vs citizen out-group
  coldness; the ranking flips by measure.
- `fig_fptp_across_measures.png` — FPTP effect (SD units, 94% CI) across all measures and both
  universes; shows the effect is null on the in/out gap, positive on coldness, and depends on
  the measure.
- `fig_polarization_quadrants.png` — two-layer typology (expert behavioral × citizen affective),
  split at absolute anchors (V-Dem = 0 global average; coldness = 7 = voters rate opponents ≤3/10).
  Four labeled quadrants: pernicious (US, India, South Africa, Poland) / contained rivalry (UK,
  Greece) / expert-perceived / depolarized (Ireland, NZ, Australia, Canada). Every democracy is
  net-cold to opponents (all ≥5), so no country sits in a "net-warm" region.
