import { useMemo } from 'react';
import { PARTY_COLORS, F5_ORDER, PARTY_NAMES, getContrastText } from '../../constants/parties';

interface Source {
  party: string;
  pct: number;
}

interface VariantData {
  variant: string;
  party: string;
  axis: string;
  direction: string;
  totalVoters: number;
  homePct: number;
  crossPct: number;
  sources: Source[];
}

interface Props {
  data: VariantData[];
}

const AXIS_LABEL: Record<string, string> = {
  so: 'Security', es: 'Elec. Skepticism', pc: 'Conservatism', rt: 'Religion',
};

function variantLabel(v: VariantData): string {
  if (v.axis === 'base') return 'base';
  const dir = v.direction === 'hi' ? 'high' : 'low';
  return `${dir} ${AXIS_LABEL[v.axis] ?? v.axis}`;
}

export function VariantAttractionChart({ data }: Props) {
  const { byParty, baseCross } = useMemo(() => {
    const grouped: Record<string, VariantData[]> = {};
    const bases: Record<string, number> = {};
    for (const v of data) {
      if (!grouped[v.party]) grouped[v.party] = [];
      grouped[v.party].push(v);
      if (v.axis === 'base') bases[v.party] = v.crossPct;
    }
    // Remove base entries and sort by incremental cross-party
    for (const p of Object.keys(grouped)) {
      grouped[p] = grouped[p]
        .filter(v => v.axis !== 'base')
        .sort((a, b) => (b.crossPct - (bases[b.party] ?? 0)) - (a.crossPct - (bases[a.party] ?? 0)));
    }
    return { byParty: grouped, baseCross: bases };
  }, [data]);

  // Global max incremental source total for consistent bar scaling
  const globalMaxInc = useMemo(() => {
    let max = 1;
    for (const variants of Object.values(byParty)) {
      for (const v of variants) {
        const baseVariant = data.find(d => d.party === v.party && d.axis === 'base');
        const baseSources: Record<string, number> = {};
        if (baseVariant) {
          for (const s of baseVariant.sources) {
            if (s.party !== v.party) baseSources[s.party] = s.pct;
          }
        }
        const incTotal = v.sources
          .filter(s => s.party !== v.party)
          .reduce((sum, s) => sum + Math.max(0, s.pct - (baseSources[s.party] ?? 0)), 0);
        if (incTotal > max) max = incTotal;
      }
    }
    return max;
  }, [byParty, data]);

  return (
    <div className="space-y-6">
      {F5_ORDER.map(party => {
        const variants = byParty[party];
        if (!variants || variants.length === 0) return null;
        const color = PARTY_COLORS[party] ?? '#6b7280';
        const name = PARTY_NAMES[party] ?? party;

        const baseRef = baseCross[party] ?? 0;

        if (variants.length === 0) return null;

        return (
          <div key={party}>
            <div className="flex items-center gap-2 mb-0.5">
              <span className="text-sm font-bold font-mono" style={{ color }}>{party}</span>
              <span className="text-sm text-muted-foreground">{name}</span>
            </div>
            <div className="text-xs text-muted-foreground mb-2">
              Base cross-party: {baseRef.toFixed(1)}% — values below show incremental attraction from each deviation
            </div>

            <div className="space-y-2.5">
              {variants.map(v => {
                const label = variantLabel(v);
                const incremental = v.crossPct - baseRef;
                const crossSources = v.sources.filter(s => s.party !== v.party);
                // Compute incremental sources (subtract base-level per-party)
                const baseVariant = data.find(d => d.party === v.party && d.axis === 'base');
                const baseSources: Record<string, number> = {};
                if (baseVariant) {
                  for (const s of baseVariant.sources) {
                    if (s.party !== v.party) baseSources[s.party] = s.pct;
                  }
                }
                const incrementalSources = crossSources.map(s => ({
                  party: s.party,
                  pct: Math.max(0, s.pct - (baseSources[s.party] ?? 0)),
                  total: s.pct,
                })).filter(s => s.pct > 0.3);
                const incTotal = incrementalSources.reduce((s, x) => s + x.pct, 0);

                const isPositive = incremental > 0.5;
                const isNegative = incremental < -0.5;

                return (
                  <div key={v.variant} className="flex items-center gap-3">
                    <div className="w-32 shrink-0 text-right">
                      <div className="text-xs font-semibold text-foreground">{label}</div>
                      <div className={`text-xs font-medium ${isPositive ? 'text-green-700' : isNegative ? 'text-red-600' : 'text-muted-foreground'}`}>
                        {incremental > 0 ? '+' : ''}{incremental.toFixed(1)}pp vs base
                      </div>
                    </div>

                    <div className="flex-1 flex items-center gap-2">
                      {incrementalSources.length > 0 ? (
                        <>
                          <div
                            className="flex h-7 rounded overflow-hidden border border-border"
                            style={{ width: `${Math.max(incTotal / globalMaxInc * 80, 4)}%`, minWidth: 30 }}
                          >
                            {incrementalSources.map(s => {
                              const sColor = PARTY_COLORS[s.party] ?? '#6b7280';
                              const widthPct = incTotal > 0 ? s.pct / incTotal * 100 : 0;
                              return (
                                <div
                                  key={s.party}
                                  style={{
                                    width: `${widthPct}%`,
                                    backgroundColor: sColor,
                                    minWidth: widthPct > 2 ? 3 : 0,
                                  }}
                                  title={`${s.party}: +${s.pct.toFixed(1)}% (total: ${s.total}%)`}
                                  className="relative"
                                >
                                  {widthPct >= 20 && (
                                    <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold drop-shadow-sm chip-text" style={{ color: getContrastText(sColor) }}>
                                      {s.party}
                                    </span>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                          <span className="text-xs text-muted-foreground whitespace-nowrap">
                            {incrementalSources.filter(s => s.pct >= 1).map(s => `${s.party} +${s.pct.toFixed(1)}%`).join(' · ')}
                          </span>
                        </>
                      ) : (
                        <span className="text-xs text-muted-foreground">no incremental attraction</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
