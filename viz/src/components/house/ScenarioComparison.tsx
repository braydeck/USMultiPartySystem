import { useMemo } from 'react';
import type { HouseSeat, HouseStateEntry } from '../../types';
import { PARTY_COLORS, F5_ORDER_WFP as F5_ORDER, CLUSTER_TO_PARTY } from '../../constants/parties';
import { Button } from '@/components/ui/button';

interface Props {
  rawMultiSeats: HouseSeat[];
  fdSeats: HouseSeat[];
  scenario: 'rawMulti' | 'factorDev';
  doubleSeats?: HouseSeat[];
  doubleFdSeats?: HouseSeat[];
  wyoming?: 'double' | 'triple';
  stateMap: Record<string, HouseStateEntry>;
  doubleStateMap?: Record<string, HouseStateEntry>;
  selectedState: string;
  onStateChange: (state: string) => void;
}

export function ScenarioComparison({ rawMultiSeats, fdSeats, scenario, doubleSeats, doubleFdSeats, wyoming = 'double', stateMap, doubleStateMap, selectedState, onStateChange }: Props) {

  const stateOptions = useMemo(() => {
    const abbrs = Object.values(stateMap).map(e => e.stateAbbr).sort();
    return ['National', ...abbrs];
  }, [stateMap]);

  const isNational = selectedState === 'national';

  // Compute rows for the selected scope
  const { rows, maxPct, showFD, showDouble } = useMemo(() => {
    const showFD = scenario === 'factorDev';
    const showDbl = wyoming === 'triple' && doubleSeats && doubleSeats.length > 0;

    if (isNational) {
      const rmTotal = rawMultiSeats.reduce((s, r) => s + r.national, 0) || 1;
      const fdTotal = fdSeats.reduce((s, r) => s + r.national, 0) || 1;
      const dblSeatsArr = showDbl ? (showFD && doubleFdSeats ? doubleFdSeats : doubleSeats!) : [];
      const dblTotal = dblSeatsArr.reduce((s, r) => s + r.national, 0) || 1;

      const rows = F5_ORDER.map(code => {
        const rm = rawMultiSeats.find(s => CLUSTER_TO_PARTY[String(s.party)] === code);
        const fd = fdSeats.find(s => CLUSTER_TO_PARTY[String(s.party)] === code);
        const dbl = dblSeatsArr.find(s => CLUSTER_TO_PARTY[String(s.party)] === code);
        return {
          code,
          popPct: rm?.pctPopulation ?? fd?.pctPopulation ?? 0,
          rmPct: rm ? rm.national / rmTotal * 100 : 0,
          fdPct: fd ? fd.national / fdTotal * 100 : 0,
          dblPct: dbl ? dbl.national / dblTotal * 100 : 0,
        };
      }).filter(r => r.popPct > 0 || r.rmPct > 0 || r.fdPct > 0);

      const maxPct = Math.max(...rows.flatMap(r => [r.popPct, r.rmPct, r.fdPct, r.dblPct]), 1);
      return { rows, maxPct, showFD, showDouble: showDbl };
    }

    // State-level view
    const fips = Object.entries(stateMap).find(([, v]) => v.stateAbbr === selectedState)?.[0] ?? '';
    const entry = stateMap[fips];
    const dblEntry = doubleStateMap?.[fips];
    if (!entry) return { rows: [], maxPct: 1, showFD, showDouble: showDbl };

    const totalSeats = entry.totalSeats || 1;
    const dblTotalSeats = dblEntry?.totalSeats || 1;
    const popShares = entry.popShares ?? dblEntry?.popShares ?? {};

    const rows = F5_ORDER.map(code => {
      const seatCount = entry.seats[code] ?? 0;
      const dblSeatCount = dblEntry?.seats?.[code] ?? 0;
      return {
        code,
        popPct: popShares[code] ?? 0,
        rmPct: seatCount / totalSeats * 100,
        fdPct: 0, // no per-state FD data available
        dblPct: dblSeatCount / dblTotalSeats * 100,
      };
    }).filter(r => r.popPct > 0 || r.rmPct > 0 || r.dblPct > 0);

    const maxPct = Math.max(...rows.flatMap(r => [r.popPct, r.rmPct, r.dblPct]), 1);
    return { rows, maxPct, showFD: false, showDouble: showDbl };
  }, [selectedState, isNational, rawMultiSeats, fdSeats, scenario, wyoming, doubleSeats, doubleFdSeats, stateMap, doubleStateMap]);

  return (
    <div className="space-y-2.5">
      {/* State selector */}
      <div className="flex flex-wrap items-center gap-2 mb-2">
        {stateOptions.slice(0, 1).map(opt => (
          <Button key={opt} size="sm"
            variant={selectedState === opt.toLowerCase() ? 'default' : 'secondary'}
            onClick={() => onStateChange(opt.toLowerCase())}>
            {opt}
          </Button>
        ))}
        <select
          className="text-xs border border-border rounded px-2 py-1 bg-background"
          value={selectedState === 'national' ? '' : selectedState}
          onChange={e => onStateChange(e.target.value || 'national')}
        >
          <option value="">Select state…</option>
          {stateOptions.slice(1).map(abbr => (
            <option key={abbr} value={abbr}>{abbr}</option>
          ))}
        </select>
        {selectedState !== 'national' && (
          <span className="text-xs text-muted-foreground">
            {stateMap[Object.entries(stateMap).find(([, v]) => v.stateAbbr === selectedState)?.[0] ?? '']?.totalSeats ?? 0} seats
          </span>
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-xs mb-1">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm inline-block bg-slate-500 opacity-50" /> Population %
        </span>
        {showDouble && (
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm inline-block bg-slate-400 border border-dashed border-slate-600" /> Double (873) seat %
          </span>
        )}
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm inline-block bg-slate-700" /> {wyoming === 'triple' ? 'Triple (~1,726)' : 'Party-Line'} seat %
        </span>
        {showFD && (
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm border-2 border-slate-700 inline-block" style={{ backgroundColor: 'transparent' }} /> Crossover seat %
          </span>
        )}
      </div>

      {rows.map(r => {
        const color = PARTY_COLORS[r.code] ?? '#6b7280';
        const rmGap = r.rmPct - r.popPct;
        const fdGap = r.fdPct - r.popPct;

        return (
          <div key={r.code} className="grid grid-cols-[56px_1fr] gap-2 items-center">
            <span className="text-xs font-bold font-mono text-right" style={{ color }}>
              {r.code}
            </span>
            <div className="space-y-0.5">
              {/* Population */}
              <div className="flex items-center gap-2">
                <div className="h-5 rounded-sm" style={{ width: `${(r.popPct / maxPct) * 100}%`, minWidth: 2, backgroundColor: color, opacity: 0.3 }} />
                <span className="text-[10px] text-muted-foreground whitespace-nowrap">{r.popPct.toFixed(1)}%</span>
              </div>
              {/* Double Wyoming (shown in triple view) */}
              {showDouble && (
                <div className="flex items-center gap-2">
                  <div className="h-5 rounded-sm border border-dashed" style={{ width: `${(r.dblPct / maxPct) * 100}%`, minWidth: 2, borderColor: color, backgroundColor: color, opacity: 0.35 }} />
                  <span className="text-[10px] whitespace-nowrap">
                    <span className="text-muted-foreground">{r.dblPct.toFixed(1)}%</span>
                    <span className="ml-1 text-muted-foreground text-[9px]">(873)</span>
                  </span>
                </div>
              )}
              {/* Active scenario */}
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
