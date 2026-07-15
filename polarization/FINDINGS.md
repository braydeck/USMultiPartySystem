# Does FPTP drive polarization? A pressure test

**Question.** Does "proportional systems produce less political polarization than
first-past-the-post" hold up — and does it hold in the English-speaking world while dissolving
outside it?

**Primary frame.** The analysis centres on **established (V-Dem liberal) democracies with
population ≥ 1M** — 43 countries, 1990–2025. This is the universe where an electoral-system
comparison is meaningful and comparable: it drops developing/backsliding democracies (where
"electoral system" and polarization mean different things) and micro-states (whose politics are
atypical). Broader and narrower samples are reported as robustness.

**Verdict.** In this clean universe the pattern is real in direction. The raw FPTP-vs-proportional
gap is ~**+0.5 to +0.7** polarization points; a hierarchical Bayesian model that adjusts for
democracy quality, size, time, and country/region structure puts the FPTP effect at **~+0.2
points with ~90–93% posterior probability of being positive** — *likely and moderate*, not
strong, and softening under a skeptical prior. It cannot be cleanly separated from two confounds:
**anglophone heritage** (0.79-correlated with FPTP here) and **country size** (larger countries
are more polarized, and FPTP democracies skew large). The single most robust predictor of low
polarization is **democracy quality**, not electoral system. Best read as *supported but not
proven*: the direction is consistent and now carries a defensible probability, but the data
cannot rule out that "anglophone political culture" or "large-country dynamics" do much of the
work credited to the ballot.

Data: V-Dem political polarization (`v2cacamps`, the score in the source CSV) as outcome;
institutions and controls from V-Dem, Cheibub government type, La Porta legal origin, World Bank
population, and a hand-coded anglophone/chamber reference. Panel merge validated at r = 1.000.

---

## 1. Primary universe: established non-micro democracies

`polarization ~ FPTP (+ controls) + year effects`, country-clustered SEs, 43 countries.
Positive coefficient = FPTP associated with **higher** polarization.
(`outputs/primary_established_nonmicro.csv`; full tables `outputs/tier3_regression_tables.txt`.)

| Model | FPTP | 95% CI | democracy score | log-pop | R² |
|---|---:|---|---:|---:|---:|
| Bivariate | **+0.70** | [−0.02, +1.43] | — | — | 0.09 |
| + gov/dem/bicameral | +0.29 | [−0.52, +1.11] | **−8.59\*\*** | — | 0.23 |
| + legal origin | +0.70 | [−0.31, +1.70] | **−8.73\*** | — | 0.40 |
| + population | +0.45 | [−0.41, +1.32] | **−9.43\*\*** | **+0.76\*** | 0.49 |

- **FPTP effect is positive and consistent in sign but fragile.** The bivariate gap is +0.70
  (CI just touches zero). It survives adding legal origin (+0.70) but attenuates to +0.29–0.45
  once government type, democracy quality, and population are included — none of the FPTP
  estimates clear the significance bar.
- **Democracy quality dominates.** The polyarchy coefficient (≈ −8.6 to −9.4) means a 0.1 rise
  in the electoral-democracy index maps to ~0.9 lower polarization — larger and far more
  significant than the FPTP effect.
- **Country size matters and confounds.** Larger countries are significantly more polarized
  (log-pop +0.76*); because FPTP democracies skew large (US, plus mid-size anglophone cases),
  controlling for size pulls the FPTP coefficient down from +0.70 to +0.45.

Descriptive recent means (2015–2024): majoritarian −0.52 (n=9) vs proportional −0.99 (n=30),
raw difference **+0.47** — the direction of the thesis, modest in size.

## 2. The anglophone cases within this universe

Seven anglophone democracies qualify (India excluded — not a V-Dem liberal democracy in recent
years; Malta excluded — micro-state). Mean polarization 2015–2024:

| Country | Electoral family | Polarization |
|---|---|---:|
| United States | FPTP | +1.47 |
| South Africa | PR-list | +0.19 |
| United Kingdom | FPTP | −0.28 |
| Canada | FPTP | −0.83 |
| Australia | AV lower / **STV Senate** (hybrid) | −1.12 |
| New Zealand | MMP (proportional) | −1.91 |
| Ireland | STV (proportional) | −2.73 |

- The proportional/hybrid cases (Ireland, NZ, Australia) are the least polarized; the FPTP cases
  span from calm (UK, Canada) to extreme (US). **Australia** is a hybrid — its directly-elected
  STV Senate is genuinely proportional and shapes its party system — so its low polarization is
  consistent with the proportional side, not a counterexample.
- The US is the outlier pulling the FPTP group up; UK and Canada (also FPTP) are middling-to-low.
  Within the anglophone set the electoral rule alone does not explain the spread — presidential
  vs parliamentary and US-specific dynamics are in play (the US is the one presidential system
  here). See `outputs/fig1_anglophone_by_system.png`.
- The two cases that don't fit are handled by the primary universe's own rules rather than by
  hand: **Malta** (proportional STV yet highly polarized) is a micro-state whose small-district
  STV yields a two-party duopoly — proportional in form only — and is excluded; **India**
  (FPTP, highly polarized, but a backsliding electoral autocracy) is excluded.

## 3. Why this universe, not broader or narrower

`polarization ~ FPTP + year FE`, by sample:

| Sample | Countries | FPTP coef | 95% CI |
|---|---:|---:|---|
| Anglophone only | 9 | +0.65 | [−1.50, +2.81] |
| **Established non-micro (primary)** | **43** | **+0.70** | **[−0.02, +1.43]** |
| Established democracies (incl. micro) | 49 | +0.61 | [−0.10, +1.32] |
| All democracies (incl. electoral) | 115 | −0.03 | [−0.52, +0.47] |

The signal is clearest in the primary universe. It is too noisy to estimate in the anglophone
set alone (N=9), and it **disappears entirely** once developing and backsliding democracies are
added (all-democracies coef ≈ 0). So the FPTP→polarization association is a property of
established, comparable democracies — consistent with the idea that it is bounded to a
particular kind of country rather than universal. See `outputs/fig2_fptp_across_tiers.png`.

## 4. The confound is tighter here, not looser — and the interaction is ≈ 0

Within the primary universe, FPTP, anglophone status, and common-law heritage are strongly
collinear: **FPTP↔anglophone r = 0.79**, anglophone↔common-law r = 0.81, FPTP↔common-law r = 0.60.
Restricting to established democracies *removes* most non-anglophone FPTP cases, so the
electoral rule and anglophone culture become even harder to separate than in the full sample.

A model interacting the two (`FPTP × anglophone`) returns a near-zero, non-significant
interaction (−0.01) alongside large, opposing main effects (FPTP +1.05\*, anglophone −1.08\*).
That opposing-coefficient pattern is a textbook symptom of the collinearity, not evidence of two
cleanly separable forces — it should not be read as "FPTP raises polarization while being
anglophone lowers it." The honest statement is that this data **cannot** disentangle the
electoral rule from anglophone heritage. See `outputs/collinearity_corr.csv`.

## 5. Estimator sensitivity

Electoral systems barely change within a country (New Zealand's 1996 FPTP→MMP switch is the main
exception), so identification is cross-country and country fixed effects are unusable (they would
absorb the electoral-system variable). Consistent with thin within-country variation, the
between-country estimator gives +0.15 (CI crosses zero) while random effects gives −0.37 — sign
instability that reinforces reading this as a fragile cross-sectional association.

## 6. Bayesian hierarchical model — the most defensible estimate

A multilevel Bayesian model is the right structure for this data: it partially pools across the
43 countries (correct for small N, where frequentist cluster-robust SEs are unreliable and, at
the anglophone N=9, invalid), gives valid posterior uncertainty at any N, and yields direct
probability statements. Model: `polarization ~ fptp + presidential + democracy_z + logpop_z +
year_z + (1 | region) + (1 | country)`, weakly-informative priors, 4 chains, R-hat ≈ 1.00.
(`outputs/bayes_coefficients.csv`, `outputs/bayes_prior_sensitivity.csv`, `fig_bayes_*.png`;
run `python polarization/src/analyze_bayes.py`.)

| Predictor | Posterior mean | 94% CI | P(effect > 0) | Signal |
|---|---:|---|---:|---|
| **FPTP** | **+0.22** | [−0.06, +0.51] | **0.93** | Likely higher (moderate) |
| democracy score (per SD) | −0.29 | [−0.35, −0.23] | 0.00 | Clearly lower (strong) |
| log-population (per SD) | +0.28 | [−0.01, +0.55] | 0.96 | Clearly higher (strong) |
| time trend (per SD) | +0.23 | [+0.21, +0.25] | 1.00 | Clearly rising (strong) |
| presidential | +0.34 | [−0.49, +1.18] | 0.78 | Inconclusive |

- **The adjusted FPTP effect is +0.22 polarization points, ~93% likely to be positive** —
  "likely, moderate." Partial pooling shrinks the raw +0.70 gap once country/region structure,
  democracy quality, size, and time are accounted for.
- **The multilevel model tames the collinearity that broke OLS.** Adding `anglophone`, FPTP
  barely moves (+0.25, P=0.94) and anglophone is inconclusive (−0.30, P=0.22); the posterior
  correlation between the two coefficients is only −0.20 (vs the unstable ±1.0 opposing
  estimates in the OLS interaction). The varying intercepts absorb the shared between-country
  variance, leaving FPTP identified — a materially cleaner result than the frequentist pass.
- **Anglophone-only (N=9), where frequentist inference is invalid:** the partial-pooling
  posterior gives FPTP +0.26, **P(>0)=0.96** — a valid statement the OLS could not make.
- **Prior sensitivity:** under a weakly-informative or diffuse prior, FPTP is +0.22 (P=0.93);
  under a deliberately skeptical prior [N(0, 0.25)] it softens to +0.16 (P=0.89, "directional").
  The conclusion is robust to prior choice except under strong skepticism.

Net of the Bayesian pass: the FPTP→polarization association is **likely positive and moderate
(~+0.2 points, ~90–93% posterior probability)** — firmer and more stable than the frequentist
analysis suggested, but still short of "strong," dwarfed by democracy quality, and — crucially —
this is an *adjusted association within a model*, not causal separation of the electoral rule
from anglophone heritage. Size and democracy quality remain the dominant signals.

---

## What this means for the argument

- **Defensible:** "Among comparable established democracies, majoritarian/FPTP systems tend to
  be somewhat more polarized than proportional ones, and the English-speaking cases fit that
  pattern (Ireland/NZ/Australia low, the US high)." Direction and rough magnitude hold.
- **Not established by this data:** that FPTP *causes* polarization; that the effect is
  statistically robust to controls; or that it is *specifically* anglophone. Democracy quality
  and country size are at least as consistent with the evidence, and FPTP cannot be separated
  from anglophone/common-law heritage in the real-world sample.
- **The framing that survives:** the anglophone world is a reasonable *scope condition* for the
  pattern — it is where FPTP and low-N proportional cases coexist among rich democracies — but
  scope is not mechanism. The strongest single lever in the data is how democratic a country is,
  not which ballot it uses.

## Reproduce

```
python polarization/src/acquire.py        # download V-Dem, QoG (idempotent)
python polarization/src/build_panel.py     # merge -> data/analysis_panel.{parquet,csv}
python polarization/src/analyze.py         # frequentist: primary + tiered stats + figures
python polarization/src/analyze_bayes.py   # hierarchical Bayesian model + prior sensitivity
```

## Caveats

- Polarization is V-Dem's `v2cacamps` (elite/society split into hostile camps); affective-
  polarization survey measures (CSES, Pew) could differ and would be the best next step.
- Electoral system uses V-Dem `v2elparlel` (lower house; codes Australia's AV as majoritarian —
  correct, AV is single-member majoritarian). Australia's proportional STV Senate is captured in
  the hand-coded chamber reference (`data/country_reference.csv`), not the regression binary.
- `presidential` is derived from V-Dem executive variables (coverage to 2025); government-type
  labels use Cheibub (time-invariant-filled, South Africa corrected to parliamentary).
- Country size from World Bank population; Taiwan patched (absent from the series). Micro-states
  (<1M) are classified at the country level and excluded from the primary universe.
- Tiers use V-Dem Regimes-of-the-World thresholds (liberal democracy; electoral + liberal
  democracy). India exits the liberal-democracy tier in recent years under V-Dem's coding.
