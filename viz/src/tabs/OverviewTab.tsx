import { useMemo } from 'react';
import type {
  PresidentialElection, FDSenateSeat, HouseSeat, VoteModelRow, ClusterProfile, FDCandidateProfile,
  FPTPState, HouseStateEntry,
} from '../types';
import {
  PARTY_COLORS, PARTY_NAMES, F5_ORDER, getContrastText,
} from '../constants/parties';
import { Card } from '@/components/ui/card';
import { FPTPvsSTV } from '../components/house/FPTPvsSTV';
import { FPTPDisproportionality } from '../components/house/FPTPDisproportionality';
import { IdeologicalConstellation } from '../components/house/IdeologicalConstellation';
import { PartyProfileGrid } from '../components/shared/PartyProfileGrid';
import { PartyProfileCard } from '../components/shared/PartyProfileCard';
import { VerdictBadge, getBayesianLabel } from '../components/legislation/UnifiedBillTable';

const FPTP_SENATE = { DEM: 47, GOP: 53 };

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

function FptpSenateBar() {
  const total = FPTP_SENATE.DEM + FPTP_SENATE.GOP;
  return (
    <div className="flex items-center gap-3">
      <div className="shrink-0 text-right" style={{ width: 120 }}>
        <div className="text-xs font-semibold text-foreground">FPTP Today</div>
        <div className="text-xs text-muted-foreground">{total} seats</div>
      </div>
      <div className="flex-1 flex rounded-lg overflow-hidden h-10">
        <div
          className="flex items-center justify-center"
          style={{ width: `${(FPTP_SENATE.DEM / total) * 100}%`, backgroundColor: '#1d4ed8' }}
        >
          <span className="text-white text-xs font-bold">Dem {FPTP_SENATE.DEM}</span>
        </div>
        <div
          className="flex items-center justify-center"
          style={{ width: `${(FPTP_SENATE.GOP / total) * 100}%`, backgroundColor: '#dc2626' }}
        >
          <span className="text-white text-xs font-bold">Rep {FPTP_SENATE.GOP}</span>
        </div>
      </div>
    </div>
  );
}

function SenateBar({ seats, label }: { seats: FDSenateSeat[]; label: string }) {
  const total = seats.length;
  const counts: Record<string, number> = {};
  for (const s of seats) {
    counts[s.senatorParty] = (counts[s.senatorParty] ?? 0) + 1;
  }
  const segments = F5_ORDER.filter(p => counts[p] > 0).map(p => ({ party: p, n: counts[p] }));
  return (
    <div className="flex items-center gap-3">
      <div className="shrink-0 text-right" style={{ width: 120 }}>
        <div className="text-xs font-semibold text-foreground">{label}</div>
        <div className="text-xs text-muted-foreground">{total} seats</div>
      </div>
      <div className="flex-1 flex rounded-lg overflow-hidden h-10">
        {segments.map(({ party, n }) => {
          const pct = (n / total) * 100;
          return (
            <div
              key={party}
              title={`${PARTY_NAMES[party] ?? party}: ${n}`}
              className="flex items-center justify-center overflow-hidden"
              style={{ width: `${pct}%`, backgroundColor: PARTY_COLORS[party] ?? '#6b7280', minWidth: pct < 2 ? 2 : 0 }}
            >
              {pct >= 6 && <span className="text-xs font-bold chip-text" style={{ color: getContrastText(PARTY_COLORS[party] ?? '#6b7280') }}>{party}</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}


function PresCell({ signs, partyCode }: { signs: string | undefined; partyCode: string }) {
  const color = PARTY_COLORS[partyCode] ?? '#6b7280';
  if (!signs) return <span className="text-slate-300 text-xs">—</span>;
  return (
    <span
      className="text-xs font-bold px-2 py-0.5 rounded border whitespace-nowrap"
      style={
        signs === 'SIGN'
          ? { backgroundColor: color + '18', color, borderColor: color + '55' }
          : { backgroundColor: '#fef2f2', color: '#b91c1c', borderColor: '#fca5a5' }
      }
    >
      {signs === 'SIGN' ? 'Signs' : 'Vetoes'}
    </span>
  );
}

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

  // Join house outcomes by variable
  const houseByVar = useMemo(
    () => Object.fromEntries(houseVotes.map(r => [r.variable, r])),
    [houseVotes],
  );

  // Bills where Condorcet president and IRV president act differently
  const divergentBills = useMemo(
    () => senateVotes.filter(r =>
      r.presRawMultiCondSigns !== undefined &&
      r.presRawMultiIRVSigns  !== undefined &&
      r.presRawMultiCondSigns !== r.presRawMultiIRVSigns,
    ),
    [senateVotes],
  );

  return (
    <div className="space-y-10">
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-1">A Proportional Government</h2>
        <p className="text-muted-foreground text-sm">
          What would the US look like with proportional representation? Here&apos;s a summary across all chambers.
        </p>
      </div>

      {/* Section 1 — House FPTP vs STV */}
      <Card className="p-5 border-2 border-indigo-200">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-4">House of Representatives</h3>
        <FPTPvsSTV seats={houseSeats} />
        <div className="mt-4">
          <DiveCard label="Dive into the House →" onClick={() => onNavigate('house')} />
        </div>
      </Card>

      {/* Section 2 — Senate */}
      <Card className="p-5 space-y-3">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">Senate</h3>
        <FptpSenateBar />
        <SenateBar seats={rawMultiSenateCond} label="Condorcet" />
        <SenateBar seats={rawMultiSenateIRV} label="IRV" />
        <div className="pt-1">
          <DiveCard label="Dive into the Senate →" onClick={() => onNavigate('senate')} />
        </div>
      </Card>

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

        {divergentBills.length > 0 && (
          <Card className="overflow-hidden border-amber-300">
            <div className="px-4 py-3 bg-amber-50 border-b border-amber-200">
              <h4 className="text-sm font-semibold text-amber-900">
                {divergentBills.length} bill{divergentBills.length !== 1 ? 's' : ''} with different presidential outcomes
              </h4>
              <p className="text-xs text-amber-700 mt-0.5">
                Only bills where {condParty} and {irvParty} act differently are shown.
              </p>
            </div>

            <div className="hidden md:grid grid-cols-[1fr_88px_96px_96px_80px_80px] gap-x-2 px-4 py-2 text-xs text-muted-foreground border-b border-border/50 uppercase tracking-widest">
              <div>Bill</div>
              <div className="text-center">House</div>
              <div className="text-center">Senate (C)</div>
              <div className="text-center">Senate (IRV)</div>
              <div className="text-center font-bold" style={{ color: PARTY_COLORS[condParty] ?? '#6b7280' }}>{condParty}</div>
              <div className="text-center font-bold" style={{ color: PARTY_COLORS[irvParty] ?? '#6b7280' }}>{irvParty}</div>
            </div>

            <div className="divide-y divide-slate-100">
              {divergentBills.map(r => {
                const hr = houseByVar[r.variable];
                const houseLabel  = getBayesianLabel([hr?.probPass]);
                const condLabel   = getBayesianLabel([r.condRawMultiProbPass]);
                const irvLabel    = getBayesianLabel([r.irvRawMultiProbPass]);
                return (
                  <div
                    key={r.variable}
                    className="flex flex-col md:grid md:grid-cols-[1fr_88px_96px_96px_80px_80px] gap-x-2 items-start md:items-center px-4 py-2.5 bg-amber-50/30"
                  >
                    <div className="min-w-0 mb-1 md:mb-0">
                      <div className="text-sm text-foreground leading-snug">{r.question}</div>
                      <div className="text-xs text-muted-foreground mt-0.5">{r.domain}</div>
                    </div>
                    <div className="flex justify-center"><VerdictBadge label={houseLabel} /></div>
                    <div className="flex justify-center"><VerdictBadge label={condLabel} /></div>
                    <div className="flex justify-center"><VerdictBadge label={irvLabel} /></div>
                    <div className="flex justify-center">
                      <PresCell signs={r.presRawMultiCondSigns} partyCode={condParty} />
                    </div>
                    <div className="flex justify-center">
                      <PresCell signs={r.presRawMultiIRVSigns} partyCode={irvParty} />
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        )}

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
    </div>
  );
}
