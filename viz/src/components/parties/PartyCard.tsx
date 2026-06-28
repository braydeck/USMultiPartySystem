import type { ClusterProfile } from '../../types';
import { PARTY_COLORS, FACTOR_POLES, FACTOR_LABELS } from '../../constants/parties';
import { vikForZ, vikForPctile } from '../../lib/vik';
import { Card } from '@/components/ui/card';

interface Props {
  cluster: ClusterProfile;
  mode?: 'strength' | 'percentile';
}

function zDesc(factor: string, z: number): string {
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

function pctDesc(factor: string, pctile: number): string {
  const poles = FACTOR_POLES[factor];
  if (!poles) return '';
  const isHigh = pctile >= 50;
  const pole = isHigh ? poles.high : poles.low;
  const magnitude = isHigh ? pctile : 100 - pctile;
  return `More ${pole.toLowerCase()} than ${Math.round(magnitude)}%`;
}

export function PartyCard({ cluster, mode = 'strength' }: Props) {
  const color = PARTY_COLORS[cluster.party] ?? '#6b7280';
  const positions = cluster.keyPositions ?? [];

  // Stand-in items for the top three discriminating factors (η²):
  // F5 Populist Conservatism, F1 Security & Order, F2 Electoral Skepticism.
  const racialProblems = cluster.variables['CC24_440b_agree']?.pct;
  const increasePolice = cluster.variables['CC24_321d']?.pct;
  const electionsFair = cluster.variables['CC24_421_1_agree']?.pct;

  return (
    <Card className="overflow-hidden flex flex-col" style={{ borderColor: color + '55' }}>
      <div className="px-5 py-4" style={{ backgroundColor: color + '22' }}>
        <div className="flex items-start justify-between">
          <div>
            <div className="text-xs font-bold uppercase tracking-widest mb-1" style={{ color }}>{cluster.party}</div>
            <div className="text-lg font-bold text-foreground">{cluster.partyName}</div>
          </div>
          <div className="text-xl font-bold rounded px-2 py-1" style={{ backgroundColor: color + '33', color }}>
            {cluster.seatsHouse}
            <span className="text-xs font-normal ml-1">seats</span>
          </div>
        </div>
      </div>

      <div className="px-5 py-4 flex-1">
        <div className="mb-4 space-y-2.5">
          {(['F1', 'F2', 'F3', 'F4', 'F5'] as const).map(f => {
            const z = (cluster as unknown as Record<string, number>)[`z_${f}`];
            const pctile = (cluster as unknown as Record<string, number>)[`pctile_${f}`];
            if (z == null) return null;

            if (mode === 'percentile' && pctile != null) {
              const isHigh = pctile >= 50;
              const fill = vikForPctile(pctile);
              const textColor = isHigh ? '#b91c1c' : '#1d4ed8';
              const desc = pctDesc(f, pctile);
              return (
                <div key={f}>
                  <div className="flex items-center justify-between text-xs mb-0.5">
                    <span className="text-muted-foreground">{FACTOR_LABELS[f]}</span>
                    <span className="font-medium" style={{ color: textColor }}>{desc}</span>
                  </div>
                  <div className="relative h-3 bg-muted rounded-full overflow-hidden">
                    {isHigh ? (
                      <div className="absolute top-0 left-0 h-full rounded-l-full"
                        style={{ width: `${pctile}%`, backgroundColor: fill }} />
                    ) : (
                      <div className="absolute top-0 right-0 h-full rounded-r-full"
                        style={{ width: `${100 - pctile}%`, backgroundColor: fill }} />
                    )}
                    <div className="absolute top-0 left-1/2 w-px h-full bg-slate-400" />
                  </div>
                </div>
              );
            }

            const desc = zDesc(f, z);
            const isHigh = z >= 0;
            const fill = vikForZ(z);
            const textColor = desc === 'Mixed' ? '#6b7280' : (isHigh ? '#b91c1c' : '#1d4ed8');
            const barPct = Math.min(Math.abs(z) / 2.5 * 50, 50);
            return (
              <div key={f}>
                <div className="flex items-center justify-between text-xs mb-0.5">
                  <span className="text-muted-foreground">{FACTOR_LABELS[f]}</span>
                  <span className="font-medium" style={{ color: textColor }}>{desc}</span>
                </div>
                <div className="relative h-3 bg-muted rounded-full overflow-hidden">
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

        {positions.length > 0 && (
          <div className="mb-3">
            <div className="text-xs text-muted-foreground uppercase tracking-widest mb-2">Strongest Positions</div>
            <ul className="space-y-1">
              {positions.map((pos, i) => (
                <li key={i} className="text-xs text-foreground flex items-start gap-1.5">
                  <span aria-hidden="true" className="mt-0.5 shrink-0"
                    style={{ color: pos.direction === 'supports' ? '#22c55e' : '#ef4444' }}>
                    {pos.direction === 'supports' ? '▲' : '▼'}
                  </span>
                  <span>
                    {pos.question}
                    <span className="text-muted-foreground ml-1">({Math.round(pos.pct)}% support)</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="grid grid-cols-3 gap-2 mt-3">
          {racialProblems !== undefined && <StatPill label="Racial problems rare" value={racialProblems} color={color} title="Racial problems in the U.S. are rare, isolated situations" />}
          {increasePolice !== undefined && <StatPill label="Increase police" value={increasePolice} color={color} title="Increase police by 10%" />}
          {electionsFair !== undefined && <StatPill label="Elections fair" value={electionsFair} color={color} title="Elections in the U.S. are fair" />}
        </div>
      </div>
    </Card>
  );
}

function StatPill({ label, value, color, title }: { label: string; value: number; color: string; title?: string }) {
  return (
    <div className="text-center rounded bg-muted py-2 px-1" title={title}>
      <div className="text-[11px] leading-tight text-muted-foreground mb-0.5">{label}</div>
      <div className="text-sm font-semibold" style={{ color }}>{Math.round(value)}%</div>
    </div>
  );
}
