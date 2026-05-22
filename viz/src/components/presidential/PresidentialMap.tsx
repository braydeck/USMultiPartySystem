import { useState } from 'react';
import { ComposableMap, Geographies, Geography } from 'react-simple-maps';
import { getBlendColor, F5_ORDER, getPrimaryParty } from '../../constants/parties';
import type { PresidentialStateWinner } from '../../types';

const GEO_URL = './topojson/states-10m.json';

type MapView = 'irv' | 'plurality';

// 2020 apportionment electoral votes by state abbreviation
const ELECTORAL_VOTES: Record<string, number> = {
  AL: 9,  AK: 3,  AZ: 11, AR: 6,  CA: 54, CO: 10, CT: 7,  DE: 3,  DC: 3,
  FL: 30, GA: 16, HI: 4,  ID: 4,  IL: 19, IN: 11, IA: 6,  KS: 6,  KY: 8,
  LA: 8,  ME: 4,  MD: 10, MA: 11, MI: 15, MN: 10, MS: 6,  MO: 10, MT: 4,
  NE: 5,  NV: 6,  NH: 4,  NJ: 14, NM: 5,  NY: 28, NC: 16, ND: 3,  OH: 17,
  OK: 7,  OR: 8,  PA: 19, RI: 4,  SC: 9,  SD: 3,  TN: 11, TX: 40, UT: 6,
  VT: 3,  VA: 13, WA: 12, WV: 4,  WI: 10, WY: 3,
};

interface Props {
  stateWinners: Record<string, PresidentialStateWinner>;
}

export function PresidentialMap({ stateWinners }: Props) {
  const [tooltip, setTooltip] = useState<string | null>(null);
  const [mapView, setMapView] = useState<MapView>('irv');

  // Derive effective winner per state for the selected view
  const effectiveWinner = (entry: PresidentialStateWinner): string => {
    if (mapView === 'irv') return entry.winner;
    const sorted = Object.entries(entry.shares).sort((a, b) => b[1] - a[1]);
    return sorted[0]?.[0] ?? entry.winner;
  };

  // Tally winner counts + electoral votes for legend
  const tally: Record<string, { states: number; evs: number }> = {};
  for (const entry of Object.values(stateWinners)) {
    const w = effectiveWinner(entry);
    const ev = ELECTORAL_VOTES[entry.stateAbbr] ?? 0;
    if (!tally[w]) tally[w] = { states: 0, evs: 0 };
    tally[w].states += 1;
    tally[w].evs += ev;
  }
  const legendEntries = Object.entries(tally).sort((a, b) => b[1].evs - a[1].evs);

  return (
    <div>
      {/* Toggle */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs font-semibold text-slate-600 uppercase tracking-widest">View:</span>
        {(['irv', 'plurality'] as MapView[]).map(v => (
          <button
            key={v}
            onClick={() => setMapView(v)}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              mapView === v
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-200 text-slate-600 hover:bg-slate-300'
            }`}
          >
            {v === 'irv' ? 'IRV Winner' : '1st Choice (Plurality)'}
          </button>
        ))}
      </div>

      <div className="relative">
        {tooltip && (
          <div className="absolute top-2 left-2 bg-white border border-slate-300 rounded px-3 py-2 text-sm text-slate-900 z-10 pointer-events-none max-w-sm shadow-sm">
            {tooltip}
          </div>
        )}
        <ComposableMap projection="geoAlbersUsa" style={{ width: '100%', height: 'auto' }}>
          <defs>
            {Object.entries(stateWinners).map(([fips, sw]) => {
              const sorted = Object.entries(sw.shares).sort((a, b) => {
                const rA = F5_ORDER.indexOf(getPrimaryParty(a[0]) as typeof F5_ORDER[number]);
                const rB = F5_ORDER.indexOf(getPrimaryParty(b[0]) as typeof F5_ORDER[number]);
                return (rA === -1 ? 99 : rA) - (rB === -1 ? 99 : rB);
              });
              let cum = 0;
              const stops: { offset: number; color: string }[] = [];
              for (const [code, share] of sorted) {
                const color = getBlendColor(code);
                stops.push({ offset: cum * 100, color });
                cum += share;
                stops.push({ offset: cum * 100, color });
              }
              return (
                <linearGradient key={fips} id={`egrad-${fips}`} x1="0%" x2="100%" y1="0%" y2="0%">
                  {stops.map((s, i) => (
                    <stop key={i} offset={`${s.offset.toFixed(1)}%`} stopColor={s.color} stopOpacity={0.85} />
                  ))}
                </linearGradient>
              );
            })}
          </defs>
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map(geo => {
                const fips = geo.id?.toString().padStart(2, '0') ?? '';
                const entry = stateWinners[fips];
                const fill = entry ? `url(#egrad-${fips})` : '#e2e8f0';
                const winner = entry ? effectiveWinner(entry) : null;

                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill={fill}
                    stroke={winner ? getBlendColor(winner) + '66' : '#cbd5e1'}
                    strokeWidth={1}
                    style={{
                      default: { outline: 'none', cursor: entry ? 'pointer' : 'default' },
                      hover:   { outline: 'none', opacity: 0.85 },
                      pressed: { outline: 'none' },
                    }}
                    onMouseEnter={() => {
                      if (entry) {
                        const w = effectiveWinner(entry);
                        const ev = ELECTORAL_VOTES[entry.stateAbbr];
                        const evStr = ev ? ` · ${ev} EV` : '';
                        const shareStr = Object.entries(entry.shares)
                          .sort((a, b) => b[1] - a[1])
                          .map(([c, v]) => `${c}: ${Math.round(v * 100)}%`)
                          .join(' · ');
                        const irvNote = mapView === 'plurality' && w !== entry.winner
                          ? ` (IRV winner: ${entry.winner})`
                          : '';
                        setTooltip(`${entry.stateAbbr}${evStr}: ${w}${irvNote} · ${shareStr}`);
                      }
                    }}
                    onMouseLeave={() => setTooltip(null)}
                  />
                );
              })
            }
          </Geographies>
        </ComposableMap>
      </div>

      <div className="flex flex-wrap gap-2 mt-3 justify-center">
        {legendEntries.map(([code, { states, evs }]) => (
          <div
            key={code}
            className="flex items-center gap-1.5 px-2 py-1 rounded text-xs font-semibold"
            style={{
              backgroundColor: getBlendColor(code) + '33',
              border: `1px solid ${getBlendColor(code)}88`,
              color: getBlendColor(code),
            }}
          >
            {code}
            <span className="bg-slate-100 text-slate-600 rounded px-1">
              {evs > 0 ? `${evs} EV` : `${states} states`}
            </span>
          </div>
        ))}
      </div>

      <p className="text-xs text-slate-500 mt-2 text-center">
        {mapView === 'irv'
          ? 'IRV winner per state. Gradient shows 1st-choice share. Hover for details.'
          : '1st-choice plurality winner per state. Hover to see if IRV changed the outcome.'}
      </p>
    </div>
  );
}
