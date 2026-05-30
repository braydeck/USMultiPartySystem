import { useState } from 'react';
import { ComposableMap, Geographies, Geography } from 'react-simple-maps';
import { getBlendColor, F5_ORDER, getPrimaryParty } from '../../constants/parties';
import type { PrimaryStateWinner } from '../../types';

const GEO_URL = './topojson/states-10m.json';

const STAGE_PODS: Record<string, Set<string>> = {
  After_Retail:     new Set(['Retail']),
  After_Pod_A:      new Set(['Retail', 'A']),
  After_Pod_C:      new Set(['Retail', 'A', 'C']),
  After_Pod_BD:     new Set(['Retail', 'A', 'B', 'C', 'D']),
};

interface Props {
  stateWinners: Record<string, PrimaryStateWinner>;
  stage: string;
}

export function PrimaryStateMap({ stateWinners, stage }: Props) {
  const [tooltip, setTooltip] = useState<string | null>(null);
  const activePods = STAGE_PODS[stage] ?? new Set();

  const tally: Record<string, number> = {};
  for (const [, s] of Object.entries(stateWinners)) {
    if (activePods.has(s.pod)) {
      tally[s.winnerCode] = (tally[s.winnerCode] ?? 0) + 1;
    }
  }
  const legendEntries = Object.entries(tally).sort((a, b) => b[1] - a[1]);

  // Build gradient stops for each active state
  const activeEntries = Object.entries(stateWinners).filter(([, s]) => activePods.has(s.pod));

  return (
    <div>
      <div className="relative" aria-label="Primary election state results map" role="img">
        {tooltip && (
          <div className="absolute top-2 left-2 bg-white border border-slate-300 rounded px-3 py-2 text-sm text-foreground z-10 pointer-events-none max-w-xs shadow-sm" role="status" aria-live="polite">
            {tooltip}
          </div>
        )}
        <ComposableMap projection="geoAlbersUsa" style={{ width: '100%', height: 'auto' }}>
          <defs>
            {activeEntries.map(([fips, sw]) => {
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
                <linearGradient key={fips} id={`pgrad-${fips}`} x1="0%" x2="100%" y1="0%" y2="0%">
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
                const hasVoted = entry && activePods.has(entry.pod);
                const fill = hasVoted ? `url(#pgrad-${fips})` : '#e2e8f0';
                const stroke = hasVoted ? '#cbd5e1' : '#cbd5e1';

                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill={fill}
                    stroke={stroke}
                    strokeWidth={0.8}
                    style={{
                      default: { outline: 'none', cursor: entry ? 'pointer' : 'default' },
                      hover:   { outline: 'none', opacity: 0.85 },
                      pressed: { outline: 'none' },
                    }}
                    onMouseEnter={() => {
                      if (entry && hasVoted) {
                        const shareStr = Object.entries(entry.shares)
                          .sort((a, b) => b[1] - a[1])
                          .map(([c, v]) => `${c}: ${Math.round(v * 100)}%`)
                          .join(' · ');
                        setTooltip(
                          `${entry.stateAbbr} (Pod ${entry.pod}): ${entry.winnerCode} wins · ${shareStr}`
                        );
                      } else if (entry) {
                        setTooltip(`${entry.stateAbbr} (Pod ${entry.pod}) — votes later`);
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

      {legendEntries.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-3 justify-center">
          {legendEntries.map(([code, count]) => (
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
              <span className="bg-muted text-muted-foreground rounded px-1">{count}</span>
            </div>
          ))}
        </div>
      )}

      <p className="text-xs text-muted-foreground mt-2 text-center">
        Gray states haven't voted yet in this stage. Gradient shows candidate share. Hover for details.
      </p>
    </div>
  );
}
