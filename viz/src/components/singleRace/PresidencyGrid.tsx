import type { ECResult, ECStateResult } from '../../lib/singleRace';
import { getContrastText, lightenHex } from '../../constants/parties';
import { CHART_TYPE } from '../../constants/typography';

// Grid [row, col] cartogram — matches the presidency simulator layout.
const STATE_GRID: Record<string, [number, number]> = {
  AK: [0, 0], ME: [0, 12],
  WA: [1, 2], MT: [1, 3], ND: [1, 4], MN: [1, 5], WI: [1, 6], MI: [1, 7], NY: [1, 9], VT: [1, 10], NH: [1, 11],
  OR: [2, 2], ID: [2, 3], SD: [2, 4], IA: [2, 5], IN: [2, 6], OH: [2, 7], PA: [2, 8], NJ: [2, 9], MA: [2, 10], RI: [2, 11],
  CA: [3, 1], NV: [3, 3], WY: [3, 4], NE: [3, 5], IL: [3, 6], KY: [3, 7], WV: [3, 8], MD: [3, 9], CT: [3, 10], DE: [3, 11],
  UT: [4, 3], CO: [4, 4], KS: [4, 5], MO: [4, 6], TN: [4, 7], VA: [4, 8], DC: [4, 9],
  AZ: [5, 2], NM: [5, 3], OK: [5, 4], AR: [5, 5], MS: [5, 6], AL: [5, 7], NC: [5, 8], SC: [5, 9],
  HI: [6, 1], TX: [6, 3], LA: [6, 5], GA: [6, 7], FL: [6, 8],
};

const CELL = 60;
const GAP = 4;
const ROWS = 7;
const COLS = 13;

interface Props {
  ec: ECResult;
  aColor: string;
  bColor: string;
}

export function PresidencyGrid({ ec, aColor, bColor }: Props) {
  const byAbbr: Record<string, ECStateResult> = {};
  for (const s of ec.states) byAbbr[s.abbr] = s;
  const width = COLS * (CELL + GAP);
  const height = ROWS * (CELL + GAP);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto" role="img" aria-label="Electoral college map">
      {Object.entries(STATE_GRID).map(([abbr, [row, col]]) => {
        const s = byAbbr[abbr];
        if (!s) return null;
        const base = s.winner === 'A' ? aColor : bColor;
        const fill = lightenHex(base, 0.15);
        const txt = getContrastText(fill);
        const x = col * (CELL + GAP);
        const y = row * (CELL + GAP);
        const label = s.split ? `${s.evA}–${s.evB}` : String(s.ev);
        return (
          <g key={abbr}>
            <rect x={x} y={y} width={CELL} height={CELL} rx={4} fill={fill} stroke="#fff" strokeWidth={1.5} />
            <text x={x + CELL / 2} y={y + CELL / 2 - 4} textAnchor="middle" fontSize={CHART_TYPE.stateLabel} fontWeight={700} fill={txt}>{abbr}</text>
            <text x={x + CELL / 2} y={y + CELL / 2 + 13} textAnchor="middle" fontSize={CHART_TYPE.cellValue} fill={txt} opacity={0.9}>{label}</text>
          </g>
        );
      })}
    </svg>
  );
}
