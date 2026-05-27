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

export default function PrimaryBuckets({ data, stageIdx }: Props) {
  const [tip, setTip] = useState<TooltipInfo | null>(null);
  const stage = data.stages[stageIdx];
  if (!stage) return null;

  // Scale all bars against a single max so nothing overflows
  const scaleMax = useMemo(
    () => Math.max(
      ...stage.winners.map(w => w.retained),
      ...stage.eliminated.map(e => e.total),
      stage.quota,
    ),
    [stage],
  );

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="text-[10px] text-slate-400">
        {stage.nEntering} enter → <strong className="text-slate-600">{stage.nWinners} elected</strong>
        {' · '}quota = {stage.quota.toFixed(1)}%
      </div>

      {/* Elected */}
      <div className="space-y-1">
        <div className="text-[10px] font-bold text-emerald-600 uppercase tracking-widest mb-1">Elected</div>
        {stage.winners.map(w => (
          <WinnerBar key={w.code} w={w} scaleMax={scaleMax} onTip={setTip} />
        ))}
      </div>

      {/* Eliminated */}
      {stage.eliminated.length > 0 && (
        <div className="space-y-1">
          <div className="text-[10px] font-bold text-red-400 uppercase tracking-widest mb-1">Eliminated</div>
          {stage.eliminated.map(e => (
            <EliminatedBar key={e.code} e={e} scaleMax={scaleMax} quota={stage.quota} onTip={setTip} />
          ))}
        </div>
      )}

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


/* ── Winner bar: width = retained, stacked by source ─────────────────────── */

function WinnerBar({ w, scaleMax, onTip }: {
  w: BucketWinner; scaleMax: number; onTip: (t: TooltipInfo | null) => void;
}) {
  const color = PARTY_COLORS[w.party] ?? '#6b7280';
  const totalInput = w.entering + w.sources.reduce((s, src) => s + src.pct, 0);

  const segments: { pct: number; color: string; opacity: number }[] = [];
  if (w.entering > 0.05) {
    segments.push({ pct: w.entering, color, opacity: 0.85 });
  }
  for (const src of w.sources) {
    segments.push({
      pct: src.pct,
      color: PARTY_COLORS[src.party] ?? '#6b7280',
      opacity: src.party === w.party ? 0.55 : 0.7,
    });
  }

  // Bar width = retained / scaleMax, capped at 88% to leave room for label
  const barW = Math.min((w.retained / scaleMax) * 88, 88);

  const tooltipLines = [
    `${w.code} — ${PARTY_NAMES[w.party] ?? w.party}`,
    `Retained: ${w.retained.toFixed(1)}%`,
    ...(w.entering > 0 ? [`Own first-choice: ${w.entering.toFixed(1)}%`] : []),
    ...w.sources.map(s => `← ${s.party}: ${s.pct.toFixed(1)}%`),
    ...(w.overflow > 0.1 ? [`↗ Surplus overflow: ${w.overflow.toFixed(1)}%`] : []),
  ];

  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-slate-500 w-12 text-right shrink-0 font-semibold">{w.code}</span>
      <div
        className="flex-1 h-6 relative cursor-pointer overflow-hidden"
        onMouseMove={e => onTip({ x: e.clientX, y: e.clientY, lines: tooltipLines })}
        onMouseLeave={() => onTip(null)}
      >
        <div className="flex h-full rounded-sm overflow-hidden" style={{ width: `${barW}%` }}>
          {segments.map((seg, i) => (
            <div
              key={i}
              className="h-full"
              style={{
                width: `${(seg.pct / totalInput) * 100}%`,
                backgroundColor: seg.color,
                opacity: seg.opacity,
                borderRight: i < segments.length - 1 ? '0.5px solid rgba(255,255,255,0.5)' : 'none',
              }}
            />
          ))}
        </div>
        <span
          className="absolute top-0 h-full flex items-center text-[9px] font-bold text-slate-500 pointer-events-none pl-1"
          style={{ left: `${barW}%` }}
        >
          {w.retained.toFixed(1)}%
        </span>
      </div>
    </div>
  );
}


/* ── Eliminated bar: stacked showing where votes went ────────────────────── */

function EliminatedBar({ e, scaleMax, quota, onTip }: {
  e: BucketEliminated; scaleMax: number; quota: number;
  onTip: (t: TooltipInfo | null) => void;
}) {
  const barW = Math.min((e.total / scaleMax) * 88, 88);
  const destTotal = e.dests.reduce((s, d) => s + d.pct, 0);
  const remainder = 100 - destTotal;

  const tooltipLines = [
    `${e.code} — ELIMINATED (${e.total.toFixed(1)}%)`,
    ...e.dests.map(d => `→ ${d.code}: ${d.pct.toFixed(0)}%`),
    ...(remainder > 1 ? [`→ exhausted: ${remainder.toFixed(0)}%`] : []),
  ];

  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-red-400 w-12 text-right shrink-0 font-semibold">{e.code}</span>
      <div
        className="flex-1 h-5 relative cursor-pointer overflow-hidden"
        onMouseMove={ev => onTip({ x: ev.clientX, y: ev.clientY, lines: tooltipLines })}
        onMouseLeave={() => onTip(null)}
      >
        {/* Destination stacked bar — shows where their votes went */}
        <div className="flex h-full rounded-sm overflow-hidden" style={{ width: `${barW}%` }}>
          {e.dests.map((d, i) => {
            const destParty = d.code.split('_')[0];
            const destColor = PARTY_COLORS[destParty] ?? '#6b7280';
            return (
              <div
                key={i}
                className="h-full relative flex items-center justify-center overflow-hidden"
                style={{
                  width: `${(d.pct / 100) * 100}%`,
                  backgroundColor: destColor,
                  opacity: 0.6,
                  borderRight: '0.5px solid rgba(255,255,255,0.5)',
                }}
              >
                {d.pct > 15 && (
                  <span className="text-[8px] font-bold text-white truncate px-0.5"
                    style={{ textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}>
                    {d.code} {d.pct.toFixed(0)}%
                  </span>
                )}
              </div>
            );
          })}
          {remainder > 5 && (
            <div
              className="h-full flex items-center justify-center"
              style={{ width: `${(remainder / 100) * 100}%`, backgroundColor: '#94a3b8', opacity: 0.3 }}
            >
              <span className="text-[7px] text-slate-500">exh</span>
            </div>
          )}
        </div>
        <span
          className="absolute top-0 h-full flex items-center text-[9px] text-red-400/70 pointer-events-none pl-1"
          style={{ left: `${barW}%` }}
        >
          {e.total.toFixed(1)}%
        </span>
      </div>
    </div>
  );
}
