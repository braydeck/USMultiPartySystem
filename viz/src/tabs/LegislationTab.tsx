import { useState } from 'react';
import type { VoteModelRow } from '../types';
import { UnifiedBillTable } from '../components/legislation/UnifiedBillTable';
import { LegislationDivergences } from '../components/legislation/LegislationDivergences';

interface Props {
  houseVotes: VoteModelRow[];
  senateVotes: VoteModelRow[];
}

type Pipeline = 'rawMulti' | 'factorDev';
type Method = 'condorcet' | 'irv';

const PIPELINE_LABELS: Record<Pipeline, string> = {
  rawMulti:  'Raw Multi',
  factorDev: 'Factor Dev',
};

const METHOD_LABELS: Record<Method, string> = {
  condorcet: 'Condorcet',
  irv: 'IRV',
};

export function LegislationTab({ houseVotes, senateVotes }: Props) {
  const [pipeline, setPipeline] = useState<Pipeline>('rawMulti');
  const [method, setMethod] = useState<Method>('condorcet');

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 mb-1">Legislation</h2>
        <p className="text-slate-500 text-sm">
          Probability of passage across both chambers and the presidency. Use the toggles
          to switch between Factor Dev/raw party composition and senate voting method.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 bg-slate-50 rounded-lg px-3 py-2">
          <span className="text-xs text-slate-600 uppercase tracking-widest">Pipeline</span>
          <div className="flex gap-1">
            {(Object.keys(PIPELINE_LABELS) as Pipeline[]).map(p => (
              <button
                key={p}
                onClick={() => setPipeline(p)}
                className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  pipeline === p
                    ? 'bg-indigo-600 text-white'
                    : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                }`}
              >
                {PIPELINE_LABELS[p]}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2 bg-slate-50 rounded-lg px-3 py-2">
          <span className="text-xs text-slate-600 uppercase tracking-widest">Senate Method</span>
          <div className="flex gap-1">
            {(Object.keys(METHOD_LABELS) as Method[]).map(m => (
              <button
                key={m}
                onClick={() => setMethod(m)}
                className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  method === m
                    ? 'bg-indigo-600 text-white'
                    : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                }`}
              >
                {METHOD_LABELS[m]}
              </button>
            ))}
          </div>
        </div>

      </div>

      <LegislationDivergences senateVotes={senateVotes} />

      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-3">
          Bill Passage Probability — {PIPELINE_LABELS[pipeline]} · {METHOD_LABELS[method]}
        </h3>
        <UnifiedBillTable
          houseRows={houseVotes}
          senateRows={senateVotes}
          pipeline={pipeline}
          senateMethod={method}
        />
      </div>
    </div>
  );
}
