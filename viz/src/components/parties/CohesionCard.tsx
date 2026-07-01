import type { CSSProperties } from 'react';
import { Card } from '@/components/ui/card';
import { PARTY_COLORS, PARTY_NAMES, getContrastText } from '../../constants/parties';
import cohesionData from '../../data/clusterCohesion.json';

interface PartyCohesion {
  mean: number;
  overdispersion: number | null;
  hist: number[];
  middleShare: number;
  n: number;
}
interface CohesionData {
  binCenters: number[];
  nItems: number;
  nation: PartyCohesion;
  parties: Record<string, PartyCohesion>;
}
const data = cohesionData as CohesionData;

interface Props {
  selected: string[];
}

// x-axis = share of a member's binary positions on the liberal side (0 = all
// conservative, 1 = all liberal). A tight centered mound → cross-pressured
// individuals; a spike at one pole → an internally consistent bloc.
const HIST_MAX = 60; // % scale ceiling for bar heights

function cohesionLabel(od: number | null): { text: string; note: string } {
  if (od == null) return { text: '—', note: '' };
  if (od < 0.8) return { text: 'Consistent bloc', note: 'members share the same positions' };
  if (od <= 1.15) return { text: 'Cross-pressured', note: 'members are individually mixed' };
  return { text: 'Internally split', note: 'distinct sub-groups' };
}

// conservative (left) → red, liberal (right) → blue
function binColor(center: number): string {
  const t = center; // 0..1
  const r = Math.round(220 - t * (220 - 37));
  const g = Math.round(38 + t * (99 - 38));
  const b = Math.round(38 + t * (235 - 38));
  return `rgb(${r},${g},${b})`;
}

function Histogram({ hist, mean }: { hist: number[]; mean: number }) {
  return (
    <div className="relative h-12 w-full">
      <div className="absolute inset-0 flex items-end gap-px">
        {hist.map((h, i) => (
          <div key={i} className="flex-1 rounded-t-sm"
            style={{ height: `${Math.min((h / HIST_MAX) * 100, 100)}%`, backgroundColor: binColor(data.binCenters[i]) }}
            title={`${Math.round(data.binCenters[i] * 100)}% liberal: ${h}% of members`} />
        ))}
      </div>
      {/* center (50/50) reference */}
      <div className="absolute top-0 bottom-0 left-1/2 w-px bg-slate-300" />
      {/* party mean */}
      <div className="absolute -top-1 bottom-0 w-[2px] bg-slate-800" style={{ left: `${mean * 100}%`, transform: 'translateX(-1px)' } as CSSProperties}
        title={`Mean ${Math.round(mean * 100)}% liberal`} />
    </div>
  );
}

export function CohesionCard({ selected }: Props) {
  const shown = selected.filter(p => data.parties[p]);
  if (shown.length === 0) return null;
  const nat = data.nation;

  return (
    <Card className="p-4">
      <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1">
        Internal cohesion
      </div>
      <p className="text-[11px] text-muted-foreground mb-3 leading-relaxed">
        Each bar = the share of members whose binary positions are that % on the liberal side.
        A spike at one pole = a party that coheres by <span className="font-medium text-foreground">shared positions</span>;
        a centered mound = one that coheres by <span className="font-medium text-foreground">cross-pressure</span> (members
        individually mixed). U.S. overall is bimodal (overdispersion {nat.overdispersion}); within a party that structure
        mostly collapses — what's left tells you how it holds together.
      </p>
      <div className="space-y-3">
        {shown.map(code => {
          const c = data.parties[code];
          const color = PARTY_COLORS[code] ?? '#6b7280';
          const lab = cohesionLabel(c.overdispersion);
          return (
            <div key={code} className="flex items-end gap-3">
              <div className="w-28 shrink-0">
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full chip-text-soft"
                  style={{ backgroundColor: color, color: getContrastText(color) }}>
                  {PARTY_NAMES[code] ?? code}
                </span>
                <div className="text-[10px] text-muted-foreground mt-1">{lab.text}</div>
              </div>
              <div className="flex-1 min-w-0">
                <Histogram hist={c.hist} mean={c.mean} />
              </div>
              <div className="w-36 shrink-0 text-[10px] text-muted-foreground tabular-nums leading-tight">
                <div>overdispersion <span className="font-mono font-semibold text-foreground">{c.overdispersion}</span></div>
                <div>picks compromise <span className="font-mono font-semibold text-foreground">{c.middleShare}%</span> <span className="opacity-70">(U.S. {nat.middleShare}%)</span></div>
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex justify-between text-[9px] text-muted-foreground mt-2 px-1">
        <span>← more conservative</span>
        <span>▎ party mean · dashed = 50/50</span>
        <span>more liberal →</span>
      </div>
    </Card>
  );
}
