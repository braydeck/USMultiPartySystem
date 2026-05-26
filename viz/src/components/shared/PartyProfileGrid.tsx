import { useState } from 'react';
import type { ClusterProfile } from '../../types';
import { PartyProfileCard } from './PartyProfileCard';

interface Props {
  clusters: ClusterProfile[];
}

export function PartyProfileGrid({ clusters }: Props) {
  const [mode, setMode] = useState<'strength' | 'percentile'>('strength');

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">Nine-Party Profiles</h3>
          <p className="text-xs text-slate-500">
            {mode === 'strength'
              ? 'Intensity of each ideological position (σ from zero = factor model center).'
              : 'How each party compares to all American voters surveyed (percentile rank).'}
          </p>
        </div>
        <div className="flex gap-1 shrink-0 ml-4">
          <button onClick={() => setMode('strength')}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              mode === 'strength' ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-600 hover:bg-slate-300'
            }`}>
            Strength
          </button>
          <button onClick={() => setMode('percentile')}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              mode === 'percentile' ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-600 hover:bg-slate-300'
            }`}>
            Percentile
          </button>
        </div>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {clusters.map(cluster => (
          <PartyProfileCard key={cluster.party} cluster={cluster} mode={mode} />
        ))}
      </div>
    </div>
  );
}
