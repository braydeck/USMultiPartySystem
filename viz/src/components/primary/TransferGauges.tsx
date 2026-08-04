import type { FDPrimaryCandidate } from '../../types';
import { getBlendColor, lightenHex } from '../../constants/parties';
import { MINOR_HEADING } from '../../constants/typography';

interface Props {
  candidates: FDPrimaryCandidate[];
  stage: string;
  prevStage: string | null;
}

export function TransferGauges({ candidates, stage, prevStage }: Props) {
  const stageData = candidates.map(c => ({
    code: c.code,
    party: (c as { party?: string }).party ?? c.code.split('_')[0],
    curr: c.stages[stage],
    prev: prevStage ? c.stages[prevStage] : null,
    status: c.stages[stage]?.status ?? 'previously_eliminated',
  }));

  const eliminated = stageData.filter(c =>
    c.status === 'eliminated_this_round' && (c.curr?.votePct ?? 0) > 0
  ).sort((a, b) => (b.prev?.votePct ?? b.curr?.votePct ?? 0) - (a.prev?.votePct ?? a.curr?.votePct ?? 0));

  const surviving = stageData.filter(c =>
    ['surviving', 'elected', 'active'].includes(c.status) && (c.curr?.votePct ?? 0) > 0
  ).sort((a, b) => (b.curr?.votePct ?? 0) - (a.curr?.votePct ?? 0));

  // Max pct for scaling bars
  const maxPct = Math.max(
    ...surviving.map(c => c.curr?.votePct ?? 0),
    ...eliminated.map(c => c.prev?.votePct ?? c.curr?.votePct ?? 0),
    0.01
  );

  if (surviving.length === 0) return null;

  return (
    <div className="space-y-4">
      {/* Eliminated candidates this round */}
      {eliminated.length > 0 && (
        <div>
          <div className={`${MINOR_HEADING} mb-2`}>
            Eliminated This Round
          </div>
          <div className="space-y-1.5">
            {eliminated.map(c => {
              const pct = c.prev?.votePct ?? c.curr?.votePct ?? 0;
              const color = getBlendColor(c.party);
              const barW = (pct / maxPct) * 100;
              return (
                <div key={c.code} className="flex items-center gap-2">
                  <div className="w-20 text-xs font-mono text-muted-foreground shrink-0 text-right">{c.code}</div>
                  <div className="flex-1 relative h-5 bg-muted rounded overflow-hidden">
                    <div
                      className="absolute inset-y-0 left-0 rounded"
                      style={{
                        width: `${barW}%`,
                        backgroundColor: color,
                        opacity: 0.35,
                      }}
                    />
                    <span className="absolute inset-0 flex items-center pl-2 text-xs text-muted-foreground">
                      {(pct * 100).toFixed(1)}% → transferred
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Surviving candidates — carry-over + absorbed */}
      <div>
        <div className={`${MINOR_HEADING} mb-2`}>
          {prevStage ? 'After Transfer' : 'Vote Share'}
        </div>
        <div className="space-y-1.5">
          {surviving.map(c => {
            const currPct = c.curr?.votePct ?? 0;
            const prevPct = c.prev?.votePct ?? currPct;
            const absorbed = Math.max(0, currPct - prevPct);
            const carryover = prevPct;
            const totalBarW = (currPct / maxPct) * 100;
            const carryoverW = prevStage ? (carryover / maxPct) * 100 : totalBarW;
            const absorbedW = prevStage ? (absorbed / maxPct) * 100 : 0;
            const color = getBlendColor(c.party);
            const lightColor = lightenHex(color, 0.45);
            const isElected = c.status === 'elected';

            return (
              <div key={c.code} className="flex items-center gap-2">
                <div className="w-20 text-xs font-mono shrink-0 text-right" style={{ color }}>
                  {c.code}
                  {isElected && <span className="ml-1 text-amber-500">★</span>}
                </div>
                <div className="flex-1 relative h-5 bg-muted rounded overflow-hidden">
                  {/* Carryover portion */}
                  <div
                    className="absolute inset-y-0 left-0"
                    style={{
                      width: `${carryoverW}%`,
                      backgroundColor: color,
                      transition: 'width 350ms ease-out',
                    }}
                  />
                  {/* Absorbed / transferred portion */}
                  {absorbedW > 0 && (
                    <div
                      className="absolute inset-y-0"
                      style={{
                        left: `${carryoverW}%`,
                        width: `${absorbedW}%`,
                        backgroundColor: lightColor,
                        transition: 'width 350ms ease-out',
                      }}
                    />
                  )}
                  <span className="absolute inset-0 flex items-center pl-2 text-xs text-white font-medium mix-blend-plus-lighter">
                    {(currPct * 100).toFixed(1)}%
                    {absorbed > 0.001 && (
                      <span className="ml-1 opacity-75">(+{(absorbed * 100).toFixed(1)}%)</span>
                    )}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {prevStage && eliminated.length > 0 && (
        <div className="text-xs text-muted-foreground border-t border-border/50 pt-2">
          Darker bar = carry-over votes · lighter extension = transfers absorbed this round
        </div>
      )}
    </div>
  );
}
