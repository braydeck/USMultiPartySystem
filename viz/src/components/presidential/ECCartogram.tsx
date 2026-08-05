import { useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { PARTY_NAMES } from '../../constants/parties';
import { partyOf } from '../../lib/stateTiles';
import {
  EC_METHODS, EC_METHOD_LABELS, EC_METHOD_BLURB,
  type ECMethod, type ECTally,
} from '../../lib/ecAllocation';
import { CartogramPanel, type CartogramView } from './CartogramPanel';
import { FIELD_LABEL } from '../../constants/typography';

/**
 * The four elector rules, on the electoral basis: 975 tiles, one per elector, states scaled to
 * electoral weight rather than population, so the two senatorial electors every state gets are
 * part of the shape.
 *
 * First-choice share used to be a fifth view here. It moved to the top-two map, where the
 * unallocated vote is the baseline the two allocations get read against; every view here is an
 * allocation, so the control is a flat list of four.
 */

const nameOf = (code: string) => PARTY_NAMES[partyOf(code)] ?? partyOf(code);

interface Props {
  tallies: Record<ECMethod, ECTally>;
  mapView: ECMethod;
  onMapView: (v: ECMethod) => void;
}

export function ECCartogram({ tallies, mapView, onMapView }: Props) {
  const tally = tallies[mapView];

  const view = useMemo<CartogramView>(() => {
    const countsByAbbr: Record<string, Record<string, number>> = {};
    const evByAbbr: Record<string, number> = {};
    for (const s of tally.states) {
      countsByAbbr[s.abbr] = s.electors;
      evByAbbr[s.abbr] = s.ev;
    }
    return {
      basis: 'ec',
      countsByAbbr,
      apportion: false,
      evByAbbr,
      totals: tally.byParty.map(p => ({ code: p.code, value: p.ev })),
      majority: tally.majority,
      format: String,
      perStateSuffix: abbr => ` · ${evByAbbr[abbr] ?? 0} electors`,
      nationalLabel: `${tally.total} electors`,
      summary: `${tally.majority} of ${tally.total} electors wins. `
        + (tally.winner ? `${nameOf(tally.winner)} clears it.` : 'Nobody clears it, so the House decides.'),
      blurb: EC_METHOD_BLURB[mapView],
      footnote: 'One hexagon = one elector. States are sized by electoral votes.',
      ariaLabel: 'Electoral college cartogram',
      subject: 'elector map',
    };
  }, [tally, mapView]);

  return (
    <CartogramPanel view={view}>
      <div className="flex flex-wrap items-center gap-2">
        <span className={FIELD_LABEL}>View</span>
        <div className="flex flex-wrap gap-1">
          {EC_METHODS.map(v => (
            <Button key={v} onClick={() => onMapView(v)} size="sm"
              variant={mapView === v ? 'default' : 'secondary'}>
              {EC_METHOD_LABELS[v]}
            </Button>
          ))}
        </div>
      </div>
    </CartogramPanel>
  );
}
