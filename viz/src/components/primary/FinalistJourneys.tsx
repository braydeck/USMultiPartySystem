import { useMemo } from 'react';
import { PARTY_COLORS, PARTY_NAMES, F5_ORDER } from '../../constants/parties';
import type { FDPrimaryData, PrimarySankeyData } from '../../types';

interface Props {
  data: FDPrimaryData;
  sankeyData: PrimarySankeyData;
}

interface StageSnapshot {
  label: string;
  pct: number;
  delta: number; // change from previous stage
  absorbed: string[]; // party codes whose voters flowed HERE
  surplusTo: string[]; // candidate codes that received surplus FROM this finalist
}

interface FinalistRow {
  code: string;
  party: string;
  partyName: string;
  stages: StageSnapshot[];
  maxPct: number;
}

function partyOf(code: string): string {
  return code.split('_')[0];
}

export default function FinalistJourneys({ data, sankeyData }: Props) {
  const rows = useMemo(() => {
    const stages = data.stagesOrder;
    const { nodes, links } = sankeyData;

    // Find finalists — survivors at last stage
    const lastStage = stages[stages.length - 1];
    const finalists = data.candidates
      .filter(c => {
        const sd = c.stages[lastStage];
        return sd && (sd.status === 'surviving' || sd.status === 'elected') && sd.votePct > 0;
      })
      .sort((a, b) => {
        const ai = F5_ORDER.indexOf(a.party as typeof F5_ORDER[number]);
        const bi = F5_ORDER.indexOf(b.party as typeof F5_ORDER[number]);
        return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
      });

    // Get initial vote share from Sankey Stage 0 nodes
    const initialPcts: Record<string, number> = {};
    for (const n of nodes) {
      if (n.stageIdx === 0) initialPcts[n.label] = n.pct;
    }

    // For each stage, find eliminated candidates and where their votes went
    // Use Sankey links: outgoing from eliminated candidates
    const eliminatedAt: Record<number, string[]> = {}; // stageIdx → eliminated codes
    for (let i = 0; i < stages.length; i++) {
      const stage = stages[i];
      eliminatedAt[i + 1] = data.candidates
        .filter(c => c.stages[stage]?.status === 'eliminated_this_round')
        .map(c => c.code);
    }

    // Build a map: at each stage transition, which finalists absorbed votes from which parties?
    // Look at elimination/surplus links from eliminated candidates to finalist nodes
    const absorbedMap: Record<string, Record<string, Set<string>>> = {}; // stageIdx → finalistCode → Set<sourceParty>
    for (let si = 1; si <= stages.length; si++) {
      absorbedMap[si] = {};
      for (const fin of finalists) {
        const targetId = `${fin.code}__${si}`;
        const sources = new Set<string>();
        for (const l of links) {
          if (l.target === targetId && l.type !== 'continuation') {
            const srcCode = l.source.split('__')[0];
            const srcParty = partyOf(srcCode);
            if (srcParty !== fin.party) {
              sources.add(srcParty);
            }
          }
        }
        // Also check: did any eliminated candidate's links target this finalist?
        // (handles chain-resolved links too)
        for (const elimCode of (eliminatedAt[si] ?? [])) {
          const elimParty = partyOf(elimCode);
          if (elimParty === fin.party) continue;
          // Check if any link from this eliminated candidate targets our finalist
          for (const l of links) {
            if (l.source === `${elimCode}__${si - 1}` && l.target === targetId) {
              sources.add(elimParty);
            }
          }
        }
        absorbedMap[si][fin.code] = sources;
      }
    }

    // Build surplus-out info: for each finalist at each stage, who received their surplus?
    const surplusMap: Record<string, Record<string, string[]>> = {};
    for (let si = 1; si <= stages.length; si++) {
      surplusMap[si] = {};
      for (const fin of finalists) {
        const srcId = `${fin.code}__${si - 1}`;
        const surplusDests: string[] = [];
        for (const l of links) {
          if (l.source === srcId && l.type === 'surplus') {
            const destCode = l.target.split('__')[0];
            if (destCode !== fin.code && l.value > 0.5) {
              surplusDests.push(destCode);
            }
          }
        }
        surplusMap[si][fin.code] = surplusDests.slice(0, 3); // top 3
      }
    }

    // Assemble rows
    const result: FinalistRow[] = [];
    let globalMax = 0;

    for (const fin of finalists) {
      const snapshots: StageSnapshot[] = [];
      const initPct = initialPcts[fin.code] ?? 0;

      // Initial Slate
      snapshots.push({
        label: 'Initial',
        pct: initPct,
        delta: 0,
        absorbed: [],
        surplusTo: [],
      });

      let prevPct = initPct;
      for (let i = 0; i < stages.length; i++) {
        const stage = stages[i];
        const sd = fin.stages[stage];
        const pct = sd?.votePct ?? 0;
        const stageLabel = data.stageLabels[stage] ?? stage.replace(/_/g, ' ').replace('After ', '');

        const absorbed = Array.from(absorbedMap[i + 1]?.[fin.code] ?? []);
        const surplusTo = surplusMap[i + 1]?.[fin.code] ?? [];

        snapshots.push({
          label: stageLabel,
          pct,
          delta: pct - prevPct,
          absorbed,
          surplusTo,
        });
        prevPct = pct;
      }

      const maxPct = Math.max(...snapshots.map(s => s.pct));
      if (maxPct > globalMax) globalMax = maxPct;

      result.push({
        code: fin.code,
        party: fin.party,
        partyName: PARTY_NAMES[fin.party] ?? fin.party,
        stages: snapshots,
        maxPct,
      });
    }

    // Normalize to global max
    for (const r of result) r.maxPct = globalMax;
    return result;
  }, [data, sankeyData]);

  if (rows.length === 0) return null;

  const globalMax = rows[0]?.maxPct ?? 25;

  return (
    <div className="space-y-4">
      {rows.map(row => {
        const color = PARTY_COLORS[row.party] ?? '#6b7280';
        return (
          <div key={row.code} className="space-y-0.5">
            {/* Header */}
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-bold" style={{ color }}>{row.code}</span>
              <span className="text-xs text-muted-foreground">{row.partyName}</span>
              <span className="text-xs font-semibold text-muted-foreground ml-auto">
                {row.stages[row.stages.length - 1].pct.toFixed(1)}%
              </span>
            </div>

            {/* Stage bars */}
            {row.stages.map((snap, si) => (
              <div key={si} className="flex items-center gap-2 h-5">
                {/* Stage label */}
                <span className="text-3xs text-muted-foreground w-12 text-right shrink-0">
                  {snap.label}
                </span>

                {/* Bar */}
                <div className="flex-1 h-4 bg-slate-50 rounded-sm overflow-hidden relative">
                  <div
                    className="h-full rounded-sm transition-all duration-300"
                    style={{
                      width: `${(snap.pct / globalMax) * 100}%`,
                      backgroundColor: color,
                      opacity: 0.75,
                    }}
                  />
                  {/* Pct label inside or outside bar */}
                  <span
                    className="absolute top-0 h-full flex items-center text-4xs font-semibold"
                    style={{
                      left: `${Math.min((snap.pct / globalMax) * 100 + 1, 95)}%`,
                      color: '#475569',
                    }}
                  >
                    {snap.pct.toFixed(1)}
                  </span>
                </div>

                {/* Annotation */}
                <div className="text-4xs text-muted-foreground w-44 shrink-0 truncate">
                  {snap.delta < -1 && snap.surplusTo.length > 0 && (
                    <span>
                      <span className="text-amber-500">↗</span> surplus → {snap.surplusTo.join(', ')}
                    </span>
                  )}
                  {snap.delta > 0.5 && snap.absorbed.length > 0 && (
                    <span>
                      <span className="text-emerald-500">←</span>{' '}
                      {snap.absorbed.map(p => (
                        <span key={p} style={{ color: PARTY_COLORS[p] ?? '#6b7280' }} className="font-semibold">
                          {p}
                        </span>
                      )).reduce<React.ReactNode[]>((acc, el, i) => i === 0 ? [el] : [...acc, ', ', el], [])}
                      {' '}voters
                    </span>
                  )}
                  {snap.delta > 0.5 && snap.absorbed.length === 0 && si > 0 && (
                    <span className="text-slate-300">← redistribution</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}
