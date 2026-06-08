import { useMemo } from 'react';
import { PARTY_COLORS, F5_ORDER } from '../../constants/parties';
import type { FDPrimaryData } from '../../types';

interface Props {
  data: FDPrimaryData;
  highlightStage?: number;
}

interface CandidateEntry {
  code: string;
  party: string;
  pct: number;
  status: 'surviving' | 'elected' | 'eliminated';
}

function partyRank(code: string): number {
  const party = code.split('_')[0];
  const idx = F5_ORDER.indexOf(party as typeof F5_ORDER[number]);
  return (idx === -1 ? 99 : idx) * 100 + code.charCodeAt(code.length - 1);
}

export default function PrimaryStageBars({ data, highlightStage }: Props) {
  const stages = data.stagesOrder;

  const stageRows = useMemo(() => {
    return stages.map(stage => {
      const candidates: CandidateEntry[] = [];

      for (const c of data.candidates) {
        const sd = c.stages[stage];
        if (!sd) continue;

        if (sd.status === 'surviving' || sd.status === 'elected') {
          candidates.push({
            code: c.code,
            party: c.party,
            pct: sd.votePct,
            status: 'surviving',
          });
        } else if (sd.status === 'eliminated_this_round') {
          candidates.push({
            code: c.code,
            party: c.party,
            pct: sd.votePct,
            status: 'eliminated',
          });
        }
      }

      // Sort: surviving first (by party order), then eliminated (by party order)
      candidates.sort((a, b) => {
        if (a.status !== b.status) return a.status === 'surviving' ? -1 : 1;
        return partyRank(a.code) - partyRank(b.code);
      });

      const surviving = candidates.filter(c => c.status === 'surviving');
      const eliminated = candidates.filter(c => c.status === 'eliminated');
      const label = data.stageLabels[stage] ?? stage.replace(/_/g, ' ').replace('After ', '');
      // Droop quota as % of pool: 100 / (seats_to_fill + 1)
      // seats_to_fill = number of survivors
      const quotaPct = surviving.length > 0 ? 100 / (surviving.length + 1) : 0;

      return { stage, label, surviving, eliminated, quotaPct };
    });
  }, [data, stages]);

  return (
    <div className="space-y-5">
      {stageRows.map((row, rowIdx) => {
        const isActive = highlightStage === undefined || highlightStage === rowIdx + 1;

        return (
          <div
            key={row.stage}
            className="transition-opacity duration-200"
            style={{ opacity: isActive ? 1 : 0.4 }}
          >
            {/* Stage header */}
            <div className="flex items-baseline gap-2 mb-2">
              <span className="text-xs font-semibold text-foreground uppercase tracking-widest">
                {row.label}
              </span>
              <span className="text-[10px] text-muted-foreground">
                {row.surviving.length} advance{row.eliminated.length > 0 ? ` · ${row.eliminated.length} eliminated` : ''}
              </span>
              {row.quotaPct > 0 && (
                <span className="text-[10px] text-muted-foreground">
                  · quota {row.quotaPct.toFixed(1)}%
                </span>
              )}
            </div>

            {/* Surviving pills */}
            <div className="flex flex-wrap gap-1.5 mb-1">
              {row.surviving.map(c => {
                const color = PARTY_COLORS[c.party] ?? '#6b7280';
                return (
                  <div
                    key={c.code}
                    className="flex items-center gap-1 rounded-md px-2 py-1 text-white text-xs font-semibold"
                    style={{ backgroundColor: color }}
                    title={`${c.code}: ${c.pct.toFixed(1)}%`}
                  >
                    <span>{c.code}</span>
                    <span className="font-mono text-[10px] opacity-75">{c.pct.toFixed(1)}%</span>
                  </div>
                );
              })}
            </div>

            {/* Eliminated pills */}
            {row.eliminated.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {row.eliminated.map(c => {
                  const color = PARTY_COLORS[c.party] ?? '#6b7280';
                  return (
                    <div
                      key={c.code}
                      className="flex items-center gap-1 rounded-md px-2 py-1 text-xs font-semibold line-through opacity-40"
                      style={{ backgroundColor: color + '22', color, border: `1px solid ${color}44` }}
                      title={`${c.code}: eliminated`}
                    >
                      <span>{c.code}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
