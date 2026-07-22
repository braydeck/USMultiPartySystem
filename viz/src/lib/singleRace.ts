// Single Race Simulator — in-browser evaluation of the app's canonical ballot model.
//
// A voter ranks all candidates by the hybrid score from
// generate_factor_deviation_ballots.compute_candidate_scores_hybrid (the scorer that
// built ballots.csv, driving the House STV / Senate IRV / Presidency IRV sims):
//
//   base candidate:    score = prob_cluster_k                          (GMM posterior)
//   variant candidate: score = prob_cluster_k * gauss(variant)/gauss(base)
//
// In a two-way FPTP race the vote goes to whichever candidate ranks higher — exactly
// how a vote transfers to its next-preferred surviving candidate in IRV/STV.
//
// We compare in log space (underflow-proof, exact ranking). Each shipped voter row is
// [w, f1..f5, lp0..lp9] where lp_k = log(prob_cluster_k). Validated to match ballots.csv
// 100% across base, cross-party, and variant matchups.

export interface SRCandidate {
  code: string;
  party: string;
  axis: string;      // 'base' | 'so' | 'es' | 'pc'
  direction: string; // 'base' | 'hi' | 'lo'
  pos: number[];     // 5-D position
}

export interface SRState {
  fips: string;
  abbr: string;
  name: string;
  ev: number;
  cds: string[];
}

export interface SRMeta {
  sigma: number;
  meNe: Record<string, { statewide: number; districts: string[] }>;
  totalEV: number;
  partyOrder: string[];
  partyClusters: Record<string, number>;
  states: SRState[];
  candidates: SRCandidate[];
}

export interface SRVoters {
  sigma: number;
  byCD: Record<string, number[][]>;
}

export interface H2HResult {
  shareA: number;
  shareB: number;
  wA: number;
  wB: number;
  winner: 'A' | 'B';
  margin: number; // |shareA - shareB|
  n: number;      // unweighted respondent count
}

export type ECRule = 'currentLaw' | 'proportional';

export interface ECStateResult {
  fips: string;
  abbr: string;
  ev: number;
  shareA: number;
  evA: number;
  evB: number;
  winner: 'A' | 'B';
  split: boolean; // ME/NE or proportional split between the two
}

export interface ECResult {
  states: ECStateResult[];
  evA: number;
  evB: number;
  needed: number;
  winner: 'A' | 'B' | 'tie';
}

const W_IDX = 0;
const F_IDX = 1;              // factors at rows[1..5]
const LP_IDX = 6;             // log-posteriors at rows[6..15]
const GAUSS_FLOOR_ADD = -Math.log(1e-10); // 23.0258509 — mirrors the 1e-10 gauss(base) floor

/** The four discriminating factor axes exposed as electorate-shift sliders (F3 residual excluded).
 * Ordered by discriminatory power: Populist Conservatism, Law & Order, Institutional Trust, Religious Traditionalism. */
export const SHIFT_AXES = [
  { idx: 4, factor: 'F5' },
  { idx: 0, factor: 'F1' },
  { idx: 1, factor: 'F2' },
  { idx: 3, factor: 'F4' },
] as const;

/**
 * An electorate shift. Both are raw-factor 5-vectors (F3 held at 0), defaulting to none.
 *  - opinionDelta: minds change. A uniform issue shift adds a constant tilt
 *    δ·(posA−posB)/σ² to every voter's margin — matters only insofar as the shift
 *    aligns with what separates the two candidates; swing voters flip, partisans hold.
 *  - turnoutBeta: who turns out. Exponential re-weighting w·exp(Σ βⱼ·fⱼ) toward a pole.
 * At zero it reproduces the validated baseline exactly.
 */
export interface Shift {
  opinionDelta?: number[];
  turnoutBeta?: number[];
}

export interface SingleRaceEngine {
  candByCode: Record<string, SRCandidate>;
  statesByFips: Record<string, SRState>;
  allCds: string[];
  factorSD: number[];
  /** Solve per-axis β so the national weighted mean of each factor shifts by sigmaTargets·SD. */
  solveTurnoutBeta: (sigmaTargets: number[]) => number[];
  /** Effective sample fraction (ESS/n) of the national electorate under a turnout β. */
  essFraction: (turnoutBeta?: number[]) => number;
  headToHead: (cdIds: string[], a: SRCandidate, b: SRCandidate, shift?: Shift) => H2HResult;
  presidencyEC: (a: SRCandidate, b: SRCandidate, rule: ECRule, shift?: Shift) => ECResult;
  /** First-choice party makeup of an electorate (share per base party, sums to 1). */
  partyBreakdown: (cdIds: string[], turnoutBeta?: number[]) => Record<string, number>;
  /** Where each candidate's votes come from — their voters' first-choice-party composition. */
  coalition: (cdIds: string[], a: SRCandidate, b: SRCandidate, shift?: Shift) => Coalition;
  /** Per-cluster targeting inputs for candidate A in a geography: electorate weight + A's share. */
  microtarget: (cdIds: string[], a: SRCandidate, b: SRCandidate, shift?: Shift) => MicrotargetGroup[];
}

/** One cluster's targeting inputs within a geography, from candidate A's perspective. */
export interface MicrotargetGroup {
  party: string;
  weight: number;     // cluster's share of the (turnout-weighted) electorate here, 0–1
  alignment: number;  // A's two-way share among that cluster's voters, 0–1
  contestedA: number; // near-boundary voters currently leaning A, as share of the whole electorate
  contestedB: number; // near-boundary voters currently leaning B, as share of the whole electorate
}

export interface Coalition {
  a: Record<string, number>; // normalised within candidate A's voters (sums to 1)
  b: Record<string, number>;
  shareA: number;
  shareB: number;
}

export function createEngine(voters: SRVoters, meta: SRMeta): SingleRaceEngine {
  const clusters = meta.partyClusters;
  const twoSigmaSq = 2 * meta.sigma * meta.sigma;

  const basePos: Record<string, number[]> = {};
  const candByCode: Record<string, SRCandidate> = {};
  for (const c of meta.candidates) {
    candByCode[c.code] = c;
    if (c.axis === 'base') basePos[c.party] = c.pos;
  }
  const statesByFips: Record<string, SRState> = {};
  for (const s of meta.states) statesByFips[s.fips] = s;
  const allCds = Object.keys(voters.byCD);

  const clusterToParty: string[] = [];
  for (const [party, k] of Object.entries(clusters)) clusterToParty[k] = party;

  // Flat national view for factor stats / turnout solves.
  const allRows: number[][] = [];
  for (const cd of allCds) for (const row of voters.byCD[cd]) allRows.push(row);

  const factorMean = [0, 0, 0, 0, 0];
  const factorSD = [0, 0, 0, 0, 0];
  {
    let wsum = 0;
    for (const r of allRows) wsum += r[W_IDX];
    for (let i = 0; i < 5; i++) {
      let m = 0;
      for (const r of allRows) m += r[W_IDX] * r[F_IDX + i];
      m /= wsum;
      let v = 0;
      for (const r of allRows) { const d = r[F_IDX + i] - m; v += r[W_IDX] * d * d; }
      factorMean[i] = m;
      factorSD[i] = Math.sqrt(v / wsum);
    }
  }

  function sqDist(row: number[], pos: number[]): number {
    let s = 0;
    for (let i = 0; i < 5; i++) {
      const d = row[F_IDX + i] - pos[i];
      s += d * d;
    }
    return s;
  }

  function logScore(row: number[], cand: SRCandidate): number {
    // Generic real-party candidates (DEM/REP/IND) aren't typology clusters, so they have no
    // posterior — score them by pure Gaussian proximity to their factor-space centroid.
    if (cand.axis === 'current') return -sqDist(row, cand.pos) / twoSigmaSq;
    const lp = row[LP_IDX + clusters[cand.party]];
    if (cand.axis === 'base') return lp;
    const dVar = sqDist(row, cand.pos);
    const dBase = sqDist(row, basePos[cand.party]);
    return lp - dVar / twoSigmaSq + Math.min(dBase / twoSigmaSq, GAUSS_FLOOR_ADD);
  }

  /** Opinion tilt constant for a matchup: δ·(posA−posB)/σ² (position-independent, see Shift). */
  function opinionK(a: SRCandidate, b: SRCandidate, delta?: number[]): number {
    if (!delta) return 0;
    let k = 0;
    for (let i = 0; i < 5; i++) k += delta[i] * (a.pos[i] - b.pos[i]);
    return k / (meta.sigma * meta.sigma);
  }

  /** Per-voter turnout weight multiplier exp(Σ βⱼ·fⱼ). */
  function turnoutMul(row: number[], beta?: number[]): number {
    if (!beta) return 1;
    let e = 0;
    for (let i = 0; i < 5; i++) e += beta[i] * row[F_IDX + i];
    return Math.exp(e);
  }

  function headToHead(cdIds: string[], a: SRCandidate, b: SRCandidate, shift?: Shift): H2HResult {
    const k = opinionK(a, b, shift?.opinionDelta);
    const beta = shift?.turnoutBeta;
    let wA = 0;
    let wB = 0;
    let n = 0;
    for (const cd of cdIds) {
      const rows = voters.byCD[cd];
      if (!rows) continue;
      for (const row of rows) {
        const w = row[W_IDX] * turnoutMul(row, beta);
        if (logScore(row, a) - logScore(row, b) + k >= 0) wA += w;
        else wB += w;
        n++;
      }
    }
    const tot = wA + wB || 1;
    return {
      shareA: wA / tot,
      shareB: wB / tot,
      wA,
      wB,
      winner: wA >= wB ? 'A' : 'B',
      margin: Math.abs(wA - wB) / tot,
      n,
    };
  }

  /** A voter's first-choice party = the base cluster with the highest posterior. */
  function firstParty(row: number[]): string {
    let bi = 0;
    let best = row[LP_IDX];
    for (let k = 1; k < 10; k++) {
      const v = row[LP_IDX + k];
      if (v > best) { best = v; bi = k; }
    }
    return clusterToParty[bi];
  }

  function partyBreakdown(cdIds: string[], turnoutBeta?: number[]): Record<string, number> {
    const acc: Record<string, number> = {};
    let tot = 0;
    for (const cd of cdIds) {
      const rows = voters.byCD[cd];
      if (!rows) continue;
      for (const row of rows) {
        const w = row[W_IDX] * turnoutMul(row, turnoutBeta);
        acc[firstParty(row)] = (acc[firstParty(row)] ?? 0) + w;
        tot += w;
      }
    }
    for (const p in acc) acc[p] /= tot || 1;
    return acc;
  }

  function coalition(cdIds: string[], a: SRCandidate, b: SRCandidate, shift?: Shift): Coalition {
    const k = opinionK(a, b, shift?.opinionDelta);
    const beta = shift?.turnoutBeta;
    const aAcc: Record<string, number> = {};
    const bAcc: Record<string, number> = {};
    let wA = 0;
    let wB = 0;
    for (const cd of cdIds) {
      const rows = voters.byCD[cd];
      if (!rows) continue;
      for (const row of rows) {
        const w = row[W_IDX] * turnoutMul(row, beta);
        const p = firstParty(row);
        if (logScore(row, a) - logScore(row, b) + k >= 0) { aAcc[p] = (aAcc[p] ?? 0) + w; wA += w; }
        else { bAcc[p] = (bAcc[p] ?? 0) + w; wB += w; }
      }
    }
    for (const p in aAcc) aAcc[p] /= wA || 1;
    for (const p in bAcc) bAcc[p] /= wB || 1;
    const tot = wA + wB || 1;
    return { a: aAcc, b: bAcc, shareA: wA / tot, shareB: wB / tot };
  }

  // A voter is "contested" when the two candidates' deciding scores are within this many log points
  // (|margin| < CONTEST_BAND ≈ the two scores within ~1.8×, i.e. a two-way prob roughly 0.35–0.65).
  // These are the swingable voters a modest opinion shift would flip.
  const CONTEST_BAND = 0.6;

  /** Per first-choice cluster: weight in the electorate, A's share within it, and near-boundary mass. */
  function microtarget(cdIds: string[], a: SRCandidate, b: SRCandidate, shift?: Shift): MicrotargetGroup[] {
    const k = opinionK(a, b, shift?.opinionDelta);
    const beta = shift?.turnoutBeta;
    const wTot: Record<string, number> = {};
    const wAwin: Record<string, number> = {};
    const wCloseA: Record<string, number> = {}; // near-boundary, currently A
    const wCloseB: Record<string, number> = {}; // near-boundary, currently B
    let total = 0;
    for (const cd of cdIds) {
      const rows = voters.byCD[cd];
      if (!rows) continue;
      for (const row of rows) {
        const w = row[W_IDX] * turnoutMul(row, beta);
        const p = firstParty(row);
        wTot[p] = (wTot[p] ?? 0) + w;
        total += w;
        const margin = logScore(row, a) - logScore(row, b) + k;
        if (margin >= 0) {
          wAwin[p] = (wAwin[p] ?? 0) + w;
          if (margin < CONTEST_BAND) wCloseA[p] = (wCloseA[p] ?? 0) + w;
        } else if (-margin < CONTEST_BAND) {
          wCloseB[p] = (wCloseB[p] ?? 0) + w;
        }
      }
    }
    return Object.keys(wTot).map(p => ({
      party: p,
      weight: wTot[p] / (total || 1),
      alignment: (wAwin[p] ?? 0) / (wTot[p] || 1),
      contestedA: (wCloseA[p] ?? 0) / (total || 1),
      contestedB: (wCloseB[p] ?? 0) / (total || 1),
    }));
  }

  /** Solve β per axis (independent 1-D bisection) so the national weighted mean of each
   * shifted factor moves by sigmaTargets·SD. Non-shift axes get β=0. */
  function solveTurnoutBeta(sigmaTargets: number[]): number[] {
    const beta = [0, 0, 0, 0, 0];
    for (const { idx } of SHIFT_AXES) {
      const s = sigmaTargets[idx] ?? 0;
      if (!s) continue;
      const target = factorMean[idx] + s * factorSD[idx];
      const meanAt = (bt: number) => {
        let num = 0, den = 0;
        for (const r of allRows) {
          const wv = r[W_IDX] * Math.exp(bt * r[F_IDX + idx]);
          num += wv * r[F_IDX + idx];
          den += wv;
        }
        return num / den;
      };
      let lo = -50, hi = 50;
      for (let it = 0; it < 60; it++) {
        const mid = (lo + hi) / 2;
        if (meanAt(mid) < target) lo = mid;
        else hi = mid;
      }
      beta[idx] = (lo + hi) / 2;
    }
    return beta;
  }

  function essFraction(beta?: number[]): number {
    let s = 0, s2 = 0;
    for (const r of allRows) {
      const w = r[W_IDX] * turnoutMul(r, beta);
      s += w;
      s2 += w * w;
    }
    return s2 > 0 ? (s * s) / s2 / allRows.length : 1;
  }

  function presidencyEC(a: SRCandidate, b: SRCandidate, rule: ECRule, shift?: Shift): ECResult {
    const states: ECStateResult[] = [];
    let evA = 0;
    let evB = 0;

    for (const st of meta.states) {
      const r = headToHead(st.cds, a, b, shift);
      let sA = 0;
      let sB = 0;
      let split = false;

      if (rule === 'currentLaw') {
        const meNe = meta.meNe[st.fips];
        if (meNe) {
          split = true;
          if (r.winner === 'A') sA += meNe.statewide;
          else sB += meNe.statewide;
          for (const cd of meNe.districts) {
            const rd = headToHead([cd], a, b, shift);
            if (rd.winner === 'A') sA += 1;
            else sB += 1;
          }
        } else if (r.winner === 'A') sA = st.ev;
        else sB = st.ev;
      } else {
        // Proportional: largest-remainder (Hamilton) two-way split.
        const aExact = r.shareA * st.ev;
        const bExact = st.ev - aExact;
        let aFloor = Math.floor(aExact);
        let bFloor = Math.floor(bExact);
        if (aFloor + bFloor < st.ev) {
          if (aExact - aFloor >= bExact - bFloor) aFloor += 1;
          else bFloor += 1;
        }
        sA = aFloor;
        sB = bFloor;
        split = sA > 0 && sB > 0;
      }

      evA += sA;
      evB += sB;
      states.push({
        fips: st.fips,
        abbr: st.abbr,
        ev: st.ev,
        shareA: r.shareA,
        evA: sA,
        evB: sB,
        winner: sA >= sB ? 'A' : 'B',
        split,
      });
    }

    const needed = Math.floor(meta.totalEV / 2) + 1; // 270
    const winner = evA >= needed ? 'A' : evB >= needed ? 'B' : 'tie';
    return { states, evA, evB, needed, winner };
  }

  return { candByCode, statesByFips, allCds, factorSD, solveTurnoutBeta, essFraction, headToHead, presidencyEC, partyBreakdown, coalition, microtarget };
}

// ── Candidate labelling (public-writing voice: plain position statements) ──────────

const AXIS_STYLE: Record<string, { hi: string; lo: string }> = {
  so: { hi: 'more law-and-order', lo: 'more civil-libertarian' },
  es: { hi: 'more election-skeptic', lo: 'more institutionalist' },
  pc: { hi: 'more economically conservative', lo: 'more economically progressive' },
};

/** Short style descriptor for a candidate variant, or '' for a base party. */
export function styleLabel(cand: SRCandidate): string {
  if (cand.axis === 'base' || cand.axis === 'current') return '';
  const s = AXIS_STYLE[cand.axis];
  if (!s) return `${cand.direction} ${cand.axis}`;
  return cand.direction === 'hi' ? s.hi : s.lo;
}
