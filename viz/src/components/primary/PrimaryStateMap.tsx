import { useState, useMemo } from 'react';
import { getBlendColor, F5_ORDER, getPrimaryParty, getContrastText } from '../../constants/parties';
import type { PrimaryStageShares, FDPrimaryData } from '../../types';

const STAGE_PODS: Record<string, Set<string>> = {
  After_Retail:     new Set(['Retail']),
  After_Pod_A:      new Set(['Retail', 'A']),
  After_Pod_C:      new Set(['Retail', 'A', 'C']),
  After_Pod_BD:     new Set(['Retail', 'A', 'B', 'C', 'D']),
};

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

const CELL_W = 64;
const CELL_H = 36;
const GAP = 4;

interface Props {
  stageShares: Record<string, PrimaryStageShares>;
  stage: string;
  primaryData: FDPrimaryData;
}

export function PrimaryStateMap({ stageShares, stage, primaryData }: Props) {
  const [hoverAbbr, setHoverAbbr] = useState<string | null>(null);
  const activePods = STAGE_PODS[stage] ?? new Set();

  // Surviving candidates at this stage, sorted by F5_ORDER then alpha
  const stageCandidates = useMemo(() => {
    return primaryData.candidates
      .filter(c => {
        const sd = c.stages[stage];
        return sd && (sd.status === 'surviving' || sd.status === 'elected');
      })
      .map(c => c.code)
      .sort((a, b) => {
        const rA = F5_ORDER.indexOf(getPrimaryParty(a) as typeof F5_ORDER[number]);
        const rB = F5_ORDER.indexOf(getPrimaryParty(b) as typeof F5_ORDER[number]);
        if (rA !== rB) return (rA === -1 ? 99 : rA) - (rB === -1 ? 99 : rB);
        return a.localeCompare(b);
      });
  }, [primaryData, stage]);

  const maxRow = Math.max(...Object.values(STATE_GRID).map(([r]) => r));
  const maxCol = Math.max(...Object.values(STATE_GRID).map(([, c]) => c));
  const totalW = (maxCol + 1) * (CELL_W + GAP) - GAP;
  const totalH = (maxRow + 1) * (CELL_H + GAP) - GAP;

  const hoverFips = hoverAbbr ? ABBR_TO_FIPS[hoverAbbr] : null;
  const hoverEntry = hoverFips ? stageShares[hoverFips] : null;
  const hoverActive = hoverEntry ? activePods.has(hoverEntry.pod) : false;
  const hoverShares = hoverActive ? hoverEntry?.stages[stage]?.shares : undefined;
  const hoverExhausted = hoverActive ? hoverEntry?.stages[stage]?.exhausted : undefined;

  return (
    <div className="flex gap-4">
      {/* Legend sidebar */}
      <div className="shrink-0 w-40">
        <div className="text-xs font-semibold text-foreground mb-2">
          {hoverAbbr && hoverEntry ? (
            <>
              {hoverAbbr}
              <span className="font-normal text-muted-foreground">
                {' '}· Pod {hoverEntry.pod}
                {!hoverActive && ' · votes later'}
              </span>
            </>
          ) : (
            <span className="text-muted-foreground">
              {stageCandidates.length} candidates · hover a state
            </span>
          )}
        </div>
        <div className="space-y-1">
          {stageCandidates.map(code => {
            const color = getBlendColor(code);
            const share = hoverShares?.[code];
            return (
              <div key={code} className="flex items-center gap-1.5">
                <span
                  className="text-[10px] font-bold px-1.5 py-0.5 rounded leading-none shrink-0 chip-text"
                  style={{ backgroundColor: color, color: getContrastText(color) }}
                >
                  {code}
                </span>
                <span className="text-xs tabular-nums text-foreground font-medium">
                  {share !== undefined ? `${(share * 100).toFixed(1)}%` : <span className="text-muted-foreground">—</span>}
                </span>
              </div>
            );
          })}
          {hoverExhausted !== undefined && hoverExhausted > 0 && (
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded leading-none shrink-0 bg-slate-300 text-white">
                EXH
              </span>
              <span className="text-xs tabular-nums text-muted-foreground font-medium">
                {(hoverExhausted * 100).toFixed(1)}%
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Grid map */}
      <div className="flex-1 overflow-x-auto min-w-0">
        <svg viewBox={`0 0 ${totalW} ${totalH}`} style={{ width: '100%', minWidth: 550 }}>
          {Object.entries(STATE_GRID).map(([abbr, [row, col]]) => {
            const fips = ABBR_TO_FIPS[abbr];
            const ss = stageShares[fips];

            const x = col * (CELL_W + GAP);
            const y = row * (CELL_H + GAP);
            const hasVoted = ss ? activePods.has(ss.pod) : false;
            const isHovered = hoverAbbr === abbr;

            if (!ss) {
              return (
                <g key={abbr}>
                  <rect x={x} y={y} width={CELL_W} height={CELL_H}
                    fill="#f8fafc" stroke="#e2e8f0" strokeWidth={0.8} rx={3} />
                  <text x={x + CELL_W / 2} y={y + CELL_H / 2 + 3}
                    textAnchor="middle" fontSize={9} fontWeight={600} fill="#cbd5e1">
                    {abbr}
                  </text>
                </g>
              );
            }

            if (!hasVoted) {
              return (
                <g
                  key={abbr}
                  onMouseEnter={() => setHoverAbbr(abbr)}
                  onMouseLeave={() => setHoverAbbr(null)}
                  style={{ cursor: 'pointer' }}
                >
                  <rect x={x} y={y} width={CELL_W} height={CELL_H}
                    fill={isHovered ? '#f1f5f9' : '#f8fafc'}
                    stroke={isHovered ? '#94a3b8' : '#e2e8f0'}
                    strokeWidth={isHovered ? 1.2 : 0.8} rx={3} />
                  <text x={x + CELL_W / 2} y={y + 11}
                    textAnchor="middle" fontSize={9} fontWeight={600} fill="#94a3b8">
                    {abbr}
                  </text>
                  <text x={x + CELL_W / 2} y={y + CELL_H - 6}
                    textAnchor="middle" fontSize={7} fill="#cbd5e1">
                    Pod {ss.pod}
                  </text>
                </g>
              );
            }

            // Active state — stacked bar from stage-specific shares
            const stageData = ss.stages[stage];
            if (!stageData) return null;

            const sorted = Object.entries(stageData.shares).sort((a, b) => {
              const rA = F5_ORDER.indexOf(getPrimaryParty(a[0]) as typeof F5_ORDER[number]);
              const rB = F5_ORDER.indexOf(getPrimaryParty(b[0]) as typeof F5_ORDER[number]);
              if (rA !== rB) return (rA === -1 ? 99 : rA) - (rB === -1 ? 99 : rB);
              return a[0].localeCompare(b[0]);
            });

            // Total includes exhausted — bar fills proportionally
            const totalShare = sorted.reduce((s, [, v]) => s + v, 0) + stageData.exhausted;
            let cum = 0;
            const barInner = CELL_W - 4;

            return (
              <g
                key={abbr}
                onMouseEnter={() => setHoverAbbr(abbr)}
                onMouseLeave={() => setHoverAbbr(null)}
                style={{ cursor: 'pointer' }}
              >
                <rect x={x} y={y} width={CELL_W} height={CELL_H}
                  fill="white"
                  stroke={isHovered ? '#1e293b' : '#e2e8f0'}
                  strokeWidth={isHovered ? 1.5 : 0.8} rx={3} />
                {sorted.map(([code, share]) => {
                  const barX = x + 2 + (cum / totalShare) * barInner;
                  const barW = (share / totalShare) * barInner;
                  cum += share;
                  return (
                    <rect key={code}
                      x={barX} y={y + 14} width={Math.max(0.5, barW)} height={CELL_H - 18}
                      fill={getBlendColor(code)} opacity={0.8} rx={1} />
                  );
                })}
                {stageData.exhausted > 0.005 && (() => {
                  const barX = x + 2 + (cum / totalShare) * barInner;
                  const barW = (stageData.exhausted / totalShare) * barInner;
                  return (
                    <rect
                      x={barX} y={y + 14} width={Math.max(0.5, barW)} height={CELL_H - 18}
                      fill="#cbd5e1" opacity={0.6} rx={1} />
                  );
                })()}
                <text x={x + CELL_W / 2} y={y + 11}
                  textAnchor="middle" fontSize={9} fontWeight={600}
                  fill={isHovered ? '#0f172a' : '#64748b'}>
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
