import type { ClusterProfile } from '../../types';
import { getBlendColor, FACTOR_POLES } from '../../constants/parties';
import { vikForZ, vikForPctile } from '../../lib/vik';
import { popShareLabel } from '../../lib/population';
import { Card } from '@/components/ui/card';

const FACTOR_SHORT_LABEL: Record<string, string> = {
  F1: 'Security',
  F2: 'Elections',
  F3: 'Establishment',
  F4: 'Religion',
  F5: 'Conservatism',
};

function zDescriptor(factor: string, z: number): string {
  const poles = FACTOR_POLES[factor];
  if (!poles) return '';
  const az = Math.abs(z);
  const direction = z >= 0 ? poles.high : poles.low;
  if (az < 0.5) return 'Mixed';
  if (az < 1.0) return `Leans ${direction.toLowerCase()}`;
  if (az < 1.5) return `Moderately ${direction.toLowerCase()}`;
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
    <Card className="overflow-hidden" style={{ borderColor: color + '55' }}>
      <div className="px-4 py-3 flex items-center justify-between" style={{ backgroundColor: color + '18' }}>
        <div>
          <span className="text-xs font-bold font-mono" style={{ color }}>{cluster.party}</span>
          <div className="text-sm font-semibold text-foreground">{cluster.partyName}</div>
        </div>
        <span className="text-xs text-muted-foreground" title="share of the adult population">{popShareLabel(cluster.party)}</span>
      </div>
      <div className="px-4 py-3 space-y-2">
        {(['F1', 'F2', 'F3', 'F4', 'F5'] as const).map(f => {
          const z = (cluster as unknown as Record<string, number>)[`z_${f}`];
          const pctile = (cluster as unknown as Record<string, number>)[`pctile_${f}`];
          if (z == null) return null;
          const label = FACTOR_SHORT_LABEL[f];

          if (mode === 'percentile' && pctile != null) {
            const isHigh = pctile >= 50;
            const fill = vikForPctile(pctile);
            const textColor = isHigh ? '#b91c1c' : '#1d4ed8';
            const desc = pctileDescriptor(f, pctile);

            return (
              <div key={f}>
                <div className="flex items-center justify-between text-xs gap-2 mb-0.5">
                  <span className="text-muted-foreground shrink-0">{label}</span>
                  <span className="font-medium" style={{ color: textColor }}>{desc}</span>
                </div>
                {/* 0-100 bar, vik-colored: blue at low pole → red at high pole */}
                <div className="relative h-2 bg-muted rounded-full overflow-hidden">
                  {isHigh ? (
                    <div className="absolute top-0 left-0 h-full rounded-l-full"
                      style={{ width: `${pctile}%`, backgroundColor: fill }} />
                  ) : (
                    <div className="absolute top-0 right-0 h-full rounded-r-full"
                      style={{ width: `${100 - pctile}%`, backgroundColor: fill }} />
                  )}
                  {/* Median marker at 50% */}
                  <div className="absolute top-0 left-1/2 w-px h-full bg-slate-400" />
                </div>
              </div>
            );
          }

          // Strength mode (default)
          const desc = zDescriptor(f, z);
          const isHigh = z >= 0;
          const fill = vikForZ(z);
          const textColor = desc === 'Mixed' ? '#6b7280' : (isHigh ? '#b91c1c' : '#1d4ed8');
          const barPct = Math.min(Math.abs(z) / 2.5 * 50, 50);
          return (
            <div key={f}>
              <div className="flex items-center justify-between text-xs gap-2 mb-0.5">
                <span className="text-muted-foreground shrink-0">{label}</span>
                <span className="font-medium" style={{ color: textColor }}>{desc}</span>
              </div>
              <div className="relative h-2 bg-muted rounded-full overflow-hidden">
                {isHigh ? (
                  <div className="absolute top-0 h-full rounded-r-full"
                    style={{ left: '50%', width: `${barPct}%`, backgroundColor: fill }} />
                ) : (
                  <div className="absolute top-0 h-full rounded-l-full"
                    style={{ left: `${50 - barPct}%`, width: `${barPct}%`, backgroundColor: fill }} />
                )}
                <div className="absolute top-0 left-1/2 w-px h-full bg-slate-400" />
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
