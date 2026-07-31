// Share bars for the House seat-share cards: one bar per quantity per party, all from a
// common zero, with the 95% sampling span drawn on the tip of the bar where one exists.
//
// Bars rather than floating bands because every row then starts on the same baseline, so
// comparing what a party earns to what it wins is judging a length, not differencing two
// positions by eye.
//
// The quantity list is passed in, so one renderer serves the national card — where the
// bootstrap supplies spans for population, votes and both counting rules — and the
// ballot-depth, crossover and per-state cards, where it does not and the bars render bare.
import { useState, type CSSProperties } from 'react';
import { getPartyColor, PARTY_NAMES } from '../../constants/parties';
import { SeatWhisker } from '../shared/SeatWhisker';

/** A sampling span in percent of whatever the row's axis measures. */
export interface Span { lo: number; hi: number; expected: number }

/** How a quantity's bar is filled. Fill separates the rule a card is about from its
 *  context; it does not have to say which row is which, because the row is labelled. */
export type Texture = 'pop' | 'context' | 'compare' | 'primary';

export interface Quantity {
  /** Stable id, used as the toggle key and to look values up. */
  key: string;
  /** Short label beside the bar. */
  label: string;
  /** Longer label, for the legend and the toggle. */
  legend: string;
  texture: Texture;
  /** Optional rows get a +/− pill and start hidden. */
  optional?: boolean;
}

export interface PartyValues {
  code: string;
  values: Record<string, { point: number; iv?: Span; seats?: number } | undefined>;
}

function fillStyle(texture: Texture, color: string): CSSProperties {
  if (texture === 'pop') return { background: `${color}2e`, border: `1.5px solid ${color}` };
  if (texture === 'context') return { background: color, opacity: 0.5 };
  if (texture === 'compare') return { background: color, opacity: 0.75 };
  return { background: color };
}

/** Gridline positions, every 5 points of share. */
function ticks(max: number): number[] {
  const out: number[] = [];
  for (let v = 0; v <= max; v += 5) out.push(v);
  return out;
}

const LABEL_COL = 'w-[64px] shrink-0 text-[10px] font-medium text-muted-foreground';
const PCT_COL = 'w-[46px] shrink-0 text-[10px] tabular-nums font-semibold text-foreground text-right';
const GUTTER = 'w-[112px] shrink-0 text-[10px] tabular-nums text-muted-foreground';

function Bar({ point, iv, max, color, texture, title }: {
  point: number; iv?: Span; max: number; color: string; texture: Texture; title: string;
}) {
  const w = Math.min(100, Math.max(0, (point / max) * 100));
  return (
    <div className="relative h-4 flex-1">
      {ticks(max).map(v => (
        <span key={v} className="absolute inset-y-0 border-l border-slate-200/80"
          style={{ left: `${(v / max) * 100}%` }} />
      ))}
      <div className="absolute inset-0 rounded-sm bg-muted/40" />
      {/* Square ends. A rounded tip blurs exactly where the bar stops, and where it stops
          is the estimate — the one place on this chart a reader has to be precise. */}
      <div className="absolute inset-y-0 left-0" title={title}
        style={{ width: `${w}%`, ...fillStyle(texture, color) }} />
      {iv && (
        // Haloed so it holds up over a saturated fill and over the empty track alike.
        <div className="absolute inset-0 [&_div]:shadow-[0_0_0_1px_rgba(255,255,255,0.9)]">
          <SeatWhisker lo={iv.lo} hi={iv.hi} centre={iv.expected} max={max} title={title} />
        </div>
      )}
    </div>
  );
}

function Swatch({ texture }: { texture: Texture }) {
  return (
    <span className="relative w-6 h-3 shrink-0 rounded-sm overflow-hidden">
      <span className="absolute inset-0 rounded-sm" style={fillStyle(texture, '#64748b')} />
    </span>
  );
}

function RowToggle({ on, onClick, label }: { on: boolean; onClick: () => void; label: string }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={on}
      className={`rounded-full border px-2.5 py-0.5 text-[11px] transition-colors ${on
        ? 'border-foreground/25 bg-muted text-foreground'
        : 'border-border text-muted-foreground hover:text-foreground'}`}>
      {on ? '−' : '+'} {label}
    </button>
  );
}

export function PopSeatRanges({ quantities, parties, max }: {
  quantities: Quantity[];
  parties: PartyValues[];
  max: number;
}) {
  const [hidden, setHidden] = useState<Set<string>>(
    () => new Set(quantities.filter(q => q.optional).map(q => q.key)),
  );
  const shown = quantities.filter(q => !q.optional || !hidden.has(q.key));
  const anyRange = parties.some(p => shown.some(q => !!p.values[q.key]?.iv));

  return (
    <div className="space-y-1">
      {quantities.some(q => q.optional) && (
        <div className="flex flex-wrap items-center gap-1.5 pb-1">
          {quantities.filter(q => q.optional).map(q => (
            <RowToggle key={q.key} label={q.legend} on={!hidden.has(q.key)}
              onClick={() => setHidden(prev => {
                const next = new Set(prev);
                if (!next.delete(q.key)) next.add(q.key);
                return next;
              })} />
          ))}
        </div>
      )}

      <div className="grid grid-cols-[110px_1fr] gap-2 pb-1">
        <span />
        <div className="flex items-center gap-2">
          <span className={LABEL_COL} /><span className={PCT_COL} />
          <div className="flex flex-1 flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-muted-foreground">
            {shown.map(q => (
              <span key={q.key} className="flex items-center gap-1.5">
                <Swatch texture={q.texture} />{q.legend}
              </span>
            ))}
            {anyRange && (
              <span className="flex items-center gap-1.5">
                <span className="relative w-5 h-2.5">
                  <span className="absolute top-1/2 inset-x-0 h-px -translate-y-1/2 bg-foreground/70" />
                  <span className="absolute top-1/2 left-1/2 -mt-[3px] -ml-[3px] w-1.5 h-1.5 rounded-full bg-foreground/85" />
                </span>
                95% of resamples, with their average
              </span>
            )}
          </div>
          <span className={GUTTER} />
        </div>
      </div>

      {parties.map(p => {
        const c = getPartyColor(p.code);
        const name = PARTY_NAMES[p.code] ?? p.code;
        return (
          <div key={p.code}
            className="grid grid-cols-[110px_1fr] items-center gap-2 py-1.5 border-t border-slate-100 first:border-t-0">
            <span className="text-xs font-medium text-foreground truncate">{name}</span>
            <div className="space-y-px">
              {shown.map(q => {
                const v = p.values[q.key];
                if (!v) return null;
                const title = `${name} ${q.legend.toLowerCase()}: ${v.point.toFixed(1)}%`
                  + (v.seats === undefined ? '' : ` (${v.seats} seats)`)
                  + (v.iv ? `, ${v.iv.lo.toFixed(1)}–${v.iv.hi.toFixed(1)}% across resamples` : '');
                return (
                  <div key={q.key} className="flex items-center gap-2">
                    <span className={LABEL_COL}>{q.label}</span>
                    <span className={PCT_COL}>{v.point.toFixed(1)}%</span>
                    <Bar point={v.point} iv={v.iv} max={max} color={c} texture={q.texture} title={title} />
                    <span className={GUTTER}>
                      {v.seats !== undefined && <span className="text-foreground">{v.seats} seats</span>}
                      {v.seats !== undefined && v.iv ? ' · ' : ''}
                      {v.iv && `${v.iv.lo.toFixed(1)}–${v.iv.hi.toFixed(1)}`}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}

      <div className="grid grid-cols-[110px_1fr] gap-2">
        <span />
        <div className="flex items-center gap-2">
          <span className={LABEL_COL} /><span className={PCT_COL} />
          <div className="relative flex-1 h-3">
            {ticks(max).map(v => (
              <span key={v} className="absolute text-[9px] text-muted-foreground -translate-x-1/2"
                style={{ left: `${(v / max) * 100}%` }}>
                {v}{v === ticks(max)[ticks(max).length - 1] ? '% share' : ''}
              </span>
            ))}
          </div>
          <span className={GUTTER} />
        </div>
      </div>

      {anyRange && (
        <p className="text-[10px] text-muted-foreground pt-1.5">
          The bar is the simulated result. The dot is the average across resamples of the
          survey, and the two can differ because seats are won district by district —
          averaging many runs is not the same as running the average once.
        </p>
      )}
    </div>
  );
}
