// Up to four range rows per party on one axis: population, votes, party list, seats. The steps
// separate what a single population-to-seats gap conflates — population to votes is turnout, votes
// to list is the district-magnitude penalty, list to seats is what transferable voting adds.
// Votes and seats are the pair that answers the card's question, so they are always on; the other
// two are opt-in, because ten parties times four rows is unreadable by default.
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
   *  weighted by the survey weight alone, so it holds still while the other rows move. */
  popIv: ShareInterval;
  /** Share of the national vote at this turnout stop, percent. Tick and band come from the same
   *  payload; sourcing a tick from one place and a band from another is what went wrong on the
   *  population row. */
  voteIv: ShareInterval;
  /** Share of the chamber under party-list PR, percent, on the same denominator as the STV row. */
  listIv?: ShareInterval;
  /** Party-list seat count, for the readout. */
  listSeats?: number;
  /** Share of the chamber, percent, on the same denominator as `seats`. */
  seatPct: number;
  seats: number;
  seatIv: Span;
}

/** One band style per quantity. Encoded by height and weight rather than by fill pattern: the vote
 *  bands are under a percentage point wide, and a hatch or a dash inside a 4px sliver is noise. */
type Texture = 'pop' | 'votes' | 'list' | 'seats';

function bandStyle(texture: Texture, color: string): CSSProperties {
  if (texture === 'pop') return { background: `${color}1f`, border: `1.5px solid ${color}`, top: 2, bottom: 2 };
  if (texture === 'list') return { background: `${color}66`, top: 4, bottom: 4 };
  // Not fully opaque: the expected dot sits inside this band and has to stay visible through it.
  if (texture === 'votes') return { backgroundColor: color, opacity: 0.7, top: 5, bottom: 5 };
  return { backgroundColor: color, opacity: 0.3, top: 1, bottom: 1 };
}

function RangeTrack({ iv, point, max, color, texture, title, pointTitle }: {
  iv: Span; point: number; max: number; color: string; texture: Texture;
  title: string; pointTitle: string;
}) {
  const g = whiskerGeometry(iv.lo, iv.hi, iv.expected, max);
  return (
    <div className="relative h-3.5 flex-1 rounded bg-muted/50">
      {g && (
        <div className="absolute rounded-sm"
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

const READOUT = 'w-[170px] shrink-0 text-[10px] tabular-nums text-muted-foreground';

function Readout({ head, iv }: { head: string; iv: { lo: number; hi: number } }) {
  return (
    <span className={READOUT}>
      <span className="font-semibold text-foreground">{head}</span>{' '}
      {iv.lo.toFixed(1)}–{iv.hi.toFixed(1)}
    </span>
  );
}

/** A swatch drawn with the same styles the rows use, in neutral grey so it reads as a key rather
 *  than as one party's row. Wrapped in a 14px box because the styles position by height. */
function Swatch({ texture }: { texture: Texture }) {
  return (
    <span className="relative w-6 h-3.5 shrink-0">
      <span className="absolute inset-x-0 rounded-sm" style={bandStyle(texture, '#64748b')} />
    </span>
  );
}

function Legend({ rows }: { rows: { texture: Texture; label: string }[] }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[10px] text-muted-foreground">
      {rows.map(r => (
        <span key={r.label} className="flex items-center gap-1.5">
          <Swatch texture={r.texture} />{r.label}
        </span>
      ))}
      <span className="flex items-center gap-1.5">
        <span className="relative w-4 h-2.5">
          <span className="absolute inset-y-0 left-1/2 -ml-px w-0.5 bg-foreground/70" />
        </span>
        estimate
      </span>
      <span className="flex items-center gap-1.5">
        <span className="relative w-4 h-2.5">
          <span className="absolute top-1/2 left-1/2 -mt-[3px] -ml-[3px] w-1.5 h-1.5 rounded-full bg-foreground/85" />
        </span>
        expected
      </span>
      <span>band = 95% of resamples</span>
    </div>
  );
}

export function PopSeatRanges({ rows, max, seatLabel, showPop, showList }: {
  rows: PopSeatRangeRow[]; max: number; seatLabel: string;
  showPop: boolean; showList: boolean;
}) {
  const legend: { texture: Texture; label: string }[] = [
    ...(showPop ? [{ texture: 'pop' as Texture, label: 'Population' }] : []),
    { texture: 'votes', label: 'Votes' },
    ...(showList ? [{ texture: 'list' as Texture, label: 'Party list' }] : []),
    { texture: 'seats', label: `${seatLabel} seats` },
  ];

  return (
    <div className="space-y-2.5">
      {rows.map(r => {
        const c = getPartyColor(r.code);
        const name = PARTY_NAMES[r.code] ?? r.code;
        const list = r.listIv;
        return (
          <div key={r.code} className="grid grid-cols-[110px_1fr] items-center gap-2">
            <span className="text-xs font-medium text-foreground truncate">{name}</span>
            <div className="space-y-[3px]">
              {showPop && (
                <div className="flex items-center gap-2">
                  <RangeTrack iv={r.popIv} point={r.popIv.point} max={max} color={c} texture="pop"
                    title={`${name} population: ${r.popIv.lo.toFixed(1)}–${r.popIv.hi.toFixed(1)}% across resamples, ${r.popIv.expected.toFixed(1)}% expected`}
                    pointTitle={`population share: ${r.popIv.point.toFixed(1)}%`} />
                  <Readout head={`Pop ${r.popIv.point.toFixed(1)}%`} iv={r.popIv} />
                </div>
              )}
              <div className="flex items-center gap-2">
                <RangeTrack iv={r.voteIv} point={r.voteIv.point} max={max} color={c} texture="votes"
                  title={`${name} votes: ${r.voteIv.lo.toFixed(1)}–${r.voteIv.hi.toFixed(1)}% of the national vote across resamples, ${r.voteIv.expected.toFixed(1)}% expected`}
                  pointTitle={`vote share: ${r.voteIv.point.toFixed(1)}%`} />
                <Readout head={`Votes ${r.voteIv.point.toFixed(1)}%`} iv={r.voteIv} />
              </div>
              {showList && list && (
                <div className="flex items-center gap-2">
                  <RangeTrack iv={list} point={list.point} max={max} color={c} texture="list"
                    title={`${name} party list: ${list.lo.toFixed(1)}–${list.hi.toFixed(1)}% of the chamber across resamples, ${list.expected.toFixed(1)}% expected`}
                    pointTitle={`party-list seat share: ${list.point.toFixed(1)}%${r.listSeats === undefined ? '' : ` (${r.listSeats})`}`} />
                  <Readout head={`List ${list.point.toFixed(1)}%${r.listSeats === undefined ? '' : ` (${r.listSeats})`}`} iv={list} />
                </div>
              )}
              <div className="flex items-center gap-2">
                <RangeTrack iv={r.seatIv} point={r.seatPct} max={max} color={c} texture="seats"
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
      <div className="grid grid-cols-[110px_1fr] gap-2 pt-1">
        <span />
        <Legend rows={legend} />
      </div>
    </div>
  );
}
