import { useMemo, useState, useEffect } from 'react';
import type {
  PresidentialElection, FDSenateSeat, HouseSeat, VoteModelRow, ClusterProfile, FDCandidateProfile,
  FPTPState, HouseStateEntry,
} from '../types';
import { F5_ORDER, PARTY_NAMES } from '../constants/parties';
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

const CLUSTER_OF: Record<string, number> = { CON: 0, LBR: 1, STY: 2, NAT: 3, LIB: 4, POP: 5, CUP: 6, OAO: 7, DSA: 8, PRG: 9 };

export function OverviewTab({
  rawMultiElection,
  rawMultiSenateCond, rawMultiSenateIRV,
  houseSeats, senateVotes, houseVotes,
  clusters, fptpStates, stateMap, clusterSpreads,
  onNavigate,
}: Props) {
  // The Overview is the headline snapshot at the app's DEFAULT settings: ballots ranked 7, 5% of the
  // turnout gap closed. House STV seats + the presidency general at that depth live in the lazy
  // bundles (party-list STV seats are depth-invariant only for list; STV changes), so derive them here.
  const [hpl, setHpl] = useState<Record<string, Record<string, Record<string, { national: { stvSeats: Record<string, number> } }>>> | null>(null);
  const [gd, setGd] = useState<Record<string, Record<string, PresidentialElection>> | null>(null);
  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/housePartyList.json`).then(r => r.json()).then(setHpl).catch(() => {});
    fetch(`${import.meta.env.BASE_URL}data/generalDepth.json`).then(r => r.json()).then(setGd).catch(() => {});
  }, []);

  const houseSeats7 = useMemo<HouseSeat[] | null>(() => {
    const stv = hpl?.top7?.double?.['5']?.national?.stvSeats;
    if (!stv) return null;
    return F5_ORDER.map(p => ({
      party: CLUSTER_OF[p], partyName: PARTY_NAMES[p], national: stv[p] ?? 0,
      urban: 0, suburban: 0, rural: 0, pctNational: 0, pctPopulation: 0,
    })).filter(s => s.national > 0) as unknown as HouseSeat[];
  }, [hpl]);
  const election = gd?.top7?.['5'] ?? rawMultiElection;
  const seats = houseSeats7 ?? houseSeats;

  const condWinner = election.condorcetWinner; // e.g. "STY_1"
  const irvWinner  = election.irvWinner;
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

      {/* Read the argument — links to the Substack series */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">Read the argument</h3>
        <div className="grid sm:grid-cols-3 gap-3">
          <a href="https://braydendecker.substack.com/p/the-problem-an-electoral-system-engineered"
            target="_blank" rel="noopener noreferrer"
            className="group rounded-md border border-border bg-card p-3 hover:bg-muted hover:border-indigo-300 hover:shadow-sm transition-all">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-foreground">The Problem</span>
              <span className="text-xs text-muted-foreground group-hover:text-indigo-500 transition-colors">Read ↗</span>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1 leading-relaxed">Mutual contempt and polarization are downstream of a Winner-Take-All electoral system.</p>
          </a>
          <a href="https://braydendecker.substack.com/p/the-solution-give-everyone-a-voice"
            target="_blank" rel="noopener noreferrer"
            className="group rounded-md border border-border bg-card p-3 hover:bg-muted hover:border-indigo-300 hover:shadow-sm transition-all">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-foreground">The Solution</span>
              <span className="text-xs text-muted-foreground group-hover:text-indigo-500 transition-colors">Read ↗</span>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1 leading-relaxed">A proportional House, consensus single-winner elections, an open national primary, and public financing.</p>
          </a>
          <a href="https://braydendecker.substack.com/p/the-simulation-a-multiparty-america"
            target="_blank" rel="noopener noreferrer"
            className="group rounded-md border border-border bg-card p-3 hover:bg-muted hover:border-indigo-300 hover:shadow-sm transition-all">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-foreground">The Simulation</span>
              <span className="text-xs text-muted-foreground group-hover:text-indigo-500 transition-colors">Read ↗</span>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1 leading-relaxed">A description of this multiparty democracy simulation.</p>
          </a>
        </div>
      </div>

      {/* Section 1 — House FPTP vs STV */}
      <Card className="p-5 border-2 border-indigo-200">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-4">House of Representatives</h3>
        <FPTPvsSTV seats={seats} />
        <div className="mt-4">
          <DiveCard label="Dive into the House →" onClick={() => onNavigate('house')} />
        </div>
      </Card>

      {/* Section 2 — Senate (shared card, identical to the Senate tab) */}
      <div className="space-y-3">
        <SenateCompositionCard condSeats={rawMultiSenateCond} irvSeats={rawMultiSenateIRV} />
        <DiveCard label="Dive into the Senate →" onClick={() => onNavigate('senate')} />
      </div>

      {/* Party profiles — blurbs + factor bars */}
      <PartyProfileGrid clusters={orderedClusters} />

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
          election={election}
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

      {/* Turnout robustness + voter-file verification (grouped at the bottom) */}
      <TurnoutRobustnessCard />
      <TurnoutVerificationCard />
    </div>
  );
}
