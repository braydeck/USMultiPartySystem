import { useMemo } from 'react';
import { Card } from '@/components/ui/card';
import type { FDSenateSeat } from '../../types';
import { F5_ORDER } from '../../constants/parties';
import { SeatRangeStrip, RangeKey } from '../shared/SeatRangeStrip';
import { UncertaintyDetail } from '../shared/UncertaintyDetail';
import type { MethodUncertainty } from '../../lib/uncertainty';

// Built from the seat array so it always matches whatever states the model covers.
function fipsToAbbr(seats: FDSenateSeat[]): Record<string, string> {
  return Object.fromEntries(seats.map(s => [s.stateFips, s.stateAbbr]));
}

// Sampling-uncertainty companion to SenateCompositionCard, split into its own card so the
// headline modal bars stay uncluttered while the range material is still one scroll away.
// Party-line only: the Crossover pipeline has no bootstrap, so callers should gate this out
// there rather than relying on the undefined-props fallback (there is none — it renders nothing).
export function SenateRangeCard({ condSeats, condU, irvU, nDraws }: {
  condSeats: FDSenateSeat[];
  condU?: MethodUncertainty;
  irvU?: MethodUncertainty;
  nDraws?: number;
}) {
  const FIPS_TO_ABBR = useMemo(() => fipsToAbbr(condSeats), [condSeats]);

  // Condorcet and IRV strips sit stacked in this card specifically so a reader can compare
  // the two methods' bar positions at a glance; sharing one axis ceiling (rather than each
  // strip scaling to its own largest `hi`) is what makes that comparison honest.
  const rangeStripMax = useMemo(() => {
    const his = [
      ...Object.values(condU?.seats ?? {}).map(v => v.hi),
      ...Object.values(irvU?.seats ?? {}).map(v => v.hi),
    ];
    return his.length ? Math.max(1, ...his) : undefined;
  }, [condU, irvU]);

  if (!condU || !irvU || !nDraws) return null;

  return (
    <Card className="p-5 border-2 border-indigo-200 space-y-3">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
        How Much Could These Results Move?
      </h3>
      <p className="text-xs text-muted-foreground">
        Resampling turnout and preference noise many times over shows how far each party&apos;s seat count could swing.
      </p>
      {/* Full party order, not just the parties in the headline bars: a party with no modal
          seats can still have a real sampling range, and the strip is where that range shows up. */}
      {/* One key above the pair: the marks are identical in both strips. */}
      <RangeKey />
      <SeatRangeStrip seats={condU.seats} order={[...F5_ORDER]} max={rangeStripMax}
        label="Condorcet" />
      <SeatRangeStrip seats={irvU.seats} order={[...F5_ORDER]} max={rangeStripMax}
        label="IRV" />

      {/* Both methods, named: the card draws both strips and Condorcet is the Senate tab's
          default, so quoting one method's close-race count unlabelled reads as the other's. */}
      <p className="text-[11px] text-muted-foreground/80">
        Races close enough to flip on sampling alone: {condU.nBelow50} of{' '}
        {Object.keys(condU.states).length} under Condorcet, {irvU.nBelow50} of{' '}
        {Object.keys(irvU.states).length} under IRV.
      </p>
      <UncertaintyDetail seats={condU.seats} states={condU.states} nDraws={nDraws}
        label="Condorcet" stateLabel={f => FIPS_TO_ABBR[f] ?? f} />
      <UncertaintyDetail seats={irvU.seats} states={irvU.states} nDraws={nDraws}
        label="IRV" stateLabel={f => FIPS_TO_ABBR[f] ?? f} />
    </Card>
  );
}
