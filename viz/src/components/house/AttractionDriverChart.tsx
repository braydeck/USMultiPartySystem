import { useState, useMemo } from 'react';
import { PARTY_COLORS, F5_ORDER, PARTY_NAMES, FACTOR_LABELS } from '../../constants/parties';

interface FactorContrib {
  factor: string;
  pct: number;
}

interface AttractionDriver {
  variant: string;
  party: string;
  axis: string;
  direction: string;
  attracted: string;
  attractedPct: number;
  factors: FactorContrib[];
}

interface Props {
  data: AttractionDriver[];
}

const FACTOR_COLOR: Record<string, string> = {
  F1: '#3b82f6', F2: '#8b5cf6', F3: '#6b7280', F4: '#ef4444', F5: '#f59e0b',
};

const AXIS_LABEL: Record<string, string> = {
  so: 'Security', ae: 'Anti-Estab', pc: 'Conservatism', rt: 'Religion',
};

export function AttractionDriverChart({ data }: Props) {
  const [expandedParty, setExpandedParty] = useState<string | null>(null);

  // Group: party → variant → attracted parties
  const grouped = useMemo(() => {
    const map: Record<string, Record<string, AttractionDriver[]>> = {};
    for (const r of data) {
      if (r.attractedPct < 2) continue;
      if (!map[r.party]) map[r.party] = {};
      if (!map[r.party][r.variant]) map[r.party][r.variant] = [];
      map[r.party][r.variant].push(r);
    }
    // Sort variants within each party by total cross-party pull
    for (const party of Object.keys(map)) {
      const sorted: Record<string, AttractionDriver[]> = {};
      const entries = Object.entries(map[party])
        .sort((a, b) => {
          const aTotal = a[1].reduce((s, x) => s + x.attractedPct, 0);
          const bTotal = b[1].reduce((s, x) => s + x.attractedPct, 0);
          return bTotal - aTotal;
        });
      for (const [k, v] of entries) sorted[k] = v.sort((a, b) => b.attractedPct - a.attractedPct);
      map[party] = sorted;
    }
    return map;
  }, [data]);

  return (
    <div>
      {/* Factor legend */}
      <div className="flex flex-wrap gap-3 text-xs mb-4">
        {['F1', 'F2', 'F3', 'F4', 'F5'].map(f => (
          <span key={f} className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-sm inline-block" style={{ backgroundColor: FACTOR_COLOR[f] }} />
            {FACTOR_LABELS[f]}
          </span>
        ))}
      </div>

      {/* Party cards */}
      <div className="space-y-3">
        {F5_ORDER.map(party => {
          const variants = grouped[party];
          if (!variants) return null;
          const color = PARTY_COLORS[party] ?? '#6b7280';
          const name = PARTY_NAMES[party] ?? party;
          const isExpanded = expandedParty === party;
          const variantCount = Object.keys(variants).length;

          return (
            <div key={party} className="rounded-xl border overflow-hidden"
              style={{ borderColor: color + '44' }}>
              {/* Party header — click to expand */}
              <button
                onClick={() => setExpandedParty(isExpanded ? null : party)}
                className="w-full px-4 py-3 flex items-center justify-between text-left transition-colors hover:brightness-95"
                style={{ backgroundColor: color + '10' }}>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold font-mono" style={{ color }}>{party}</span>
                  <span className="text-sm text-slate-700">{name}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-500">{variantCount} deviation{variantCount !== 1 ? 's' : ''} with cross-party pull</span>
                  <span className="text-xs text-slate-400">{isExpanded ? '▼' : '▶'}</span>
                </div>
              </button>

              {/* Expanded: show variants → attracted parties */}
              {isExpanded && (
                <div className="px-4 py-3 space-y-4">
                  {Object.entries(variants).map(([variantCode, drivers]) => {
                    const first = drivers[0];
                    const label = `${first.direction === 'hi' ? 'high' : 'low'} ${AXIS_LABEL[first.axis] ?? first.axis}`;

                    return (
                      <div key={variantCode}>
                        <div className="text-xs font-semibold text-slate-700 mb-1.5">
                          {label}
                        </div>

                        <div className="space-y-1.5 ml-3">
                          {drivers.map((r, idx) => {
                            const attColor = PARTY_COLORS[r.attracted] ?? '#6b7280';
                            return (
                              <div key={idx} className="flex items-center gap-2">
                                <div className="w-16 shrink-0 text-right">
                                  <span className="text-xs font-bold" style={{ color: attColor }}>
                                    {r.attracted}
                                  </span>
                                  <span className="text-[10px] text-slate-400 ml-1">{r.attractedPct}%</span>
                                </div>

                                <div className="flex-1 flex h-5 rounded overflow-hidden border border-slate-200">
                                  {r.factors.map(f => (
                                    <div key={f.factor}
                                      style={{
                                        width: `${f.pct}%`,
                                        backgroundColor: FACTOR_COLOR[f.factor] ?? '#6b7280',
                                        minWidth: f.pct > 3 ? 2 : 0,
                                      }}
                                      title={`${FACTOR_LABELS[f.factor]}: ${f.pct.toFixed(0)}%`}
                                      className="relative">
                                      {f.pct >= 20 && (
                                        <span className="absolute inset-0 flex items-center justify-center text-[9px] font-bold text-white">
                                          {FACTOR_LABELS[f.factor]?.split(' ')[0]} {f.pct.toFixed(0)}%
                                        </span>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
