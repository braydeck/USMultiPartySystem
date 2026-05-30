import { useState, useMemo } from 'react';
import type { ClusterProfile, FDCandidateProfile } from '../types';
import { getBlendColor, PARTY_NAMES, F5_ORDER, VAR_FACTOR, FACTOR_SHORT, FACTOR_LABELS, FACTOR_POLES } from '../constants/parties';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface Props {
  clusters: ClusterProfile[];
  fdProfiles: Record<string, FDCandidateProfile>;
}

const DOMAINS = [
  'Taxes & Economy',
  'Immigration',
  'Police & Guns',
  'Abortion',
  'Environment & Climate',
  'Healthcare & Housing',
  'Civil Liberties',
  'Elections & Trust',
  'Racial & Gender',
  'Religion',
  // Demographic sections
  'Household',
  'Race & Ethnicity',
  'Economics',
  'Gender & Sexuality',
  'Education',
  'Voting History',
  'Other',
  'Demographics',  // catch-all for any legacy vars
];

const FACTORS = ['F1', 'F2', 'F3', 'F4', 'F5'] as const;
type FactorKey = typeof FACTORS[number];

interface VarEntry {
  key: string;
  question: string;
  pcts: Record<string, number>;
  overall: number | null;
  maxGap: number;
  highlighted: boolean;
  factor: string | null;
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
    'Voted Biden (2020)', 'Voted Trump (2020)', 'Did not vote (2020)', 'Did not vote (2016)',
  ],
  Abortion: [
    'Median abortion cutoff (weeks)',
    'Permit abortion only in rape/incest/life danger cases',
    'Prohibit restrictions on abortion access (Congress bill)',
    'Prohibit abortion-inducing drugs by mail',
    'Prohibit women traveling to another state for abortion',
  ],
};

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

// ── Dot-on-track row for policy variables ─────────────────────────────────
// maxVal: axis maximum (100 for %, 40 for weeks, etc.)
// unit: display suffix ('' for pure %, 'wks', etc.)

const POLICY_LINE_Y = 32;
const POLICY_H      = 72;
const DOT_R         = 5.5;
const ABOVE_Y       = POLICY_LINE_Y - DOT_R - 5;   // label baseline above dot
const BELOW_Y       = POLICY_LINE_Y + DOT_R + 13;  // label baseline below dot

function DotTrack({
  question, factor, highlighted, pcts, codes, gap, maxVal = 100, unit = '%', overall, showNatAvg,
}: {
  question: string;
  factor: string | null;
  highlighted: boolean;
  pcts: Record<string, number>;
  codes: string[];
  gap: number;
  maxVal?: number;
  unit?: string;
  overall?: number | null;
  showNatAvg?: boolean;
}) {
  const toPos  = (v: number) => (v / maxVal) * 100;  // value → 0-100% position
  const toDisp = (v: number) => unit === '%' ? `${Math.round(v)}%` : `${v % 1 === 0 ? v : v.toFixed(1)} ${unit}`;

  const present = [...codes]
    .filter(c => pcts[c] !== undefined)
    .sort((a, b) => pcts[a]! - pcts[b]!);

  const lo = present.length > 0 ? toPos(pcts[present[0]]!) : 0;
  const hi = present.length > 0 ? toPos(pcts[present[present.length - 1]]!) : 0;

  // Axis labels depend on scale
  const midVal = maxVal / 2;
  const axisL  = unit === '%' ? '0%' : `0 ${unit}`;
  const axisMid = unit === '%' ? '50%' : `${midVal % 1 === 0 ? midVal : midVal.toFixed(0)} ${unit}`;
  const axisR  = unit === '%' ? '100%' : `${maxVal} ${unit}`;

  return (
    <div className={`px-3 py-3 ${highlighted ? 'bg-amber-50' : 'hover:bg-muted/50'}`}>
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="text-xs text-foreground leading-snug flex-1 min-w-0 font-medium">
          {factor && (
            <span className="inline-block text-[9px] font-bold px-1 py-0.5 rounded mr-1.5 bg-muted text-muted-foreground align-middle">
              {FACTOR_SHORT[factor]}
            </span>
          )}
          {question}
        </div>
        {gap > 0 && (
          <span className={`text-[11px] font-mono shrink-0 mt-0.5 font-semibold ${highlighted ? 'text-amber-600' : 'text-muted-foreground'}`}>
            {gap.toFixed(0)}{unit === '%' ? 'pp' : ` ${unit}`}
          </span>
        )}
      </div>
      <svg width="100%" height={POLICY_H} style={{ overflow: 'visible' }}>
        {/* 50% reference line */}
        <line x1="50%" y1={3} x2="50%" y2={POLICY_LINE_Y + 5}
          stroke="#94a3b8" strokeWidth={1} strokeDasharray="3,2" />
        {/* National average marker */}
        {showNatAvg && overall != null && (
          <>
            <line x1={`${toPos(overall)}%`} y1={POLICY_LINE_Y - 12}
              x2={`${toPos(overall)}%`} y2={POLICY_LINE_Y + 12}
              stroke="#059669" strokeWidth={2.5} />
            <text x={`${toPos(overall)}%`} y={8}
              textAnchor="middle" fontSize={8} fill="#059669" fontWeight="600">
              All Americans: {toDisp(overall)}
            </text>
          </>
        )}
        {/* Base track */}
        <line x1="1%" y1={POLICY_LINE_Y} x2="99%" y2={POLICY_LINE_Y}
          stroke="#e2e8f0" strokeWidth={1.5} />
        {/* Range span */}
        {present.length > 1 && (
          <line
            x1={`${lo}%`} y1={POLICY_LINE_Y}
            x2={`${hi}%`} y2={POLICY_LINE_Y}
            stroke={highlighted ? '#fbbf24' : '#cbd5e1'}
            strokeWidth={3} strokeLinecap="round"
          />
        )}
        {/* Dots + combined inline labels */}
        {present.map((code, idx) => {
          const raw  = pcts[code]!;
          const pos  = toPos(raw);
          const color = getBlendColor(code);
          const above = idx % 2 === 0;
          const labelY = above ? ABOVE_Y : BELOW_Y;
          const anchor = pos < 12 ? 'start' : pos > 88 ? 'end' : 'middle';
          return (
            <g key={code}>
              <circle cx={`${pos}%`} cy={POLICY_LINE_Y} r={DOT_R}
                fill={color} stroke="white" strokeWidth={2} />
              <text x={`${pos}%`} y={labelY} textAnchor={anchor} dominantBaseline="auto">
                <tspan fontWeight="700" fontSize={11} fill={color}>{code}</tspan>
                <tspan fontSize={10} fill="#475569"> {toDisp(raw)}</tspan>
              </text>
            </g>
          );
        })}
        {/* Axis */}
        <text x="1%"  y={POLICY_H - 3} fontSize={8} fill="#94a3b8" textAnchor="start">{axisL}</text>
        <text x="50%" y={POLICY_H - 3} fontSize={8} fill="#94a3b8" textAnchor="middle">{axisMid}</text>
        <text x="99%" y={POLICY_H - 3} fontSize={8} fill="#94a3b8" textAnchor="end">{axisR}</text>
      </svg>
    </div>
  );
}

// ── Dot-on-track row for factor scores (−2 to +2 scale) ───────────────────

const FACTOR_LINE_Y = 33;
const FACTOR_H      = 82;
const FACTOR_DOT_R  = 6;
const FACTOR_MIN    = -2.5;  // z-score range
const FACTOR_MAX    =  2.5;
const fvToPct = (v: number) => ((v - FACTOR_MIN) / (FACTOR_MAX - FACTOR_MIN)) * 100;
const TIER_BOUNDS   = [-2.0, -1.5, -1.0, -0.5, 0, 0.5, 1.0, 1.5, 2.0];

function FactorDotRow({
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
      // Also check for precomputed percentile
      const cl = clusters.find(c => c.party === code) ?? clusters.find(c => c.party === code.split('_')[0]);
      const pctile = (cl as any)?.[`pctile_${factor}`] ?? zToPctile(z);
      return { code, z, pctile };
    })
    .filter((s): s is { code: string; z: number; pctile: number } => s !== null)
    .sort((a, b) => a.z - b.z);

  const isPercentile = scaleMode === 'percentile';
  const toPos = isPercentile
    ? (item: { z: number; pctile: number }) => item.pctile
    : (item: { z: number; pctile: number }) => fvToPct(item.z);
  const fmtVal = isPercentile
    ? (item: { z: number; pctile: number }) => `${Math.round(item.pctile)}%`
    : (item: { z: number; pctile: number }) => `${item.z >= 0 ? '+' : ''}${item.z.toFixed(1)}σ`;

  return (
    <div className="px-4 py-3 border-t border-slate-50 first:border-t-0">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-sm font-semibold text-foreground">{FACTOR_LABELS[factor]}</span>
        <span className="text-[10px] text-muted-foreground font-mono bg-muted px-1 rounded">{FACTOR_SHORT[factor]}</span>
      </div>
      <svg width="100%" height={FACTOR_H} style={{ overflow: 'visible' }}>
        {/* Tier boundary ticks */}
        {!isPercentile && TIER_BOUNDS.map(v => (
          <line key={v}
            x1={`${fvToPct(v)}%`} y1={FACTOR_LINE_Y - 8}
            x2={`${fvToPct(v)}%`} y2={FACTOR_LINE_Y + 8}
            stroke={v === 0 ? '#94a3b8' : '#cbd5e1'}
            strokeWidth={v === 0 ? 1.5 : 1} />
        ))}
        {isPercentile && (
          <line x1="50%" y1={FACTOR_LINE_Y - 8} x2="50%" y2={FACTOR_LINE_Y + 8}
            stroke="#94a3b8" strokeWidth={1.5} />
        )}
        {/* Base line */}
        <line x1="1%" y1={FACTOR_LINE_Y} x2="99%" y2={FACTOR_LINE_Y}
          stroke="#e2e8f0" strokeWidth={1.5} />
        {/* Tier labels */}
        {!isPercentile ? (
          <>
            {/* Zone background shading — intensity increases outward */}
            {/* Centrist */}
            <rect x={`${fvToPct(-0.5)}%`} y={FACTOR_LINE_Y - 10} width={`${fvToPct(0.5) - fvToPct(-0.5)}%`} height={20} fill="#f1f5f9" rx={3} />
            {/* Leans */}
            <rect x={`${fvToPct(0.5)}%`} y={FACTOR_LINE_Y - 10} width={`${fvToPct(1.0) - fvToPct(0.5)}%`} height={20} fill="#fecaca" opacity={0.25} rx={2} />
            <rect x={`${fvToPct(-1.0)}%`} y={FACTOR_LINE_Y - 10} width={`${fvToPct(-0.5) - fvToPct(-1.0)}%`} height={20} fill="#bfdbfe" opacity={0.25} rx={2} />
            {/* Moderately */}
            <rect x={`${fvToPct(1.0)}%`} y={FACTOR_LINE_Y - 10} width={`${fvToPct(1.5) - fvToPct(1.0)}%`} height={20} fill="#fca5a5" opacity={0.35} rx={2} />
            <rect x={`${fvToPct(-1.5)}%`} y={FACTOR_LINE_Y - 10} width={`${fvToPct(-1.0) - fvToPct(-1.5)}%`} height={20} fill="#93c5fd" opacity={0.35} rx={2} />
            {/* Strongly */}
            <rect x={`${fvToPct(1.5)}%`} y={FACTOR_LINE_Y - 10} width={`${fvToPct(FACTOR_MAX) - fvToPct(1.5)}%`} height={20} fill="#f87171" opacity={0.3} rx={2} />
            <rect x={`${fvToPct(FACTOR_MIN)}%`} y={FACTOR_LINE_Y - 10} width={`${fvToPct(-1.5) - fvToPct(FACTOR_MIN)}%`} height={20} fill="#60a5fa" opacity={0.3} rx={2} />
            {/* Zone labels at zone CENTERS */}
            <text x={`${fvToPct(-1.75)}%`}  y={FACTOR_LINE_Y - 14} fontSize={7} fill="#94a3b8" textAnchor="middle">Strongly</text>
            <text x={`${fvToPct(-1.25)}%`}  y={FACTOR_LINE_Y - 14} fontSize={7} fill="#94a3b8" textAnchor="middle">Moderately</text>
            <text x={`${fvToPct(-0.75)}%`}  y={FACTOR_LINE_Y - 14} fontSize={7} fill="#94a3b8" textAnchor="middle">Leans</text>
            <text x={`${fvToPct(0)}%`}      y={FACTOR_LINE_Y - 14} fontSize={7} fill="#94a3b8" textAnchor="middle">Centrist</text>
            <text x={`${fvToPct(0.75)}%`}   y={FACTOR_LINE_Y - 14} fontSize={7} fill="#94a3b8" textAnchor="middle">Leans</text>
            <text x={`${fvToPct(1.25)}%`}   y={FACTOR_LINE_Y - 14} fontSize={7} fill="#94a3b8" textAnchor="middle">Moderately</text>
            <text x={`${fvToPct(1.75)}%`}   y={FACTOR_LINE_Y - 14} fontSize={7} fill="#94a3b8" textAnchor="middle">Strongly</text>
            {/* Pole labels at ends */}
            <text x="1%"  y={FACTOR_H - 4} fontSize={8} fill="#2563eb" fontWeight="600">
              ← {FACTOR_POLES[factor]?.low ?? ''}
            </text>
            <text x="99%" y={FACTOR_H - 4} fontSize={8} fill="#dc2626" fontWeight="600" textAnchor="end">
              {FACTOR_POLES[factor]?.high ?? ''} →
            </text>
          </>
        ) : (
          <>
            <text x="1%"  y={FACTOR_H - 4} fontSize={8} fill="#2563eb" fontWeight="600">
              ← {FACTOR_POLES[factor]?.low ?? ''} (0%)
            </text>
            <text x="50%" y={FACTOR_H - 4} fontSize={8} fill="#94a3b8" textAnchor="middle">50% (median)</text>
            <text x="99%" y={FACTOR_H - 4} fontSize={8} fill="#dc2626" fontWeight="600" textAnchor="end">
              {FACTOR_POLES[factor]?.high ?? ''} (100%) →
            </text>
          </>
        )}
        {/* Dots */}
        {scored.map((item, idx) => {
          const pct   = toPos(item);
          const color = getBlendColor(item.code);
          const above = idx % 2 === 0;
          const labelY = above
            ? FACTOR_LINE_Y + FACTOR_DOT_R + 13
            : FACTOR_LINE_Y + FACTOR_DOT_R + 25;
          const anchor = pct < 12 ? 'start' : pct > 88 ? 'end' : 'middle';
          return (
            <g key={item.code}>
              <circle cx={`${pct}%`} cy={FACTOR_LINE_Y} r={FACTOR_DOT_R}
                fill={color} stroke="white" strokeWidth={2} />
              <text x={`${pct}%`} y={labelY} textAnchor={anchor}>
                <tspan fontWeight="700" fontSize={11} fill={color}>{item.code}</tspan>
                <tspan fontSize={10} fill="#475569"> {fmtVal(item)}</tspan>
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function getSectionTitle(key: string): string {
  if (key === 'Untagged') return 'Other / Untagged';
  if ((FACTORS as readonly string[]).includes(key)) return `${FACTOR_LABELS[key]} (${FACTOR_SHORT[key]})`;
  return key;
}

export function CompareTab({ clusters, fdProfiles }: Props) {
  const [selected, setSelected] = useState<string[]>([]);
  const [minGap, setMinGap] = useState(15);
  const [activeFactors, setActiveFactors] = useState<Set<string>>(new Set());
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set(['Untagged']));
  const [groupBy, setGroupBy] = useState<'category' | 'factor'>('category');
  const [showNatAvg, setShowNatAvg] = useState(true);
  const [factorScale, setFactorScale] = useState<'strength' | 'percentile'>('strength');
  const [divergeOnly, setDivergeOnly] = useState(false);

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
    setSelected(prev => [...prev, code]);
  };

  const removeParty = (code: string) => {
    setSelected(prev => prev.filter(c => c !== code));
  };

  const toggleFactor = (f: string) => {
    setActiveFactors(prev => {
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

      const groupKey = groupBy === 'factor'
        ? (factor ?? 'Untagged')
        : entry.domain;

      // Factor filter only applies in category mode
      if (groupBy === 'category' && activeFactors.size > 0 && !activeFactors.has(factor ?? '')) continue;

      if (!grouped[groupKey]) grouped[groupKey] = [];
      grouped[groupKey].push({
        key, question: entry.question, pcts: entry.pcts, overall: entry.overall,
        maxGap, highlighted: maxGap >= minGap, factor,
        maxVal: entry.maxVal, unit: entry.unit,
      });
    }

    for (const key of Object.keys(grouped)) {
      const order = SECTION_QUESTION_ORDER[key];
      if (order) {
        grouped[key].sort((a, b) => {
          const ai = order.indexOf(a.question);
          const bi = order.indexOf(b.question);
          if (ai !== -1 && bi !== -1) return ai - bi;
          if (ai !== -1) return -1;
          if (bi !== -1) return 1;
          return b.maxGap - a.maxGap;
        });
      } else {
        grouped[key].sort((a, b) => {
          if (a.highlighted !== b.highlighted) return a.highlighted ? -1 : 1;
          return b.maxGap - a.maxGap;
        });
      }
    }

    return grouped;
  }, [selected, clusters, fdProfiles, minGap, activeFactors, groupBy]);

  // Ordered section keys
  const sectionKeys = useMemo(() => {
    if (groupBy === 'category') {
      return DOMAINS.filter(d => (sectionVarMap[d]?.length ?? 0) > 0);
    }
    const factorKeys = FACTORS.filter(f => (sectionVarMap[f]?.length ?? 0) > 0);
    const hasUntagged = (sectionVarMap['Untagged']?.length ?? 0) > 0;
    return [...factorKeys, ...(hasUntagged ? ['Untagged'] : [])];
  }, [sectionVarMap, groupBy]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-1">Party Comparison</h2>
        <p className="text-muted-foreground text-sm">
          Compare any number of parties across all policy domains. Amber rows highlight where
          parties differ by ≥{minGap}pp and sort to the top of each section.
        </p>
      </div>

      {/* Party selector */}
      <Card className="p-4">
        <div className="text-sm font-semibold text-foreground mb-3">Select parties to compare</div>
        <div className="flex items-center gap-2 flex-wrap">
          {selected.map(code => {
            const color = getBlendColor(code);
            const label = PARTY_NAMES[code] ?? code;
            return (
              <span
                key={code}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold text-white"
                style={{ backgroundColor: color }}
              >
                {code}
                <span className="font-normal opacity-75 text-xs hidden sm:inline">— {label}</span>
                <button
                  onClick={() => removeParty(code)}
                  className="ml-0.5 opacity-70 hover:opacity-100 leading-none"
                  aria-label={`Remove ${label}`}
                >
                  ×
                </button>
              </span>
            );
          })}
          <select
            className="text-sm border border-border rounded px-2 py-1.5 text-foreground bg-white"
            value=""
            onChange={e => { if (e.target.value) addParty(e.target.value); }}
            aria-label="Select party to add"
          >
            <option value="">+ Add party</option>
            {pureOptions.filter(o => !selected.includes(o.code)).length > 0 && (
              <optgroup label="Pure parties">
                {pureOptions.filter(o => !selected.includes(o.code)).map(o => (
                  <option key={o.code} value={o.code}>{o.code} — {o.label}</option>
                ))}
              </optgroup>
            )}
            {fdOptions.filter(o => !selected.includes(o.code)).length > 0 && (
              <optgroup label="Factor Deviation candidates">
                {fdOptions.filter(o => !selected.includes(o.code)).map(o => (
                  <option key={o.code} value={o.code}>{o.code}</option>
                ))}
              </optgroup>
            )}
          </select>
        </div>
        {selected.length === 0 && (
          <p className="text-xs text-muted-foreground mt-2">
            Try: PRG + NAT (maximum divergence) · SD + CON (presidential rivals) · SD_hi_so + SD (factor deviation vs base)
          </p>
        )}
      </Card>

      {selected.length >= 1 && (
        <>
          {/* Factor scores */}
          <Card className="overflow-hidden">
            <div className="px-4 py-3 border-b border-border/50 bg-muted flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">Factor Scores</span>
                <span className="text-xs text-muted-foreground ml-3">
                  {factorScale === 'strength' ? 'Strongly >1.5σ · Moderately 1.0σ · Leans 0.5σ · Centrist <0.5σ' : '0% = lowest · 50% = median · 100% = highest'}
                </span>
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
            <div>
              {FACTORS.map(f => (
                <FactorDotRow key={f} factor={f} codes={selected} clusters={clusters} fdProfiles={fdProfiles} scaleMode={factorScale} />
              ))}
            </div>
          </Card>

          {/* Controls: group by + factor filter (category mode only) + highlight threshold */}
          <div className="flex flex-wrap items-start gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground uppercase tracking-widest">Group by</span>
              {(['category', 'factor'] as const).map(g => (
                <Button
                  key={g}
                  onClick={() => setGroupBy(g)}
                  variant={groupBy === g ? 'default' : 'secondary'}
                  size="sm"
                >
                  {g === 'category' ? 'Category' : 'Factor'}
                </Button>
              ))}
            </div>

            {groupBy === 'category' && (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs text-muted-foreground uppercase tracking-widest">Filter</span>
                <Button
                  onClick={() => setActiveFactors(new Set())}
                  variant={activeFactors.size === 0 ? 'default' : 'secondary'}
                  size="sm"
                >
                  All
                </Button>
                {FACTORS.map(f => (
                  <Button
                    key={f}
                    onClick={() => toggleFactor(f)}
                    variant={activeFactors.has(f) ? 'default' : 'secondary'}
                    size="sm"
                  >
                    {FACTOR_LABELS[f]} ({FACTOR_SHORT[f]})
                  </Button>
                ))}
              </div>
            )}

            <Button onClick={() => setShowNatAvg(!showNatAvg)}
              variant={showNatAvg ? 'default' : 'secondary'}
              size="sm">
              {showNatAvg ? '✓ National Avg' : 'National Avg'}
            </Button>
            <Button onClick={() => setDivergeOnly(!divergeOnly)}
              variant={divergeOnly ? 'default' : 'secondary'}
              size="sm">
              {divergeOnly ? '✓ Divergences only' : 'Divergences only'}
            </Button>

            <label className="flex items-center gap-1.5 text-xs text-muted-foreground whitespace-nowrap ml-auto">
              Highlight gap ≥
              <input
                type="number"
                min={0}
                max={100}
                value={minGap}
                onChange={e => setMinGap(Math.max(0, Math.min(100, Number(e.target.value))))}
                className="w-14 border border-border rounded px-2 py-1 text-center font-mono text-foreground bg-white"
              />
              pp
            </label>
          </div>

          {/* Sections */}
          {sectionKeys.length === 0 ? (
            <Card className="p-8 text-center text-muted-foreground text-sm">
              No variables match the selected filter.
            </Card>
          ) : (
            <div className="space-y-3">
              {sectionKeys.map(sectionKey => {
                const allVars = sectionVarMap[sectionKey] ?? [];
                const vars = divergeOnly ? allVars.filter(v => v.highlighted) : allVars;
                if (vars.length === 0) return null;
                const collapsed = collapsedSections.has(sectionKey);
                const highlightCount = allVars.filter(v => v.highlighted).length;

                return (
                  <Card key={sectionKey} className="overflow-hidden">
                    <button
                      className="w-full flex items-center justify-between px-4 py-3 hover:bg-muted transition-colors text-left"
                      onClick={() => toggleSection(sectionKey)}
                      aria-expanded={!collapsed}
                    >
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-semibold text-foreground">{getSectionTitle(sectionKey)}</span>
                        <span className="text-xs bg-muted text-muted-foreground rounded-full px-2 py-0.5">{vars.length}</span>
                        {highlightCount > 0 && (
                          <span className="text-xs bg-amber-100 text-amber-700 font-medium rounded-full px-2 py-0.5">
                            {highlightCount} diverge
                          </span>
                        )}
                      </div>
                      <span className="text-muted-foreground text-xs flex-shrink-0 ml-2">{collapsed ? '▶' : '▼'}</span>
                    </button>

                    {!collapsed && (
                      <div className="border-t border-border/50 grid grid-cols-1 sm:grid-cols-2">
                        {vars.map((v, i) => (
                          <div
                            key={v.key}
                            className={[
                              i >= 2 ? 'border-t border-border/50' : '',
                              i % 2 === 0 ? 'sm:border-r border-slate-300' : '',
                            ].filter(Boolean).join(' ')}
                          >
                            <DotTrack
                              question={v.question}
                              factor={v.factor}
                              highlighted={v.highlighted}
                              pcts={v.pcts}
                              codes={selected}
                              gap={v.maxGap}
                              maxVal={v.maxVal}
                              unit={v.unit}
                              overall={v.overall}
                              showNatAvg={showNatAvg}
                            />
                          </div>
                        ))}
                      </div>
                    )}
                  </Card>
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
            Add a second party to compare — amber rows highlight where they diverge by ≥{minGap}pp.
          </div>
        </Card>
      )}
    </div>
  );
}
