import { useMemo } from 'react';
import type {
  PresidentialElection, FDSenateSeat, HouseSeat, VoteModelRow, ClusterProfile, FDCandidateProfile,
  FPTPState, HouseStateEntry,
} from '../types';
import { F5_ORDER } from '../constants/parties';
import { Card } from '@/components/ui/card';
import { FPTPvsSTV } from '../components/house/FPTPvsSTV';
import { FPTPDisproportionality } from '../components/house/FPTPDisproportionality';
import { IdeologicalConstellation } from '../components/house/IdeologicalConstellation';
import { PartyProfileGrid } from '../components/shared/PartyProfileGrid';
import { PartyProfileCard } from '../components/shared/PartyProfileCard';
import { LegislationDivergences } from '../components/legislation/LegislationDivergences';
import { TurnoutRobustnessCard } from '../components/shared/TurnoutRobustnessCard';
import { PopulationBreakdown } from '../components/shared/PopulationBreakdown';
import { TurnoutVerificationCard } from '../components/shared/TurnoutVerificationCard';
import { SenateCompositionCard } from '../components/senate/SenateCompositionCard';

interface Props {
  fdElection: PresidentialElection;
  rawMultiElection: PresidentialElection;
  rawMultiSenateCond: FDSenateSeat[];
  rawMultiSenateIRV: FDSenateSeat[];
  fdSenateCond: FDSenateSeat[];
  fdSenateIRV: FDSenateSeat[];
  houseSeats: HouseSeat[];
  senateVotes: VoteModelRow[];
  houseVotes: VoteModelRow[];
  clusters: ClusterProfile[];
  fdProfiles: Record<string, FDCandidateProfile>;
  fptpStates: FPTPState[];
  stateMap: Record<string, HouseStateEntry>;
  clusterSpreads: { party: string; n: number; [key: string]: string | number }[];
  onNavigate: (tab: string) => void;
}

// Prominent call-to-action card linking to a full scenario tab.
function DiveCard({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex w-full items-center justify-between rounded-lg border-2 border-indigo-200 bg-indigo-50/60 px-4 py-3 text-left transition-colors hover:border-indigo-300 hover:bg-indigo-100"
    >
      <span className="text-sm font-semibold text-indigo-900">{label}</span>
      <span className="text-lg text-indigo-500 transition-transform group-hover:translate-x-0.5" aria-hidden="true">→</span>
    </button>
  );
}

// ── Reusable sub-components ────────────────────────────────────────────────

// ── Main component ─────────────────────────────────────────────────────────

export function OverviewTab({
  rawMultiElection,
  rawMultiSenateCond, rawMultiSenateIRV,
  houseSeats, senateVotes, houseVotes,
  clusters, fptpStates, stateMap, clusterSpreads,
  onNavigate,
}: Props) {
  const condWinner = rawMultiElection.condorcetWinner; // e.g. "CUP_1"
  const irvWinner  = rawMultiElection.irvWinner;       // e.g. "SD_1"
  const condParty  = condWinner.split('_')[0];
  const irvParty   = irvWinner.split('_')[0];

  const clusterByParty = useMemo(
    () => Object.fromEntries(clusters.map(c => [c.party, c])),
    [clusters],
  );
  const orderedClusters = F5_ORDER.map(p => clusterByParty[p]).filter(Boolean) as ClusterProfile[];

  return (
    <div className="space-y-10">
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-1">A Proportional Government</h2>
        <p className="text-muted-foreground text-sm">
          What would the US look like with proportional representation? Here&apos;s a summary across all chambers.
        </p>
      </div>

      {/* Section 0 — Population breakdown */}
      <PopulationBreakdown />

      {/* Section 1 — House FPTP vs STV */}
      <Card className="p-5 border-2 border-indigo-200">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-4">House of Representatives</h3>
        <FPTPvsSTV seats={houseSeats} />
        <div className="mt-4">
          <DiveCard label="Dive into the House →" onClick={() => onNavigate('house')} />
        </div>
      </Card>

      {/* Section 2 — Senate (shared card, identical to the Senate tab) */}
      <div className="space-y-3">
        <SenateCompositionCard condSeats={rawMultiSenateCond} irvSeats={rawMultiSenateIRV} />
        <DiveCard label="Dive into the Senate →" onClick={() => onNavigate('senate')} />
      </div>

      {/* Section 3 — State disproportionality callouts */}
      <div>
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">FPTP Disproportionality — State Examples</h3>
        <p className="text-xs text-muted-foreground mb-3">
          Winner-take-all districts systematically over-represent the dominant party. Compare FPTP, 2-party proportional, and multi-party STV.
        </p>
        <FPTPDisproportionality states={fptpStates} stateMap={stateMap} />
      </div>

      {/* Section 4 — Presidential winners + legislative divergences */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">Presidential Outcomes</h3>
        <p className="text-xs text-muted-foreground">
          Condorcet and IRV often elect different presidents. The winner shapes which bills become law.
        </p>

        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <div className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-2">Condorcet Winner</div>
            {clusterByParty[condParty] && <PartyProfileCard cluster={clusterByParty[condParty]} />}
          </div>
          <div>
            <div className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-2">IRV Winner</div>
            {clusterByParty[irvParty] && <PartyProfileCard cluster={clusterByParty[irvParty]} />}
          </div>
        </div>

        <LegislationDivergences
          houseVotes={houseVotes}
          senateVotes={senateVotes}
          election={rawMultiElection}
          pipeline="rawMulti"
          wyoming="double"
        />

        <DiveCard label="Dive into the Presidency →" onClick={() => onNavigate('presidency')} />
      </div>

      {/* Section 5 — Ideological Constellation */}
      <Card className="p-5">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">Ideological Constellation</h3>
        <p className="text-xs text-muted-foreground mb-4">
          Drag axes to explore ideological dimensions. Default: Security &amp; Order (X) vs Populist Conservatism (Y).
        </p>
        <IdeologicalConstellation
          nodes={clusters.filter(c => c.party).map(c => ({
            id: c.party,
            label: c.party,
            seats: c.seatsHouse,
            F1: ((c as any).z_F1 ?? 0),
            F2: ((c as any).z_F2 ?? 0),
            F3: ((c as any).z_F3 ?? 0),
            F4: ((c as any).z_F4 ?? 0),
            F5: ((c as any).z_F5 ?? 0),
          }))}
          clusterSpreads={clusterSpreads}
        />
      </Card>

      {/* Section 6 — Party profiles */}
      <PartyProfileGrid clusters={orderedClusters} />

      {/* Section 7 — Turnout robustness + voter-file verification (grouped at the bottom) */}
      <TurnoutRobustnessCard />
      <TurnoutVerificationCard />
    </div>
  );
}
