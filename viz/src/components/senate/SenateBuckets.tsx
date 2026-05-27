import { useState } from 'react';
import { PARTY_COLORS, PARTY_NAMES } from '../../constants/parties';

interface Source { party: string; pct: number }
interface Finalist { code: string; party: string; firstChoice: number; sources: Source[]; total: number }
interface StateData { fips: string; abbr: string; condWinner: string; irvWinner: string; finalists: Finalist[] }
interface Average { party: string; seats: number; avgFirstChoice: number; avgSources: Source[]; avgTotal: number }
interface BucketData { states: Record<string, StateData>; averages: Average[] }

interface Props {
  data: BucketData;
  method: 'condorcet' | 'irv';
}

interface TooltipInfo { x: number; y: number; lines: string[] }

export default function SenateBuckets({ data, method }: Props) {
  const [selectedState, setSelectedState] = useState<string | null>(null);
  const [tip, setTip] = useState<TooltipInfo | null>(null);

  const stateList = Object.values(data.states).sort((a, b) => a.abbr.localeCompare(b.abbr));
  const selectedData = selectedState ? data.states[selectedState] : null;

  return (
    <div className="space-y-4">
      {/* State selector */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => setSelectedState(null)}
          className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
            !selectedState ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          National Average
        </button>
        <select
          value={selectedState ?? ''}
          onChange={e => setSelectedState(e.target.value || null)}
          className="text-xs border border-slate-200 rounded px-2 py-1 text-slate-600"
        >
          <option value="">Select a state…</option>
          {stateList.map(st => (
            <option key={st.fips} value={st.fips}>{st.abbr}</option>
          ))}
        </select>
      </div>

      {/* National averages */}
      {!selectedState && (
        <div className="space-y-1.5">
          <div className="text-[10px] text-slate-400 mb-2">
            Average vote composition for each winning party&apos;s senators ({method === 'condorcet' ? 'Condorcet' : 'IRV'})
          </div>
          {data.averages.map(a => {
            const color = PARTY_COLORS[a.party] ?? '#6b7280';
            const totalInput = a.avgFirstChoice + a.avgSources.reduce((s, src) => s + src.pct, 0);
            const maxBar = Math.max(...data.averages.map(x => x.avgTotal));

            return (
              <div key={a.party} className="flex items-center gap-2">
                <span className="text-[10px] text-slate-500 w-10 text-right shrink-0 font-semibold">{a.party}</span>
                <span className="text-[9px] text-slate-400 w-5 text-right shrink-0">{a.seats}s</span>
                <div
                  className="flex-1 h-6 relative cursor-pointer overflow-hidden"
                  onMouseMove={e => setTip({
                    x: e.clientX, y: e.clientY,
                    lines: [
                      `${PARTY_NAMES[a.party] ?? a.party} — ${a.seats} seats (avg)`,
                      `Own first-choice: ${a.avgFirstChoice.toFixed(1)}%`,
                      ...a.avgSources.map(s => `← ${s.party}: ${s.pct.toFixed(1)}%`),
                      `Total: ${a.avgTotal.toFixed(1)}%`,
                    ],
                  })}
                  onMouseLeave={() => setTip(null)}
                >
                  <div
                    className="flex h-full rounded-sm overflow-hidden"
                    style={{ width: `${Math.min((a.avgTotal / maxBar) * 88, 88)}%` }}
                  >
                    {a.avgFirstChoice > 0 && (
                      <div className="h-full" style={{
                        width: `${(a.avgFirstChoice / totalInput) * 100}%`,
                        backgroundColor: color, opacity: 0.85,
                      }} />
                    )}
                    {a.avgSources.map((s, i) => (
                      <div key={i} className="h-full" style={{
                        width: `${(s.pct / totalInput) * 100}%`,
                        backgroundColor: PARTY_COLORS[s.party] ?? '#6b7280',
                        opacity: 0.65,
                        borderLeft: '0.5px solid rgba(255,255,255,0.5)',
                      }} />
                    ))}
                  </div>
                  <span className="absolute top-0 h-full flex items-center text-[9px] font-bold text-slate-500 pointer-events-none pl-1"
                    style={{ left: `${Math.min((a.avgTotal / maxBar) * 88, 88)}%` }}>
                    {a.avgTotal.toFixed(1)}%
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* State drill-down */}
      {selectedData && (
        <div className="space-y-1.5">
          <div className="text-[10px] text-slate-400 mb-1">
            {selectedData.abbr} — {method === 'condorcet' ? 'Condorcet' : 'IRV'} winner:{' '}
            <strong className="text-slate-600">
              {method === 'condorcet' ? selectedData.condWinner : selectedData.irvWinner}
            </strong>
          </div>
          {selectedData.finalists.map(f => {
            const color = PARTY_COLORS[f.party] ?? '#6b7280';
            const totalInput = f.firstChoice + f.sources.reduce((s, src) => s + src.pct, 0);
            const maxBar = Math.max(...selectedData.finalists.map(x => x.total));
            const winnerCode = method === 'condorcet' ? selectedData.condWinner : selectedData.irvWinner;
            const isWinner = f.code === winnerCode;

            return (
              <div key={f.code} className="flex items-center gap-2">
                <span className={`text-[10px] w-12 text-right shrink-0 font-semibold ${isWinner ? 'text-emerald-600' : 'text-slate-400'}`}>
                  {isWinner ? '★ ' : ''}{f.code}
                </span>
                <div
                  className="flex-1 h-6 relative cursor-pointer overflow-hidden"
                  onMouseMove={e => setTip({
                    x: e.clientX, y: e.clientY,
                    lines: [
                      `${f.code} — ${PARTY_NAMES[f.party] ?? f.party}${isWinner ? ' ★ WINNER' : ''}`,
                      `Own first-choice: ${f.firstChoice.toFixed(1)}%`,
                      ...f.sources.map(s => `← ${s.party}: ${s.pct.toFixed(1)}%`),
                      `Total: ${f.total.toFixed(1)}%`,
                    ],
                  })}
                  onMouseLeave={() => setTip(null)}
                >
                  <div
                    className="flex h-full rounded-sm overflow-hidden"
                    style={{
                      width: `${Math.min((f.total / maxBar) * 88, 88)}%`,
                      border: isWinner ? `2px solid ${color}` : 'none',
                    }}
                  >
                    {f.firstChoice > 0 && (
                      <div className="h-full" style={{
                        width: `${(f.firstChoice / totalInput) * 100}%`,
                        backgroundColor: color, opacity: 0.85,
                      }} />
                    )}
                    {f.sources.map((s, i) => (
                      <div key={i} className="h-full" style={{
                        width: `${(s.pct / totalInput) * 100}%`,
                        backgroundColor: PARTY_COLORS[s.party] ?? '#6b7280',
                        opacity: 0.6,
                        borderLeft: '0.5px solid rgba(255,255,255,0.5)',
                      }} />
                    ))}
                  </div>
                  <span className="absolute top-0 h-full flex items-center text-[9px] font-bold text-slate-500 pointer-events-none pl-1"
                    style={{ left: `${Math.min((f.total / maxBar) * 88, 88)}%` }}>
                    {f.total.toFixed(1)}%
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Tooltip */}
      {tip && (
        <div className="fixed z-50 bg-slate-800 text-white text-xs rounded px-3 py-2 shadow-lg pointer-events-none"
          style={{ left: tip.x + 12, top: tip.y - 10, maxWidth: 280 }}>
          {tip.lines.map((l, i) => (
            <div key={i} className={i === 0 ? 'font-semibold mb-0.5' : 'text-slate-300'}>{l}</div>
          ))}
        </div>
      )}
    </div>
  );
}
