import { useState } from 'react';
import {
  ComposableMap,
  Geographies,
  Geography,
} from 'react-simple-maps';
import { getPartyColor } from '../../constants/parties';
import type { SenateSeat } from '../../types';

const GEO_URL = './topojson/states-10m.json';

interface StatePod {
  stateAbbr: string;
  pod: string;
  bench: boolean;
  retail: boolean;
}

interface Props {
  statePods: Record<string, StatePod>;
  senateSeats: SenateSeat[];
}

const POD_COLORS: Record<string, string> = {
  A: '#4ade80',
  B: '#60a5fa',
  C: '#f97316',
  D: '#a78bfa',
};

export function StateDominanceMap({ statePods, senateSeats }: Props) {
  const [tooltip, setTooltip] = useState<string | null>(null);

  const seatByFips = Object.fromEntries(
    senateSeats.map(s => [s.stateFips, s])
  );

  return (
    <div className="relative" aria-label="Primary election state results map" role="img">
      {tooltip && (
        <div className="absolute top-2 left-2 bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm z-10 pointer-events-none" role="status" aria-live="polite">
          {tooltip}
        </div>
      )}
      <ComposableMap
        projection="geoAlbersUsa"
        style={{ width: '100%', height: 'auto' }}
      >
        <Geographies geography={GEO_URL}>
          {({ geographies }) =>
            geographies.map(geo => {
              const fips = geo.id?.toString().padStart(2, '0') ?? '';
              const pod = statePods[fips];
              const seat = seatByFips[fips];
              const fill = seat
                ? getPartyColor(seat.senatorCode) + 'bb'
                : '#1e293b';
              const stroke = pod ? POD_COLORS[pod.pod] ?? '#475569' : '#334155';

              return (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  fill={fill}
                  stroke={stroke}
                  strokeWidth={1.5}
                  style={{
                    default: { outline: 'none' },
                    hover: { outline: 'none', opacity: 0.8 },
                    pressed: { outline: 'none' },
                  }}
                  onMouseEnter={() => {
                    const abbr = pod?.stateAbbr ?? fips;
                    const label = seat
                      ? `${abbr}: ${seat.senatorLabel} (${seat.senatorType})`
                      : abbr;
                    setTooltip(label);
                  }}
                  onMouseLeave={() => setTooltip(null)}
                />
              );
            })
          }
        </Geographies>
      </ComposableMap>
      <div className="flex gap-3 flex-wrap justify-center mt-2 text-xs">
        {Object.entries(POD_COLORS).map(([pod, color]) => (
          <span key={pod} className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-sm inline-block" style={{ backgroundColor: color }} />
            Pod {pod}
          </span>
        ))}
      </div>
    </div>
  );
}
