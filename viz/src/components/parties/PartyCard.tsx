import type { ClusterProfile } from '../../types';
import { PARTY_COLORS } from '../../constants/parties';
import { FactorBar } from '../shared/FactorBar';

interface Props {
  cluster: ClusterProfile;
}

export function PartyCard({ cluster }: Props) {
  const color = PARTY_COLORS[cluster.party] ?? '#6b7280';
  const positions = cluster.keyPositions ?? [];

  const taxCut = cluster.variables['CC24_341a']?.pct;
  const immigration = cluster.variables['CC24_323b']?.pct;
  const church = cluster.variables['pew_churatd']?.pct;

  return (
    <div
      className="rounded-xl border overflow-hidden flex flex-col"
      style={{ borderColor: color + '55' }}
    >
      <div className="px-5 py-4" style={{ backgroundColor: color + '22' }}>
        <div className="flex items-start justify-between">
          <div>
            <div
              className="text-xs font-bold uppercase tracking-widest mb-1"
              style={{ color }}
            >
              {cluster.party}
            </div>
            <div className="text-lg font-bold text-slate-900">{cluster.partyName}</div>
          </div>
          <div
            className="text-xl font-bold rounded px-2 py-1"
            style={{ backgroundColor: color + '33', color }}
          >
            {cluster.seatsHouse}
            <span className="text-xs font-normal ml-1">seats</span>
          </div>
        </div>
      </div>

      <div className="px-5 py-4 flex-1">
        <div className="mb-3">
          {(['F1','F2','F3','F4','F5'] as const).map(f => (
            <FactorBar key={f} factor={f} value={(cluster as any)[f]} />
          ))}
        </div>

        {positions.length > 0 && (
          <div className="mb-3">
            <div className="text-xs text-slate-500 uppercase tracking-widest mb-2">Strongest Positions</div>
            <ul className="space-y-1">
              {positions.map((pos, i) => (
                <li key={i} className="text-xs text-slate-700 flex items-start gap-1.5">
                  <span className="sr-only">{pos.direction === 'supports' ? 'Supports:' : 'Opposes:'}</span>
                  <span
                    aria-hidden="true"
                    className="mt-0.5 shrink-0"
                    style={{ color: pos.direction === 'supports' ? '#22c55e' : '#ef4444' }}
                  >
                    {pos.direction === 'supports' ? '▲' : '▼'}
                  </span>
                  <span>
                    {pos.question}
                    <span className="text-slate-500 ml-1">({Math.round(pos.pct)}% support)</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="grid grid-cols-3 gap-2 mt-3">
          {taxCut !== undefined && (
            <StatPill label="Tax Cuts" value={taxCut} color={color} />
          )}
          {immigration !== undefined && (
            <StatPill label="Border" value={immigration} color={color} />
          )}
          {church !== undefined && (
            <StatPill label="Church" value={church} color={color} />
          )}
        </div>
      </div>
    </div>
  );
}

function StatPill({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="text-center rounded bg-slate-100 py-2 px-1">
      <div className="text-xs text-slate-500 mb-0.5">{label}</div>
      <div className="text-sm font-semibold" style={{ color }}>
        {Math.round(value)}%
      </div>
    </div>
  );
}
