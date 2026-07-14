# Party Profiles — how the ten parties are distinct

Derived from the CES 2024 typology (10 DPGMM clusters on 5 EFA factors). Every number
below is from `clusterProfiles.json` / `clusterIntensity.json`.

## The four lenses used

1. **Factor signature** — where the party sits on the five factors (z-scores, SDs from the
   national mean):
   - **F1 Security & Order** (high = pro-police/order; low = civil-libertarian)
   - **F2 Electoral Skepticism** (high = distrusts elections)
   - **F3 Government Distrust** (high = distrusts government)
   - **F4 Religious Traditionalism** (high = religious/traditional)
   - **F5 Populist Conservatism** (high = conservative/populist)
2. **Distance from the electorate** — mean absolute deviation of the party's positions from
   the national average, across policy items (`meanDev`). Low = holds the country's positions;
   high = stands apart.
3. **Definition style** — is the party defined by **deviant** planks (many positions ≥25pp from
   the country), by **mainstream** consensus (strongly-held positions the country shares), or by
   **ambivalence** (sitting at "neither" a lot)?
4. **Internal cohesion** — the ambivalence index = mean "neither" share across the agree
   battery. High = members decline to commit / are cross-pressured; low = members take sides.

## At a glance

| party | bloc | seats | pop % | meanDev | deviant planks | mainstream-strong | ambivalence | defined by |
|---|---|---|---|---|---|---|---|---|
| **CON** Conservative | right | 201 | 17.7 | 14.8 | 14 | 22 | 26 | mainstream-right consensus |
| **LBR** Labor | left | 159 | 14.8 | 13.2 | 10 | 29 | 21 | mainstream-progressive consensus |
| **STY** Solidarity | center | 129 | 14.3 | **8.0** | **2** | 23 | **29** | ambivalence + electoral skepticism |
| **POP** Populist | right | 106 | 10.4 | 17.7 | 19 | 21 | 27 | immigration hardline + skepticism |
| **LIB** Liberal | left | 93 | 8.8 | 21.2 | 41 | 17 | 10 | racial-justice + secular liberalism |
| **CUP** Civic Union | center | 89 | 9.3 | **7.0** | 3 | 30 | 19 | institutional/electoral trust |
| **NAT** Nationalist | right | 41 | 8.7 | 28.5 | 49 | 12 | 20 | nationalist-traditionalist maximalism |
| **DSA** Dem. Socialists | left | 25 | 5.9 | 27.6 | 51 | 12 | 9 | radical left + anti-establishment |
| **OAO** Order & Opportunity | center | 15 | 5.3 | 10.6 | 10 | 39 | 20 | law-and-order + economic progressivism |
| **PRG** Progressive | left | 15 | 4.7 | **30.9** | **61** | 10 | **3** | maximalist civil-libertarian left |

Two cross-cutting facts worth holding onto:

- **The center parties are literally closest to the electorate** (CUP 7.0, STY 8.0, OAO 10.6),
  the two large wings next (LBR 13.2, CON 14.8), and the ideological vanguards farthest (DSA,
  NAT, PRG all ≥27). Distance-from-center tracks size and radicalism.
- **Ambivalence is orthogonal to left–right.** The most ambivalent parties are STY (29), POP
  (27), CON (26) — one from each bloc. Commitment vs. cross-pressure is its own axis, and the
  two biggest *right* parties (CON, POP) are internally less committed than the small radical
  ones (PRG 3, DSA 9).

---

## LEFT — LIB, LBR, PRG, DSA

Shared floor: all four are economically left (F5 −0.6 to −1.1), civil-libertarian (F1
negative), and secular (F4 negative). They split on **how far** they go and **whether they
trust institutions**.

**LBR — Labor** (159 seats · 14.8%). The **mainstream** left and the largest left party.
`meanDev 13.2` is the lowest of the bloc — it mostly holds broadly-popular progressive
positions (same-sex/interracial marriage 96%, a Dreamer pathway 98%, expand abortion access
87%) rather than radical ones (only 10 deviant planks vs 29 mainstream-strong). Economically
left but moderate (F5 −0.64), near-center on order and electoral trust. It is the bloc's
center of gravity: progressive-by-consensus, not by vanguard.

**LIB — Liberal** (93 seats · 8.8%). Strongly liberal (F5 −1.08) and secular (F4 −0.66), and
**strongly trusting of elections** (F2 −0.91) — the establishment-liberal bloc. Its signature
is racial-justice and immigration: affirms white advantage (89%, Δ+37) and structural racism
(83%, Δ+37), grants undocumented legal status (98%), opposes the wall (10%), and is hawkish on
Ukraine arms (72%). Distinct from the electorate (meanDev 21, 41 deviant planks) but less
absolutist than PRG/DSA on policing.

**PRG — Progressive** (15 seats · 4.7%). The **maximalist** left — the single most distinct
party from the electorate (meanDev 30.9, 61 deviant planks, ambivalence 3 — it commits on
everything). Most civil-libertarian on the board (F1 −1.60). Defined by near-total *opposition*:
deny asylum 0%, increase police 0.4%, parental consent for pronoun changes 8%, the wall 1%.
Trusts elections (F2 −0.77). It is LIB's positions taken to the pole.

**DSA — Democratic Socialists** (25 seats · 5.9%). As radical as PRG on policing (F1 −1.66,
"decrease police" 87% Δ+60) and economics (F5 −0.99), but the distinguishing trait is
**electoral skepticism** (F2 +0.62) — unlike PRG/LIB, DSA *distrusts* elections. It is the
radical **anti-establishment** left, where PRG is the radical **institutional** left.

*Within the bloc:* LBR (mainstream, closest to country) → LIB (strong liberal,
racial-justice, trusting) → PRG (maximalist, trusting) → DSA (maximalist, skeptical). Trust in
elections (F2) separates the two vanguards; distance-from-center separates LBR from the rest.

---

## CENTER — OAO, STY, CUP

Not one "mush" — three genuinely different ways of being central. They are the three parties
closest to the electorate, but for opposite reasons, and they diverge hard on **electoral
trust**.

**CUP — Civic Union** (89 seats · 9.3%). The **institutionalist** center and the party closest
to the electorate overall (meanDev 7.0). Its one sharp signature is **electoral trust** (F2
−1.00): U.S. elections are fair (94%, Δ+31), the 2024 count was fair (100%, Δ+25). Mildly right
on order (F1 +0.34) and religion (F4 +0.27), dead-center economically (F5 +0.04). Low
ambivalence (19) — it *does* hold positions; they're just the country's consensus ones.

**STY — Solidarity** (129 seats · 14.3%). The **ambivalent** center. Its ambivalence (29) is
high but *not* unique — POP (27) and CON (26) are right there, and all three are equally
cross-pressured at the individual level (overdispersion ≈1). What sets STY apart is that its
ambivalence is **unanchored**: only **2** deviant planks and meanDev 8.0, versus POP's 19 /
CON's 14. POP and CON are ambivalent *around a hard core* (immigration, order) — the neutrality
is a texture on a firm identity; STY has the same neutrality with no core to anchor it, so the
ambivalence *is* the identity. Its only real leans are **electoral skepticism** (F2 +0.80 — the
mirror image of CUP) and mild religiosity (F4 +0.34). A large, disengaged, cross-pressured
moderate bloc defined by the absence of a signature.

**OAO — Order & Opportunity** (15 seats · 5.3%). The **cross-cutting** center: economically
progressive left (F5 −0.78) but strongly **pro-order** (F1 +0.92). Signature is law-and-order
fused with an open immigration/economic stance: increase police 100% (Δ+43), renew surveillance
72%, deny asylum 100% — *and* grant undocumented legal status 90%. Otherwise mainstream (39
mainstream-strong, 10 deviant, meanDev 10.6) and election-trusting (F2 −0.77). It doesn't fit
the left–right line, which is why it reads as center despite sharp positions.

*Within the bloc:* CUP (trusts institutions, consensus positions) and STY (skeptical of
institutions, no positions) are near-opposites on F2 despite both being "center"; OAO is the
odd one, central only because its order-conservatism and economic-progressivism cancel on the
left–right axis.

---

## RIGHT — POP, NAT, CON

Shared floor: all three are populist-conservative (F5 positive), pro-order (F1 positive), and
religious-traditional (F4 positive). They split on **how extreme** and **how anti-establishment**.

**CON — Conservative** (201 seats · 17.7%). The **mainstream** right and the largest party in
the model. Strong on the consensus-right positions — increase police 100%, build the wall 91%,
deny asylum 100% — but only 14 deviant planks and meanDev 14.8, i.e. much closer to the
electorate than NAT. Near-center on electoral trust (F2 −0.03) and notably ambivalent (26),
especially on racial items. Establishment conservatism: firm on order, not a skeptic, not a
maximalist.

**NAT — Nationalist** (41 seats · 8.7%). The **maximalist** right — most populist-conservative
(F5 +1.72) and most religious-traditional (F4 +0.94) on the board, meanDev 28.5, 49 deviant
planks. Defined by hard opposition across the board: no Dreamer pathway (0.3%, Δ−70), no legal
status (0.2%), no top-rate rise (8%), no EPA CO₂ authority (5%), no renewables mandate (9%).
Electorally skeptical (F2 +0.52). It is CON's positions pushed to the pole and extended to
climate and taxes.

**POP — Populist** (106 seats · 10.4%). The **anti-establishment** right — most electorally
skeptical party on the board (F2 +0.93), high populist-conservatism (F5 +1.13), but *lower* on
order than CON/NAT (F1 +0.26) and high ambivalence (27). Signature is immigration hardline
(wall 87%, no legal status 12%, no Dreamer pathway 28%) and anti-racial-justice, but it's
markedly non-committal elsewhere. Populism defined by grievance and skepticism more than by a
full conservative program.

*Within the bloc:* CON (mainstream, largest, order-focused, trusts elections) → NAT
(maximalist nationalist-traditionalist, most extreme) → POP (skeptical, immigration-driven,
ambivalent elsewhere). Electoral skepticism (F2) and religiosity (F4) separate NAT/POP from
the establishment CON.

---

## Summary of what makes each *distinct*

- **PRG** — most distinct from the electorate; maximalist civil-libertarian left, commits on everything.
- **DSA** — radical left that also distrusts elections (anti-establishment).
- **LIB** — strong secular liberalism centered on racial justice and immigration; trusts institutions.
- **LBR** — mainstream progressive consensus; the left position closest to the country.
- **OAO** — law-and-order + economic progressivism; cross-cuts the left–right axis.
- **STY** — the disengaged, electorally-skeptical middle; ambivalent like POP/CON but, unlike them, with no signature to anchor it.
- **CUP** — the institutionalist middle, defined by trust in elections and consensus positions.
- **POP** — grievance populism: immigration hardline + electoral skepticism, non-committal elsewhere.
- **NAT** — nationalist-traditionalist maximalism across immigration, taxes, and climate.
- **CON** — mainstream establishment right; firm on order, close to the electorate, not a skeptic.
