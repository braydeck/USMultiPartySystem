// Paired range rows for the disproportionality read: a party's population share and its seat
// share as two spans on one axis. Two spans that miss each other mark real over- or
// under-representation; two that overlap put the gap inside sampling noise, which is the question
// the card exists to answer and which two bars plus one whisker cannot show.
import { getPartyColor, PARTY_NAMES } from '../../constants/parties';
import { SeatWhisker } from '../shared/SeatWhisker';
import { whiskerGeometry } from '../../lib/whisker';
import type { ShareInterval } from '../../lib/uncertainty';

/** A sampling span in percent of whatever the row's axis measures. */
export interface Span { lo: number; hi: number; expected: number }

export interface PopSeatRangeRow {
  code: string;
  /** Share of the population, percent, span and point from one payload. Stop-invariant: it is
   *  weighted by the survey weight alone, so it holds still while the seat span moves. */
  popIv: ShareInterval;
  /** Share of the chamber, percent, on the same denominator as `seats`. */
  seatPct: number;
  seats: number;
  seatIv: Span;
}

function RangeTrack({ iv, point, max, color, outline, title, pointTitle }: {
  iv: Span; point: number; max: number; color: string;
  /** Population is the outlined span, seats the filled one — the same contrast the bar
   *  rendering uses, because the two are shares of different things (people vs. a chamber). */
  outline?: boolean;
  title: string; pointTitle: string;
}) {
  const g = whiskerGeometry(iv.lo, iv.hi, iv.expected, max);
  return (
    <div className="relative h-4 flex-1 rounded bg-muted/50">
      {g && (
        <div className="absolute inset-y-[3px] rounded-sm" style={outline
          ? { left: `${g.leftPct}%`, width: `${g.widthPct}%`, background: `${color}1f`, border: `1.5px solid ${color}` }
          : { left: `${g.leftPct}%`, width: `${g.widthPct}%`, backgroundColor: color, opacity: 0.34 }} />
      )}
      <SeatWhisker lo={iv.lo} hi={iv.hi} centre={iv.expected} max={max} title={title} />
      {/* Clamp the tick's position only. A point estimate can sit outside its own bounds — the
          chamber is an argmax per district, not a draw from this interval — and the readout on
          the right must keep reporting the real number. */}
      <div className="absolute inset-y-0 w-0.5" title={pointTitle}
        style={{ left: `${Math.min(100, Math.max(0, (point / max) * 100))}%`, backgroundColor: color }} />
    </div>
  );
}

const READOUT = 'w-[152px] shrink-0 text-[10px] tabular-nums text-muted-foreground';

export function PopSeatRanges({ rows, max, seatLabel }: {
  rows: PopSeatRangeRow[]; max: number; seatLabel: string;
}) {
  return (
    <div className="space-y-3">
      {rows.map(r => {
        const c = getPartyColor(r.code);
        const name = PARTY_NAMES[r.code] ?? r.code;
        return (
          <div key={r.code} className="grid grid-cols-[110px_1fr] items-center gap-2">
            <span className="text-xs font-medium text-foreground truncate">{name}</span>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <RangeTrack iv={r.popIv} point={r.popIv.point} max={max} color={c} outline
                  title={`${name} population: ${r.popIv.lo.toFixed(1)}–${r.popIv.hi.toFixed(1)}% across resamples, ${r.popIv.expected.toFixed(1)}% expected`}
                  pointTitle={`population share: ${r.popIv.point.toFixed(1)}%`} />
                <span className={READOUT}>
                  <span className="font-semibold text-foreground">Pop {r.popIv.point.toFixed(1)}%</span>{' '}
                  {r.popIv.lo.toFixed(1)}–{r.popIv.hi.toFixed(1)}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <RangeTrack iv={r.seatIv} point={r.seatPct} max={max} color={c}
                  title={`${name} seats: ${r.seatIv.lo.toFixed(1)}–${r.seatIv.hi.toFixed(1)}% of the chamber across resamples, ${r.seatIv.expected.toFixed(1)}% expected`}
                  pointTitle={`${seatLabel} seat share: ${r.seatPct.toFixed(1)}% (${r.seats})`} />
                <span className={READOUT}>
                  <span className="font-semibold text-foreground">{seatLabel} {r.seatPct.toFixed(1)}% ({r.seats})</span>{' '}
                  {r.seatIv.lo.toFixed(1)}–{r.seatIv.hi.toFixed(1)}
                </span>
              </div>
            </div>
          </div>
        );
      })}
      <div className="grid grid-cols-[110px_1fr] gap-2">
        <span />
        <div className="flex items-center gap-2">
          <div className="flex flex-1 justify-between text-[9px] text-muted-foreground">
            <span>0</span><span>{max.toFixed(0)}% share</span>
          </div>
          <span className={READOUT} />
        </div>
      </div>
    </div>
  );
}
