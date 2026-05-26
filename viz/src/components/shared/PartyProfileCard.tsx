import type { ClusterProfile } from '../../types';
import { getBlendColor, FACTOR_POLES } from '../../constants/parties';

const FACTOR_SHORT_LABEL: Record<string, string> = {
  F1: 'Security',
  F2: 'Elections',
  F3: 'Establishment',
  F4: 'Religion',
  F5: 'Ideology',
};

function zDescriptor(factor: string, z: number): string {
  const poles = FACTOR_POLES[factor];
  if (!poles) return '';
  const az = Math.abs(z);
  const direction = z >= 0 ? poles.high : poles.low;
  if (az < 0.5) return 'Moderate';
  if (az < 1.0) return `Leans ${direction.toLowerCase()}`;
  if (az < 1.5) return direction;
  if (az < 2.0) return `Strongly ${direction.toLowerCase()}`;
  return `Very strongly ${direction.toLowerCase()}`;
}

function pctileDescriptor(factor: string, pctile: number): string {
  const poles = FACTOR_POLES[factor];
  if (!poles) return '';
  const isHigh = pctile >= 50;
  const pole = isHigh ? poles.high : poles.low;
  const magnitude = isHigh ? pctile : 100 - pctile;
  return `More ${pole.toLowerCase()} than ${Math.round(magnitude)}%`;
}

interface Props {
  cluster: ClusterProfile;
  mode?: 'strength' | 'percentile';
}

export function PartyProfileCard({ cluster, mode = 'strength' }: Props) {
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
      <div className="px-4 py-3 space-y-2">
        {(['F1', 'F2', 'F3', 'F4', 'F5'] as const).map(f => {
          const z = (cluster as unknown as Record<string, number>)[`z_${f}`];
          const pctile = (cluster as unknown as Record<string, number>)[`pctile_${f}`];
          if (z == null) return null;
          const label = FACTOR_SHORT_LABEL[f];

          if (mode === 'percentile' && pctile != null) {
            const isHigh = pctile >= 50;
            const magnitude = isHigh ? pctile : 100 - pctile;
            const barColor = isHigh ? '#dc2626' : '#2563eb';
            const desc = pctileDescriptor(f, pctile);
            const barPct = magnitude / 2; // 100% fills half the bar
            return (
              <div key={f}>
                <div className="flex items-center justify-between text-xs gap-2 mb-0.5">
                  <span className="text-slate-500 shrink-0">{label}</span>
                  <span className="font-medium" style={{ color: magnitude < 55 ? '#6b7280' : barColor }}>{desc}</span>
                </div>
                <div className="relative h-2 bg-slate-100 rounded-full overflow-hidden">
                  {isHigh ? (
                    <div className="absolute top-0 h-full rounded-r-full"
                      style={{ left: '50%', width: `${barPct}%`, backgroundColor: barColor, opacity: 0.5 }} />
                  ) : (
                    <div className="absolute top-0 h-full rounded-l-full"
                      style={{ left: `${50 - barPct}%`, width: `${barPct}%`, backgroundColor: barColor, opacity: 0.5 }} />
                  )}
                  <div className="absolute top-0 left-1/2 w-px h-full bg-slate-400" />
                </div>
              </div>
            );
          }

          // Strength mode (default)
          const desc = zDescriptor(f, z);
          const isHigh = z >= 0;
          const barColor = isHigh ? '#dc2626' : '#2563eb';
          const barPct = Math.min(Math.abs(z) / 2.5 * 50, 50);
          return (
            <div key={f}>
              <div className="flex items-center justify-between text-xs gap-2 mb-0.5">
                <span className="text-slate-500 shrink-0">{label}</span>
                <span className="font-medium" style={{ color: desc === 'Moderate' ? '#6b7280' : barColor }}>{desc}</span>
              </div>
              <div className="relative h-2 bg-slate-100 rounded-full overflow-hidden">
                {isHigh ? (
                  <div className="absolute top-0 h-full rounded-r-full"
                    style={{ left: '50%', width: `${barPct}%`, backgroundColor: barColor, opacity: 0.5 }} />
                ) : (
                  <div className="absolute top-0 h-full rounded-l-full"
                    style={{ left: `${50 - barPct}%`, width: `${barPct}%`, backgroundColor: barColor, opacity: 0.5 }} />
                )}
                <div className="absolute top-0 left-1/2 w-px h-full bg-slate-400" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
