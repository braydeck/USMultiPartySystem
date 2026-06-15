# Full Reform.md — Data Audit

## Overview

Full Reform.md contains simulation results from an **old pipeline** that produced "coalition blend" candidates (CON/SD, SD/STY, etc.). The current viz app uses a different data model:

- **Crossover candidates** (Factor Deviation): axis-shifted variants like STY_lo_ae, CON_hi_pc
- **Pure partisans** (Raw Multi): identical-position candidates like STY_1, CON_1

The sections below need updating to match the current data.

---

## Sections That Need Updating

### 1. Presidential Winner (~lines 1025-1031)

**Current claim:** "Both IRV and Condorcet elect the same president: an SD/CON coalition candidate."

**Actual data:**

- Crossover IRV: STY_hi_so (Solidarity, tough on security) — 60.3% final round
- Crossover Condorcet: STY_hi_so (same winner)
- Pure partisan IRV: SD_1 (Social Democrat) — 54.4% final round
- Pure partisan Condorcet: STY_1 (Solidarity)

**Action:** Complete rewrite. The "coalition blend" presidential candidate concept no longer exists.

---

### 2. Senate Coalition Types (~lines 1264-1426)

**Current claim:** 16 named coalition types (SD/STY, CON/SD, CON/STY, CON/CTR, CON/REF, SD/LIB, STY/SD, STY/CON, STY/REF, SD/CON, REF/STY, REF/SD, CTR/LIB, PRG/DSA, CON/NAT, LIB/CTR) with detailed profiles and state lists.

**Actual data:** None of these types exist. The current pipeline produces axis-deviation candidates (e.g., STY_lo_ae, SD_hi_so) — same party with a shift on one ideological dimension, not two-party blends.

**Action:** Replace entire section with crossover candidate profiles based on actual FD data.

---

### 3. Single-Party Senate Seats (~lines 1438-1450)

**Current claims:** STY IRV:2 / Cond:5, SD IRV:6 / Cond:6, CON IRV:3 / Cond:3, CTR IRV:2 / Cond:1, LIB IRV:1 / Cond:1

**Actual data (pure partisan field):**

- Condorcet: STY 33, SD 15, CON 1, REF 1, CTR 1
- IRV: SD 26, CON 11, STY 11, REF 2, LIB 1

**Action:** Replace with actual pure partisan seat counts.

---

### 4. State-by-State Senate Table (~lines 1479-1535)

**Current claim:** Lists all 51 seats using coalition blend notation (CON/STY, SD/STY, etc.) with 17 states differing between methods.

**Actual data:** Every entry uses wrong notation. The crossover field shows 21 states where the winning party differs between Condorcet and IRV. The pure partisan field shows 25 states that differ.

**Action:** Replace entire table with actual data from the four JSON files (fdSenateCondorcet, fdSenateIRV, pureMultiSenateCondorcet, pureMultiSenateIRV).

---

### 5. Legislative Outlook (~lines 1543-1575)

**Specific wrong claims:**

- "Deny asylum passes both chambers in all scenarios" — Actually FAILS in FD senate (condFD: 22.6%, irvFD: 12.4%)
- "Police funding increase passes both chambers in all scenarios" — FAILS in FD senate (condFD: 2.2%, irvFD: 1.3%)
- "TikTok ban passes both chambers" — FAILS in FD senate (condFD: 19.4%, irvFD: 22.6%)
- "Halt oil/gas leases fails in all scenarios" — Actually PASSES in FD IRV senate (89.3%)
- "Student loan forgiveness — CON/SD vetoes" — No CON/SD president exists. FD president (STY_hi_so) signs it.
- "The Five Split Bills" framework — Too simple. The actual data shows ~10+ bills that vary across scenarios.
- Medicaid work requirements: described as passing; actually TOSS-UP in FD senate
- Fossil fuel production: described as passing all; actually TOSS-UP/FAIL in FD senate

**Action:** Rewrite with scenario-dependent analysis. The FD senate (dominated by STY variants) produces substantially more left-leaning outcomes than the old document described.

---

### 6. Factor Score Table (~lines 1617-1643)

**Current claim:** 23 types listed (9 parties + 14 coalition blends like CON/NAT, SD/LIB, STY/REF, etc.)

**Actual data:** Coalition blend types don't exist. Should list 9 base parties + key crossover variants that actually win seats.

**Action:** Replace with factor scores for base parties and winning crossover types.

---

## Sections That Are Correct (No Updates Needed)

- **Lines 1-342 (Diagnosis & Thesis)** — Pure theory and institutional analysis
- **Lines 343-860 (Electoral Reform design)** — Legislative architecture, funding mechanisms
- **Lines 1035-1262 (The Nine Parties, Part I)** — Demographics, policy positions, house seat counts are all correct
- **Lines 1577-1614 (Factor definitions F1-F5)** — Methodology unchanged
- **Lines 1649+ (Governance Reform)** — CRO, JIRA legislature design — no simulation data

---

## Data Source Files (for updating)

| File | Contents |
|------|----------|
| `viz/src/data/fdSenateCondorcet.json` | Crossover Condorcet senate |
| `viz/src/data/fdSenateIRV.json` | Crossover IRV senate |
| `viz/src/data/pureMultiSenateCondorcet.json` | Pure partisan Condorcet senate |
| `viz/src/data/pureMultiSenateIRV.json` | Pure partisan IRV senate |
| `viz/src/data/fdPresidentialElection.json` | Crossover presidential |
| `viz/src/data/rawMultiPresidentialElection.json` | Pure partisan presidential |
| `viz/src/data/senateVoteModel.json` | Senate vote predictions |
| `viz/src/data/houseVoteModel.json` | House vote predictions |
