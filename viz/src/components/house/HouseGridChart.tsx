import { useMemo, useState } from 'react';
import { PARTY_COLORS, F5_ORDER_WFP as F5_ORDER } from '../../constants/parties';
import type { HouseStateEntry, DistrictResult } from '../../types';

interface Props {
  stateMap: Record<string, HouseStateEntry>;
  districtResults: Record<string, DistrictResult[]>;
}

// Geographic grid [row, col]
const STATE_GRID: Record<string, [number, number]> = {
  AK: [0,0],
  WA: [1,2], MT: [1,3], ND: [1,4], MN: [1,5], WI: [1,6], MI: [1,7], NY: [1,9], VT: [1,10], NH: [1,11], ME: [1,12],
  OR: [2,2], ID: [2,3], SD: [2,4], IA: [2,5], IN: [2,6], OH: [2,7], PA: [2,8], NJ: [2,9], MA: [2,10], RI: [2,11],
  CA: [3,1], NV: [3,3], WY: [3,4], NE: [3,5], IL: [3,6], KY: [3,7], WV: [3,8], MD: [3,9], CT: [3,10], DE: [3,11],
             UT: [4,3], CO: [4,4], KS: [4,5], MO: [4,6], TN: [4,7], VA: [4,8], DC: [4,9],
  AZ: [5,2], NM: [5,3], OK: [5,4], AR: [5,5], MS: [5,6], AL: [5,7], NC: [5,8], SC: [5,9],
  HI: [6,1],            TX: [6,3], LA: [6,5],             GA: [6,7], FL: [6,8],
};

const FIPS_TO_ABBR: Record<string, string> = {
  '01':'AL','02':'AK','04':'AZ','05':'AR','06':'CA','08':'CO','09':'CT','10':'DE','11':'DC',
  '12':'FL','13':'GA','15':'HI','16':'ID','17':'IL','18':'IN','19':'IA','20':'KS','21':'KY',
  '22':'LA','23':'ME','24':'MD','25':'MA','26':'MI','27':'MN','28':'MS','29':'MO','30':'MT',
  '31':'NE','32':'NV','33':'NH','34':'NJ','35':'NM','36':'NY','37':'NC','38':'ND','39':'OH',
  '40':'OK','41':'OR','42':'PA','44':'RI','45':'SC','46':'SD','47':'TN','48':'TX','49':'UT',
  '50':'VT','51':'VA','53':'WA','54':'WV','55':'WI','56':'WY',
};

const ABBR_TO_FIPS: Record<string, string> = Object.fromEntries(
  Object.entries(FIPS_TO_ABBR).map(([fips, abbr]) => [abbr, fips])
);

const TIER_ORDER = ['URBAN', 'SUBURBAN', 'RURAL'];

// Seat square geometry
const SQ      = 8;   // square side length
const SQ_GAP  = 1;   // gap between squares in a row
const DIST_GAP = 3;  // gap between district rows
const LABEL_H = 11;  // state label height
const PAD     = 3;   // cell padding
const COL_GAP = 6;   // gap between grid columns
const ROW_GAP = 6;   // gap between grid rows

function cellWidth(maxDistSeats: number): number {
  return maxDistSeats * (SQ + SQ_GAP) - SQ_GAP + PAD * 2;
}
function cellHeight(numDists: number): number {
  return numDists * SQ + Math.max(0, numDists - 1) * DIST_GAP + LABEL_H + PAD * 2;
}

export function HouseGridChart({ stateMap, districtResults }: Props) {
  const [activeParty, setActiveParty] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<string | null>(null);

  const byAbbr: Record<string, HouseStateEntry> = {};
  for (const [fips, entry] of Object.entries(stateMap)) {
    byAbbr[FIPS_TO_ABBR[fips] ?? entry.stateAbbr] = entry;
  }

  // Pre-compute sorted districts and cell dimensions per state
  const stateData = useMemo(() => {
    const out: Record<string, { dists: DistrictResult[], cw: number, ch: number }> = {};
    for (const abbr of Object.keys(STATE_GRID)) {
      const fips  = ABBR_TO_FIPS[abbr];
      const dists = [...((fips ? districtResults[fips] : undefined) ?? [])].sort(
        (a, b) => TIER_ORDER.indexOf(a.densityTier) - TIER_ORDER.indexOf(b.densityTier)
      );
      const maxSeats = dists.length ? Math.max(...dists.map(d => d.seatCount)) : 1;
      out[abbr] = {
        dists,
        cw: cellWidth(maxSeats),
        ch: cellHeight(Math.max(1, dists.length)),
      };
    }
    return out;
  }, [districtResults]);

  // Parties actually present across states (so the highlight legend only lists real parties).
  const presentParties = useMemo(() => {
    const s = new Set<string>();
    for (const e of Object.values(stateMap)) for (const p of Object.keys(e.seats ?? {})) s.add(p);
    return s;
  }, [stateMap]);

  const maxRow = Math.max(...Object.values(STATE_GRID).map(([r]) => r));
  const maxCol = Math.max(...Object.values(STATE_GRID).map(([, c]) => c));

  // Column widths = max cell width of states in each column
  const colWidths: number[] = Array(maxCol + 1).fill(0);
  for (const [abbr, [, col]] of Object.entries(STATE_GRID)) {
    colWidths[col] = Math.max(colWidths[col], stateData[abbr]?.cw ?? 0);
  }
  // Column x-offsets
  const colX: number[] = [];
  let xAcc = 0;
  for (let c = 0; c <= maxCol; c++) {
    colX[c] = xAcc;
    xAcc += colWidths[c] + COL_GAP;
  }

  // Row heights = max cell height of states in each row
  const rowHeights: number[] = Array(maxRow + 1).fill(0);
  for (const [abbr, [row]] of Object.entries(STATE_GRID)) {
    rowHeights[row] = Math.max(rowHeights[row], stateData[abbr]?.ch ?? 0);
  }
  // Row y-offsets
  const rowY: number[] = [];
  let yAcc = 0;
  for (let r = 0; r <= maxRow; r++) {
    rowY[r] = yAcc;
    yAcc += rowHeights[r] + ROW_GAP;
  }

  const totalW = xAcc - COL_GAP;
  const totalH = yAcc - ROW_GAP;

  return (
    <div>
      {/* Party highlight filter */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        <span className="text-xs text-muted-foreground self-center mr-1">Highlight:</span>
        {F5_ORDER.filter(p => presentParties.has(p)).map(p => (
          <button
            key={p}
            onClick={() => setActiveParty(activeParty === p ? null : p)}
            className="text-xs px-2 py-0.5 rounded border transition-all"
            style={{
              borderColor: PARTY_COLORS[p],
              color: activeParty === p ? 'white' : PARTY_COLORS[p],
              backgroundColor: activeParty === p ? PARTY_COLORS[p] : 'transparent',
              opacity: activeParty && activeParty !== p ? 0.35 : 1,
            }}
          >
            {p}
          </button>
        ))}
        {activeParty && (
          <button
            onClick={() => setActiveParty(null)}
            className="text-xs px-2 py-0.5 rounded border border-slate-300 text-muted-foreground"
          >
            clear
          </button>
        )}
      </div>

      <div className="h-8 mb-1">
        {tooltip && (
          <div className="text-sm text-foreground bg-white border border-border rounded px-3 py-1.5 shadow-sm inline-block">
            {tooltip}
          </div>
        )}
      </div>

      <div className="overflow-x-auto">
        <svg
          viewBox={`0 0 ${totalW} ${totalH}`}
          style={{ width: '100%', minWidth: 700 }}
        >
          {Object.entries(STATE_GRID).map(([abbr, [row, col]]) => {
            const { dists, cw, ch } = stateData[abbr];
            const entry = byAbbr[abbr];
            if (!entry && dists.length === 0) return null;

            // Center cell within its column/row slot
            const cx = colX[col] + Math.floor((colWidths[col] - cw) / 2);
            const cy = rowY[row] + Math.floor((rowHeights[row] - ch) / 2);

            const pluralityParty = dists[0]?.elected[0] ?? entry?.pluralityParty ?? '';
            const labelColor = activeParty
              ? '#94a3b8'
              : (PARTY_COLORS[pluralityParty] ?? '#64748b');

            return (
              <g key={abbr}>
                {/* Cell background */}
                <rect
                  x={cx} y={cy} width={cw} height={ch}
                  fill={(PARTY_COLORS[pluralityParty] ?? '#64748b') + '08'}
                  stroke={(PARTY_COLORS[pluralityParty] ?? '#64748b') + '22'}
                  strokeWidth={0.8}
                  rx={2}
                />

                {/* District rows — one per district, sorted urban→suburban→rural */}
                {dists.map((dist, di) => {
                  const distY = cy + PAD + di * (SQ + DIST_GAP);
                  // Sort seats by F5_ORDER for consistent left-to-right coloring
                  const seats = [...dist.elected].sort(
                    (a, b) => F5_ORDER.indexOf(a as typeof F5_ORDER[number]) - F5_ORDER.indexOf(b as typeof F5_ORDER[number])
                  );
                  const counts: Record<string, number> = {};
                  for (const p of dist.elected) counts[p] = (counts[p] ?? 0) + 1;

                  return (
                    <g
                      key={dist.districtId}
                      style={{ cursor: 'pointer' }}
                      onMouseEnter={() => {
                        const s = F5_ORDER.filter(p => counts[p])
                          .map(p => `${p}:${counts[p]}`).join(' · ');
                        setTooltip(`${abbr} ${dist.densityTier} (${dist.seatCount}s) — ${s}`);
                      }}
                      onMouseLeave={() => setTooltip(null)}
                    >
                      {seats.map((party, si) => (
                        <rect
                          key={si}
                          x={cx + PAD + si * (SQ + SQ_GAP)}
                          y={distY}
                          width={SQ}
                          height={SQ}
                          fill={PARTY_COLORS[party] ?? '#6b7280'}
                          opacity={!activeParty || party === activeParty ? 0.88 : 0.06}
                          rx={1}
                        />
                      ))}
                    </g>
                  );
                })}

                {/* State abbreviation */}
                <text
                  x={cx + cw / 2}
                  y={cy + ch - 2}
                  textAnchor="middle"
                  fontSize={8}
                  fontWeight={600}
                  fill={labelColor}
                >
                  {abbr}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <p className="text-xs text-muted-foreground mt-2 text-center">
        Each square = one STV seat · rows = districts (urban → suburban → rural) · cell size ∝ state representation · click a party to see its geographic reach
      </p>
    </div>
  );
}
