import { PARTY_COLORS, PARTY_NAMES } from '../../constants/parties';
import { PartyProfileCard } from '../shared/PartyProfileCard';
import { Card } from '@/components/ui/card';
import { ECBar } from './ECScenarioCards';
import type { ClusterProfile, TopTwoCell, TopTwoRoute } from '../../types';
import type { ECTally } from '../../lib/ecAllocation';
import { GROUP_LABEL, CARD_HINT, FOOTNOTE } from '../../constants/typography';

/**
 * What the top-two clause buys on its own, with states left free to go winner-take-all.
 *
 * One card per counting method. The full ballot's result is already above under National
 * Override, so these show only the winner-take-all case — the question this section asks is
 * whether dropping the proportionality clause changes anything, and the answer is a number, not
 * a second copy of the proportional result.
 */

const party = (code: string) => code.split('_')[0];
const colorOf = (code: string) => PARTY_COLORS[party(code)] ?? '#94a3b8';
const nameOf = (code: string) => PARTY_NAMES[party(code)] ?? party(code);

/** A route's winner-take-all tally in the shape ECBar draws, so both sections share one bar. */
function asTally(route: TopTwoRoute): ECTally {
  const byParty = [route.a, route.b]
    .map(code => ({ code, ev: route.wta[code] ?? 0 }))
    .sort((x, y) => y.ev - x.ev);
  return {
    method: 'fptp',
    states: [],
    byParty,
    total: route.totalEv,
    majority: route.majority,
    winner: route.wtaWinner,
  };
}

function RouteCard({ title, route, clusterByParty, label }: {
  title: string;
  route: TopTwoRoute;
  clusterByParty: Record<string, ClusterProfile>;
  label: (code: string) => string;
}) {
  const winner = route.wtaWinner;
  const cluster = winner ? clusterByParty[party(winner)] : undefined;
  // The margin the whole section turns on: how far the national two-way vote sits from the
  // 50% line where winner-take-all could start electing the runner-up.
  const cushion = route.popA - 50;
  return (
    <div className="space-y-2">
      <div>
        <h4 className={GROUP_LABEL}>{title} — {label(route.a)} v {label(route.b)}</h4>
        <p className={CARD_HINT}>
          {label(route.a)} takes {route.popA.toFixed(1)}% of the two-way vote.
        </p>
      </div>
      {winner && cluster
        ? <PartyProfileCard cluster={cluster} />
        : (
          <Card className="p-4 border-amber-300 bg-amber-50/40">
            <div className="text-sm font-semibold text-amber-900">No majority — decided by the House</div>
            <p className="text-xs text-amber-800 mt-1">
              Winner-take-all leaves neither finalist at {route.majority} electors.
            </p>
          </Card>
        )}
      <ECBar tally={asTally(route)} />
      <p className={FOOTNOTE}>
        {winner === route.a
          ? <>Elects the national {title} winner. </>
          : <>Does <span className="font-semibold text-amber-700">not</span> elect the national {title} winner. </>}
        Proportional allocation elects the same president here:{' '}
        <span style={{ color: colorOf(route.a) }} className="font-semibold">{nameOf(route.a)}</span>
        {' '}is {cushion.toFixed(1)} points clear of a tie, and the two allocation rules only
        pick different presidents in a near-tie.
      </p>
    </div>
  );
}

export function TopTwoScenarioCards({ cell, clusterByParty, label }: {
  cell: TopTwoCell;
  clusterByParty: Record<string, ClusterProfile>;
  label: (code: string) => string;
}) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 items-start">
      <RouteCard title="Condorcet" route={cell.condorcet} clusterByParty={clusterByParty} label={label} />
      <RouteCard title="IRV" route={cell.irv} clusterByParty={clusterByParty} label={label} />
    </div>
  );
}
