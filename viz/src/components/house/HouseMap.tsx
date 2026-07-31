import { useMemo, useState } from 'react';
import type { DistrictResult } from '../../types';
import { PARTY_COLORS, PARTY_NAMES, F5_ORDER_WFP as F5_ORDER, getContrastText } from '../../constants/parties';
import { Card } from '@/components/ui/card';
import { HexCartogram } from './HexCartogram';

const TIER_LABELS: Record<string, string> = {
  URBAN:    'Urban',
  SUBURBAN: 'Suburban',
  RURAL:    'Rural',
};

const TIER_COLORS: Record<string, string> = {
  URBAN:    '#4f46e5',
  SUBURBAN: '#f97316',
  RURAL:    '#16a34a',
};

const US_STATES: { name: string; fips: string; abbr: string }[] = [
  { name: 'Alabama', fips: '01', abbr: 'AL' }, { name: 'Alaska', fips: '02', abbr: 'AK' },
  { name: 'Arizona', fips: '04', abbr: 'AZ' }, { name: 'Arkansas', fips: '05', abbr: 'AR' },
  { name: 'California', fips: '06', abbr: 'CA' }, { name: 'Colorado', fips: '08', abbr: 'CO' },
  { name: 'Connecticut', fips: '09', abbr: 'CT' }, { name: 'Delaware', fips: '10', abbr: 'DE' },
  { name: 'District of Columbia', fips: '11', abbr: 'DC' },
  { name: 'Florida', fips: '12', abbr: 'FL' }, { name: 'Georgia', fips: '13', abbr: 'GA' },
  { name: 'Hawaii', fips: '15', abbr: 'HI' }, { name: 'Idaho', fips: '16', abbr: 'ID' },
  { name: 'Illinois', fips: '17', abbr: 'IL' }, { name: 'Indiana', fips: '18', abbr: 'IN' },
  { name: 'Iowa', fips: '19', abbr: 'IA' }, { name: 'Kansas', fips: '20', abbr: 'KS' },
  { name: 'Kentucky', fips: '21', abbr: 'KY' }, { name: 'Louisiana', fips: '22', abbr: 'LA' },
  { name: 'Maine', fips: '23', abbr: 'ME' }, { name: 'Maryland', fips: '24', abbr: 'MD' },
  { name: 'Massachusetts', fips: '25', abbr: 'MA' }, { name: 'Michigan', fips: '26', abbr: 'MI' },
  { name: 'Minnesota', fips: '27', abbr: 'MN' }, { name: 'Mississippi', fips: '28', abbr: 'MS' },
  { name: 'Missouri', fips: '29', abbr: 'MO' }, { name: 'Montana', fips: '30', abbr: 'MT' },
  { name: 'Nebraska', fips: '31', abbr: 'NE' }, { name: 'Nevada', fips: '32', abbr: 'NV' },
  { name: 'New Hampshire', fips: '33', abbr: 'NH' }, { name: 'New Jersey', fips: '34', abbr: 'NJ' },
  { name: 'New Mexico', fips: '35', abbr: 'NM' }, { name: 'New York', fips: '36', abbr: 'NY' },
  { name: 'North Carolina', fips: '37', abbr: 'NC' }, { name: 'North Dakota', fips: '38', abbr: 'ND' },
  { name: 'Ohio', fips: '39', abbr: 'OH' }, { name: 'Oklahoma', fips: '40', abbr: 'OK' },
  { name: 'Oregon', fips: '41', abbr: 'OR' }, { name: 'Pennsylvania', fips: '42', abbr: 'PA' },
  { name: 'Rhode Island', fips: '44', abbr: 'RI' }, { name: 'South Carolina', fips: '45', abbr: 'SC' },
  { name: 'South Dakota', fips: '46', abbr: 'SD' }, { name: 'Tennessee', fips: '47', abbr: 'TN' },
  { name: 'Texas', fips: '48', abbr: 'TX' }, { name: 'Utah', fips: '49', abbr: 'UT' },
  { name: 'Vermont', fips: '50', abbr: 'VT' }, { name: 'Virginia', fips: '51', abbr: 'VA' },
  { name: 'Washington', fips: '53', abbr: 'WA' }, { name: 'West Virginia', fips: '54', abbr: 'WV' },
  { name: 'Wisconsin', fips: '55', abbr: 'WI' }, { name: 'Wyoming', fips: '56', abbr: 'WY' },
];

interface Props {
  districtResults: Record<string, DistrictResult[]>;
  districtCountyMap: Record<string, string[]>;
  wyoming: 'double' | 'triple';
  /** state FIPS, or 'national' for the whole map */
  selectedFips: string;
  onSelectFips: (fips: string) => void;
}

export function HouseMap({ districtResults, districtCountyMap, wyoming, selectedFips, onSelectFips }: Props) {
  const abbrToFips = useMemo(
    () => Object.fromEntries(US_STATES.map(s => [s.abbr, s.fips])), [],
  );
  const stateEntry = US_STATES.find(s => s.fips === selectedFips);
  const districts  = stateEntry ? (districtResults[stateEntry.fips] ?? []) : [];

  // Multi-select rather than the grid's one-at-a-time, so a coalition can be assembled
  // and read as a single footprint.
  const [highlight, setHighlight] = useState<ReadonlySet<string>>(new Set());
  const toggleParty = (p: string) => setHighlight(prev => {
    const next = new Set(prev);
    if (!next.delete(p)) next.add(p);
    return next;
  });

  const seatTotals = useMemo(() => {
    const per: Record<string, number> = {};
    let all = 0;
    for (const rows of Object.values(districtResults)) {
      for (const d of rows) for (const p of d.elected) { per[p] = (per[p] ?? 0) + 1; all++; }
    }
    return { per, all };
  }, [districtResults]);

  const picked = F5_ORDER.filter(p => highlight.has(p));
  const pickedSeats = picked.reduce((s, p) => s + (seatTotals.per[p] ?? 0), 0);
  const majority = Math.floor(seatTotals.all / 2) + 1;

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* The legend doubles as the highlight control — the party names are already
            here, so a separate row of the same names would just be the list twice.
            F5_ORDER, not the colour table: that also carries DEM/IND/REP for the
            current-party comparisons, which have no seats on this map, and it holds OAO
            out of ideological sequence. */}
        <div className="flex flex-wrap gap-x-3 gap-y-1 items-center">
          {F5_ORDER.map(party => {
            const on = highlight.has(party);
            const off = highlight.size > 0 && !on;
            return (
              <button
                key={party}
                onClick={() => toggleParty(party)}
                aria-pressed={on}
                title={`Highlight ${PARTY_NAMES[party]} — ${seatTotals.per[party] ?? 0} seats`}
                className="flex items-center gap-1 text-xs font-semibold rounded px-1 -mx-1 py-0.5 transition-opacity hover:bg-slate-100"
                style={{ color: PARTY_COLORS[party], opacity: off ? 0.4 : 1 }}
              >
                <span
                  className="w-2.5 h-2.5 rounded-sm"
                  style={{
                    backgroundColor: on || !highlight.size ? PARTY_COLORS[party] : 'transparent',
                    boxShadow: `inset 0 0 0 1.5px ${PARTY_COLORS[party]}`,
                  }}
                />
                {PARTY_NAMES[party]}
              </button>
            );
          })}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <label className="text-xs font-semibold text-muted-foreground">State:</label>
          <select
            value={selectedFips}
            onChange={e => onSelectFips(e.target.value)}
            className="text-sm border border-border rounded px-2 py-1 bg-white text-foreground"
          >
            <option value="national">All states</option>
            {US_STATES.map(s => (
              <option key={s.fips} value={s.fips}>{s.name}</option>
            ))}
          </select>
        </div>
      </div>

      {picked.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="text-muted-foreground">Highlighted:</span>
          {picked.map(p => (
            <span key={p} className="font-bold px-1.5 py-0.5 rounded chip-text"
              style={{ backgroundColor: PARTY_COLORS[p], color: getContrastText(PARTY_COLORS[p]) }}>
              {p} {seatTotals.per[p] ?? 0}
            </span>
          ))}
          <span className="tabular-nums font-semibold text-foreground">
            {pickedSeats} of {seatTotals.all} seats ({(pickedSeats / seatTotals.all * 100).toFixed(1)}%)
          </span>
          <span className={pickedSeats >= majority ? 'text-emerald-700 font-semibold' : 'text-muted-foreground'}>
            {pickedSeats >= majority
              ? `majority, +${pickedSeats - majority}`
              : `${majority - pickedSeats} short of ${majority}`}
          </span>
          <button onClick={() => setHighlight(new Set())}
            className="px-2 py-0.5 rounded border border-border text-muted-foreground hover:bg-slate-100">
            clear
          </button>
        </div>
      )}

      <HexCartogram
        wyoming={wyoming}
        districtResults={districtResults}
        highlight={highlight}
        selected={stateEntry?.abbr ?? null}
        onSelectState={abbr => onSelectFips(
          abbrToFips[abbr] === selectedFips ? 'national' : (abbrToFips[abbr] ?? 'national'),
        )}
        footnote={
          <>One hexagon is one seat, filled with the party that won it. Heavy outlines
          separate districts; states are scaled so area tracks population. Click a state
          to zoom, click it again to zoom back out.</>
        }
      />

      {/* District cards for selected state */}
      {stateEntry && districts.length > 0 && (() => {
        // Aggregate seat counts across all districts in the selected state
        const stateTotals: Record<string, number> = {};
        for (const d of districts) {
          for (const p of d.elected) stateTotals[p] = (stateTotals[p] ?? 0) + 1;
        }
        const stateTotal = Object.values(stateTotals).reduce((s, n) => s + n, 0);
        const orderedState = F5_ORDER.filter(p => stateTotals[p]);

        return (
        <div>
          <div className="flex items-center justify-between mb-1">
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
              Districts — {stateEntry.name}
            </h4>
            <span className="text-xs text-muted-foreground">{stateTotal} seats total</span>
          </div>

          {/* State-level summary bar */}
          <div className="mb-4">
            <div className="flex rounded overflow-hidden h-7">
              {orderedState.map(p => {
                const pct = (stateTotals[p] / stateTotal) * 100;
                return (
                  <div
                    key={p}
                    title={`${PARTY_NAMES[p] ?? p}: ${stateTotals[p]} seats (${pct.toFixed(1)}%)`}
                    className="flex items-center justify-center overflow-hidden"
                    style={{ width: `${pct}%`, backgroundColor: PARTY_COLORS[p] ?? '#6b7280', minWidth: pct < 4 ? 2 : 0 }}
                  >
                    {pct >= 8 && (
                      <span className="text-xs font-bold leading-none px-0.5 chip-text" style={{ color: getContrastText(PARTY_COLORS[p] ?? '#6b7280') }}>
                        {p} {stateTotals[p]}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
            <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1">
              {orderedState.map(p => (
                <span key={p} className="text-xs tabular-nums" style={{ color: PARTY_COLORS[p] ?? '#6b7280' }}>
                  {p} {stateTotals[p]} ({((stateTotals[p] / stateTotal) * 100).toFixed(0)}%)
                </span>
              ))}
            </div>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {districts.map(d => {
              const tierColor = TIER_COLORS[d.densityTier] ?? '#6b7280';
              return (
                <Card
                  key={d.districtId}
                  className="p-3 space-y-2"
                  style={{ borderColor: tierColor + '44', backgroundColor: tierColor + '08' }}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold px-1.5 py-0.5 rounded chip-text" style={{ backgroundColor: tierColor, color: getContrastText(tierColor) }}>
                      {TIER_LABELS[d.densityTier] ?? d.densityTier}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {d.seatCount} seats · {d.nRespondents} resp.
                      {/* A district can hold seats without holding any counties: Maricopa's
                          population justifies ~11.6 seats but the whole-county draw gives all of it
                          to 04-01, so 04-03 has no footprint and is counted on the statewide pool.
                          Say so rather than letting the respondent count imply a local electorate. */}
                      {(districtCountyMap[d.districtId] ?? []).length === 0 && (
                        <span className="ml-1 italic" title={
                          'This district holds no counties of its own — the whole-county draw assigned '
                          + 'them all to its neighbours. Its members are elected from the statewide pool, '
                          + 'so the respondent count above is the state total, not this district.'
                        }>· statewide pool</span>
                      )}
                    </span>
                  </div>
                  {/* Seat bar */}
                  <div className="flex rounded-sm overflow-hidden h-4">
                    {F5_ORDER.filter(p => d.elected.includes(p)).map(p => {
                      const cnt = d.elected.filter(x => x === p).length;
                      const pct = (cnt / d.seatCount) * 100;
                      return (
                        <div
                          key={p}
                          title={`${PARTY_NAMES[p] ?? p}: ${cnt}`}
                          style={{ width: `${pct}%`, backgroundColor: PARTY_COLORS[p] ?? '#6b7280' }}
                        />
                      );
                    })}
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {[...d.elected]
                      .sort((a, b) => F5_ORDER.indexOf(a as typeof F5_ORDER[number]) - F5_ORDER.indexOf(b as typeof F5_ORDER[number]))
                      .map((party, i) => (
                        <span
                          key={i}
                          className="text-xs font-bold px-1.5 py-0.5 rounded chip-text"
                          style={{ backgroundColor: PARTY_COLORS[party] ?? '#6b7280', color: getContrastText(PARTY_COLORS[party] ?? '#6b7280') }}
                          title={PARTY_NAMES[party] ?? party}
                        >
                          {party}
                        </span>
                      ))}
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
        );
      })()}
      {stateEntry && districts.length === 0 && (
        <p className="text-xs text-muted-foreground italic">No district data for {stateEntry.name}.</p>
      )}
    </div>
  );
}
