import { useMemo, useState, useEffect } from 'react';
import type {
  PresidentialElection, FDSenateSeat, HouseSeat, ClusterProfile, FDCandidateProfile,
  FPTPState, HouseStateEntry,
} from '../types';
import { F5_ORDER } from '../constants/parties';
import { Card } from '@/components/ui/card';
import { FPTPvsSTV } from '../components/house/FPTPvsSTV';
import { FPTPDisproportionality } from '../components/house/FPTPDisproportionality';
import { IdeologicalConstellation } from '../components/house/IdeologicalConstellation';
import { PartyProfileGrid } from '../components/shared/PartyProfileGrid';
import { PartyProfileCard } from '../components/shared/PartyProfileCard';
import { PopulationBreakdown } from '../components/shared/PopulationBreakdown';
import { SenateCompositionCard } from '../components/senate/SenateCompositionCard';
import { ConceptStrip } from '../components/shared/ConceptStrip';
import { seatMapToHouseSeats } from '../components/house/PartyListView';
import { uncertaintyAt } from '../lib/uncertainty';
import { DEFAULT_STOP_INDEX } from '../lib/participationStops';
import { PAGE_TITLE, SECTION_HEADING, CARD_HEADING, MINOR_HEADING, GROUP_LABEL, METRIC_VALUE, CARD_HINT, FOOTNOTE } from '../constants/typography';

interface Props {
  fdElection: PresidentialElection;
  rawMultiElection: PresidentialElection;
  rawMultiSenateCond: FDSenateSeat[];
  rawMultiSenateIRV: FDSenateSeat[];
  fdSenateCond: FDSenateSeat[];
  fdSenateIRV: FDSenateSeat[];
  houseSeats: HouseSeat[];
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
  houseSeats,
  clusters, fptpStates, stateMap, clusterSpreads,
  onNavigate,
}: Props) {
  // The Overview is the headline snapshot at the app's DEFAULT settings: ballots ranked 7, 5% of the
  // turnout gap closed. House STV seats + the presidency general at that depth live in the lazy
  // bundles (party-list STV seats are depth-invariant only for list; STV changes), so derive them here.
  type Wasted = { list: number; stv: number };
  const [hpl, setHpl] = useState<Record<string, Record<string, Record<string, {
    national: { stvSeats: Record<string, number>; listSeats: Record<string, number>;
      unrepresented: Wasted; excess: Wasted } }>>> | null>(null);
  const [gd, setGd] = useState<Record<string, Record<string, PresidentialElection>> | null>(null);
  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/housePartyList.json`).then(r => r.json()).then(setHpl).catch(() => {});
    fetch(`${import.meta.env.BASE_URL}data/generalDepth.json`).then(r => r.json()).then(setGd).catch(() => {});
  }, []);

  const houseSeats7 = useMemo<HouseSeat[] | null>(() => {
    const stv = hpl?.top7?.double?.['5']?.national?.stvSeats;
    return stv ? seatMapToHouseSeats(stv) : null;
  }, [hpl]);
  const houseListSeats7 = useMemo<HouseSeat[] | null>(() => {
    const list = hpl?.top7?.double?.['5']?.national?.listSeats;
    return list ? seatMapToHouseSeats(list) : null;
  }, [hpl]);
  const wasted = hpl?.top7?.double?.['5']?.national;
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

  // Overview is pinned to the app's default stop, the same one the Senate tab opens on, so
  // both cards report the same chamber. Derived rather than hardcoded so changing the
  // default in one place cannot leave the two silently disagreeing.
  const senateUnc = uncertaintyAt(DEFAULT_STOP_INDEX);

  return (
    <div className="space-y-10">
      <div>
        <h2 className={`${PAGE_TITLE} mb-1`}>A Proportional Government</h2>
        <p className="text-muted-foreground text-sm">
          What would the US look like with proportional representation? Here&apos;s a summary across all chambers.
        </p>
      </div>

      {/* Section 0 — Population breakdown */}
      <PopulationBreakdown />

      {/* Read the argument — links to the Substack series */}
      <div className="space-y-3">
        <h3 className={SECTION_HEADING}>Read the argument</h3>
        <div className="grid sm:grid-cols-3 gap-3">
          <a href="https://braydendecker.substack.com/p/the-problem-an-electoral-system-engineered"
            target="_blank" rel="noopener noreferrer"
            className="group rounded-md border border-border bg-card p-3 hover:bg-muted hover:border-indigo-300 hover:shadow-sm transition-all">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-foreground">The Problem</span>
              <span className="text-xs text-muted-foreground group-hover:text-indigo-500 transition-colors">Read ↗</span>
            </div>
            <p className={`${FOOTNOTE} mt-1 leading-relaxed`}>Mutual contempt and polarization are downstream of a Winner-Take-All electoral system.</p>
          </a>
          <a href="https://braydendecker.substack.com/p/the-solution-give-everyone-a-voice"
            target="_blank" rel="noopener noreferrer"
            className="group rounded-md border border-border bg-card p-3 hover:bg-muted hover:border-indigo-300 hover:shadow-sm transition-all">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-foreground">The Solution</span>
              <span className="text-xs text-muted-foreground group-hover:text-indigo-500 transition-colors">Read ↗</span>
            </div>
            <p className={`${FOOTNOTE} mt-1 leading-relaxed`}>A proportional House, consensus single-winner elections, an open national primary, and public financing.</p>
          </a>
          <a href="https://braydendecker.substack.com/p/the-simulation-a-multiparty-america"
            target="_blank" rel="noopener noreferrer"
            className="group rounded-md border border-border bg-card p-3 hover:bg-muted hover:border-indigo-300 hover:shadow-sm transition-all">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-foreground">The Simulation</span>
              <span className="text-xs text-muted-foreground group-hover:text-indigo-500 transition-colors">Read ↗</span>
            </div>
            <p className={`${FOOTNOTE} mt-1 leading-relaxed`}>A description of this multiparty democracy simulation.</p>
          </a>
        </div>
      </div>

      {/* Concept strip — FPTP / Condorcet / IRV / STV / Party List, so the results below don't assume prior knowledge */}
      <ConceptStrip />

      {/* Electoral Outcomes — one sub-group per chamber, in the order the argument builds
          them. Each chamber's label sits OUTSIDE its cards so all three read as peers. */}
      <div className="space-y-6">
        <h3 className={SECTION_HEADING}>Electoral Outcomes</h3>

      {/* The House — the composition comparison, then what today's system wastes. */}
      <div className="space-y-4">
      <h4 className={GROUP_LABEL}>The House of Representatives</h4>
      <Card className="p-5">
        <FPTPvsSTV seats={seats} systemLabel="STV" otherSystemSeats={houseListSeats7 ?? undefined} otherSystemLabel="Party List" />
        <div className="mt-4">
          <DiveCard label="Dive into the House →" onClick={() => onNavigate('house')} />
        </div>
      </Card>

      {/* What the current system costs, in the two directions a vote is wasted: one that
          elected nobody and one piled on a winner who had already won. */}
      {wasted && (
        <div className="grid gap-4 lg:grid-cols-2 items-start">
          <Card className="p-4">
            <h4 className={`${CARD_HEADING} mb-1`}>
              Voters left unrepresented
            </h4>
            <p className={`${CARD_HINT} mb-4`}>Nobody they voted for won a seat.</p>
            <div className="grid grid-cols-3 gap-2">
              <div className="rounded-lg border border-rose-200 bg-rose-50 p-3">
                <div className="text-2xs text-muted-foreground">Today&apos;s House <span className="opacity-70">· 2024</span></div>
                <div className={`${METRIC_VALUE} text-rose-700`}>35.8%</div>
              </div>
              <div className="rounded-lg border border-border bg-muted/40 p-3">
                <div className="text-2xs text-muted-foreground">Party list</div>
                <div className={`${METRIC_VALUE} text-foreground`}>{wasted.unrepresented.list.toFixed(1)}%</div>
              </div>
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
                <div className="text-2xs text-muted-foreground">STV</div>
                <div className={`${METRIC_VALUE} text-emerald-700`}>{wasted.unrepresented.stv.toFixed(1)}%</div>
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <h4 className={`${CARD_HEADING} mb-1`}>
              Over-quota surplus
            </h4>
            <p className={`${CARD_HINT} mb-4`}>Votes above what a winner needed.</p>
            <div className="grid grid-cols-3 gap-2">
              <div className="rounded-lg border border-rose-200 bg-rose-50 p-3">
                <div className="text-2xs text-muted-foreground">Today&apos;s House <span className="opacity-70">· 2024</span></div>
                <div className={`${METRIC_VALUE} text-rose-700`}>14.2%</div>
              </div>
              <div className="rounded-lg border border-border bg-muted/40 p-3">
                <div className="text-2xs text-muted-foreground">Party list <span className="opacity-70">· stranded</span></div>
                <div className={`${METRIC_VALUE} text-foreground`}>{wasted.excess.list.toFixed(1)}%</div>
              </div>
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
                <div className="text-2xs text-muted-foreground">STV <span className="opacity-70">· transferred</span></div>
                <div className={`${METRIC_VALUE} text-emerald-700`}>{wasted.excess.stv.toFixed(1)}%</div>
              </div>
            </div>
          </Card>
        </div>
      )}
      </div>

      {/* The Senate — shared card, identical to the Senate tab. */}
      <div className="space-y-3">
        <h4 className={GROUP_LABEL}>The Senate</h4>
        <SenateCompositionCard condSeats={rawMultiSenateCond} irvSeats={rawMultiSenateIRV}
          condU={senateUnc?.senate.cond} irvU={senateUnc?.senate.irv} />
        <DiveCard label="Dive into the Senate →" onClick={() => onNavigate('senate')} />
      </div>

      {/* The Presidency — the two methods' winners side by side. */}
      <div className="space-y-4">
        <h4 className={GROUP_LABEL}>The Presidency</h4>
        <p className={CARD_HINT}>
          Condorcet and IRV often elect different presidents. The winner shapes which bills become law.
        </p>
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <h5 className={`${MINOR_HEADING} mb-2`}>Condorcet Winner</h5>
            {clusterByParty[condParty] && <PartyProfileCard cluster={clusterByParty[condParty]} />}
          </div>
          <div>
            <h5 className={`${MINOR_HEADING} mb-2`}>IRV Winner</h5>
            {clusterByParty[irvParty] && <PartyProfileCard cluster={clusterByParty[irvParty]} />}
          </div>
        </div>
        <DiveCard label="Dive into the Presidency →" onClick={() => onNavigate('presidency')} />
      </div>
      </div>

      {/* Section 4 — Parties */}
      <div className="space-y-4">
        <h3 className={SECTION_HEADING}>Parties</h3>
      </div>

      {/* Party profiles — blurbs + factor bars */}
      <PartyProfileGrid clusters={orderedClusters} />

      {/* Ideological Constellation */}
      <Card className="p-5">
        <h4 className={`${CARD_HEADING} mb-1`}>Ideological Constellation</h4>
        <p className={`${CARD_HINT} mb-4`}>
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

      {/* Section 4 — State disproportionality callouts */}
      <div>
        <h3 className={`${SECTION_HEADING} mb-1`}>FPTP Disproportionality — State Examples</h3>
        <p className={`${CARD_HINT} mb-3`}>
          Winner-take-all districts systematically over-represent the dominant party. Compare FPTP, 2-party proportional, and multi-party STV.
        </p>
        <FPTPDisproportionality states={fptpStates} stateMap={stateMap} />
      </div>

    </div>
  );
}
