import { useMemo, useState } from 'react';
import { getPartyColor, PARTY_NAMES } from '../../constants/parties';
import type { ShareInterval } from '../../lib/uncertainty';

/** A sampling span in percent of whatever the row's axis measures. */
export interface Span { lo: number; hi: number; expected: number }

export interface PopSeatRangeRow {
  code: string;
  /** Share of the population, percent. Stop-invariant: weighted by the survey weight
   *  alone, so it holds still while the other rows move with turnout. */
  popIv: ShareInterval;
  /** Share of the national vote at this turnout stop, percent. */
  voteIv: ShareInterval;
  /** The comparison rule's share of the chamber, on the same denominator as the primary
   *  row: party list when STV is primary, STV when the list is. */
  cmpIv?: ShareInterval;
  /** Comparison-rule seat count, for the readout. */
  cmpSeats?: number;
  /** The primary rule's share of the chamber, on the same denominator as `seats`. */
  seatPct: number;
  seats: number;
  seatIv: Span;
}

/**
 * Population, votes and seats per party, on one row each.
 *
 * Replaces a stack of four range tracks per party — forty near-identical grey bars
 * separated only by opacity, where the quantity the reader wanted (the gap between what
 * a party earns and what it wins) was a distance they had to estimate by eye.
 *
 * Two views of the same numbers:
 *
 * - **Levels** puts every quantity for a party on one row of a shared axis, joined by a
 *   connector. The gap becomes a line with a length, which is readable; the quantities
 *   are told apart by marker shape, which is a strong channel for categories, rather
 *   than by four grades of one.
 * - **Range** is the honest view: the 95% span of the seat estimate, with the vote share
 *   marked on it, so the reader can see which gaps the resampling can actually resolve.
 * - **Gap** drops the levels and plots seats minus votes against zero. It answers the
 *   card's actual question directly and sorts the parties by who the counting rule
 *   helps, at the cost of the absolute shares.
 *
 * Levels carries no uncertainty at all, deliberately. It used to draw the seat band and
 * the connector in the same colour at different opacities, which overlapped into a third
 * shade that encoded nothing — and it banded seats but not votes, with no reason given.
 * Uncertainty belongs to Range, where it can be drawn once and labelled.
 */

export type CompareView = 'levels' | 'range' | 'gap';

interface Props {
  rows: PopSeatRangeRow[];
  max: number;
  /** The rule this view is about: 'STV' or 'List'. */
  seatLabel: string;
  /** The other counting rule, when its payload is available. */
  compareLabel?: string;
}

const NAME_COL = 'w-[104px] shrink-0 text-xs font-medium text-foreground truncate';
const ROW_H = 26;

/** Gridline positions every 5 points, so a reader can measure rather than guess. */
function ticks(max: number): number[] {
  const step = max > 30 ? 10 : 5;
  const out: number[] = [];
  for (let v = 0; v <= max; v += step) out.push(v);
  return out;
}

function Grid({ max }: { max: number }) {
  return (
    <>
      {ticks(max).map(v => (
        <div key={v} className="absolute inset-y-0 border-l border-slate-200/70"
          style={{ left: `${(v / max) * 100}%` }} />
      ))}
    </>
  );
}

function Axis({ max, unit }: { max: number; unit: string }) {
  return (
    <div className="relative h-4">
      {ticks(max).map(v => (
        <span key={v} className="absolute text-[9px] text-muted-foreground -translate-x-1/2"
          style={{ left: `${(v / max) * 100}%` }}>
          {v}{v === ticks(max)[ticks(max).length - 1] ? unit : ''}
        </span>
      ))}
    </div>
  );
}

// ── levels ───────────────────────────────────────────────────────────────────

/**
 * Markers, in the order the reader steps through them: who lives here, who turned out,
 * what each rule turns that into. Shape carries the quantity; colour carries the party.
 */
function Marker({ kind, color, left }: { kind: 'pop' | 'votes' | 'cmp' | 'seat'; color: string; left: number }) {
  const pos = { left: `${left}%`, top: '50%' } as const;
  if (kind === 'pop') {
    return <span className="absolute w-2.5 h-2.5 rounded-full border-[1.5px] bg-white -translate-x-1/2 -translate-y-1/2"
      style={{ ...pos, borderColor: color }} />;
  }
  if (kind === 'votes') {
    return <span className="absolute w-[3px] h-3.5 rounded-sm -translate-x-1/2 -translate-y-1/2"
      style={{ ...pos, backgroundColor: color }} />;
  }
  if (kind === 'cmp') {
    return <span className="absolute w-2 h-2 -translate-x-1/2 -translate-y-1/2 rotate-45 border-[1.5px] bg-white"
      style={{ ...pos, borderColor: color }} />;
  }
  return <span className="absolute w-3 h-3 rounded-full -translate-x-1/2 -translate-y-1/2 ring-2 ring-white"
    style={{ ...pos, backgroundColor: color }} />;
}

function LevelsRow({ r, max, showPop, showCmp }: {
  r: PopSeatRangeRow; max: number; showPop: boolean; showCmp: boolean;
}) {
  const c = getPartyColor(r.code);
  const name = PARTY_NAMES[r.code] ?? r.code;
  const pts = [
    ...(showPop ? [r.popIv.point] : []),
    r.voteIv.point,
    ...(showCmp && r.cmpIv ? [r.cmpIv.point] : []),
    r.seatPct,
  ];
  const lo = Math.min(...pts), hi = Math.max(...pts);
  const gap = r.seatPct - r.voteIv.point;
  const pct = (v: number) => (v / max) * 100;

  return (
    <div className="flex items-center gap-2" style={{ height: ROW_H }}>
      <span className={NAME_COL} title={name}>{name}</span>
      <div className="relative flex-1 h-full">
        <Grid max={max} />
        {/* Structural, not data: a neutral rule linking this row's markers so the gap
            reads as a length. Grey on purpose — in the party colour it competed with
            the markers and, when it overlapped anything, invented a shade. */}
        <div className="absolute top-1/2 h-px -translate-y-1/2 bg-slate-300"
          style={{ left: `${pct(lo)}%`, width: `${pct(hi - lo)}%` }} />
        {showPop && <Marker kind="pop" color={c} left={pct(r.popIv.point)} />}
        <Marker kind="votes" color={c} left={pct(r.voteIv.point)} />
        {showCmp && r.cmpIv && <Marker kind="cmp" color={c} left={pct(r.cmpIv.point)} />}
        <Marker kind="seat" color={c} left={pct(r.seatPct)} />
      </div>
      <span className="w-[128px] shrink-0 text-[10px] tabular-nums text-right">
        <span className="text-muted-foreground">{r.voteIv.point.toFixed(1)} → </span>
        <span className="font-semibold text-foreground">{r.seatPct.toFixed(1)}%</span>
        <span className={gap >= 0 ? 'text-emerald-700' : 'text-rose-700'}>
          {' '}{gap >= 0 ? '+' : ''}{gap.toFixed(1)}
        </span>
        <span className="text-muted-foreground"> ({r.seats})</span>
      </span>
    </div>
  );
}

// ── range ────────────────────────────────────────────────────────────────────

/**
 * Whether the seat estimate and the vote share can actually be told apart.
 *
 * A gap smaller than the seat interval is a gap the resampling cannot resolve, and
 * saying "Solidarity loses 0.8 points" when its seat span runs either side of its vote
 * share would be reading noise. Those rows are drawn hollow and called out.
 */
const resolved = (r: PopSeatRangeRow) =>
  r.voteIv.point < r.seatIv.lo || r.voteIv.point > r.seatIv.hi;

function RangeRow({ r, max, total }: { r: PopSeatRangeRow; max: number; total: number }) {
  const c = getPartyColor(r.code);
  const name = PARTY_NAMES[r.code] ?? r.code;
  const pct = (v: number) => (v / max) * 100;
  const seatsAt = (share: number) => Math.round((share / 100) * total);
  const clear = resolved(r);
  return (
    <div className="flex items-center gap-2" style={{ height: ROW_H }}>
      <span className={NAME_COL} title={name}>{name}</span>
      <div className="relative flex-1 h-full">
        <Grid max={max} />
        {/* The seat span. Solid when it clears the vote share, hollow when it does not. */}
        <div className="absolute top-1/2 h-4 -translate-y-1/2 rounded"
          title={`${name}: ${seatsAt(r.seatIv.lo)}–${seatsAt(r.seatIv.hi)} seats across resamples`}
          style={{
            left: `${pct(r.seatIv.lo)}%`, width: `${pct(r.seatIv.hi - r.seatIv.lo)}%`,
            backgroundColor: clear ? `${c}59` : 'transparent',
            border: `1.5px solid ${c}`,
          }} />
        {/* Point estimate. Clamped for drawing only — an argmax per district can land
            outside its own resampled span, and the readout still reports the real one. */}
        <div className="absolute inset-y-1 w-[3px] -translate-x-1/2 rounded-sm"
          title={`estimate ${r.seats} seats`}
          style={{ left: `${Math.min(100, Math.max(0, pct(r.seatPct)))}%`, backgroundColor: c }} />
        {/* Vote share, as the line the seat span is being judged against. */}
        <div className="absolute inset-y-0 w-px -translate-x-1/2 bg-slate-500"
          title={`vote share ${r.voteIv.point.toFixed(1)}%`}
          style={{ left: `${pct(r.voteIv.point)}%` }} />
      </div>
      <span className="w-[128px] shrink-0 text-[10px] tabular-nums text-right">
        <span className="font-semibold text-foreground">{r.seats}</span>
        <span className="text-muted-foreground"> ({seatsAt(r.seatIv.lo)}–{seatsAt(r.seatIv.hi)})</span>
        {!clear && <span className="text-muted-foreground italic"> · spans votes</span>}
      </span>
    </div>
  );
}

// ── gap ──────────────────────────────────────────────────────────────────────

function GapRow({ r, span, seatLabel }: { r: PopSeatRangeRow; span: number; seatLabel: string }) {
  const c = getPartyColor(r.code);
  const name = PARTY_NAMES[r.code] ?? r.code;
  const gap = r.seatPct - r.voteIv.point;
  const half = (Math.abs(gap) / span) * 50;
  const clear = resolved(r);
  return (
    <div className="flex items-center gap-2" style={{ height: ROW_H }}>
      <span className={NAME_COL} title={name}>{name}</span>
      <div className="relative flex-1 h-full">
        <div className="absolute inset-y-0 left-1/2 border-l border-slate-300" />
        <div className="absolute top-1/2 h-3.5 -translate-y-1/2 rounded-sm"
          title={`${name}: ${gap >= 0 ? '+' : ''}${gap.toFixed(1)} points against its vote share`
            + (clear ? '' : ' — inside the seat estimate\u2019s own range, so not resolvable')}
          style={{
            backgroundColor: clear ? c : 'transparent',
            border: clear ? undefined : `1.5px solid ${c}`,
            left: gap >= 0 ? '50%' : `${50 - half}%`,
            width: `${half}%`,
          }} />
      </div>
      <span className="w-[128px] shrink-0 text-[10px] tabular-nums text-right">
        <span className={`font-semibold ${!clear ? 'text-muted-foreground'
          : gap >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
          {gap >= 0 ? '+' : ''}{gap.toFixed(1)} pts
        </span>
        <span className="text-muted-foreground"> · {seatLabel} {r.seats}</span>
      </span>
    </div>
  );
}

// ── chart ────────────────────────────────────────────────────────────────────

function Toggle({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={on}
      className={`rounded-full border px-2.5 py-0.5 text-[11px] transition-colors ${on
        ? 'border-foreground/25 bg-muted text-foreground'
        : 'border-border text-muted-foreground hover:text-foreground'}`}>
      {children}
    </button>
  );
}

export function SeatShareCompare({ rows, max, seatLabel, compareLabel }: Props) {
  const [view, setView] = useState<CompareView>('levels');
  // Population and the other counting rule stay opt-in: the card's claim is votes
  // against this rule, and four markers on every row is more than it needs to make it.
  const [showPop, setShowPop] = useState(false);
  const [showCmpRaw, setShowCmp] = useState(false);
  const hasCmp = !!compareLabel && rows.every(r => !!r.cmpIv);
  const showCmp = showCmpRaw && hasCmp;

  const sortedByGap = useMemo(
    () => [...rows].sort((a, b) => (b.seatPct - b.voteIv.point) - (a.seatPct - a.voteIv.point)),
    [rows],
  );
  // Chamber size, recovered from any row: seats and their share come from one payload.
  const total = useMemo(() => {
    const r = rows.find(x => x.seats > 0 && x.seatPct > 0);
    return r ? Math.round(r.seats / (r.seatPct / 100)) : 0;
  }, [rows]);
  const unresolved = rows.filter(r => !resolved(r)).length;
  const span = useMemo(() => {
    const m = Math.max(...rows.map(r => Math.abs(r.seatPct - r.voteIv.point)));
    return Math.max(1, Math.ceil(m));
  }, [rows]);

  const controls = (
    <div className="flex flex-wrap items-center gap-1.5 pb-2">
      <div className="flex rounded-full border border-border overflow-hidden mr-1">
        {(['levels', 'range', 'gap'] as const).map(v => (
          <button key={v} type="button" onClick={() => setView(v)} aria-pressed={view === v}
            className={`px-2.5 py-0.5 text-[11px] capitalize transition-colors ${view === v
              ? 'bg-foreground text-background' : 'text-muted-foreground hover:text-foreground'}`}>
            {v}
          </button>
        ))}
      </div>
      {view === 'levels' && (
        <>
          <Toggle on={showPop} onClick={() => setShowPop(v => !v)}>{showPop ? '\u2212' : '+'} Population</Toggle>
          {hasCmp && (
            <Toggle on={showCmpRaw} onClick={() => setShowCmp(v => !v)}>
              {showCmpRaw ? '\u2212' : '+'} {compareLabel}
            </Toggle>
          )}
        </>
      )}
    </div>
  );

  if (view === 'range') {
    return (
      <div className="space-y-1">
        {controls}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-muted-foreground pb-1">
          <span className="flex items-center gap-1.5">
            <span className="w-5 h-3 rounded border-[1.5px] border-slate-400 bg-slate-400/35" />
            95% of resamples
          </span>
          <span className="flex items-center gap-1.5">
            <span className="relative w-3 h-3"><span className="absolute inset-y-0 left-1/2 w-[3px] -translate-x-1/2 rounded-sm bg-slate-500" /></span>
            {seatLabel} estimate
          </span>
          <span className="flex items-center gap-1.5">
            <span className="relative w-3 h-3"><span className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-slate-500" /></span>
            vote share
          </span>
          <span>hollow = span crosses the vote share</span>
        </div>
        {rows.map(r => <RangeRow key={r.code} r={r} max={max} total={total} />)}
        <div className="flex items-center gap-2">
          <span className={NAME_COL} />
          <div className="flex-1"><Axis max={max} unit="% share" /></div>
          <span className="w-[128px] shrink-0" />
        </div>
        <p className="text-[10px] text-muted-foreground pt-1">
          Seats each party wins across resamples of the survey.
          {unresolved > 0 && ` ${unresolved} of ${rows.length} span their own vote share, so
            for those the gap between votes and seats is smaller than the sampling error.`}
        </p>
      </div>
    );
  }

  if (view === 'gap') {
    return (
      <div className="space-y-1">
        {controls}
        <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
          <span className={NAME_COL} />
          <div className="relative flex-1 flex justify-between">
            <span>−{span} pts · under-represented</span>
            <span>over-represented · +{span} pts</span>
          </div>
          <span className="w-[128px] shrink-0" />
        </div>
        {sortedByGap.map(r => <GapRow key={r.code} r={r} span={span} seatLabel={seatLabel} />)}
        <p className="text-[10px] text-muted-foreground pt-1">
          Seat share minus vote share, in percentage points. Sorted by who the counting rule
          helps. Hollow bars sit inside the seat estimate&apos;s own 95% range, so those gaps
          are not resolvable — see Range.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {controls}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-muted-foreground pb-1">
        {showPop && <Key kind="pop">Population</Key>}
        <Key kind="votes">Votes</Key>
        {showCmp && compareLabel && <Key kind="cmp">{compareLabel}</Key>}
        <Key kind="seat">{seatLabel} seats</Key>
      </div>
      {rows.map(r => (
        <LevelsRow key={r.code} r={r} max={max} showPop={showPop} showCmp={showCmp} />
      ))}
      <div className="flex items-center gap-2">
        <span className={NAME_COL} />
        <div className="flex-1"><Axis max={max} unit="% share" /></div>
        <span className="w-[128px] shrink-0" />
      </div>
    </div>
  );
}

function Key({ kind, children }: { kind: 'pop' | 'votes' | 'cmp' | 'seat'; children: React.ReactNode }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="relative w-4 h-3">
        <Marker kind={kind} color="#64748b" left={50} />
      </span>
      {children}
    </span>
  );
}
