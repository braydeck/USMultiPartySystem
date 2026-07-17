import { useState, useMemo, useEffect } from 'react';
import type { ClusterProfile, FDCandidateProfile, ConstellationNode } from '../types';
import { useUrlState } from '../hooks/useUrlState';
import { centralityMark, type SignatureFilter } from '../lib/signature';
import { useSignatureFilter } from '../hooks/useSignatureFilter';
import { SignatureFilters } from '../components/shared/SignatureFilters';
import { PartySelector } from '../components/shared/PartySelector';
import { IdeologicalConstellation } from '../components/house/IdeologicalConstellation';
import { RangeBarCell, CompositionStackCell, HeatmapCell, FactorTags, type RangeMeta, type CompMeta } from '../components/shared/DistributionCells';
import { SignatureHeatmap, type HeatRow } from '../components/shared/SignatureHeatmap';
import { PartyRowLabel, SigTag, type RowMark } from '../components/shared/PartyRowLabel';
import distributionsData from '../data/distributions.json';
import { buildSubgroups, stripPrefix } from '../lib/subgroups';
import { IntensityBar, IntensityLegend, intensityFor, splitShares, itemSignature, BAM_LEFT, BAM_RIGHT, type IntensityItem } from '../components/shared/IntensityBar';
import { getBlendColor, getPrimaryParty, PARTY_NAMES, F5_ORDER_WFP as F5_ORDER, VAR_FACTOR, VAR_ALL_FACTORS, FACTOR_ITEMS, FACTOR_SHORT, FACTOR_LABELS, FACTOR_POLES, etaPurple } from '../constants/parties';
import { bamForZ, BAM_TEXT_LOW, BAM_TEXT_HIGH } from '../lib/bam';
import factorLoadingsData from '../data/factorLoadings.json';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface Props {
  clusters: ClusterProfile[];
  fdProfiles: Record<string, FDCandidateProfile>;
  clusterSpreads: { party: string; n: number; [key: string]: string | number }[];
}

const DOMAINS = [
  'Taxes & Economy',
  'Government Spending',
  'Immigration',
  'Police & Guns',
  'Abortion',
  'Environment & Climate',
  'Healthcare & Housing',
  'Civil Liberties',
  'Foreign Policy & Defense',
  'Elections & Trust',
  'Racial & Gender',
  'Religion',
  // Demographic sections
  'Household',
  'Race & Ethnicity',
  'Economics',
  'Gender & Sexuality',
  'Education',
  'Faith',
  'Voting History',
  'Other',
  'Demographics',  // catch-all for any legacy vars
];

// Top-level grouping above the domain sections. Policy = concrete positions; Attitudes =
// values/identity leanings; Demographics = who the party is. Demographics defaults collapsed.
const SUPER_GROUPS: { name: string; defaultOpen: boolean; domains: string[] }[] = [
  { name: 'Policy', defaultOpen: true, domains: [
    'Taxes & Economy', 'Government Spending', 'Immigration', 'Police & Guns', 'Abortion',
    'Environment & Climate', 'Healthcare & Housing', 'Civil Liberties', 'Foreign Policy & Defense'] },
  { name: 'Attitudes', defaultOpen: true, domains: ['Elections & Trust', 'Racial & Gender', 'Religion'] },
  { name: 'Demographics', defaultOpen: false, domains: [
    'Household', 'Race & Ethnicity', 'Economics', 'Gender & Sexuality', 'Education', 'Faith',
    'Voting History', 'Other', 'Demographics'] },
];

// Distribution items (range/composition/diverging) built by prepare_data.build_distributions.
type DistMeta = { viz: 'range' | 'composition' | 'diverging' | 'heatmap'; domain: string; question: string;
  order: number; unit?: string; segLabels?: string[]; colors?: string[]; pivot?: number; valueUnit?: string };
const DIST = distributionsData as unknown as {
  meta: Record<string, DistMeta>;
  national: Record<string, { pcts?: number[]; p10?: number } & Record<string, number | number[]>>;
  parties: Record<string, Record<string, { pcts?: number[]; p10?: number } & Record<string, number | number[]>>>;
};

// ---- Signature test for distribution charts (deviance + concentration-consensus) ----
type DistData = { pcts?: number[]; p10?: number; q25?: number; median?: number; q75?: number; p90?: number };

/** Where value x falls (0–100) within a national distribution given by 5 percentile anchors;
 *  linear interpolation between anchors, linear extrapolation past the ends, clamped. */
function nationalPercentileOf(x: number, n: DistData): number {
  const a: [number, number][] = [[n.p10!, 10], [n.q25!, 25], [n.median!, 50], [n.q75!, 75], [n.p90!, 90]];
  if (x <= a[0][0]) { const s = (a[1][1] - a[0][1]) / ((a[1][0] - a[0][0]) || 1); return Math.max(0, a[0][1] + (x - a[0][0]) * s); }
  for (let i = 0; i < a.length - 1; i++) {
    if (x <= a[i + 1][0]) { const t = (x - a[i][0]) / ((a[i + 1][0] - a[i][0]) || 1); return a[i][1] + t * (a[i + 1][1] - a[i][1]); }
  }
  const j = a.length - 2, s = (a[j + 1][1] - a[j][1]) / ((a[j + 1][0] - a[j][0]) || 1);
  return Math.min(100, a[j + 1][1] + (x - a[j + 1][0]) * s);
}

// Factor-loading badges (SO/GD/PC/RT/ES) for a distribution or intensity key. Distribution
// keys map to their underlying EFA variable first (only abortion weeks loads on a factor).
const DIST_EFA_KEY: Record<string, string> = { abortion_weeks: 'CC24_325_median' };
function factorShorts(key: string): string[] {
  const entry = VAR_ALL_FACTORS[key] ?? VAR_ALL_FACTORS[key + '_agree'];
  return entry ? entry.map(f => FACTOR_SHORT[f.factor]) : [];
}
const distFactors = (k: string): string[] => factorShorts(DIST_EFA_KEY[k] ?? k);

// Ordered distribution items (a latent scale binned into categories): distance uses an
// order-aware Earth Mover's metric, not the order-blind TVD used for the nominal ones.
const ORDERED_DIST = new Set(['income', 'educ', 'ideo5', 'pid3']);
const tvd = (p: number[], q: number[]) => 0.5 * p.reduce((s, v, i) => s + Math.abs(v - (q[i] ?? 0)), 0);
/** Normalized 1-D Earth Mover's Distance (0–100) over ordered bins: Σ|CDFp−CDFq| / (n−1). */
function emd(p: number[], q: number[]): number {
  const n = p.length; if (n <= 1) return 0;
  let cp = 0, cq = 0, acc = 0;
  for (let i = 0; i < n - 1; i++) { cp += p[i]; cq += (q[i] ?? 0); acc += Math.abs(cp - cq); }
  return acc / (n - 1);
}

/** A distribution item's signature components for one party: `cohesive` (concentration) and
 *  `distance` from national (0–100). Mirrors the scalar itemSignature so the dot + D/M marks
 *  mean the same thing across all chart types. */
function distSigParts(meta: DistMeta, party: DistData, national: DistData, f: SignatureFilter, ordered: boolean): { cohesive: boolean; distance: number } {
  if (meta.viz === 'range') {
    const distance = Math.abs(nationalPercentileOf(party.median!, national) - 50) * 2;
    const pIqr = party.q75! - party.q25!, nIqr = (national.q75! - national.q25!) || 1;
    return { cohesive: pIqr <= nIqr * (1 - (f.consPct - 50) / 100), distance };
  }
  const p = party.pcts ?? [], nat = national.pcts ?? [];
  const distance = ordered ? emd(p, nat) : tvd(p, nat);
  return { cohesive: (p.length ? Math.max(...p) : 0) >= f.consPct, distance };
}

const FACTORS = ['F1', 'F2', 'F3', 'F4', 'F5'] as const;
type FactorKey = typeof FACTORS[number];

// Discriminatory value (η²): how strongly each factor sorts voters into parties.
// Source: factorLoadings.json (same metric shown in the About → Methodology section).
const FACTOR_ETA: Record<string, number> = Object.fromEntries(
  (factorLoadingsData as { factor: string; eta: number }[]).map(f => [f.factor, f.eta])
);
// Factors shown, ordered by discriminatory value, strongest first (F5, F1, F2, F4).
// F3 (Government Distrust) is dropped: it is a non-interpretable residual whose party scores
// run opposite to real distrust — see docs/EFA_FACTORS.md.
const FACTORS_BY_DISCRIMINATION = ([...FACTORS] as FactorKey[])
  .filter(f => f !== 'F3')
  .sort((a, b) => (FACTOR_ETA[b] ?? 0) - (FACTOR_ETA[a] ?? 0));

interface VarEntry {
  key: string;
  question: string;
  pcts: Record<string, number>;
  overall: number | null;
  maxGap: number;
  highlighted: boolean;
  factor: string | null;
  factors: { factor: string; loading: number }[];
  maxVal: number;
  unit: string;
}

// Natural ordering for demographic/structural sections
const SECTION_QUESTION_ORDER: Record<string, string[]> = {
  Education: [
    'Less than high school', 'High school graduate', 'Some college (no degree)',
    "Associate's degree (2-year)", "Bachelor's degree (4-year)", 'Post-graduate degree',
  ],
  Economics: [
    'Family income under $50k', 'Family income $50k\u2013$100k', 'Family income over $100k',
    'Employed full-time', 'Employed part-time', 'Currently unemployed', 'Retired', 'Homemaker',
    'Gig / freelance worker', 'Owns stocks or mutual funds',
    'Current union member', 'Former union member', 'Household has union member',
  ],
  'Race & Ethnicity': [
    'White', 'Black', 'Hispanic', 'Asian', 'Multiracial',
    'Immigrant (naturalized citizen)', 'Immigrant (not yet a citizen)', 'US-born, parent was immigrant',
  ],
  'Gender & Sexuality': [
    'Identifies as man', 'Identifies as woman', 'Non-binary or other gender',
    'Heterosexual / straight', 'Lesbian', 'Gay man', 'Bisexual',
  ],
  Household: [
    'Married', 'Never married', 'Has children under 18',
    'Owns home', 'Rents home',
    'Lives in: city', 'Lives in: suburb', 'Lives in: town/small city', 'Lives in: rural area',
  ],
  'Voting History': [
    '2016: Hillary Clinton (D)', '2016: Donald Trump (R)', '2016: Third-party / other', '2016: Did not vote',
    '2020: Joe Biden (D)', '2020: Donald Trump (R)', '2020: Third-party / other', '2020: Did not vote',
    '2024: Kamala Harris (D)', '2024: Donald Trump (R)', '2024: Third-party / other', '2024: Did not vote',
    '2024: Approve of Joe Biden (job)', '2024: Approve of Kamala Harris (job)',
    '2024: Self-reported turnout', '2024: Voter-file-verified turnout',
  ],
  Abortion: [
    'Median abortion cutoff (weeks)',
    'Always allow abortion as a matter of personal choice',
    'Expand abortion access and affordability',
    'Permit abortion only in rape/incest/life danger cases',
    'Make abortion illegal in all circumstances',
    'Prohibit restrictions on abortion access (Congress bill)',
    'Protect access to contraception (Congress bill)',
    'Prohibit abortion-inducing drugs by mail',
    'Prohibit women traveling to another state for abortion',
  ],
  'Government Spending': [
    'Increase state spending on welfare',
    'Increase state spending on health care',
    'Increase state spending on education',
    'Increase state spending on law enforcement',
    'Increase state spending on transportation & infrastructure',
  ],
  'Foreign Policy & Defense': [
    'Ukraine: stay out of the conflict',
    'Ukraine: send humanitarian aid',
    'Ukraine: impose economic sanctions on Russia',
    'Ukraine: provide arms to Ukraine',
    'Ukraine: send non-combat military advisors',
    'Ukraine: send significant force to fight Russia',
    'Ukraine: negotiate a Russia–Ukraine peace accord',
    'Ukraine: fund post-war reconstruction',
    'Israel/Gaza: stay out of the conflict',
    'Israel/Gaza: send humanitarian aid',
    'Israel/Gaza: provide arms to Israel',
    'Israel/Gaza: provide arms to Hamas',
    'Israel/Gaza: send US Navy & troops to contain the conflict',
    'Israel/Gaza: send non-combat military support to Israel',
    'Israel/Gaza: send non-combat military support to Gaza',
    'Israel/Gaza: negotiate a peace settlement',
    'Israel/Gaza: fund post-war reconstruction',
    'Use US troops: to ensure the oil supply',
    'Use US troops: to destroy a terrorist camp',
    'Use US troops: to stop genocide or civil war',
    'Use US troops: to spread democracy',
    'Use US troops: to protect allies under attack',
    'Use US troops: to help the UN uphold international law',
    'Use US troops: for none of these reasons',
  ],
};

// Sub-header grouping for "Prefix: option" batteries — see lib/subgroups.

function getVariables(
  code: string,
  clusters: ClusterProfile[],
  fdProfiles: Record<string, FDCandidateProfile>,
): Record<string, { pct: number; question: string; domain: string }> {
  const cluster = clusters.find(c => c.party === code);
  if (cluster) return cluster.variables as Record<string, { pct: number; question: string; domain: string }>;
  const fdp = fdProfiles[code];
  if (fdp?.variables) return fdp.variables as Record<string, { pct: number; question: string; domain: string }>;
  return {};
}

function getFactorScores(
  code: string,
  clusters: ClusterProfile[],
  fdProfiles: Record<string, FDCandidateProfile>,
): Record<FactorKey, number> | null {
  const cluster = clusters.find(c => c.party === code);
  if (cluster) return { F1: cluster.F1, F2: cluster.F2, F3: cluster.F3, F4: cluster.F4, F5: cluster.F5 };
  const fdp = fdProfiles[code];
  if (fdp) return { F1: fdp.F1, F2: fdp.F2, F3: fdp.F3, F4: fdp.F4, F5: fdp.F5 };
  return null;
}

// Population SDs for raw→z conversion
const POP_SD: Record<string, number> = { F1: 0.787, F2: 0.818, F3: 0.630, F4: 0.486, F5: 0.879 };
function rawToZ(val: number, factor: string): number {
  return val / (POP_SD[factor] || 1);
}



// ── Diverging factor-score bars: stacked per party, centered at the U.S. mean, teal
// toward the low pole / magenta toward the high pole (bam) — the party-card FactorBar style.
function FactorBarRow({
  factor, codes, clusters, fdProfiles, scaleMode,
}: {
  factor: FactorKey;
  codes: string[];
  clusters: ClusterProfile[];
  fdProfiles: Record<string, FDCandidateProfile>;
  scaleMode: 'strength' | 'percentile';
}) {
  const zToPctile = (z: number) => (1 / (1 + Math.exp(-1.7 * z))) * 100;
  const scored = codes
    .map(code => {
      const raw = getFactorScores(code, clusters, fdProfiles)?.[factor];
      if (raw === undefined) return null;
      const z = rawToZ(raw, factor);
      const cl = clusters.find(c => c.party === code) ?? clusters.find(c => c.party === code.split('_')[0]);
      const pctile = (cl as unknown as Record<string, number>)?.[`pctile_${factor}`] ?? zToPctile(z);
      return { code, z, pctile };
    })
    .filter((s): s is { code: string; z: number; pctile: number } => s !== null)
    .sort((a, b) => a.z - b.z);
  const isPct = scaleMode === 'percentile';
  const poles = FACTOR_POLES[factor];
  return (
    <div className="px-4 py-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-sm font-semibold text-foreground">{FACTOR_LABELS[factor]}</span>
        <span className="text-[10px] text-muted-foreground font-mono bg-muted px-1 rounded">{FACTOR_SHORT[factor]}</span>
        {FACTOR_ETA[factor] !== undefined && (
          <span className="ml-auto flex items-center gap-1.5" title={`Discriminatory value: η² = ${FACTOR_ETA[factor].toFixed(3)} — how strongly this factor sorts voters into parties`}>
            <span className="text-[10px] text-muted-foreground font-mono">η² {FACTOR_ETA[factor].toFixed(2)}</span>
            <span className="block w-16 h-1.5 bg-muted rounded-full overflow-hidden">
              <span className="block h-full rounded-full" style={{ width: `${FACTOR_ETA[factor] * 100}%`, backgroundColor: etaPurple(FACTOR_ETA[factor]) }} />
            </span>
          </span>
        )}
      </div>
      <div className="space-y-1">
        {scored.map(({ code, z, pctile }) => {
          const isHigh = isPct ? pctile >= 50 : z >= 0;
          const w = isPct ? Math.abs(pctile - 50) : Math.min(Math.abs(z) / 2.5, 1) * 50;
          const color = bamForZ(z);
          const val = isPct ? `${Math.round(pctile)}%` : `${z >= 0 ? '+' : ''}${z.toFixed(1)}σ`;
          return (
            <div key={code} className="flex items-center gap-2 text-[10px] tabular-nums">
              <span className="w-11 shrink-0 font-bold text-right" style={{ color: getBlendColor(code) }}>{code}</span>
              <div className="flex-1 relative h-3 rounded-sm bg-muted overflow-hidden">
                <div className="absolute inset-y-0 rounded-sm" style={{ left: isHigh ? '50%' : `${50 - w}%`, width: `${w}%`, backgroundColor: color }} />
                <div className="absolute top-0 bottom-0 w-px bg-slate-400" style={{ left: '50%' }} />
              </div>
              <span className="w-12 shrink-0 text-right font-semibold" style={{ color: z >= 0 ? BAM_TEXT_HIGH : BAM_TEXT_LOW }}>{val}</span>
            </div>
          );
        })}
      </div>
      <div className="flex justify-between text-[9px] mt-1.5">
        <span style={{ color: '#2563eb' }}>← {poles?.low ?? ''}</span>
        <span className="text-muted-foreground">{isPct ? '50% = median' : '0 = U.S. mean'}</span>
        <span style={{ color: '#dc2626' }}>{poles?.high ?? ''} →</span>
      </div>
    </div>
  );
}

function FactorItemsPanel({
  factor, codes, clusters, fdProfiles, minGap, sigFilter, divergeOnly,
  filterCohesion, filterDeviant, filterMainstream,
}: {
  factor: string;
  codes: string[];
  clusters: ClusterProfile[];
  fdProfiles: Record<string, FDCandidateProfile>;
  minGap: number;
  sigFilter: SignatureFilter;
  divergeOnly: boolean;
  filterCohesion: boolean;
  filterDeviant: boolean;
  filterMainstream: boolean;
}) {
  const items = FACTOR_ITEMS[factor] ?? [];
  // Continuous EFA items that are now box-plot distributions (abortion weeks) pull from DIST.
  const RANGE_KEY: Record<string, string> = { CC24_325_median: 'abortion_weeks' };

  type Row = {
    key: string; loading: number; highlighted: boolean; marks: Record<string, RowMark>;
    kind: 'intensity' | 'range' | 'binary';
    iv?: IntensityItem; rangeKey?: string;
    question?: string; pcts?: Record<string, number>; overall?: number | null; maxVal?: number; unit?: string;
  };
  const rows: Row[] = [];

  for (const item of items) {
    const rangeKey = RANGE_KEY[item.key];
    if (rangeKey && DIST.national[rangeKey]) {
      const marks: Record<string, RowMark> = Object.fromEntries(
        codes.filter(c => DIST.parties[c]?.[rangeKey]).map(c => {
          const { cohesive, distance } = distSigParts(DIST.meta[rangeKey], DIST.parties[c][rangeKey] as never, DIST.national[rangeKey] as never, sigFilter, ORDERED_DIST.has(rangeKey));
          return [c, { dot: cohesive, mark: centralityMark(distance, sigFilter) }];
        }));
      rows.push({ key: item.key, loading: item.loading, highlighted: false, marks, kind: 'range', rangeKey });
      continue;
    }
    const pcts: Record<string, number> = {};
    let question = ''; let overall: number | null = null; let maxVal = 100; let unit = '%';
    for (const code of codes) {
      const v = getVariables(code, clusters, fdProfiles)[item.key];
      if (v) {
        pcts[code] = v.pct;
        if (!question) question = v.question;
        if (overall === null) overall = (v as any).overall ?? null;
        maxVal = (v as unknown as Record<string, number>)['maxVal'] ?? 100;
        unit = (v as unknown as Record<string, string>)['unit'] ?? '%';
      }
    }
    if (Object.keys(pcts).length === 0) continue;
    const pctVals = Object.values(pcts);
    const maxGap = pctVals.length > 1 ? Math.max(...pctVals) - Math.min(...pctVals) : 0;
    const marks: Record<string, RowMark> = Object.fromEntries(
      codes.filter(c => pcts[c] !== undefined).map(c => {
        const { cohesive, distance } = itemSignature(item.key, c, pcts[c], overall ?? pcts[c], maxVal, sigFilter);
        return [c, { dot: cohesive, mark: centralityMark(distance, sigFilter) }];
      }));
    const iv = intensityFor(item.key);
    rows.push({ key: item.key, loading: item.loading, highlighted: maxGap >= minGap, marks,
      kind: iv ? 'intensity' : 'binary', iv: iv ?? undefined, question, pcts, overall, maxVal, unit });
  }

  const shown = rows.filter(r => {
    const vals = Object.values(r.marks);
    if (divergeOnly && !r.highlighted) return false;
    if (filterCohesion && !vals.some(m => m.dot)) return false;
    if (filterDeviant && !vals.some(m => m.mark === 'D')) return false;
    if (filterMainstream && !vals.some(m => m.mark === 'M')) return false;
    return true;
  });

  if (shown.length === 0) {
    return (
      <div className="px-4 py-3 text-xs text-muted-foreground italic border-t border-border/30">
        No items match the current filter.
      </div>
    );
  }

  return (
    <div className="border-t border-border/30 bg-slate-50/50">
      <div className="px-4 py-2">
        <span className="text-[10px] text-muted-foreground uppercase tracking-widest">
          Underlying EFA items ({shown.length})
        </span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2">
        {shown.map((r, i) => (
          <div
            key={r.key}
            className={[
              i >= 2 ? 'border-t border-border/50' : '',
              i % 2 === 0 ? 'sm:border-r border-slate-300' : '',
            ].filter(Boolean).join(' ')}
          >
            {r.kind === 'intensity' ? (
              <IntensityCell item={r.iv!} codes={codes} question={r.iv!.question} marks={r.marks} loadingWeight={r.loading} diverges={r.highlighted} />
            ) : r.kind === 'range' ? (
              <RangeBarCell meta={DIST.meta[r.rangeKey!] as unknown as RangeMeta}
                national={DIST.national[r.rangeKey!] as never}
                byCode={Object.fromEntries(codes.filter(c => DIST.parties[c]?.[r.rangeKey!]).map(c => [c, DIST.parties[c][r.rangeKey!]])) as never}
                codes={codes} marks={r.marks} factors={distFactors(r.rangeKey!)} loadingWeight={r.loading} diverges={r.highlighted} />
            ) : (
              <StackedBarCell
                item={{
                  question: r.question!, factor: null, pcts: r.pcts!, overall: r.overall!,
                  maxVal: r.maxVal!, unit: r.unit!, highlighted: r.highlighted, loadingWeight: r.loading,
                }}
                codes={codes}
                marks={r.marks}
                label={r.question!}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// Structural shape the bar cell needs — satisfied by both the section VarEntry and the
// EFA-panel entries.
interface BarItem {
  question: string;
  factor?: string | null;
  factors?: { factor: string; loading: number }[];
  pcts: Record<string, number>;
  overall: number | null;
  maxVal: number;
  unit: string;
  highlighted: boolean;
  loadingWeight?: number;
}

// Single-value item: the national average + each selected party as a stacked horizontal
// bar on a shared 0–max axis. Replaces the dot-track — aligned bars, no occlusion, and it
// scales to any number of parties by stacking. Matches the IntensityCell row layout.
function StackedBarCell({ item, codes, marks, label }: { item: BarItem; codes: string[]; marks?: Record<string, RowMark>; label: string }) {
  const maxVal = item.maxVal || 100;
  const unit = item.unit || '%';
  const disp = (x: number) => (unit === '%' ? `${Math.round(x)}%` : `${x % 1 === 0 ? x : x.toFixed(1)} ${unit}`);
  const rows: string[] = ['__NAT__', ...codes];
  return (
    <div className="px-3 py-3">
      <div className="text-xs text-foreground leading-snug font-medium mb-2">
        {item.highlighted && <span className="text-amber-500 mr-1 align-middle" title="Selected parties diverge here">◆</span>}
        {item.loadingWeight !== undefined && (
          <span className="text-[9px] font-mono font-semibold text-indigo-600 mr-1.5 align-middle">
            {item.loadingWeight >= 0 ? '+' : ''}{item.loadingWeight.toFixed(2)}
          </span>
        )}
        {item.factors && item.factors.length > 0
          ? item.factors.map(f => (
              <span key={f.factor} className="inline-block text-[9px] font-bold px-1 py-0.5 rounded mr-1 bg-muted text-muted-foreground align-middle">{FACTOR_SHORT[f.factor]}</span>
            ))
          : item.factor
            ? <span className="inline-block text-[9px] font-bold px-1 py-0.5 rounded mr-1.5 bg-muted text-muted-foreground align-middle">{FACTOR_SHORT[item.factor]}</span>
            : null}
        {label}
      </div>
      <div className="space-y-1">
        {rows.map(code => {
          const isNat = code === '__NAT__';
          const val = isNat ? item.overall : item.pcts[code];
          if (val == null) return null;
          const color = isNat ? '#64748b' : getBlendColor(code);
          const pos = Math.min((val / maxVal) * 100, 100);
          return (
            <div key={code} className="flex items-center gap-2 text-[10px] tabular-nums">
              <PartyRowLabel code={code} signature={marks?.[code]?.dot} mark={marks?.[code]?.mark} />
              <div className="flex-1 relative h-3 rounded-sm bg-muted overflow-hidden">
                <div className="absolute inset-y-0 left-0 rounded-sm"
                  style={{ width: `${pos}%`, backgroundColor: isNat ? '#cbd5e1' : color }} />
              </div>
              <span className="w-11 shrink-0 text-right" style={{ color: isNat ? '#64748b' : 'inherit' }}>{disp(val)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Full-distribution cell for a multi-point item: national + each selected party as a
// stacked bar (diverging bipolar via bam), so Maintain/Neither and intensity are visible
// instead of the single collapsed dot.
function IntensityCell({ item, codes, question, marks, loadingWeight, diverges }:
  { item: IntensityItem; codes: string[]; question: string; marks?: Record<string, RowMark>; loadingWeight?: number; diverges?: boolean }) {
  return (
    <div className="px-3 py-3">
      <div className="text-xs text-foreground leading-snug font-medium mb-1">
        {diverges && <span className="text-amber-500 mr-1 align-middle" title="Selected parties diverge here">◆</span>}
        {loadingWeight !== undefined && (
          <span className="text-[9px] font-mono font-semibold text-indigo-600 mr-1.5 align-middle">
            {loadingWeight >= 0 ? '+' : ''}{loadingWeight.toFixed(2)}
          </span>
        )}
        <FactorTags shorts={factorShorts(item.variable)} />{question}
      </div>
      <IntensityLegend item={item} />
      {/* column header */}
      <div className="flex items-center gap-2 text-[9px] text-muted-foreground uppercase tracking-wide mt-1.5 mb-0.5">
        <span className="w-11 shrink-0" />
        <span className="w-24 shrink-0 text-center">neither</span>
        <span className="w-7 shrink-0" />
        <span className="flex-1 text-center">distribution</span>
        <span className="w-7 shrink-0" />
      </div>
      <div className="space-y-1">
        {(['__NAT__', ...codes]).map(code => {
          const shares = code === '__NAT__' ? item.national : item.parties[code];
          if (!shares) return null;
          const sp = splitShares(item, shares);
          return (
            <div key={code} className="flex items-center gap-2 text-[10px] tabular-nums">
              <PartyRowLabel code={code} signature={marks?.[code]?.dot} mark={marks?.[code]?.mark} />
              {sp && (sp.neutral != null ? (
                <div className="w-24 shrink-0 flex items-center gap-1">
                  <div className="relative h-3 flex-1 rounded-sm bg-muted overflow-hidden" title={`Neither ${Math.round(sp.neutral)}%`}>
                    <div className="absolute inset-y-0 left-0 bg-slate-400" style={{ width: `${sp.neutral}%` }} />
                  </div>
                  <span className="w-7 text-right text-foreground font-semibold">{Math.round(sp.neutral)}%</span>
                </div>
              ) : (
                <div className="w-24 shrink-0" />
              ))}
              {sp && <span className="w-7 shrink-0 text-right font-semibold" style={{ color: BAM_LEFT }}>{Math.round(sp.leftTotal)}%</span>}
              <div className="flex-1 min-w-0"><IntensityBar item={item} shares={shares} /></div>
              {sp && <span className="w-7 shrink-0 font-semibold" style={{ color: BAM_RIGHT }}>{Math.round(sp.rightTotal)}%</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function getSectionTitle(key: string): string {
  if (key === 'Untagged') return 'Other / Untagged';
  if ((FACTORS as readonly string[]).includes(key)) return `${FACTOR_LABELS[key]} (${FACTOR_SHORT[key]})`;
  return key;
}

const COMPARE_STORE_KEY = 'stv:compareFilters';
interface SavedCompare {
  cmp?: string;
  minGap?: number;
  divergeOnly?: boolean;
  factorScale?: 'strength' | 'percentile';
}
function loadSavedCompare(): SavedCompare {
  try { return JSON.parse(localStorage.getItem(COMPARE_STORE_KEY) || '{}'); } catch { return {}; }
}
function saveCompare(s: SavedCompare) {
  try { localStorage.setItem(COMPARE_STORE_KEY, JSON.stringify(s)); } catch { /* private mode / quota — ignore */ }
}

export function CompareTab({ clusters, fdProfiles, clusterSpreads }: Props) {
  // Selection lives in the URL (?cmp=STY,SD,DSA) so it is deep-linkable (e.g. from the quiz).
  // Selection + filters are also persisted to localStorage and restored on return, since
  // tab navigation clears the query string.
  const saved = useMemo(loadSavedCompare, []);
  const [cmp, setCmp] = useUrlState<string>('cmp', '', { push: false });
  const selected = useMemo(() => (cmp ? cmp.split(',').filter(Boolean) : []), [cmp]);
  // Party rows/columns always render in PC order (PRG→NAT), regardless of pick order.
  // FD variants sort by their base party. Selection-management still uses `selected`.
  const orderedSelected = useMemo(() =>
    [...selected].sort((a, b) =>
      (F5_ORDER as readonly string[]).indexOf(getPrimaryParty(a)) -
      (F5_ORDER as readonly string[]).indexOf(getPrimaryParty(b))),
    [selected]);
  const [minGap, setMinGap] = useState(saved.minGap ?? 15);
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set());
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(
    () => new Set(SUPER_GROUPS.filter(g => !g.defaultOpen).map(g => g.name)));
  const [expandedFactors, setExpandedFactors] = useState<Set<string>>(new Set());
  const [factorScale, setFactorScale] = useState<'strength' | 'percentile'>(saved.factorScale ?? 'strength');
  const [divergeOnly, setDivergeOnly] = useState(saved.divergeOnly ?? false);
  // Mobile: condense the sticky control bar once scrolled into the list; tap to expand.
  // Desktop keeps the full bar (there's room), so this only gates the small-screen layout.
  const [filtersExpanded, setFiltersExpanded] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => {
      const s = window.scrollY > 140;
      setScrolled(s);
      if (!s) setFiltersExpanded(false);   // back at top → always full, reset manual expand
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  const compact = scrolled && !filtersExpanded;   // collapse only on mobile (md: overrides below)
  // Signature filter shared with Party Platforms (URL params) so the two views agree.
  const sig = useSignatureFilter();
  const sigFilter = sig.filter;

  // Per-row signature annotations (left cohesion dot + right D/M mark), always computed from
  // the thresholds, for scalar items and distribution items alike.
  const scalarMarks = (v: VarEntry): Record<string, RowMark> => Object.fromEntries(
    selected.filter(c => v.pcts[c] !== undefined).map(c => {
      const { cohesive, distance } = itemSignature(v.key, c, v.pcts[c]!, v.overall ?? v.pcts[c]!, v.maxVal, sigFilter);
      return [c, { dot: cohesive, mark: centralityMark(distance, sigFilter) }];
    }));
  const distMarks = (k: string): Record<string, RowMark> => Object.fromEntries(
    selected.filter(c => DIST.parties[c]?.[k]).map(c => {
      const { cohesive, distance } = distSigParts(DIST.meta[k], DIST.parties[c][k] as never, DIST.national[k] as never, sigFilter, ORDERED_DIST.has(k));
      return [c, { dot: cohesive, mark: centralityMark(distance, sigFilter) }];
    }));
  // A row passes the (per-axis) filter checkboxes if, for each checked axis, some selected
  // party is marked on it. Divergence (amber) is handled separately via `highlighted`.
  const passSigFilters = (m: Record<string, RowMark>): boolean => {
    const vals = Object.values(m);
    if (sig.filterCohesion && !vals.some(x => x.dot)) return false;
    if (sig.filterDeviant && !vals.some(x => x.mark === 'D')) return false;
    if (sig.filterMainstream && !vals.some(x => x.mark === 'M')) return false;
    return true;
  };

  // Restore the last selection when arriving with an empty URL (e.g. via tab nav, which
  // clears query params). A deep-link / shared ?cmp=... takes precedence over the saved one.
  useEffect(() => {
    if (!cmp && saved.cmp) setCmp(saved.cmp);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Persist selection + filters for next time.
  useEffect(() => {
    saveCompare({ cmp, minGap, divergeOnly, factorScale });
  }, [cmp, minGap, divergeOnly, factorScale]);

  // Build option list: pure parties in F5_ORDER, then FD candidates grouped by party
  const pureOptions = F5_ORDER
    .filter(code => clusters.some(c => c.party === code))
    .map(code => ({ code, label: PARTY_NAMES[code] ?? code }));

  const fdOptions = Object.entries(fdProfiles)
    .sort((a, b) => {
      const ai = F5_ORDER.indexOf(a[1].party as typeof F5_ORDER[number]);
      const bi = F5_ORDER.indexOf(b[1].party as typeof F5_ORDER[number]);
      if (ai !== bi) return ai - bi;
      return a[0].localeCompare(b[0]);
    })
    .map(([code]) => ({ code, label: code }));

  const addParty = (code: string) => {
    if (selected.includes(code)) return;
    setCmp([...selected, code].join(','));
  };

  const removeParty = (code: string) => {
    setCmp(selected.filter(c => c !== code).join(','));
  };

  const toggleFactorExpand = (f: string) => {
    setExpandedFactors(prev => {
      const next = new Set(prev);
      if (next.has(f)) next.delete(f); else next.add(f);
      return next;
    });
  };

  const toggleSection = (key: string) => {
    setCollapsedSections(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  };

  const toggleGroup = (name: string) => {
    setCollapsedGroups(prev => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name); else next.add(name);
      return next;
    });
  };

  // Build vars grouped by category or factor
  const sectionVarMap = useMemo((): Record<string, VarEntry[]> => {
    if (selected.length < 1) return {};

    const varMap = new Map<string, {
      question: string; domain: string; pcts: Record<string, number>;
      overall: number | null; maxVal: number; unit: string;
    }>();
    for (const code of selected) {
      const vars = getVariables(code, clusters, fdProfiles);
      for (const [key, v] of Object.entries(vars)) {
        if (!varMap.has(key)) varMap.set(key, {
          question: v.question, domain: v.domain, pcts: {},
          overall: (v as any).overall ?? null,
          maxVal: (v as unknown as Record<string, number>)['maxVal'] ?? 100,
          unit: (v as unknown as Record<string, string>)['unit'] ?? '%',
        });
        varMap.get(key)!.pcts[code] = v.pct;
      }
    }

    const grouped: Record<string, VarEntry[]> = {};
    for (const [key, entry] of varMap) {
      const pcts = selected.map(c => entry.pcts[c]).filter((v): v is number => v !== undefined);
      if (pcts.length < 1) continue;
      const maxGap = Math.max(...pcts) - Math.min(...pcts);
      const factor = VAR_FACTOR[key] ?? null;
      const factors = VAR_ALL_FACTORS[key] ?? [];

      const groupKey = entry.domain;

      if (!grouped[groupKey]) grouped[groupKey] = [];
      grouped[groupKey].push({
        key, question: entry.question, pcts: entry.pcts, overall: entry.overall,
        maxGap, highlighted: maxGap >= minGap, factor, factors,
        maxVal: entry.maxVal, unit: entry.unit,
      });
    }

    // Rich distribution rows (ordinal/freq via IntensityBar) sort above plain binary bars, so
    // binaries sink to the bottom of each section for visual consistency.
    const rich = (k: string) => (intensityFor(k) ? 0 : 1);
    for (const key of Object.keys(grouped)) {
      const order = SECTION_QUESTION_ORDER[key];
      if (order) {
        grouped[key].sort((a, b) => {
          if (rich(a.key) !== rich(b.key)) return rich(a.key) - rich(b.key);
          const ai = order.indexOf(a.question);
          const bi = order.indexOf(b.question);
          if (ai !== -1 && bi !== -1) return ai - bi;
          if (ai !== -1) return -1;
          if (bi !== -1) return 1;
          return b.maxGap - a.maxGap;
        });
      } else {
        grouped[key].sort((a, b) => {
          if (rich(a.key) !== rich(b.key)) return rich(a.key) - rich(b.key);
          if (a.highlighted !== b.highlighted) return a.highlighted ? -1 : 1;
          return b.maxGap - a.maxGap;
        });
      }
    }

    return grouped;
  }, [selected, clusters, fdProfiles, minGap]);

  // Distribution items (range / composition) grouped by section domain, ordered within.
  const distBySection = useMemo(() => {
    const by: Record<string, string[]> = {};
    for (const [k, m] of Object.entries(DIST.meta)) {
      (by[m.domain] ||= []).push(k);
    }
    for (const d in by) by[d].sort((a, b) => DIST.meta[a].order - DIST.meta[b].order);
    return by;
  }, []);

  // Ordered section keys — a section appears if it has policy vars OR distribution items.
  const sectionKeys = useMemo(() => {
    return DOMAINS.filter(d => (sectionVarMap[d]?.length ?? 0) > 0 || (distBySection[d]?.length ?? 0) > 0);
  }, [sectionVarMap, distBySection]);

  // Constellation nodes — all parties, always shown as the overview map.
  const constellationNodes = useMemo((): ConstellationNode[] =>
    F5_ORDER.filter(code => clusters.some(c => c.party === code)).map(code => {
      const c = clusters.find(x => x.party === code) as unknown as Record<string, number> & { seatsHouse?: number };
      return {
        id: code, label: code, seats: c.seatsHouse ?? 0,
        F1: c.z_F1 ?? 0, F2: c.z_F2 ?? 0, F3: c.z_F3 ?? 0, F4: c.z_F4 ?? 0, F5: c.z_F5 ?? 0,
      };
    }), [clusters]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-1">Parties</h2>
        <p className="text-muted-foreground text-sm leading-relaxed">
          Select one party to see its platform, or several to compare. Single-number positions render as a
          heatmap shaded by support, with a US baseline column; richer items keep their distribution bars and
          box plots. Signature tags read the same everywhere: <SigTag kind="C" /> when a party holds a position
          cohesively, plus <SigTag kind="M" /> mainstream or <SigTag kind="D" /> deviant from the US average.
          A <span className="text-amber-500 font-bold">◆</span> marks rows where the selected parties diverge (≥{minGap}pp apart).
        </p>
      </div>

      {/* Ideological constellation — overview map, placed above the filters so it doesn't
          interrupt the flow between the filter controls and the list they act on. */}
      <Card className="p-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">Ideological Constellation</h3>
        <p className="text-[11px] text-muted-foreground mb-3 leading-relaxed">
          Each party is an ellipse spanning its members' range on the two strongest factors. Where ellipses{' '}
          <span className="font-medium text-foreground">overlap</span>, voters sit in shared factor space, cross-pressured between those parties.
        </p>
        <IdeologicalConstellation nodes={constellationNodes} clusterSpreads={clusterSpreads} />
      </Card>

      {/* Party selector + signature filter — sticky so both can be adjusted while scrolling
          the (long, annotated) list. On mobile it condenses to a summary strip once scrolled;
          tap to expand. Desktop (md+) always shows the full bar. */}
      <div className="sticky top-[40px] z-20 bg-white/95 backdrop-blur-sm border-b border-border/50 -mx-4 px-4 py-2">
        {/* Condensed summary — mobile only, when scrolled */}
        {compact && (
          <button
            type="button"
            onClick={() => setFiltersExpanded(true)}
            className="flex md:hidden w-full items-center justify-between gap-2 text-xs py-0.5"
          >
            <span className="flex items-center gap-1.5 min-w-0">
              <span className="font-semibold text-foreground shrink-0">
                {selected.length ? `${selected.length} ${selected.length === 1 ? 'party' : 'parties'}` : 'Select parties'}
              </span>
              <span className="flex items-center gap-0.5 overflow-hidden">
                {orderedSelected.slice(0, 10).map(c => (
                  <span key={c} className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: getBlendColor(c) }} />
                ))}
              </span>
            </span>
            <span className="shrink-0 font-medium text-indigo-600">Parties &amp; filters ▾</span>
          </button>
        )}

        {/* Full controls — always on desktop; on mobile only when not condensed */}
        <div className={`space-y-2 ${compact ? 'hidden md:block' : ''}`}>
          {scrolled && filtersExpanded && (
            <div className="flex md:hidden justify-end -mb-1">
              <button type="button" onClick={() => setFiltersExpanded(false)}
                className="text-xs font-medium text-indigo-600">▴ collapse</button>
            </div>
          )}
          <PartySelector
            selected={selected}
            onToggle={code => (selected.includes(code) ? removeParty(code) : addParty(code))}
            baseParties={pureOptions.map(o => o.code)}
            crossover={fdOptions.filter(o => !pureOptions.some(p => p.code === o.code)).map(o => ({ code: o.code, label: o.code }))}
          />
          {selected.length >= 1 && (
            <div className="pt-1.5 border-t border-border/40 flex flex-wrap items-center gap-x-5 gap-y-1.5">
              <SignatureFilters s={sig} accent="#6366f1" />
              <div className="flex items-center gap-1.5 text-[11px] shrink-0 border-l border-border/50 pl-4">
                <span className="font-semibold text-foreground whitespace-nowrap"><span className="text-amber-500">◆</span> Divergence</span>
                <input type="range" min={0} max={50} step={5} value={minGap}
                  onChange={e => setMinGap(Number(e.target.value))} className="w-16" style={{ accentColor: '#6366f1' }} />
                <span className="font-mono font-semibold tabular-nums w-9" style={{ color: '#6366f1' }}>≥{minGap}</span>
                <label className="flex items-center gap-0.5 cursor-pointer text-muted-foreground" title="Filter to diverging rows">
                  <input type="checkbox" checked={divergeOnly} onChange={e => setDivergeOnly(e.target.checked)}
                    style={{ accentColor: '#6366f1' }} />
                  filter
                </label>
              </div>
            </div>
          )}
        </div>
      </div>
      {selected.length === 0 && (
        <p className="text-xs text-muted-foreground">
          Select a party for its platform, or several to compare. Try: PRG + NAT (maximum divergence) ·
          LBR + CON (presidential rivals) · LBR_hi_so + LBR (crossover vs base).
        </p>
      )}


      {selected.length >= 1 && (
        <>
          {/* Factor scores */}
          <Card className="overflow-hidden">
            <div className="px-4 py-3 border-b border-border/50 bg-muted flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">Factor Scores</span>
                <span className="text-xs text-muted-foreground ml-3">
                  {factorScale === 'strength' ? 'Strongly >1.5σ · Moderately 1.0σ · Leans 0.5σ · Mixed <0.5σ' : '0% = lowest · 50% = median · 100% = highest'}
                </span>
                <span className="text-[10px] text-muted-foreground ml-3">ordered by discriminatory value (η²)</span>
              </div>
              <div className="flex gap-1">
                <Button onClick={() => setFactorScale('strength')}
                  variant={factorScale === 'strength' ? 'default' : 'secondary'}
                  size="sm">
                  Strength
                </Button>
                <Button onClick={() => setFactorScale('percentile')}
                  variant={factorScale === 'percentile' ? 'default' : 'secondary'}
                  size="sm">
                  Percentile
                </Button>
              </div>
            </div>
            <div className="divide-y divide-border/50">
              {FACTORS_BY_DISCRIMINATION.map(f => {
                const isExpanded = expandedFactors.has(f);
                return (
                  <div key={f}>
                    <div
                      className="cursor-pointer hover:bg-muted/30 transition-colors"
                      onClick={() => toggleFactorExpand(f)}
                      role="button"
                      aria-expanded={isExpanded}
                    >
                      <FactorBarRow factor={f} codes={orderedSelected} clusters={clusters} fdProfiles={fdProfiles} scaleMode={factorScale} />
                      <div className="flex items-center justify-center pb-2 gap-1">
                        <span className="text-muted-foreground text-[10px]">{isExpanded ? '▲' : '▼'}</span>
                        <span className="text-[10px] text-muted-foreground">
                          {isExpanded ? 'collapse items' : `expand items (${(FACTOR_ITEMS[f] ?? []).length})`}
                        </span>
                      </div>
                    </div>
                    {isExpanded && (
                      <FactorItemsPanel
                        factor={f}
                        codes={orderedSelected}
                        clusters={clusters}
                        fdProfiles={fdProfiles}
                        minGap={minGap}
                        sigFilter={sigFilter}
                        divergeOnly={divergeOnly}
                        filterCohesion={sig.filterCohesion}
                        filterDeviant={sig.filterDeviant}
                        filterMainstream={sig.filterMainstream}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </Card>


          {/* Sections */}
          {sectionKeys.length === 0 ? (
            <Card className="p-8 text-center text-muted-foreground text-sm">
              No variables match the selected filter.
            </Card>
          ) : (
            <div className="space-y-5">
              {SUPER_GROUPS.map(group => {
                const groupSections = sectionKeys.filter(k => group.domains.includes(k));
                if (groupSections.length === 0) return null;
                const gCollapsed = collapsedGroups.has(group.name);
                return (
                  <div key={group.name}>
                    <button onClick={() => toggleGroup(group.name)}
                      className="w-full flex items-center gap-2 mb-2 text-left">
                      <h3 className="text-lg font-bold text-foreground">{group.name}</h3>
                      <span className="text-xs bg-muted text-muted-foreground rounded-full px-2 py-0.5">{groupSections.length}</span>
                      <span className="text-muted-foreground text-xs ml-auto">{gCollapsed ? '▶ show' : '▼ hide'}</span>
                    </button>
                    {!gCollapsed && (
                      <div className="space-y-3">
              {groupSections.map(sectionKey => {
                const allVars = sectionVarMap[sectionKey] ?? [];
                // Annotation model: every item is shown and marked (cohesion dot + D/M); the
                // per-axis filter checkboxes optionally trim to rows matching the checked axes.
                const vars = allVars.filter(v => (!divergeOnly || v.highlighted)
                  && passSigFilters(scalarMarks(v)));
                const distKeys = (distBySection[sectionKey] ?? []).filter(k =>
                  selected.some(c => DIST.parties[c]?.[k]) && passSigFilters(distMarks(k)));
                if (vars.length === 0 && distKeys.length === 0) return null;
                const collapsed = collapsedSections.has(sectionKey);
                // Count only diverging rows that survive the active filters (not the hidden ones).
                const highlightCount = vars.filter(v => v.highlighted).length;

                return (
                  <Card key={sectionKey} className="overflow-hidden">
                    <button
                      className="w-full flex items-center justify-between px-4 py-3 hover:bg-muted transition-colors text-left"
                      onClick={() => toggleSection(sectionKey)}
                      aria-expanded={!collapsed}
                    >
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-semibold text-foreground">{getSectionTitle(sectionKey)}</span>
                        <span className="text-xs bg-muted text-muted-foreground rounded-full px-2 py-0.5">{vars.length + distKeys.length}</span>
                        {highlightCount > 0 && (
                          <span className="text-xs bg-amber-100 text-amber-700 font-medium rounded-full px-2 py-0.5">
                            {highlightCount} diverge
                          </span>
                        )}
                      </div>
                      <span className="text-muted-foreground text-xs flex-shrink-0 ml-2">{collapsed ? '▶' : '▼'}</span>
                    </button>

                    {!collapsed && (
                      <div className="border-t border-border/50">
                        {(() => {
                          const byCodeFor = (k: string) => Object.fromEntries(
                            selected.filter(c => DIST.parties[c]?.[k]).map(c => [c, DIST.parties[c][k]])) as Record<string, never>;
                          // All distribution items go two-per-row for density and legibility —
                          // heatmaps included (they read better compact than sprawled full width).
                          return (
                            <div className="grid grid-cols-1 sm:grid-cols-2">
                              {distKeys.map((k, i) => {
                                const m = DIST.meta[k];
                                const marks = distMarks(k);
                                return (
                                  <div key={k} className={[
                                    i >= 2 ? 'border-t border-border/50' : '',
                                    i % 2 === 0 ? 'sm:border-r border-slate-300' : '',
                                  ].filter(Boolean).join(' ')}>
                                    {m.viz === 'range'
                                      ? <RangeBarCell meta={m as unknown as RangeMeta}
                                          national={DIST.national[k] as never} byCode={byCodeFor(k)} codes={orderedSelected} marks={marks} factors={distFactors(k)} />
                                      : m.viz === 'heatmap'
                                      ? <HeatmapCell meta={m as unknown as CompMeta}
                                          national={DIST.national[k] as never} byCode={byCodeFor(k)} codes={orderedSelected} marks={marks} factors={distFactors(k)} />
                                      : <CompositionStackCell meta={m as unknown as CompMeta}
                                          national={DIST.national[k] as never} byCode={byCodeFor(k)} codes={orderedSelected} marks={marks} factors={distFactors(k)} />}
                                  </div>
                                );
                              })}
                            </div>
                          );
                        })()}
                        {buildSubgroups(sectionKey, vars).map(grp => (
                          <div key={grp.header ?? 'main'}>
                            {grp.header && (
                              <div className="px-4 pt-3 pb-1.5 bg-slate-50 border-t border-border/50">
                                <div className="text-xs font-semibold text-foreground">{grp.label}</div>
                                {grp.multi && (
                                  <div className="text-[11px] text-muted-foreground">Select all that apply: share of each party choosing this option (can exceed 100%)</div>
                                )}
                              </div>
                            )}
                            {(() => {
                              const gl = grp.items.map(v => intensityFor(v.key)).find(Boolean);
                              return gl ? <div className="px-4 pt-2 pb-0.5 border-t border-border/40"><IntensityLegend item={gl} /></div> : null;
                            })()}
                            {(() => {
                              // Single-number items → one heatmap block; multi-point (intensity) items keep their bars.
                              const heatItems = grp.items.filter(v => !intensityFor(v.key));
                              const intensityItems = grp.items.filter(v => intensityFor(v.key));
                              const heatRows: HeatRow[] = heatItems.map(v => ({
                                key: v.key,
                                question: grp.header ? stripPrefix(v.question) : v.question,
                                pcts: v.pcts, overall: v.overall, maxVal: v.maxVal, unit: v.unit,
                                marks: scalarMarks(v), highlighted: v.highlighted, factorShorts: factorShorts(v.key),
                              }));
                              return (
                                <>
                                  {heatRows.length > 0 && <SignatureHeatmap rows={heatRows} selected={orderedSelected} />}
                                  {intensityItems.length > 0 && (
                                    <div className="grid grid-cols-1 sm:grid-cols-2 border-t border-border/40">
                                      {intensityItems.map((v, i) => (
                                        <div key={v.key} className={[
                                          i >= 2 ? 'border-t border-border/50' : '',
                                          i % 2 === 0 ? 'sm:border-r border-slate-300' : '',
                                        ].filter(Boolean).join(' ')}>
                                          <IntensityCell item={intensityFor(v.key)!} codes={orderedSelected}
                                            question={intensityFor(v.key)!.question} marks={scalarMarks(v)} diverges={v.highlighted} />
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </>
                              );
                            })()}
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>
                );
              })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {selected.length === 0 && (
        <Card className="p-12 text-center">
          <div className="text-muted-foreground text-sm">Select a party above to explore their positions</div>
          <div className="text-slate-300 text-xs mt-2">
            Add a second party to compare. A ◆ marks rows where they diverge by ≥{minGap}pp.
          </div>
        </Card>
      )}
    </div>
  );
}
