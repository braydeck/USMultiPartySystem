import { useContext, useMemo } from 'react';
import type { HouseSeat } from '../../types';
import { CLUSTER_TO_PARTY, PARTY_NAMES, PARTY_COLORS, F5_ORDER_WFP as F5_ORDER, getContrastText } from '../../constants/parties';
import { useElementWidth } from '../../hooks/useElementWidth';
import { CARD_HEADING } from '../../constants/typography';
import { MajorityMark, MajorityLine } from '../shared/MajorityMark';
import { DissolveCompareContext } from '../../lib/dissolveCompare';

// 2024 House composition (approximate)
const FPTP_HOUSE = { GOP: 220, DEM: 215 };
const FPTP_TOTAL = FPTP_HOUSE.GOP + FPTP_HOUSE.DEM;

// 2024 House popular vote, GOP ~51.7%, DEM ~46.9%. The votes strip over today's bar shows the
// two-party split (GOP 52.4%, DEM 47.6%), which a proportional count would turn into 228 and 207 seats.
const FPTP_VOTE = { GOP: 51.7, DEM: 46.9 };
export const DEM_COLOR = '#1d4ed8', GOP_COLOR = '#dc2626';
const VOTES_STRIP_HEIGHT = 6;

// Shared with SenateCompositionCard so every seat-share bar in the app reads at the same scale.
// The label sits above the bar (not beside it), so the bar itself gets the full row width —
// more room for segment labels, especially on narrow screens. Bar height is shorter than the
// old side-label layout to offset the label line's added vertical space.
export const BAR_HEIGHT = 40;
/** Height of today's two-party reference bar: about half a simulated bar, since it is the reference. */
export const TODAY_BAR_HEIGHT = 22;

// Keep in sync with the `@container (min-width: …)` rule for `.seat-segment-label` in index.css —
// that's what actually hides an inline segment label; this is the JS-side mirror of the same
// threshold, used to decide which parties are worth repeating in the legend below.
export const LABEL_MIN_WIDTH = 25;

interface Props {
  seats: HouseSeat[];
  /** First-choice vote share by party code, in percent; draws a votes strip over each simulated bar. */
  voteShare?: Record<string, number>;
  systemLabel: 'STV' | 'Party List' | 'MMP';
  /** The other proportional system's seats at the current Wyoming rule — a 4th row in double-Wyoming view. */
  otherSystemSeats?: HouseSeat[];
  otherSystemLabel?: 'STV' | 'Party List' | 'MMP';
  /** This system's seats under double-Wyoming — the comparison row in triple-Wyoming view. */
  doubleSeats?: HouseSeat[];
  wyoming?: 'double' | 'triple';
  /** Extra system bars rendered after the primary, before the double-Wyoming comparison. */
  extraBars?: { label: string; seats: HouseSeat[] }[];
}

function buildSegments(seats: HouseSeat[]): { party: string; seats: number }[] {
  const segments: { party: string; seats: number }[] = [];
  for (const party of F5_ORDER) {
    const clusterId = Object.entries(CLUSTER_TO_PARTY).find(([, p]) => p === party)?.[0];
    if (!clusterId) continue;
    const row = seats.find(s => String(s.party) === clusterId);
    if (row && row.national > 0) segments.push({ party, seats: row.national });
  }
  return segments;
}

// Parties whose rendered sliver would fall under LABEL_MIN_WIDTH in this bar — i.e. the ones
// whose inline label the container query is hiding, and so are worth surfacing in the legend.
function smallPartiesIn(segments: { party: string; seats: number }[], total: number, barWidth: number): Set<string> {
  const set = new Set<string>();
  if (!barWidth || !total) return set;
  for (const s of segments) {
    const pxWidth = (s.seats / total) * barWidth;
    if (pxWidth < LABEL_MIN_WIDTH) set.add(s.party);
  }
  return set;
}

function BarLabel({ label, total, faded = false, note }: { label: string; total: number; faded?: boolean; note?: string }) {
  return (
    <div className="flex items-baseline gap-1.5 mb-1">
      <span className={`text-xs font-semibold ${faded ? 'text-muted-foreground' : 'text-foreground'}`}>{label}</span>
      <span className="text-xs text-muted-foreground">· {total} seats</span>
      {note && <span className="ml-auto text-xs text-muted-foreground">{note}</span>}
    </div>
  );
}

/** The thin strip of vote shares that sits over a seat bar, so seats read against the votes behind them. */
function VotesStrip({ shares }: { shares: { key: string; pct: number; color: string; title: string }[] }) {
  const total = shares.reduce((s, x) => s + x.pct, 0);
  if (!total) return null;
  return (
    <div className="flex rounded-sm overflow-hidden mb-0.5" style={{ height: VOTES_STRIP_HEIGHT }}>
      {shares.map(x => (
        <div key={x.key} title={x.title}
          style={{ width: `${(x.pct / total) * 100}%`, backgroundColor: x.color }} />
      ))}
    </div>
  );
}

function partyVotes(voteShare: Record<string, number>) {
  return F5_ORDER.filter(p => (voteShare[p] ?? 0) > 0).map(p => ({
    key: p, pct: voteShare[p], color: PARTY_COLORS[p] ?? '#6b7280',
    title: `${PARTY_NAMES[p] ?? p}: ${voteShare[p].toFixed(1)}% of first-choice votes`,
  }));
}

function SeatBar({ label, total, segments, faded = false, voteShare }: {
  label: string; total: number; segments: { party: string; seats: number }[]; faded?: boolean;
  voteShare?: Record<string, number>;
}) {
  return (
    <div>
      <BarLabel label={label} total={total} faded={faded}
        note={voteShare ? 'strip: first-choice votes · bar: seats' : undefined} />
      <div className="relative">
        <MajorityMark />
        <MajorityLine />
        {voteShare && <VotesStrip shares={partyVotes(voteShare)} />}
        <div className={`flex rounded-lg overflow-hidden ${faded ? 'opacity-60' : ''}`} style={{ height: BAR_HEIGHT }}>
          {segments.map(({ party, seats: n }) => {
            const pct = (n / total) * 100;
            const color = PARTY_COLORS[party] ?? '#6b7280';
            return (
              <div
                key={party}
                title={`${PARTY_NAMES[party] ?? party}: ${n} seats (${pct.toFixed(1)}%)`}
                className="seat-segment flex min-w-0 items-center justify-center overflow-hidden"
                style={{ width: `${pct}%`, backgroundColor: color, minWidth: pct < 3 ? 2 : 0 }}
              >
                <span className="seat-segment-label text-xs font-bold leading-tight text-center px-0.5 chip-text" style={{ color: getContrastText(color) }}>
                  {party}<br />{pct.toFixed(1)}%
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/** Today's House: the two-party vote as a strip over the seats it produced. Half the height of a
 *  simulated bar, since it is the reference rather than the result. */
function TodayBar() {
  const { DEM: dem, GOP: gop } = FPTP_HOUSE;
  const twoParty = FPTP_VOTE.DEM + FPTP_VOTE.GOP;
  const demVote = (FPTP_VOTE.DEM / twoParty) * 100, gopVote = (FPTP_VOTE.GOP / twoParty) * 100;
  return (
    <div>
      <BarLabel label="Today's House" total={FPTP_TOTAL} note="strip: votes · bar: seats" />
      <div className="relative">
        <MajorityMark />
        <MajorityLine />
        <VotesStrip shares={[
          { key: 'DEM', pct: demVote, color: DEM_COLOR, title: `Democrats: ${demVote.toFixed(1)}% of the two-party vote, 207 seats if counted proportionally` },
          { key: 'GOP', pct: gopVote, color: GOP_COLOR, title: `Republicans: ${gopVote.toFixed(1)}% of the two-party vote, 228 seats if counted proportionally` },
        ]} />
        <div className="flex rounded-md overflow-hidden" style={{ height: TODAY_BAR_HEIGHT }}>
          <div className="flex items-center justify-center" title={`Democrats: ${dem} seats`}
            style={{ width: `${(dem / FPTP_TOTAL) * 100}%`, backgroundColor: DEM_COLOR }}>
            <span className="text-white text-xs font-bold">Dem {dem} ({((dem / FPTP_TOTAL) * 100).toFixed(0)}%)</span>
          </div>
          <div className="flex items-center justify-center" title={`Republicans: ${gop} seats`}
            style={{ width: `${(gop / FPTP_TOTAL) * 100}%`, backgroundColor: GOP_COLOR }}>
            <span className="text-white text-xs font-bold">Rep {gop} ({((gop / FPTP_TOTAL) * 100).toFixed(0)}%)</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function Legend({ label, segments, smallParties }: {
  label: string; segments: { party: string; seats: number }[]; smallParties: Set<string>;
}) {
  const total = segments.reduce((s, r) => s + r.seats, 0);
  const shown = segments.filter(s => smallParties.has(s.party));
  if (!shown.length) return null;
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
      <span className="shrink-0 text-xs font-semibold text-foreground" style={{ width: 68 }}>{label}</span>
      {shown.map(({ party, seats: n }) => (
        <span key={party} className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: PARTY_COLORS[party] ?? '#6b7280' }} />
          <span className="text-xs text-foreground font-semibold">{party}</span>
          <span className="text-xs text-muted-foreground">{total ? (n / total * 100).toFixed(1) : '0.0'}%</span>
        </span>
      ))}
    </div>
  );
}

export function FPTPvsSTV({ seats, voteShare, systemLabel, otherSystemSeats, otherSystemLabel, doubleSeats, wyoming = 'double', extraBars }: Props) {
  const [rootRef, rootWidth] = useElementWidth<HTMLDivElement>();
  // With parties dissolved, the full field replaces today's FPTP and two-party PR bars.
  const cmp = useContext(DissolveCompareContext);
  const fullSeats = cmp?.dissolved.length ? cmp.full[systemLabel] : undefined;
  const fullTotal = fullSeats?.reduce((s, r) => s + r.national, 0) ?? 0;
  const fullSegments = useMemo(() => (fullSeats && fullTotal > 0 ? buildSegments(fullSeats) : null), [fullSeats, fullTotal]);
  const without = cmp ? `without ${cmp.dissolved.join(', ')}` : '';

  const total = seats.reduce((s, r) => s + r.national, 0);
  const segments = buildSegments(seats);

  const otherTotal = otherSystemSeats?.reduce((s, r) => s + r.national, 0) ?? 0;
  const otherSegments = otherSystemSeats && otherTotal > 0 ? buildSegments(otherSystemSeats) : null;

  const dblTotal = doubleSeats?.reduce((s, r) => s + r.national, 0) ?? 0;
  const dblSegments = doubleSeats && dblTotal > 0 ? buildSegments(doubleSeats) : null;

  const extraBuilt = useMemo(() => (extraBars ?? []).map(b => ({
    label: b.label,
    total: b.seats.reduce((s, r) => s + r.national, 0),
    segments: buildSegments(b.seats),
  })).filter(b => b.total > 0), [extraBars]);

  const isTriple = wyoming === 'triple';

  const allLabels = [systemLabel, ...(otherSystemLabel && !isTriple ? [otherSystemLabel] : []), ...extraBuilt.map(b => b.label)];
  const title = fullSegments
    ? `Full Field vs ${without[0].toUpperCase()}${without.slice(1)}`
    : isTriple
    ? `${systemLabel} — Double vs Triple Wyoming`
    : `FPTP vs ${allLabels.join(' vs ')}`;

  // Union of parties whose sliver is too narrow for its inline label in any bar.
  const smallParties = useMemo(() => {
    const sets = [smallPartiesIn(segments, total, rootWidth)];
    if (isTriple && dblSegments) sets.push(smallPartiesIn(dblSegments, dblTotal, rootWidth));
    if (!isTriple && otherSegments) sets.push(smallPartiesIn(otherSegments, otherTotal, rootWidth));
    for (const b of extraBuilt) sets.push(smallPartiesIn(b.segments, b.total, rootWidth));
    if (fullSegments) sets.push(smallPartiesIn(fullSegments, fullTotal, rootWidth));
    const merged = new Set<string>();
    for (const s of sets) for (const p of s) merged.add(p);
    return merged;
  }, [segments, total, otherSegments, otherTotal, dblSegments, dblTotal, extraBuilt, isTriple, rootWidth, fullSegments, fullTotal]);

  return (
    <div ref={rootRef} className="space-y-3">
      <h4 className={`${CARD_HEADING} mb-1`}>
        {title}
      </h4>

      {fullSegments ? <>
        <SeatBar label={`${systemLabel} · full field`} total={fullTotal} segments={fullSegments} />
        <SeatBar label={`${systemLabel} · ${without}`} total={total} segments={segments} />
      </> : <>
        <TodayBar />
        <SeatBar label={isTriple ? `${systemLabel} (triple)` : `${systemLabel} (sim)`} total={total} segments={segments} voteShare={voteShare} />
      </>}
      {!isTriple && otherSegments && <SeatBar label={`${otherSystemLabel} (sim)`} total={otherTotal} segments={otherSegments} voteShare={voteShare} />}
      {extraBuilt.map(b => <SeatBar key={b.label} label={b.label} total={b.total} segments={b.segments} voteShare={voteShare} />)}
      {isTriple && dblSegments && <SeatBar label={`${systemLabel} (double)`} total={dblTotal} segments={dblSegments} faded />}

      {smallParties.size > 0 && (
        <div className="mt-3 pt-2 border-t border-border/50">
          <Legend label={systemLabel} segments={segments} smallParties={smallParties} />
        </div>
      )}
    </div>
  );
}
