import type { RCVRace } from '../../types';
import { CHART_TYPE, CHART_FILL, FOOTNOTE, CARD_HINT } from '../../constants/typography';
import { partyColor } from './ballotParties';
import { shortName } from './names';

/**
 * Every head-to-head matchup on the same ballots. A row that is green all the way
 * across is a Condorcet winner: preferred to each rival one-on-one.
 */

const CELL = 54;
const LABEL_W = 104;

export function CondorcetGrid({ race }: { race: RCVRace }) {
  if (race.condorcetAvailable === false) {
    return (
      <p className={CARD_HINT}>
        Maine published this contest&apos;s round-by-round tally but not its cast vote record, so
        head-to-head results cannot be computed. In the final pairing on continuing ballots,{' '}
        {race.irvWinner} led {race.irvRounds[race.irvRounds.length - 1].pcts[race.irvWinner].toFixed(1)}
        –{(100 - race.irvRounds[race.irvRounds.length - 1].pcts[race.irvWinner]).toFixed(1)}.
      </p>
    );
  }

  const cands = race.candidates.filter(c => race.condorcetMatrix[c]);
  if (!cands.length) return null;

  const w = LABEL_W + cands.length * CELL;
  const h = LABEL_W + cands.length * CELL + 4;
  const cw = race.condorcetWinner;

  return (
    <div className="space-y-1.5">
      <div className="overflow-x-auto">
        <svg viewBox={`0 0 ${w} ${h}`} style={{ width: '100%', maxWidth: w, height: 'auto' }}>
          {cands.map((cand, ci) => (
            <g key={`col-${cand}`} transform={`translate(${LABEL_W + ci * CELL + CELL / 2}, ${LABEL_W - 6}) rotate(-40)`}>
              <text
                textAnchor="start" fontSize={CHART_TYPE.smallTick}
                fill={cand === cw ? '#0f172a' : CHART_FILL.label}
                fontWeight={cand === cw ? 'bold' : 'normal'}
              >
                {shortName(cand)}
              </text>
            </g>
          ))}

          {cands.map((rowCand, ri) => (
            <g key={rowCand}>
              <rect
                x={LABEL_W - 8} y={LABEL_W + ri * CELL + CELL / 2 - 5}
                width={4} height={10} rx={2}
                fill={partyColor(race.parties[rowCand])}
              />
              <text
                x={LABEL_W - 14} y={LABEL_W + ri * CELL + CELL / 2 + 4}
                textAnchor="end" fontSize={CHART_TYPE.smallTick}
                fill={rowCand === cw ? '#0f172a' : CHART_FILL.label}
                fontWeight={rowCand === cw ? 'bold' : 'normal'}
              >
                {shortName(rowCand)}
              </text>
              {cands.map((colCand, ci) => {
                const x = LABEL_W + ci * CELL;
                const y = LABEL_W + ri * CELL;
                if (rowCand === colCand) {
                  return <rect key={colCand} x={x} y={y} width={CELL} height={CELL} fill="#f4f6f9" />;
                }
                const pct = race.condorcetMatrix[rowCand]?.[colCand] ?? 0.5;
                const wins = pct > 0.5;
                const intensity = Math.min(1, Math.abs(pct - 0.5) * 4);
                const fill = wins
                  ? `rgba(16,140,104,${0.14 + intensity * 0.5})`
                  : `rgba(190,70,60,${0.1 + intensity * 0.34})`;
                return (
                  <g key={colCand}>
                    <rect x={x} y={y} width={CELL} height={CELL} fill={fill} stroke="#fff" strokeWidth={1} />
                    <text
                      x={x + CELL / 2} y={y + CELL / 2 + 4} textAnchor="middle"
                      fontSize={CHART_TYPE.axisTick} fontWeight="bold"
                      fill={wins ? '#065f46' : '#8f2a22'}
                    >
                      {(pct * 100).toFixed(0)}%
                    </text>
                    <title>{rowCand} beats {colCand} on {(pct * 100).toFixed(1)}% of ballots that rank either</title>
                  </g>
                );
              })}
            </g>
          ))}
        </svg>
      </div>
      <p className={FOOTNOTE}>
        Each cell is the share of ballots ranking the row candidate above the column candidate.
        Green means the row wins that pairing.
        {cw && ` ${cw} wins every one.`}
      </p>
    </div>
  );
}
