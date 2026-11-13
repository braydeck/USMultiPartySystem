import { useMemo } from 'react';
import { delegations, delegationSeats, SPLIT_THRESHOLD_PP } from '../../lib/senateDelegations';
import { Card } from '@/components/ui/card';
import type { FDSenateSeat } from '../../types';
import { PARTY_COLORS, PARTY_NAMES, F5_ORDER, getContrastText } from '../../constants/parties';
import { BAR_HEIGHT, LABEL_MIN_WIDTH, TODAY_BAR_HEIGHT, DEM_COLOR, GOP_COLOR } from '../house/FPTPvsSTV';
import { useElementWidth } from '../../hooks/useElementWidth';
import type { MethodUncertainty } from '../../lib/uncertainty';
import { CARD_HEADING, FOOTNOTE } from '../../constants/typography';
import { MajorityMark, MajorityLine } from '../shared/MajorityMark';

// Shared "FPTP Today vs Preferential Senate" composition card, used by both the Senate tab
// and the Overview summary so the two charts are identical. Condorcet/IRV model one winner
// per state; ×2 fills both of a state's seats for a full-chamber view.
function SenateCompBar({ label, seats, segments, total: totalOverride, multiplier = 1 }: {
  label: string;
  seats?: FDSenateSeat[];
  segments?: { party: string; n: number; color: string }[];
  total?: number;
  multiplier?: number;
}) {
  const segs = segments ?? (() => {
    const counts: Record<string, number> = {};
    for (const s of seats ?? []) {
      const p = s.senatorParty ?? s.senatorCode.split('_')[0];
      counts[p] = (counts[p] ?? 0) + 1;
    }
    return F5_ORDER.filter(p => counts[p] > 0).map(p => ({
      party: p, n: counts[p] * multiplier, color: PARTY_COLORS[p] ?? '#6b7280',
    }));
  })();
  const total = totalOverride ?? segs.reduce((s, x) => s + x.n, 0);

  return (
    <div>
      <div className="flex items-baseline gap-1.5 mb-1">
        <span className="text-xs font-semibold text-foreground">{label}</span>
        <span className="text-xs text-muted-foreground">· {total} seats</span>
      </div>
      <div className="relative">
        <MajorityMark />
        <MajorityLine />
        <div className="flex rounded-lg overflow-hidden" style={{ height: BAR_HEIGHT }}>
          {segs.map(({ party, n, color }) => {
            const pct = (n / total) * 100;
            return (
              <div key={party}
                title={`${PARTY_NAMES[party] ?? party}: ${n} seats (${pct.toFixed(0)}%)`}
                className="seat-segment flex min-w-0 items-center justify-center overflow-hidden"
                style={{ width: `${pct}%`, backgroundColor: color, minWidth: pct < 3 ? 2 : 0 }}>
                <span className="seat-segment-label text-xs font-bold leading-tight text-center px-0.5 chip-text"
                  style={{ color: getContrastText(color) }}>
                  {party}<br />{n}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// 2025 Senate: 47 Democrats (independents who caucus with them included) and 53 Republicans.
const TODAY_SENATE = { DEM: 47, GOP: 53 };

/** Today's Senate at the height of the House card's two-party reference bar, so the two cards match. */
function TodaySenateBar() {
  const { DEM: dem, GOP: gop } = TODAY_SENATE, total = dem + gop;
  return (
    <div>
      <div className="flex items-baseline gap-1.5 mb-1">
        <span className="text-xs font-semibold text-foreground">Today's Senate</span>
        <span className="text-xs text-muted-foreground">· {total} seats</span>
      </div>
      <div className="relative">
        <MajorityMark />
        <MajorityLine />
        <div className="flex rounded-md overflow-hidden" style={{ height: TODAY_BAR_HEIGHT }}>
          <div className="flex items-center justify-center" title={`Democrats: ${dem} seats`}
            style={{ width: `${dem}%`, backgroundColor: DEM_COLOR }}>
            <span className="text-white text-xs font-bold">Dem {dem} ({dem}%)</span>
          </div>
          <div className="flex items-center justify-center" title={`Republicans: ${gop} seats`}
            style={{ width: `${gop}%`, backgroundColor: GOP_COLOR }}>
            <span className="text-white text-xs font-bold">Rep {gop} ({gop}%)</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/** Seats per party on the 102 basis, with the split rule where resampling exists: a state whose
 *  winner changes from sample to sample sends one senator of each party, because its two seats are
 *  decided by two electorates six years apart. Elsewhere the single modelled winner, doubled. */
function chamber(seats: FDSenateSeat[], u?: MethodUncertainty): { counts: Record<string, number>; total: number; split: number } {
  if (u) {
    const d = delegationSeats(u.states);
    return { counts: d, total: Object.values(d).reduce((a, b) => a + b, 0),
      split: delegations(u.states).filter(x => x.split).length };
  }
  const c: Record<string, number> = {};
  for (const s of seats) {
    const p = s.senatorParty ?? s.senatorCode.split('_')[0];
    c[p] = (c[p] ?? 0) + 2;
  }
  return { counts: c, total: seats.length * 2, split: 0 };
}

interface ChamberInput { condSeats: FDSenateSeat[]; irvSeats: FDSenateSeat[]; condU?: MethodUncertainty; irvU?: MethodUncertainty }

/** With `fullField`, the bars compare the full field against the dissolved one (`dissolved` names
 *  the parties out) under each method, in place of today's FPTP chamber. */
export function SenateCompositionCard({ condSeats, irvSeats, condU, irvU, fullField, dissolved }: ChamberInput & {
  fullField?: ChamberInput;
  dissolved?: string[];
}) {
  const [rootRef, rootWidth] = useElementWidth<HTMLDivElement>();

  const bars = useMemo(() => {
    const cond = chamber(condSeats, condU), irv = chamber(irvSeats, irvU);
    if (fullField && dissolved?.length) {
      const fc = chamber(fullField.condSeats, fullField.condU), fi = chamber(fullField.irvSeats, fullField.irvU);
      const tag = `without ${dissolved.join(', ')}`;
      return [
        { label: 'Condorcet · full field', ...fc }, { label: `Condorcet · ${tag}`, ...cond },
        { label: 'IRV · full field', ...fi }, { label: `IRV · ${tag}`, ...irv },
      ];
    }
    return [{ label: 'Condorcet ×2', ...cond }, { label: 'IRV ×2', ...irv }];
  }, [condSeats, irvSeats, condU, irvU, fullField, dissolved]);
  const comparing = bars.length === 4;

  // Parties whose sliver is too narrow for its inline label in any bar, listed below with their
  // count in every bar (an explicit 0 where a bar lacks them).
  const shownRows = useMemo(() => {
    if (!rootWidth) return [];
    const small = new Set<string>();
    for (const b of bars) for (const [p, n] of Object.entries(b.counts)) {
      if (n > 0 && b.total && (n / b.total) * rootWidth < LABEL_MIN_WIDTH) small.add(p);
    }
    return F5_ORDER.filter(p => small.has(p));
  }, [bars, rootWidth]);

  return (
    <Card ref={rootRef} className="p-5 space-y-3">
      <h4 className={`${CARD_HEADING} mb-1`}>
        {comparing ? 'Full Field vs Dissolved Senate' : 'FPTP Today vs Preferential Senate'}
      </h4>
      {!comparing && <TodaySenateBar />}
      {bars.map(b => (
        <SenateCompBar key={b.label} label={b.label} total={b.total}
          segments={F5_ORDER.filter(p => (b.counts[p] ?? 0) > 0)
            .map(p => ({ party: p, n: b.counts[p], color: PARTY_COLORS[p] ?? '#6b7280' }))} />
      ))}

      {/* Legend — a combined row per party, shown only for slivers too narrow for their inline
          label; a plainly legible bar segment doesn't need restating below. */}
      {shownRows.length > 0 && (
        <div className="space-y-1 pt-2 border-t border-border/50">
          <div className="text-xs font-semibold text-foreground">{comparing ? 'Condorcet full / dissolved · IRV full / dissolved' : 'Condorcet / IRV'}</div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            {shownRows.map(p => (
              <span key={p} className="flex items-center gap-1.5" title={PARTY_NAMES[p] ?? p}>
                <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: PARTY_COLORS[p] ?? '#6b7280' }} />
                <span className="text-xs text-foreground font-semibold">{p}</span>
                <span className="text-xs text-muted-foreground">{bars.map(b => b.counts[p] ?? 0).join('/')}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      <p className={FOOTNOTE}>
        Two seats per state, {bars[0].total} in all.{' '}
        {comparing
          ? `In the full field a state splits its delegation when its top two parties finish within ${SPLIT_THRESHOLD_PP} points across resamples; with parties dissolved, each state's winner holds both seats.`
          : <>A state splits its delegation when its top two parties finish within {SPLIT_THRESHOLD_PP} points across resamples
            {bars[0].split > 0 && `: ${bars[0].split} under Condorcet, ${bars[1].split} under IRV`}.</>}
      </p>
    </Card>
  );
}
