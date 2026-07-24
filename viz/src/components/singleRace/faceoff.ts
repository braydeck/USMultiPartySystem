// Shared faceoff math for the Single Race view: turns per-cluster microtarget inputs into the
// A-vs-B bar segments (likely vs mobilize) and the persuadable middle. Used by the headline bar
// and the per-cluster breakdown alike.
import partyPopulation from '../../data/partyPopulation.json';
import clusterProfiles from '../../data/clusterProfiles.json';
import type { MicrotargetGroup } from '../../lib/singleRace';

// ── Turnout by election cycle — CES 2020-2024 validated voter file data ─────────────────────
// Presidential turnout from 2024 CES (TargetSmart TS_g2024), midterm from 2022 (TS_g2022),
// cross-validated against 2020 (Catalist CL_2020gvm). Rates are per-party, nationally weighted.
// Retention = fraction of the party's base that shows up for the given cycle type.
const CIVIC = ['newsint', 'CC24_430a_1', 'CC24_430a_2', 'CC24_430a_3', 'CC24_430a_4', 'CC24_430a_5', 'CC24_430a_6'];

export type ElectionCycle = 'midterm' | 'presidential';

type PopRow = { party: string; turnoutPresidential: number; turnoutMidterm: number };
type Profile = { party: string; variables: Record<string, { pct?: number }> };

const turnoutByParty: Record<string, { presidential: number; midterm: number }> = {};
for (const r of partyPopulation as PopRow[])
  turnoutByParty[r.party] = { presidential: r.turnoutPresidential / 100, midterm: r.turnoutMidterm / 100 };

const engByParty: Record<string, number> = {};
for (const c of clusterProfiles as Profile[]) {
  const vals = CIVIC.map(k => c.variables[k]?.pct).filter((x): x is number => x != null);
  engByParty[c.party] = vals.reduce((s, x) => s + x, 0) / (vals.length || 1);
}
const ev = Object.values(engByParty);
const eMin = Math.min(...ev), eMax = Math.max(...ev);
const persuadByParty: Record<string, number> = {};
for (const [p, e] of Object.entries(engByParty)) persuadByParty[p] = 1 - (e - eMin) / ((eMax - eMin) || 1);

export const retention = (p: string, cycle: ElectionCycle = 'midterm') => {
  const t = turnoutByParty[p];
  return t ? t[cycle] : 0.60;
};
export const persuadability = (p: string) => persuadByParty[p] ?? 0.5;

/**
 * All widths are percentages within the bar's scope (electorate or one cluster). Each side splits
 * into mobilize (dormant pole) + likely (solid) + persuadable (soft, near the boundary). Persuadable
 * is A-side vs B-side — different voters — so the bar and table can mark them apart.
 */
export interface Faceoff {
  aPct: number; bPct: number;         // total support for A / B (full population, sums to 100)
  aMobPct: number; bMobPct: number;   // dormant subset within each side's total
  aPerPct: number; bPerPct: number;   // "persuadable": near-boundary voters currently leaning A / B
  aLikelyPct: number; bLikelyPct: number; // likely-voter result (active only, sums to 100)
}

/** Whole-electorate faceoff from the per-cluster microtarget groups.
 *  aMobRate/bMobRate (0–1): fraction of each side's unlikely-voter pool that gets mobilized
 *  (converted from dormant to active). At 0 = baseline turnout. At 1 = every aligned unlikely
 *  voter shows up. The mobilized voters shift the effective electorate composition — if A
 *  mobilizes but B doesn't, A gains effective vote share. */
export function aggregateFaceoff(
  groups: MicrotargetGroup[],
  cycle: ElectionCycle = 'midterm',
  aMobRate = 0,
  bMobRate = 0,
): Faceoff {
  let aLik = 0, bLik = 0, aMob = 0, bMob = 0, aPer = 0, bPer = 0;
  for (const g of groups) {
    const ret = retention(g.party, cycle), per = persuadability(g.party);
    const aTotal = g.weight * g.alignment;
    const bTotal = g.weight * (1 - g.alignment);
    const aDormant = aTotal * (1 - ret);
    const bDormant = bTotal * (1 - ret);
    aLik += (aTotal - aDormant) + aDormant * aMobRate;
    bLik += (bTotal - bDormant) + bDormant * bMobRate;
    aMob += aDormant * (1 - aMobRate);
    bMob += bDormant * (1 - bMobRate);
    aPer += g.contestedA * per;
    bPer += g.contestedB * per;
  }
  const total = aLik + bLik + aMob + bMob || 1;
  const likelyTotal = aLik + bLik || 1;
  return {
    aPct: (aLik + aMob) / total * 100,
    bPct: (bLik + bMob) / total * 100,
    aMobPct: aMob / total * 100,
    bMobPct: bMob / total * 100,
    aPerPct: aPer / total * 100,
    bPerPct: bPer / total * 100,
    aLikelyPct: aLik / likelyTotal * 100,
    bLikelyPct: bLik / likelyTotal * 100,
  };
}

/** Disjoint segment widths (they sum to 100 within the bar's scope): each side is mobilize + likely +
 * persuadable, with persuadable hugging the boundary. Shared by the bar and the table so they agree. */
export interface Carved { aMob: number; aLik: number; aPer: number; bPer: number; bLik: number; bMob: number; }
export function carve(f: Faceoff): Carved {
  const aPct = Math.max(0, Math.min(100, f.aPct));
  const bPct = Math.max(0, 100 - aPct);
  const aPer = Math.max(0, Math.min(f.aPerPct, aPct));
  const aMob = Math.max(0, Math.min(f.aMobPct, aPct - aPer));
  const aLik = Math.max(0, aPct - aPer - aMob);
  const bPer = Math.max(0, Math.min(f.bPerPct, bPct));
  const bMob = Math.max(0, Math.min(f.bMobPct, bPct - bPer));
  const bLik = Math.max(0, bPct - bPer - bMob);
  return { aMob, aLik, aPer, bPer, bLik, bMob };
}

export interface ClusterFaceoff extends Faceoff { party: string; weight: number; }

/** Per contributing cluster, its internal A/B split (0–100 within the cluster) + mobilize + persuade. */
export function perClusterFaceoff(
  groups: MicrotargetGroup[],
  cycle: ElectionCycle = 'midterm',
  aMobRate = 0,
  bMobRate = 0,
): ClusterFaceoff[] {
  return groups
    .filter(g => g.weight >= 0.005)
    .map(g => {
      const ret = retention(g.party, cycle), per = persuadability(g.party);
      const w = g.weight || 1;
      const aDorm = g.alignment * (1 - ret);
      const bDorm = (1 - g.alignment) * (1 - ret);
      const aAct = (g.alignment - aDorm) + aDorm * aMobRate;
      const bAct = ((1 - g.alignment) - bDorm) + bDorm * bMobRate;
      const total = aAct + bAct || 1;
      const likelyTotal = aAct + bAct || 1;
      return {
        party: g.party,
        weight: g.weight,
        aPct: aAct / total * 100,
        bPct: bAct / total * 100,
        aMobPct: aDorm * (1 - aMobRate) / total * 100,
        bMobPct: bDorm * (1 - bMobRate) / total * 100,
        aPerPct: Math.min(1, (g.contestedA / w) * per) * 100,
        bPerPct: Math.min(1, (g.contestedB / w) * per) * 100,
        aLikelyPct: aAct / likelyTotal * 100,
        bLikelyPct: bAct / likelyTotal * 100,
      };
    })
    .sort((a, b) => b.weight - a.weight);
}
