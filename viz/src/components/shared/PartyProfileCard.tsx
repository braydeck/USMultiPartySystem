import type { ClusterProfile } from '../../types';
import { getBlendColor, FACTOR_POLES } from '../../constants/parties';

const FACTOR_SHORT_LABEL: Record<string, string> = {
  F1: 'Security',
  F2: 'Elections',
  F3: 'Establishment',
  F4: 'Religion',
  F5: 'Ideology',
};

function pctileDescriptor(factor: string, pctile: number): string {
  const poles = FACTOR_POLES[factor];
  if (!poles) return '';
  const isHigh = pctile >= 50;
  const pole = isHigh ? poles.high : poles.low;
  const magnitude = isHigh ? pctile : 100 - pctile;
  return `${Math.round(magnitude)}% more ${pole.toLowerCase()}`;
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
      <div className="px-4 py-3 space-y-2">
        {(['F1', 'F2', 'F3', 'F4', 'F5'] as const).map(f => {
          const pctile = (cluster as unknown as Record<string, number>)[`pctile_${f}`];
          const label = FACTOR_SHORT_LABEL[f];

          if (pctile == null) return null;

          const isHigh = pctile >= 50;
          const magnitude = isHigh ? pctile : 100 - pctile;
          const barWidth = magnitude;
          const desc = pctileDescriptor(f, pctile);
          const barColor = isHigh ? '#dc2626' : '#2563eb';

          return (
            <div key={f}>
              <div className="flex items-center justify-between text-xs gap-2 mb-0.5">
                <span className="text-slate-500 shrink-0">{label}</span>
                <span className="font-medium" style={{ color: barColor }}>{desc}</span>
              </div>
              {/* Diverging bar: center = avg voter, each half = 0-100% */}
              <div className="relative h-2 bg-slate-100 rounded-full overflow-hidden">
                {isHigh ? (
                  <div className="absolute top-0 h-full rounded-r-full"
                    style={{ left: '50%', width: `${magnitude / 2}%`, backgroundColor: barColor, opacity: 0.5 }} />
                ) : (
                  <div className="absolute top-0 h-full rounded-l-full"
                    style={{ left: `${50 - magnitude / 2}%`, width: `${magnitude / 2}%`, backgroundColor: barColor, opacity: 0.5 }} />
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
