import { useMemo, useState } from 'react';
import { PARTY_COLORS, PARTY_NAMES } from '../../constants/parties';

interface BucketSource { party: string; pct: number }
interface BucketDest { code: string; pct: number }
interface BucketWinner {
  code: string; party: string; entering: number;
  sources: BucketSource[]; total: number; retained: number; overflow: number;
}
interface BucketEliminated {
  code: string; party: string; entering: number;
  sources: BucketSource[]; total: number;
  dests: BucketDest[];
}
interface BucketStage {
  name: string; label: string; quota: number;
  nEntering: number; nWinners: number;
  winners: BucketWinner[]; eliminated: BucketEliminated[];
}
interface BucketData { pool: number; stages: BucketStage[] }

interface Props {
  data: BucketData;
  stageIdx: number;
}

interface TooltipInfo { x: number; y: number; lines: string[] }

function CandidatePill({ code, party, dimmed }: { code: string; party: string; dimmed?: boolean }) {
  const color = PARTY_COLORS[party] ?? '#6b7280';
  return (
    <span
      className="inline-flex items-center text-[10px] font-bold px-1.5 py-0.5 rounded text-white leading-none shrink-0"
      style={{ backgroundColor: color, opacity: dimmed ? 0.4 : 1 }}
    >
      {code}
    </span>
  );
}

export default function PrimaryBuckets({ data, stageIdx }: Props) {
  const [tip, setTip] = useState<TooltipInfo | null>(null);
  const stage = data.stages[stageIdx];
  if (!stage) return null;

  // Sort survivors by first-choice preference (entering) descending
  const sortedWinners = useMemo(
    () => [...stage.winners].sort((a, b) => b.entering - a.entering),
    [stage],
  );

  // Sort eliminated by total votes held descending
  const sortedEliminated = useMemo(
    () => [...stage.eliminated].sort((a, b) => b.total - a.total),
    [stage],
  );

  // (scaleMax no longer needed — all bars are 100% stacked)

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="text-[10px] text-muted-foreground">
        {stage.nEntering} enter → <strong className="text-muted-foreground">{stage.nWinners} survive</strong>
        {' · '}quota = {stage.quota.toFixed(1)}%
      </div>

      {/* Survivors */}
      <div className="space-y-1.5">
        <div className="text-[10px] font-bold text-emerald-600 uppercase tracking-widest mb-1">Survivors</div>
        {sortedWinners.map(w => (
          <WinnerBar key={w.code} w={w} onTip={setTip} />
        ))}
      </div>

      {/* Eliminated */}
      {sortedEliminated.length > 0 && (() => {
        const withVotes = sortedEliminated.filter(e => e.total > 0.05);
        const noVotes = sortedEliminated.filter(e => e.total <= 0.05);
        return (
          <div className="space-y-2">
            <div className="text-[10px] font-bold text-red-400 uppercase tracking-widest">Eliminated</div>
            {withVotes.length > 0 && (
              <>
                <div className="text-[10px] text-muted-foreground -mt-1 mb-1">Bars show where each eliminated candidate&apos;s votes transferred to</div>
                {withVotes.map(e => (
                  <EliminatedRow key={e.code} e={e} onTip={setTip} />
                ))}
              </>
            )}
            {noVotes.length > 0 && (
              <div>
                <div className="text-[10px] text-muted-foreground mb-1">
                  Eliminated with no votes ({noVotes.length}):
                </div>
                <div className="flex flex-wrap gap-1">
                  {noVotes.map(e => (
                    <CandidatePill key={e.code} code={e.code} party={e.party} dimmed />
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })()}

      {/* Tooltip */}
      {tip && (
        <div
          className="fixed z-50 bg-slate-800 text-white text-xs rounded px-3 py-2 shadow-lg pointer-events-none"
          style={{ left: tip.x + 12, top: tip.y - 10, maxWidth: 280 }}
        >
          {tip.lines.map((l, i) => (
            <div key={i} className={i === 0 ? 'font-semibold mb-0.5' : 'text-slate-300'}>{l}</div>
          ))}
        </div>
      )}
    </div>
  );
}


/* ── Survivor bar ─────────────────────────────────────────────────────────── */

function WinnerBar({ w, onTip }: {
  w: BucketWinner; onTip: (t: TooltipInfo | null) => void;
}) {
  const color = PARTY_COLORS[w.party] ?? '#6b7280';
  const totalInput = w.entering + w.sources.reduce((s, src) => s + src.pct, 0);

  const enteringLabel = 'First-choice';

  const segments: { label: string; pct: number; color: string; opacity: number }[] = [];
  if (w.entering > 0.05) {
    segments.push({ label: enteringLabel, pct: w.entering, color, opacity: 0.85 });
  }
  for (const src of w.sources) {
    segments.push({
      label: `← ${src.party}`,
      pct: src.pct,
      color: PARTY_COLORS[src.party] ?? '#6b7280',
      opacity: src.party === w.party ? 0.55 : 0.7,
    });
  }

  const tooltipLines = [
    `${w.code} — ${PARTY_NAMES[w.party] ?? w.party}`,
    `Retained: ${w.retained.toFixed(1)}% of pool`,
    ...(w.entering > 0 ? [`${enteringLabel}: ${w.entering.toFixed(1)}%`] : []),
    ...w.sources.map(s => `← ${s.party}: ${s.pct.toFixed(1)}%`),
    ...(w.overflow > 0.1 ? [`↗ Surplus overflow: ${w.overflow.toFixed(1)}%`] : []),
  ];

  return (
    <div className="flex items-center gap-2">
      <div className="w-20 shrink-0 text-right">
        <CandidatePill code={w.code} party={w.party} />
      </div>
      <div
        className="flex-1 h-6 cursor-pointer"
        onMouseMove={e => onTip({ x: e.clientX, y: e.clientY, lines: tooltipLines })}
        onMouseLeave={() => onTip(null)}
      >
        <div className="flex h-full rounded-sm overflow-hidden">
          {segments.map((seg, i) => {
            const widthPct = (seg.pct / totalInput) * 100;
            return (
              <div
                key={i}
                className="h-full flex items-center justify-center overflow-hidden"
                style={{
                  width: `${widthPct}%`,
                  backgroundColor: seg.color,
                  opacity: seg.opacity,
                  borderRight: i < segments.length - 1 ? '0.5px solid rgba(255,255,255,0.5)' : 'none',
                }}
              >
                {widthPct > 12 && (
                  <span className="text-[8px] font-bold text-white truncate px-0.5"
                    style={{ textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}>
                    {seg.label} {seg.pct.toFixed(1)}%
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
      <span className="text-[9px] font-bold text-muted-foreground shrink-0 w-10 text-right">
        {w.retained.toFixed(1)}%
      </span>
    </div>
  );
}


/* ── Eliminated row: label + 100% stacked bar ────────────────────────────── */

function EliminatedRow({ e, onTip }: { e: BucketEliminated; onTip: (t: TooltipInfo | null) => void }) {
  const destTotal = e.dests.reduce((s, d) => s + d.pct, 0);
  const remainder = 100 - destTotal;

  const tooltipLines = [
    `${e.code} — ELIMINATED (held ${e.total.toFixed(1)}%)`,
    ...e.dests.map(d => `→ ${d.code}: ${d.pct.toFixed(0)}%`),
    ...(remainder > 1 ? [`→ exhausted: ${remainder.toFixed(0)}%`] : []),
  ];

  return (
    <div>
      <div className="flex items-center gap-2 mb-0.5">
        <CandidatePill code={e.code} party={e.party} dimmed />
        <span className="text-[10px] text-muted-foreground">
          held {e.total.toFixed(1)}% → transferred to:
        </span>
      </div>
      <div className="flex items-center gap-2">
        <div className="w-20 shrink-0" />
        <div
          className="flex-1 h-5 cursor-pointer"
          onMouseMove={ev => onTip({ x: ev.clientX, y: ev.clientY, lines: tooltipLines })}
          onMouseLeave={() => onTip(null)}
        >
          <div className="flex h-full rounded-sm overflow-hidden">
            {e.dests.map((d, i) => {
              const destParty = d.code.split('_')[0];
              const destColor = PARTY_COLORS[destParty] ?? '#6b7280';
              return (
                <div
                  key={i}
                  className="h-full flex items-center justify-center overflow-hidden"
                  style={{
                    width: `${d.pct}%`,
                    backgroundColor: destColor,
                    opacity: 0.65,
                    borderRight: i < e.dests.length - 1 ? '0.5px solid rgba(255,255,255,0.5)' : 'none',
                  }}
                >
                  {d.pct > 12 && (
                    <span className="text-[8px] font-bold text-white truncate px-0.5"
                      style={{ textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}>
                      {d.code} {d.pct.toFixed(0)}%
                    </span>
                  )}
                </div>
              );
            })}
            {remainder > 1 && (
              <div
                className="h-full flex items-center justify-center"
                style={{ width: `${remainder}%`, backgroundColor: '#94a3b8', opacity: 0.3 }}
              >
                {remainder > 8 && (
                  <span className="text-[8px] text-muted-foreground">exh {remainder.toFixed(0)}%</span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
