import type { ClusterProfile } from '../../types';
import { getBlendColor, FACTOR_POLES } from '../../constants/parties';

const FACTOR_SHORT_LABEL: Record<string, string> = {
  F1: 'Security',
  F2: 'Electoral',
  F4: 'Religion',
  F5: 'Ideology',
};

function factorDescriptor(factor: string, value: number): string {
  const poles = FACTOR_POLES[factor];
  if (!poles) return '';
  if (value >  0.75) return `Very ${poles.high}`;
  if (value >  0.25) return poles.high;
  if (value > -0.25) return 'Moderate';
  if (value > -0.75) return poles.low;
  return `Very ${poles.low}`;
}

interface Props {
  cluster: ClusterProfile;
}

export function PartyProfileCard({ cluster }: Props) {
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
      <div className="px-4 py-3 space-y-1.5">
        {(['F1', 'F2', 'F4', 'F5'] as const).map(f => {
          const val = (cluster as unknown as Record<string, number>)[f];
          const desc = factorDescriptor(f, val);
          const label = FACTOR_SHORT_LABEL[f];
          const descColor = val < -0.25 ? '#2563eb' : val > 0.25 ? '#dc2626' : '#6b7280';
          return (
            <div key={f} className="flex items-center justify-between text-xs gap-2">
              <span className="text-slate-500 shrink-0">{label}</span>
              <span className="font-medium text-right" style={{ color: descColor }}>{desc}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
