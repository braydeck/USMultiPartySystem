import { useMemo } from 'react';
import { useUrlState, resetUrlParams } from '../hooks/useUrlState';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import type { SenateSeat, VoteModelRow, SenateScenario, ClusterProfile, ConstellationNode, FDSenateSeat, FDHouseSeat, FDCandidateProfile, SenateIrvRoundsData, SenateWinnowData } from '../types';
import { SenateMap } from '../components/senate/SenateMap';
import { IdeologicalConstellation } from '../components/house/IdeologicalConstellation';
import { ParliamentChart } from '../components/shared/ParliamentChart';
import { PartyVariantBar } from '../components/shared/PartyVariantBar';
import { PartyProfileGrid } from '../components/shared/PartyProfileGrid';
import type { ParliamentSegment } from '../components/shared/ParliamentChart';
import { FACTOR_LABELS, DISPLAY_FACTORS, partyOrder } from '../constants/parties';
import { PIPELINE_LABELS, METHOD_LABELS } from '../constants/labels';
import { SHOW_CROSSOVER, PIPELINE_OPTIONS } from '../constants/features';
import { ToggleGroup } from '../components/shared/ToggleGroup';
import { ParticipationSlider, GAP_STOPS } from '../components/shared/ParticipationSlider';
import { DEFAULT_GAP_STOP } from '../lib/participationStops';
import { StickyControlBar } from '../components/shared/StickyControlBar';
import { CollapsibleSection } from '../components/shared/CollapsibleSection';
// Compression stops (5-point steps to 30% of the turnout gap closed); floor comes via props.
import senCondL5 from '../data/pureMultiSenateCondorcetTurnoutL5.json';
import senCondL10 from '../data/pureMultiSenateCondorcetTurnoutL10.json';
import senCondL15 from '../data/pureMultiSenateCondorcetTurnoutL15.json';
import senCondL20 from '../data/pureMultiSenateCondorcetTurnoutL20.json';
import senCondL25 from '../data/pureMultiSenateCondorcetTurnoutL25.json';
import senCondL30 from '../data/pureMultiSenateCondorcetTurnoutL30.json';
import senIrvL5 from '../data/pureMultiSenateIRVTurnoutL5.json';
import senIrvL10 from '../data/pureMultiSenateIRVTurnoutL10.json';
import senIrvL15 from '../data/pureMultiSenateIRVTurnoutL15.json';
import senIrvL20 from '../data/pureMultiSenateIRVTurnoutL20.json';
import senIrvL25 from '../data/pureMultiSenateIRVTurnoutL25.json';
import senIrvL30 from '../data/pureMultiSenateIRVTurnoutL30.json';
// Crossover (FD) senate compression stops.
import fdSenCond0 from '../data/fdSenateCondorcetTurnout.json';
import fdSenCond5 from '../data/fdSenateCondorcetTurnoutL5.json';
import fdSenCond10 from '../data/fdSenateCondorcetTurnoutL10.json';
import fdSenCond15 from '../data/fdSenateCondorcetTurnoutL15.json';
import fdSenCond20 from '../data/fdSenateCondorcetTurnoutL20.json';
import fdSenCond25 from '../data/fdSenateCondorcetTurnoutL25.json';
import fdSenCond30 from '../data/fdSenateCondorcetTurnoutL30.json';
import fdSenIrv0 from '../data/fdSenateIRVTurnout.json';
import fdSenIrv5 from '../data/fdSenateIRVTurnoutL5.json';
import fdSenIrv10 from '../data/fdSenateIRVTurnoutL10.json';
import fdSenIrv15 from '../data/fdSenateIRVTurnoutL15.json';
import fdSenIrv20 from '../data/fdSenateIRVTurnoutL20.json';
import fdSenIrv25 from '../data/fdSenateIRVTurnoutL25.json';
import fdSenIrv30 from '../data/fdSenateIRVTurnoutL30.json';
// Senate bill vote model, tracked across turnout (rank-7 winnow + depth-7 president = app default).
// Coalition / head-to-head / winnow, tracked across the turnout stops so every senate
// card reports the same chamber the seat data does.
import senIrvRounds0 from '../data/senateIrvRoundsTurnout.json';
import senIrvRounds5 from '../data/senateIrvRoundsTurnoutL5.json';
import senIrvRounds10 from '../data/senateIrvRoundsTurnoutL10.json';
import senIrvRounds15 from '../data/senateIrvRoundsTurnoutL15.json';
import senIrvRounds20 from '../data/senateIrvRoundsTurnoutL20.json';
import senIrvRounds25 from '../data/senateIrvRoundsTurnoutL25.json';
import senIrvRounds30 from '../data/senateIrvRoundsTurnoutL30.json';
import senCondView0 from '../data/senateCondorcetTurnout.json';
import senCondView5 from '../data/senateCondorcetTurnoutL5.json';
import senCondView10 from '../data/senateCondorcetTurnoutL10.json';
import senCondView15 from '../data/senateCondorcetTurnoutL15.json';
import senCondView20 from '../data/senateCondorcetTurnoutL20.json';
import senCondView25 from '../data/senateCondorcetTurnoutL25.json';
import senCondView30 from '../data/senateCondorcetTurnoutL30.json';
import senWinnow0 from '../data/senateBucketsTurnout.json';
import senWinnow5 from '../data/senateBucketsTurnoutL5.json';
import senWinnow10 from '../data/senateBucketsTurnoutL10.json';
import senWinnow15 from '../data/senateBucketsTurnoutL15.json';
import senWinnow20 from '../data/senateBucketsTurnoutL20.json';
import senWinnow25 from '../data/senateBucketsTurnoutL25.json';
import senWinnow30 from '../data/senateBucketsTurnoutL30.json';
import { SenateCoalitionCard } from '../components/senate/SenateCoalitionCard';
import { SenateWinnowCard } from '../components/senate/SenateWinnowCard';
import SenateCondorcetView from '../components/senate/SenateCondorcetView';
import { SenateCompositionCard } from '../components/senate/SenateCompositionCard';
import { SenateRangeCard } from '../components/senate/SenateRangeCard';
import { VariantImpactChart } from '../components/house/VariantImpactChart';
import { VariantAttractionChart } from '../components/house/VariantAttractionChart';
import { AttractionDriverChart } from '../components/house/AttractionDriverChart';
import { uncertaintyAt } from '../lib/uncertainty';
import { delegationSeats } from '../lib/senateDelegations';
import { PAGE_TITLE, CARD_HEADING, FIELD_LABEL, CARD_HINT } from '../constants/typography';

interface Props {
  condorcetFD:       FDSenateSeat[];
  irvFD:             FDSenateSeat[];
  condorcetRawMulti: FDSenateSeat[];
  irvRawMulti:       FDSenateSeat[];
  condorcetRawMultiTurnout: FDSenateSeat[];
  irvRawMultiTurnout:       FDSenateSeat[];
  voteModel:         VoteModelRow[];
  clusters:          ClusterProfile[];
  fdProfiles:        Record<string, FDCandidateProfile>;
  clusterSpreads:    { party: string; n: number; [key: string]: string | number }[];
  houseTransfers: { source: string; totalVoters: number; destinations: { party: string; pct: number }[] }[];
  fdVariantAttraction: { variant: string; party: string; axis: string; direction: string; totalVoters: number; homePct: number; crossPct: number; sources: { party: string; pct: number }[] }[];
  fdAttractionDrivers: { variant: string; party: string; axis: string; direction: string; attracted: string; attractedPct: number; factors: { factor: string; pct: number }[] }[];
}

export function SenateTab({ condorcetRawMultiTurnout, irvRawMultiTurnout,
                             clusters, fdProfiles, clusterSpreads,
                             fdVariantAttraction, fdAttractionDrivers }: Props) {
  const [pipeline, setPipeline] = useUrlState<'factorDev' | 'rawMulti'>('pipeline', 'rawMulti', { allowed: PIPELINE_OPTIONS, map: { factorDev: 'crossover', rawMulti: 'party-line' } });
  const [method, setMethod] = useUrlState<'condorcet' | 'irv'>('method', 'condorcet', { allowed: ['condorcet', 'irv'] });
  // Participation: gap-compression stop (0 = observed 2024 turnout … 100 = full parity).
  const [part, setPart] = useUrlState<string>('part', String(DEFAULT_GAP_STOP), { allowed: ['0', '5', '10', '15', '20', '25', '30'] });
  const rawMultiOn = pipeline === 'rawMulti';
  const gi = Math.max(0, GAP_STOPS.indexOf(Number(part) as typeof GAP_STOPS[number]));
  // Each state elects one senator among 5 finalists via IRV/Condorcet; voters rank all 5 (full
  // ranking), so there is no ballot-depth toggle here.
  // Compression stops [0,5,10,15,20,25,30] for each pipeline; condRM/irvRM are the ACTIVE
  // scenario's Condorcet/IRV senate at the current turnout stop.
  const rmCondStops = [condorcetRawMultiTurnout, senCondL5, senCondL10, senCondL15, senCondL20, senCondL25, senCondL30] as unknown as FDSenateSeat[][];
  const rmIrvStops  = [irvRawMultiTurnout, senIrvL5, senIrvL10, senIrvL15, senIrvL20, senIrvL25, senIrvL30] as unknown as FDSenateSeat[][];
  const fdCondStops = [fdSenCond0, fdSenCond5, fdSenCond10, fdSenCond15, fdSenCond20, fdSenCond25, fdSenCond30] as unknown as FDSenateSeat[][];
  const fdIrvStops  = [fdSenIrv0, fdSenIrv5, fdSenIrv10, fdSenIrv15, fdSenIrv20, fdSenIrv25, fdSenIrv30] as unknown as FDSenateSeat[][];
  const condRM = (rawMultiOn ? rmCondStops : fdCondStops)[gi];
  const irvRM  = (rawMultiOn ? rmIrvStops  : fdIrvStops )[gi];
  // Sampling uncertainty at the active stop. Party-line only — the Crossover pipeline
  // is not bootstrapped, so these are undefined there and every consumer degrades.
  const unc = rawMultiOn ? uncertaintyAt(gi) : undefined;
  // Coalition / head-to-head / winnow at the current stop. Party-line only — the
  // Crossover pipeline has no equivalent per-state round data.
  const irvRoundsStops = [senIrvRounds0, senIrvRounds5, senIrvRounds10, senIrvRounds15,
                          senIrvRounds20, senIrvRounds25, senIrvRounds30] as unknown as SenateIrvRoundsData[];
  const condViewStops  = [senCondView0, senCondView5, senCondView10, senCondView15,
                          senCondView20, senCondView25, senCondView30];
  const winnowStops    = [senWinnow0, senWinnow5, senWinnow10, senWinnow15,
                          senWinnow20, senWinnow25, senWinnow30] as unknown as SenateWinnowData[];

  const [parliamentFactor, setParliamentFactor] = useUrlState<string>('factor', 'F5', { allowed: [...DISPLAY_FACTORS] });


  const scenario: SenateScenario =
    pipeline === 'factorDev'
      ? (method === 'condorcet' ? 'condFD' : 'irvFD')
      : (method === 'condorcet' ? 'condRawMulti' : 'irvRawMulti');

  // condRM/irvRM already resolve to the active pipeline, so both scenarios map to them.
  const SEAT_MAP: Record<SenateScenario, SenateSeat[]> = {
    condFD:       condRM as unknown as SenateSeat[],
    irvFD:        irvRM  as unknown as SenateSeat[],
    condRawMulti: condRM as unknown as SenateSeat[],
    irvRawMulti:  irvRM  as unknown as SenateSeat[],
  };
  const activeSeats = SEAT_MAP[scenario];

  const seatCounts: Record<string, number> = {};
  for (const s of activeSeats) {
    seatCounts[s.senatorCode] = (seatCounts[s.senatorCode] ?? 0) + 1;
  }

  // The composition card's headline is the MODAL chamber, so the fan chart and the
  // constellation below it have to report that same chamber — a chart drawn from the single
  // observed run sits under a modal headline and contradicts it. Party level, on the 51-seat
  // basis `seatCounts` uses. Undefined for Crossover, which has no bootstrap and keeps the
  // observed run everywhere. Do not revert these two consumers to `seatCounts`.
  const methodU = method === 'condorcet' ? unc?.senate.cond : unc?.senate.irv;
  // Seats under the split rule, so the chamber matches the headline card: a state whose
  // winner changes across resamples returns one senator from each of its two closest
  // parties rather than two from the modal winner.
  const modalCounts = useMemo(() => methodU
    ? Object.fromEntries(Object.entries(delegationSeats(methodU.states))
        .filter(([, n]) => n > 0)
        .map(([p, n]) => [p, n / 2]))
    : undefined, [methodU]);

  const clusterByParty = useMemo(
    () => Object.fromEntries(clusters.map(c => [c.party, c])),
    [clusters]
  );
  const orderedClusters = useMemo(() => partyOrder().map(p => clusterByParty[p]).filter(Boolean) as ClusterProfile[], [clusterByParty]);

  function getFactorScore(code: string, factor: string): number {
    const zKey = `z_${factor}`;
    const cl = clusterByParty[code];
    if (cl) { const z = (cl as any)[zKey]; if (z != null) return z; }
    const base = code.split('_')[0];
    const baseCl = clusterByParty[base];
    if (baseCl) { const z = (baseCl as any)[zKey]; if (z != null) return z; }
    const fd = fdProfiles[code];
    if (fd) return (fd as unknown as Record<string, number>)[factor] ?? 0;
    return 0;
  }

  const globalRange = useMemo((): [number, number] => {
    const vals = [
      ...clusters.map(c => (c as unknown as Record<string, number>)[parliamentFactor] ?? 0),
      ...Object.values(fdProfiles).map(p => (p as unknown as Record<string, number>)[parliamentFactor] ?? 0),
    ];
    return vals.length > 0 ? [Math.min(...vals), Math.max(...vals)] : [-2, 2];
  }, [clusters, fdProfiles, parliamentFactor]);

  // Same convention as SenateCompositionCard, so the two charts read on one scale. The
  // split rule moves seats between parties but never changes the chamber size.
  const chamberSeats = modalCounts
    ? Object.values(modalCounts).reduce((a, b) => a + b, 0) * 2
    : activeSeats.length * 2;
  // On the modal path the counts are already collapsed to parties, so the _1/_2 ordinal
  // jitter the observed path needs to separate CON_1 from CON_2 has nothing to separate.
  const parliamentSegments: ParliamentSegment[] = (modalCounts
    ? Object.entries(modalCounts).map(([code, seats]) => ({
        code, seats: seats * 2, fVal: getFactorScore(code, parliamentFactor),
      }))
    : Object.entries(seatCounts).map(([code, seats]) => {
        const base = getFactorScore(code, parliamentFactor);
        const nSuffix = parseInt(code.split('_').pop() ?? '') || 0;
        return { code, seats: seats * 2, fVal: base + (nSuffix > 0 ? (nSuffix - 1) * 0.001 : 0) };
      })
  ).sort((a, b) => a.fVal - b.fVal);

  // Variant seat data for PartyVariantBar
  const fdVariantSeats = useMemo((): FDHouseSeat[] => {
    const fdSeats = (method === 'condorcet' ? condRM : irvRM);
    const countByCode: Record<string, FDHouseSeat> = {};
    for (const seat of fdSeats) {
      const key = seat.senatorCode;
      if (!countByCode[key]) {
        countByCode[key] = {
          code: seat.senatorCode, party: seat.senatorParty,
          axis: seat.senatorAxis, direction: seat.senatorDir,
          urban: 0, suburban: 0, rural: 0, national: 0, pctNational: 0,
        };
      }
      countByCode[key].national += 1;
    }
    return Object.values(countByCode);
  }, [condRM, irvRM, method]);

  const constellationNodes: ConstellationNode[] = Object.entries(modalCounts ?? seatCounts)
    .map(([code, seats]) => ({
      id: code, label: code, seats,
      F1: getFactorScore(code, 'F1'), F2: getFactorScore(code, 'F2'),
      F3: getFactorScore(code, 'F3'), F4: getFactorScore(code, 'F4'),
      F5: getFactorScore(code, 'F5'),
    }));

  const isFD = pipeline === 'factorDev';

  return (
    <div className="space-y-8">
      <div>
        <h2 className={`${PAGE_TITLE} mb-1`}>Senate</h2>
        <p className="text-muted-foreground text-sm">
          Each state elects two senators via Condorcet or IRV.
          <span className="block mt-1.5"> 
          Condorcet finds the most broadly acceptable candidate and permits real third-party presence. 
          </span>
          <span className="block mt-1.5"> 
          IRV amplifies strong-base parties leading to two-party dominance that reflects the current Senate.
          </span>
        </p>
      </div>

      <StickyControlBar label="Senate settings">
        {SHOW_CROSSOVER && (
          <ToggleGroup label="Scenario" value={pipeline} onChange={setPipeline}
            options={PIPELINE_OPTIONS} labels={PIPELINE_LABELS} />
        )}
        <ToggleGroup label="Method" value={method} onChange={setMethod}
          options={['condorcet', 'irv'] as const} labels={METHOD_LABELS} />
        <ParticipationSlider value={Number(part)} onChange={v => setPart(String(v))} />
      </StickyControlBar>

      {/* FPTP vs Preferential Senate Comparison (shared with Overview) */}
      <SenateCompositionCard condSeats={condRM} irvSeats={irvRM}
        condU={unc?.senate.cond} irvU={unc?.senate.irv} />

      {/* Same section, id and content as the House tab, so a reader who opened it
          there finds it open here. */}
      <CollapsibleSection id="profiles" title="See party profiles"
        hint="Ten parties, their positions and who they draw from">
        <PartyProfileGrid clusters={orderedClusters} />
        <Card className="p-4">
          <h4 className={`${CARD_HEADING} mb-3`}>
            Ideological Constellation
          </h4>
          <IdeologicalConstellation nodes={constellationNodes} clusterSpreads={clusterSpreads} />
        </Card>
      </CollapsibleSection>

      {/* Sampling range, split from the composition card above so the headline bars stay
          clean; party-line only, since Crossover has no bootstrap. */}
      {rawMultiOn && (
        <SenateRangeCard condSeats={condRM}
          condU={unc?.senate.cond} irvU={unc?.senate.irv} nDraws={unc?.nDraws} />
      )}

      {/* Parliament fan chart */}
      <Card className="p-4">
        <h4 className={`${CARD_HEADING} mb-1`}>
          Senate Chamber — {METHOD_LABELS[method]} · {chamberSeats} seats
        </h4>
        <p className={`${CARD_HINT} mb-3`}>
          {modalCounts
            ? 'Two seats per state, split between the top two where the state is contested.'
            : 'One winner per state, filling both of that state\'s seats.'}
          {' '}Matches the bars above.
        </p>
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <span className={FIELD_LABEL}>Order by</span>
          {DISPLAY_FACTORS.map(f => (
            <Button key={f} onClick={() => setParliamentFactor(f)} title={FACTOR_LABELS[f]}
              variant={parliamentFactor === f ? 'default' : 'secondary'}
              size="sm">
              {FACTOR_LABELS[f]}
            </Button>
          ))}
        </div>
        <ParliamentChart segments={parliamentSegments} factor={parliamentFactor} globalRange={globalRange} />
      </Card>

      {/* FD: Variant bar below fan chart */}
      {isFD && fdVariantSeats.length > 0 && (
        <Card className="p-4">
          <h4 className={`${CARD_HEADING} mb-1`}>
            Senate Seats by Variant
          </h4>
          <p className={`${CARD_HINT} mb-3`}>
            Full color = base; lighter = hi axis deviation; darker = lo axis deviation.
          </p>
          <PartyVariantBar seats={fdVariantSeats} totalLabel="51 senate seats" />
        </Card>
      )}

      <Card className="p-4">
        <SenateMap seats={activeSeats}
          states={method === 'condorcet' ? unc?.senate.cond.states : unc?.senate.irv.states} />
      </Card>

      {/* One slot, switched by method: IRV builds a coalition through transfers, so it
          gets the vote-flow view. Condorcet never transfers anything — it compares every
          pair directly, so it gets the matrix. */}
      {rawMultiOn && (method === 'irv' ? (
        <Card className="p-4">
          <h4 className={`${CARD_HEADING} mb-1`}>
            How Senators Build Their Coalition (IRV)
          </h4>
          <p className={`${CARD_HINT} mb-3`}>
            No party starts near a majority, so every winner assembles one from transfers.
            Each bar runs from that party&apos;s own first-choice block through the transfers it
            picked up as rivals were eliminated, ending at the tally that won.
            Select a state to watch the rounds play out.
          </p>
          <SenateCoalitionCard data={irvRoundsStops[gi]} states={unc?.senate.irv.states} />
        </Card>
      ) : (
        <Card className="p-4">
          <h4 className={`${CARD_HEADING} mb-1`}>
            Head-to-Head Matrix (Condorcet)
          </h4>
          <p className={`${CARD_HINT} mb-3`}>
            Condorcet picks the candidate who beats every rival one-on-one, so what matters is
            the full grid of pairings rather than a transfer sequence. The national view counts
            how often each party wins its matchups across the {activeSeats.length} state races.
            Select a state for that race&apos;s actual margins.
          </p>
          <SenateCondorcetView data={condViewStops[gi]} states={unc?.senate.cond.states} />
        </Card>
      ))}

      {/* The winnow runs before either method, so it shows under both. */}
      {rawMultiOn && (
        <Card className="p-4">
          <h4 className={`${CARD_HEADING} mb-1`}>
            How the Field Narrows to Five Finalists
          </h4>
          <p className={`${CARD_HINT} mb-3`}>
            Before either method picks a senator, a five-seat STV round cuts the state&apos;s full
            candidate field to five. Its Droop quota is {winnowStops[gi].quotaPct.toFixed(1)}%, not a
            majority, so these tallies sit on a much lower scale than the winning coalitions above
            and say which candidates survived, not who won.
          </p>
          <SenateWinnowCard data={winnowStops[gi]} />
        </Card>
      )}

      <Card className="p-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h4 className={`${CARD_HEADING} mb-1`}>
            How this senate votes on bills
          </h4>
          <p className={CARD_HINT}>
            The bill-by-bill model lives on the Legislation tab, with the whipping rules and
            the full bill set.
          </p>
        </div>
        <Button onClick={() => resetUrlParams({ tab: 'legislation' })}>Open Legislation</Button>
      </Card>

      {/* FD Analysis section */}
      {isFD && (
        <>
          <div className="border-t-2 border-violet-200 pt-6">
            <h3 className="text-lg font-bold text-violet-800 mb-1">Crossover Analysis — Senate</h3>
            <p className={`${CARD_HINT} mb-6`}>
              How do ideological deviations affect senate composition under {method === 'condorcet' ? 'Condorcet' : 'IRV'}?
            </p>
          </div>

          <Card className="p-4">
            <h4 className={`${CARD_HEADING} mb-1`}>
              Variant Impact by Party
            </h4>
            <p className={`${CARD_HINT} mb-4`}>
              Which ideological deviations win senate seats?
            </p>
            <VariantImpactChart seats={fdVariantSeats} />
          </Card>

          {fdVariantAttraction.length > 0 && (
            <Card className="p-4">
              <h4 className={`${CARD_HEADING} mb-1`}>
                Variant Voter Attraction Sources
              </h4>
              <p className={`${CARD_HINT} mb-4`}>
                Incremental cross-party attraction for each deviation relative to the party base.
              </p>
              <VariantAttractionChart data={fdVariantAttraction} />
            </Card>
          )}

          {fdAttractionDrivers.length > 0 && (
            <Card className="p-4">
              <h4 className={`${CARD_HEADING} mb-1`}>
                Cross-Party Attraction Drivers
              </h4>
              <p className={`${CARD_HINT} mb-3`}>
                Which factors explain each variant&apos;s cross-party pull?
              </p>
              <AttractionDriverChart data={fdAttractionDrivers} />
            </Card>
          )}
        </>
      )}
    </div>
  );
}
