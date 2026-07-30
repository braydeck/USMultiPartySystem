// Three range rows per party on one axis: population, votes, seats. The two steps separate what a
// single population-to-seats gap conflates — population to votes is turnout, votes to seats is what
// the electoral system does. Solidarity gives up 4.4pp on turnout alone, before the counting rule
// touches anything, and a two-row version of this card cannot show that.
import type { CSSProperties } from 'react';
import { getPartyColor, PARTY_NAMES } from '../../constants/parties';
import { SeatWhisker } from '../shared/SeatWhisker';
import { whiskerGeometry } from '../../lib/whisker';
import type { ShareInterval } from '../../lib/uncertainty';

/** A sampling span in percent of whatever the row's axis measures. */
export interface Span { lo: number; hi: number; expected: number }

export interface PopSeatRangeRow {
  code: string;
  /** Share of the population, percent, span and point from one payload. Stop-invariant: it is
   *  weighted by the survey weight alone, so it holds still while the other two rows move. */
  popIv: ShareInterval;
  /** Share of the national vote at this turnout stop, percent. Tick and band come from the same
   *  payload; sourcing a tick from one place and a band from another is what went wrong on the
   *  population row. */
  voteIv: ShareInterval;
  /** Share of the chamber, percent, on the same denominator as `seats`. */
  seatPct: number;
  seats: number;
  seatIv: Span;
}

/** Population hollow, votes hatched, seats filled. Three rows across ten parties only reads if the
 *  rows separate without reading their labels. */
type Texture = 'hollow' | 'hatch' | 'fill';

function bandStyle(texture: Texture, color: string): CSSProperties {
  if (texture === 'hollow') return { background: `${color}1f`, border: `1.5px solid ${color}` };
  if (texture === 'hatch') {
    return { backgroundImage: `repeating-linear-gradient(45deg, ${color} 0 1.5px, transparent 1.5px 4.5px)` };
  }
  return { backgroundColor: color, opacity: 0.34 };
}

function RangeTrack({ iv, point, max, color, texture, title, pointTitle }: {
  iv: Span; point: number; max: number; color: string; texture: Texture;
  title: string; pointTitle: string;
}) {
  const g = whiskerGeometry(iv.lo, iv.hi, iv.expected, max);
  return (
    <div className="relative h-3.5 flex-1 rounded bg-muted/50">
      {g && (
        <div className="absolute inset-y-[2px] rounded-sm"
          style={{ left: `${g.leftPct}%`, width: `${g.widthPct}%`, ...bandStyle(texture, color) }} />
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

const READOUT = 'w-[160px] shrink-0 text-[10px] tabular-nums text-muted-foreground';

function Readout({ head, iv }: { head: string; iv: { lo: number; hi: number } }) {
  return (
    <span className={READOUT}>
      <span className="font-semibold text-foreground">{head}</span>{' '}
      {iv.lo.toFixed(1)}–{iv.hi.toFixed(1)}
    </span>
  );
}

export function PopSeatRanges({ rows, max, seatLabel }: {
  rows: PopSeatRangeRow[]; max: number; seatLabel: string;
}) {
  return (
    <div className="space-y-2.5">
      {rows.map(r => {
        const c = getPartyColor(r.code);
        const name = PARTY_NAMES[r.code] ?? r.code;
        return (
          <div key={r.code} className="grid grid-cols-[110px_1fr] items-center gap-2">
            <span className="text-xs font-medium text-foreground truncate">{name}</span>
            <div className="space-y-[3px]">
              <div className="flex items-center gap-2">
                <RangeTrack iv={r.popIv} point={r.popIv.point} max={max} color={c} texture="hollow"
                  title={`${name} population: ${r.popIv.lo.toFixed(1)}–${r.popIv.hi.toFixed(1)}% across resamples, ${r.popIv.expected.toFixed(1)}% expected`}
                  pointTitle={`population share: ${r.popIv.point.toFixed(1)}%`} />
                <Readout head={`Pop ${r.popIv.point.toFixed(1)}%`} iv={r.popIv} />
              </div>
              <div className="flex items-center gap-2">
                <RangeTrack iv={r.voteIv} point={r.voteIv.point} max={max} color={c} texture="hatch"
                  title={`${name} votes: ${r.voteIv.lo.toFixed(1)}–${r.voteIv.hi.toFixed(1)}% of the national vote across resamples, ${r.voteIv.expected.toFixed(1)}% expected`}
                  pointTitle={`vote share: ${r.voteIv.point.toFixed(1)}%`} />
                <Readout head={`Votes ${r.voteIv.point.toFixed(1)}%`} iv={r.voteIv} />
              </div>
              <div className="flex items-center gap-2">
                <RangeTrack iv={r.seatIv} point={r.seatPct} max={max} color={c} texture="fill"
                  title={`${name} seats: ${r.seatIv.lo.toFixed(1)}–${r.seatIv.hi.toFixed(1)}% of the chamber across resamples, ${r.seatIv.expected.toFixed(1)}% expected`}
                  pointTitle={`${seatLabel} seat share: ${r.seatPct.toFixed(1)}% (${r.seats})`} />
                <Readout head={`${seatLabel} ${r.seatPct.toFixed(1)}% (${r.seats})`} iv={r.seatIv} />
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
