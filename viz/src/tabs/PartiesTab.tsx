import { useState } from 'react';
import type { ClusterProfile, FDCandidateProfile } from '../types';
import { PartyCard } from '../components/parties/PartyCard';
import { IdeologicalConstellation } from '../components/house/IdeologicalConstellation';
import { FACTOR_LABELS } from '../constants/parties';
import { CompareTab } from './CompareTab';

interface Props {
  clusters: ClusterProfile[];
  clusterSpreads: { party: string; n: number; [key: string]: string | number }[];
  fdProfiles: Record<string, FDCandidateProfile>;
}

type SortFactor = 'F1' | 'F2' | 'F3' | 'F4' | 'F5';
type Section = 'profiles' | 'compare';

export function PartiesTab({ clusters, clusterSpreads, fdProfiles }: Props) {
  const [sortFactor, setSortFactor] = useState<SortFactor>('F5');
  const [cardMode, setCardMode] = useState<'strength' | 'percentile'>('strength');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [section, setSection] = useState<Section>('profiles');

  function toggleSort(f: SortFactor) {
    if (sortFactor === f) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortFactor(f);
      setSortDir('desc');
    }
  }

  const sorted = [...clusters]
    .filter(c => c.party)
    .sort((a, b) => {
      const diff = (a as any)[sortFactor] - (b as any)[sortFactor];
      return sortDir === 'asc' ? diff : -diff;
    });

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 mb-1">Parties</h2>
        <p className="text-slate-500 text-sm">
          A 10-cluster model of the American electorate, with the Blue Dog remnant (C7) merged
          into adjacent clusters. Each party reflects a distinct ideological constellation
          derived from CES 2024 survey data.
        </p>
      </div>

      {/* Section toggle — sticky */}
      <div className="sticky top-[40px] z-10 bg-white/95 backdrop-blur-sm border-b border-slate-100 -mx-4 px-4 py-2 flex gap-2">
        <button
          onClick={() => setSection('profiles')}
          className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
            section === 'profiles' ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
          }`}
        >
          Party Profiles
        </button>
        <button
          onClick={() => setSection('compare')}
          className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
            section === 'compare' ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
          }`}
        >
          Compare Policies
        </button>
      </div>

      {section === 'profiles' && (
        <>
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
              nodes={sorted.map(c => ({
                id: c.party, label: c.party,
                seats: c.seatsHouse,
                F1: ((c as any).z_F1 ?? 0),
                F2: ((c as any).z_F2 ?? 0),
                F3: ((c as any).z_F3 ?? 0),
                F4: ((c as any).z_F4 ?? 0),
                F5: ((c as any).z_F5 ?? 0),
              }))}
              clusterSpreads={clusterSpreads}
            />
          </div>

          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest">Party Profiles</h3>
            <div className="flex gap-1">
              <button onClick={() => setCardMode('strength')}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                  cardMode === 'strength' ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-600 hover:bg-slate-300'
                }`}>Strength</button>
              <button onClick={() => setCardMode('percentile')}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                  cardMode === 'percentile' ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-600 hover:bg-slate-300'
                }`}>Percentile</button>
            </div>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {sorted.map(c => (
              <PartyCard key={c.id} cluster={c} mode={cardMode} />
            ))}
          </div>
        </>
      )}

      {section === 'compare' && (
        <CompareTab clusters={clusters} fdProfiles={fdProfiles} />
      )}
    </div>
  );
}
