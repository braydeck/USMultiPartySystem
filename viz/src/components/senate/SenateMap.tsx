import { useState } from 'react';
import { ComposableMap, Geographies, Geography } from 'react-simple-maps';
import { getBlendColor } from '../../constants/parties';
import type { SenateSeat } from '../../types';

const GEO_URL = './topojson/states-10m.json';

interface Props {
  seats: SenateSeat[];
}

export function SenateMap({ seats }: Props) {
  const [tooltip, setTooltip] = useState<string | null>(null);

  const seatByFips = Object.fromEntries(seats.map(s => [s.stateFips, s]));

  return (
    <div>
      <div className="relative">
        {tooltip && (
          <div className="absolute top-2 left-2 bg-white border border-slate-300 rounded px-3 py-2 text-sm text-slate-900 z-10 pointer-events-none max-w-xs shadow-sm">
            {tooltip}
          </div>
        )}
        <ComposableMap projection="geoAlbersUsa" style={{ width: '100%', height: 'auto' }}>
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map(geo => {
                const fips = geo.id?.toString().padStart(2, '0') ?? '';
                const seat = seatByFips[fips];
                const fill = seat
                  ? getBlendColor(seat.senatorCode) + 'cc'
                  : '#e2e8f0';

                return (
                  <Geography
                    key={geo.rsmKey}
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
                        setTooltip(`${seat.stateAbbr}: ${seat.senatorLabel} (${seat.senatorType})`);
                      }
                    }}
                    onMouseLeave={() => setTooltip(null)}
                  />
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
              onMouseEnter={() => setTooltip(`DC: ${dc.senatorLabel} (${dc.senatorType})`)}
              onMouseLeave={() => setTooltip(null)}
            >
              <div className="text-center text-[9px] font-bold text-slate-500 mb-0.5 leading-none">DC</div>
              <div
                className="rounded border border-slate-300 w-12 h-7"
                style={{ backgroundColor: color + 'cc' }}
              />
            </div>
          );
        })()}
      </div>

      <p className="text-xs text-slate-500 mt-2 text-center">
        Blended senators shown as interpolated colors · hover for details
      </p>
    </div>
  );
}
