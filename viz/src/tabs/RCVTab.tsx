import { useCallback, useState } from 'react';
import { useUrlState } from '../hooks/useUrlState';
import type { RCVData, RCVRace, HouseStateEntry, SenateIrvRoundsData } from '../types';
import { Card } from '@/components/ui/card';
import { ToggleGroup } from '../components/shared/ToggleGroup';
import { StickyControlBar } from '../components/shared/StickyControlBar';
import { MechanismStrip, type Mechanism } from '../components/shared/MechanismStrip';
import { SYSTEM_COLORS } from '../constants/parties';
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

function raceDomId(race: RCVRace): string {
  return `rcv-${raceKey(race).replace(/[^a-zA-Z0-9-]/g, '')}`;
}

/** The four counting rules this tab recounts the same ballots under. */
const COUNTING_RULES: Mechanism[] = [
  {
    term: 'First past the post',
    color: SYSTEM_COLORS.FPTP,
    what: 'Counts first choices only; whoever leads wins, majority or not.',
    consequence: "Today's rule in 48 states. Shown here as each contest's round-one leader.",
  },
  {
    term: 'IRV',
    color: SYSTEM_COLORS.IRV,
    what: 'Drops the last-placed candidate each round and moves their ballots to the next choice still standing.',
    consequence: 'What Alaska and Maine actually run. Rewards first-choice strength.',
  },
  {
    term: 'Condorcet',
    color: SYSTEM_COLORS.Condorcet,
    what: 'Seats the candidate who beats every rival one-on-one across the same ballots.',
    consequence: 'Rewards broad acceptability. Needs the full ballots, not just the rounds.',
  },
  {
    term: 'STV',
    color: SYSTEM_COLORS.STV,
    what: 'Fills several seats at once; ballots transfer once a candidate clears the quota or is eliminated.',
    consequence: 'The proportional rule this project proposes, run here at double the seats.',
  },
];

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

  /** Open a race and bring it into view — clicking a coverage cell or a summary chip
   *  otherwise expands a card several screens down and looks like nothing happened. */
  const jumpTo = useCallback((race: RCVRace) => {
    setOpenRace(raceKey(race));
    requestAnimationFrame(() => {
      document.getElementById(raceDomId(race))
        ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  }, []);

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
              domId={raceDomId(race)}
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
          vote records let the same ballots be recounted four ways, so the counting rules this
          project simulates can be checked against real votes.
        </p>
      </div>

      <MechanismStrip items={COUNTING_RULES} />

      <StickyControlBar label="RCV settings">
        <ToggleGroup
          label="State" value={stateTab} onChange={setStateTab}
          options={['AK', 'ME'] as const}
          labels={{ AK: 'Alaska', ME: 'Maine' }}
        />
      </StickyControlBar>

      {tabulated.length > 0 && (
        <Card className="p-4 space-y-3">
          <p className="text-sm text-foreground/85 leading-snug">
            {tabulated.length} contests in {stateLabel} went past the first round. Transfers changed
            the winner in {transferFlips.length}
            {condorcetKnown.length > 0 && (
              <>
                , and the Condorcet winner lost in {condorcetFailures.length}
                {condorcetKnown.length < tabulated.length &&
                  ` of the ${condorcetKnown.length} whose ballots are published`}
              </>
            )}
            .
          </p>
          <div className="flex flex-wrap gap-1.5">
            {tabulated.map(race => (
              <button
                key={raceKey(race)}
                onClick={() => jumpTo(race)}
                className="text-2xs font-medium px-2 py-1 rounded-full border border-border bg-card hover:bg-muted hover:border-foreground/30 transition-colors"
              >
                <span className="tabular-nums text-muted-foreground mr-1">{race.year}</span>
                {race.raceName}
                <span className="text-muted-foreground ml-1">· {race.irvRounds.length} rounds</span>
              </button>
            ))}
          </div>
          {condorcetFailures.length > 0 && (
            <p className={CARD_HINT}>
              {condorcetFailures
                .map(r => `${r.year} ${r.raceName}: ${r.condorcetWinner} beat every rival one-on-one and was eliminated for finishing last on first choices`)
                .join('; ')}.
            </p>
          )}
        </Card>
      )}

      <SimulationBanner
        stateLabel={stateLabel}
        house={houseStateMap[fips]}
        senate={senate}
      />

      <DelegationPanel stateAbbr={stateTab} house={houseStateMap[fips]} races={races} />

      <CoveragePanel stateAbbr={stateTab} races={races} onSelect={jumpTo} />

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
                    domId={raceDomId(race)}
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
