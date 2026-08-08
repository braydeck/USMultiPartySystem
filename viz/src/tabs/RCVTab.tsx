import { useState } from 'react';
import { useUrlState } from '../hooks/useUrlState';
import type { RCVData, RCVRace, HouseStateEntry, SenateIrvRoundsData } from '../types';
import { Card } from '@/components/ui/card';
import { ToggleGroup } from '../components/shared/ToggleGroup';
import { StickyControlBar } from '../components/shared/StickyControlBar';
import { PAGE_TITLE, SECTION_HEADING, CARD_HINT, FOOTNOTE } from '../constants/typography';
import { CoveragePanel } from './rcv/CoveragePanel';
import { SimulationBanner, type SenateSimResult } from './rcv/SimulationBanner';
import { DelegationPanel } from './rcv/DelegationPanel';
import { RaceCard } from './rcv/RaceCard';

// The simulation's own baseline (no participation adjustment), matching the
// houseStateMap this tab is handed.
import senateIrvData from '../data/senateIrvRounds.json';
import senateCondorcetData from '../data/senateCondorcet.json';

const FIPS: Record<'AK' | 'ME', string> = { AK: '02', ME: '23' };
const STATE_LABEL: Record<'AK' | 'ME', string> = { AK: 'Alaska', ME: 'Maine' };

const senateIrv = senateIrvData as unknown as SenateIrvRoundsData;
const senateCondorcet = senateCondorcetData as unknown as {
  states: Record<string, { abbr: string; winner: string | null }>;
};

interface Props {
  data: RCVData;
  houseStateMap: Record<string, HouseStateEntry>;
}

/** Trim the "_1" candidate suffix the senate simulation uses down to the party code. */
function partyOf(code: string | null | undefined): string | null {
  return code ? code.split('_')[0] : null;
}

function raceKey(race: RCVRace): string {
  return `${race.year}-${race.contestType}-${race.office}-${race.raceName}`;
}

export function RCVTab({ data, houseStateMap }: Props) {
  const [stateTab, setStateTab] = useUrlState<'AK' | 'ME'>('rcvState', 'AK', { allowed: ['AK', 'ME'] });
  const [openRace, setOpenRace] = useState<string | null>(null);

  const races = data[stateTab];
  const stateLabel = STATE_LABEL[stateTab];
  const fips = FIPS[stateTab];

  const tabulated = races.filter(r => r.irvRounds.length > 1);
  const generals = tabulated.filter(r => r.contestType === 'GENERAL');
  const primaries = tabulated.filter(r => r.contestType !== 'GENERAL');
  const decidedFirstRound = races.filter(r => r.irvRounds.length === 1);

  const condorcetKnown = tabulated.filter(r => r.condorcetAvailable !== false);
  const condorcetFailures = tabulated.filter(r => r.irvMatchesCondorcet === false);
  const transferFlips = tabulated.filter(r => !r.irvMatchesPlurality);

  const senate: SenateSimResult = {
    irvWinner: partyOf(senateIrv.states[fips]?.winner),
    condorcetWinner: partyOf(senateCondorcet.states[fips]?.winner),
  };

  function toggle(race: RCVRace) {
    const key = raceKey(race);
    setOpenRace(cur => (cur === key ? null : key));
  }

  function renderGroup(title: string, group: RCVRace[], note?: string) {
    if (group.length === 0) return null;
    return (
      <div className="space-y-2">
        <div className="flex items-baseline justify-between gap-3 border-b border-border/50 pb-1">
          <h3 className={SECTION_HEADING}>{title}</h3>
          <span className={FOOTNOTE}>{group.length} contests</span>
        </div>
        {note && <p className={CARD_HINT}>{note}</p>}
        <div className="space-y-2">
          {group.map(race => (
            <RaceCard
              key={raceKey(race)}
              race={race}
              open={openRace === raceKey(race)}
              onToggle={() => toggle(race)}
            />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className={`${PAGE_TITLE} mb-1`}>Ranked ballots in practice: Alaska and Maine</h2>
        <p className="text-muted-foreground text-sm max-w-3xl">
          Alaska and Maine are the only states that rank ballots in federal elections. Their cast
          vote records are the closest thing to a test of the counting rules this project simulates:
          the same ballots can be recounted as first-past-the-post, as an instant runoff, as a
          head-to-head round robin, and as multi-seat STV.
        </p>
      </div>

      <StickyControlBar label="RCV settings">
        <ToggleGroup
          label="State" value={stateTab} onChange={setStateTab}
          options={['AK', 'ME'] as const}
          labels={{ AK: 'Alaska', ME: 'Maine' }}
        />
      </StickyControlBar>

      <CoveragePanel stateAbbr={stateTab} races={races} onSelect={r => setOpenRace(raceKey(r))} />

      <SimulationBanner
        stateLabel={stateLabel}
        house={houseStateMap[fips]}
        senate={senate}
      />

      <DelegationPanel stateAbbr={stateTab} house={houseStateMap[fips]} races={races} />

      {tabulated.length > 0 && (
        <Card className="px-4 py-3 space-y-1">
          <p className="text-sm text-foreground/85">
            Transfers changed the winner in {transferFlips.length} of {tabulated.length} ranked
            contests in {stateLabel}. Ranked counting seated someone other than the head-to-head
            winner in {condorcetFailures.length} of the {condorcetKnown.length} with a published
            cast vote record.
          </p>
          {condorcetFailures.length > 0 && (
            <p className={CARD_HINT}>
              {condorcetFailures
                .map(r => `${r.year} ${r.raceName}: ${r.condorcetWinner} beat both rivals one-on-one and finished third on first choices`)
                .join('; ')}.
            </p>
          )}
        </Card>
      )}

      {races.length === 0 ? (
        <Card className="border-dashed border-slate-300 p-10 text-center">
          <div className="text-muted-foreground text-sm">No race data loaded for {stateLabel}.</div>
        </Card>
      ) : (
        <div className="space-y-8">
          {renderGroup('General elections', generals)}
          {renderGroup(
            'Primaries',
            primaries,
            'Maine ranks primary ballots for every office, including the ones its general elections count by plurality.',
          )}
          {decidedFirstRound.length > 0 && (
            <div className="space-y-2">
              <h3 className={`${SECTION_HEADING} border-b border-border/50 pb-1`}>
                Decided on first choices
              </h3>
              <p className={CARD_HINT}>
                Ranked ballots were cast and never needed: the leader already had a majority, so no
                transfer, head-to-head or STV comparison arises.
              </p>
              <div className="space-y-2">
                {decidedFirstRound.map(race => (
                  <RaceCard
                    key={raceKey(race)}
                    race={race}
                    open={openRace === raceKey(race)}
                    onToggle={() => toggle(race)}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
