import { useState } from 'react';
import { ComposableMap, Geographies, Geography } from 'react-simple-maps';
import { getBlendColor } from '../../constants/parties';
import type { SenateSeat } from '../../types';
import type { StateUncertainty } from '../../lib/uncertainty';

const GEO_URL = './topojson/states-10m.json';

interface Props {
  seats: SenateSeat[];
  states?: Record<string, StateUncertainty>;
}

export function SenateMap({ seats, states }: Props) {
  const [tooltip, setTooltip] = useState<string | null>(null);

  const seatByFips = Object.fromEntries(seats.map(s => [s.stateFips, s]));

  return (
    <div>
      <div className="relative" aria-label="Senate election results map" role="img">
        {tooltip && (
          <div className="absolute top-2 left-2 bg-white border border-slate-300 rounded px-3 py-2 text-sm text-foreground z-10 pointer-events-none max-w-xs shadow-sm" role="status" aria-live="polite">
            {tooltip}
          </div>
        )}
        <ComposableMap projection="geoAlbersUsa" style={{ width: '100%', height: 'auto' }}>
          <defs>
            {/* Diagonal hatch marks states whose winner flips on sampling. A numeric
                label is not an option here: this is a geoAlbersUsa projection and the
                least stable states (WY, ND, VT, DC, RI) are the smallest on screen. */}
            <pattern id="unstable-hatch" width="6" height="6" patternUnits="userSpaceOnUse"
              patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="6" stroke="#0f172a" strokeWidth="1.6" strokeOpacity="0.5" />
            </pattern>
          </defs>
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map(geo => {
                const fips = geo.id?.toString().padStart(2, '0') ?? '';
                const seat = seatByFips[fips];
                const fill = seat
                  ? getBlendColor(seat.senatorCode) + 'cc'
                  : '#e2e8f0';

                return (
                  <g key={geo.rsmKey}>
                    <Geography
                      geography={geo}
                      fill={fill}
                      stroke="#cbd5e1"
                      strokeWidth={1}
                      style={{
                        default: { outline: 'none', cursor: seat ? 'pointer' : 'default' },
                        hover:   { outline: 'none', opacity: 0.8 },
                        pressed: { outline: 'none' },
                      }}
                      onMouseEnter={() => {
                        if (seat) {
                          const u = states?.[fips];
                          const prob = u ? ` — ${Math.round(u.pModal * 100)}% of resamples` : '';
                          setTooltip(`${seat.stateAbbr}: ${seat.senatorLabel} (${seat.senatorType})${prob}`);
                        }
                      }}
                      onMouseLeave={() => setTooltip(null)}
                    />
                    {states?.[fips] && states[fips].pModal < 0.5 && (
                      <Geography geography={geo} fill="url(#unstable-hatch)" stroke="none"
                        style={{ default: { outline: 'none', pointerEvents: 'none' },
                                 hover: { outline: 'none', pointerEvents: 'none' },
                                 pressed: { outline: 'none', pointerEvents: 'none' } }} />
                    )}
                  </g>
                );
              })
            }
          </Geographies>
        </ComposableMap>

        {/* DC inset — geoAlbersUsa renders DC as a near-invisible dot */}
        {(() => {
          const dc = seatByFips['11'];
          if (!dc) return null;
          const color = getBlendColor(dc.senatorCode);
          return (
            <div
              className="absolute cursor-pointer"
              style={{ bottom: '14%', right: '4%' }}
              onMouseEnter={() => {
                const u = states?.['11'];
                const prob = u ? ` — ${Math.round(u.pModal * 100)}% of resamples` : '';
                setTooltip(`DC: ${dc.senatorLabel} (${dc.senatorType})${prob}`);
              }}
              onMouseLeave={() => setTooltip(null)}
            >
              <div className="text-center text-[9px] font-bold text-muted-foreground mb-0.5 leading-none">DC</div>
              <div
                className="rounded border border-slate-300 w-12 h-7"
                style={{ backgroundColor: color + 'cc' }}
              />
            </div>
          );
        })()}
      </div>

      <p className="text-xs text-muted-foreground mt-2 text-center">
        Blended senators shown as interpolated colors · hover for details
      </p>

      {states && (
        <div className="flex items-center gap-2 mt-2 text-[10px] text-muted-foreground">
          <svg width="14" height="14" aria-hidden="true">
            <rect width="14" height="14" fill="#e2e8f0" />
            <rect width="14" height="14" fill="url(#unstable-hatch)" />
          </svg>
          Hatched: the winner changes in more than half of resamples
        </div>
      )}
    </div>
  );
}
