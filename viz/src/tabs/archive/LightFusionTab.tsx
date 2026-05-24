import { useState } from 'react';
import type { BlendProfile } from '../types';
import { BlendCard } from '../components/parties/BlendCard';
import { IdeologicalConstellation } from '../components/house/IdeologicalConstellation';
import { FACTOR_LABELS } from '../constants/parties';

interface Props {
  profiles: BlendProfile[];
}

type SortFactor = 'F1' | 'F2' | 'F3' | 'F4' | 'F5';

export function LightFusionTab({ profiles }: Props) {
  const [sortFactor, setSortFactor] = useState<SortFactor>('F5');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  function toggleSort(f: SortFactor) {
    if (sortFactor === f) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortFactor(f);
      setSortDir('desc');
    }
  }

  const lfProfiles = [...profiles.filter(p => p.isLightFusion)]
    .sort((a, b) => {
      const diff = (a as unknown as Record<string, number>)[sortFactor] - (b as unknown as Record<string, number>)[sortFactor];
      return sortDir === 'asc' ? diff : -diff;
    });

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 mb-1">Light Fusion Candidates</h2>
        <p className="text-slate-500 text-sm max-w-2xl">
          Light fusion candidates run as one party but draw 80% of their identity from their
          base coalition and 20% from an adjacent one. Unlike blended senators (who genuinely
          straddle two parties), light fusion candidates maintain a clear home party while
          appealing to neighboring voters. These 16 candidates competed in the presidential
          primary alongside the 9 core parties.
        </p>
      </div>

      {/* Sort controls */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-slate-600 uppercase tracking-widest">Sort by</span>
        {(['F1','F2','F3','F4','F5'] as SortFactor[]).map(f => (
          <button
            key={f}
            onClick={() => toggleSort(f)}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              sortFactor === f
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
            }`}
          >
            {FACTOR_LABELS[f]}{' '}
            {sortFactor === f
              ? (sortDir === 'desc' ? '↓' : '↑')
              : <span className="text-slate-300">↕</span>}
          </button>
        ))}
      </div>

      {/* Constellation */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-3">
          Ideological Constellation
        </h3>
        <IdeologicalConstellation
          nodes={lfProfiles.map(p => ({
            id: p.code, label: p.code,
            seats: p.seatsCond + p.seatsIRV,
            F1: p.F1, F2: p.F2, F3: p.F3, F4: p.F4, F5: p.F5,
          }))}
        />
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {lfProfiles.map(p => (
          <BlendCard key={p.code} profile={p} />
        ))}
      </div>
    </div>
  );
}
