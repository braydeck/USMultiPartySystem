// Shared faceoff math for the Single Race view: turns per-cluster microtarget inputs into the
// A-vs-B bar segments (likely vs mobilize) and the persuadable middle. Used by the headline bar
// and the per-cluster breakdown alike.
import partyPopulation from '../../data/partyPopulation.json';
import clusterProfiles from '../../data/clusterProfiles.json';
import type { MicrotargetGroup } from '../../lib/singleRace';

// ── Midterm dropoff (surge & decline) — LITERATURE PLACEHOLDER ──────────────────────────────
// Peripheral (low-propensity) voters fall away in midterms; core voters persist. Retention scales
// with presidential turnout, ~0.90 (core) to ~0.50 (peripheral), weighted mean ~0.70 (Catalist
// magnitudes; A. Campbell / J.E. Campbell surge-and-decline).
// TODO: replace with EMPIRICAL per-cluster retention from 2020/2022 (+2016/2018) CES waves.
const RET_LO = 0.50, RET_HI = 0.90;
// Civic-engagement composite (Parties-tab items) → persuadability (its inverse): low-engagement
// voters are more movable but heuristic-driven (Zaller / Popkin).
const CIVIC = ['newsint', 'CC24_430a_1', 'CC24_430a_2', 'CC24_430a_3', 'CC24_430a_4', 'CC24_430a_5', 'CC24_430a_6'];

type PopRow = { party: string; turnout: number };
type Profile = { party: string; variables: Record<string, { pct?: number }> };

const turnoutByParty: Record<string, number> = {};
for (const r of partyPopulation as PopRow[]) turnoutByParty[r.party] = r.turnout;
const tv = Object.values(turnoutByParty);
const tMin = Math.min(...tv), tMax = Math.max(...tv);
const retentionByParty: Record<string, number> = {};
for (const [p, t] of Object.entries(turnoutByParty)) retentionByParty[p] = RET_LO + (RET_HI - RET_LO) * (t - tMin) / ((tMax - tMin) || 1);

const engByParty: Record<string, number> = {};
for (const c of clusterProfiles as Profile[]) {
  const vals = CIVIC.map(k => c.variables[k]?.pct).filter((x): x is number => x != null);
  engByParty[c.party] = vals.reduce((s, x) => s + x, 0) / (vals.length || 1);
}
const ev = Object.values(engByParty);
const eMin = Math.min(...ev), eMax = Math.max(...ev);
const persuadByParty: Record<string, number> = {};
for (const [p, e] of Object.entries(engByParty)) persuadByParty[p] = 1 - (e - eMin) / ((eMax - eMin) || 1);

export const retention = (p: string) => retentionByParty[p] ?? 0.70;
export const persuadability = (p: string) => persuadByParty[p] ?? 0.5;

/**
 * All widths are percentages within the bar's scope (electorate or one cluster). Each side splits
 * into mobilize (dormant pole) + likely (solid) + persuadable (soft, near the boundary). Persuadable
 * is A-side vs B-side — different voters — so the bar and table can mark them apart.
 */
export interface Faceoff {
  aPct: number; bPct: number;         // total support for A / B
  aMobPct: number; bMobPct: number;   // "mobilize": aligned voters who skip midterms
  aPerPct: number; bPerPct: number;   // "persuadable": near-boundary voters currently leaning A / B
}

/** Whole-electorate faceoff from the per-cluster microtarget groups. */
export function aggregateFaceoff(groups: MicrotargetGroup[]): Faceoff {
  let aSup = 0, bSup = 0, aMob = 0, bMob = 0, aPer = 0, bPer = 0;
  for (const g of groups) {
    const ret = retention(g.party), per = persuadability(g.party);
    aSup += g.weight * g.alignment;
    bSup += g.weight * (1 - g.alignment);
    aMob += g.weight * g.alignment * (1 - ret);
    bMob += g.weight * (1 - g.alignment) * (1 - ret);
    aPer += g.contestedA * per;
    bPer += g.contestedB * per;
  }
  const t = aSup + bSup || 1;
  return {
    aPct: aSup / t * 100, bPct: bSup / t * 100,
    aMobPct: aMob / t * 100, bMobPct: bMob / t * 100,
    aPerPct: aPer / t * 100, bPerPct: bPer / t * 100,
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
export function perClusterFaceoff(groups: MicrotargetGroup[]): ClusterFaceoff[] {
  return groups
    .filter(g => g.weight >= 0.005)
    .map(g => {
      const ret = retention(g.party), per = persuadability(g.party);
      const w = g.weight || 1;
      return {
        party: g.party,
        weight: g.weight,
        aPct: g.alignment * 100,
        bPct: (1 - g.alignment) * 100,
        aMobPct: g.alignment * (1 - ret) * 100,
        bMobPct: (1 - g.alignment) * (1 - ret) * 100,
        aPerPct: Math.min(1, (g.contestedA / w) * per) * 100,
        bPerPct: Math.min(1, (g.contestedB / w) * per) * 100,
      };
    })
    .sort((a, b) => b.weight - a.weight);
}
