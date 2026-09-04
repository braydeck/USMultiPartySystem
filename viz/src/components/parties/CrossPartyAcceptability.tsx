import { useMemo, useState } from 'react';
import { Card } from '@/components/ui/card';
import { getBlendColor, PARTY_NAMES } from '../../constants/parties';
import { cividisForFrac, cividisText, CIVIDIS_COLORS } from '../../lib/cividis';
import { PartyCode } from '../shared/PartyRowLabel';
import { MINOR_HEADING, TABLE_HEADER, CARD_HINT } from '../../constants/typography';
import affinityData from '../../data/crossPartyAffinity.json';

/**
 * Cross-party acceptability, from pipeline/build_cross_party_affinity.py.
 *
 * Received / leaked / net are percentage points of the electorate, weighted by
 * commonpostweight. net is identically softShare − hardShare (asserted in the pipeline), so
 * the diverging bar and the soft-vs-first-choice column are two readings of one number.
 */
type PartyStat = {
  received: number; leaked: number; net: number;
  softShare: number; hardShare: number; retained: number;
};
const DATA = affinityData as unknown as {
  order: string[];
  nVoters: number;
  parties: Record<string, PartyStat>;
  matrix: Record<string, Record<string, number>>;
};

const OUTFLOW = '#64748b';       // slate-500: regard leaving, dispersed across other parties
const LEVEL_EPS = 0.05;          // below this the net rounds to 0.0 at the displayed precision

const NAME_COL = 'w-28 sm:w-44 shrink-0';
// Matrix-only variant. Sticky so a horizontally scrolled cell keeps its row name; the background
// has to be opaque because cells pass behind the label rather than under it, which is why the
// matrix section below uses a solid bg-slate-50 instead of a half-transparent tint.
const NAME_COL_STICKY = `${NAME_COL} sticky left-0 z-10 bg-slate-50`;
const VAL_COL = 'w-10 shrink-0';

const name = (p: string) => PARTY_NAMES[p] ?? p;
const pp = (x: number) => `${x >= 0 ? '' : '−'}${Math.abs(x).toFixed(1)}`;
const signed = (x: number) => (Math.abs(x) <= LEVEL_EPS ? '0.0' : `${x > 0 ? '+' : '−'}${Math.abs(x).toFixed(1)}`);
const COUNT_WORDS = ['No', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten'];
const count = (n: number) => COUNT_WORDS[n] ?? String(n);

export function CrossPartyAcceptability() {
  const [showMatrix, setShowMatrix] = useState(false);

  const rows = useMemo(
    () => DATA.order.map(p => ({ party: p, ...DATA.parties[p] })).sort((a, b) => b.net - a.net),
    []);
  // One scale for both sides, so a bar's length means the same thing left and right of zero.
  const axisMax = useMemo(
    () => Math.ceil(Math.max(...rows.map(r => Math.max(r.received, r.leaked))) * 2) / 2,
    [rows]);
  const cellMax = useMemo(
    () => Math.max(...DATA.order.flatMap(a => DATA.order.filter(b => b !== a).map(b => DATA.matrix[a][b]))),
    []);

  const gain = rows.filter(r => r.net > LEVEL_EPS);
  const give = rows.filter(r => r.net < -LEVEL_EPS);
  const level = rows.filter(r => Math.abs(r.net) <= LEVEL_EPS);

  return (
    <Card className="overflow-hidden">
      <div className="px-4 py-3 border-b border-border/50 bg-muted">
        <span className={MINOR_HEADING}>Cross-party acceptability</span>
        <span className="text-xs text-muted-foreground ml-3">percentage points of the electorate</span>
      </div>

      <div className="px-4 pt-3">
        <p className={`${CARD_HINT} leading-relaxed`}>
          Every voter carries a posterior across all ten parties, not only the one they would rank
          first. Right of zero is the regard other parties' voters place on a party; left of zero is
          the regard that party's own voters place elsewhere.
        </p>
      </div>

      {/* Diverging bars, sorted by net. Values sit in fixed columns rather than on the bars, so
          every number is readable at every bar length.
          Below sm the row breaks into two lines (name + net, then the bar with its two values):
          six columns and a comparable track do not fit 390px, and shrinking the track to ~110px
          leaves bars too short to compare. `sm:contents` dissolves the two mobile line wrappers
          at sm+, so one markup tree serves both layouts and the sm+ order comes from sm:order-*. */}
      <div className="px-4 py-3">
        <div className="hidden sm:flex items-end gap-2 mb-1.5">
          <span className={`${NAME_COL} ${TABLE_HEADER}`}>party</span>
          <span className={`${VAL_COL} text-right ${TABLE_HEADER}`}>gives</span>
          <span className="flex-1 min-w-0" />
          <span className={`${VAL_COL} ${TABLE_HEADER}`}>gets</span>
          <span className={`w-11 shrink-0 text-right ${TABLE_HEADER}`}>net</span>
          <span className={`w-20 shrink-0 text-right ${TABLE_HEADER}`}>soft / 1st</span>
        </div>

        <div className="space-y-2 sm:space-y-1">
          {rows.map(r => {
            const color = getBlendColor(r.party);
            const wOut = (r.leaked / axisMax) * 50;
            const wIn = (r.received / axisMax) * 50;
            const rowTitle = `${name(r.party)}: gives away ${r.leaked.toFixed(2)} pp, receives `
              + `${r.received.toFixed(2)} pp, net ${r.net > 0 ? '+' : '−'}${Math.abs(r.net).toFixed(2)} pp`;
            return (
              <div key={r.party} className="sm:flex sm:items-center sm:gap-2">
                <div className="flex items-center gap-2 sm:contents">
                  <span className={`flex-1 min-w-0 sm:flex-none ${NAME_COL} sm:order-1 text-xs font-semibold truncate`}
                    style={{ color }} title={name(r.party)}>
                    {name(r.party)}
                  </span>
                  <span className="w-11 shrink-0 sm:order-5 text-right text-xs tabular-nums font-bold text-foreground"
                    title={rowTitle}>
                    {signed(r.net)}
                  </span>
                  <span className="hidden sm:block sm:order-6 w-20 shrink-0 text-right text-3xs tabular-nums text-muted-foreground"
                    title={`Soft posterior share ${r.softShare.toFixed(1)}% vs first-choice share ${r.hardShare.toFixed(1)}%`}>
                    {r.softShare.toFixed(1)} / {r.hardShare.toFixed(1)}
                  </span>
                </div>
                <div className="flex items-center gap-2 sm:contents">
                  <span className={`${VAL_COL} sm:order-2 text-right text-3xs tabular-nums text-muted-foreground`}>
                    {pp(r.leaked)}
                  </span>
                  <div className="flex-1 min-w-0 sm:order-3 relative h-4 rounded-sm bg-muted overflow-hidden"
                    title={rowTitle}>
                    <div className="absolute inset-y-0 rounded-sm"
                      style={{ left: `${50 - wOut}%`, width: `${wOut}%`, backgroundColor: OUTFLOW }} />
                    <div className="absolute inset-y-0 rounded-sm"
                      style={{ left: '50%', width: `${wIn}%`, backgroundColor: color }} />
                    <div className="absolute inset-y-0 w-px bg-slate-700" style={{ left: '50%' }} />
                  </div>
                  <span className={`${VAL_COL} sm:order-4 text-3xs tabular-nums font-semibold`} style={{ color }}>
                    {pp(r.received)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Axis under the track. Both halves share one scale, and the direction words sit here
            rather than in the column heads, which the mobile layout drops. */}
        <div className="flex items-center gap-2 mt-1.5">
          <span className={`hidden sm:block ${NAME_COL}`} />
          <span className={VAL_COL} />
          <span className={`flex-1 min-w-0 flex justify-between gap-1 ${TABLE_HEADER}`}>
            <span>{axisMax.toFixed(1)} given away &larr;</span>
            <span>0 pp</span>
            <span>&rarr; {axisMax.toFixed(1)} received</span>
          </span>
          <span className={VAL_COL} />
          <span className="hidden sm:block w-11 shrink-0" />
          <span className="hidden sm:block w-20 shrink-0" />
        </div>
      </div>

      <div className="px-4 pb-3">
        <p className={`${CARD_HINT} leading-relaxed`}>
          {count(gain.length)} parties take in more than they give away:{' '}
          {gain.map((r, i) => (
            <span key={r.party}>
              {i > 0 && ', '}
              <span className="font-medium" style={{ color: getBlendColor(r.party) }}>{name(r.party)}</span>{' '}
              {signed(r.net)}
            </span>
          ))}
          .{' '}
          {level.length > 0 && (
            <>
              {level.map(r => name(r.party)).join(' and ')} {level.length === 1 ? 'is' : 'are'} level, and{' '}
            </>
          )}
          {count(give.length).toLowerCase()} give away more, from {name(give[0].party)} at {signed(give[0].net)} to{' '}
          {name(give[give.length - 1].party)} at {signed(give[give.length - 1].net)}. The net is the gap
          between a party's soft posterior share and its first-choice share, so soft share runs above
          first-choice share whenever a party collects more regard from other parties' voters than its
          own voters give away.
        </p>
      </div>

      <button type="button" onClick={() => setShowMatrix(v => !v)}
        className="w-full flex items-center justify-center gap-1.5 px-4 py-2 border-t border-border/50 hover:bg-muted/40 transition-colors"
        aria-expanded={showMatrix}>
        <span className="text-3xs text-muted-foreground">{showMatrix ? '▲' : '▼'}</span>
        <span className="text-3xs text-muted-foreground">
          {showMatrix ? 'hide who holds the regard' : 'who holds the regard (10 × 10)'}
        </span>
      </button>

      {showMatrix && (
        <div className="px-4 py-3 border-t border-border/50 bg-slate-50">
          <p className={`${CARD_HINT} leading-relaxed mb-3`}>
            Each cell is the electorate mass a first-choice group places on another party. Rows read
            across as what a party's voters extend elsewhere; columns read down as who extends regard
            to a party. Own-party mass is held in its own column, on its own scale, so the
            off-diagonal cells stay legible against it.
          </p>
          <div className="overflow-x-auto">
            <div className="inline-block min-w-full">
              <div className="flex items-end gap-px mb-1">
                <span className={`${NAME_COL_STICKY} ${TABLE_HEADER} leading-tight pr-2`}>
                  &darr; first choice<br />&rarr; regard placed on
                </span>
                <span className={`w-10 shrink-0 text-center ${TABLE_HEADER}`}>keeps</span>
                <span className="w-2 shrink-0" />
                {DATA.order.map(c => (
                  <span key={c} className="flex-1 min-w-6 flex justify-center text-3xs font-bold" title={name(c)}>
                    <PartyCode code={c} />
                  </span>
                ))}
                <span className="w-2 shrink-0" />
                <span className={`w-10 shrink-0 text-center ${TABLE_HEADER}`}>gives</span>
              </div>

              {DATA.order.map(src => {
                const s = DATA.parties[src];
                const srcColor = getBlendColor(src);
                return (
                  <div key={src} className="flex items-stretch gap-px mb-px">
                    <span className={`${NAME_COL_STICKY} text-xs font-medium truncate self-center pr-2`}
                      style={{ color: srcColor }} title={name(src)}>
                      {name(src)}
                    </span>
                    <span className="w-10 shrink-0 h-6 flex items-center justify-center rounded-sm text-3xs font-bold tabular-nums"
                      style={{ backgroundColor: srcColor, color: '#fff' }}
                      title={`${name(src)} voters keep ${pp(s.retained)} pp on their own party, of ${pp(s.hardShare)} pp total`}>
                      {pp(s.retained)}
                    </span>
                    <span className="w-2 shrink-0" />
                    {DATA.order.map(dst => {
                      if (dst === src) {
                        // Own-party mass lives in the keeps column; tint the diagonal in the party's
                        // colour so the reader can trace it rather than losing it among true zeros.
                        return <span key={dst} className="flex-1 min-w-6 h-6 rounded-sm"
                          style={{ backgroundColor: srcColor, opacity: 0.16 }}
                          title={`${name(src)} own mass is in the keeps column`} />;
                      }
                      const v = DATA.matrix[src][dst];
                      const show = v >= 0.05;
                      const bg = show ? cividisForFrac(v / cellMax) : undefined;
                      return (
                        <span key={dst}
                          className="flex-1 min-w-6 h-6 flex items-center justify-center rounded-sm text-3xs font-semibold tabular-nums"
                          style={bg ? { backgroundColor: bg, color: cividisText(bg) } : { backgroundColor: 'var(--muted)' }}
                          title={`${name(src)} voters on ${name(dst)}: ${v.toFixed(2)} pp`}>
                          {show ? v.toFixed(1) : ''}
                        </span>
                      );
                    })}
                    <span className="w-2 shrink-0" />
                    <span className="w-10 shrink-0 h-6 flex items-center justify-center text-3xs tabular-nums font-semibold text-muted-foreground"
                      title={`${name(src)} voters place ${pp(s.leaked)} pp on other parties`}>
                      {pp(s.leaked)}
                    </span>
                  </div>
                );
              })}

              {/* Column margin: the received total, which is what the diverging bars plot. */}
              <div className="flex items-stretch gap-px mt-1 pt-1 border-t border-border/50">
                <span className={`${NAME_COL_STICKY} self-center pr-2 ${TABLE_HEADER}`}>gets</span>
                <span className="w-10 shrink-0" />
                <span className="w-2 shrink-0" />
                {DATA.order.map(c => (
                  <span key={c}
                    className="flex-1 min-w-6 h-6 flex items-center justify-center text-3xs tabular-nums font-bold"
                    style={{ color: getBlendColor(c) }}
                    title={`${name(c)} receives ${pp(DATA.parties[c].received)} pp from other parties' voters`}>
                    {pp(DATA.parties[c].received)}
                  </span>
                ))}
                <span className="w-2 shrink-0" />
                <span className="w-10 shrink-0" />
              </div>

              <div className={`flex items-center gap-2 mt-2 ${TABLE_HEADER}`}>
                <span>0</span>
                <span className="h-2 w-24 rounded-sm"
                  style={{ backgroundImage: `linear-gradient(90deg, ${CIVIDIS_COLORS.join(', ')})` }} />
                <span>{cellMax.toFixed(1)} pp</span>
                <span className="normal-case tracking-normal">
                  cells below 0.05 pp left blank &middot; keeps column on its own scale
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
