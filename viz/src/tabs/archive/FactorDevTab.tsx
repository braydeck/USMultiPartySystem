import { useState } from 'react';
import type {
  FDSenateSeat, FDHouseSeat, FDPrimaryData, FDCandidateProfile, PresidentialElection,
} from '../types';
import { PARTY_COLORS, FACTOR_LABELS } from '../constants/parties';
import { PartyVariantBar } from '../components/shared/PartyVariantBar';

interface Props {
  fdPrimary: FDPrimaryData;
  fdPresidentialElection: PresidentialElection;
  fdSenateCondorcet: FDSenateSeat[];
  fdSenateIRV: FDSenateSeat[];
  fdHouseSeats: FDHouseSeat[];
  fdProfiles: Record<string, FDCandidateProfile>;
}

function partyColor(party: string): string {
  return PARTY_COLORS[party] ?? '#6b7280';
}

/** Aggregate FD senate seats into FDHouseSeat-like shape for PartyVariantBar */
function senateToVariantSeats(seats: FDSenateSeat[]): FDHouseSeat[] {
  const countByCode: Record<string, FDHouseSeat> = {};
  for (const seat of seats) {
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
}

export function FactorDevTab({
  fdPrimary,
  fdPresidentialElection,
  fdSenateCondorcet,
  fdSenateIRV,
  fdHouseSeats,
  fdProfiles,
}: Props) {
  const [senateView, setSenateView] = useState<'condorcet' | 'irv'>('condorcet');

  // ── Presidential ──────────────────────────────────────────────────────────
  const irvWinner = fdPresidentialElection.irvWinner;
  const condorcetWinner = fdPresidentialElection.condorcetWinner;
  const irvRounds = fdPresidentialElection.irvRounds;
  const finalists = irvRounds.length > 0
    ? irvRounds[0].candidates.map(c => c.code)
    : [];

  // ── Primary finalists ─────────────────────────────────────────────────────
  const primaryFinalists = fdPrimary.candidates.filter(
    c => c.stages['After_Pod_BD']?.status === 'surviving',
  );

  // ── Senate ────────────────────────────────────────────────────────────────
  const senateSeats = senateView === 'condorcet' ? fdSenateCondorcet : fdSenateIRV;
  const senateVariantSeats = senateToVariantSeats(senateSeats);
  const totalSenateSeats = senateSeats.length;

  // ── Profiles spot-check ───────────────────────────────────────────────────
  const spotProfile = fdProfiles[irvWinner];

  return (
    <div className="space-y-8">

      {/* ── Header ── */}
      <div>
        <h2 className="text-2xl font-bold text-slate-900 mb-1">Factor Deviation Scenario</h2>
        <p className="text-slate-500 text-sm max-w-3xl">
          Instead of blending parties together, candidates deviate on individual EFA factor axes
          from their base party centroid (±25% of inter-party SD). 71 candidates across 4 axes
          competed in a full primary → general → senate → house pipeline.
        </p>
      </div>

      {/* ── Presidential results ── */}
      <div className="bg-white rounded-xl p-5 border border-slate-200 space-y-5">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest">
          Presidential Election
        </h3>

        {/* Winner cards */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: 'Primary finalists', value: primaryFinalists.length, sub: primaryFinalists.map(c => c.code).join(', ') },
            { label: 'IRV winner', value: irvWinner, sub: 'National general election', color: partyColor(fdProfiles[irvWinner]?.party ?? '') },
            { label: 'Condorcet winner', value: condorcetWinner, sub: 'Head-to-head pairwise', color: partyColor(fdProfiles[condorcetWinner]?.party ?? '') },
            { label: 'IRV rounds', value: irvRounds.length, sub: `Among ${finalists.length} finalists` },
          ].map(card => (
            <div key={card.label} className="rounded-lg border border-slate-200 p-3">
              <div className="text-xs text-slate-500 mb-1">{card.label}</div>
              <div
                className="text-xl font-bold font-mono"
                style={card.color ? { color: card.color } : undefined}
              >
                {card.value}
              </div>
              <div className="text-xs text-slate-400 mt-0.5">{card.sub}</div>
            </div>
          ))}
        </div>

        {/* IRV rounds table */}
        {irvRounds.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="text-left py-1.5 pr-3 text-slate-400 font-medium">Round</th>
                  {irvRounds[0].candidates.map(c => (
                    <th
                      key={c.code}
                      className="text-right py-1.5 px-2 font-mono font-semibold"
                      style={{ color: partyColor(fdProfiles[c.code]?.party ?? '') }}
                    >
                      {c.code}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {irvRounds.map(rnd => (
                  <tr key={rnd.round} className="border-b border-slate-50 hover:bg-slate-50">
                    <td className="py-1.5 pr-3 text-slate-500">R{rnd.round}</td>
                    {irvRounds[0].candidates.map(c => {
                      const entry = rnd.candidates.find(x => x.code === c.code);
                      if (!entry) return <td key={c.code} className="py-1.5 px-2" />;
                      return (
                        <td
                          key={c.code}
                          className={`text-right py-1.5 px-2 font-mono tabular-nums ${
                            entry.eliminated ? 'line-through text-slate-300' :
                            entry.winner    ? 'font-bold text-green-700' : 'text-slate-700'
                          }`}
                        >
                          {entry.pct.toFixed(1)}%
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Senate composition ── */}
      <div className="bg-white rounded-xl p-5 border border-slate-200 space-y-4">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest">
            Senate Composition
          </h3>
          <span className="text-xs text-slate-400">— {totalSenateSeats} seats</span>
          <div className="flex gap-1 ml-auto">
            {(['condorcet', 'irv'] as const).map(v => (
              <button
                key={v}
                onClick={() => setSenateView(v)}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                  senateView === v
                    ? 'bg-slate-800 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {v === 'condorcet' ? 'Condorcet' : 'IRV'}
              </button>
            ))}
          </div>
        </div>
        <p className="text-xs text-slate-500">
          Full color = base party; lighter = hi axis deviation; darker = lo axis deviation.
        </p>
        <PartyVariantBar seats={senateVariantSeats} />
      </div>

      {/* ── House seats ── */}
      <div className="bg-white rounded-xl p-5 border border-slate-200 space-y-3">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest">
          House Seats
        </h3>
        <p className="text-xs text-slate-500">
          873 seats stacked by axis variant. Full color = base; lighter = hi; darker = lo.
        </p>
        <PartyVariantBar seats={fdHouseSeats} totalLabel="873 house seats" />
      </div>

      {/* ── Candidate profiles spot-check ── */}
      {spotProfile && (
        <div className="bg-white rounded-xl p-5 border border-slate-200 space-y-3">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest">
            Winner Profile — {irvWinner}
          </h3>
          <div className="flex flex-wrap gap-4 text-xs">
            {(['F1','F2','F3','F4','F5'] as const).map(f => (
              <div key={f} className="space-y-0.5">
                <div className="text-slate-400">{FACTOR_LABELS[f]}</div>
                <div className="font-mono font-semibold text-slate-700">
                  {(spotProfile[f] as number).toFixed(3)}
                </div>
              </div>
            ))}
          </div>
          {spotProfile.keyPositions.length > 0 && (
            <div>
              <div className="text-xs text-slate-400 mb-2">Key positions (vs. national average)</div>
              <div className="space-y-1">
                {spotProfile.keyPositions.slice(0, 5).map(kp => (
                  <div key={kp.variable} className="flex items-start justify-between gap-4 text-xs">
                    <span className="text-slate-600 flex-1">{kp.question.slice(0, 72)}</span>
                    <span className={`font-mono font-semibold flex-shrink-0 ${kp.diff > 0 ? 'text-green-700' : 'text-red-700'}`}>
                      {kp.diff > 0 ? '+' : ''}{kp.diff.toFixed(1)}pp
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

    </div>
  );
}
