# EFA Factor Reference

Detailed reference for the 5-factor Exploratory Factor Analysis (EFA) solution underlying the political typology.

**Solution:** 24-item, oblique rotation (Promax), k=5 factors
**Sample:** N=45,707 (2024 CES, listwise deletion)
**Dropped item:** CC24_340a — near-Heywood condition (λ=−0.947); removed from ITEMS_25 to produce final ITEMS_24 set
**Files:** `Claude/analysis/efa/efa_loadings_k5_final.csv`, `Claude/analysis/efa/efa_phi_k5_final.csv`

**Why k=5 (not k=4):** A 4-factor solution yields three clean factors (enforcement; a merged election+government *trust* factor; merged religion+values) plus an **uninterpretable junk factor** — mixed loadings dominated by the homeless post-9/11 surveillance item, soaking up under-extraction leftover. k=5 spends that degree of freedom on a *meaningful* split instead (Electoral Skepticism vs Government Distrust). The trade-off: k=5's Government Distrust barely discriminates parties (η²=0.057) — but a weak-yet-clean dimension (benign ballast) is preferable to a junk dimension that injects incoherent variance into clustering. See **Robustness** below.

---
  ---
  Exact Population Shares

  ┌──────────────────────┬──────────┬────────────┐
  │        Party         │ Weighted │ Unweighted │
  ├──────────────────────┼──────────┼────────────┤
  │ CON (Conservative)   │ 17.74%   │ 17.36%     │
  ├──────────────────────┼──────────┼────────────┤
  │ SD (Social Democrat) │ 14.81%   │ 16.07%     │
  ├──────────────────────┼──────────┼────────────┤
  │ STY (Solidarity)     │ 14.25%   │ 11.68%     │
  ├──────────────────────┼──────────┼────────────┤
  │ POP (Populist)         │ 10.43%   │ 8.76%      │
  ├──────────────────────┼──────────┼────────────┤
  │ CUP (Centrist)       │ 9.35%    │ 8.52%      │
  ├──────────────────────┼──────────┼────────────┤
  │ LIB (Liberal)        │ 8.81%    │ 11.50%     │
  ├──────────────────────┼──────────┼────────────┤
  │ NAT (Nationalist)    │ 8.71%    │ 8.20%      │
  ├──────────────────────┼──────────┼────────────┤
  │ DSA (Dem. Socialist) │ 5.94%    │ 5.83%      │
  ├──────────────────────┼──────────┼────────────┤Z
  │ PRG (Progressive)    │ 4.70%    │ 5.67%      │
  ├──────────────────────┼──────────┼────────────┤
  │ C7 (Blue Dogs)       │ 5.26%    │ 6.42%      │
  └──────────────────────┴──────────┴────────────┘
  ---                                                                                                           
  Factor Rankings by Discriminating Power (η²)                                                                  
                                               
  η² = fraction of each factor's total variance explained by cluster membership. A B/W ratio above 1 means      
  clusters are more spread out than the within-cluster noise — the factor genuinely sorts people into parties.
                                               
  ┌───────────────────────┬───────┬─────────┬──────────────────────────────────────────────────────────────┐
  │        Factor         │  η²   │  B/W    │                        Interpretation                        │
  │                       │       │  ratio  │                                                              │
  ├───────────────────────┼───────┼─────────┼──────────────────────────────────────────────────────────────┤
  │ F5 Populist           │ 0.736 │ 1.67    │ Strongest partisan sorter — clusters are 1.7× wider apart    │
  │ Conservatism          │       │         │ than the within-cluster spread                               │
  ├───────────────────────┼───────┼─────────┼──────────────────────────────────────────────────────────────┤
  │ F1 Security & Order   │ 0.701 │ 1.53    │ Nearly as strong — the main left/right axis                  │
  ├───────────────────────┼───────┼─────────┼──────────────────────────────────────────────────────────────┤
  │ F2 Electoral          │ 0.375 │ 0.775   │ Cross-cutting: within-cluster noise (σ=0.664) is larger than │
  │ Skepticism            │       │         │  between-cluster spread (σ=0.514)                            │
  ├───────────────────────┼───────┼─────────┼──────────────────────────────────────────────────────────────┤
  │ F4 Religious          │ 0.305 │ 0.663   │ Moderate — some party sorting, substantial within-cluster    │
  │ Traditionalism        │       │         │ noise                                                        │
  ├───────────────────────┼───────┼─────────┼──────────────────────────────────────────────────────────────┤
  │ F3 Govt Distrust      │ 0.057 │ 0.246   │ Essentially nothing — confirmed by the EFA docs ("all types  │
  │                       │       │         │ Medium")                                                     │
  └───────────────────────┴───────┴─────────┴──────────────────────────────────────────────────────────────┘

  The η²-derived weights relative to F1 are: F1=1.0, F2=0.54, F3=0.08, F4=0.44, F5=1.05.

## Factor Names & Orientation

| Factor | Name | High Score Means | Low Score Means |
|--------|------|-----------------|-----------------|
| F1 | Security & Order | Pro-law enforcement, pro-border security, pro-surveillance | Civil libertarian, anti-enforcement |
| F2 | Electoral Skepticism | Believes elections are NOT fair; distrusts voting systems | Trusts electoral institutions |
| F3 | Government Distrust | Low trust in federal and state government | Trusts government institutions |
| F4 | Religious Traditionalism | Traditional religious values; conservative on abortion & same-sex marriage | Secular, socially progressive |
| F5 | Populist Conservatism | Populist-right: anti-immigration, fiscal conservatism, racial traditionalism | Progressive-left |

**Sign convention for F5:** Most items load negatively because the survey coded liberal positions as higher numeric values. A negative loading means high F5 predicts the conservative response (lower numeric value).

---

## Factor Intercorrelation Matrix (Phi)

| | F1 | F2 | F3 | F4 | F5 |
|--|----|----|----|----|-----|
| **F1** | 1.00 | +0.02 | −0.04 | **+0.55** | **−0.51** |
| **F2** | +0.02 | 1.00 | **+0.34** | +0.18 | −0.15 |
| **F3** | −0.04 | **+0.34** | 1.00 | +0.03 | −0.27 |
| **F4** | **+0.55** | +0.18 | +0.03 | 1.00 | **−0.55** |
| **F5** | **−0.51** | −0.15 | −0.27 | **−0.55** | 1.00 |

Key relationships:
- **F1↔F4 (+0.55):** Security/order and religious traditionalism cluster together — the "socially conservative" combination
- **F1↔F5 (−0.51):** Security-oriented voters tend to be lower on the populist-conservative axis — enforcement conservatives differ from populist conservatives
- **F4↔F5 (−0.55):** Religious traditionalism and populist conservatism are moderately anti-correlated — NAT types score Very High F5 but only High F4; religious social conservatives aren't always economic populists
- **F2↔F3 (+0.34):** Electoral skepticism and government distrust travel together, but F2 is specifically about election integrity
- **F1↔F2 (+0.02):** Near-orthogonal — security orientation does not predict electoral skepticism

---

## Full Factor Loadings (|loading| > 0.20 shown)

*Positive loading = higher factor score predicts higher variable value. For F5, most conservative items have negative loadings because the survey coded liberal response = higher number.*

### F1 — Security & Order

| Item | Loading | Survey Question |
|------|---------|----------------|
| CC24_321d | +0.734 | Support increasing number of police officers by 10% |
| CC24_323b | +0.705 | Support increasing border patrols on US-Mexico border |
| CC24_340f | +0.664 | Support denying asylum to those seeking it from Central America |
| CC24_321e | +0.653 | Oppose decreasing number of police officers by 10% |
| CC24_340e | +0.493 | Support continuing post-9/11 surveillance programs |
| CC24_323a | +0.319 | Oppose granting legal status to undocumented immigrants |
| CC24_323d | +0.313 | Oppose Dreamer pathway to citizenship |
| CC24_324b | +0.268 | Permit abortion only in rape/incest/life-danger cases |
| CC24_341a | +0.260 | Support extending 2017 Trump tax cuts |

### F2 — Electoral Skepticism

| Item | Loading | Survey Question |
|------|---------|----------------|
| CC24_421_2 | +0.901 | State/local elections NOT run fairly |
| CC24_421_1 | +0.726 | US elections NOT run fairly |
| CC24_424 | +0.380 | Low trust in state government |
| CC24_423 | +0.240 | Low trust in federal government |
| CC24_440c | +0.209 | Women seek to gain power by getting control over men |
| CC24_341a | +0.202 | Support extending 2017 Trump tax cuts |

**Note:** F2 is near-orthogonal to partisan ID (Cramér's V ≈ 0.15). STY (Solidarity), POP (Populist), and DSA all score High on F2 despite being ideologically opposed on F1 and F5 — electoral skepticism cuts across the left-right divide.

### F3 — Government Distrust

| Item | Loading | Survey Question |
|------|---------|----------------|
| CC24_423 | +0.663 | Low trust in federal government |
| CC24_424 | +0.476 | Low trust in state government |
| CC24_340e | −0.319 | Oppose continuing post-9/11 surveillance programs |
| CC24_323a | +0.270 | Oppose granting legal status to undocumented immigrants |
| CC24_323d | +0.225 | Oppose Dreamer pathway to citizenship |
| CC24_440c | −0.219 | Women seek to gain power by getting control over men |
| CC24_440b | −0.208 | Racial problems in the U.S. are rare, isolated situations |
| CC24_303 | +0.203 | Perceive prices as higher (inflation sensitivity) |

**Critical note:** CC24_423 and CC24_424 load on BOTH F2 and F3. The distinction is: F2 = specifically about *election* integrity; F3 = general *institutional* trust. F3 has an unusual ideological mix that doesn't map cleanly to left-right.

**Key finding for coalition analysis:** All 23 winning types score Medium on F3 (range −0.21 to +0.13). The full winning coalition set is mildly above the population mean on government distrust but undifferentiated from each other. F3 does not drive coalition formation.

**Validity re-check (July 2026): F3 is a residual factor, and its sign is misleading.** Re-deriving the relationship from the stored factor scores (repro: `analysis/efa/verify_f3_inversion.py`) shows the factor does not measure what its name implies:

- Across the ten parties, the F3 score correlates **−0.38** with actual government distrust (the raw `govt_trust_imputed` indicator), and **−0.21** at the respondent level. The two *most* government-distrusting parties in the raw data — POP (0.37) and NAT (0.43) — score *lowest* on the F3 factor (both ≈ −0.21). CON, only mid-pack on raw distrust (0.18), scores *highest* among the right parties (+0.11). The factor inverts its own construct: a party's F3 z-score runs opposite to how much it actually distrusts government.
- The real government-distrust signal lives in **F2 (Electoral Skepticism)**, which correlates **+0.84** with raw government distrust across parties. In a weighted regression of raw distrust on all five factor scores, F2's coefficient is **+0.151** (t=68) while F3's is **−0.165** (t=−58).
- Mechanism: the two government-trust items (CC24_423/424) load on both F2 and F3, and F2 — where the party-level variance actually sits — absorbs them. F3's *discriminating* variance instead comes from its culturally-coded cross-loading items (immigration, race, hostile sexism), which already belong to F5/PC. So F3's party ordering tracks a culturally-progressive residual, not distrust, which is why hard-right POP falls below institutionalist CON.

**Consequence:** F3 functions as a **residual / suppressor factor**, not an interpretable substantive dimension. It earns its k=5 slot only by keeping the trust variance split so DPGMM can isolate CUP (see Robustness) — not as a number to display next to a party. The "Government Distrust" label is actively misleading, since a party's F3 score is *negatively* related to its real government distrust; the genuine institutional-distrust axis is F2. When surfacing factors in the UI, F3 should be dropped or explicitly flagged as a non-interpretable residual, and F2 is the axis that should carry the "distrust / anti-establishment" reading.

### F4 — Religious Traditionalism

| Item | Loading | Survey Question |
|------|---------|----------------|
| pew_churatd | +0.688 | Church attendance frequency |
| CC24_325 | +0.688 | Support stricter abortion week limits |
| CC24_340c | +0.651 | Oppose requiring states to recognize same-sex marriages |
| CC24_340b | +0.489 | Oppose federal protections prohibiting abortion restrictions |
| CC24_341d | +0.300 | Oppose infrastructure spending |
| CC24_324b | +0.297 | Permit abortion only in rape/incest/life-danger cases |
| CC24_341c | +0.285 | Oppose allowing $400k+ tax rates to rise |
| CC24_341a | +0.240 | Support extending 2017 Trump tax cuts |
| CC24_303 | +0.219 | Perceive prices as higher |

**Note:** Church attendance (`pew_churatd`) has the joint-highest loading (+0.69) alongside abortion week limits — this is genuinely the *religious values* axis, not just social conservatism generically.

### F5 — Populist Conservatism

| Item | Loading | Survey Question | High F5 → |
|------|---------|----------------|-----------|
| CC24_440b | −0.616 | Racial problems are rare/isolated | Agree (conservative) |
| CC24_321b | −0.557 | Easier concealed-carry permits | Support (pro-gun) |
| CC24_323d | −0.540 | Dreamer pathway to citizenship | Oppose |
| CC24_341c | −0.534 | Allow $400k+ tax rates to rise | Oppose (fiscal conservative) |
| CC24_323a | −0.520 | Legal status for undocumented immigrants | Oppose |
| CC24_440c | −0.437 | Women seek to gain power by getting control over men | Agree (conservative) |
| CC24_341d | −0.365 | Infrastructure spending | Oppose |
| CC24_340e | +0.341 | Post-9/11 surveillance programs | Support |
| CC24_340f | −0.271 | Deny asylum to Central American seekers | Support |
| CC24_341a | −0.238 | Extend 2017 Trump tax cuts | Support |

**Note on negative signs:** The CES coded liberal/progressive positions as higher numeric values. So negative loadings indicate high F5 predicts the *conservative* response. NAT (Nationalist) at +1.51 and POP (Populist) at +0.99 are the most extreme; PRG (Progressive) at −0.99 and LIB (Liberal) at −0.95 are the most progressive.

---

## Winning Coalition Type Scores on All Factors

Sorted by F5 descending (most populist-conservative to most progressive):

| Type | Chamber | F1 SecOrd | F2 ElecSkep | F3 GovtDis | F4 ReligTrad | F5 PopCons |
|------|---------|-----------|-------------|------------|--------------|------------|
| NAT | house | +0.737 | +0.428 | −0.208 | +0.457 | **+1.510** |
| POP | both | +0.202 | +0.759 | −0.206 | +0.147 | +0.990 |
| CON/NAT | senate | +0.752 | +0.198 | −0.045 | +0.336 | +0.966 |
| CON/POP | senate | +0.592 | +0.219 | +0.013 | +0.196 | +0.612 |
| POP/STY | senate | −0.038 | +0.722 | −0.081 | +0.153 | +0.601 |
| STY/POP | senate | −0.154 | +0.704 | −0.019 | +0.157 | +0.411 |
| CON | both | +0.767 | −0.024 | +0.111 | +0.219 | +0.442 |
| CON/CUP | senate | +0.577 | −0.325 | +0.002 | +0.185 | +0.289 |
| CON/STY | senate | +0.258 | +0.263 | +0.120 | +0.196 | +0.230 |
| STY/CON | senate | +0.076 | +0.365 | +0.124 | +0.188 | +0.155 |
| CUP | both | +0.266 | −0.817 | −0.174 | +0.130 | +0.039 |
| CON/SD | senate | +0.236 | −0.027 | +0.102 | −0.035 | −0.011 |
| STY | both | −0.446 | +0.658 | +0.133 | +0.165 | −0.062 |
| SD/CON | senate | +0.153 | −0.028 | +0.101 | −0.074 | −0.081 |
| SD/CUP | senate | −0.122 | −0.369 | −0.023 | −0.141 | −0.305 |
| STY/SD | senate | −0.430 | +0.313 | +0.112 | −0.090 | −0.313 |
| SD/STY | senate | −0.425 | +0.196 | +0.105 | −0.177 | −0.398 |
| SD | both | −0.414 | −0.032 | +0.091 | −0.345 | −0.564 |
| LIB/CUP | senate | −0.171 | −0.773 | −0.121 | −0.142 | −0.554 |
| SD/LIB | senate | −0.438 | −0.381 | +0.004 | −0.334 | −0.753 |
| DSA | house | **−1.303** | +0.504 | +0.076 | −0.387 | −0.874 |
| LIB | both | −0.462 | −0.744 | −0.086 | −0.323 | −0.950 |
| PRG | house | **−1.260** | −0.634 | −0.206 | −0.387 | −0.990 |

---

## Absolute Tier Distribution by Factor

(Thresholds: Very High > +0.75 | High +0.25–+0.75 | Medium −0.25–+0.25 | Low −0.75–−0.25 | Very Low < −0.75)

### F1 — Security & Order
| Tier | Types |
|------|-------|
| Very High | CON (+0.77), CON/NAT (+0.75) |
| High | NAT (+0.74), CON/POP (+0.59), CON/CUP (+0.58), CUP (+0.27), CON/STY (+0.26) |
| Medium | CON/SD (+0.24), POP (+0.20), SD/CON (+0.15), STY/CON (+0.08), POP/STY (−0.04), SD/CUP (−0.12), STY/POP (−0.15), LIB/CUP (−0.17) |
| Low | SD (−0.41), SD/STY (−0.42), STY/SD (−0.43), SD/LIB (−0.44), STY (−0.45), LIB (−0.46) |
| Very Low | PRG (−1.26), DSA (−1.30) |

### F2 — Electoral Skepticism
| Tier | Types |
|------|-------|
| Very High | POP (+0.76) |
| High | POP/STY (+0.72), STY/POP (+0.70), STY (+0.66), DSA (+0.50), NAT (+0.43), STY/CON (+0.36), STY/SD (+0.31), CON/STY (+0.26) |
| Medium | CON/POP (+0.22), CON/NAT (+0.20), SD/STY (+0.20), CON (−0.02), CON/SD (−0.03), SD/CON (−0.03), SD (−0.03) |
| Low | CON/CUP (−0.32), SD/CUP (−0.37), SD/LIB (−0.38), PRG (−0.63), LIB (−0.74) |
| Very Low | LIB/CUP (−0.77), CUP (−0.82) |

### F3 — Government Distrust
| Tier | Types |
|------|-------|
| Very High | *(none)* |
| High | *(none)* |
| Medium | **All 23 types** (range: −0.21 to +0.13) |
| Low | *(none)* |
| Very Low | *(none)* |

### F4 — Religious Traditionalism
| Tier | Types |
|------|-------|
| Very High | *(none)* |
| High | NAT (+0.46), CON/NAT (+0.34) |
| Medium | CON (+0.22) through SD/CON (−0.07) — 16 types |
| Low | LIB (−0.32), SD/LIB (−0.33), SD (−0.34), DSA (−0.39), PRG (−0.39) |
| Very Low | *(none)* |

### F5 — Populist Conservatism
| Tier | Types |
|------|-------|
| Very High | NAT (+1.51), POP (+0.99), CON/NAT (+0.97) |
| High | CON/POP (+0.61), POP/STY (+0.60), CON (+0.44), STY/POP (+0.41), CON/CUP (+0.29) |
| Medium | CON/STY (+0.23) through SD/CON (−0.08) — 6 types |
| Low | SD/CUP (−0.30), STY/SD (−0.31), SD/STY (−0.40), LIB/CUP (−0.55), SD (−0.56) |
| Very Low | SD/LIB (−0.75), DSA (−0.87), LIB (−0.95), PRG (−0.99) |

---

## Cross-Cutting Findings

1. **F3 is non-differentiating** — All winning types cluster in Medium. Government distrust as a raw dimension is shared broadly across the winning coalition space.

2. **F2 is the most cross-cutting** — POP (+0.76), STY (+0.66), and DSA (+0.50) all score High on electoral skepticism despite being maximally opposed on F5. These three parties would align on election-reform legislation despite sharing little else ideologically.

3. **NAT is the outlier on F5** — At +1.51, NAT is a full standard deviation above the next highest type (POP at +0.99). In coalition analysis, NAT forms a distinct bloc on the populist-right pole that no senate blend type fully reaches.

4. **DSA and PRG are near-identical on F4 and F5** — Both score −0.387 on F4 and approximately −0.87/−0.99 on F5. Their main distinction is F1 (DSA: −1.303, PRG: −1.260) and F2 (DSA: +0.504, PRG: −0.634) — DSA distrusts elections; PRG trusts them.

5. **CON and CUP diverge sharply on F2** — CON scores −0.024 (Medium) while CUP scores −0.817 (Very Low). Despite having similar seat counts and both being "right-of-center," they are on opposite sides of the electoral skepticism divide.

---

## Robustness: choice of k and residualization

The production typology rests on three modeling choices that aren't forced by the data alone: **k=5 factors** (parallel analysis was borderline between 4 and 5), **F1-residualization** of the two culture factors (F4, F5) before clustering, and the **DPGMM** itself. Because Government Distrust (F3) has near-zero discriminating power (η²=0.057) and Electoral Skepticism already carries the trust signal, k=4 is a defensible alternative. To check whether the nine parties are real structure or artifacts of these choices, we re-ran the full pipeline (polychoric → PAF → oblimin → Thomson scores → DPGMM) under three variants — **k=5 no-resid, k=4 resid, k=4 no-resid** — and matched each variant's clusters back to the production parties in the common 24-item space.

> Reproduction is approximate: listwise N=45,214 (vs production 45,707 — "Not sure" on the government-trust items mapped to the scale midpoint), oblimin rather than the stored solution, DPGMM stochasticity. Treat magnitudes as indicative; the qualitative survival pattern is stable. Scripts: `analysis/efa/{compare_k4_vs_k5_clustering, cluster_survival_k4_k5, build_cluster_explorer_data}.py`; interactive write-up: `analysis/efa/cluster_explorer.html`.

### What survives

| Party | k=5 no-resid | k=4 resid | k=4 no-resid |
|---|---|---|---|
| SD, STY, POP, CON, NAT | preserved | preserved | preserved |
| CUP | preserved | **split → CON** | **split → CON** |
| PRG | absorbed (→DSA) | preserved | preserved |
| LIB | **split** | **split** | **split** |
| DSA | **split** | **split** | **split** |

All four variants still produce 10 well-populated DPGMM clusters — k=4 does **not** break the clustering. What changes is *which* groups form.

### Findings

1. **Robust core (real structure):** SD, STY, POP, CON, NAT survive in every variant, residualized or not, k=4 or k=5. Crucially this includes **STY**, the cross-cutting flagship (left-ish enforcement + high electoral skepticism + religious traditionalism) — it is not an artifact of the modeling choices.

2. **The cross-cutting structure survives without residualization.** In every variant there are simultaneously left-skeptic, right-skeptic, and right-trusting clusters — electoral skepticism stays orthogonal to the enforcement (left–right) axis. Residualization *sharpens* separation (it moves ~40% of assignments, ARI≈0.60 vs baseline) but does not *create* the cross-cutting result.

3. **The left bloc is weakly separated.** PRG, DSA, LIB, SD sit close together in policy space (pairwise cosine ≈ 0.72–0.77). LIB and DSA split in every variant; PRG wobbles. Only k=5 + residualization pulls the left quartet cleanly apart — they are the least robust groupings in the typology.

4. **Civic Union (CUP) requires k=5.** At k=4, Electoral Skepticism and Government Distrust merge into one trust factor, and CUP — the institutionalist defined by trusting *both* elections and government — loses the dimension that distinguishes it and is absorbed into Conservative. CUP only stands alone when the two trust dimensions are kept separate. **This is the concrete payoff of k=5**, despite Government Distrust's low standalone η².

5. **Net:** the production choice (k=5 + residualization) is the only configuration that resolves all nine parties. The dominant, cross-cutting structure is robust; the *full nine-way resolution* specifically depends on separating the trust dimensions (rescues CUP) and residualizing the culture factors (rescues the left quartet).

### Cluster strength (assignment confidence)

Strength = weighted mean of each cluster's max posterior probability (how cleanly members are assigned), from the production posteriors in `typology_cluster_assignments.csv`. The centroid-separation/silhouette proxy was tried and **discarded** — it contradicts this measure (it under-rates STY, which is centrally located but confidently assigned), because DPGMM uses full-covariance Gaussians, not round blobs.

| weakest → strongest | conf |
|---|--:|
| CUP | 0.66 |
| C7 (Blue Dog) | 0.70 |
| CON / SD / LIB | 0.74 |
| PRG | 0.76 |
| POP / NAT | 0.80 |
| STY / DSA | 0.81 |

Residualized vs non-residualized clusterings have ~the same average confidence (≈0.77 either way) — residualization changes *which* clusters form, not their cohesion. Government Distrust is never residualized (only F4/F5 are), so its η² is essentially unchanged by the residualization choice (≈0.06 production; 0.28→0.26 in the reproduction): not residualizing does **not** rescue its discriminating power.

### Decisions (and the reasoning)

**Keep C7 (Blue Dogs) excluded → 9 parties.** C7's assignment confidence (0.70) is second-lowest but *not* the lowest — CUP (0.66) is lower and is kept. The deciding factor is interpretability, not confidence: CUP is low-confidence but has a clear identity (the institutionalist), whereas C7 is the *ambiguous middle* spanning the CON/CUP boundary with no distinct platform. A 10th "leftover" party weakens the typology more than it adds. **Caveat to carry:** dropping C7 sends a real cross-pressured constituency — the "law-and-order Democrat" (high enforcement, progressive on race, pro-institution, Democratic-leaning) — into Conservative, where it's mislabeled. This is a known representation gap, surfaced by the no-residualization run (where those voters re-coalesce as a distinct blend).

**Keep residualization on.** By cluster confidence the two paradigms are a near-tie (≈0.77), so residualization isn't a quality trade — it's a structure choice, and the residualized version resolves the full nine (especially the weakly-separated left quartet LIB/DSA/PRG, which collapses without it). What non-residualization "adds" is mostly the left bloc merging into coarser groups, plus the one law-and-order-Democrat blend — which is ~40% the already-dropped Blue Dogs. Trading clean left-party separation to re-surface the ambiguous group we rejected is a bad trade. Residualization also has a principled basis: removing the dominant enforcement axis's pull on the culture factors lets them vary independently of left–right, which is what lets the *other* cross-cutting structure (STY) show up cleanly rather than smeared along the main axis.

> Interactive write-up of this comparison: `analysis/efa/cluster_explorer.html` (built by `build_cluster_explorer_{data,html}.py`); strength re-fit in `cluster_confidence_k5.py`; survival/correspondence in `cluster_survival_k4_k5.py` and `compare_k4_vs_k5_clustering.py`.

---

## Orthogonal cleavages outside the factor model

The 5 factors and the 9 parties are a **domestic-policy** typology. A separate question is whether items *excluded* from the EFA hide a coherent dimension the model misses. Tested with a method suited to the data — PCA on binary indicators + communality (weighted R² of each excluded item on the 5 factor scores), **not** polychoric EFA. Scripts: `analysis/efa/explore_foreign_policy.py`, `explore_extra_dims.py`.

**Excluded *clean* (EFA-compatible) items carry no hidden dimension.** Of ~30 support/oppose and agree/disagree items left out, the strongly-polarized ones are already well explained by the 5 factors (build-the-wall R²=0.54, racial-resentment 0.48–0.50, climate 0.39–0.45, assault-rifle ban 0.39) — redundant, so excluding them was parsimony/balance, not loss. The low-communality ones don't cohere into a factor (pairwise |r| mostly <0.3); they're either **valence issues** (background checks R²=0.13 at 93% support; mental-health spending; expand Medicaid — broadly popular, little discriminating signal) or the one genuinely off-axis thread below. Re-including any of these would not improve the model.

**Foreign policy is a real, mostly-orthogonal cleavage — engagement ↔ isolationism.** PCA on the Ukraine / Israel–Gaza / use-of-force batteries gives a coherent PC1 (~25% variance): every engagement action loads one way, "stay out / none" the other. It correlates only modestly with the domestic factors (F5 −0.33, F2 −0.29, F1 −0.26, F3 ≈ 0) and separates the 9 clusters at **η²=0.18 — on par with Religious Traditionalism (F4=0.181) and 3× the retained Government Distrust (F3=0.061)**. It cross-cuts the parties: isolationism is highest at the *anti-establishment* poles — populist-right **POP** and economically-left **STY** meet at the isolationist end, despite sitting opposite on left–right. It was correctly kept out of the polychoric EFA for the **data-shape** reason (multi-select / the mechanical "none" anti-correlation), not for lack of signal.

**Housing/zoning is a faint second off-axis thread.** "Relax zoning for apartments" has R²=0.04 with the five factors (essentially unrelated) and correlates 0.31 with affordable-housing — a YIMBY–NIMBY cleavage structurally like foreign policy, but only 2–3 items, far too thin to anchor a stable factor.

**Decision:** treat foreign-policy engagement (and, faintly, housing) as **documented orthogonal overlays** — cross-cutting cleavages the two-party frame erases, present even inside the 9 domestic-policy parties — not as new factors or clustering inputs. The discipline: fix the validated domestic foundation, add dimensions as overlays, never as foundation-changers.

---

## The 6-D foreign-policy variant: fracturing the middle

We tested what happens if foreign policy were a *party-defining* sixth dimension, not just an overlay — clustering on the five production factor scores **plus** a foreign-policy engagement↔isolationism score (PCA of the Ukraine / Israel–Gaza / use-of-force batteries), scaled to a typical factor's strength, everything else held to production (`analysis/efa/sixdim_cluster.py`; explorer `sixdim_explorer.html`; coalition view `coalition_fracture.html`).

**It does not break the system.** 10 well-populated clusters; mean assignment confidence **0.752 vs 0.755** (statistically identical to the 5-D parties). ARI vs production = 0.54. So foreign policy is a "free" dimension — it carves new structure without degrading the existing clusters.

**It fractures the cross-pressured middle, not the poles.** Counting how many 6-D clusters each production party spreads across (≥15% of its members):

| stable poles (1 cluster) | fractured middle (2–3 clusters) |
|---|---|
| PRG, DSA, LIB, CON, NAT | STY (3), SD (2), CUP (2), POP (2), C7 (2) |

The ideological poles hold; the cross-pressured center splits along engagement↔isolationism. The signature new entity is an **isolationist bloc** (POP 37 / STY 36 / CON 11, FP engagement −1.78) — drawn from the populist right *and* the economic left, united only by "stay out." SD splits into an **internationalist wing** (SD/LIB, FP +0.92) and a lower-engagement SD/STY group; STY fragments three ways.

**Legislation effect (party-discipline House, seats ∝ population).** The electorate is identical, so most outcomes hold — but the re-sorted blocs, voting as units, **flip two knife-edge immigration bills toward restriction**: *grant legal status to undocumented* 60%→49% (fails, despite 59% popular) and *deny asylum* 50%→59% (passes). Foreign-policy votes also become more decisive/whippable (the isolationist bloc votes cohesively instead of splitting inside every party). The flips come from bloc mechanics under perfect party discipline, not changed minds — a reminder that *party structure*, not just opinion, decides near-even bills.

**C7 (Blue Dogs), revisited.** C7's members split **65% into a Conservative-led cluster, 26% into a Liberal-led one** — left and right. C7 is Democratic by identity (45% Dem, very racially progressive, values −1.09) but enforcement-hawkish, so an enforcement-dominated clustering drags it rightward. This is the representation gap in miniature: drop C7 and these Democratic-leaning voters get folded into Conservative. It also fits the broader pattern — **the cross-pressured middle and the left are far more fractious than the right** (CON/NAT solid everywhere; LIB/DSA/SD/STY/CUP/POP/C7 all split under one lens or another).

**Decision.** Keep the **5-D, residualized, 9-party model as the backbone** (it's the validated foundation the whole simulation runs on). Foreign policy stays a **documented overlay** for the current "what parties would emerge from today's opinion" framing. The 6-D run is preserved as the **forward-looking "where this is heading" variant**: it shows the foreign-policy realignment is latent in the data and would fracture the middle into more partisan camps *if* foreign policy keeps rising in salience — but its headline new group (the everyone-who-wants-to-stay-out bloc) is a real *cleavage*, not yet a plausible governing *party* (it agrees on one issue and little else). Cohesion can't decide between 5-D and 6-D (they tie at ~0.75); plausibility favors the 5-D parties as coalitions, with the 6-D as the scenario for an emerging populist/nationalist foreign-policy axis.
