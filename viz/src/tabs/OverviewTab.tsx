import { useMemo } from 'react';
import type {
  PresidentialElection, FDSenateSeat, HouseSeat, VoteModelRow, ClusterProfile, FDCandidateProfile,
  FPTPState, HouseStateEntry,
} from '../types';
import {
  PARTY_COLORS, PARTY_NAMES, F5_ORDER, getBlendColor, FACTOR_POLES,
} from '../constants/parties';
import { FPTPvsSTV } from '../components/house/FPTPvsSTV';
import { FPTPDisproportionality } from '../components/house/FPTPDisproportionality';
import { IdeologicalConstellation } from '../components/house/IdeologicalConstellation';
import { PartyProfileGrid } from '../components/shared/PartyProfileGrid';
import { VerdictBadge, getBayesianLabel } from '../components/legislation/UnifiedBillTable';

const FPTP_SENATE = { DEM: 47, GOP: 53 };

// Short labels for the 4 discriminating factors (F3 excluded — near-zero between-cluster variance)
const FACTOR_SHORT_LABEL: Record<string, string> = {
  F1: 'Security',
  F2: 'Electoral',
  F4: 'Religion',
  F5: 'Ideology',
};

function factorDescriptor(factor: string, value: number): string {
  const poles = FACTOR_POLES[factor];
  if (!poles) return '';
  if (value >  0.75) return `Very ${poles.high}`;
  if (value >  0.25) return poles.high;
  if (value > -0.25) return 'Moderate';
  if (value > -0.75) return poles.low;
  return `Very ${poles.low}`;
}

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
}

// ── Reusable sub-components ────────────────────────────────────────────────

function FptpSenateBar() {
  const total = FPTP_SENATE.DEM + FPTP_SENATE.GOP;
  return (
    <div className="flex items-center gap-3">
      <div className="shrink-0 text-right" style={{ width: 120 }}>
        <div className="text-xs font-semibold text-slate-700">FPTP Today</div>
        <div className="text-xs text-slate-400">{total} seats</div>
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
        <div className="text-xs font-semibold text-slate-700">{label}</div>
        <div className="text-xs text-slate-400">{total} seats</div>
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
              {pct >= 6 && <span className="text-white text-xs font-bold">{party}</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}


function PresWinnerCard({
  method, winner, cluster,
}: { method: string; winner: string; cluster: ClusterProfile | undefined }) {
  const partyCode = winner.split('_')[0];
  const color = PARTY_COLORS[partyCode] ?? getBlendColor(partyCode);
  const partyName = PARTY_NAMES[partyCode] ?? partyCode;

  return (
    <div className="rounded-xl border-2 p-4 flex flex-col gap-3" style={{ borderColor: color + '88' }}>
      <div>
        <div className="text-xs text-slate-400 font-medium uppercase tracking-wider mb-1">{method} winner</div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-black font-mono" style={{ color }}>{partyCode}</span>
          <span className="text-sm font-semibold text-slate-600">{partyName}</span>
        </div>
      </div>
      {cluster && (
        <div className="space-y-1.5">
          {(['F1', 'F2', 'F4', 'F5'] as const).map(f => {
            const val = (cluster as unknown as Record<string, number>)[f];
            const desc = factorDescriptor(f, val);
            const label = FACTOR_SHORT_LABEL[f];
            const descColor = val < -0.25 ? '#2563eb' : val > 0.25 ? '#dc2626' : '#6b7280';
            return (
              <div key={f} className="flex items-center justify-between text-xs gap-2">
                <span className="text-slate-400 shrink-0">{label}</span>
                <span className="font-medium text-right" style={{ color: descColor }}>{desc}</span>
              </div>
            );
          })}
        </div>
      )}
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

function OverviewPartyCard({ cluster }: { cluster: ClusterProfile }) {
  const color = getBlendColor(cluster.party);
  return (
    <div className="rounded-xl border overflow-hidden" style={{ borderColor: color + '55' }}>
      <div className="px-4 py-3 flex items-center justify-between" style={{ backgroundColor: color + '18' }}>
        <div>
          <span className="text-xs font-bold font-mono" style={{ color }}>{cluster.party}</span>
          <div className="text-sm font-semibold text-slate-800">{cluster.partyName}</div>
        </div>
        <span className="text-xs text-slate-500">{cluster.seatsHouse}s</span>
      </div>
      <div className="px-4 py-3 space-y-1.5">
        {(['F1', 'F2', 'F4', 'F5'] as const).map(f => {
          const val = (cluster as unknown as Record<string, number>)[f];
          const desc = factorDescriptor(f, val);
          const label = FACTOR_SHORT_LABEL[f];
          const descColor = val < -0.25 ? '#2563eb' : val > 0.25 ? '#dc2626' : '#6b7280';
          return (
            <div key={f} className="flex items-center justify-between text-xs gap-2">
              <span className="text-slate-500 shrink-0">{label}</span>
              <span className="font-medium text-right" style={{ color: descColor }}>{desc}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

export function OverviewTab({
  rawMultiElection,
  rawMultiSenateCond, rawMultiSenateIRV,
  houseSeats, senateVotes, houseVotes,
  clusters, fptpStates, stateMap, clusterSpreads,
}: Props) {
  const condWinner = rawMultiElection.condorcetWinner; // e.g. "CTR_1"
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
        <h2 className="text-2xl font-bold text-slate-900 mb-1">A Proportional Government</h2>
        <p className="text-slate-500 text-sm">
          What would the US look like with proportional representation? Here&apos;s a summary across all chambers.
        </p>
      </div>

      {/* Section 1 — House FPTP vs STV */}
      <div className="bg-white rounded-xl p-5 border-2 border-indigo-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-4">House of Representatives</h3>
        <FPTPvsSTV seats={houseSeats} />
      </div>

      {/* Section 2 — Senate */}
      <div className="bg-white rounded-xl p-5 border border-slate-200 space-y-3">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">Senate</h3>
        <FptpSenateBar />
        <SenateBar seats={rawMultiSenateCond} label="Condorcet" />
        <SenateBar seats={rawMultiSenateIRV} label="IRV" />
      </div>

      {/* Section 3 — State disproportionality callouts */}
      <div>
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">FPTP Disproportionality — State Examples</h3>
        <p className="text-xs text-slate-500 mb-3">
          Winner-take-all districts systematically over-represent the dominant party. Compare FPTP, 2-party proportional, and multi-party STV.
        </p>
        <FPTPDisproportionality states={fptpStates} stateMap={stateMap} />
      </div>

      {/* Section 4 — Presidential winners + legislative divergences */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest">Presidential Outcomes</h3>
        <p className="text-xs text-slate-500">
          Condorcet and IRV often elect different presidents. The winner shapes which bills become law.
        </p>

        <div className="grid sm:grid-cols-2 gap-4">
          <PresWinnerCard
            method="Condorcet"
            winner={condWinner}
            cluster={clusterByParty[condParty]}
          />
          <PresWinnerCard
            method="IRV"
            winner={irvWinner}
            cluster={clusterByParty[irvParty]}
          />
        </div>

        {divergentBills.length > 0 && (
          <div className="bg-white rounded-xl border border-amber-300 overflow-hidden">
            <div className="px-4 py-3 bg-amber-50 border-b border-amber-200">
              <h4 className="text-sm font-semibold text-amber-900">
                {divergentBills.length} bill{divergentBills.length !== 1 ? 's' : ''} with different presidential outcomes
              </h4>
              <p className="text-xs text-amber-700 mt-0.5">
                Only bills where {condParty} and {irvParty} act differently are shown.
              </p>
            </div>

            <div className="hidden md:grid grid-cols-[1fr_88px_96px_96px_80px_80px] gap-x-2 px-4 py-2 text-xs text-slate-500 border-b border-slate-100 uppercase tracking-widest">
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
                      <div className="text-sm text-slate-800 leading-snug">{r.question}</div>
                      <div className="text-xs text-slate-400 mt-0.5">{r.domain}</div>
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
          </div>
        )}
      </div>

      {/* Section 5 — Ideological Constellation */}
      <div className="bg-white rounded-xl p-5 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">Ideological Constellation</h3>
        <p className="text-xs text-slate-500 mb-4">
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
      </div>

      {/* Section 6 — Party profiles */}
      <PartyProfileGrid clusters={orderedClusters} />
    </div>
  );
}
