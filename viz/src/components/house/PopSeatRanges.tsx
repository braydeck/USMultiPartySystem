// Up to four range rows per party on one axis: population, votes, the other counting rule, and the
// rule this view is about. The steps separate what a single population-to-seats gap conflates —
// population to votes is turnout, and splitting votes-to-seats across the two rules separates the
// district-magnitude penalty they share from what each rule adds on top.
//
// Serves both House views: the STV view makes STV primary and party list the comparison, the
// party-list view swaps them. Votes and the primary rule are always on; the other two are opt-in,
// because ten parties times four rows is unreadable by default.
import { useState, type CSSProperties } from 'react';
import { getPartyColor, PARTY_NAMES } from '../../constants/parties';
import { SeatWhisker } from '../shared/SeatWhisker';
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
  /** The comparison rule's share of the chamber, percent, on the same denominator as the primary
   *  row: party list when STV is primary, STV when the list is. Optional because it needs its own
   *  bootstrap payload, which not every gate has. */
  cmpIv?: ShareInterval;
  /** Comparison-rule seat count, for the readout. */
  cmpSeats?: number;
  /** The primary rule's share of the chamber, percent, on the same denominator as `seats`. */
  seatPct: number;
  seats: number;
  seatIv: Span;
}

/** How each quantity's bar is filled. The row is named beside it, so fill no longer has
 *  to carry identity — it only separates the rule this card is about from its context. */
type Texture = 'pop' | 'votes' | 'cmp' | 'seats';

function fillStyle(texture: Texture, color: string): CSSProperties {
  if (texture === 'pop') return { background: `${color}2e`, border: `1.5px solid ${color}` };
  if (texture === 'votes') return { background: color, opacity: 0.55 };
  if (texture === 'cmp') return { background: color, opacity: 0.75 };
  return { background: color };
}

/** Gridline positions, every 5 points of share. */
function ticks(max: number): number[] {
  const out: number[] = [];
  for (let v = 0; v <= max; v += 5) out.push(v);
  return out;
}

/**
 * One quantity as a bar from zero, with its 95% span drawn as a whisker at the tip.
 *
 * Bars beat floating bands here for the same reason bars usually do: every row starts on
 * the same baseline, so the comparison is a length rather than two positions the reader
 * has to difference by eye. The uncertainty rides on the end of the bar, which is where
 * the reader is already looking, instead of becoming a second mark to decode.
 */
function BarTrack({ iv, point, max, color, texture, title, pointTitle }: {
  iv: Span; point: number; max: number; color: string; texture: Texture;
  title: string; pointTitle: string;
}) {
  const w = Math.min(100, Math.max(0, (point / max) * 100));
  return (
    <div className="relative h-4 flex-1">
      {ticks(max).map(v => (
        <span key={v} className="absolute inset-y-0 border-l border-slate-200/80"
          style={{ left: `${(v / max) * 100}%` }} />
      ))}
      <div className="absolute inset-0 rounded-sm bg-muted/40" />
      <div className="absolute inset-y-0 left-0 rounded-sm" title={pointTitle}
        style={{ width: `${w}%`, ...fillStyle(texture, color) }} />
      {/* Haloed so it holds up over a saturated fill and over the empty track alike. */}
      <div className="absolute inset-0 [&_div]:shadow-[0_0_0_1px_rgba(255,255,255,0.9)]">
        <SeatWhisker lo={iv.lo} hi={iv.hi} centre={iv.expected} max={max} title={title} />
      </div>
    </div>
  );
}

const READOUT = 'w-[122px] shrink-0 text-[10px] tabular-nums text-muted-foreground text-right';
const ROW_LABEL = 'w-[46px] shrink-0 text-[10px] font-medium text-muted-foreground';

function Readout({ head, iv }: { head: string; iv: { lo: number; hi: number } }) {
  return (
    <span className={READOUT}>
      <span className="font-semibold text-foreground">{head}</span>{' '}
      {iv.lo.toFixed(1)}–{iv.hi.toFixed(1)}
    </span>
  );
}

/** Names the quantity beside its own bar. Four bands separated only by opacity meant
 *  every row had to be decoded against the legend; the label removes that step. */
function RowLabel({ children }: { children: React.ReactNode }) {
  return <span className={ROW_LABEL}>{children}</span>;
}

/** A swatch drawn with the same styles the rows use, in neutral grey so it reads as a key rather
 *  than as one party's row. Wrapped in a 14px box because the styles position by height. */
function Swatch({ texture }: { texture: Texture }) {
  return (
    <span className="relative w-6 h-3 shrink-0 rounded-sm overflow-hidden">
      <span className="absolute inset-0 rounded-sm" style={fillStyle(texture, '#64748b')} />
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

/** Adds or removes one range row. Votes and the primary rule have no toggle: they are the
 *  comparison the card exists to make. */
function RowToggle({ on, onClick, label }: { on: boolean; onClick: () => void; label: string }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={on}
      className={`rounded-full border px-2.5 py-0.5 text-[11px] transition-colors ${on
        ? 'border-foreground/25 bg-muted text-foreground'
        : 'border-border text-muted-foreground hover:text-foreground'}`}>
      {on ? '\u2212' : '+'} {label}
    </button>
  );
}

export function PopSeatRanges({ rows, max, seatLabel, compareLabel }: {
  rows: PopSeatRangeRow[]; max: number;
  /** The rule whose row is always on, drawn as the widest band: 'STV' or 'List'. */
  seatLabel: string;
  /** The opt-in comparison rule. Absent when no comparison payload is available. */
  compareLabel?: string;
}) {
  // Votes against the primary rule is the card's claim; population and the other counting rule are
  // context the reader opts into, because four rows across ten parties is too dense to read cold.
  const [showPop, setShowPop] = useState(false);
  const [showCmp, setShowCmp] = useState(false);
  const hasCmp = !!compareLabel && rows.every(r => !!r.cmpIv);
  const showCompare = showCmp && hasCmp;

  const legend: { texture: Texture; label: string }[] = [
    ...(showPop ? [{ texture: 'pop' as Texture, label: 'Population' }] : []),
    { texture: 'votes', label: 'Votes' },
    ...(showCompare ? [{ texture: 'cmp' as Texture, label: compareLabel! }] : []),
    { texture: 'seats', label: `${seatLabel} seats` },
  ];

  return (
    <div className="space-y-2.5">
      <div className="flex flex-wrap items-center gap-1.5">
        <RowToggle on={showPop} onClick={() => setShowPop(v => !v)} label="Population" />
        {hasCmp && <RowToggle on={showCmp} onClick={() => setShowCmp(v => !v)} label={compareLabel!} />}
      </div>
      {/* Above the rows: the key has to be read before the rows mean anything. */}
      <div className="grid grid-cols-[110px_1fr] gap-2 pb-1">
        <span />
        <div className="flex items-center gap-2">
          <span className={ROW_LABEL} />
          <Legend rows={legend} />
        </div>
      </div>
      {rows.map(r => {
        const c = getPartyColor(r.code);
        const name = PARTY_NAMES[r.code] ?? r.code;
        const cmp = r.cmpIv;
        return (
          <div key={r.code}
            className="grid grid-cols-[110px_1fr] items-center gap-2 py-1.5 border-t border-slate-100 first:border-t-0">
            <span className="text-xs font-medium text-foreground truncate">{name}</span>
            <div className="space-y-px">
              {showPop && (
                <div className="flex items-center gap-2">
                  <RowLabel>Pop</RowLabel>
                  <BarTrack iv={r.popIv} point={r.popIv.point} max={max} color={c} texture="pop"
                    title={`${name} population: ${r.popIv.lo.toFixed(1)}–${r.popIv.hi.toFixed(1)}% across resamples, ${r.popIv.expected.toFixed(1)}% expected`}
                    pointTitle={`population share: ${r.popIv.point.toFixed(1)}%`} />
                  <Readout head={`${r.popIv.point.toFixed(1)}%`} iv={r.popIv} />
                </div>
              )}
              <div className="flex items-center gap-2">
                <RowLabel>Votes</RowLabel>
                <BarTrack iv={r.voteIv} point={r.voteIv.point} max={max} color={c} texture="votes"
                  title={`${name} votes: ${r.voteIv.lo.toFixed(1)}–${r.voteIv.hi.toFixed(1)}% of the national vote across resamples, ${r.voteIv.expected.toFixed(1)}% expected`}
                  pointTitle={`vote share: ${r.voteIv.point.toFixed(1)}%`} />
                <Readout head={`${r.voteIv.point.toFixed(1)}%`} iv={r.voteIv} />
              </div>
              {showCompare && cmp && (
                <div className="flex items-center gap-2">
                  <RowLabel>{compareLabel}</RowLabel>
                  <BarTrack iv={cmp} point={cmp.point} max={max} color={c} texture="cmp"
                    title={`${name} under ${compareLabel}: ${cmp.lo.toFixed(1)}–${cmp.hi.toFixed(1)}% of the chamber across resamples, ${cmp.expected.toFixed(1)}% expected`}
                    pointTitle={`${compareLabel} seat share: ${cmp.point.toFixed(1)}%${r.cmpSeats === undefined ? '' : ` (${r.cmpSeats})`}`} />
                  <Readout head={`${cmp.point.toFixed(1)}%${r.cmpSeats === undefined ? '' : ` (${r.cmpSeats})`}`} iv={cmp} />
                </div>
              )}
              <div className="flex items-center gap-2">
                <RowLabel>{seatLabel}</RowLabel>
                <BarTrack iv={r.seatIv} point={r.seatPct} max={max} color={c} texture="seats"
                  title={`${name} seats: ${r.seatIv.lo.toFixed(1)}–${r.seatIv.hi.toFixed(1)}% of the chamber across resamples, ${r.seatIv.expected.toFixed(1)}% expected`}
                  pointTitle={`${seatLabel} seat share: ${r.seatPct.toFixed(1)}% (${r.seats})`} />
                <Readout head={`${r.seatPct.toFixed(1)}% (${r.seats})`} iv={r.seatIv} />
              </div>
            </div>
          </div>
        );
      })}
      <div className="grid grid-cols-[110px_1fr] gap-2">
        <span />
        <div className="flex items-center gap-2">
          <span className={ROW_LABEL} />
          <div className="relative flex-1 h-3">
            {ticks(max).map(v => (
              <span key={v} className="absolute text-[9px] text-muted-foreground -translate-x-1/2"
                style={{ left: `${(v / max) * 100}%` }}>
                {v}{v === ticks(max)[ticks(max).length - 1] ? '% share' : ''}
              </span>
            ))}
          </div>
          <span className={READOUT} />
        </div>
      </div>
    </div>
  );
}
