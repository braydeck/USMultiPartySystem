import { useState } from 'react';
import { ComposableMap, Geographies, Geography } from 'react-simple-maps';
import { getBlendColor } from '../../constants/parties';
import type { SenateSeat } from '../../types';
import type { StateUncertainty } from '../../lib/uncertainty';
import { delegations, SPLIT_THRESHOLD_PP } from '../../lib/senateDelegations';

const GEO_URL = './topojson/states-10m.json';

interface Props {
  seats: SenateSeat[];
  states?: Record<string, StateUncertainty>;
}

const HATCH_ID = 'senate-map-unstable-hatch';

// `modal` arrives as a bare party code and `observed` as a PARTY_N candidate code, so
// both go through the project's party-from-code convention before display or coloring.
const partyOf = (code: string) => code.split('_')[0];

const pct = (p: number) => `${Math.round(p * 100)}%`;

// Names the party the map is actually showing and quotes that party's own share; a
// substituted state also reports the observed run, whose winner the map no longer shows.
function tooltipFor(abbr: string, seat: SenateSeat, u?: StateUncertainty, split?: [string, string]): string {
  if (!u) return `${abbr}: ${seat.senatorLabel} (${seat.senatorType})`;
  const line = split
    ? `${abbr}: splits — one ${split[0]}, one ${split[1]}`
    : `${abbr}: ${partyOf(u.modal)} takes both seats — ${pct(u.pModal)} of resamples`;
  return u.substituted
    ? `${line}; observed run ${partyOf(u.observed)} at ${pct(u.pObserved)}`
    : line;
}

export function SenateMap({ seats, states }: Props) {
  const [tooltip, setTooltip] = useState<string | null>(null);

  const seatByFips = Object.fromEntries(seats.map(s => [s.stateFips, s]));
  // A contested state returns one senator from each of its two closest parties, so it is
  // drawn in both colours rather than being coloured by its modal winner alone.
  const splitByFips: Record<string, [string, string]> = states
    ? Object.fromEntries(delegations(states).filter(d => d.split)
        .map(d => [d.fips, [d.topParty, d.runnerParty!] as [string, string]]))
    : {};
  const splitCount = Object.keys(splitByFips).length;

  return (
    <div>
      {/* Bound the height, as the House cartogram does: geoAlbersUsa is about 4:3, so at
          full width on a wide card the map runs taller than a laptop viewport and the
          reader never sees the country and the legend at once. */}
      <div className="relative mx-auto w-full" style={{ maxWidth: '88vh' }}
        aria-label="Senate election results map" role="img">
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
            <pattern id={HATCH_ID} width="6" height="6" patternUnits="userSpaceOnUse"
              patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="6" stroke="#0f172a" strokeWidth="1.6" strokeOpacity="0.5" />
            </pattern>
            {/* Hard stop, one half per senator — a blend would read as a third party.
                Split left/right, not diagonally: the instability hatch is already a 45°
                diagonal and the two were impossible to tell apart. */}
            {Object.entries(splitByFips).map(([fips, [a, bParty]]) => (
              <linearGradient key={fips} id={`sen-split-${fips}`} x1="0" y1="0" x2="1" y2="0">
                <stop offset="50%" stopColor={getBlendColor(a) + 'cc'} />
                <stop offset="50%" stopColor={getBlendColor(bParty) + 'cc'} />
              </linearGradient>
            ))}
          </defs>
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map(geo => {
                const fips = geo.id?.toString().padStart(2, '0') ?? '';
                const seat = seatByFips[fips];
                const u = states?.[fips];
                // The composition card headlines the modal chamber, so the map colors by
                // modal: counting colors here has to reproduce that headline rather than
                // the single observed run. No record (Crossover) means observed only.
                const split = splitByFips[fips];
                const fill = !seat ? '#e2e8f0'
                  : split ? `url(#sen-split-${fips})`
                    : getBlendColor(u ? partyOf(u.modal) : seat.senatorCode) + 'cc';

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
                        if (seat) setTooltip(tooltipFor(seat.stateAbbr, seat, u, split));
                      }}
                      onMouseLeave={() => setTooltip(null)}
                    />
                    {u && u.pModal < 0.5 && (
                      <Geography geography={geo} fill={`url(#${HATCH_ID})`} stroke="none"
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
          const u = states?.['11'];
          const color = getBlendColor(u ? partyOf(u.modal) : dc.senatorCode);
          return (
            <div
              className="absolute cursor-pointer"
              style={{ bottom: '14%', right: '4%' }}
              onMouseEnter={() => setTooltip(tooltipFor('DC', dc, u))}
              onMouseLeave={() => setTooltip(null)}
            >
              <div className="text-center text-[9px] font-bold text-muted-foreground mb-0.5 leading-none">DC</div>
              <div
                className="rounded border border-slate-300 w-12 h-7"
                style={{
                  backgroundColor: color + 'cc',
                  ...(splitByFips['11'] ? {
                    backgroundImage: `linear-gradient(45deg, ${getBlendColor(splitByFips['11'][0])}cc 0 50%, ${getBlendColor(splitByFips['11'][1])}cc 50% 100%)`,
                  } : {}),
                  // The inset is a div, not SVG, so it cannot carry the hatch pattern;
                  // a CSS gradient reproduces the same 45° stripe at the same threshold.
                  ...(u && u.pModal < 0.5
                    ? { backgroundImage: 'repeating-linear-gradient(45deg, rgba(15,23,42,0.5) 0 1.6px, transparent 1.6px 6px)' }
                    : {}),
                }}
              />
            </div>
          );
        })()}
      </div>

      <p className="text-xs text-muted-foreground mt-2 text-center">
        One race is modelled per state; a state whose winner changes across resamples is
        read as splitting its two seats between its closest parties.
      </p>

      {states && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-[10px] text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <svg width="14" height="14" aria-hidden="true">
              <rect width="14" height="14" fill="#e2e8f0" />
              <rect width="14" height="14" fill={`url(#${HATCH_ID})`} />
            </svg>
            Hatched: no party wins the state in half of resamples
          </span>
          {splitCount > 0 && (
            <span className="flex items-center gap-1.5">
              <svg width="14" height="14" aria-hidden="true">
                <rect width="7" height="14" fill="#cbd5e1" />
                <rect x="7" width="7" height="14" fill="#94a3b8" />
              </svg>
              Two-tone: {splitCount} states split, runner-up within {SPLIT_THRESHOLD_PP} points
            </span>
          )}
        </div>
      )}
    </div>
  );
}
