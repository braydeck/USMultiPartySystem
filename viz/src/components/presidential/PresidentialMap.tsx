import { useState, useMemo } from 'react';
import { getBlendColor, F5_ORDER, getPrimaryParty, buildDisplayLabels, getContrastText } from '../../constants/parties';
import type { PresidentialStateWinner, HouseStateEntry } from '../../types';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

// Geographic grid [row, col] — matches good_governance_trap layout
const STATE_GRID: Record<string, [number, number]> = {
  AK: [0,0],                                                                                       ME: [0,12],
  WA: [1,2], MT: [1,3], ND: [1,4], MN: [1,5], WI: [1,6], MI: [1,7], NY: [1,9], VT: [1,10], NH: [1,11],
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
  Object.entries(FIPS_TO_ABBR).map(([f, a]) => [a, f])
);

type MapMode = 'irv' | 'plurality' | 'condorcet';

const TOTAL_SENATORS = 102; // 51 states × 2

interface Props {
  stateWinners: Record<string, PresidentialStateWinner>;
  stateMap?: Record<string, HouseStateEntry>;
}

// ── EC vote calculator ────────────────────────────────────────────────────────

function computeEC(
  stateWinners: Record<string, PresidentialStateWinner>,
  houseSeats: Record<string, number>,
  winnerFn: (sw: PresidentialStateWinner) => string,
  labels: Record<string, string>,
) {
  // Tally by display label so simplified codes group correctly
  const tally: Record<string, { code: string; states: number; evs: number; stateList: string[] }> = {};
  let totalEV = 0;

  for (const [fips, sw] of Object.entries(stateWinners)) {
    const rawWinner = winnerFn(sw);
    const displayWinner = labels[rawWinner] ?? rawWinner;
    const house = houseSeats[fips] ?? 0;
    const ev = house + 2;
    totalEV += ev;
    if (!tally[displayWinner]) tally[displayWinner] = { code: rawWinner, states: 0, evs: 0, stateList: [] };
    tally[displayWinner].states += 1;
    tally[displayWinner].evs += ev;
    tally[displayWinner].stateList.push(sw.stateAbbr);
  }

  const needed = Math.floor(totalEV / 2) + 1;
  const sorted = Object.entries(tally).sort((a, b) => b[1].evs - a[1].evs);
  const ecWinner = sorted.find(([, t]) => t.evs >= needed);

  return { tally: sorted, totalEV, needed, ecWinner: ecWinner?.[0] ?? null };
}

// ── National Share Bar ───────────────────────────────────────────────────────

function NationalShareBar({
  shares,
  labels,
}: {
  shares: { code: string; pct: number }[];
  labels: Record<string, string>;
}) {
  if (shares.length === 0) return null;
  const leader = shares[0];
  const leaderLabel = labels[leader.code] ?? leader.code;

  return (
    <div>
      {/* Winner callout */}
      <div className="text-sm mb-2">
        <span className="font-bold" style={{ color: getBlendColor(leader.code) }}>
          {leaderLabel}
        </span>
        <span className="text-foreground"> leads with </span>
        <span className="font-bold">{(leader.pct * 100).toFixed(1)}%</span>
        <span className="text-muted-foreground"> of the first-choice vote</span>
      </div>

      {/* 100% stacked bar */}
      <div className="flex rounded overflow-hidden h-8 mb-2">
        {shares.map(({ code, pct }) => {
          const w = pct * 100;
          const color = getBlendColor(code);
          return (
            <div
              key={code}
              className="flex items-center justify-center overflow-hidden"
              style={{ width: `${w}%`, backgroundColor: color, minWidth: w < 2 ? 2 : 0 }}
              title={`${labels[code] ?? code}: ${(pct * 100).toFixed(1)}%`}
            >
              {w > 6 && (
                <span className="text-xs font-bold px-0.5 truncate chip-text"
                  style={{ color: getContrastText(color), textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}>
                  {labels[code] ?? code} {(pct * 100).toFixed(1)}%
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Proportional Vote Cartogram ──────────────────────────────────────────────

const CELL_W = 64;
const CELL_H = 36;
const GAP = 4;

function ProportionalCartogram({
  stateWinners,
  houseSeats,
  labels,
}: {
  stateWinners: Record<string, PresidentialStateWinner>;
  houseSeats: Record<string, number>;
  labels: Record<string, string>;
}) {
  const [hoverAbbr, setHoverAbbr] = useState<string | null>(null);

  const maxRow = Math.max(...Object.values(STATE_GRID).map(([r]) => r));
  const maxCol = Math.max(...Object.values(STATE_GRID).map(([, c]) => c));
  const totalW = (maxCol + 1) * (CELL_W + GAP) - GAP;
  const totalH = (maxRow + 1) * (CELL_H + GAP) - GAP;

  const hoverEntry = hoverAbbr ? stateWinners[ABBR_TO_FIPS[hoverAbbr]] : null;

  // Get all candidate codes in consistent order
  const allCandidates = useMemo(() => {
    const codes = new Set<string>();
    for (const sw of Object.values(stateWinners)) {
      for (const code of Object.keys(sw.shares)) codes.add(code);
    }
    return [...codes].sort((a, b) => {
      const rA = F5_ORDER.indexOf(getPrimaryParty(a) as typeof F5_ORDER[number]);
      const rB = F5_ORDER.indexOf(getPrimaryParty(b) as typeof F5_ORDER[number]);
      return (rA === -1 ? 99 : rA) - (rB === -1 ? 99 : rB);
    });
  }, [stateWinners]);

  return (
    <div className="flex gap-4">
      {/* Legend sidebar */}
      <div className="shrink-0 w-36">
        <div className="text-xs font-semibold text-foreground mb-2">
          {hoverAbbr ? (
            <>
              {hoverAbbr}
              <span className="font-normal text-muted-foreground"> · {(houseSeats[ABBR_TO_FIPS[hoverAbbr]] ?? 0) + 2} EV</span>
            </>
          ) : (
            <span className="text-muted-foreground">Hover a state</span>
          )}
        </div>
        <div className="space-y-1">
          {allCandidates.map(code => {
            const color = getBlendColor(code);
            const share = hoverEntry?.shares[code];
            return (
              <div key={code} className="flex items-center gap-1.5">
                <span
                  className="text-[10px] font-bold px-1.5 py-0.5 rounded leading-none shrink-0 chip-text"
                  style={{ backgroundColor: color, color: getContrastText(color) }}
                >
                  {labels[code] ?? code}
                </span>
                <span className="text-xs tabular-nums text-foreground font-medium">
                  {share !== undefined ? `${(share * 100).toFixed(1)}%` : <span className="text-muted-foreground">—</span>}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Grid map */}
      <div className="flex-1 overflow-x-auto min-w-0">
        <svg viewBox={`0 0 ${totalW} ${totalH}`} style={{ width: '100%', minWidth: 550 }}>
          {Object.entries(STATE_GRID).map(([abbr, [row, col]]) => {
            const fips = ABBR_TO_FIPS[abbr];
            const sw = stateWinners[fips];
            if (!sw) return null;

            const x = col * (CELL_W + GAP);
            const y = row * (CELL_H + GAP);

            const sorted = Object.entries(sw.shares).sort((a, b) => {
              const rA = F5_ORDER.indexOf(getPrimaryParty(a[0]) as typeof F5_ORDER[number]);
              const rB = F5_ORDER.indexOf(getPrimaryParty(b[0]) as typeof F5_ORDER[number]);
              return (rA === -1 ? 99 : rA) - (rB === -1 ? 99 : rB);
            });

            let cum = 0;
            const isHovered = hoverAbbr === abbr;

            return (
              <g
                key={abbr}
                onMouseEnter={() => setHoverAbbr(abbr)}
                onMouseLeave={() => setHoverAbbr(null)}
                style={{ cursor: 'pointer' }}
              >
                <rect
                  x={x} y={y} width={CELL_W} height={CELL_H}
                  fill="white"
                  stroke={isHovered ? '#1e293b' : '#e2e8f0'}
                  strokeWidth={isHovered ? 1.5 : 0.8}
                  rx={3}
                />
                {sorted.map(([code, share]) => {
                  const barX = x + 2 + cum * (CELL_W - 4);
                  const barW = share * (CELL_W - 4);
                  cum += share;
                  return (
                    <rect
                      key={code}
                      x={barX} y={y + 14} width={Math.max(0.5, barW)} height={CELL_H - 18}
                      fill={getBlendColor(code)}
                      opacity={0.8}
                      rx={1}
                    />
                  );
                })}
                <text
                  x={x + CELL_W / 2} y={y + 11}
                  textAnchor="middle" fontSize={9} fontWeight={600}
                  fill={isHovered ? '#0f172a' : '#64748b'}
                >
                  {abbr}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}

// ── Winner Map (Cartogram) ───────────────────────────────────────────────────

function WinnerCartogram({
  stateWinners,
  houseSeats,
  mode,
  labels,
}: {
  stateWinners: Record<string, PresidentialStateWinner>;
  houseSeats: Record<string, number>;
  mode: MapMode;
  labels: Record<string, string>;
}) {
  const [hoverAbbr, setHoverAbbr] = useState<string | null>(null);
  const [hoverBar, setHoverBar] = useState<string | null>(null);

  const winnerFn = (sw: PresidentialStateWinner): string => {
    if (mode === 'irv') return sw.winner;
    if (mode === 'condorcet') return sw.condorcetWinner;
    // plurality = highest first-choice share
    const sorted = Object.entries(sw.shares).sort((a, b) => b[1] - a[1]);
    return sorted[0]?.[0] ?? sw.winner;
  };

  const ec = useMemo(
    () => computeEC(stateWinners, houseSeats, winnerFn, labels),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [stateWinners, houseSeats, mode, labels],
  );

  const maxRow = Math.max(...Object.values(STATE_GRID).map(([r]) => r));
  const maxCol = Math.max(...Object.values(STATE_GRID).map(([, c]) => c));
  const totalW = (maxCol + 1) * (CELL_W + GAP) - GAP;
  const totalH = (maxRow + 1) * (CELL_H + GAP) - GAP;

  const hoverFips = hoverAbbr ? ABBR_TO_FIPS[hoverAbbr] : null;
  const hoverEntry = hoverFips ? stateWinners[hoverFips] : null;

  return (
    <div>
      {/* EC outcome banner */}
      <div className={`rounded-lg px-4 py-3 mb-3 text-sm ${ec.ecWinner ? 'bg-green-50 border border-green-200' : 'bg-amber-50 border border-amber-200'}`}>
        {ec.ecWinner ? (
          <div>
            <span className="font-bold" style={{ color: getBlendColor(ec.tally.find(([c]) => c === ec.ecWinner)?.[1].code ?? ec.ecWinner) }}>
              {ec.ecWinner}
            </span>
            <span className="text-foreground"> wins the Electoral College with </span>
            <span className="font-bold">{ec.tally.find(([c]) => c === ec.ecWinner)?.[1].evs} / {ec.totalEV}</span>
            <span className="text-muted-foreground"> EV ({ec.needed} needed)</span>
          </div>
        ) : (
          <div>
            <span className="font-semibold text-amber-800">No candidate reaches {ec.needed} EV</span>
            <span className="text-amber-700">: election goes to the House (each state gets one vote)</span>
          </div>
        )}
      </div>

      {/* EC tally bar with hover */}
      <div className="flex rounded overflow-hidden h-7 mb-3">
        {ec.tally.map(([displayCode, { code: rawCode, evs, states }]) => {
          const pct = (evs / ec.totalEV) * 100;
          const isBarHover = hoverBar === displayCode;
          return (
            <div
              key={displayCode}
              className="flex items-center justify-center overflow-hidden relative transition-opacity"
              style={{
                width: `${pct}%`,
                backgroundColor: getBlendColor(rawCode),
                minWidth: pct < 3 ? 2 : 0,
                opacity: hoverBar && !isBarHover ? 0.5 : 1,
              }}
              onMouseEnter={() => setHoverBar(displayCode)}
              onMouseLeave={() => setHoverBar(null)}
            >
              {pct >= 6 && (
                <span className="text-xs font-bold px-0.5 chip-text" style={{ color: getContrastText(getBlendColor(rawCode)) }}>
                  {isBarHover ? `${states} states` : `${displayCode} ${evs}`}
                </span>
              )}
              {pct < 6 && isBarHover && (
                <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-foreground text-white text-[10px] font-semibold px-2 py-1 rounded whitespace-nowrap z-10 pointer-events-none">
                  {displayCode}: {evs} EV · {states} states
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Hover tooltip */}
      <div className="h-7 mb-1">
        {hoverEntry && hoverAbbr && (
          <div className="text-sm text-foreground inline-block">
            <span className="font-semibold">{hoverAbbr}</span>
            <span className="text-muted-foreground"> · {(houseSeats[hoverFips!] ?? 0) + 2} EV · Winner: </span>
            <span className="font-bold" style={{ color: getBlendColor(winnerFn(hoverEntry)) }}>
              {labels[winnerFn(hoverEntry)] ?? winnerFn(hoverEntry)}
            </span>
          </div>
        )}
      </div>

      {/* Grid map */}
      <div className="overflow-x-auto">
        <svg viewBox={`0 0 ${totalW} ${totalH}`} style={{ width: '100%', minWidth: 600 }}>
          {Object.entries(STATE_GRID).map(([abbr, [row, col]]) => {
            const fips = ABBR_TO_FIPS[abbr];
            const sw = stateWinners[fips];
            if (!sw) return null;

            const x = col * (CELL_W + GAP);
            const y = row * (CELL_H + GAP);
            const winner = winnerFn(sw);
            const color = getBlendColor(winner);
            const ev = (houseSeats[fips] ?? 0) + 2;
            const isHovered = hoverAbbr === abbr;

            return (
              <g
                key={abbr}
                onMouseEnter={() => setHoverAbbr(abbr)}
                onMouseLeave={() => setHoverAbbr(null)}
                style={{ cursor: 'pointer' }}
              >
                <rect
                  x={x} y={y} width={CELL_W} height={CELL_H}
                  fill={color + '22'}
                  stroke={isHovered ? color : color + '66'}
                  strokeWidth={isHovered ? 2 : 1}
                  rx={3}
                />
                {/* State label */}
                <text
                  x={x + CELL_W / 2} y={y + 14}
                  textAnchor="middle" fontSize={10} fontWeight={700}
                  fill={color}
                >
                  {abbr}
                </text>
                {/* EV count */}
                <text
                  x={x + CELL_W / 2} y={y + CELL_H - 6}
                  textAnchor="middle" fontSize={8} fill="#94a3b8"
                >
                  {ev} EV
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────────────────────

export function PresidentialMap({ stateWinners, stateMap }: Props) {
  const [mapMode, setMapMode] = useState<MapMode>('irv');

  // Build display labels: simplify CON_1 → CON when no CON_2 exists
  const displayLabels = useMemo(() => {
    const codes = new Set<string>();
    for (const sw of Object.values(stateWinners)) {
      codes.add(sw.winner);
      codes.add(sw.condorcetWinner);
      for (const code of Object.keys(sw.shares)) codes.add(code);
    }
    return buildDisplayLabels(codes);
  }, [stateWinners]);

  // Build house seats per FIPS from stateMap prop
  const houseSeats = useMemo(() => {
    const out: Record<string, number> = {};
    if (stateMap) {
      for (const [fips, entry] of Object.entries(stateMap)) {
        out[fips] = entry.totalSeats;
      }
    }
    return out;
  }, [stateMap]);

  const totalHouseSeats = Object.values(houseSeats).reduce((s, n) => s + n, 0);
  const totalEV = totalHouseSeats + TOTAL_SENATORS;

  // National first-choice aggregation (weighted by respondents)
  const nationalShares = useMemo(() => {
    const totals: Record<string, number> = {};
    let totalResp = 0;
    for (const sw of Object.values(stateWinners)) {
      const n = sw.nRespondents;
      totalResp += n;
      for (const [code, share] of Object.entries(sw.shares)) {
        totals[code] = (totals[code] ?? 0) + share * n;
      }
    }
    if (totalResp === 0) return [];
    return Object.entries(totals)
      .map(([code, weighted]) => ({ code, pct: weighted / totalResp }))
      .sort((a, b) => b.pct - a.pct);
  }, [stateWinners]);

  return (
    <div className="space-y-6">
      {/* National FPTP Projection */}
      <Card className="p-4">
        <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
          National FPTP Projection
        </h4>
        <p className="text-xs text-muted-foreground mb-3">
          Who would win under current first-past-the-post rules with these candidates.
        </p>
        <NationalShareBar shares={nationalShares} labels={displayLabels} />
      </Card>

      {/* Proportional vote cartogram */}
      <Card className="p-4">
        <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
          State Vote Shares
        </h4>
        <p className="text-xs text-muted-foreground mb-3">
          First-choice vote proportions per state. Hover for breakdown.
        </p>
        <ProportionalCartogram stateWinners={stateWinners} houseSeats={houseSeats} labels={displayLabels} />
      </Card>

      {/* Winner maps */}
      <Card className="p-4">
        <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
          Election Results Without National Override
        </h4>
        <p className="text-xs text-muted-foreground mb-3">
          Who wins each state under different methods. EC = {totalEV} votes ({totalHouseSeats} House + {TOTAL_SENATORS} Senate). {Math.floor(totalEV / 2) + 1} needed to win.
        </p>
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">Method:</span>
          {([['irv', 'IRV'], ['plurality', 'Plurality'], ['condorcet', 'Condorcet']] as [MapMode, string][]).map(([v, label]) => (
            <Button
              key={v}
              onClick={() => setMapMode(v)}
              variant={mapMode === v ? 'default' : 'secondary'}
              size="sm"
            >
              {label}
            </Button>
          ))}
        </div>
        <WinnerCartogram stateWinners={stateWinners} houseSeats={houseSeats} mode={mapMode} labels={displayLabels} />
      </Card>
    </div>
  );
}
