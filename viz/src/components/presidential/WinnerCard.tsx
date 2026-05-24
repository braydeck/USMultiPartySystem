import { useState } from 'react';
import type { PresidentialElection, ClusterProfile, FDCandidateProfile } from '../../types';
import { getBlendColor, PARTY_NAMES } from '../../constants/parties';

interface Props {
  data: PresidentialElection;
  clusters: ClusterProfile[];
  fdProfiles: Record<string, FDCandidateProfile>;
}

interface SharedDiff {
  question: string;
  pctA: number;
  pctB: number;
  diffPp: number;
}

interface CandidateInfo {
  code: string;
  partyName: string;
  color: string;
  finalPct?: number;
  statesWon: number;
  matchupVsOther: { margin: number; aWinsPct: number } | null;
}

function getVariables(
  code: string,
  clusters: ClusterProfile[],
  fdProfiles: Record<string, FDCandidateProfile>,
): Record<string, { pct: number; question: string }> {
  const cluster = clusters.find(c => c.party === code);
  if (cluster) return cluster.variables;
  const fd = fdProfiles[code];
  if (fd?.variables) return fd.variables as Record<string, { pct: number; question: string }>;
  // Raw Multi variant: strip _N suffix and retry (e.g. "SD_1" → "SD")
  const baseCode = code.replace(/_\d+$/, '');
  if (baseCode !== code) {
    const baseCluster = clusters.find(c => c.party === baseCode);
    if (baseCluster) return baseCluster.variables;
  }
  return {};
}

function computeSharedDiffs(
  codeA: string,
  codeB: string,
  clusters: ClusterProfile[],
  fdProfiles: Record<string, FDCandidateProfile>,
  minGap = 25,
  maxResults = 6,
): SharedDiff[] {
  const varsA = getVariables(codeA, clusters, fdProfiles);
  const varsB = getVariables(codeB, clusters, fdProfiles);
  const diffs: SharedDiff[] = [];
  for (const [key, vA] of Object.entries(varsA)) {
    const vB = varsB[key];
    if (!vB) continue;
    const gap = Math.abs(vA.pct - vB.pct);
    if (gap >= minGap) {
      diffs.push({ question: vA.question, pctA: vA.pct, pctB: vB.pct, diffPp: gap });
    }
  }
  return diffs.sort((a, b) => b.diffPp - a.diffPp).slice(0, maxResults);
}

function buildInfo(
  code: string,
  otherCode: string,
  data: PresidentialElection,
  clusters: ClusterProfile[],
  fdProfiles: Record<string, FDCandidateProfile>,
  isFinalRound: boolean,
): CandidateInfo {
  const cluster = clusters.find(c => c.party === code)
               ?? clusters.find(c => c.party === code.replace(/_\d+$/, ''));
  const fd = fdProfiles[code];
  const partyName = cluster?.partyName ?? fd?.code ?? PARTY_NAMES[code] ?? code;
  const color = getBlendColor(code);

  const finalRound = data.irvRounds[data.irvRounds.length - 1];
  const finalPct = isFinalRound
    ? finalRound?.candidates.find(c => c.code === code || c.winner)?.pct
    : undefined;

  const statesWon = Object.values(data.irvStateWinners).filter(s => s.winner === code).length;

  const matchup = data.condorcetMatchups.find(
    m => (m.candidateA === code && m.candidateB === otherCode) ||
         (m.candidateB === code && m.candidateA === otherCode)
  );
  const matchupVsOther = matchup
    ? { margin: matchup.winner === code ? matchup.margin : -matchup.margin, aWinsPct: matchup.aWinsPct }
    : null;

  return { code, partyName, color, finalPct, statesWon, matchupVsOther };
}

function CandidateCard({
  info,
  methodLabel,
  otherInfo,
  sharedDiffs,
  minGap,
}: {
  info: CandidateInfo;
  methodLabel: string;
  otherInfo: CandidateInfo;
  sharedDiffs: SharedDiff[];
  minGap: number;
}) {
  // sharedDiffs are computed as (irvWinner=A, condorcetWinner=B)
  const isIRV = methodLabel === 'IRV';

  return (
    <div className="rounded-xl border-2 overflow-hidden flex flex-col" style={{ borderColor: info.color }}>
      {/* Header */}
      <div className="px-5 py-3" style={{ backgroundColor: info.color + '12' }}>
        <div className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-0.5">
          {methodLabel} Winner
        </div>
        <div className="flex items-end gap-2">
          <div className="text-3xl font-black font-mono" style={{ color: info.color }}>{info.code}</div>
          <div className="text-base font-semibold text-slate-700 mb-0.5">{info.partyName}</div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 border-b border-slate-200 divide-x divide-slate-200">
        {info.finalPct !== undefined && (
          <div className="px-3 py-2 text-center">
            <div className="text-xl font-bold" style={{ color: info.color }}>{info.finalPct.toFixed(1)}%</div>
            <div className="text-xs text-slate-500">Final Round</div>
          </div>
        )}
        {info.finalPct === undefined && <div className="px-3 py-2" />}
        <div className="px-3 py-2 text-center">
          <div className="text-xl font-bold" style={{ color: info.color }}>{info.statesWon}</div>
          <div className="text-xs text-slate-500">States (IRV)</div>
        </div>
        <div className="px-3 py-2 text-center">
          {info.matchupVsOther !== null ? (
            <>
              <div className={`text-xl font-bold`}
                style={{ color: info.matchupVsOther.margin > 0 ? info.color : '#94a3b8' }}>
                {info.matchupVsOther.margin > 0 ? '+' : ''}{info.matchupVsOther.margin.toFixed(1)}pp
              </div>
              <div className="text-xs text-slate-500">vs {otherInfo.code}</div>
            </>
          ) : (
            <div className="text-xs text-slate-400">—</div>
          )}
        </div>
      </div>

      {/* Where they differ — show positions where this candidate is higher */}
      {sharedDiffs.length > 0 && (
        <div className="px-5 py-3 flex-1">
          <div className="text-xs font-semibold text-slate-600 uppercase tracking-widest mb-2">Where They Differ</div>
          <ul className="space-y-2">
            {sharedDiffs.map((d, i) => {
              const myPct = isIRV ? d.pctA : d.pctB;
              const theirPct = isIRV ? d.pctB : d.pctA;
              const iAmHigher = myPct > theirPct;
              return (
                <li key={i} className="text-xs">
                  <div className="flex items-start gap-1.5">
                    <span
                      className="mt-0.5 shrink-0"
                      style={{ color: iAmHigher ? '#22c55e' : '#ef4444' }}
                    >
                      {iAmHigher ? '▲' : '▼'}
                    </span>
                    <span className="text-slate-700 leading-snug">{d.question}</span>
                  </div>
                  <div className="flex gap-3 mt-0.5 ml-4 text-slate-500">
                    <span style={{ color: info.color }} className="font-semibold">{Math.round(myPct)}%</span>
                    <span className="text-slate-300">vs</span>
                    <span style={{ color: otherInfo.color }}>{Math.round(theirPct)}%</span>
                    <span className="text-slate-400">({d.diffPp.toFixed(0)}pp gap)</span>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
      {sharedDiffs.length === 0 && (
        <div className="px-5 py-4 flex-1 text-xs text-slate-400 italic">
          No policy positions with ≥{minGap}pp gap found between these candidates.
        </div>
      )}
    </div>
  );
}

export function WinnerCard({ data, clusters, fdProfiles }: Props) {
  const [minGap, setMinGap] = useState(25);

  const irvInfo = buildInfo(data.irvWinner, data.condorcetWinner, data, clusters, fdProfiles, true);
  const condInfo = buildInfo(data.condorcetWinner, data.irvWinner, data, clusters, fdProfiles, false);

  // Compute cross-candidate diffs (pctA = IRV winner, pctB = Condorcet winner)
  const sharedDiffs = computeSharedDiffs(data.irvWinner, data.condorcetWinner, clusters, fdProfiles, minGap);

  const sameWinner = data.irvWinner === data.condorcetWinner;

  return (
    <div className="space-y-3">
      {sameWinner ? (
        <div className="rounded-xl border-2 overflow-hidden" style={{ borderColor: irvInfo.color }}>
          <div className="px-5 py-3" style={{ backgroundColor: irvInfo.color + '12' }}>
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-0.5">
              IRV & Condorcet Winner
            </div>
            <div className="flex items-end gap-2">
              <div className="text-3xl font-black font-mono" style={{ color: irvInfo.color }}>{irvInfo.code}</div>
              <div className="text-base font-semibold text-slate-700 mb-0.5">{irvInfo.partyName}</div>
            </div>
          </div>
          <div className="grid grid-cols-2 border-b border-slate-200 divide-x divide-slate-200">
            <div className="px-4 py-2 text-center">
              <div className="text-xl font-bold" style={{ color: irvInfo.color }}>{irvInfo.finalPct?.toFixed(1)}%</div>
              <div className="text-xs text-slate-500">Final Round</div>
            </div>
            <div className="px-4 py-2 text-center">
              <div className="text-xl font-bold" style={{ color: irvInfo.color }}>{irvInfo.statesWon}</div>
              <div className="text-xs text-slate-500">States (IRV)</div>
            </div>
          </div>
        </div>
      ) : (
        <>
          <div className="flex justify-end">
            <label className="flex items-center gap-1.5 text-xs text-slate-500">
              Min gap to show
              <input
                type="number"
                min={0}
                max={100}
                value={minGap}
                onChange={e => setMinGap(Math.max(0, Math.min(100, Number(e.target.value))))}
                className="w-14 border border-slate-200 rounded px-2 py-1 text-center font-mono text-slate-700 bg-white"
              />
              pp
            </label>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <CandidateCard info={irvInfo} methodLabel="IRV" otherInfo={condInfo} sharedDiffs={sharedDiffs} minGap={minGap} />
            <CandidateCard info={condInfo} methodLabel="Condorcet" otherInfo={irvInfo} sharedDiffs={sharedDiffs} minGap={minGap} />
          </div>

          {/* Head-to-head callout */}
          <div className="rounded-lg bg-slate-50 border border-slate-200 px-4 py-3">
            <div className="text-xs font-semibold text-slate-600 uppercase tracking-widest mb-2">
              How They Differ
            </div>
            <div className="grid sm:grid-cols-2 gap-3 text-xs text-slate-600">
              <div>
                <span className="font-semibold" style={{ color: irvInfo.color }}>{irvInfo.code}</span>
                {' '}wins via IRV because its voters transfer well from eliminated candidates.
                In head-to-head, it
                {' '}{irvInfo.matchupVsOther?.margin != null && irvInfo.matchupVsOther.margin > 0
                  ? <span className="text-red-600 font-medium">loses</span>
                  : <span className="text-green-600 font-medium">beats</span>
                }
                {' '}<span className="font-semibold" style={{ color: condInfo.color }}>{condInfo.code}</span>
                {' '}by {Math.abs(irvInfo.matchupVsOther?.margin ?? 0).toFixed(1)}pp.
              </div>
              <div>
                <span className="font-semibold" style={{ color: condInfo.color }}>{condInfo.code}</span>
                {' '}is the Condorcet winner — it beats every other candidate in direct comparison.
                But under IRV, early eliminations prevent it from accumulating enough transfers.
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
