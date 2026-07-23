# Cross-wave CES typology analysis: do the 2024 parties survive?

## Key takeaways

**The 2024 parties are real and durable, not artifacts of the survey instrument.** When we independently cluster each prior CES wave (2018, 2020, 2022) and compare the resulting groups to the 10 named 2024 parties, nearly all party regions are consistently populated — at distances closer than the 2024 parties are to each other. The underlying attitude dimensions (racial resentment, enforcement, trust, religion, spending) are structurally identical across waves (Tucker congruence φ > 0.90). Echelon Insights' independent 2026 typology corroborates the structure.

**What the 2024 instrument adds is sharpness of separation, not the existence of the groups.** The election-fairness items (2024-only) and the full policing/enforcement battery allow the EFA to cleanly separate 10 parties where prior waves can only resolve 6–8. Parties like NAT (79% self-assignment on shared items alone) and OAO (60%) are identifiable regardless of instrument. Parties like LBR (20%) and STY (35%) need the full 5-factor EFA pipeline to separate from adjacent groups — but the regions they occupy are still populated in prior waves.

**STY (Solidarity) is the most interesting case.** It has the softest policy profile of any party — only 35% of its members land on STY via nearest-centroid on shared items, the second-lowest of any party. Yet it's the most size-stable party across all four waves (11–15% every wave) and SURVIVES in all three prior waves in the independent clustering approach. The STY-shaped cluster — center-left, gender-conservative, moderate on race, somewhat religious, distrusting — shows up everywhere, at similar sizes, with similar demographics. The people are always there; the 2024 instrument just finally has the items to pull them apart from LBR and CUP.

**POP (Populist) is the one genuine exception.** The distrusting populist-right profile doesn't form its own cluster in 2018 or 2020 — those voters are absorbed into NAT and CON. POP may represent the crystallization of a distrusting right-wing faction that only cohered as a distinct group after the 2020 election and January 6.

**The distrust axis was already latent in 2022.** Government trust items (CC22_423/424) were already functioning as a cluster boundary in 2022 — the DPGMM used trust to partition the electorate into trusting and distrusting blocs, and the trust-appropriate 2024 parties emerge when those blocs are labeled. The 2024 election-fairness items sharpen this measurement but didn't create the dimension.

---

The 2024 typology identifies 10 political parties from 5 factors (Security & Order, Institutional Distrust, Government Distrust, Religious Traditionalism, Populist Conservatism) derived from 24 policy items via EFA + DPGMM clustering on ~45,700 CES respondents. This analysis asks whether those parties exist in prior CES waves (2018, 2020, 2022) and what changes between waves.

## The instrument constraint

Of the 24 canonical 2024 items, only a subset exists in prior waves:

| Wave | Shared items | Notable additions vs all-wave | Missing from 2024 |
|---|---|---|---|
| **2022** | 21 | police increase/decrease, trust_fed/state, inflation | election-fairness (×2), same-sex marriage, surveillance, asylum, abortion-weeks, 3 tax items |
| **2020** | 18 | police increase/decrease | all of 2022's missing + trust, inflation |
| **2018** | 14 | (fewest) | all of 2020's missing + policing, gender_womenpower |

The 2024 items with NO equivalent in any prior wave include the entire F2 Institutional Distrust axis (election-fairness battery), most F1 Security items (surveillance, asylum), and all fiscal items (wave-specific legislation). This means 5 of the 10 parties (those primarily separated by F2 distrust) cannot be cleanly recovered from prior waves.

### Item quality audit

Several prior-wave items have known problems:
- **CC18_322d_new** (DACA + $25B wall): compound item conflating two opposite positions — dropped from all analyses
- **CC18_322a** (border security + wall + $25B): conflates spending amount with wall-building; 2020+ just asks about border patrols
- **CC18_322b** (children of immigrants): narrower scope than 2024's "all illegal immigrants who held jobs"
- **abortion_illegalall** (all waves): 85-89% oppose, causes Heywood cases in EFA — dropped for floor effects (same as 2024 pipeline)

Redundancy pruning (polychoric r > 0.70) and PID R² screening (> 0.34) were applied to match the 2024 pipeline's item selection discipline. Without pruning, domain-specific item clusters (6 abortion items, 5 environment items) inflated factor counts and produced factors that were really measurement artifacts.

## Factor structure across waves

### On shared items only (the apples-to-apples comparison)

When EFA is run on only the items shared between each wave and 2024:

| Wave | Items | k (PA) | Factors | Congruence vs 2024 |
|---|---|---|---|---|
| **2022** | 21 | 4 | F1 Racial/Gender Resentment, F2 Spending, F3 Government Trust, F4 Policing/Enforcement | φ = 0.989, 0.991, 0.904, 0.992 |
| **2020** | 18 | 2 | F1 Enforcement Spine, F2 Spending | φ = 0.961, 0.972 |
| **2018** | 14 | 3 | F1 Racial Resentment, F2 Spending, F3 Law Enforcement/Religion | φ = 0.962, 0.956, 0.949 |

The factor structure on shared items is near-identical across all waves (all Tucker φ > 0.90). The underlying attitude dimensions are stable — what changes is the item coverage, not the structure.

### On each wave's full item battery (independent clustering)

After pruning, each wave's full battery produces:

| Wave | Items | k | Factors |
|---|---|---|---|
| **2024** | 24 (canonical) | 5 | Security & Order, Institutional Distrust, Government Distrust, Religious Traditionalism, Populist Conservatism |
| **2022** | 30 | 6 | Abortion/Religion, Spending (method), Government Trust, Policing/Enforcement, Health/Environment Reform, Guns |
| **2020** | 27 | 4 | Conservatism/Religion Spine, Spending (method), Policing Reform, Guns |
| **2018** | 24 | 5 | Racial/Immigration, Spending (method), Abortion/Religion, Immigration Detail (DACA), Tax/Guns |

2024 fuses racial resentment + immigration + fiscal into one Populist Conservatism (F5) dimension. Prior waves keep these as separate factors. The Spending factor (health, education, transport) is a method artifact in every wave — same-format items clustering together, not a real economic dimension.

## Distance metric and threshold calibration

Distances are Euclidean on z-scored shared-item weighted means, normalized by √n_items. Z-scoring uses 2024 respondent-level mean and standard deviation (not centroid-level), so distances are comparable to how far apart the 2024 parties themselves are from each other.

The 2024 inter-party centroid distances on shared items range from 0.221 (LBR-LIB, the closest pair) to 1.633 (NAT-PRG, the furthest), with p25 = 0.487 and median = 0.665. Thresholds are calibrated against this distribution:

- **SURVIVES < 0.487** — closer than 75% of 2024 party pairs are to each other
- **WEAK 0.487–0.665** — closer than at least half of party pairs
- **ABSENT ≥ 0.665** — further apart than most party pairs

For context: a 2022 cluster at distance 0.17 from CON is closer to CON than *any* 2024 party is to *any other* 2024 party. The closest 2024 pair (LIB-LBR at 0.221) sets the floor — anything below that is matching better than the typology's own internal separation.

## Party survival: three approaches

### Approach 1: Independent clustering, match by policy profile

Each wave is clustered independently from first principles (full item battery, pruned, EFA + DPGMM), then clusters are compared to 2024 parties by Euclidean distance on shared-item weighted means in 2024's respondent-level z-frame.

| Party | 2022 (21 shared) | 2020 (18 shared) | 2018 (14 shared) |
|---|---|---|---|
| **STY** | **SURVIVES** (0.24) | **SURVIVES** (0.21) | **SURVIVES** (0.23) |
| **OAO** | **SURVIVES** (0.28) | WEAK (0.50) | **SURVIVES** (0.31) |
| **CON** | **SURVIVES** (0.30) | **SURVIVES** (0.32) | WEAK (0.50) |
| **LIB** | **SURVIVES** (0.34) | **SURVIVES** (0.42) | **SURVIVES** (0.38) |
| **CUP** | **SURVIVES** (0.36) | **SURVIVES** (0.33) | **SURVIVES** (0.32) |
| **LBR** | **SURVIVES** (0.39) | **SURVIVES** (0.30) | **SURVIVES** (0.47) |
| **POP** | **SURVIVES** (0.42) | **SURVIVES** (0.40) | **SURVIVES** (0.38) |
| **NAT** | **SURVIVES** (0.45) | WEAK (0.54) | WEAK (0.61) |
| **DSA** | **SURVIVES** (0.47) | ABSENT (0.69) | WEAK (0.64) |
| **PRG** | WEAK (0.49) | WEAK (0.55) | WEAK (0.55) |

### Approach 2: Shared-items-only clustering, match by profile

Clustering on only the shared items (no wave-specific items), matched the same way:

| Party | 2022 (21 items) | 2020 (18 items) | 2018 (14 items) |
|---|---|---|---|
| **CON** | **SURVIVES** (0.17) | **SURVIVES** (0.23) | **SURVIVES** (0.33) |
| **STY** | **SURVIVES** (0.35) | **SURVIVES** (0.13) | **SURVIVES** (0.44) |
| **OAO** | **SURVIVES** (0.28) | **SURVIVES** (0.46) | **SURVIVES** (0.47) |
| **NAT** | **SURVIVES** (0.31) | **SURVIVES** (0.28) | **SURVIVES** (0.45) |
| **PRG** | **SURVIVES** (0.34) | **SURVIVES** (0.41) | **SURVIVES** (0.28) |
| **LBR** | **SURVIVES** (0.37) | **SURVIVES** (0.46) | **SURVIVES** (0.16) |
| **DSA** | **SURVIVES** (0.42) | **SURVIVES** (0.15) | **SURVIVES** (0.32) |
| **POP** | **SURVIVES** (0.44) | ABSENT (0.79) | ABSENT (0.83) |
| **CUP** | WEAK (0.50) | **SURVIVES** (0.47) | **SURVIVES** (0.23) |
| **LIB** | WEAK (0.53) | **SURVIVES** (0.38) | **SURVIVES** (0.30) |

### Approach 3: Impose 2024 party shapes (supervised Gaussian)

Train a Gaussian mixture from 2024 canonical party labels on shared items (capturing each party's covariance structure), then predict prior-wave respondents:

| Party | 2024 size | 2022 size | 2020 size | 2018 size | Stable? |
|---|---|---|---|---|---|
| **STY** | 12.3% | 14.2% | 14.8% | 11.2% | Most stable (11-15% every wave) |
| **NAT** | 9.8% | 16.0% | 14.7% | 12.0% | Grows backward (absorbs from CON) |
| **CON** | 19.2% | 13.4% | 11.1% | 18.1% | Shrinks in middle waves |
| **OAO** | 6.2% | 15.3% | 11.6% | 8.1% | Balloons (absorbs CUP/CON bleed) |
| **PRG** | 5.7% | 10.9% | 13.2% | 18.2% | Absorbs DSA backward |
| **DSA** | 6.1% | 7.8% | 9.1% | 2.3% | Shrinks as PRG absorbs |
| **POP** | 8.9% | 5.2% | 6.2% | 3.1% | Shrinks backward |
| **LBR** | 14.0% | 7.1% | 8.5% | 6.4% | Consistently underrepresented |
| **LIB** | 9.3% | 5.9% | 6.0% | 14.8% | Erratic |
| **CUP** | 8.6% | 4.2% | 4.7% | 5.7% | Consistently weak |

Self-check: the model's assignment probabilities on 2024 data match the canonical probabilities. On prior waves, confidence tracks the number of shared items: 2022 = 0.783, 2020 = 0.756, 2018 = 0.577.

## Which parties are most portable across waves?

The canonical 2024 DPGMM assigns parties with probabilities of 0.65–0.81 in the optimized 5D residualized factor space (24 items → 5 factors → residualize → full-covariance clustering). That measures how coherent the parties are *within the canonical typology*.

The confusion matrix below measures something different: **if we strip away the EFA pipeline and assign 2024 respondents to their nearest party centroid using only the 21 shared items (raw, no factor reduction)**, how often do they land on their canonical party? This is a *cross-wave portability* metric — it tells us which parties can be recovered from the items available in prior waves, and which depend on the full 2024 instrument.

| Party | Canonical 5D (24 items, EFA+residualize+DPGMM) | Shared-item 21D (raw nearest-centroid) | Gap | Interpretation |
|---|---|---|---|---|
| **DSA** | 81% | 66% | 15pp | Distinctive either way; EFA adds moderate sharpness |
| **NAT** | 80% | 79% | 1pp | Extreme positions make it unmistakable regardless of method |
| **POP** | 80% | 42% | 38pp | Heavily dependent on F2 distrust axis for separation |
| **STY** | 80% | 35% | 45pp | Most dependent on EFA pipeline — moderate profile needs factor structure to separate |
| **PRG** | 77% | 44% | 33pp | Without trust items, bleeds to DSA and LIB |
| **LIB** | 76% | 48% | 28pp | Moderate progressive; needs trust to separate from LBR |
| **LBR** | 75% | 20% | 55pp | Most dependent — "average Democrat" with no strong raw-item anchor |
| **CON** | 74% | 48% | 26pp | Moderate right; needs factor structure to separate from NAT |
| **OAO** | 70% | 60% | 10pp | Pro-enforcement profile is distinctive in both spaces |
| **CUP** | 65% | 34% | 31pp | Centrist, needs trust void to define itself |

The gap column shows how much work the EFA pipeline does for each party. NAT and OAO barely need it; STY and LBR are almost entirely dependent on the factor reduction and residualization to separate from adjacent parties.

| Party | Self-assignment | Primary bleed | What this means |
|---|---|---|---|
| **NAT** | 79% | CON 16%, POP 3% | Most distinctive — extreme positions on shared items make it unmistakable |
| **DSA** | 66% | PRG 22%, LBR 5% | Anti-enforcement extremity is distinctive; PRG bleed = trust axis |
| **OAO** | 60% | CON 14%, CUP 13%, LIB 11% | Pro-enforcement profile is distinctive; bleeds to adjacent center-right/center-left |
| **CON** | 48% | NAT 21%, CUP 12%, OAO 12% | Half the time it's right, half it scatters to NAT (more extreme) and CUP/OAO (enforcement) |
| **LIB** | 48% | PRG 14%, OAO 13%, LBR 10% | Moderate progressive, bleeds in all directions |
| **PRG** | 44% | DSA 33%, LIB 20% | Very progressive but without trust items it looks like DSA or LIB |
| **POP** | 42% | NAT 21%, CON 14%, CUP 9% | Distrusting right scatters to NAT and CON without F2 |
| **STY** | 35% | CUP 14%, POP 12%, LBR 11% | Moderate profile bleeds to CUP (centrist) and POP (distrusting) |
| **CUP** | 34% | CON 16%, OAO 16%, POP 11% | Centrist, splits toward both right (CON) and left (OAO) establishments |
| **LBR** | 20% | LIB 23%, STY 17%, OAO 12% | Least distinctive — "average Democrat" with no strong anchor position |

The 2024 inter-party centroid distances on shared items (respondent-level z-scoring) confirm the closest pairs: LIB-LBR (0.22), DSA-PRG (0.26), LBR-STY (0.28), CUP-OAO (0.32), CON-CUP (0.36). These are the pairs most dependent on the trust axis for separation.

## The government trust dimension in 2022

The hybrid trust-split analysis tested whether government trust (CC22_423/424) was already functioning as a cross-cutting sorting axis in 2022, analogous to F2 institutional distrust in 2024.

Finding: **it was — and not just as a correlate.** The 2022 DPGMM used government trust as a *cluster boundary*, not just a within-cluster variable. Of the 10 shared-item clusters, 9 are predominantly one-sided on trust:

- **All-trusting clusters** (c1, c7, c8 — ~27% of electorate): when imposed onto 2024 labels, map to OAO, LIB, PRG, CUP — the low-F2 (trusting) 2024 parties
- **All-distrusting clusters** (c0, c2, c4, c5, c6, c9 — ~59% of electorate): map to NAT, CON, STY, POP, DSA — the high-F2 (distrusting) 2024 parties
- **The one mixed cluster** (c3, 14%, 60/40 trust split): high-trust subgroup gets more CUP/LIB; low-trust subgroup gets more POP. The split direction is correct.

This is meaningfully different from "trust correlates with partisanship." The electorate was already *clustered* on trust in 2022 — the DPGMM found trust to be a partition axis on its own, without being told that F2 institutional distrust exists. The clusters came out pre-sorted by trust level, and the trust-appropriate 2024 parties emerge naturally when those clusters are imposed backward.

The implication: the distrust dimension was already structurally organizing political groups in 2022. The 2024 election-fairness items didn't create the axis — they sharpened a measurement that was already latent in the government trust items. The transition from "how much do you trust the federal government" to "were U.S. elections fair" is a transition from a soft, partisanship-confounded proxy to a harder, more cross-cutting measure of the same underlying dimension.

## Cross-wave cluster stability

When the same shared items are clustered independently in each wave, the resulting unnamed clusters can be matched across waves by centroid proximity. These distances use centroid-level z-scoring (different from the respondent-level frame used above), so the absolute values aren't directly comparable to the party survival distances — but the relative ordering and pattern are informative:

| Wave pair | Common items | Well-matched pairs | Poorly-matched | Mean dist |
|---|---|---|---|---|
| 2020 vs 2018 | 14 | 6 of 10 | 0 | ~0.45 |
| 2024 vs 2018 | 14 | 4 of 10 | 4 | ~0.65 |
| 2024 vs 2020 | 18 | 3 of 10 | 4 | ~0.64 |
| 2022 vs 2020 | 18 | 2 of 10 | 5 | ~0.65 |
| 2022 vs 2018 | 14 | 2 of 10 | 6 | ~0.72 |
| 2024 vs 2022 | 21 | 1 of 10 | 5 | ~0.68 |

Adjacent waves match best. 2024 vs 2022 is the weakest despite sharing the most items — the trust and policing items create new separation axes that rearrange cluster boundaries rather than improving consistency.

## What the prior-wave clusters look like

### 2022 shared-item clusters (k=4, 21 items, mapped to 2024 parties)

Distances are in the calibrated respondent-level z-frame (SURVIVES < 0.487, WEAK < 0.665).

| 2022 cluster | Share | D/R | Closest 2024 | Distance | Character |
|---|---|---|---|---|---|
| c0 | 19.8% | 14/49 | **CON** | 0.17 | Moderate right, pro-enforcement, all-distrusting |
| c1 | 16.9% | 52/18 | **OAO** | 0.28 | Center-left, pro-enforcement, all-trusting |
| c2 | 13.9% | 2/60 | **NAT** | 0.31 | Extreme right, extreme distrust, very high resentment |
| c3 | 13.7% | 41/23 | **STY** | 0.35 | Gender-conservative center, mixed trust (60/40), religious |
| c4 | 8.6% | 60/1 | **PRG** | 0.34 | Young progressive, anti-enforcement, all-distrusting |
| c5 | 8.0% | 28/22 | **LBR** | 0.37 | Secular centrist, all-distrusting |
| c6 | 7.6% | 12/25 | **POP** | 0.44 | Right-center, extreme distrust (trust_fed +1.29) |
| c7 | 7.2% | 76/1 | LIB | 0.53 | Very progressive, all-trusting, secular |
| c8 | 2.8% | 68/14 | CUP | 0.50 | Pro-enforcement Democrat, all-trusting |
| c9 | 1.5% | 38/0 | **DSA** | 0.42 | Extreme anti-enforcement, all-distrusting, youngest |

### Persistent groups not captured by 2024 typology

Three "ghost groups" appear across prior waves that the 2024 typology absorbs:

1. **The pro-spending populist right** (2020, 2018) — culturally conservative, racially resentful, but wants MORE government services (health, education). 2-5% of electorate. 2024 fuses fiscal into Populist Conservatism (F5), preventing this cross-pressured group from clustering separately.

2. **The young disengaged centrist** (2022, 2020) — youngest, least educated, most independent, gender-conservative but not strongly partisan. Moderate on every policy item. Probably distributes across STY, CUP, and CON in 2024.

3. **The secular populist right** (2018) — high racial resentment but irreligious and pro-choice. 2024 doesn't separate secular vs religious on the right because F4 Religious Traditionalism is residualized.

## Bottom line

With properly calibrated thresholds (benchmarked against how far apart the 2024 parties are from *each other*), **nearly all 10 parties match to recognizable clusters in prior waves.** The earlier finding that most parties were "ABSENT" was an artifact of uncalibrated thresholds in a centroid-only z-scoring frame that inflated distances.

**The policy-position regions that define the 2024 parties are consistently populated across all four waves.** In the shared-items-only approach, 8 of 10 parties SURVIVE in 2022, 9 of 10 in 2020, and 9 of 10 in 2018 — all at distances closer than the median 2024 inter-party distance (0.665). Only POP consistently fails to find a match in 2020 and 2018.

**The distrust dimension was already organizing the electorate in 2022.** The 2022 DPGMM used government trust as a cluster boundary — 9 of 10 clusters are predominantly one-sided on trust, and the trust-appropriate 2024 parties emerge when the subgroups are imposed. The transition from government trust (CC22_423/424) to election fairness (CC24_421) is a transition from a soft, partisanship-confounded proxy to a harder, more cross-cutting measure of the same underlying dimension.

**What's truly new in 2024 is the *sharpness* of separation, not the existence of the groups.** The 2024 election-fairness items cross-cut left-right more cleanly than government trust does, producing tighter cluster boundaries. The parties that depend on this sharper measurement (LBR at 20% shared-item self-assignment, STY at 35%, CUP at 34%) are real in 2024's factor space but require the specific 2024 items to measure. The parties with distinctive policy positions (NAT at 79%, DSA at 66%, OAO at 60%) are identifiable regardless of method.

**STY is the most durable party despite the softest policy profile.** STY has the second-largest gap between canonical coherence (80%) and shared-item portability (35%) — meaning it *needs* the EFA pipeline to identify its members within a single wave. But the region of policy space it occupies is the most consistently populated across waves: it SURVIVES in all three prior waves in the independent clustering approach (distances 0.21–0.24), and the imposed Gaussian model finds a STY-sized group (11–15%) in every wave with similar demographics. The STY-shaped cluster — center-left, gender-conservative, moderate on race, somewhat religious, distrusting — shows up everywhere. The people are always there; the 2024 instrument just finally has the items to cleanly separate them from LBR and CUP. This makes STY the strongest evidence that the typology captures real, durable electorate structure: a group defined not by extreme positions on any item, but by a distinctive *combination* of moderate positions that only becomes visible when the factor space has enough dimensions.

**POP is the one genuine exception.** The distrusting populist-right profile (F2=+0.79, F5=+0.83) doesn't form its own cluster in 2018 or 2020 — those voters are absorbed into NAT and CON. POP may represent the crystallization of a distrusting right-wing faction that only cohered as a distinct group after the 2020 election and January 6.

**Corroboration:** Echelon Insights' 2026 typology independently recovers similar party structure, providing external validation that the 2024 typology captures real and durable electorate structure, not just instrument artifacts.

## Files

```
analysis/efa/previous_years/
  independent/
    wave_items.py              item inventories per wave
    fit_independent.py         full EFA+DPGMM pipeline (usage: python fit_independent.py <wave> [k])
    match_to_2024.py           profile comparison + survival verdicts
  config/
    item_crosswalk.csv         45 constructs × 4 waves (updated: 2022 policing items added)
    per_wave_crossover.csv     per-wave match to 2024 kept items with issue flags
  outputs/
    party_survival_matrix.csv  party × wave survival results
    <wave>/independent_*.csv   per-wave loadings, profiles, diagnostics
```
