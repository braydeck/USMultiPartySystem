# Party profiles: the nine parties

Generated 2026-11-14 by `scripts/build_party_profiles.py`. Do not edit by hand. 49,431 CES 2024 respondents, 9 parties from a DPGMM on 4 EFA factors. Scenario: field rawMulti, depth top7, turnout gap 5%, double magnitude (873 House seats, 102 Senate seats). Parties run left to right by how often they vote together.

Prose is the app's copy (`viz/src/constants/parties.ts`). Numbers: shares from `partyPopulation.json`, factors from `clusterProfiles.json` and `factorLoadings.json`, House from `houseDepthNational.json` and `houseMmpNational.json`, Senate from `uncertainty*.json` (two-per-state delegations), presidency from `generalDepth.json` and `primaryDepth.json`, agreement from `candidateVoteModel.json`, partial fit from `crossPartyAffinity.json`. For the full tables see `docs/AGENT_SUMMARY.md`.

## At a glance

| Party | Pop % | Voter % | House STV | House list | House MMP | Senate Cond | Senate IRV | Pres. first choice % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **DSA** Democratic Socialists | 3.3 | 3.8 | 3 | 13 | 31 | 0 | 0 | — |
| **PRG** Progressive | 6.1 | 8.7 | 59 | 67 | 68 | 0 | 1 | — |
| **LBR** Labor | 11.7 | 13.4 | 140 | 130 | 119 | 4 | 8 | 26.3 |
| **CUP** Civic Union | 10.8 | 11.3 | 122 | 112 | 98 | 24 | 12 | 13.8 |
| **STY** Solidarity | 22.1 | 11.7 | 149 | 127 | 112 | 31 | 39 | 17.1 |
| **OAO** Order and Opportunity | 7.5 | 6.3 | 31 | 42 | 58 | 0 | 0 | — |
| **CON** Conservative | 17.6 | 19.0 | 185 | 168 | 160 | 43 | 40 | 19.2 |
| **LP** Libertarian | 2.9 | 1.7 | 1 | 1 | 8 | 0 | 0 | — |
| **NAT** Nationalist | 18.0 | 24.0 | 183 | 213 | 219 | 0 | 2 | 23.7 |

| Factor | η² | High pole | Low pole |
| --- | ---: | --- | --- |
| Cultural Conservatism (F4) | 0.745 | Restricts abortion and gender transition for minors; backs school vouchers; born-again | Protects abortion access, same-sex marriage and contraception |
| Security & Order (F1) | 0.693 | More police and border patrols, more law-enforcement spending | Fewer police, more spending on other services |
| Economic Conservatism (F5) | 0.686 | Cuts state spending on health care, education and welfare; opposes Medicaid expansion | Raises state social spending, expands Medicaid, taxes high earners |
| Government Distrust (F2) | 0.233 | Little or no trust in federal and state government; doubts elections are fair | Trusts federal and state government and elections |

---

## DSA: Democratic Socialists

*Against police, border enforcement, and surveillance; the youngest and most secular party.*

The anti-state left. Its members are unanimous against police and border enforcement, distrust the federal government, and oppose state controls on speech and the internet. It has the most support of any party for non-combat aid to Gaza. The youngest party, and the most secular, LGBT, and unmarried. Mostly renters, and the most likely to have protested in the past year.

| Factor | z | Percentile |
| --- | ---: | ---: |
| Cultural Conservatism | -1.56 | 10 |
| Security & Order | -2.02 | 3 |
| Economic Conservatism | -1.07 | 17 |
| Government Distrust | +0.47 | 70 |

Signature positions (% of members who support; gap vs the nation in points):

| Position | Support % | Gap |
| --- | ---: | ---: |
| Increase border patrols | 0.9 | -58.6 |
| Decrease police by 10%, increase other funding | 100.0 | +42.7 |
| Ban TikTok unless China sells to a US company | 11.2 | -29.9 |
| Increase state spending on welfare | 93.8 | +25.6 |
| Require able-bodied Medicaid recipients under 64 to work | 9.9 | -18.4 |

| Measure | Value |
| --- | --- |
| Population / 2024 voter share | 3.3% / 3.8% |
| House seats (double, 5% gap): STV / list / MMP | 3 / 13 / 31 of 873 |
| Senate seats (5% gap): Condorcet / IRV | 0 / 0 of 102 |
| Presidential primary | best candidate DSA_1 cut at Retail |
| General: first choice %, head-to-head W–L | not a finalist |
| Closest on bills (free vote / whipped) | PRG 92 / 95, LBR 88 / 92 |
| Own-party share of members' posterior | 80% |
| Members' partial fit goes mostly to | PRG, LBR |


## PRG: Progressive

*The professional left: progressive across the board, the most politically active, and pro-Ukraine.*

The left's professional and activist class. Progressive on every domain at near-unanimity, and the party most committed to Ukraine. It is also the most politically active party: nearly half gave money to a campaign in the past year, and it has the highest verified turnout. It accepts border patrols and trusts elections. The most college-educated, highest-income, and most invested party.

| Factor | z | Percentile |
| --- | ---: | ---: |
| Cultural Conservatism | -1.59 | 10 |
| Security & Order | -0.75 | 21 |
| Economic Conservatism | -1.11 | 15 |
| Government Distrust | -0.44 | 36 |

Signature positions (% of members who support; gap vs the nation in points):

| Position | Support % | Gap |
| --- | ---: | ---: |
| School voucher subsidies | 3.4 | -17.7 |
| Extend the 2017 tax cuts | 7.0 | -16.7 |
| Increase border patrols | 66.9 | +40.4 |
| Increase state spending on transportation & infrastructure | 93.4 | +7.1 |
| Increase state spending on law enforcement | 23.8 | +15.6 |

| Measure | Value |
| --- | --- |
| Population / 2024 voter share | 6.1% / 8.7% |
| House seats (double, 5% gap): STV / list / MMP | 59 / 67 / 68 of 873 |
| Senate seats (5% gap): Condorcet / IRV | 0 / 1 of 102 |
| Presidential primary | best candidate PRG_1 cut at Pod BD |
| General: first choice %, head-to-head W–L | not a finalist |
| Closest on bills (free vote / whipped) | LBR 93 / 97, DSA 92 / 95 |
| Own-party share of members' posterior | 74% |
| Members' partial fit goes mostly to | LBR, OAO |


## LBR: Labor

*Progressive on rights, climate, and taxes; three in ten cross over on tax cuts and vouchers.*

The left's rank and file. It is for abortion rights, a path to legal status, clean-energy rules, Medicaid expansion, and higher taxes on top earners, each at roughly nine in ten. About three in ten members back the 2017 tax cuts, school vouchers, and limits on gender medicine for minors, and just over half want more state welfare spending. It trusts government and elections at about the national average. The most suburban party.

| Factor | z | Percentile |
| --- | ---: | ---: |
| Cultural Conservatism | -1.13 | 23 |
| Security & Order | -0.99 | 16 |
| Economic Conservatism | -0.71 | 33 |
| Government Distrust | -0.22 | 42 |

Signature positions (% of members who support; gap vs the nation in points):

| Position | Support % | Gap |
| --- | ---: | ---: |
| Increase state spending on transportation & infrastructure | 78.5 | -15.3 |
| Renew post-9/11 surveillance programs | 24.9 | +11.2 |
| Halt new oil and gas leases on federal lands | 81.1 | -14.8 |
| Protect access to contraception | 87.7 | -5.4 |
| Raise corporate income tax from 21% to 28% | 88.6 | -9.6 |

| Measure | Value |
| --- | --- |
| Population / 2024 voter share | 11.7% / 13.4% |
| House seats (double, 5% gap): STV / list / MMP | 140 / 130 / 119 of 873 |
| Senate seats (5% gap): Condorcet / IRV | 4 / 8 of 102 |
| Presidential primary | LBR_1 reaches the general |
| General: first choice %, head-to-head W–L | 26.3%, 1–3 |
| Closest on bills (free vote / whipped) | PRG 93 / 97, DSA 88 / 92 |
| Own-party share of members' posterior | 72% |
| Members' partial fit goes mostly to | CUP, STY |


## CUP: Civic Union

*Socially liberal and pro-police; funds public services and resists aid paid to individuals.*

The fiscally cautious center. Socially liberal on abortion, same-sex marriage, and assault weapons, pro-police, and trusting of elections. It funds shared public services: nine in ten back infrastructure and mental-health and school-safety spending, seven in ten want more state spending on health care, schools, and roads, and eight in ten back Medicaid expansion and higher taxes on top earners. It resists aid paid to individuals: 37% back student-debt relief, 20% want more state welfare spending, and a majority would add work requirements to Medicaid. It has the most self-described moderates of any party.

| Factor | z | Percentile |
| --- | ---: | ---: |
| Cultural Conservatism | -0.79 | 32 |
| Security & Order | +0.43 | 59 |
| Economic Conservatism | -0.03 | 57 |
| Government Distrust | -0.51 | 34 |

Signature positions (% of members who support; gap vs the nation in points):

| Position | Support % | Gap |
| --- | ---: | ---: |
| Prohibit women traveling to another state for abortion | 8.4 | -18.0 |
| Increase state spending on welfare | 19.5 | -33.9 |
| Decrease police by 10%, increase other funding | 8.5 | -19.2 |
| School voucher subsidies | 26.4 | -40.5 |
| Repeal the Affordable Care Act | 11.0 | -18.4 |

| Measure | Value |
| --- | --- |
| Population / 2024 voter share | 10.8% / 11.3% |
| House seats (double, 5% gap): STV / list / MMP | 122 / 112 / 98 of 873 |
| Senate seats (5% gap): Condorcet / IRV | 24 / 12 of 102 |
| Presidential primary | CUP_1 reaches the general |
| General: first choice %, head-to-head W–L | 13.8%, 3–1 |
| Closest on bills (free vote / whipped) | OAO 88 / 78, STY 85 / 73 |
| Own-party share of members' posterior | 68% |
| Members' partial fit goes mostly to | STY, LBR |


## STY: Solidarity

*The working-class middle: economically left, culturally traditional, and least engaged in politics.*

The working-class middle, and the largest party. Its members agree on the country's consensus positions: seven in ten or more back border patrols, parental consent on pronouns, higher taxes on top earners, infrastructure and mental-health spending, and age checks on adult websites, each within ten points of the national figure. Beyond that consensus it leans left on economic help (student-debt relief, Medicaid) and right on school vouchers and the 2017 tax cuts. It is also the party furthest from politics: one in five follows public affairs and 31% voted in 2024 by the voter file, both the lowest of any party, and few back arms or aid for Ukraine (16% and 40%). Majority non-white; the lowest-income, most female, and most Southern party, with the most children at home.

| Factor | z | Percentile |
| --- | ---: | ---: |
| Cultural Conservatism | +0.38 | 62 |
| Security & Order | -0.60 | 25 |
| Economic Conservatism | -0.29 | 49 |
| Government Distrust | -0.13 | 45 |

Signature positions (% of members who support; gap vs the nation in points):

| Position | Support % | Gap |
| --- | ---: | ---: |
| Make abortion illegal in all circumstances | 17.1 | +10.9 |
| Spend $150B/yr on infrastructure | 75.2 | -21.0 |
| Increase spending on mental health & school safety | 89.9 | -7.9 |
| School voucher subsidies | 73.1 | +27.8 |
| Permanent status/pathway for Dreamers | 80.1 | -14.0 |

| Measure | Value |
| --- | --- |
| Population / 2024 voter share | 22.1% / 11.7% |
| House seats (double, 5% gap): STV / list / MMP | 149 / 127 / 112 of 873 |
| Senate seats (5% gap): Condorcet / IRV | 31 / 39 of 102 |
| Presidential primary | STY_1 reaches the general |
| General: first choice %, head-to-head W–L | 17.1%, 4–0 |
| Closest on bills (free vote / whipped) | OAO 88 / 89, CUP 85 / 73 |
| Own-party share of members' posterior | 78% |
| Members' partial fit goes mostly to | CON, CUP |


## OAO: Order and Opportunity

*Spends on health care, schools, and police alike, and trusts government the most.*

The urban Democratic base. Its members want government to do more of everything, policing included: they back Medicaid expansion, student-debt relief, and more state health spending at near-unanimity, along with more police and border patrols. They trust the federal and state governments more than any other party. On culture they sit near the national average, and three in ten attend church weekly. Older city residents, the highest Black and Catholic shares of any party, and the fewest independents.

| Factor | z | Percentile |
| --- | ---: | ---: |
| Cultural Conservatism | +0.03 | 52 |
| Security & Order | +0.28 | 53 |
| Economic Conservatism | -1.21 | 10 |
| Government Distrust | -0.85 | 23 |

Signature positions (% of members who support; gap vs the nation in points):

| Position | Support % | Gap |
| --- | ---: | ---: |
| Increase state spending on transportation & infrastructure | 92.2 | +32.6 |
| Increase state spending on law enforcement | 88.0 | +39.6 |
| Forgive up to $20k of student loan debt per person | 95.1 | +34.3 |
| Expand federal tax incentives for affordable housing | 94.4 | +15.6 |
| Age verification for adult web content | 92.2 | +13.0 |

| Measure | Value |
| --- | --- |
| Population / 2024 voter share | 7.5% / 6.3% |
| House seats (double, 5% gap): STV / list / MMP | 31 / 42 / 58 of 873 |
| Senate seats (5% gap): Condorcet / IRV | 0 / 0 of 102 |
| Presidential primary | best candidate OAO_1 cut at Pod C |
| General: first choice %, head-to-head W–L | not a finalist |
| Closest on bills (free vote / whipped) | CUP 88 / 78, STY 88 / 89 |
| Own-party share of members' posterior | 63% |
| Members' partial fit goes mostly to | STY, CUP |


## CON: Conservative

*United on borders, police, energy, and tax cuts; split on abortion, guns, and climate.*

The mainstream right. Its members agree on order and low taxes: the wall, more police, border patrols, fossil fuels, and the 2017 tax cuts. On abortion, guns, climate, immigration status, and the Affordable Care Act they split, with a third to a half taking the liberal position. On spending and trust in elections it sits at the national average. The most Republican-identifying party.

| Factor | z | Percentile |
| --- | ---: | ---: |
| Cultural Conservatism | +0.56 | 68 |
| Security & Order | +0.88 | 77 |
| Economic Conservatism | +0.39 | 70 |
| Government Distrust | +0.18 | 57 |

Signature positions (% of members who support; gap vs the nation in points):

| Position | Support % | Gap |
| --- | ---: | ---: |
| Build a wall between the U.S. and Mexico | 92.9 | +23.7 |
| Increase fossil fuel production in the U.S. | 89.6 | +19.8 |
| Require background checks on all gun sales | 94.3 | +5.5 |
| Parental consent for name/pronoun changes at school | 88.9 | +15.4 |
| Prohibit women traveling to another state for abortion | 27.9 | +11.2 |

| Measure | Value |
| --- | --- |
| Population / 2024 voter share | 17.6% / 19.0% |
| House seats (double, 5% gap): STV / list / MMP | 185 / 168 / 160 of 873 |
| Senate seats (5% gap): Condorcet / IRV | 43 / 40 of 102 |
| Presidential primary | CON_1 reaches the general |
| General: first choice %, head-to-head W–L | 19.2%, 2–2 |
| Closest on bills (free vote / whipped) | NAT 83 / 89, LP 80 / 73 |
| Own-party share of members' posterior | 71% |
| Members' partial fit goes mostly to | NAT, STY |


## LP: Libertarian

*Distrusts elections and government, opposes public spending of every kind, and wants out of foreign wars.*

The disaffected right. Distrust defines it: it has the least faith in elections and state government of any party. It opposes spending on roads, police, and welfare alike, and it wants the U.S. out of Ukraine and Gaza. On abortion, the wall, and guns it sits at the national average. Younger, the most independent and religiously unaffiliated party, and the most often out of work. Three in ten follow public affairs, and a third voted in 2024 by the voter file.

| Factor | z | Percentile |
| --- | ---: | ---: |
| Cultural Conservatism | -0.31 | 44 |
| Security & Order | -0.83 | 19 |
| Economic Conservatism | +1.38 | 90 |
| Government Distrust | +1.12 | 88 |

Signature positions (% of members who support; gap vs the nation in points):

| Position | Support % | Gap |
| --- | ---: | ---: |
| Increase state spending on law enforcement | 11.1 | -49.4 |
| Increase state spending on transportation & infrastructure | 20.0 | -34.9 |
| Ban TikTok unless China sells to a US company | 31.7 | -28.7 |
| Forgive up to $20k of student loan debt per person | 31.5 | -11.3 |
| Grant legal status to long-term undocumented immigrants | 33.7 | -8.8 |

| Measure | Value |
| --- | --- |
| Population / 2024 voter share | 2.9% / 1.7% |
| House seats (double, 5% gap): STV / list / MMP | 1 / 1 / 8 of 873 |
| Senate seats (5% gap): Condorcet / IRV | 0 / 0 of 102 |
| Presidential primary | best candidate LP_1 cut at Retail |
| General: first choice %, head-to-head W–L | not a finalist |
| Closest on bills (free vote / whipped) | CON 80 / 73, STY 78 / 41 |
| Own-party share of members' posterior | 75% |
| Members' partial fit goes mostly to | STY, CON |


## NAT: Nationalist

*Conservative on every issue at near-unanimity, and the most politically engaged right.*

The conservative core. It takes the right-hand position on nearly every item at near-unanimity, and it is the party most set against the health-care safety net: nine in ten would repeal the Affordable Care Act, and fewer than one in five want more state health spending. It takes the most resentful position of any party on all nine racial and gender resentment items. It is the party most attached to property and arms: older, white, rural homeowners, stockholders, and gun owners. It follows politics closely and votes almost without exception.

| Factor | z | Percentile |
| --- | ---: | ---: |
| Cultural Conservatism | +1.07 | 87 |
| Security & Order | +0.90 | 78 |
| Economic Conservatism | +1.30 | 89 |
| Government Distrust | +0.67 | 77 |

Signature positions (% of members who support; gap vs the nation in points):

| Position | Support % | Gap |
| --- | ---: | ---: |
| Prevent government from banning gas stoves | 94.2 | +25.4 |
| Repeal the Affordable Care Act | 91.2 | +36.2 |
| Always allow abortion as a matter of personal choice | 10.5 | -36.8 |
| School voucher subsidies | 91.0 | +33.6 |
| Extend the 2017 tax cuts | 96.0 | +28.6 |

| Measure | Value |
| --- | --- |
| Population / 2024 voter share | 18.0% / 24.0% |
| House seats (double, 5% gap): STV / list / MMP | 183 / 213 / 219 of 873 |
| Senate seats (5% gap): Condorcet / IRV | 0 / 2 of 102 |
| Presidential primary | NAT_1 reaches the general |
| General: first choice %, head-to-head W–L | 23.7%, 0–4 |
| Closest on bills (free vote / whipped) | CON 83 / 89, LP 71 / 84 |
| Own-party share of members' posterior | 80% |
| Members' partial fit goes mostly to | CON, LP |
