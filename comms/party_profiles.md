# American Political Party Profiles

*A guide to the political types in a proportional representation simulation based on CES 2024 survey data (N=45,707)*

---

## Introduction

This document profiles the political parties and candidate types that emerge when you run American survey data through a proportional representation system. The underlying data comes from the 2024 Cooperative Election Study, one of the largest academic surveys of American political opinion, with responses from over 45,000 adults weighted to match the national population. These parties were not invented — they were discovered. Researchers applied clustering algorithms to how Americans actually answered 172 policy and demographic questions, and the nine parties described below are the natural groupings that fell out. The question this project asks is simple: if Americans could vote for a party that actually matched their views, what would the map look like?

Five underlying dimensions replace the single left-right axis that dominates American political conversation. The first is **Security & Order** — whether someone wants more police, more border enforcement, and more surveillance. The second is **Electoral Skepticism** — whether someone believes American elections are run fairly. The third is **Government Distrust** — general low trust in federal and state institutions (this dimension turns out to be nearly identical across all winning parties and does not differentiate them). The fourth is **Religious Traditionalism** — the weight someone gives to church attendance, traditional views on abortion, and traditional views on marriage. The fifth is **Populist Conservatism** — the cluster of attitudes around immigration restriction, fiscal conservatism, and racial traditionalism that defines the populist right. Some party profiles look contradictory at first glance. They usually stop looking contradictory once you see all five dimensions at once.

No party holds a majority. The simulation fills an 873-seat House, and the three largest parties — Conservative (202 seats, 23.1%), Social Democrat (164 seats, 18.8%), and Solidarity (130 seats, 14.9%) — collectively hold just over half. Every legislative majority requires coalition-building across parties that disagree on at least two or three fundamental issues. That is the design. The system forces the negotiation that the current two-party structure conceals behind partisan loyalty.

### Two Candidate Fields

The simulation tests two different ways candidates might emerge in a multi-party system:

**The crossover field** puts 37 candidates into the race: 9 who run on the pure party platform, plus 28 *crossover candidates* — politicians from one party who break from their base on a single ideological dimension. A crossover candidate is defined by a shift on one of three axes: Security & Order (tougher or softer on policing and enforcement), Anti-Establishment (more or less institutional distrust), or Populist Conservatism (more or less immigration-restrictionist). The result is candidates like "a Solidarity senator who runs tougher on security" or "a Social Democrat who softens on enforcement" — the kind of politicians who exist in every real legislature. Crossover candidates test whether voters reward ideological flexibility.

**The pure partisan field** puts 27 candidates into the race: 3 per party, all running on the identical party platform. No one breaks from their base on any dimension. This tests the structural effect of proportional voting alone — what happens when parties compete as monoliths.

Each field is then counted two ways: **Instant Runoff Voting (IRV)**, which eliminates the last-place candidate each round and redistributes their votes until someone crosses 50%; and **Condorcet** (ranked pairs), which finds the candidate who would beat every other candidate in a head-to-head matchup. These two methods often produce different winners because they reward different things — IRV rewards first-choice accumulation, Condorcet rewards broad acceptability. The combination of two fields and two methods produces four scenarios, and the results diverge in ways that matter.

---

## The Presidency

**Solidarity wins the presidency in three of four scenarios — but a different kind of Solidarity each time.**

| Scenario | Winner | Final margin |
|----------|--------|-------------|
| Crossover IRV | **STY_hi_so** (Solidarity, tough on security) | 60.3% vs. SD_lo_es 39.7% |
| Crossover Condorcet | **STY_hi_so** (same candidate) | Beats all opponents; closest: SD_lo_es at 39.7% |
| Pure partisan IRV | **SD_1** (Social Democrat) | 54.4% vs. CON_1 45.6% |
| Pure partisan Condorcet | **STY_1** (Solidarity, pure) | Beats all opponents; closest: SD_1 at 40.9% |

In the crossover field, both methods converge on the same president: a Solidarity candidate who breaks from the party base by running tougher on security. STY_hi_so's factor profile shifts Security & Order from the base STY position of −0.45 to −0.27 — still left of center on enforcement, but meaningfully less anti-police than the median Solidarity voter. This is the Solidarity candidate who can credibly promise working-class economic policy while also promising not to defund anyone's local police department. In the final IRV round, STY_hi_so defeats SD_lo_es (a Social Democrat who softens on enforcement) by 60–40 after absorbing transfers from eliminated Conservative and Populist voters who prefer any candidate with security credibility over a pure civil-libertarian Social Democrat.

In the pure partisan field, the two methods diverge. IRV elects a **Social Democrat** — SD_1 wins the final round 54.4% to 45.6% against CON_1 after Solidarity is eliminated in round 3 and its transfers split roughly evenly. Condorcet elects a **pure Solidarity partisan** — STY_1 beats every other candidate in head-to-head matchups, including SD_1 by a margin of 18 points. The divergence illustrates a structural property: IRV penalizes candidates who aren't many voters' first choice (STY_1 starts in third at 18.4%) even when those candidates would beat everyone one-on-one.

**What each president signs and vetoes:**

The three presidents — STY_hi_so, SD_1, and STY_1 — produce meaningfully different legislative records despite all sitting left of center.

**STY_hi_so** (crossover president) governs as a working-class centrist with a security edge. Signs the 2017 tax cut extension, border enforcement, fossil fuel production, the gender transition ban for minors, parental consent for school pronoun changes, and school vouchers. Vetoes the corporate tax hike (47% coalition support), the congressional abortion access protection (48%), and federal same-sex marriage recognition (48.5%) — all measures where the "tough on security" Solidarity coalition splits just below the 50% threshold. This president represents the Solidarity voter who goes to church, distrusts the political establishment, and doesn't want anyone defunding their local police.

**SD_1** (pure IRV president) governs as a progressive economic reformer. Signs the corporate tax hike, abortion access protection, same-sex marriage recognition, and student loan forgiveness. Vetoes the 2017 tax cut extension (49% support), the gender transition ban for minors (49%), parental consent for school pronouns (46%), school vouchers (44%), fossil fuel production increases (36%), and Medicaid work requirements (45%). This president represents the secular, racially diverse, working-class Social Democrat who views cultural conservatism as incompatible with the party's identity.

**STY_1** (pure Condorcet president) splits the difference. Signs same-sex marriage (54%), the gender transition ban (60%), school vouchers (61%), abortion access protection (53%), and the tax cut extension (61%). Vetoes police expansion (35%), Medicaid work requirements (49%), asylum denial (40%), and the TikTok ban (41%). This president — the pure Solidarity partisan — is the most centrist of the three, signing measures from both sides that clear 50% in the Solidarity coalition.

The pattern: where STY_hi_so and SD_1 disagree on every cultural issue, STY_1 governs the middle. The crossover field produces a president with a sharper ideological profile than the pure partisan field's Condorcet winner.

---

## Part I: The Nine Parties

---

### Progressive (PRG) — 14 House Seats (1.6%)

Progressives are the smallest party in the system, but they are not an outlier — they are a pole. They sit at the extreme end of nearly every dimension: the most anti-enforcement, the most secular, the most economically redistributive, the most permissive on immigration. What animates them is not just policy positions but a coherent worldview in which government's primary function is to actively reduce inequality — in income, in race, in gender, in access to healthcare. They want federal power used aggressively and unapologetically toward those ends. The fact that only 14 House seats correspond to this profile reflects not that these views are rare, but that they are concentrated: young, urban, highly educated, and dispersed across districts that already elect other left-leaning candidates.

**Who they are:**
- Median age 41 · 53.1% male · 76.3% white · 60.2% 4-yr+ degree · 32.6% city
- Income: upper-middle ($70–80k) · 43.9% married · 11.4% own a gun · 28.1% LGBTQ+ · 4.3% born-again evangelical
- 9.3% current union members · 4.3% veterans

**Where they stand:**
- Support DACA/Dreamer pathway: 100%
- Renewable energy mandate: 98.0%
- Medicaid expansion: 99.3%
- Assault rifle ban: 96.5%
- Raise corporate taxes: 97.3%

**Unusually for American politics:**
- 90.8% of Progressives say U.S. elections are run fairly — the most institutionally trusting of any left party. Despite holding radical positions on nearly every policy issue, Progressives show a deep commitment to the democratic process itself, distinguishing them sharply from DSA, where only 32.8% believe elections are run fairly.
- Despite averaging age 41 and being 28.1% LGBTQ+, PRG is 53% male — a reminder that progressive politics draws heavily from educated men alongside its more visible feminist and queer constituencies.

**Senate seats:** 0 in all four scenarios. PRG's support is too concentrated in a handful of urban House districts to command a state-level plurality under any method or candidate field.

---

### Democratic Socialists (DSA) — 22 House Seats (2.5%)

The Democratic Socialists are ideologically close to Progressives on economic and social policy, but they come from a different cultural place. DSA has the highest LGBTQ+ share of any party — nearly four in ten members identify as LGBTQ+ — and the youngest median age (33) in the system. What distinguishes DSA from PRG is not what they want from government but how they feel about the government they have. DSA members are deeply skeptical that American elections are run fairly, a sentiment that sits in sharp tension with their progressive politics but makes sense when you consider a community with long experience of disenfranchisement and structural exclusion. They want universal healthcare, aggressive redistribution, and an end to immigration enforcement — and they do not trust the current system to deliver any of it.

**Who they are:**
- Median age 33 · 32.8% male · 65.9% white · 42.7% 4-yr+ degree · 30.0% city
- Income: middle ($60–70k) · 29.0% married · 9.8% own a gun · 38.6% LGBTQ+ · 7.3% born-again evangelical
- 7.1% current union members · 3.0% veterans

**Where they stand:**
- Support DACA/Dreamer pathway: 100%
- Medicaid expansion: 98.8%
- EPA CO2 regulation: 96.9%
- Raise corporate taxes: 88.5%
- Assault rifle ban: 93.2%

**Unusually for American politics:**
- Only 32.8% of DSA members believe U.S. elections are run fairly — the lowest of any party in the system, below even Populist (36.4%) and Nationalist (47.9%). Electoral distrust is not a right-wing monopoly; for a party that is 38.6% LGBTQ+ and 34.1% non-white, there are independent reasons to doubt whether the system delivers equal treatment.
- DSA has the lowest marriage rate of any party (29.0%) and among the highest non-voting rates in 2020 (27.5% did not vote), a combination that reflects a young, non-traditional left base that remains substantially disengaged from electoral participation despite deep political conviction.

**Senate seats:** 0 in all four scenarios. Like PRG, DSA's vote share never commands a state-level plurality; its support is too young, too urban, and too dispersed.

---

### Liberal (LIB) — 93 House Seats (10.7%)

Liberals are the third-largest left-leaning party, and in many ways the most surprising. They are the oldest left-leaning party (median age 55), whiter and more male than most of their ideological neighbors, and among the least LGBTQ+ of the left-leaning parties. Their urban share (29.7% city) is nearly identical to Social Democrat (30.7%) — LIB is not particularly rural, just suburban and spread across smaller metros rather than dense urban cores. What unifies them is a civil libertarian streak: they want government out of the bedroom and the boardroom alike, and they trust electoral institutions more than any other party in the system. Their economics are unambiguously left — near-universal support for taxing high earners, EPA regulation, and renewable mandates — but they break from their left-leaning neighbors on security and immigration, supporting border patrols at 75.3% and far readier to restrict gender-transition care for minors. They are older, relatively prosperous, and more likely to personally own a gun than PRG or DSA, while still supporting universal background checks at 99.6%.

**Who they are:**
- Median age 55 · 52.0% male · 69.4% white · 48.5% 4-yr+ degree · 29.7% city
- Income: upper-middle ($70–80k) · 49.1% married · 17.0% own a gun · 14.3% LGBTQ+ · 14.1% born-again evangelical
- 8.0% current union members · 8.0% veterans

**Where they stand:**
- Universal background checks: 99.6%
- Support DACA/Dreamer pathway: 100%
- EPA CO2 regulation: 95.2%
- Renewable energy mandate: 94.3%
- Medicaid expansion: 95.4%

**Unusually for American politics:**
- 99.6% support universal background checks even as 17.0% personally own guns — more gun ownership than PRG (11.4%) or DSA (9.8%). Their libertarianism cuts both ways: they trust individuals with firearms while also trusting institutions — 94.5% say U.S. elections are run fairly, the highest of any party in the system.
- 32.6% of Liberals support banning gender-transition surgery for minors — roughly double the PRG rate (15.6%) and well above DSA (21.7%) — reflecting a genuine moderation on gender issues that coexists with broadly progressive economics.

**Senate seats:** Pure partisan IRV: 1 *(Vermont)*. All other scenarios: 0. LIB's civil-libertarian profile wins Vermont under IRV when the elimination order favors its second-choice accumulation, but it cannot command a plurality in any state under Condorcet or in the crossover field where axis-shifted SD and STY candidates absorb its voters.

---

### Social Democrat (SD) — 164 House Seats (18.8%)

Social Democrats are the second-largest party in the system and, in many ways, the most recognizable to European observers of American politics. They want an expanded welfare state, regulated markets, labor protections, and immigration reform — the European center-left platform, applied to American conditions. They are disproportionately Black, Hispanic, and working-class, with a median age matching the national center and ideological self-placement of 2.9 on a 7-point scale. They trust elections at roughly the national rate, support Medicaid expansion at near-universal rates, and are strong backers of clean energy. What makes them politically complicated is their working-class base, which produces genuine ambivalence on immigration — not hostility, but a calculation about labor market competition and community change that distinguishes them from their left-leaning neighbors.

**Who they are:**
- Median age 43 · 44.6% male · 56.7% white · 35.1% 4-yr+ degree · 30.7% city
- Income: middle ($60–70k) · 37.5% married · 18.2% own a gun · 14.6% LGBTQ+ · 19.2% born-again evangelical
- 6.4% current union members · 6.7% veterans

**Where they stand:**
- Medicaid expansion: 93.5%
- Renewable energy mandate: 90.3%
- Support DACA/Dreamer pathway: 98.4%
- Infrastructure spending: 90.7%
- Universal background checks: 98.4%

**Unusually for American politics:**
- 72.2% support increasing border patrols — a clear majority — reflecting a working-class base more ambivalent on immigration than a "liberal" label would suggest. SD simultaneously backs a permanent Dreamer pathway at 98.4% while supporting border enforcement at 72.2%, a combination that reads as labor-protection rather than nativism.
- SD is far more racially diverse than its size-peer Conservative (78.4% white): SD is 56.7% white, 16.4% Black, and 13.1% Hispanic, and largely secular — only 11.8% attend church weekly and 19.2% are born-again. Its identity is rooted in a multiracial working class, not the college-educated progressive elite its policy positions might suggest.

**Senate seats:** SD is the dominant senate party under IRV and competitive under Condorcet. Crossover IRV: 27 seats (the largest total in any scenario, winning through axis-shifted variants that soften on security or tone down anti-establishment rhetoric). Crossover Condorcet: 11 seats. Pure partisan IRV: 26 seats. Pure partisan Condorcet: 15 seats. SD's strength under IRV reflects its second-choice appeal — voters who rank SD second after their preferred party is eliminated.

---

### Solidarity (STY) — 130 House Seats (14.9%)

Solidarity is the most politically disorienting party in the system, and arguably the most important one to understand. They are the youngest working-class party (median age 38), majority female (60.7%), majority non-white (56.6%), lowest household income of any party in the system, and — most surprisingly — 37.7% born-again evangelical. Their economics lean center-left: they support infrastructure spending and Medicaid expansion, but express ambivalence on immigration and are more skeptical of corporate tax hikes than their left-leaning neighbors. What makes STY genuinely novel is their combination of economic marginalization with deep institutional distrust: just 35.5% believe national elections are run fairly — among the lowest in the system, alongside Populist (36.4%) and DSA (32.8%). Nearly half (44%) didn't vote in 2020. They are the party of Americans most left behind by the economy — low income, limited education, religiously conservative, and alienated from both political parties.

**Who they are:**
- Median age 38 · 39.3% male · 43.4% white · 23.0% 4-yr+ degree · 36.3% city
- Income: working-class ($40–50k) · 34.2% married · 18.8% own a gun · 11.7% LGBTQ+ · 37.7% born-again evangelical
- 4.4% current union members · 5.5% veterans

**Where they stand:**
- Universal background checks: 88.8%
- Support DACA/Dreamer pathway: 86.7%
- Medicaid expansion: 84.3%
- Raise corporate taxes: 53.4%
- Increase police by 10%: just 35.0% support

**Unusually for American politics:**
- Just 35.5% of STY believe national elections are run fairly — as skeptical as Populist (36.4%) — yet only 16.3% voted for Trump in 2020 and 44% didn't vote at all. STY's electoral skepticism comes from the left, not the right: for a majority non-white, lowest-income, female-majority party, distrust of institutions reflects lived experience of exclusion rather than election denialism.
- STY is the only party that combines majority non-white membership, majority female membership, the lowest income in the system, and 37.7% born-again evangelical identity — a demographic profile that fits no existing political coalition and explains why they are estranged from both parties rather than firmly attached to either.

**Senate seats:** STY dominates under Condorcet — where broad head-to-head acceptability matters most — and competes strongly under IRV. Crossover Condorcet: 34 seats (the largest total in any scenario, overwhelmingly through the establishment-friendly STY_lo_es variant). Crossover IRV: 19 seats. Pure partisan Condorcet: 33 seats. Pure partisan IRV: 11 seats. STY's Condorcet dominance reflects its position as the spatial median of the multi-party field — the party that the most other voters can tolerate even if it isn't their first choice.

---

### Civic Union Party (CUP) — 103 House Seats (11.8%)

The Civic Union Party occupies a genuinely unusual political position: moderate on almost everything, deeply religious, and among the most trusting of elections of any party in the system. Its members describe themselves as slightly conservative (3.6 on the 7-point scale) and voted 41.9% for Trump and 33.2% for Biden in 2020 — making them a Trump-plurality party that nonetheless trusts elections more than almost any other constituency in the simulation. They are significantly evangelical (43% born-again), older (median age 51), homeowning, and married — the religious moderate who is economically pragmatic, culturally traditional without being extreme, and the genuine swing-right voter the two-party system has long fought over. They support background checks, Medicaid expansion, and infrastructure spending, but also back border enforcement and are split on abortion.

**Who they are:**
- Median age 51 · 54.4% male · 66.2% white · 29.0% 4-yr+ degree · 27.2% city
- Income: lower-middle ($50–60k) · 47.5% married · 29.0% own a gun · 5.5% LGBTQ+ · 43.0% born-again evangelical
- 5.4% current union members · 8.7% veterans

**Where they stand:**
- Universal background checks: 94.9%
- Medicaid expansion: 79.1%
- Infrastructure spending: 79.7%
- Increase border patrols: 93.2%
- Support same-sex marriage: 55.8%

**Unusually for American politics:**
- 93.8% of CUP say U.S. elections are run fairly — among the highest in the system. Yet 41.9% voted for Trump in 2020 and only 33.2% for Biden, making CUP the most genuinely swing-right party in the system, not the "reluctant Democrat" the two-party framing would suggest. They lean Trump but trust the elections Biden won — a combination that is genuinely unusual.
- Despite being 43.0% born-again evangelical and favoring stricter abortion limits (median cutoff 12 weeks), a 55.8% majority still support federal recognition of same-sex marriage — suggesting a religious conservatism focused on reproductive rather than sexual ethics.

**Senate seats:** CUP rarely wins outright but its moderate position makes it a kingmaker in coalitions. Crossover IRV: 1 seat *(South Dakota — via CUP_hi_pc, a Civic Union Party candidate who runs more populist-conservative)*. Pure partisan Condorcet: 1 seat *(Wyoming)*. All other scenarios: 0. CUP's spatial center position means other parties' crossover candidates absorb its voters before CUP itself can win.

---

### Conservative (CON) — 202 House Seats (23.1%)

Conservatives are the largest party in the system and the dominant force on the center-right. They are high on Security & Order, moderate on Religious Traditionalism, trusting of elections, and sitting at a moderate +0.44 on Populist Conservatism — meaningfully right but not at the populist extreme. They are older, whiter, and more married than the national average, with above-average incomes, and near gender parity (49% male). Their politics are recognizable as the Eisenhower-to-Reagan Republican tradition: law enforcement, border security, religious values, low taxes, and a belief that American institutions basically work. They are hawkish on immigration and police funding, opposed to most climate regulation, and split nearly in half on some social issues. What distinguishes them from NAT is not just intensity but institutional orientation — Conservatives trust elections and, to a striking degree, trust background checks.

**Who they are:**
- Median age 59 · 49.0% male · 78.4% white · 30.3% 4-yr+ degree · 20.5% city
- Income: middle ($60–70k) · 56.2% married · 39.2% own a gun · 3.4% LGBTQ+ · 42.6% born-again evangelical
- 4.1% current union members · 13.6% veterans

**Where they stand:**
- Extend 2017 tax cuts: 85.1%
- Increase border patrols: 99.5%
- Increase police funding: 99.7%
- Deny asylum seekers: 99.8%
- ACA repeal: 62.1%

**Unusually for American politics:**
- 93.8% of Conservatives support universal background checks on gun sales — better than nine in ten. This is the signature cross-cutting finding for CON: a party that is 39.2% gun-owning and 99.5% pro-border-patrol nonetheless backs a policy their partisan analog in the two-party system has blocked for decades. Their gun politics are about ownership and rights, not about blocking all regulation.
- 64.0% of Conservatives believe national elections are run fairly — almost exactly the national average (62.8%) — reflecting an institutional conservatism that CON shares with CUP but not with POP (36.4% believe elections fair) or NAT (47.9%).

**Senate seats:** CON wins few seats under Condorcet but breaks through under IRV — especially in the pure partisan field where its strong first-choice base survives elimination rounds. Crossover Condorcet: 1 seat *(Tennessee — via CON_lo_pc, a Conservative softened on populism)*. Crossover IRV: 3 seats *(Idaho via CON_hi_pc, Oklahoma via CON_lo_es, Wyoming via base CON)*. Pure partisan Condorcet: 1 seat *(Tennessee)*. Pure partisan IRV: 11 seats *(Arkansas, Idaho, Indiana, Iowa, Kentucky, Michigan, Montana, North Carolina, North Dakota, Ohio, Tennessee)*. The IRV–Condorcet gap is dramatic: CON accumulates first-choice votes in contested states but loses head-to-head matchups to the centrist STY and SD candidates who attract broader second-choice support.

---

### Populist (POP) — 99 House Seats (11.3%)

Populist is the Tea Party and MAGA populism stripped of the Republican establishment — deeply suspicious that elections are run fairly, intensely restrictionist on immigration, and socially conservative without being particularly evangelical. Populist members are older (median age 46), majority male (51.2%), rural, and low-education relative to income. They feel left behind and channel that anxiety into distrust of both elections and elites. What makes Populist genuinely different from Conservative is their anti-institutional streak: just 36.4% believe national elections are run fairly and 80.4% express low trust in the federal government — a suspicion of concentrated power that reaches even into law enforcement, where Populist is markedly cooler on policing than the rest of the right. They are not reflexively pro-establishment; they are pro-themselves, against a system they believe is rigged by people who are not like them.

**Who they are:**
- Median age 46 · 51.2% male · 70.2% white · 25.8% 4-yr+ degree · 23.1% city
- Income: lower-middle ($50–60k) · 45.5% married · 37.3% own a gun · 7.1% LGBTQ+ · 39.9% born-again evangelical
- 4.6% current union members · 9.5% veterans

**Where they stand:**
- Increase border patrols: 89.1%
- Deny asylum seekers: 87.1%
- Extend 2017 tax cuts: 75.7%
- ACA repeal: 67.2%
- Believe elections are run fairly: 36.4%

**Unusually for American politics:**
- Just 44.2% of Populist support increasing police funding — the lowest of any right-leaning party and far below Conservative (99.7%) — and 19.5% actively want to cut it. Populist's anti-establishment suspicion extends even to law enforcement, the one institution the two-party right treats as sacrosanct.
- 80.4% support universal background checks despite being among the most immigration-restrictionist parties — suggesting gun-regulation opposition in the two-party system reflects partisan packaging more than genuine voter preference.

**Senate seats:** POP wins seats primarily through its establishment-friendly crossover variant (POP_lo_es), which tones down anti-establishment rhetoric enough to attract transfers from moderate voters. Crossover Condorcet: 5 seats *(Idaho, North Dakota, Oklahoma, South Dakota, Wyoming)*. Crossover IRV: 1 seat *(North Dakota)*. Pure partisan Condorcet: 1 seat *(Idaho)*. Pure partisan IRV: 2 seats *(Arizona, Wyoming)*. POP's Condorcet success in the crossover field reflects a surprising dynamic: when a Populist candidate dials back institutional distrust, the resulting profile — fiscally populist, immigration-restrictionist, but trusting enough of elections to seem governable — commands a plurality in deeply conservative states.

---

### Nationalist (NAT) — 46 House Seats (5.3%)

The Nationalist Party is the populist far-right pole of the system. At +1.51 on Populist Conservatism — a full standard deviation above the next highest type — they are an outlier even within a system designed to find outliers. They are the oldest party (median age 60), the most male (63.6%), the most rural (only 15.9% city), and the most evangelical (47.7% born-again) — but they are also the second highest income party in the simulation, and more college-educated (39.3%) than Conservative (30.3%) or Populist (25.8%). NAT is not the economically precarious working class; it is prosperous older white rural Christians who have organized their politics around immigration restriction and cultural anxiety rather than economic grievance. They want borders enforced, firearms secured, tradition maintained, and a specific vision of American national identity preserved. Their 89.4% Trump support in 2020 and near-universal immigration restriction coexist with household incomes that benefit substantially from the tax cuts they demand.

**Who they are:**
- Median age 60 · 63.6% male · 81.2% white · 39.3% 4-yr+ degree · 15.9% city
- Income: upper-middle ($70–80k) · 63.1% married · 54.9% own a gun · 3.3% LGBTQ+ · 47.7% born-again evangelical
- 5.5% current union members · 18.1% veterans

**Where they stand:**
- Increase border patrols: 100%
- Deny asylum seekers: 100%
- Extend 2017 tax cuts: 93.8%
- Oppose same-sex marriage: 73.5% (only 26.5% in favor)
- Believe elections are run fairly: 47.9%

**Unusually for American politics:**
- Despite being the most evangelical party (47.7% born-again) and the most rural (15.9% city), NAT ranks second in household income — a profile of prosperous older white rural Christians, not the economically precarious working class its anti-establishment rhetoric might suggest. NAT is more college-educated (39.3%) than Conservative (30.3%) or Populist (25.8%), and their near-universal support for the 2017 tax cuts aligns with their actual economic position rather than contradicting it.
- 75.8% support universal background checks — a solid majority, even in the most nativist and gun-owning party in the system.

**Senate seats:** 0 in all four scenarios. NAT's extreme F5 position (+1.51) places it too far from the median voter to win any state-level plurality — even in the most conservative states, where crossover Conservative or Populist candidates absorb its voters by running closer to the center.

---

## Part II: The Crossover Senate

When candidates can break from their party on a single ideological dimension, the Senate map transforms. Instead of nine parties competing as monoliths, 37 candidates compete — and the winners are overwhelmingly crossover types who figured out which dimension to shift on. The first-named party is the base identity; the axis shift describes the direction they moved to win.

Three axes produce all the variation: **Security & Order** (tougher or softer on policing and enforcement), **Anti-Establishment** (more or less institutional distrust), and **Populist Conservatism** (more or less immigration-restrictionist and racially traditional). A candidate shifts on only one axis at a time — they keep their party's position on everything else.

---

### STY_lo_es — The Establishment Solidarity Senator
**Condorcet: 20 seats · IRV: 10 seats**

*A Solidarity senator who tones down anti-establishment rhetoric and signals trust in institutions.*

This is the most successful crossover type in the system. By shifting from STY's base Electoral Skepticism of +0.66 down to +0.51, this candidate keeps Solidarity's working-class economics, its skepticism of police expansion, and its multi-racial coalition — while dropping just enough institutional distrust to become broadly acceptable in head-to-head matchups against every other candidate. Under Condorcet, STY_lo_es wins 20 states spanning every region: Alabama, Alaska, Arkansas, California, Colorado, Indiana, Kentucky, Michigan, Montana, Nebraska, New Jersey, New Mexico, New York, North Carolina, Ohio, Oregon, Texas, Virginia, Washington, and Wisconsin. Under IRV, where first-choice intensity matters more, the count drops to 10 as SD variants absorb some of these states.

**Factor profile:** F1 −0.45 (anti-enforcement) · F2 +0.51 (mildly skeptical) · F4 +0.17 (moderate religious) · F5 −0.06 (near-center)

**Why it works:** Condorcet rewards the candidate who offends the fewest voters. STY_lo_es is still a Solidarity candidate — still working-class, still pro-Medicaid, still anti-police-expansion — but the establishment-friendliness means center-right voters rank it ahead of more extreme options. When every head-to-head matchup is resolved, the candidate nobody hates beats the candidates half the electorate loves and half despises.

---

### SD_lo_so — The Civil Libertarian Social Democrat
**Condorcet: 1 seat · IRV: 11 seats**

*A Social Democrat who runs softer on security — more skeptical of policing, less supportive of enforcement.*

SD_lo_so shifts Security & Order from SD's base of −0.41 down to −0.60, deepening the civil-libertarian streak while keeping SD's progressive economics, institutional trust, and secular profile. Under IRV, this candidate dominates the blue-state corridor: California, Colorado, Illinois, Minnesota, New Hampshire, New Jersey, New Mexico, New York, Oregon, Pennsylvania, and Washington. Under Condorcet, it wins only New Hampshire — the rest of those states go to the broadly-acceptable STY_lo_es instead.

**Factor profile:** F1 −0.60 (strongly anti-enforcement) · F2 −0.03 (trusts elections) · F4 −0.35 (secular) · F5 −0.56 (progressive)

**Why it works under IRV:** In states with educated, secular, progressive-leaning electorates, SD_lo_so accumulates first-choice votes from the LIB and PRG bases whose members rank it first over the base SD candidate. As more conservative candidates are eliminated, SD_lo_so's transfers hold. The civil-libertarian shift is a signal: *I am the most anti-surveillance, anti-enforcement option you can elect who also has a realistic chance of winning.*

---

### SD_lo_es — The Establishment Social Democrat
**Condorcet: 4 seats · IRV: 10 seats**

*A Social Democrat who signals institutional trust and tones down anti-establishment sentiment.*

SD_lo_es shifts Electoral Skepticism from SD's base of −0.03 to −0.18 — a subtle move that makes the candidate even more trusting of elections than base SD. This resonates in states where the center-left electorate wants progressive economics without populist grievance. Under IRV, it wins: Arizona, Delaware, DC, Kansas, Maryland, Massachusetts, Michigan, Vermont, Virginia, and Wisconsin. Under Condorcet: DC, Illinois, Massachusetts, Vermont.

**Factor profile:** F1 −0.41 (anti-enforcement) · F2 −0.18 (trusts elections) · F4 −0.35 (secular) · F5 −0.56 (progressive)

**Why it works:** In states with large educated-professional populations (Massachusetts, Virginia, Maryland), the establishment-friendly Social Democrat wins by being the candidate most associated with institutional stability. Where SD_lo_so appeals to the libertarian left, SD_lo_es appeals to the institutional left.

---

### STY_hi_so — The Law-and-Order Solidarity Senator
**Condorcet: 5 seats · IRV: 5 seats**

*A Solidarity senator who breaks right on security — more pro-police, tougher on enforcement.*

STY_hi_so shifts Security & Order from STY's base of −0.45 to −0.27, moving meaningfully toward the center on policing while keeping everything else: the working-class identity, the electoral skepticism, the multi-racial base. This is the same candidate type that wins the presidency — and it wins senate seats in states where the conservative working class is large enough to reward a Solidarity politician willing to say "I support your local police department." States: Louisiana, Missouri, Nevada, South Carolina, and West Virginia under both methods; also Tennessee under IRV (replacing the Condorcet's CON_lo_pc winner).

**Factor profile:** F1 −0.27 (moderate on enforcement) · F2 +0.66 (electorally skeptical) · F4 +0.17 (moderate religious) · F5 −0.06 (near-center)

**Why it works:** In the Deep South and Appalachia, a pure Solidarity candidate's anti-police stance is disqualifying for enough voters to prevent a win. STY_hi_so makes one calculated concession — police and enforcement — while keeping the economic populism that animates Solidarity's base. The result: a senator who votes for Medicaid expansion and against ACA repeal, but who also votes for border funding and won't defund anyone's sheriff's department.

---

### STY_lo_pc — The Progressive Solidarity Senator
**Condorcet: 4 seats · IRV: 3 seats**

*A Solidarity senator who softens on populist conservatism — more progressive on immigration and race.*

STY_lo_pc shifts Populist Conservatism from STY's base of −0.06 down to −0.27, pulling the candidate leftward on immigration and racial attitudes while keeping Solidarity's working-class economics and institutional skepticism. States under Condorcet: Connecticut, Florida, Georgia, Hawaii. Under IRV: Florida, Hawaii, Mississippi.

**Factor profile:** F1 −0.45 (anti-enforcement) · F2 +0.66 (electorally skeptical) · F4 +0.17 (moderate religious) · F5 −0.27 (progressive-leaning)

**Why it works:** In diverse states with large non-white working-class populations (Florida, Georgia, Hawaii), the base STY position is already close to the state median — but a slight leftward shift on race and immigration picks up enough additional minority voters to command a plurality. This is the Solidarity senator for states where the multi-racial coalition is the majority.

---

### SD_hi_so — The Security-Minded Social Democrat
**Condorcet: 5 seats · IRV: 1 seat**

*A Social Democrat who runs tougher on security — more supportive of policing and enforcement.*

SD_hi_so shifts Security & Order from SD's base of −0.41 to −0.23, making a meaningful concession toward law-and-order while keeping progressive economics. Under Condorcet, this candidate wins in states with mixed electorates where progressive economics need a security credential: Delaware, Maine, Minnesota, Pennsylvania, Rhode Island. Under IRV, only Rhode Island — the rest are absorbed by other SD or STY variants.

**Factor profile:** F1 −0.23 (moderate on enforcement) · F2 −0.03 (trusts elections) · F4 −0.35 (secular) · F5 −0.56 (progressive)

**Why it works under Condorcet:** In purple states like Pennsylvania and Minnesota, SD_hi_so beats every other candidate one-on-one because it occupies the precise ideological sweet spot: progressive enough for the center-left base, security-credible enough to win transfers from center-right voters who would never rank a pure SD candidate above a Conservative.

---

### POP_lo_es — The Establishment Populist Senator
**Condorcet: 5 seats · IRV: 1 seat**

*A Populist senator who tones down anti-establishment rhetoric and signals trust in institutions.*

POP_lo_es shifts Electoral Skepticism from POP's base of +0.76 down to +0.61 — still deeply skeptical by any standard, but measurably less hostile to institutions than the pure Populist position. This candidate keeps Populist's immigration restrictionism, fiscal populism, and cultural conservatism while becoming just acceptable enough to win in deeply red states. Under Condorcet: Idaho, North Dakota, Oklahoma, South Dakota, Wyoming. Under IRV: only North Dakota.

**Factor profile:** F1 +0.20 (moderate enforcement) · F2 +0.61 (electorally skeptical) · F4 +0.15 (moderate religious) · F5 +0.99 (strongly conservative)

**Why it works:** In the five most conservative states in the system, no center-left candidate wins a head-to-head matchup. POP_lo_es wins by being the rightmost candidate that has moderated enough to beat CON variants one-on-one. Under IRV, only North Dakota produces enough first-choice Populist votes to survive elimination — in the other four states, first-choice CON voters outnumber POP voters, and IRV rewards that first-choice lead.

---

### Other Crossover Types

Several types win a small number of seats:

**STY_lo_so** (Solidarity, softer on security) — Condorcet: 2 *(Kansas, Utah)* · IRV: 1 *(Utah)*. A deeply civil-libertarian Solidarity candidate (F1 −0.63), winning in states with libertarian-leaning electorates.

**STY (base)** — Condorcet: 2 *(Maryland, Mississippi)* · IRV: 0. The unshifted Solidarity candidate wins in two states where the base profile is already close to the state median.

**STY_hi_pc** (Solidarity, more populist-conservative) — Condorcet: 1 *(Arizona)* · IRV: 0. A Solidarity candidate who shifts rightward on immigration — notable for winning Arizona, which goes to SD_lo_es under IRV.

**SD_hi_es** (Social Democrat, more anti-establishment) — Condorcet: 0 · IRV: 2 *(Connecticut, Maine)*. An SD candidate who signals more institutional skepticism, winning in New England under IRV.

**SD (base)** — Condorcet: 1 *(Iowa)* · IRV: 2 *(Georgia, Iowa)*. The unshifted Social Democrat wins where the base profile matches the state.

**SD_lo_pc** (Social Democrat, less populist-conservative) — Condorcet: 0 · IRV: 1 *(Nevada)*. A more progressive SD variant.

**CON_lo_pc** (Conservative, less populist) — Condorcet: 1 *(Tennessee)* · IRV: 0. The only Conservative to win under Condorcet — by softening populism enough to beat STY and POP in head-to-head matchups.

**CON_hi_pc** (Conservative, more populist) — Condorcet: 0 · IRV: 1 *(Idaho)*. A hard-right Conservative who survives IRV in the most conservative state outside the deep South.

**CON_lo_es** (Conservative, establishment-friendly) — Condorcet: 0 · IRV: 1 *(Oklahoma)*.

**CON (base)** — Condorcet: 0 · IRV: 1 *(Wyoming)*.

**CUP_hi_pc** (Civic Union Party, more populist-conservative) — Condorcet: 0 · IRV: 1 *(South Dakota)*. The only Civic Union Party win in the crossover field.

---

## Part III: The Pure Partisan Senate

When candidates run only on the pure party platform — no axis shifts, no crossover positioning — the map simplifies dramatically. Only five parties win seats, and the balance between STY and SD depends entirely on which counting method is used.

### Condorcet: STY Dominance

Under Condorcet, Solidarity wins 33 of 51 seats — a near-supermajority driven by the same dynamic that makes STY_lo_es the dominant crossover type: Solidarity sits at the spatial median of the nine-party field, and in head-to-head matchups against every other party, more voters prefer STY than oppose it.

| Party | Seats | States |
|-------|-------|--------|
| STY | 33 | AL, AK, AZ, AR, CA, CO, FL, GA, HI, IN, IA, KS, KY, LA, MD, MI, MS, MO, MT, NE, NV, NC, ND, OH, OK, PA, SC, SD, TX, UT, VA, WI, WV |
| SD | 15 | CT, DE, DC, IL, ME, MA, MN, NH, NJ, NM, NY, OR, RI, VT, WA |
| CON | 1 | TN |
| POP | 1 | ID |
| CUP | 1 | WY |

### IRV: Three-Way Competition

Under IRV, the map transforms. Social Democrat wins 26 seats, while Conservative — which won only 1 under Condorcet — breaks through to 11, and Solidarity drops to 11. The shift happens because IRV rewards first-choice intensity: CON voters are enthusiastic first-rankers whose candidates survive early elimination rounds, while STY voters — many of whom are broadly acceptable but not many voters' passionate first choice — are eliminated before their broad appeal can matter.

| Party | Seats | States |
|-------|-------|--------|
| SD | 26 | CA, CO, CT, DE, DC, FL, GA, IL, ME, MD, MA, MN, MO, NE, NV, NH, NJ, NM, NY, OR, PA, RI, SC, VA, WA, WI |
| CON | 11 | AR, ID, IN, IA, KY, MI, MT, NC, ND, OH, TN |
| STY | 11 | AL, AK, HI, KS, LA, MS, OK, SD, TX, UT, WV |
| POP | 2 | AZ, WY |
| LIB | 1 | VT |

The 25-state divergence between methods is the largest in the simulation. CON gains 10 seats under IRV that it loses under Condorcet; STY loses 22 seats. The implication is stark: for Solidarity, which counting method the Senate uses matters more than any policy position.

---

## Electoral Breakdown

### Senate Seat Totals by Party Across All Four Scenarios

| Party | Crossover Condorcet | Crossover IRV | Pure Condorcet | Pure IRV |
|-------|:---:|:---:|:---:|:---:|
| STY | 34 | 19 | 33 | 11 |
| SD | 11 | 27 | 15 | 26 |
| CON | 1 | 3 | 1 | 11 |
| POP | 5 | 1 | 1 | 2 |
| CUP | 0 | 1 | 1 | 0 |
| LIB | 0 | 0 | 0 | 1 |
| PRG | 0 | 0 | 0 | 0 |
| DSA | 0 | 0 | 0 | 0 |
| NAT | 0 | 0 | 0 | 0 |

The pattern is consistent: **Condorcet produces STY dominance; IRV produces SD dominance** — across both candidate fields. The crossover field amplifies whatever the counting method already favors: STY variants win even more states under crossover Condorcet (34 vs. 32 pure), and SD variants win even more under crossover IRV (27 vs. 26 pure).

### State-by-State: Crossover Field

States where both methods elect the same party are in plain text. The **21 states where the winning party differs** are bold. States where the party is the same but the crossover variant differs are marked with *.

| State | Condorcet | IRV |
|-------|-----------|-----|
| Alabama | STY_lo_es | STY_lo_es |
| Alaska | STY_lo_es | STY_lo_es |
| **Arizona** | **STY_hi_pc** | **SD_lo_es** |
| Arkansas | STY_lo_es | STY_lo_es |
| **California** | **STY_lo_es** | **SD_lo_so** |
| **Colorado** | **STY_lo_es** | **SD_lo_so** |
| **Connecticut** | **STY_lo_pc** | **SD_hi_es** |
| Delaware* | SD_hi_so | SD_lo_es |
| DC | SD_lo_es | SD_lo_es |
| Florida | STY_lo_pc | STY_lo_pc |
| **Georgia** | **STY_lo_pc** | **SD** |
| Hawaii | STY_lo_pc | STY_lo_pc |
| **Idaho** | **POP_lo_es** | **CON_hi_pc** |
| Illinois* | SD_lo_es | SD_lo_so |
| Indiana | STY_lo_es | STY_lo_es |
| Iowa | SD | SD |
| **Kansas** | **STY_lo_so** | **SD_lo_es** |
| Kentucky | STY_lo_es | STY_lo_es |
| Louisiana | STY_hi_so | STY_hi_so |
| Maine* | SD_hi_so | SD_hi_es |
| **Maryland** | **STY** | **SD_lo_es** |
| Massachusetts | SD_lo_es | SD_lo_es |
| **Michigan** | **STY_lo_es** | **SD_lo_es** |
| Minnesota* | SD_hi_so | SD_lo_so |
| Mississippi* | STY | STY_lo_pc |
| Missouri | STY_hi_so | STY_hi_so |
| Montana | STY_lo_es | STY_lo_es |
| Nebraska | STY_lo_es | STY_lo_es |
| **Nevada** | **STY_hi_so** | **SD_lo_pc** |
| New Hampshire | SD_lo_so | SD_lo_so |
| **New Jersey** | **STY_lo_es** | **SD_lo_so** |
| **New Mexico** | **STY_lo_es** | **SD_lo_so** |
| **New York** | **STY_lo_es** | **SD_lo_so** |
| North Carolina | STY_lo_es | STY_lo_es |
| North Dakota | POP_lo_es | POP_lo_es |
| Ohio | STY_lo_es | STY_lo_es |
| **Oklahoma** | **POP_lo_es** | **CON_lo_es** |
| **Oregon** | **STY_lo_es** | **SD_lo_so** |
| Pennsylvania* | SD_hi_so | SD_lo_so |
| Rhode Island | SD_hi_so | SD_hi_so |
| South Carolina | STY_hi_so | STY_hi_so |
| **South Dakota** | **POP_lo_es** | **CUP_hi_pc** |
| **Tennessee** | **CON_lo_pc** | **STY_hi_so** |
| Texas | STY_lo_es | STY_lo_es |
| Utah | STY_lo_so | STY_lo_so |
| Vermont | SD_lo_es | SD_lo_es |
| **Virginia** | **STY_lo_es** | **SD_lo_es** |
| **Washington** | **STY_lo_es** | **SD_lo_so** |
| West Virginia | STY_hi_so | STY_hi_so |
| **Wisconsin** | **STY_lo_es** | **SD_lo_es** |
| **Wyoming** | **POP_lo_es** | **CON** |

### State-by-State: Pure Partisan Field

The **25 states where the winner differs** between methods are bold.

| State | Condorcet | IRV |
|-------|-----------|-----|
| Alabama | STY | STY |
| Alaska | STY | STY |
| **Arizona** | **STY** | **POP** |
| **Arkansas** | **STY** | **CON** |
| **California** | **STY** | **SD** |
| **Colorado** | **STY** | **SD** |
| Connecticut | SD | SD |
| Delaware | SD | SD |
| DC | SD | SD |
| **Florida** | **STY** | **SD** |
| **Georgia** | **STY** | **SD** |
| Hawaii | STY | STY |
| **Idaho** | **POP** | **CON** |
| Illinois | SD | SD |
| **Indiana** | **STY** | **CON** |
| **Iowa** | **STY** | **CON** |
| Kansas | STY | STY |
| **Kentucky** | **STY** | **CON** |
| Louisiana | STY | STY |
| Maine | SD | SD |
| **Maryland** | **STY** | **SD** |
| Massachusetts | SD | SD |
| **Michigan** | **STY** | **CON** |
| Minnesota | SD | SD |
| Mississippi | STY | STY |
| **Missouri** | **STY** | **SD** |
| **Montana** | **STY** | **CON** |
| **Nebraska** | **STY** | **SD** |
| **Nevada** | **STY** | **SD** |
| New Hampshire | SD | SD |
| New Jersey | SD | SD |
| New Mexico | SD | SD |
| New York | SD | SD |
| **North Carolina** | **STY** | **CON** |
| **North Dakota** | **STY** | **CON** |
| **Ohio** | **STY** | **CON** |
| Oklahoma | STY | STY |
| Oregon | SD | SD |
| **Pennsylvania** | **STY** | **SD** |
| Rhode Island | SD | SD |
| **South Carolina** | **STY** | **SD** |
| South Dakota | STY | STY |
| Tennessee | CON | CON |
| Texas | STY | STY |
| Utah | STY | STY |
| **Vermont** | **SD** | **LIB** |
| **Virginia** | **STY** | **SD** |
| Washington | SD | SD |
| West Virginia | STY | STY |
| **Wisconsin** | **STY** | **SD** |
| **Wyoming** | **CUP** | **POP** |

---

## Legislative Outlook

The vote simulation models 37 binary policy items across all scenarios. The legislative outcome depends on three things: whether the bill passes the House, whether it passes the Senate (which varies by scenario), and whether the president signs it (which varies by which president the scenario produces).

The crossover field's STY-dominated senate produces meaningfully more left-leaning outcomes than the pure partisan field's more competitive senate. Several bills that pass easily under one scenario fail under another — not because voters changed their minds, but because the counting method and candidate field changed which voices are represented.

### What Passes in All Scenarios

These bills clear the House, pass every senate configuration, and are signed by all three possible presidents:

**Taxes & Spending** — Allow top-bracket rates on incomes over $400k to rise to 35% (65.3% support). Spend $150B/yr on infrastructure (80.5%). Expand federal tax incentives for affordable housing (72.4%).

**Immigration** — Grant legal status to long-term undocumented immigrants (59.2%). Permanent DACA pathway for Dreamers (70.4%). Increase border patrols (79.6%). Forgive up to $20k of student loan debt (54.2%).

**Environment** — Give EPA authority to regulate CO2 emissions (62.4%). Require 20% renewable electricity (66.1%). Strengthen Clean Air and Water Act enforcement (55.2%). Prevent government from banning gas stoves (67.5%).

**Police & Public Safety** — Ban assault rifles (59.6%). Universal background checks on all gun sales (92.5%). Increase spending on mental health and school safety (86.5%).

**Healthcare** — Expand Medicaid for incomes under $25k/$40k (78.7%).

**Civil Liberties** — Age verification for adult web content (78.8%).

### What Fails in All Scenarios

- **Easier concealed carry** (38.9%) — fails in all chambers; every president vetoes
- **Decrease police 10%** (26.8%) — no cross-party coalition reaches majority
- **Renew post-9/11 surveillance programs** (34.0%) — fails in all chambers; every president vetoes
- **ACA repeal** (38.5%) — fails clearly in all chambers; every president vetoes
- **Prohibit abortion-inducing drugs by mail** (41.2%) — fails in all chambers
- **Restrict interstate travel for abortion** (18.5%) — fails decisively

### Where the President Decides

These bills pass the House and most senate configurations, but whether they become law depends on which president the scenario produces. The three presidents — STY_hi_so (crossover), SD_1 (pure IRV), and STY_1 (pure Condorcet) — have distinct veto patterns.

| Bill | Overall support | STY_hi_so | SD_1 | STY_1 |
|------|:---:|:---:|:---:|:---:|
| Extend 2017 tax cuts | 62.9% | Signs | **Vetoes** (49%) | Signs |
| Raise corporate tax 21%→28% | 57.7% | **Vetoes** (47%) | Signs | Signs |
| Prohibit restrictions on abortion access | 63.0% | **Vetoes** (48%) | Signs | Signs |
| Federal recognition of same-sex marriages | 66.1% | **Vetoes** (48.5%) | Signs | Signs |
| Prevent gender transition surgery for minors | 60.1% | Signs | **Vetoes** (49%) | Signs |
| Parental consent for school name/pronoun changes | 62.7% | Signs | **Vetoes** (46%) | Signs |
| School voucher subsidies | 56.2% | Signs | **Vetoes** (44%) | Signs |

The STY_hi_so and SD_1 presidents have *opposite* veto profiles. STY_hi_so vetoes the progressive social agenda (abortion access, same-sex marriage, corporate tax hike) because the "tough on security" Solidarity coalition is just conservative enough on social issues to split below 50%. SD_1 vetoes the conservative social agenda (gender transition ban, parental consent, vouchers, tax cut extension) because the progressive SD base cannot stomach these measures. STY_1, the pure Solidarity Condorcet winner, signs almost everything from both sides — the spatial median president.

### Where the Senate Decides

These bills pass the House but fail in the crossover field's STY-dominated senate, producing dramatically different outcomes depending on which candidate field is used:

| Bill | House | Crossover Senate | Pure Partisan Senate | All presidents |
|------|:---:|:---:|:---:|:---:|
| Deny asylum at the border | PASS | **FAIL** (Cond 23%, IRV 12%) | Mixed (Cond FAIL, IRV PASS) | STY_hi_so vetoes; SD_1 vetoes; STY_1 vetoes |
| Increase police funding 10% | PASS | **FAIL** (Cond 2%, IRV 1%) | Mixed (Cond FAIL, IRV TOSS-UP) | All presidents veto |
| Ban TikTok unless China sells | PASS | **FAIL** (Cond 19%, IRV 23%) | Mixed (Cond FAIL, IRV TOSS-UP) | All presidents veto |
| Increase fossil fuel production | PASS | **TOSS-UP/FAIL** (Cond 46%, IRV 17%) | Mixed | STY_hi_so signs; SD_1 vetoes; STY_1 signs (barely, 50%) |
| Halt oil/gas leases on federal land | FAIL | Cond TOSS-UP, **IRV PASS (89%)** | Cond PASS (71%), IRV TOSS-UP | STY_hi_so vetoes; SD_1 signs; STY_1 signs (51%) |

The crossover senate's STY dominance blocks enforcement-heavy and security-oriented bills that would pass in the pure partisan field. The most striking result: halting new oil/gas leases on federal land, which fails in the House and was described as dead-on-arrival in two-party politics, *passes* the crossover IRV senate at 89% probability — because the STY-variant senators who dominate that chamber represent an electorate skeptical of fossil fuel expansion.

### The Toss-Ups

**Relaxing local zoning laws** (50.2%) sits at almost exactly 50/50 in the House and varies by senate scenario. It passes the crossover senate but is a toss-up in the pure partisan senate. All three presidents would sign it.

**Medicaid work requirements** (53.3%) passes the House but is a toss-up in every senate configuration. SD_1 and STY_1 both veto it; STY_hi_so signs.

**Abortion restricted to rape/incest/life danger** (51.4%) is a toss-up in the House, varies across senate scenarios, and splits the presidents: STY_hi_so and STY_1 sign; SD_1 vetoes.

---

## Appendix: The Five Ideological Dimensions

### Factor Overview

The five factors underlying this typology were identified through Exploratory Factor Analysis (EFA) of 24 survey items from the 2024 CES, using oblique (Promax) rotation. N=45,707 after listwise deletion.

**Tier thresholds:** Very High > +0.75 | High +0.25 to +0.75 | Medium −0.25 to +0.25 | Low −0.75 to −0.25 | Very Low < −0.75

---

### F1 — Security & Order

High scorers favor increasing police by 10%, expanding border patrols, denying asylum to Central American migrants, renewing post-9/11 surveillance programs, and opposing legal status for undocumented immigrants. Low scorers oppose all of the above. This is the law enforcement and national security axis — it is distinct from fiscal conservatism (which loads on F5) and from religious values (which load on F4). F1 and F4 are strongly correlated (+0.55), reflecting the traditional "socially conservative" combination, but they are not the same thing: CON scores Very High on F1 but only Medium on F4.

---

### F2 — Electoral Skepticism

High scorers disagree that U.S. elections are run fairly and disagree that their 2024 state/local elections were fair. This factor is near-orthogonal to partisan identity. Critically, POP (+0.76), STY (+0.66), and DSA (+0.50) all score High on F2 despite being maximally opposed on F5. Electoral skepticism cuts across the left-right divide. CUP (−0.82) is the most trusting party.

---

### F3 — Government Distrust

High scorers distrust the federal and state governments generally. This factor shares items with F2 but captures general institutional distrust rather than specifically electoral skepticism. Critically: all nine parties score Medium on F3 (range: −0.21 to +0.13). Government distrust does not differentiate parties from each other — it is a background condition shared broadly across the electorate.

---

### F4 — Religious Traditionalism

High scorers attend church frequently, favor stricter limits on abortion, and oppose federal recognition of same-sex marriages. Church attendance and abortion week limits have the joint-highest loadings (+0.69 each). This is genuinely the religious values axis, not just social conservatism broadly: NAT (+0.46) is the only High-scoring party; all others are Medium or Low.

---

### F5 — Populist Conservatism

High scorers agree that racial problems are rare and isolated, oppose Dreamer pathways to citizenship, oppose raising top-bracket tax rates, oppose legal status for undocumented immigrants, and disagree with progressive racial attitudes. NAT at +1.51 is a full standard deviation above the next type (POP at +0.99). PRG (−0.99) and LIB (−0.95) anchor the opposite pole.

---

### Factor Score Table — Nine Parties + Key Crossover Types

Sorted by F5, most populist-conservative first. Crossover types that win senate seats are included.

| Type | Description | F1 Sec/Ord | F2 ElecSkep | F3 GovtDis | F4 ReligTrad | F5 PopCons |
|------|-------------|-----------|-------------|------------|--------------|------------|
| NAT | Nationalist | +0.737 | +0.428 | −0.208 | +0.457 | **+1.510** |
| POP | Populist | +0.202 | +0.759 | −0.206 | +0.147 | +0.990 |
| POP_lo_es | Populist, establishment-friendly | +0.202 | +0.613 | −0.206 | +0.147 | +0.990 |
| CON_hi_pc | Conservative, more populist | +0.767 | −0.024 | +0.111 | +0.219 | +0.653 |
| CON | Conservative | +0.767 | −0.024 | +0.111 | +0.219 | +0.442 |
| CON_lo_es | Conservative, establishment-friendly | +0.767 | −0.170 | +0.111 | +0.219 | +0.442 |
| CON_lo_pc | Conservative, less populist | +0.767 | −0.024 | +0.111 | +0.219 | +0.232 |
| CUP_hi_pc | Civic Union Party, more populist | +0.266 | −0.817 | −0.174 | +0.130 | +0.250 |
| STY_hi_pc | Solidarity, more populist | −0.446 | +0.658 | +0.133 | +0.165 | +0.149 |
| CUP | Civic Union Party | +0.266 | −0.817 | −0.174 | +0.130 | +0.039 |
| STY | Solidarity (base) | −0.446 | +0.658 | +0.133 | +0.165 | −0.062 |
| STY_lo_es | Solidarity, establishment-friendly | −0.446 | +0.512 | +0.133 | +0.165 | −0.062 |
| STY_hi_so | Solidarity, tough on security | −0.265 | +0.658 | +0.133 | +0.165 | −0.062 |
| STY_lo_so | Solidarity, soft on security | −0.627 | +0.658 | +0.133 | +0.165 | −0.062 |
| STY_lo_pc | Solidarity, less populist | −0.446 | +0.658 | +0.133 | +0.165 | −0.273 |
| SD_hi_es | Soc. Democrat, anti-establishment | −0.414 | +0.114 | +0.091 | −0.345 | −0.564 |
| SD_hi_so | Soc. Democrat, tough on security | −0.234 | −0.032 | +0.091 | −0.345 | −0.564 |
| SD | Social Democrat (base) | −0.414 | −0.032 | +0.091 | −0.345 | −0.564 |
| SD_lo_es | Soc. Democrat, establishment-friendly | −0.414 | −0.178 | +0.091 | −0.345 | −0.564 |
| SD_lo_so | Soc. Democrat, soft on security | −0.595 | −0.032 | +0.091 | −0.345 | −0.564 |
| SD_lo_pc | Soc. Democrat, less populist | −0.414 | −0.032 | +0.091 | −0.345 | −0.775 |
| DSA | Democratic Socialists | −1.303 | +0.504 | +0.076 | −0.387 | −0.874 |
| LIB | Liberal | −0.462 | −0.744 | −0.086 | −0.323 | −0.950 |
| PRG | Progressive | −1.260 | −0.634 | −0.206 | −0.387 | −0.990 |

---

*Simulation based on CES 2024 data (N=45,707). House seats allocated by Single Transferable Vote; Senate seats allocated by Instant Runoff Voting (IRV) and Condorcet (ranked pairs) methods. Party cluster assignments derived from k-means clustering on EFA factor scores. Crossover candidates generated by shifting base party positions ±25% of inter-party standard deviation on one discriminating axis.*
