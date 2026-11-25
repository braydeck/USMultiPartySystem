# Agent summary: the nine-party simulation

Generated 2026-11-24 by `scripts/build_agent_summary.py` from the site's payloads. Do not edit by hand; rerun the script after the pipeline. Party order is left to right (`pipeline/party_codes.LEFT_RIGHT`, from `data/processed/party_order.csv`).

| Setting | Value | Source |
| --- | --- | --- |
| Respondents | 49,431 | `viz/src/data/crossPartyAffinity.json` nVoters |
| Parties | 9 | `pipeline/party_codes.py` |
| Field | rawMulti | app default (`scenario` URL param) |
| Ballot depth | top7 | app default (`depth`) |
| Turnout gap stop | 5% | app default (`part`) |
| Turnout stops in payloads | 0%, 5%, 10%, 15%, 20%, 25%, 30% | tab sources |
| Magnitude | double | app default (`wyoming`) |
| House seats (double) | 873 | `viz/src/data/houseDepthNational.json` |
| House seats (triple) | 1726 | same |
| Electors | 975 | `viz/src/data/houseStateMap.json` seats + 2 per state |
| Senate races / seats | 51 / 102 | `viz/src/data/pureMultiSenate*.json` (one race per state); chamber seats two per state |
| Legislation bills | 37 | `viz/src/data/candidateVoteModel.json` |
| Legislation default vote model | free | app default (`voteModel`) |

Sections: [Parties](#parties) · [House](#house) · [Presidency](#presidency) · [Senate](#senate) · [Legislation](#legislation) · [Coalitions by domain](#coalitions-by-domain) · [Budget priorities](#budget-priorities)

## Parties

Sources: `viz/src/data/partyPopulation.json` (shares), `viz/src/data/clusterProfiles.json` (factor z-scores, key positions), `viz/src/data/factorLoadings.json` (η²), `viz/src/constants/parties.ts` (names, taglines).

Population share is each party's first-choice share of adults (post-weighted). Voter share re-weights the same head count by validated 2024 turnout (the 2024 electorate as cast). Factor z-scores are SDs from the national mean; high = more of the named trait.

| Party | Pop % | Voter % (2024) | Cultural Conservatism z (F4, η² 0.74) | Security & Order z (F1, η² 0.69) | Economic Conservatism z (F5, η² 0.69) | Government Distrust z (F2, η² 0.23) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **DSA** Democratic Socialists | 3.3 | 3.8 | -1.56 | -2.02 | -1.07 | +0.47 |
| **PRG** Progressive | 6.1 | 8.7 | -1.59 | -0.75 | -1.11 | -0.44 |
| **LBR** Labor | 11.7 | 13.4 | -1.13 | -0.99 | -0.71 | -0.22 |
| **CUP** Civic Union | 10.8 | 11.3 | -0.79 | +0.43 | -0.03 | -0.51 |
| **STY** Solidarity | 22.1 | 11.7 | +0.38 | -0.60 | -0.29 | -0.13 |
| **OAO** Order and Opportunity | 7.5 | 6.3 | +0.03 | +0.28 | -1.21 | -0.85 |
| **CON** Conservative | 17.6 | 19.0 | +0.56 | +0.88 | +0.39 | +0.18 |
| **LP** Libertarian | 2.9 | 1.7 | -0.31 | -0.83 | +1.38 | +1.12 |
| **NAT** Nationalist | 18.0 | 24.0 | +1.07 | +0.90 | +1.30 | +0.67 |

| Factor | Key | η² | Between/within | High pole | Low pole |
| --- | --- | ---: | ---: | --- | --- |
| Cultural Conservatism | F4 | 0.745 | 1.71 | Restricts abortion and gender transition for minors; backs school vouchers; born-again | Protects abortion access, same-sex marriage and contraception |
| Security & Order | F1 | 0.693 | 1.5 | More police and border patrols, more law-enforcement spending | Fewer police, more spending on other services |
| Economic Conservatism | F5 | 0.686 | 1.48 | Cuts state spending on health care, education and welfare; opposes Medicaid expansion | Raises state social spending, expands Medicaid, taxes high earners |
| Government Distrust | F2 | 0.233 | 0.55 | Little or no trust in federal and state government; doubts elections are fair | Trusts federal and state government and elections |

Profiles (tagline from the app; positions are the party's top differentiators: % of members who support, and the gap vs the nation in points):

| Party | Tagline | Top positions |
| --- | --- | --- |
| **DSA** | Against police, border enforcement, and surveillance; the youngest and most secular party | Increase border patrols 1% (-59); Decrease police by 10%, increase other funding 100% (+43); Ban TikTok unless China sells to a US company 11% (-30) |
| **PRG** | The professional left: progressive across the board, the most politically active, and pro-Ukraine | School voucher subsidies 3% (-18); Extend the 2017 tax cuts 7% (-17); Increase border patrols 67% (+40) |
| **LBR** | Progressive on rights, climate, and taxes; three in ten cross over on tax cuts and vouchers | Increase state spending on transportation & infrastructure 78% (-15); Renew post-9/11 surveillance programs 25% (+11); Halt new oil and gas leases on federal lands 81% (-15) |
| **CUP** | Socially liberal and pro-police; funds public services and resists aid paid to individuals | Prohibit women traveling to another state for abortion 8% (-18); Increase state spending on welfare 20% (-34); Decrease police by 10%, increase other funding 8% (-19) |
| **STY** | The working-class middle: economically left, culturally traditional, and least engaged in politics | Make abortion illegal in all circumstances 17% (+11); Spend $150B/yr on infrastructure 75% (-21); Increase spending on mental health & school safety 90% (-8) |
| **OAO** | Spends on health care, schools, and police alike, and trusts government the most | Increase state spending on transportation & infrastructure 92% (+33); Increase state spending on law enforcement 88% (+40); Forgive up to $20k of student loan debt per person 95% (+34) |
| **CON** | United on borders, police, energy, and tax cuts; split on abortion, guns, and climate | Build a wall between the U.S. and Mexico 93% (+24); Increase fossil fuel production in the U.S. 90% (+20); Require background checks on all gun sales 94% (+6) |
| **LP** | Distrusts elections and government, opposes public spending of every kind, and wants out of foreign wars | Increase state spending on law enforcement 11% (-49); Increase state spending on transportation & infrastructure 20% (-35); Ban TikTok unless China sells to a US company 32% (-29) |
| **NAT** | Conservative on every issue at near-unanimity, and the most politically engaged right | Prevent government from banning gas stoves 94% (+25); Repeal the Affordable Care Act 91% (+36); Always allow abortion as a matter of personal choice 10% (-37) |

## House

Sources: STV and party list from `viz/src/data/houseDepthNational.json` [top7][magnitude][stop] (what the House tab shows at a ranked depth); MMP from `viz/src/data/houseMmpNational.json` (MMP uses the 436 real districts plus a per-state top-off; it has no depth setting). Turnout stop 5%.

### Double magnitude

| Party | Vote % | STV seats | STV % | List seats | List % | MMP seats | MMP % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DSA | 3.8 | 3 | 0.3 | 13 | 1.5 | 31 | 3.6 |
| PRG | 8.5 | 59 | 6.8 | 67 | 7.7 | 68 | 7.8 |
| LBR | 13.2 | 140 | 16.0 | 130 | 14.9 | 119 | 13.6 |
| CUP | 11.3 | 122 | 14.0 | 112 | 12.8 | 98 | 11.2 |
| STY | 12.6 | 149 | 17.1 | 127 | 14.5 | 112 | 12.8 |
| OAO | 6.4 | 31 | 3.6 | 42 | 4.8 | 58 | 6.6 |
| CON | 18.9 | 185 | 21.2 | 168 | 19.2 | 160 | 18.3 |
| LP | 1.8 | 1 | 0.1 | 1 | 0.1 | 8 | 0.9 |
| NAT | 23.5 | 183 | 21.0 | 213 | 24.4 | 219 | 25.1 |
| **Total** |  | 873 |  | 873 |  | 873 |  |

| Metric | STV | Party list | MMP |
| --- | ---: | ---: | ---: |
| Gallagher index | 6.04 | 3.27 | 1.5 |
| Unrepresented voters % | 0.68 | 16.65 | 10.46 |
| Wasted votes % | 15.03 | 20.98 |  |
| MMP district / top-off / overhang seats |  |  | 436 / 437 / 23 |

### Triple magnitude

| Party | Vote % | STV seats | STV % | List seats | List % | MMP seats | MMP % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DSA | 3.8 | 18 | 1.0 | 29 | 1.7 | 61 | 3.5 |
| PRG | 8.5 | 120 | 7.0 | 134 | 7.8 | 144 | 8.3 |
| LBR | 13.2 | 261 | 15.1 | 240 | 13.9 | 231 | 13.4 |
| CUP | 11.3 | 232 | 13.4 | 210 | 12.2 | 195 | 11.3 |
| STY | 12.6 | 285 | 16.5 | 253 | 14.7 | 223 | 12.9 |
| OAO | 6.4 | 71 | 4.1 | 87 | 5.0 | 114 | 6.6 |
| CON | 18.9 | 357 | 20.7 | 339 | 19.6 | 323 | 18.7 |
| LP | 1.8 | 11 | 0.6 | 11 | 0.6 | 34 | 2.0 |
| NAT | 23.5 | 371 | 21.5 | 423 | 24.5 | 401 | 23.2 |
| **Total** |  | 1726 |  | 1726 |  | 1726 |  |

| Metric | STV | Party list | MMP |
| --- | ---: | ---: | ---: |
| Gallagher index | 4.88 | 2.78 | 0.43 |
| Unrepresented voters % | 0.12 | 14.77 | 1.52 |
| Wasted votes % | 13.89 | 18.96 |  |
| MMP district / top-off / overhang seats |  |  | 436 / 1290 / 1 |

STV seats by turnout stop (double, top7):

| Party | 0% | 5% | 10% | 15% | 20% | 25% | 30% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DSA | 3 | 3 | 2 | 1 | 1 | 2 | 2 |
| PRG | 61 | 59 | 59 | 56 | 54 | 54 | 51 |
| LBR | 142 | 140 | 139 | 138 | 137 | 138 | 139 |
| CUP | 123 | 122 | 124 | 122 | 123 | 123 | 123 |
| STY | 141 | 149 | 152 | 163 | 171 | 180 | 184 |
| OAO | 30 | 31 | 32 | 32 | 32 | 30 | 32 |
| CON | 186 | 185 | 181 | 179 | 180 | 174 | 173 |
| LP | 1 | 1 | 1 | 1 | 1 | 2 | 2 |
| NAT | 186 | 183 | 183 | 181 | 174 | 170 | 167 |

## Presidency

Sources: primary from `viz/public/data/primaryDepth.json` [top7]; general from `viz/public/data/generalDepth.json` [top7] (identical to `rawMultiPresidentialElectionTurnoutL5.json` at the default); top-two reduction from `viz/public/data/topTwo.json`; per-state elector rules computed here with a port of `viz/src/lib/ecAllocation.ts` over `irvStateWinners`, weights `houseStateMap.json` seats + 2.

### Primary (27 candidates, stages Retail → Pod A → Pod C → Pod BD; turnout 5%)

Finalists: LBR_1, CUP_1, STY_1, CON_1, NAT_1. Cells are the vote % held after each stage's STV count; survivors are elected at the quota, so they tie by construction. ✗ marks the stage a candidate was cut.

| Candidate | Retail % | Pod A % | Pod C % | Pod BD % |
| --- | ---: | ---: | ---: | ---: |
| NAT_1 | 7.7 | 10.0 | 12.5 | 16.7 |
| CON_1 | 7.7 | 10.0 | 12.5 | 16.7 |
| LBR_1 | 7.7 | 10.0 | 12.5 | 16.7 |
| STY_1 | 7.7 | 10.0 | 12.5 | 16.7 |
| CUP_1 | 7.7 | 10.0 | 12.5 | 16.7 |
| PRG_1 | 7.7 | 10.0 | 12.5 | 0.0 ✗ |
| NAT_2 | 7.7 | 10.0 | 12.5 | 0.0 ✗ |
| OAO_1 | 7.7 | 10.0 | 0.0 ✗ |  |
| CON_2 | 7.7 | 10.0 | 0.0 ✗ |  |
| CON_3 | 7.7 | 0.0 ✗ |  |  |
| NAT_3 | 7.7 | 0.0 ✗ |  |  |
| STY_2 | 7.7 | 0.0 ✗ |  |  |
| DSA_1 | 0.0 ✗ |  |  |  |
| LP_1 | 0.0 ✗ |  |  |  |
| CUP_2 | 0.0 ✗ |  |  |  |
| CUP_3 | 0.0 ✗ |  |  |  |
| DSA_2 | 0.0 ✗ |  |  |  |
| DSA_3 | 0.0 ✗ |  |  |  |
| LBR_2 | 0.0 ✗ |  |  |  |
| LBR_3 | 0.0 ✗ |  |  |  |
| LP_2 | 0.0 ✗ |  |  |  |
| LP_3 | 0.0 ✗ |  |  |  |
| OAO_2 | 0.0 ✗ |  |  |  |
| OAO_3 | 0.0 ✗ |  |  |  |
| PRG_2 | 0.0 ✗ |  |  |  |
| PRG_3 | 0.0 ✗ |  |  |  |
| STY_3 | 0.0 ✗ |  |  |  |

### General: winners and finalists by turnout stop

| Stop | Finalists (national first-choice %) | Condorcet | IRV | FPTP (first choice) |
| --- | --- | --- | --- | --- |
| 0% | LBR_1 26.7, NAT_1 24.2, CON_1 19.3, STY_1 16.1, CUP_1 13.8 | STY_1 | STY_1 | LBR_1 |
| 5% | LBR_1 26.3, NAT_1 23.7, CON_1 19.2, STY_1 17.1, CUP_1 13.8 | STY_1 | STY_1 | LBR_1 |
| 10% | LBR_1 25.9, NAT_1 23.2, CON_1 19.1, STY_1 17.9, CUP_1 13.7 | STY_1 | STY_1 | LBR_1 |
| 15% | LBR_1 25.6, NAT_1 22.8, CON_1 19.1, STY_1 18.8, CUP_1 13.7 | STY_1 | STY_1 | LBR_1 |
| 20% | LBR_1 25.3, NAT_1 22.4, STY_1 19.6, CON_1 19.0, CUP_1 13.7 | STY_1 | STY_1 | LBR_1 |
| 25% | LBR_1 25.0, NAT_1 22.1, STY_1 20.3, CON_1 18.9, CUP_1 13.7 | STY_1 | STY_1 | LBR_1 |
| 30% | LBR_1 24.7, NAT_1 21.7, STY_1 21.0, CON_1 18.8, CUP_1 13.7 | STY_1 | STY_1 | LBR_1 |

### Head-to-head matrix (turnout 5%): % of voters ranking row above column

|  | LBR_1 | CUP_1 | STY_1 | CON_1 | NAT_1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| LBR_1 | — | 28.9 | 30.1 | 39.4 | 51.8 |
| CUP_1 | 71.1 | — | 45.2 | 50.4 | 65.0 |
| STY_1 | 69.9 | 54.8 | — | 54.8 | 66.7 |
| CON_1 | 60.6 | 49.6 | 45.2 | — | 76.3 |
| NAT_1 | 48.2 | 35.0 | 33.3 | 23.7 | — |

### IRV rounds (turnout 5%)

| Candidate | R1 | R2 | R3 | R4 |
| --- | ---: | ---: | ---: | ---: |
| LBR_1 | 26.3 | 30.1 | 30.1 ✗ |  |
| CUP_1 | 13.8 ✗ |  |  |  |
| STY_1 | 17.1 | 24.7 | 36.6 | 66.7 |
| CON_1 | 19.2 | 21.5 ✗ |  |  |
| NAT_1 | 23.7 | 23.7 | 33.3 | 33.3 |

### Electors by rule and turnout stop

Total electors 975, majority 488. Top-2 rules: every ballot counts for whichever of the two national finalists it ranks higher (pair from the Condorcet or the IRV route), then each state allocates proportionally or winner-take-all. Per-state rules ignore the national result. A blank winner means no majority (the House decides).

| Stop | Rule | Electors | Winner | Note |
| --- | --- | --- | --- | --- |
| 0% | Top-2 proportional (condorcet pair) | STY_1 524, CUP_1 451 | STY_1 | pop STY_1 54.3% |
| 0% | Top-2 WTA (condorcet pair) | STY_1 669, CUP_1 306 | STY_1 | pop STY_1 54.3% |
| 0% | Top-2 proportional (irv pair) | STY_1 652, NAT_1 323 | STY_1 | pop STY_1 66.2% |
| 0% | Top-2 WTA (irv pair) | STY_1 948, NAT_1 27 | STY_1 | pop STY_1 66.2% |
| 0% | Per-state proportional to first choice | LBR_1 261, NAT_1 225, CON_1 190, STY_1 164, CUP_1 135 |  |  |
| 0% | Per-state WTA, first choice | LBR_1 502, NAT_1 451, CON_1 17, STY_1 5 | LBR_1 |  |
| 0% | Per-state IRV, WTA | STY_1 480, CON_1 344, CUP_1 55, NAT_1 51, LBR_1 45 |  |  |
| 0% | Per-state Condorcet, WTA | STY_1 421, CUP_1 294, CON_1 252, LBR_1 8 |  |  |
| 5% | Top-2 proportional (condorcet pair) | STY_1 530, CUP_1 445 | STY_1 | pop STY_1 54.8% |
| 5% | Top-2 WTA (condorcet pair) | STY_1 680, CUP_1 295 | STY_1 | pop STY_1 54.8% |
| 5% | Top-2 proportional (irv pair) | STY_1 656, NAT_1 319 | STY_1 | pop STY_1 66.7% |
| 5% | Top-2 WTA (irv pair) | STY_1 948, NAT_1 27 | STY_1 | pop STY_1 66.7% |
| 5% | Per-state proportional to first choice | LBR_1 257, NAT_1 219, CON_1 189, STY_1 173, CUP_1 137 |  |  |
| 5% | Per-state WTA, first choice | LBR_1 502, NAT_1 437, CON_1 31, STY_1 5 | LBR_1 |  |
| 5% | Per-state IRV, WTA | STY_1 484, CON_1 364, CUP_1 45, NAT_1 41, LBR_1 41 |  |  |
| 5% | Per-state Condorcet, WTA | STY_1 442, CUP_1 283, CON_1 242, LBR_1 8 |  |  |
| 10% | Top-2 proportional (condorcet pair) | STY_1 533, CUP_1 442 | STY_1 | pop STY_1 55.2% |
| 10% | Top-2 WTA (condorcet pair) | STY_1 691, CUP_1 284 | STY_1 | pop STY_1 55.2% |
| 10% | Top-2 proportional (irv pair) | STY_1 658, NAT_1 317 | STY_1 | pop STY_1 67.2% |
| 10% | Top-2 WTA (irv pair) | STY_1 948, NAT_1 27 | STY_1 | pop STY_1 67.2% |
| 10% | Per-state proportional to first choice | LBR_1 254, NAT_1 218, CON_1 188, STY_1 179, CUP_1 136 |  |  |
| 10% | Per-state WTA, first choice | LBR_1 502, NAT_1 378, STY_1 64, CON_1 31 | LBR_1 |  |
| 10% | Per-state IRV, WTA | STY_1 546, CON_1 302, LBR_1 46, NAT_1 41, CUP_1 40 | STY_1 |  |
| 10% | Per-state Condorcet, WTA | STY_1 453, CUP_1 272, CON_1 242, LBR_1 8 |  |  |
| 15% | Top-2 proportional (condorcet pair) | STY_1 540, CUP_1 435 | STY_1 | pop STY_1 55.6% |
| 15% | Top-2 WTA (condorcet pair) | STY_1 711, CUP_1 264 | STY_1 | pop STY_1 55.6% |
| 15% | Top-2 proportional (irv pair) | STY_1 663, NAT_1 312 | STY_1 | pop STY_1 67.6% |
| 15% | Top-2 WTA (irv pair) | STY_1 968, NAT_1 7 | STY_1 | pop STY_1 67.6% |
| 15% | Per-state proportional to first choice | LBR_1 250, NAT_1 213, CON_1 189, STY_1 186, CUP_1 137 |  |  |
| 15% | Per-state WTA, first choice | LBR_1 502, NAT_1 299, STY_1 153, CON_1 21 | LBR_1 |  |
| 15% | Per-state IRV, WTA | STY_1 562, CON_1 241, CUP_1 105, LBR_1 46, NAT_1 21 | STY_1 |  |
| 15% | Per-state Condorcet, WTA | STY_1 513, CUP_1 252, CON_1 202, LBR_1 8 | STY_1 |  |
| 20% | Top-2 proportional (condorcet pair) | STY_1 543, CUP_1 432 | STY_1 | pop STY_1 56.0% |
| 20% | Top-2 WTA (condorcet pair) | STY_1 792, CUP_1 183 | STY_1 | pop STY_1 56.0% |
| 20% | Top-2 proportional (irv pair) | STY_1 673, NAT_1 302 | STY_1 | pop STY_1 68.1% |
| 20% | Top-2 WTA (irv pair) | STY_1 975, NAT_1 0 | STY_1 | pop STY_1 68.1% |
| 20% | Per-state proportional to first choice | LBR_1 248, NAT_1 208, STY_1 193, CON_1 187, CUP_1 139 |  |  |
| 20% | Per-state WTA, first choice | LBR_1 502, NAT_1 239, STY_1 193, CON_1 41 | LBR_1 |  |
| 20% | Per-state IRV, WTA | STY_1 591, CON_1 267, CUP_1 50, LBR_1 46, NAT_1 21 | STY_1 |  |
| 20% | Per-state Condorcet, WTA | STY_1 623, CON_1 173, CUP_1 171, LBR_1 8 | STY_1 |  |
| 25% | Top-2 proportional (condorcet pair) | STY_1 543, CUP_1 432 | STY_1 | pop STY_1 56.4% |
| 25% | Top-2 WTA (condorcet pair) | STY_1 798, CUP_1 177 | STY_1 | pop STY_1 56.4% |
| 25% | Top-2 proportional (irv pair) | STY_1 676, NAT_1 299 | STY_1 | pop STY_1 68.5% |
| 25% | Top-2 WTA (irv pair) | STY_1 975, NAT_1 0 | STY_1 | pop STY_1 68.5% |
| 25% | Per-state proportional to first choice | LBR_1 244, NAT_1 207, STY_1 202, CON_1 186, CUP_1 136 |  |  |
| 25% | Per-state WTA, first choice | LBR_1 502, NAT_1 239, STY_1 193, CON_1 41 | LBR_1 |  |
| 25% | Per-state IRV, WTA | STY_1 697, CON_1 163, LBR_1 58, CUP_1 36, NAT_1 21 | STY_1 |  |
| 25% | Per-state Condorcet, WTA | STY_1 643, CUP_1 165, CON_1 159, LBR_1 8 | STY_1 |  |
| 30% | Top-2 proportional (condorcet pair) | STY_1 550, CUP_1 425 | STY_1 | pop STY_1 56.7% |
| 30% | Top-2 WTA (condorcet pair) | STY_1 802, CUP_1 173 | STY_1 | pop STY_1 56.7% |
| 30% | Top-2 proportional (irv pair) | STY_1 676, NAT_1 299 | STY_1 | pop STY_1 68.9% |
| 30% | Top-2 WTA (irv pair) | STY_1 975, NAT_1 0 | STY_1 | pop STY_1 68.9% |
| 30% | Per-state proportional to first choice | LBR_1 241, STY_1 210, NAT_1 202, CON_1 185, CUP_1 137 |  |  |
| 30% | Per-state WTA, first choice | LBR_1 502, NAT_1 224, STY_1 208, CON_1 41 | LBR_1 |  |
| 30% | Per-state IRV, WTA | STY_1 591, CON_1 163, CUP_1 142, LBR_1 58, NAT_1 21 | STY_1 |  |
| 30% | Per-state Condorcet, WTA | STY_1 643, CUP_1 165, CON_1 159, LBR_1 8 | STY_1 |  |

## Senate

Sources: `viz/src/data/uncertainty<stop>.json` senate (re-clustering bootstrap; the Senate map and chamber read this) and `viz/src/data/pureMultiSenate{Condorcet,IRV}<stop>.json` (the single observed run, the map's fallback fill). Delegations computed with a port of `viz/src/lib/senateDelegations.ts`. Rank-7 ballots, one modelled race per state (51).

The chamber is two senators per state (102 seats). Each state sends its bootstrap-modal winner twice, unless the runner-up is within 21 points of resample win share, in which case it splits one each.

Chamber seats by turnout stop (split states in the last column):

| Stop | Method | DSA | PRG | LBR | CUP | STY | OAO | CON | LP | NAT | Total | Splits |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0% | Condorcet |  |  | 4 | 25 | 27 |  | 46 |  |  | 102 | 14 |
| 0% | IRV |  | 1 | 10 | 13 | 30 |  | 45 |  | 3 | 102 | 17 |
| 5% | Condorcet |  |  | 4 | 24 | 31 |  | 43 |  |  | 102 | 15 |
| 5% | IRV |  | 1 | 8 | 12 | 39 |  | 40 |  | 2 | 102 | 16 |
| 10% | Condorcet |  |  | 4 | 21 | 37 |  | 40 |  |  | 102 | 17 |
| 10% | IRV |  | 1 | 8 | 10 | 44 |  | 36 |  | 3 | 102 | 18 |
| 15% | Condorcet |  |  | 4 | 18 | 41 |  | 39 |  |  | 102 | 17 |
| 15% | IRV |  | 1 | 8 | 9 | 48 |  | 34 |  | 2 | 102 | 19 |
| 20% | Condorcet |  |  | 4 | 15 | 46 |  | 37 |  |  | 102 | 16 |
| 20% | IRV |  | 1 | 8 | 9 | 49 |  | 33 |  | 2 | 102 | 18 |
| 25% | Condorcet |  |  | 4 | 14 | 48 |  | 36 |  |  | 102 | 14 |
| 25% | IRV |  | 1 | 8 | 7 | 55 |  | 30 |  | 1 | 102 | 20 |
| 30% | Condorcet |  |  | 4 | 14 | 53 |  | 31 |  |  | 102 | 16 |
| 30% | IRV |  |  | 8 | 8 | 58 |  | 28 |  |  | 102 | 18 |

Single observed run, one winner per state (51 races):

| Stop | Method | DSA | PRG | LBR | CUP | STY | OAO | CON | LP | NAT |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0% | Condorcet |  |  | 2 | 15 | 13 |  | 21 |  |  |
| 0% | IRV |  | 1 | 4 | 6 | 14 |  | 24 |  | 2 |
| 5% | Condorcet |  |  | 2 | 13 | 16 |  | 20 |  |  |
| 5% | IRV |  | 2 | 2 | 5 | 16 |  | 25 |  | 1 |
| 10% | Condorcet |  |  | 2 | 10 | 19 |  | 20 |  |  |
| 10% | IRV |  | 1 | 3 | 3 | 21 |  | 22 |  | 1 |
| 15% | Condorcet |  |  | 2 | 9 | 23 |  | 17 |  |  |
| 15% | IRV |  | 1 | 3 | 4 | 25 |  | 18 |  |  |
| 20% | Condorcet |  |  | 2 | 6 | 27 |  | 16 |  |  |
| 20% | IRV |  | 1 | 3 | 3 | 27 |  | 17 |  |  |
| 25% | Condorcet |  |  | 2 | 5 | 29 |  | 15 |  |  |
| 25% | IRV |  | 1 | 3 | 3 | 33 |  | 11 |  |  |
| 30% | Condorcet |  |  | 2 | 5 | 29 |  | 15 |  |  |
| 30% | IRV |  | 1 | 3 | 5 | 30 |  | 12 |  |  |

Bootstrap at turnout 5% (1000 draws), on the 102-seat basis with each state's winner doubled: expected [95% range]

| Party | Condorcet | IRV |
| --- | --- | --- |
| DSA |  |  |
| PRG | 0.1 [0–2] | 1.3 [0–4] |
| LBR | 3.6 [0–6] | 9.2 [2–17] |
| CUP | 27.4 [2–80] | 17.3 [2–65] |
| STY | 32.7 [0–61] | 33.8 [0–58] |
| OAO | 0.1 [0–2] | 0.3 [0–2] |
| CON | 37.7 [14–60] | 35.1 [14–52] |
| LP | 0.1 [0–1] | 0.0 [0–1] |
| NAT | 0.2 [0–2] | 5.0 [0–12] |

By state (turnout 5%): observed winner · resample leader and its share · delegation

| State | Cond observed | Cond resample | Cond seats | IRV observed | IRV resample | IRV seats |
| --- | --- | --- | --- | --- | --- | --- |
| AK | STY | STY 80%, CUP 9% | STY/STY | STY | STY 51%, LBR 24% | STY/STY |
| AL | CON | CON 85%, STY 10% | CON/CON | STY | STY 61%, CON 33% | STY/STY |
| AR | STY | STY 48%, CON 47% | STY/CON (split) | STY | STY 66%, CON 26% | STY/STY |
| AZ | CON | CON 96%, CUP 2% | CON/CON | STY | CON 34%, NAT 33% | CON/NAT (split) |
| CA | CUP | CUP 64%, STY 36% | CUP/CUP | STY | STY 53%, CUP 40% | STY/CUP (split) |
| CO | STY | STY 45%, CUP 45% | STY/CUP (split) | CON | LBR 59%, CON 24% | LBR/LBR |
| CT | STY | STY 59%, CUP 41% | STY/CUP (split) | CON | STY 67%, CON 18% | STY/STY |
| DC | LBR | LBR 91%, CUP 6% | LBR/LBR | PRG | LBR 46%, PRG 23% | LBR/LBR |
| DE | CUP | STY 50%, CUP 34% | STY/CUP (split) | CUP | CUP 46%, STY 26% | CUP/STY (split) |
| FL | STY | STY 64%, CUP 28% | STY/STY | STY | STY 84%, CUP 11% | STY/STY |
| GA | STY | STY 56%, CUP 22% | STY/STY | STY | STY 80%, CUP 13% | STY/STY |
| HI | CUP | CUP 50%, STY 46% | CUP/STY (split) | CON | CON 37%, CUP 34% | CON/CUP (split) |
| IA | CON | CON 73%, CUP 21% | CON/CON | CON | CON 47%, CUP 32% | CON/CUP (split) |
| ID | CON | CON 96%, NAT 3% | CON/CON | CON | CON 74%, NAT 19% | CON/CON |
| IL | STY | STY 54%, CUP 45% | STY/CUP (split) | CON | CON 66%, STY 23% | CON/CON |
| IN | CON | CON 70%, STY 22% | CON/CON | CON | CON 64%, STY 31% | CON/CON |
| KS | CON | CON 58%, STY 32% | CON/CON | CON | CON 42%, STY 27% | CON/STY (split) |
| KY | CON | CON 65%, STY 27% | CON/CON | CON | CON 55%, STY 40% | CON/STY (split) |
| LA | CON | CON 74%, STY 19% | CON/CON | STY | STY 80%, CON 8% | STY/STY |
| MA | CUP | CUP 51%, STY 47% | CUP/STY (split) | LBR | LBR 44%, STY 32% | LBR/STY (split) |
| MD | STY | STY 54%, CUP 45% | STY/CUP (split) | STY | STY 61%, CUP 28% | STY/STY |
| ME | CUP | CUP 55%, STY 32% | CUP/CUP | CON | CON 57%, CUP 26% | CON/CON |
| MI | CON | CON 73%, STY 14% | CON/CON | CON | CON 60%, NAT 19% | CON/CON |
| MN | CUP | CUP 81%, STY 10% | CUP/CUP | CON | CON 71%, LBR 17% | CON/CON |
| MO | CON | CON 84%, STY 12% | CON/CON | CON | STY 52%, CON 42% | STY/CON (split) |
| MS | CON | CON 60%, STY 33% | CON/CON | CON | CON 60%, STY 36% | CON/CON |
| MT | CON | CON 84%, STY 8% | CON/CON | CUP | CON 51%, STY 23% | CON/CON |
| NC | STY | STY 61%, CUP 22% | STY/STY | STY | STY 57%, CON 24% | STY/STY |
| ND | CON | CON 62%, CUP 25% | CON/CON | CON | CUP 42%, CON 35% | CUP/CON (split) |
| NE | CON | CON 67%, CUP 17% | CON/CON | CON | CON 47%, CUP 36% | CON/CUP (split) |
| NH | CUP | CUP 78%, STY 11% | CUP/CUP | CON | CON 72%, CUP 20% | CON/CON |
| NJ | CUP | CUP 52%, STY 44% | CUP/STY (split) | CON | CON 65%, CUP 20% | CON/CON |
| NM | STY | STY 74%, CUP 21% | STY/STY | STY | STY 61%, LBR 21% | STY/STY |
| NV | STY | STY 66%, CUP 23% | STY/STY | CON | STY 35%, CON 31% | STY/CON (split) |
| NY | CUP | CUP 50%, STY 49% | CUP/STY (split) | STY | STY 46%, CON 24% | STY/STY |
| OH | STY | CON 51%, STY 32% | CON/STY (split) | CON | CON 50%, STY 42% | CON/STY (split) |
| OK | CON | CON 77%, STY 12% | CON/CON | STY | STY 54%, CUP 25% | STY/STY |
| OR | CUP | CUP 62%, STY 30% | CUP/CUP | LBR | LBR 78%, PRG 9% | LBR/LBR |
| PA | CUP | CUP 66%, STY 27% | CUP/CUP | CON | CON 73%, CUP 21% | CON/CON |
| RI | CUP | CUP 52%, STY 40% | CUP/STY (split) | CUP | CUP 48%, LBR 22% | CUP/CUP |
| SC | STY | STY 50%, CON 35% | STY/CON (split) | STY | STY 79%, CON 12% | STY/STY |
| SD | CON | CON 80%, CUP 11% | CON/CON | CON | CON 68%, CUP 15% | CON/CON |
| TN | CON | CON 99%, NAT 0% | CON/CON | NAT | CON 55%, NAT 32% | CON/CON |
| TX | STY | STY 62%, CUP 22% | STY/STY | STY | STY 92%, CUP 6% | STY/STY |
| UT | CON | CON 77%, STY 16% | CON/CON | CON | CON 51%, STY 36% | CON/STY (split) |
| VA | STY | STY 77%, CUP 18% | STY/STY | STY | STY 75%, CON 15% | STY/STY |
| VT | LBR | LBR 66%, CUP 17% | LBR/LBR | PRG | LBR 32%, PRG 30% | LBR/PRG (split) |
| WA | CUP | CUP 59%, STY 41% | CUP/STY (split) | CUP | CUP 52%, LBR 24% | CUP/CUP |
| WI | STY | CUP 47%, STY 27% | CUP/STY (split) | CUP | CUP 59%, CON 20% | CUP/CUP |
| WV | CON | CON 96%, CUP 3% | CON/CON | CON | CON 95%, CUP 2% | CON/CON |
| WY | CON | CON 86%, CUP 7% | CON/CON | CON | CON 44%, NAT 30% | CON/NAT (split) |

## Legislation

Source: `viz/src/data/candidateVoteModel.json` (37 bills, each party's observed support), computed with a port of `viz/src/components/legislation/PartyAgreement.tsx`. Position-based, so it does not move with seats or turnout.

### Free vote: 100 − average gap in support across the bills

|  | DSA | PRG | LBR | CUP | STY | OAO | CON | LP | NAT |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DSA | — | 92 | 88 | 68 | 63 | 69 | 42 | 53 | 26 |
| PRG | 92 | — | 93 | 75 | 69 | 75 | 48 | 57 | 32 |
| LBR | 88 | 93 | — | 80 | 75 | 81 | 54 | 64 | 38 |
| CUP | 68 | 75 | 80 | — | 85 | 88 | 73 | 74 | 56 |
| STY | 63 | 69 | 75 | 85 | — | 88 | 78 | 78 | 61 |
| OAO | 69 | 75 | 81 | 88 | 88 | — | 72 | 70 | 55 |
| CON | 42 | 48 | 54 | 73 | 78 | 72 | — | 80 | 83 |
| LP | 53 | 57 | 64 | 74 | 78 | 70 | 80 | — | 71 |
| NAT | 26 | 32 | 38 | 56 | 61 | 55 | 83 | 71 | — |

### Whipped: % of bills where both parties' majorities fall on the same side

|  | DSA | PRG | LBR | CUP | STY | OAO | CON | LP | NAT |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DSA | — | 95 | 92 | 73 | 68 | 62 | 24 | 24 | 14 |
| PRG | 95 | — | 97 | 78 | 73 | 68 | 30 | 30 | 19 |
| LBR | 92 | 97 | — | 81 | 76 | 70 | 32 | 32 | 22 |
| CUP | 73 | 78 | 81 | — | 73 | 78 | 51 | 35 | 41 |
| STY | 68 | 73 | 76 | 73 | — | 89 | 57 | 41 | 46 |
| OAO | 62 | 68 | 70 | 78 | 89 | — | 57 | 35 | 46 |
| CON | 24 | 30 | 32 | 51 | 57 | 57 | — | 73 | 89 |
| LP | 24 | 30 | 32 | 35 | 41 | 35 | 73 | — | 84 |
| NAT | 14 | 19 | 22 | 41 | 46 | 46 | 89 | 84 | — |

### Bills at turnout 5% (pass probability; president from the party-line field)

Sources: `houseVoteModelTurnoutL5.json` (houseRawMultiProbPass = STV double, houseListProbPass = party list double), `senateVoteModelTurnoutL5.json` (cond/irvRawMultiProbPass, presRawMultiCond/IRVSigns).

| Bill | Nation % | House STV | House list | Senate Cond | Senate IRV | Pres (Cond) | Pres (IRV) |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| Extend the 2017 tax cuts | 63 | 1.00 | 1.00 | 1.00 | 1.00 | SIGN | SIGN |
| Raise corporate income tax from 21% to 28% | 58 | 1.00 | 1.00 | 0.87 | 0.81 | SIGN | SIGN |
| Allow rates on $400k+ earners to rise to 35% | 65 | 1.00 | 1.00 | 1.00 | 1.00 | SIGN | SIGN |
| Spend $150B/yr on infrastructure | 80 | 1.00 | 1.00 | 1.00 | 1.00 | SIGN | SIGN |
| Grant legal status to long-term undocumented immigrants | 59 | 1.00 | 1.00 | 0.84 | 0.87 | SIGN | SIGN |
| Increase border patrols | 80 | 1.00 | 1.00 | 1.00 | 1.00 | SIGN | SIGN |
| Permanent status/pathway for Dreamers | 70 | 1.00 | 1.00 | 1.00 | 1.00 | SIGN | SIGN |
| Forgive up to $20k of student loan debt per person | 54 | 0.01 | 0.00 | 0.09 | 0.34 | SIGN | SIGN |
| Deny asylum for illegal border crossings | 63 | 1.00 | 1.00 | 1.00 | 1.00 | SIGN | SIGN |
| Ban assault rifles | 60 | 1.00 | 1.00 | 0.93 | 0.89 | SIGN | SIGN |
| Easier concealed-carry permits | 39 | 0.00 | 0.00 | 0.04 | 0.08 | VETO | VETO |
| Require background checks on all gun sales | 93 | 1.00 | 1.00 | 1.00 | 1.00 | SIGN | SIGN |
| Increase police by 10% | 57 | 1.00 | 1.00 | 0.99 | 0.98 | VETO | VETO |
| Decrease police by 10%, increase other funding | 27 | 0.00 | 0.00 | 0.00 | 0.00 | VETO | VETO |
| Increase spending on mental health & school safety | 86 | 1.00 | 1.00 | 1.00 | 1.00 | SIGN | SIGN |
| Prohibit restrictions on abortion access | 63 | 1.00 | 1.00 | 0.92 | 0.92 | SIGN | SIGN |
| Prohibit abortion-inducing drugs by mail | 41 | 0.00 | 0.00 | 0.18 | 0.33 | SIGN | SIGN |
| Prohibit women traveling to another state for abortion | 18 | 0.00 | 0.00 | 0.00 | 0.00 | VETO | VETO |
| Federal recognition of same-sex & interracial marriages | 66 | 1.00 | 1.00 | 0.98 | 0.96 | SIGN | SIGN |
| Ban TikTok unless China sells to a US company | 55 | 1.00 | 1.00 | 0.94 | 0.90 | VETO | VETO |
| Renew post-9/11 surveillance programs | 34 | 0.00 | 0.00 | 0.13 | 0.08 | VETO | VETO |
| Prevent gender transition surgery for minors | 60 | 1.00 | 1.00 | 1.00 | 1.00 | SIGN | SIGN |
| Parental consent for name/pronoun changes at school | 63 | 1.00 | 1.00 | 1.00 | 1.00 | SIGN | SIGN |
| Age verification for adult web content | 79 | 1.00 | 1.00 | 1.00 | 1.00 | SIGN | SIGN |
| School voucher subsidies | 56 | 1.00 | 1.00 | 0.82 | 0.94 | SIGN | SIGN |
| Give EPA power to regulate CO2 emissions | 62 | 1.00 | 1.00 | 0.98 | 0.95 | SIGN | SIGN |
| Require 20% renewable electricity | 66 | 1.00 | 1.00 | 1.00 | 1.00 | SIGN | SIGN |
| Strengthen Clean Air/Water Act enforcement (even if it costs jobs) | 55 | 0.91 | 0.76 | 0.58 | 0.50 | SIGN | SIGN |
| Increase fossil fuel production in the U.S. | 57 | 1.00 | 1.00 | 0.99 | 1.00 | SIGN | SIGN |
| Halt new oil and gas leases on federal lands | 45 | 0.00 | 0.00 | 0.02 | 0.02 | SIGN | SIGN |
| Prevent government from banning gas stoves | 67 | 1.00 | 1.00 | 1.00 | 1.00 | SIGN | SIGN |
| Relax local zoning laws to allow more apartments/condos | 50 | 0.17 | 0.18 | 0.35 | 0.35 | SIGN | SIGN |
| Expand federal tax incentives for affordable housing | 72 | 1.00 | 1.00 | 1.00 | 1.00 | SIGN | SIGN |
| Require able-bodied Medicaid recipients under 64 to work | 53 | 1.00 | 1.00 | 0.88 | 0.84 | SIGN | SIGN |
| Repeal the Affordable Care Act | 38 | 0.00 | 0.00 | 0.02 | 0.07 | VETO | VETO |
| Expand Medicaid (income <$25k individual / <$40k family) | 79 | 1.00 | 1.00 | 1.00 | 1.00 | SIGN | SIGN |
| Build a wall between the U.S. and Mexico | 54 | 1.00 | 1.00 | 0.99 | 1.00 | VETO | VETO |

## Coalitions by domain

Which parties form the majority on each kind of issue, at the app defaults (House STV double magnitude, depth top7, turnout 5%; Senate condorcet delegations), with every party casting all its seats the way its majority leans (support > 50%). Port of `domainCoalitions` / `coalitionSegments` in `viz/src/components/legislation/voteBloc.ts`, over the 37 bills plus the 5 Budget items. Each cell: % of the domain's items on which the party is on the winning side (yes on a pass, no on a defeat), then % on which it is pivotal (the yes party whose seats carry the running total, stacked by support, to half the chamber).

### House: 873 seats, majority 437

| Party | DSA | PRG | LBR | CUP | STY | OAO | CON | LP | NAT |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Seats | 3 | 59 | 140 | 122 | 149 | 31 | 185 | 1 | 183 |

| Domain | Items | Pass | DSA | PRG | LBR | CUP | STY | OAO | CON | LP | NAT |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Taxes & Economy | 5 | 4/5 | 60 | 60 | 60 | 80 | 80 (60) | 80 | 80 (20) | 40 | 60 |
| Immigration | 5 | 4/5 | 60 | 80 | 80 | 100 (80) | 100 | 100 | 60 | 40 | 40 |
| Police & Guns | 6 | 4/6 | 67 | 67 | 67 | 100 (17) | 83 (33) | 100 | 67 (17) | 50 | 67 |
| Abortion | 3 | 2/3 | 67 | 67 | 67 | 67 | 100 (67) | 67 | 67 | 33 | 67 |
| Civil Liberties | 7 | 6/7 | 29 | 43 | 43 | 57 (14) | 86 (57) | 86 | 86 (14) | 71 | 86 |
| Environment & Climate | 6 | 5/6 | 50 | 50 | 67 | 83 (17) | 83 (67) | 83 | 50 | 33 | 50 |
| Healthcare & Housing | 5 | 4/5 | 80 | 80 | 80 | 100 (80) | 100 | 100 | 60 | 0 | 20 |
| Budget | 5 | 4/5 | 60 | 60 | 60 | 100 (20) | 80 (40) | 80 | 100 (20) | 20 | 60 |

| Domain | Most common winning side | Votes | Items | Items that fail |
| --- | --- | ---: | ---: | --- |
| Taxes & Economy | DSA PRG LBR CUP STY OAO CON NAT | yes | 1/5 | Forgive up to $20k of student loan debt per person |
| Immigration | PRG LBR CUP STY OAO CON LP NAT | yes | 1/5 | Build a wall between the U.S. and Mexico |
| Police & Guns | DSA PRG LBR CUP STY OAO CON LP NAT | yes | 2/6 | Easier concealed-carry permits; Decrease police by 10%, increase other funding |
| Abortion | DSA PRG LBR CUP STY OAO CON LP NAT | no | 1/3 | Prohibit women traveling to another state for abortion |
| Civil Liberties | STY OAO CON LP NAT | yes | 3/7 | Renew post-9/11 surveillance programs |
| Environment & Climate | DSA PRG LBR CUP STY OAO | yes | 3/6 | Halt new oil and gas leases on federal lands |
| Healthcare & Housing | DSA PRG LBR CUP STY OAO CON | yes | 2/5 | Repeal the Affordable Care Act |
| Budget | DSA PRG LBR CUP STY OAO CON | yes | 2/5 | Increase state spending on welfare |

### Senate: 102 seats, majority 52

| Party | DSA | PRG | LBR | CUP | STY | OAO | CON | LP | NAT |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Seats | 0 | 0 | 4 | 24 | 31 | 0 | 43 | 0 | 0 |

| Domain | Items | Pass | DSA | PRG | LBR | CUP | STY | OAO | CON | LP | NAT |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Taxes & Economy | 5 | 4/5 |  |  | 60 | 80 | 80 (60) |  | 80 (20) |  |  |
| Immigration | 5 | 4/5 |  |  | 80 | 100 (80) | 100 |  | 60 |  |  |
| Police & Guns | 6 | 4/6 |  |  | 67 | 100 (17) | 83 (33) |  | 67 (17) |  |  |
| Abortion | 3 | 2/3 |  |  | 67 | 67 | 100 (67) |  | 67 |  |  |
| Civil Liberties | 7 | 6/7 |  |  | 43 | 57 (14) | 86 (57) |  | 86 (14) |  |  |
| Environment & Climate | 6 | 5/6 |  |  | 67 | 83 (17) | 83 (67) |  | 50 |  |  |
| Healthcare & Housing | 5 | 4/5 |  |  | 80 | 100 (80) | 100 |  | 60 |  |  |
| Budget | 5 | 4/5 |  |  | 60 | 100 (20) | 80 (40) |  | 100 (20) |  |  |

| Domain | Most common winning side | Votes | Items | Items that fail |
| --- | --- | ---: | ---: | --- |
| Taxes & Economy | LBR CUP STY CON | yes | 2/5 | Forgive up to $20k of student loan debt per person |
| Immigration | LBR CUP STY CON | yes | 2/5 | Build a wall between the U.S. and Mexico |
| Police & Guns | LBR CUP STY CON | yes | 2/6 | Easier concealed-carry permits; Decrease police by 10%, increase other funding |
| Abortion | LBR CUP STY CON | no | 1/3 | Prohibit women traveling to another state for abortion |
| Civil Liberties | STY CON | yes | 3/7 | Renew post-9/11 surveillance programs |
| Environment & Climate | LBR CUP STY | yes | 3/6 | Halt new oil and gas leases on federal lands |
| Healthcare & Housing | LBR CUP STY CON | yes | 2/5 | Repeal the Affordable Care Act |
| Budget | LBR CUP STY CON | yes | 3/5 | Increase state spending on welfare |

## Budget priorities

Source: `viz/src/data/budgetPriorities.json` (`pipeline/build_budget_priorities.py`), CES CC24_443_1..5: should the respondent's state legislature increase or decrease spending on each category. Each cell is the weighted % choosing slightly or greatly increase, against maintain or decrease. These are state spending preferences, not federal bills; they are not in the bill set the party order is computed from. Port of `viz/src/components/legislation/BudgetPriorities.tsx`.

### Level and share by category (% wanting more; level = mean of the 5, national 57)

| Party | Level | Welfare | Health care | Education | Law enforcement | Transportation & infrastructure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| OAO | 89 | 68 | 100 | 98 | 88 | 92 |
| PRG | 79 | 81 | 100 | 99 | 24 | 93 |
| DSA | 77 | 94 | 100 | 100 | 0 | 94 |
| LBR | 65 | 55 | 89 | 88 | 16 | 79 |
| CUP | 58 | 19 | 71 | 70 | 60 | 69 |
| CON | 55 | 15 | 57 | 59 | 83 | 63 |
| STY | 52 | 39 | 69 | 64 | 37 | 51 |
| NAT | 38 | 1 | 18 | 29 | 84 | 59 |
| LP | 15 | 11 | 18 | 17 | 11 | 20 |
| National | 57 | 33 | 64 | 65 | 55 | 66 |

### Mix: category minus the party's own level, in points

| Party | Welfare | Health care | Education | Law enforcement | Transportation & infrastructure |
| --- | ---: | ---: | ---: | ---: | ---: |
| OAO | -21 | +11 | +9 | -1 | +3 |
| PRG | +2 | +20 | +19 | -56 | +14 |
| DSA | +16 | +22 | +22 | -77 | +17 |
| LBR | -11 | +24 | +23 | -49 | +13 |
| CUP | -38 | +13 | +12 | +2 | +11 |
| CON | -41 | +2 | +3 | +27 | +8 |
| STY | -13 | +17 | +12 | -15 | -1 |
| NAT | -37 | -20 | -9 | +46 | +21 |
| LP | -5 | +3 | +2 | -4 | +5 |

### Chamber outcome at the defaults (free vote: P(pass), port of `passProbability`; whipped: pass/fail)

| Category | Nation % | House free | House whipped | House yes side | Senate free | Senate whipped | Senate yes side |
| --- | ---: | ---: | --- | --- | ---: | --- | --- |
| Welfare | 33 | 0.00 | fails | DSA PRG OAO LBR | 0.00 | fails | LBR |
| Health care | 64 | 1.00 | passes, pivotal STY | DSA OAO PRG LBR CUP STY CON | 1.00 | passes, pivotal STY | LBR CUP STY CON |
| Education | 65 | 1.00 | passes, pivotal STY | DSA PRG OAO LBR CUP STY CON | 1.00 | passes, pivotal STY | LBR CUP STY CON |
| Law enforcement | 55 | 1.00 | passes, pivotal CUP | OAO NAT CON CUP | 0.99 | passes, pivotal CUP | CON CUP |
| Transportation & infrastructure | 66 | 1.00 | passes, pivotal CON | DSA PRG OAO LBR CUP CON NAT STY | 0.99 | passes, pivotal CON | LBR CUP CON STY |
