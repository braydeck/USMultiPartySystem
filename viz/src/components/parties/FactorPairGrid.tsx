import { useMemo, useState } from 'react';
import { PARTY_COLORS, PARTY_NAMES, FACTOR_LABELS, FACTOR_POLES, F5_ORDER } from '../../constants/parties';
import { CARD_HEADING, CARD_HINT, CHART_FILL, CHART_TYPE } from '../../constants/typography';
import { ELLIPSE_FACTORS, PARTY_ELLIPSES, pairEllipse } from '../../lib/partyOverlap';
import { Card } from '@/components/ui/card';

const SIZE = 260;
const PAD = { l: 30, r: 10, t: 10, b: 30 };
const PLOT = SIZE - PAD.l - PAD.r;

/** Every two-factor view of the four interpretable factors, one panel per pair. Each party is
 *  its 50% ellipse, rotated by the correlation between the two factors inside that party. Two
 *  parties that overlap in one panel and separate in another are told apart by the factor the
 *  overlapping panel leaves out. */
export function FactorPairGrid({ factors, selected }: {
  /** Factors in display order; pairs are built from it, so the first factor is on every top-row x-axis. */
  factors: readonly string[];
  /** Parties picked in the tab's selector. Emphasised, never filtered. */
  selected: readonly string[];
}) {
  const [hover, setHover] = useState<string | null>(null);
  const parties = F5_ORDER.filter(p => PARTY_ELLIPSES[p]);
  const focus = hover ? [hover] : selected.filter(p => PARTY_ELLIPSES[p]);
  const isDim = (p: string) => focus.length > 0 && !focus.includes(p);

  const pairs = useMemo(() => {
    const out: [string, string][] = [];
    for (let i = 0; i < factors.length; i++) for (let j = i + 1; j < factors.length; j++) out.push([factors[i], factors[j]]);
    return out;
  }, [factors]);

  // One symmetric domain for every panel, so an ellipse's size means the same thing in all six.
  const extent = useMemo(() => {
    let m = 0;
    for (const p of parties) {
      const { mean, cov } = PARTY_ELLIPSES[p];
      // Half-width of a 50% ellipse's bounding box along factor i is sqrt(2 ln 2 · var_i).
      for (const f of factors) {
        const i = ELLIPSE_FACTORS.indexOf(f);
        m = Math.max(m, Math.abs(mean[i]) + Math.sqrt(2 * Math.LN2 * cov[i][i]));
      }
    }
    return Math.ceil(m * 4) / 4 + 0.25;
  }, [parties, factors]);
  const scale = (v: number) => ((v + extent) / (2 * extent)) * PLOT;
  const ticks = Array.from({ length: Math.floor(extent) * 2 + 1 }, (_, i) => i - Math.floor(extent));

  return (
    <Card className="p-4">
      <h4 className={`${CARD_HEADING} mb-1`}>Party Overlap by Factor</h4>
      <p className={`${CARD_HINT} mb-3 leading-relaxed max-w-2xl`}>
        Each ellipse holds the middle half of a party's voters on two factors, in standard deviations
        of the electorate. Hover a party to trace it through all six panels.
      </p>

      <div className="flex flex-wrap gap-1 mb-3">
        {parties.map(p => (
          <button key={p} type="button"
            onMouseEnter={() => setHover(p)} onMouseLeave={() => setHover(null)}
            onFocus={() => setHover(p)} onBlur={() => setHover(null)}
            className="text-3xs px-1.5 py-0.5 rounded border font-semibold transition-opacity"
            style={{ borderColor: PARTY_COLORS[p], color: PARTY_COLORS[p], opacity: isDim(p) ? 0.35 : 1 }}
            title={PARTY_NAMES[p]}>
            {p}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {pairs.map(([fx, fy]) => (
          <figure key={`${fx}-${fy}`} className="min-w-0">
            <figcaption className="text-xs font-medium text-foreground mb-1 text-center">
              {FACTOR_LABELS[fx]} × {FACTOR_LABELS[fy]}
            </figcaption>
            <svg viewBox={`0 0 ${SIZE} ${SIZE}`} width="100%" style={{ height: 'auto', display: 'block' }}
              aria-label={`Party ellipses on ${FACTOR_LABELS[fx]} and ${FACTOR_LABELS[fy]}`}>
              <g transform={`translate(${PAD.l},${PAD.t})`}>
                <rect width={PLOT} height={PLOT} fill="#f8fafc" stroke="#e2e8f0" />
                {ticks.map(t => (
                  <g key={t}>
                    <line x1={scale(t)} x2={scale(t)} y1={0} y2={PLOT}
                      stroke={t === 0 ? '#cbd5e1' : '#eef2f6'} strokeDasharray={t === 0 ? '4,3' : undefined} />
                    <line y1={PLOT - scale(t)} y2={PLOT - scale(t)} x1={0} x2={PLOT}
                      stroke={t === 0 ? '#cbd5e1' : '#eef2f6'} strokeDasharray={t === 0 ? '4,3' : undefined} />
                    <text x={scale(t)} y={PLOT + 11} textAnchor="middle" fontSize={CHART_TYPE.smallTick} fill={CHART_FILL.tick}>{t}</text>
                    <text x={-5} y={PLOT - scale(t) + 3} textAnchor="end" fontSize={CHART_TYPE.smallTick} fill={CHART_FILL.tick}>{t}</text>
                  </g>
                ))}
                <text x={0} y={PLOT + 24} fontSize={CHART_TYPE.inMark} fill={CHART_FILL.label}>← {FACTOR_POLES[fx]?.low}</text>
                <text x={PLOT} y={PLOT + 24} textAnchor="end" fontSize={CHART_TYPE.inMark} fill={CHART_FILL.label}>{FACTOR_POLES[fx]?.high} →</text>
                <text transform={`translate(-22,${PLOT}) rotate(-90)`} fontSize={CHART_TYPE.inMark} fill={CHART_FILL.label}>← {FACTOR_POLES[fy]?.low}</text>
                <text transform={`translate(-22,0) rotate(-90)`} textAnchor="end" fontSize={CHART_TYPE.inMark} fill={CHART_FILL.label}>{FACTOR_POLES[fy]?.high} →</text>

                {[...parties]
                  .map(p => ({ p, e: pairEllipse(PARTY_ELLIPSES[p], fx, fy) }))
                  // Largest first, and the focused parties last, so nothing emphasised sits under a fill.
                  .sort((a, b) => (Number(!isDim(a.p)) - Number(!isDim(b.p))) || (b.e.rx * b.e.ry - a.e.rx * a.e.ry))
                  .map(({ p, e }) => {
                    const px = PLOT / (2 * extent);
                    const dim = isDim(p);
                    return (
                      <g key={p} onMouseEnter={() => setHover(p)} onMouseLeave={() => setHover(null)} style={{ cursor: 'default' }}>
                        <title>{`${PARTY_NAMES[p]}: ${PARTY_ELLIPSES[p].coverage50[`${fx}-${fy}`]}% of its voters fall inside this ellipse`}</title>
                        {/* Screen y runs downward, so the data-space rotation flips sign. */}
                        <ellipse cx={scale(e.cx)} cy={PLOT - scale(e.cy)} rx={e.rx * px} ry={e.ry * px}
                          transform={`rotate(${-e.angle} ${scale(e.cx)} ${PLOT - scale(e.cy)})`}
                          fill={PARTY_COLORS[p]} fillOpacity={dim ? 0.03 : 0.12}
                          stroke={PARTY_COLORS[p]} strokeOpacity={dim ? 0.2 : 0.9} strokeWidth={dim ? 1 : 1.5} />
                        {!dim && (
                          <text x={scale(e.cx)} y={PLOT - scale(e.cy) + 3} textAnchor="middle"
                            fontSize={CHART_TYPE.inMark} fontWeight={700} fill={PARTY_COLORS[p]}
                            stroke="#f8fafc" strokeWidth={2.5} paintOrder="stroke">{p}</text>
                        )}
                      </g>
                    );
                  })}
              </g>
            </svg>
          </figure>
        ))}
      </div>
    </Card>
  );
}
