import type { HouseStateEntry } from '../../types';
import { Card } from '@/components/ui/card';
import { PARTY_COLORS, PARTY_NAMES, F5_ORDER, getContrastText } from '../../constants/parties';
import { SYSTEM_COLORS } from '../../constants/parties';
import { CARD_HEADING, CARD_HINT, MINOR_HEADING, FOOTNOTE } from '../../constants/typography';

/**
 * What the CES simulation elects in this state — the House delegation and the
 * Senate seat — shown once per state above the real-ballot races.
 *
 * The Senate half carries two winners because the simulation's IRV and Condorcet
 * tabulations disagree in some states, and which one you run is the whole question
 * the real races below are evidence about.
 */

export interface SenateSimResult {
  irvWinner: string | null;
  condorcetWinner: string | null;
}

function PartyChip({ code, label }: { code: string; label?: string }) {
  const bg = PARTY_COLORS[code] ?? '#6b7280';
  return (
    <span
      className="inline-flex items-center gap-1.5 text-sm font-bold px-2.5 py-1 rounded-full chip-text"
      style={{ backgroundColor: bg, color: getContrastText(bg) }}
      title={PARTY_NAMES[code] ?? code}
    >
      {code}
      {label && <span className="font-normal opacity-85">{label}</span>}
    </span>
  );
}

function seatTally(seats: Record<string, number>): string {
  return Object.entries(seats)
    .sort((a, b) => F5_ORDER.indexOf(a[0] as typeof F5_ORDER[number]) - F5_ORDER.indexOf(b[0] as typeof F5_ORDER[number]))
    .map(([party, n]) => `${n} ${PARTY_NAMES[party] ?? party}`)
    .join(' · ');
}

function SeatBar({ seats, total }: { seats: Record<string, number>; total: number }) {
  const ordered = Object.entries(seats).sort(
    (a, b) => F5_ORDER.indexOf(a[0] as typeof F5_ORDER[number]) - F5_ORDER.indexOf(b[0] as typeof F5_ORDER[number]),
  );
  return (
    <div className="flex rounded overflow-hidden" style={{ height: 32 }}>
      {ordered.map(([party, n]) => {
        const bg = PARTY_COLORS[party] ?? '#6b7280';
        return (
          <div
            key={party}
            title={`${PARTY_NAMES[party] ?? party}: ${n} of ${total} seats`}
            className="flex items-center justify-center"
            style={{ width: `${(n / total) * 100}%`, backgroundColor: bg, minWidth: 6 }}
          >
            <span className="text-xs font-bold chip-text" style={{ color: getContrastText(bg) }}>
              {party}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export function SimulationBanner({
  stateLabel, house, senate,
}: {
  stateLabel: string;
  house: HouseStateEntry | undefined;
  senate: SenateSimResult;
}) {
  if (!house) return null;
  const total = house.totalSeats;
  const today = total / 2;
  const parties = Object.keys(house.seats as Record<string, number>).length;
  const senateAgrees = senate.irvWinner && senate.irvWinner === senate.condorcetWinner;

  return (
    <Card className="p-4 space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h4 className={CARD_HEADING}>What the simulation elects in {stateLabel}</h4>
        <span className={CARD_HINT}>Ten-party slate, CES 2024 survey respondents</span>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <div className="flex items-baseline gap-2">
            <h5 className={MINOR_HEADING}>House delegation</h5>
            <span className={FOOTNOTE}>
              STV, {total} seats ({today} today × 2)
            </span>
          </div>
          <SeatBar seats={house.seats as Record<string, number>} total={total} />
          <p className={CARD_HINT}>
            {seatTally(house.seats as Record<string, number>)} — {parties} parties across{' '}
            {stateLabel}&apos;s {total} seats.
          </p>
        </div>

        <div className="space-y-1.5">
          <div className="flex items-baseline gap-2">
            <h5 className={MINOR_HEADING}>Senate seat</h5>
            <span className={FOOTNOTE}>Single winner, ten candidates</span>
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 pt-0.5">
            <div className="flex items-center gap-2">
              <span className="text-2xs font-bold uppercase tracking-wider" style={{ color: SYSTEM_COLORS.IRV }}>IRV</span>
              {senate.irvWinner ? <PartyChip code={senate.irvWinner} /> : <span className={CARD_HINT}>—</span>}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-2xs font-bold uppercase tracking-wider" style={{ color: SYSTEM_COLORS.Condorcet }}>Condorcet</span>
              {senate.condorcetWinner ? <PartyChip code={senate.condorcetWinner} /> : <span className={CARD_HINT}>—</span>}
            </div>
          </div>
          <p className={CARD_HINT}>
            {senateAgrees
              ? 'Both methods seat the same party.'
              : `IRV seats ${PARTY_NAMES[senate.irvWinner ?? ''] ?? senate.irvWinner}; the party that beats every rival head-to-head is ${PARTY_NAMES[senate.condorcetWinner ?? ''] ?? senate.condorcetWinner}.`}
          </p>
        </div>
      </div>
    </Card>
  );
}
