import { useMemo } from 'react';
import { PartyFlowHeatmap } from '../shared/PartyFlowMatrix';
import { ToggleGroup } from '../shared/ToggleGroup';
import { useUrlState } from '../../hooks/useUrlState';
import { overlapRows, similarityOrder } from '../../lib/partyOverlap';
import { orderRows } from '../../lib/partyFlow';
import { CARD_HEADING, CARD_HINT } from '../../constants/typography';
import { PARTY_NAMES } from '../../constants/parties';
import { Card } from '@/components/ui/card';

const AXES = { row: 'voters of', col: 'also fit' };
const SORTS = ['similarity', 'ideology'] as const;
type Sort = typeof SORTS[number];
const SORT_LABELS: Record<Sort, string> = { similarity: 'Similarity', ideology: 'Ideology' };

/** How much each party's voters also fit every other party, read off the same cluster
 *  membership probabilities that build the ranked ballots. Uses all five factors at once, so
 *  no overlap is created or hidden by projecting onto two axes. */
export function PartyOverlapMatrix() {
  const [sort, setSort] = useUrlState<Sort>('ovsort', 'similarity', { allowed: [...SORTS] });
  const rows = useMemo(() => overlapRows(), []);
  const ordered = useMemo(() => {
    if (sort === 'ideology') return orderRows(rows, 'ideology');
    const seq = similarityOrder(rows);
    return [...rows].sort((a, b) => seq.indexOf(a.party) - seq.indexOf(b.party));
  }, [rows, sort]);
  const example = useMemo(() => {
    const prg = rows.find(r => r.party === 'PRG');
    const top = prg && [...prg.segments].sort((a, b) => b.share - a.share)[0];
    return prg && top
      ? `Progressive voters average ${Math.round((prg.selfShare ?? 0) * 100)}% Progressive and ${Math.round(top.share * 100)}% ${PARTY_NAMES[top.party]}.`
      : '';
  }, [rows]);

  return (
    <Card className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-2 mb-3">
        <div className="max-w-2xl">
          <h4 className={`${CARD_HEADING} mb-1`}>Party Overlap</h4>
          <p className={`${CARD_HINT} leading-relaxed`}>
            Each row is one party's voters. The model gives every voter a probability of belonging to
            each party, and a cell is the average of those probabilities across the row party's
            voters. {example} Overlap here counts all five factors at once.
          </p>
        </div>
        <ToggleGroup label="Order" value={sort} onChange={setSort} options={SORTS} labels={SORT_LABELS} />
      </div>
      <PartyFlowHeatmap rows={ordered} axes={AXES} selfLabel="Own" />
    </Card>
  );
}
