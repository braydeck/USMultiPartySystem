import type { HouseSeat } from '../../types';
import { PARTY_COLORS, F5_ORDER, CLUSTER_TO_PARTY } from '../../constants/parties';

interface Props {
  rawMultiSeats: HouseSeat[];
  fdSeats: HouseSeat[];
  scenario: 'rawMulti' | 'factorDev';
}

export function ScenarioComparison({ rawMultiSeats, fdSeats, scenario }: Props) {
  const rmTotal = rawMultiSeats.reduce((s, r) => s + r.national, 0) || 1;
  const fdTotal = fdSeats.reduce((s, r) => s + r.national, 0) || 1;
  const showFD = scenario === 'factorDev';

  const rows = F5_ORDER.map(code => {
    const rm = rawMultiSeats.find(s => CLUSTER_TO_PARTY[String(s.party)] === code);
    const fd = fdSeats.find(s => CLUSTER_TO_PARTY[String(s.party)] === code);
    return {
      code,
      popPct: rm?.pctPopulation ?? fd?.pctPopulation ?? 0,
      rmPct: rm ? rm.national / rmTotal * 100 : 0,
      fdPct: fd ? fd.national / fdTotal * 100 : 0,
    };
  }).filter(r => r.popPct > 0 || r.rmPct > 0 || r.fdPct > 0);

  const maxPct = Math.max(...rows.flatMap(r => [r.popPct, r.rmPct, r.fdPct]), 1);

  return (
    <div className="space-y-2.5">
      <div className="flex gap-4 text-xs mb-1">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm inline-block bg-slate-500 opacity-50" /> Population %
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm inline-block bg-slate-700" /> Raw Multi seat %
        </span>
        {showFD && (
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm border-2 border-slate-700 inline-block" style={{ backgroundColor: 'transparent' }} /> Factor Dev seat %
          </span>
        )}
      </div>

      {rows.map(r => {
        const color = PARTY_COLORS[r.code] ?? '#6b7280';
        const rmGap = r.rmPct - r.popPct;
        const fdGap = r.fdPct - r.popPct;

        return (
          <div key={r.code} className="grid grid-cols-[56px_1fr] gap-2 items-center">
            <span className="text-xs font-bold font-mono text-right" style={{ color }}>{r.code}</span>
            <div className="space-y-0.5">
              {/* Population */}
              <div className="flex items-center gap-2">
                <div className="h-5 rounded-sm" style={{ width: `${(r.popPct / maxPct) * 100}%`, minWidth: 2, backgroundColor: color, opacity: 0.3 }} />
                <span className="text-[10px] text-muted-foreground whitespace-nowrap">{r.popPct.toFixed(1)}%</span>
              </div>
              {/* Raw Multi */}
              <div className="flex items-center gap-2">
                <div className="h-5 rounded-sm" style={{ width: `${(r.rmPct / maxPct) * 100}%`, minWidth: 2, backgroundColor: color, opacity: 0.75 }} />
                <span className="text-[10px] whitespace-nowrap">
                  <span style={{ color }}>{r.rmPct.toFixed(1)}%</span>
                  <span className={`ml-1 ${rmGap > 0.5 ? 'text-green-600' : rmGap < -1 ? 'text-red-500' : 'text-muted-foreground'}`}>
                    ({rmGap > 0 ? '+' : ''}{rmGap.toFixed(1)})
                  </span>
                </span>
              </div>
              {/* Factor Dev */}
              {showFD && (
                <div className="flex items-center gap-2">
                  <div className="h-5 rounded-sm border-2" style={{
                    width: `${(r.fdPct / maxPct) * 100}%`, minWidth: 2,
                    borderColor: color, backgroundColor: color + '22',
                  }} />
                  <span className="text-[10px] whitespace-nowrap">
                    <span style={{ color }}>{r.fdPct.toFixed(1)}%</span>
                    <span className={`ml-1 ${fdGap > 0.5 ? 'text-green-600' : fdGap < -1 ? 'text-red-500' : 'text-muted-foreground'}`}>
                      ({fdGap > 0 ? '+' : ''}{fdGap.toFixed(1)})
                    </span>
                  </span>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
