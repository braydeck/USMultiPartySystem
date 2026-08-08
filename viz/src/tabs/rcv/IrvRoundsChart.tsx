import type { RCVRace } from '../../types';
import { CHART_TYPE, CHART_FILL, FOOTNOTE } from '../../constants/typography';
import { partyColor } from './ballotParties';
import { shortName } from './names';

/**
 * One stacked bar per counting round, with the majority line drawn once across all
 * of them. Reading down the bars shows where each eliminated candidate's ballots
 * went, and how much of the bar stops arriving at all as ballots exhaust.
 */

const W = 620;
const LABEL_W = 96;
const BAR_W = W - LABEL_W - 44;
const BAR_H = 26;
const GAP = 8;

export function IrvRoundsChart({ race }: { race: RCVRace }) {
  const rounds = race.irvRounds;
  if (!rounds.length) return null;

  const order = race.candidates;
  const startBallots = rounds[0].continuingBallots;
  const chartH = rounds.length * (BAR_H + GAP) + 14;

  return (
    <div className="space-y-1.5">
      <div className="overflow-x-auto">
        <svg viewBox={`0 0 ${W} ${chartH}`} style={{ width: '100%', height: 'auto', minWidth: 420 }}>
          {rounds.map((round, ri) => {
            const y = ri * (BAR_H + GAP);
            // Bars share one scale — the first round's continuing ballots — so the
            // bar visibly shortens as ballots exhaust instead of re-normalising.
            const scale = BAR_W / startBallots;
            let x = LABEL_W;
            const segs = order
              .filter(c => (round.totals[c] ?? 0) > 0)
              .map(c => {
                const w = (round.totals[c] ?? 0) * scale;
                const seg = { cand: c, x, w, pct: round.pcts[c] ?? 0 };
                x += w;
                return seg;
              });
            const eliminated = round.eliminated;

            return (
              <g key={ri}>
                <text x={0} y={y + BAR_H / 2 + 1} fontSize={CHART_TYPE.smallTick} fill={CHART_FILL.label}>
                  Round {round.round}
                </text>
                {eliminated.length > 0 && (
                  <text x={0} y={y + BAR_H / 2 + 11} fontSize={CHART_TYPE.inMark} fill={CHART_FILL.tick}>
                    −{eliminated.map(shortName).join(', ')}
                  </text>
                )}
                {segs.map(({ cand, x: sx, w, pct }) => {
                  const isOut = eliminated.includes(cand);
                  return (
                    <g key={cand}>
                      <rect
                        x={sx} y={y} width={Math.max(w, 1)} height={BAR_H}
                        fill={partyColor(race.parties[cand])}
                        opacity={isOut ? 0.4 : 0.92}
                        stroke="#fff"
                        strokeWidth={1}
                      >
                        <title>{cand}: {round.totals[cand].toLocaleString()} ({pct.toFixed(1)}%)</title>
                      </rect>
                      {w > 44 && (
                        <text
                          x={sx + w / 2} y={y + BAR_H / 2 + 3}
                          textAnchor="middle" fontSize={CHART_TYPE.inMark}
                          fill="#fff" fontWeight="bold"
                        >
                          {pct.toFixed(1)}%
                        </text>
                      )}
                    </g>
                  );
                })}
                {/* Exhausted remainder */}
                {(() => {
                  const used = segs.reduce((s, g) => s + g.w, 0);
                  const rest = BAR_W - used;
                  if (rest <= 1) return null;
                  return (
                    <rect x={LABEL_W + used} y={y} width={rest} height={BAR_H} fill="#e9ecf1">
                      <title>
                        {(startBallots - round.continuingBallots).toLocaleString()} ballots no longer counting
                      </title>
                    </rect>
                  );
                })()}
              </g>
            );
          })}

          {/* Majority of continuing ballots, per round */}
          {rounds.map((round, ri) => {
            const y = ri * (BAR_H + GAP);
            const x = LABEL_W + (round.continuingBallots / startBallots) * BAR_W * 0.5;
            return (
              <line
                key={`maj-${ri}`} x1={x} y1={y - 1} x2={x} y2={y + BAR_H + 1}
                stroke="#334155" strokeWidth={1.25} strokeDasharray="3 2"
              />
            );
          })}
          <text
            x={LABEL_W + BAR_W * 0.5} y={rounds.length * (BAR_H + GAP) + 9}
            textAnchor="middle" fontSize={CHART_TYPE.smallTick} fill={CHART_FILL.label}
          >
            majority of ballots still counting
          </text>
        </svg>
      </div>
      <p className={FOOTNOTE}>
        Bars share one scale, so the grey tail is ballots that stopped counting — {' '}
        {(startBallots - rounds[rounds.length - 1].continuingBallots).toLocaleString()} of{' '}
        {startBallots.toLocaleString()} by the final round.
      </p>
    </div>
  );
}
