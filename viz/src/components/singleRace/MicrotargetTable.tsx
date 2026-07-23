import { PARTY_COLORS, getContrastText } from '../../constants/parties';
import { perClusterFaceoff, carve, type ElectionCycle } from './faceoff';
import type { MicrotargetGroup } from '../../lib/singleRace';

function rgba(hex: string, a: number): string {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!m) return `rgba(107,114,128,${a})`;
  return `rgba(${parseInt(m[1], 16)},${parseInt(m[2], 16)},${parseInt(m[3], 16)},${a})`;
}
const fmt = (v: number) => (v < 0.05 ? '—' : v >= 10 ? v.toFixed(0) : v.toFixed(1));

/**
 * Per-group breakdown as a table, grouped by action (Likely / Mobilize / Persuade) with a column for
 * each candidate under each action, so the two parties sit side by side within each action. Numbers
 * are % of that group; each column is a unidirectional heatmap in that candidate's color.
 */
export function MicrotargetTable({ groups, cycle = 'midterm', aMobRate = 0, bMobRate = 0, aColor, bColor, aParty, bParty }: {
  groups: MicrotargetGroup[]; cycle?: ElectionCycle; aMobRate?: number; bMobRate?: number;
  aColor: string; bColor: string; aParty: string; bParty: string;
}) {
  const rows = perClusterFaceoff(groups, cycle, aMobRate, bMobRate).map(cf => ({ party: cf.party, weight: cf.weight, ...carve(cf) }));
  const cols = ['aLik', 'bLik', 'aMob', 'bMob', 'aPer', 'bPer'] as const;
  const max: Record<string, number> = {};
  for (const c of cols) max[c] = Math.max(0.001, ...rows.map(r => r[c]));

  const Cell = ({ v, col, color, border }: { v: number; col: typeof cols[number]; color: string; border?: boolean }) => {
    const t = v / max[col];
    return (
      <div className={border ? 'border-l border-border/60 pl-0.5' : ''}>
        <div className="text-center tabular-nums px-1 py-1 rounded-sm"
          style={{ background: rgba(color, 0.08 + 0.8 * t), color: t > 0.55 ? getContrastText(color) : '#374151' }}>
          {fmt(v)}
        </div>
      </div>
    );
  };

  const grpHead = 'text-[9px] font-semibold uppercase tracking-wider text-center text-muted-foreground pb-0.5';
  const sub = 'text-[9px] font-semibold uppercase tracking-wider text-center';
  return (
    <div className="grid grid-cols-[52px_26px_repeat(6,minmax(0,1fr))] gap-x-1 gap-y-0.5 text-[11px] items-center">
      {/* Row 1: action groups */}
      <div /><div />
      <div className={grpHead} style={{ gridColumn: '3 / span 2' }}>Likely</div>
      <div className={`${grpHead} border-l border-border/60`} style={{ gridColumn: '5 / span 2' }}>Mobilize</div>
      <div className={`${grpHead} border-l border-border/60`} style={{ gridColumn: '7 / span 2' }}>Persuade</div>
      {/* Row 2: party sub-columns */}
      <div className="text-[9px] text-muted-foreground uppercase tracking-wider">Group</div>
      <div className="text-[9px] text-muted-foreground uppercase tracking-wider text-center">Sz</div>
      <div className={sub} style={{ color: aColor }}>{aParty}</div>
      <div className={sub} style={{ color: bColor }}>{bParty}</div>
      <div className={`${sub} border-l border-border/60`} style={{ color: aColor }}>{aParty}</div>
      <div className={sub} style={{ color: bColor }}>{bParty}</div>
      <div className={`${sub} border-l border-border/60`} style={{ color: aColor }}>{aParty}</div>
      <div className={sub} style={{ color: bColor }}>{bParty}</div>
      {/* Data */}
      {rows.map(r => (
        <div key={r.party} className="contents">
          <div className="flex items-center gap-1 min-w-0">
            <span className="w-2 h-2 rounded-full shrink-0" style={{ background: PARTY_COLORS[r.party] ?? '#6b7280' }} />
            <span className="font-medium text-foreground">{r.party}</span>
          </div>
          <div className="text-center tabular-nums text-muted-foreground">{r.weight >= 0.01 ? (r.weight * 100).toFixed(0) : '<1'}</div>
          <Cell v={r.aLik} col="aLik" color={aColor} />
          <Cell v={r.bLik} col="bLik" color={bColor} />
          <Cell v={r.aMob} col="aMob" color={aColor} border />
          <Cell v={r.bMob} col="bMob" color={bColor} />
          <Cell v={r.aPer} col="aPer" color={aColor} border />
          <Cell v={r.bPer} col="bPer" color={bColor} />
        </div>
      ))}
    </div>
  );
}
