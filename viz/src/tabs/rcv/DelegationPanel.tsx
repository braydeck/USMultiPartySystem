import type { HouseStateEntry, RCVRace } from '../../types';
import { Card } from '@/components/ui/card';
import { PARTY_COLORS, PARTY_NAMES, F5_ORDER, SYSTEM_COLORS, getContrastText } from '../../constants/parties';
import { CARD_HEADING, CARD_HINT, MINOR_HEADING, FOOTNOTE } from '../../constants/typography';
import { BALLOT_PARTY_NAMES, partyColor } from './ballotParties';

/**
 * The doubled-seat delegation this project proposes for the state, against the
 * single-winner seats it elects today.
 *
 * Maine's districts are combined rather than doubled separately: two 2-seat
 * districts would each still be a near-lock, so the proposal pools them into one
 * 4-seat delegation. That is the whole reason a per-race STV panel made no sense
 * here, and the diagram is where it gets said.
 */

interface SeatCard {
  label: string;
  sublabel: string;
  /** Ballot-line party codes (D/R/I…) for today's seats. */
  seats: { code: string; name?: string }[];
  ballotLine: boolean;
}

function SeatRow({ card }: { card: SeatCard }) {
  const colorOf = (code: string) =>
    card.ballotLine ? partyColor(code) : PARTY_COLORS[code] ?? '#6b7280';
  const nameOf = (code: string) =>
    (card.ballotLine ? BALLOT_PARTY_NAMES[code] : PARTY_NAMES[code]) ?? code;

  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2.5 space-y-1.5">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-xs font-semibold text-foreground">{card.label}</span>
        <span className={FOOTNOTE}>{card.sublabel}</span>
      </div>
      <div className="flex gap-1">
        {card.seats.map((s, i) => {
          const bg = colorOf(s.code);
          return (
            <div
              key={i}
              className="flex-1 rounded flex items-center justify-center py-1.5 min-w-0"
              style={{ backgroundColor: bg }}
              title={`${nameOf(s.code)}${s.name ? ` — ${s.name}` : ''}`}
            >
              <span className="text-2xs font-bold chip-text truncate px-1" style={{ color: getContrastText(bg) }}>
                {s.code}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Arrow() {
  return (
    <div className="flex items-center justify-center py-1 sm:py-0">
      <span className="text-muted-foreground text-lg leading-none rotate-90 sm:rotate-0">→</span>
    </div>
  );
}

/** Alaska's real-ballot STV at 2 seats, one row per election that has ranked ballots. */
function RealBallotStv({ races }: { races: RCVRace[] }) {
  const withStv = races.filter(r => r.stvElected && r.stvElected.length > 0);
  if (withStv.length === 0) return null;

  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline gap-2">
        <h5 className={MINOR_HEADING}>Same ballots, two seats</h5>
        <span className={FOOTNOTE}>STV re-run on each election&apos;s cast vote record</span>
      </div>
      <div className="space-y-1">
        {withStv.map(race => {
          const elected = race.stvElected!;
          return (
            <div key={`${race.year}-${race.raceName}`} className="flex flex-wrap items-center gap-2">
              <span className="text-2xs text-muted-foreground tabular-nums w-32 shrink-0">
                {race.year} {race.raceName.includes('special') ? 'special' : 'general'}
              </span>
              <div className="flex flex-wrap gap-1">
                {elected.map(cand => {
                  const bg = partyColor(race.parties[cand]);
                  return (
                    <span
                      key={cand}
                      className="text-2xs font-semibold px-2 py-0.5 rounded-full chip-text"
                      style={{ backgroundColor: bg, color: getContrastText(bg) }}
                    >
                      {cand}
                    </span>
                  );
                })}
              </div>
              <span className={FOOTNOTE}>
                IRV seated {race.irvWinner} alone
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function simSeats(house: HouseStateEntry): { code: string }[] {
  const entries = Object.entries(house.seats as Record<string, number>).sort(
    (a, b) => F5_ORDER.indexOf(a[0] as typeof F5_ORDER[number]) - F5_ORDER.indexOf(b[0] as typeof F5_ORDER[number]),
  );
  return entries.flatMap(([party, n]) => Array.from({ length: n }, () => ({ code: party })));
}

export function DelegationPanel({
  stateAbbr, house, races,
}: {
  stateAbbr: 'AK' | 'ME';
  house: HouseStateEntry | undefined;
  races: RCVRace[];
}) {
  if (!house) return null;
  const total = house.totalSeats;

  const today: SeatCard[] = stateAbbr === 'ME'
    ? [
        { label: 'CD1', sublabel: 'Portland and the coast', seats: [{ code: 'D', name: 'Chellie Pingree' }], ballotLine: true },
        { label: 'CD2', sublabel: 'Rural interior', seats: [{ code: 'D', name: 'Jared Golden' }], ballotLine: true },
      ]
    : [
        { label: 'At-large', sublabel: 'One seat statewide', seats: [{ code: 'R', name: 'Nick Begich III' }], ballotLine: true },
      ];

  const proposed: SeatCard = {
    label: stateAbbr === 'ME' ? 'One 4-seat delegation' : 'One 2-seat delegation',
    sublabel: `STV, ${total} seats`,
    seats: simSeats(house),
    ballotLine: false,
  };

  return (
    <Card className="p-4 space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h4 className={CARD_HEADING}>
          {stateAbbr === 'ME' ? 'Two districts become one 4-seat delegation' : 'One seat becomes two'}
        </h4>
        <span className="text-2xs font-bold uppercase tracking-wider" style={{ color: SYSTEM_COLORS.STV }}>STV</span>
      </div>

      {/* Stacks below sm: three columns at 400px squeezes the proposed delegation
          into unreadable slivers. */}
      <div className="flex flex-col sm:grid gap-x-3 gap-y-1" style={{ gridTemplateColumns: 'minmax(0,1fr) auto minmax(0,1fr)' }}>
        <h5 className={MINOR_HEADING}>Today</h5>
        <div className="hidden sm:block" />
        <h5 className={`${MINOR_HEADING} hidden sm:block`}>Proposed</h5>
        <div className="space-y-2">
          {today.map(card => <SeatRow key={card.label} card={card} />)}
        </div>
        <Arrow />
        <div className="space-y-1">
          <h5 className={`${MINOR_HEADING} sm:hidden`}>Proposed</h5>
          <SeatRow card={proposed} />
        </div>
      </div>

      <p className={CARD_HINT}>
        {stateAbbr === 'ME'
          ? `Doubling each district separately leaves two 2-seat races that Democrats win in CD1 and split in CD2, so the proposal pools both into a single statewide 4-seat delegation. The simulation fills it with ${Object.keys(house.seats as Record<string, number>).length} parties.`
          : 'Alaska already votes statewide, so its one at-large seat simply becomes two. That is enough for a second party to reach quota.'}
      </p>

      {stateAbbr === 'AK' && <RealBallotStv races={races} />}
    </Card>
  );
}
