import { useMemo, useState } from 'react';
import { PARTY_COLORS, F5_ORDER } from '../../constants/parties';
import type { FDPrimaryData } from '../../types';

interface Props {
  data: FDPrimaryData;
  highlightStage?: number;
}

interface Segment {
  code: string;
  party: string;
  pct: number;
  willBeEliminated: boolean;
}

interface StageRow {
  label: string;
  segments: Segment[];
  quota: number; // as percentage of total pool (0 if N/A)
  eliminated: string[];
}

function partyRank(code: string): number {
  const party = code.split('_')[0];
  const idx = F5_ORDER.indexOf(party as typeof F5_ORDER[number]);
  const suffix = parseInt(code.split('_')[1] || '0', 10) || 0;
  return (idx === -1 ? 99 : idx) * 10 + suffix;
}

export default function PrimaryStageBars({ data, highlightStage }: Props) {
  const [hovered, setHovered] = useState<{ code: string; pct: number; rect: DOMRect } | null>(null);

  const rows = useMemo(() => {
    const stages = data.stagesOrder;
    const result: StageRow[] = [];

    // Row 0: Initial Slate — parties with first-choice vote shares
    // Compute from candidates: _1 candidates hold all initial first-choice votes
    // Since the JSON doesn't include Initial_Slate, we derive from After_Retail's entries
    const initialSegs: Segment[] = [];
    const partyFirstChoice: Record<string, number> = {};
    const partyCount: Record<string, number> = {};
    for (const c of data.candidates) {
      const party = c.party;
      partyCount[party] = (partyCount[party] ?? 0) + 1;
      // _1 candidates' first-choice votes ≈ the party's initial share
      // We can approximate from After_Retail: sum party's surviving + eliminated totals
      // But simpler: check if code ends in _1 and use the max stage pct ratio
    }
    // Use pool_size and voteTotal from first stage to compute first-choice %
    const firstStage = stages[0];
    const poolSize = data.candidates.reduce((s, c) => {
      const sd = c.stages[firstStage];
      return sd ? Math.max(s, sd.quotaThreshold * (
        // Droop quota = pool / (seats+1); for 12 seats: pool = quota * 13
        // For After_Retail seats=12, quota ≈ pool/13
        13)) : s;
    }, 0);
    // Collect ALL candidates at first stage (surviving + eliminated_this_round)
    for (const c of data.candidates) {
      const sd = c.stages[firstStage];
      if (!sd) continue;
      // First-choice goes entirely to _1 candidates
      // For initial display, group by party
      const party = c.party;
      if (sd.voteTotal > 0 || sd.status === 'eliminated_this_round') {
        // _1 candidates had non-zero initial votes; _2/_3 had 0
        if (c.code.endsWith('_1') || (!c.code.match(/_\d+$/))) {
          // Check: does this candidate have first-choice data?
          // Approximate initial % from the transfer math:
          // _1 candidate's initial share ≈ sum of all party candidates' After_Retail shares
          // (since surplus from _1 creates _2)
        }
      }
    }

    // Simpler approach: aggregate by party at first stage
    const partySums: Record<string, number> = {};
    for (const c of data.candidates) {
      const sd = c.stages[firstStage];
      if (!sd) continue;
      const party = c.party;
      partySums[party] = (partySums[party] ?? 0) + sd.voteTotal;
    }
    const totalVotes = Object.values(partySums).reduce((s, v) => s + v, 0) || 1;
    for (const [party, total] of Object.entries(partySums)) {
      if (total > 0) {
        initialSegs.push({
          code: `${party} ×${partyCount[party] ?? 1}`,
          party,
          pct: total / totalVotes * 100,
          willBeEliminated: false,
        });
      }
    }
    initialSegs.sort((a, b) => partyRank(a.party) - partyRank(b.party));
    // Mark parties that lose ALL candidates in the first round
    const firstStageSurvivors = new Set(
      data.candidates
        .filter(c => c.stages[firstStage]?.status === 'surviving' || c.stages[firstStage]?.status === 'elected')
        .map(c => c.party)
    );
    for (const seg of initialSegs) {
      if (!firstStageSurvivors.has(seg.party)) {
        seg.willBeEliminated = true;
      }
    }

    result.push({
      label: `Initial Slate · ${data.candidates.length} candidates, ${Object.keys(partyCount).length} parties`,
      segments: initialSegs,
      quota: 0,
      eliminated: [],
    });

    // Stage rows
    for (let i = 0; i < stages.length; i++) {
      const stage = stages[i];
      const nextStage = stages[i + 1];
      const label = data.stageLabels[stage] ?? stage.replace(/_/g, ' ').replace('After ', '');

      const segs: Segment[] = [];
      const eliminated: string[] = [];
      let poolTotal = 0;
      let quotaRaw = 0;

      for (const c of data.candidates) {
        const sd = c.stages[stage];
        if (!sd) continue;
        if ((sd.status === 'surviving' || sd.status === 'elected') && sd.votePct > 0) {
          const willBeElim = nextStage
            ? c.stages[nextStage]?.status === 'eliminated_this_round'
            : false;
          segs.push({
            code: c.code,
            party: c.party,
            pct: sd.votePct,
            willBeEliminated: willBeElim,
          });
          poolTotal += sd.voteTotal;
          if (sd.quotaThreshold > 0) quotaRaw = sd.quotaThreshold;
        }
        if (sd.status === 'eliminated_this_round') {
          eliminated.push(c.code);
        }
      }

      segs.sort((a, b) => partyRank(a.code) - partyRank(b.code));

      // Quota as % of the full pool
      const quotaPct = poolTotal > 0 ? (quotaRaw / poolTotal) * segs.length * 100 / segs.length : 0;
      // Simpler: quota / (sum of all survivor voteTotals) * 100... but that's not right either.
      // quota = pool / (seats + 1). Survivor shares sum to ~100%.
      // quota_pct_of_bar = (quota / pool) * 100 = 1/(seats+1) * 100
      const nSeats = segs.length;
      const quotaPctOfBar = nSeats > 0 ? 100 / (nSeats + 1) : 0;

      result.push({
        label: `${label} · ${segs.length} candidates`,
        segments: segs,
        quota: quotaPctOfBar,
        eliminated,
      });
    }

    return result;
  }, [data]);

  return (
    <div className="space-y-3">
      {rows.map((row, rowIdx) => {
        const isActive = highlightStage === undefined || highlightStage === rowIdx;
        const totalPct = row.segments.reduce((s, seg) => s + seg.pct, 0) || 1;

        // Group segments by party for bracket rendering
        const parties = new Map<string, Segment[]>();
        for (const seg of row.segments) {
          if (!parties.has(seg.party)) parties.set(seg.party, []);
          parties.get(seg.party)!.push(seg);
        }

        return (
          <div
            key={rowIdx}
            className="transition-opacity duration-200"
            style={{ opacity: isActive ? 1 : 0.35 }}
          >
            {/* Label row */}
            <div className="flex items-baseline gap-2 mb-0.5">
              <span className="text-xs font-semibold text-slate-600">{row.label}</span>
              {row.quota > 0 && (
                <span className="text-[10px] text-slate-400 font-medium">
                  quota {row.quota.toFixed(1)}%
                </span>
              )}
            </div>

            {/* Bar */}
            <div className="relative flex h-8 rounded overflow-hidden bg-slate-100">
              {row.segments.map((seg, si) => {
                const w = (seg.pct / totalPct) * 100;
                const color = PARTY_COLORS[seg.party] ?? '#6b7280';
                // Thin party-group separator
                const prevParty = si > 0 ? row.segments[si - 1].party : null;
                const newParty = seg.party !== prevParty;

                return (
                  <div
                    key={seg.code}
                    className="relative flex items-center justify-center overflow-hidden cursor-pointer"
                    style={{
                      width: `${w}%`,
                      minWidth: 2,
                      backgroundColor: color,
                      opacity: seg.willBeEliminated ? 0.3 : 0.85,
                      borderLeft: newParty && si > 0 ? '2px solid rgba(255,255,255,0.6)' : '0.5px solid rgba(255,255,255,0.25)',
                    }}
                    onMouseEnter={(e) => setHovered({ code: seg.code, pct: seg.pct, rect: e.currentTarget.getBoundingClientRect() })}
                    onMouseLeave={() => setHovered(null)}
                  >
                    {w > 5 && (
                      <span
                        className="text-[9px] font-bold text-white truncate px-0.5 select-none"
                        style={{ textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}
                      >
                        {seg.code}
                      </span>
                    )}
                  </div>
                );
              })}

              {/* Quota marker */}
              {row.quota > 0 && (
                <div
                  className="absolute top-0 bottom-0 pointer-events-none"
                  style={{ left: `${row.quota}%` }}
                >
                  <div className="h-full border-l-[1.5px] border-dashed border-white/80" />
                </div>
              )}
            </div>

            {/* Eliminated note */}
            {row.eliminated.length > 0 && (
              <div className="text-[10px] text-slate-400 mt-0.5 truncate">
                <span className="text-slate-500">↗</span> {row.eliminated.join(', ')} eliminated
              </div>
            )}
          </div>
        );
      })}

      {/* Floating tooltip */}
      {hovered && (
        <div
          className="fixed z-50 bg-slate-800 text-white text-xs rounded px-2.5 py-1.5 shadow-lg pointer-events-none whitespace-nowrap"
          style={{
            left: hovered.rect.left + hovered.rect.width / 2,
            top: hovered.rect.top - 32,
            transform: 'translateX(-50%)',
          }}
        >
          <span className="font-semibold">{hovered.code}</span>
          <span className="text-slate-300 ml-1">{hovered.pct.toFixed(1)}%</span>
        </div>
      )}
    </div>
  );
}
