# Do the 2024 parties survive in earlier waves?

Independent EFA + DPGMM clustering on each CES wave (2018/2020/2022), compared to the 10 named 2024 parties by shared-item policy profiles + partisan composition. Each wave is clustered from first principles — its own item universe, its own parallel-analysis-determined factor count, no projection into 2024's factor space.

## Summary matrix

| Party | 2022 | 2020 | 2018 | Assessment |
|---|---|---|---|---|
| **DSA** | SURVIVES | SURVIVES | MERGED w/ PRG | The most robust party. A strongly-Democratic, all-progressive cluster exists in every wave. |
| **STY** | WEAK (profile=best, partisan≠) | SURVIVES | ABSENT | Policy profile persists (lowest distance in 2022), but the *people* shift — centrists in 2022, center-left in 2020. The STY *identity* (distrust + center-left + non-progressive) is 2024-only. |
| **LBR** | WEAK | MERGED w/ OAO | MERGED w/ LIB | Moderate-Democratic bloc exists but doesn't separate cleanly from OAO or LIB without the F2 distrust axis. |
| **NAT** | WEAK | ABSENT | ABSENT | Extreme populist-conservative-traditional profile only separates in 2022 with the full item battery. |
| **CON** | WEAK | WEAK | ABSENT | Center-right Republican cluster is recognizable but sized wrong (5–8% vs 19%) — it's embedded in larger right blocs. |
| **POP** | WEAK | ABSENT | ABSENT | High-distrust populist-right. Without distrust items (2018/2020) or the full item set, doesn't separate from NAT/CON. |
| **OAO** | MERGED w/ CUP | ABSENT | MERGED w/ STY/CUP | Anti-populist, pro-enforcement, mixed-partisan. Needs F2 + F5 interaction to separate. |
| **CUP** | ABSENT | MERGED w/ STY | MERGED w/ STY/OAO | Trusts institutions, mixed-partisan. Defined by LOW F2 distrust — can't exist without that axis. |
| **LIB** | ABSENT | ABSENT | MERGED w/ LBR | Strongly-Democratic, institution-trusting. Without F2, merges with LBR (both are progressive Democrats). |
| **PRG** | MERGED w/ LIB | ABSENT | ABSENT | The most extreme progressive cluster. Only separates from DSA/LIB with the full F1 Security + F2 Distrust separation. |

## Key findings

**1. DSA is the only party that cleanly survives.**

Democratic Socialists — the strongly-progressive, all-Democratic, anti-enforcement bloc — cluster separately in 2022 (dist 1.39, 69D/0R vs 62D/0R) and 2020 (dist 1.60, 74D/0R). In 2018 it merges with PRG into a single large progressive cluster (16.5%), but the profile is still recognizable. This cluster is defined by extreme positions on racial resentment, immigration, and abortion — items that exist in every wave. It does not depend on the 2024-specific F2 distrust axis.

**2. STY's policy profile is the best-matching of all parties — but the identity is 2024-only.**

In 2022, STY has the lowest normalized distance of any party (0.30), meaning its policy positions on shared items are almost perfectly replicated. But the cluster holding those positions (c2: 12.7%, 24D/26R) is centrist, not center-left (STY in 2024 is 36D/17R). The ~20pp partisan difference drops the verdict from SURVIVES to WEAK.

In 2020, STY maps to c1 (13.4%, 50D/11R) with a good profile distance (0.33). This cluster is more Democratic than 2024 STY, not less. The STY-like policy profile exists in both years; who holds it changes.

The STY special analysis searched for clusters meeting all three STY criteria: center-left (>30% Dem, <25% Rep), non-progressive (race problems-rare > 2.5), and distrusting government (trust_fed > 2.5). No cluster in any prior wave meets all three. The intersection of non-progressive + distrusting + center-left is what makes STY distinctive — and it only coheres as a cluster when the F2 election-fairness items enter the survey in 2024.

**3. The F2-defined pairs (LIB/PRG, CUP/OAO) are inseparable before 2024.**

The parties that differ primarily on F2 Institutional Distrust collapse into pairs:
- **LIB + PRG** merge: both are progressive Democrats. LIB trusts institutions (F2 = -0.74), PRG does too (F2 = -0.63). Their F1 Security scores separate them in 2024 (LIB = -0.46, PRG = -1.26), but without the full F1 item battery (police/asylum/surveillance are 2024-only), they look identical.
- **CUP + OAO** merge: both are center-right mixed-partisan. CUP trusts institutions (F2 = -0.82), OAO distrusts (F2 = -0.63, but on the opposite side of F5 at -1.09). Without F2, the OAO vs CUP distinction collapses.

**4. NAT and POP don't separate from the broader right before 2022.**

NAT (extreme populist-conservative-traditional, 1D/60R, F5 = +1.09) and POP (high-distrust populist-right, 10D/46R, F5 = +0.88) need either the full item battery or the distrust axis to separate from each other and from CON. In 2022 they appear as WEAK matches; in 2020/2018 they are ABSENT — their voters are absorbed into generic strongly-Republican clusters.

**5. The 2018 electorate partitions into 9 clusters, not 10.**

With only 14 shared items and no distrust/policing items, the DPGMM finds 9 effective clusters in 2018 (vs 10 in every other wave). Most parties MERGE or are ABSENT. The electorate looked simpler — a large center (20%, 33D/28R), two progressive blocs, two conservative blocs, and a few smaller mixed clusters. The 10-party structure is a product of the 2024 instrument's richer item coverage plus the emergence of the distrust axis.

**6. CON is recognizable but undersized.**

Conservative matches to small (5–8%) strongly-Republican clusters in all three prior waves. In 2024 CON is 19.2% — the largest party. The CON profile on shared items exists, but in prior waves those voters are spread across multiple right-leaning clusters (CON + NAT + POP overlap). CON's distinctiveness — moderate on everything except enforcement — only separates with the F1 Security axis that 2024's police/asylum/surveillance items provide.

## Method

- **Item universe per wave:** all policy-attitude items (Support/Oppose, Agree/Disagree, Likert spending, trust), excluding split-sample items (441e/f/g) and roll-call votes. Items: 2022=41, 2020=40, 2018=37.
- **Screening:** PID R² > 0.50 (none dropped), ceiling/floor > 90% (gun_bgchecks in 2018, police_bodycams in 2020).
- **EFA:** weighted polychoric → parallel analysis → PAF + oblimin → Thomson scores → partisan sign-align → residualize correlated factors on enforcement anchor.
- **Clustering:** DPGMM (n_components=10, dirichlet_process, full covariance, n_init=5, seed=42).
- **Matching:** weighted mean on shared items per cluster/party → z-score → Euclidean distance → Hungarian optimal 1:1 assignment. Thresholds normalized by √n_shared_items: SURVIVES < 0.45×√n, WEAK < 0.65×√n.
- **Shared items with 2024:** 19 (2022), 18 (2020), 14 (2018). Subset of each wave's items that also appear in the 2024 canonical set via the crosswalk.

## Factor structures

| Wave | k (PA) | Factors (by dominant items) |
|---|---|---|
| 2024 | 5 | Security/Order, Institutional Distrust, Government Distrust, Religious Traditionalism, Populist Conservatism |
| 2022 | 7 | Guns, Immigration/Enforcement, Abortion/Religion, Spending, Racial/Gender, Government Trust, Environment/Health |
| 2020 | 6 | Policing/Immigration, Racial, Abortion, Spending, Guns, Executive Orders |
| 2018 | 5 | Immigration, Abortion/Religion, Spending, Tax/Executive, Racial |

2024 fuses racial resentment + immigration + fiscal into Populist Conservatism (F5). Prior waves keep these as separate factors. Government Trust appears as a clean factor in 2022 (matching 2024's F3). Security/policing appears in 2020 (post-Floyd policing battery) but not 2018 or 2022. The Institutional Distrust axis (F2, election-fairness) is 2024-only.

## Files

- `outputs/party_survival_matrix.csv` — full results table
- `outputs/<wave>/independent_loadings.csv` — factor loadings per wave
- `outputs/<wave>/independent_cluster_profiles.csv` — weighted item means per cluster
- `outputs/<wave>/independent_cluster_partisan.csv` — Dem/Rep/Ind % per cluster
- `outputs/<wave>/independent_diagnostics.txt` — item screening, PA k, anchors
- Script: `independent/fit_independent.py <wave>`, `independent/match_to_2024.py`
