import { useState, useMemo } from 'react';
import { F5_ORDER } from '../../constants/parties';
import { PopSeatRanges, type Span, type Texture, type Quantity, type PartyValues } from '../house/PopSeatRanges';

export type { Span } from '../house/PopSeatRanges';

export interface SystemEntry {
  key: string;
  label: string;
  texture: Texture;
  seats: Record<string, number>;
  totalSeats: number;
  intervals?: Record<string, Span>;
  defaultOn?: boolean;
}

interface Props {
  systems: SystemEntry[];
  voteShare: Record<string, number>;
  voteIntervals?: Record<string, Span>;
  populationShare?: Record<string, number>;
  populationIntervals?: Record<string, Span>;
  stateOptions?: { value: string; label: string }[];
  selectedState?: string;
  onStateChange?: (v: string) => void;
  wyoming?: 'double' | 'triple';
  onWyomingChange?: (w: 'double' | 'triple') => void;
}

function Pill({ on, onClick, label }: { on: boolean; onClick: () => void; label: string }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={on}
      className={`rounded-full border px-2.5 py-0.5 text-2xs transition-colors ${on
        ? 'border-foreground/25 bg-muted text-foreground'
        : 'border-border text-muted-foreground hover:text-foreground'}`}>
      {on ? '−' : '+'} {label}
    </button>
  );
}

export function VotesVsSeats({
  systems, voteShare, voteIntervals, populationShare, populationIntervals,
  stateOptions, selectedState, onStateChange, wyoming, onWyomingChange,
}: Props) {
  const [enabled, setEnabled] = useState<Set<string>>(() => {
    const on = new Set<string>(['votes']);
    for (const s of systems) if (s.defaultOn) on.add(s.key);
    return on;
  });

  const toggle = (key: string) =>
    setEnabled(prev => { const n = new Set(prev); if (!n.delete(key)) n.add(key); return n; });

  const activeSystems = systems.filter(s => enabled.has(s.key));
  const showVotes = enabled.has('votes');
  const showPop = enabled.has('pop') && !!populationShare;

  const quantities = useMemo((): Quantity[] => {
    const qs: Quantity[] = [];
    if (showPop) qs.push({ key: 'pop', label: 'Pop', legend: 'Population', texture: 'pop' });
    if (showVotes) qs.push({ key: 'votes', label: 'Votes', legend: 'Votes', texture: 'context' });
    for (const s of activeSystems) {
      qs.push({ key: s.key, label: s.label, legend: s.label, texture: s.texture });
    }
    return qs;
  }, [showPop, showVotes, activeSystems]);

  const parties = useMemo((): PartyValues[] => {
    const rows: PartyValues[] = [];
    for (const code of F5_ORDER) {
      const hasData = (voteShare[code] ?? 0) > 0
        || activeSystems.some(s => (s.seats[code] ?? 0) > 0)
        || (showPop && (populationShare?.[code] ?? 0) > 0);
      if (!hasData) continue;

      const values: Record<string, { point: number; iv?: Span; seats?: number } | undefined> = {};
      if (showPop && populationShare) {
        values.pop = { point: populationShare[code] ?? 0, iv: populationIntervals?.[code] };
      }
      if (showVotes) {
        values.votes = { point: voteShare[code] ?? 0, iv: voteIntervals?.[code] };
      }
      for (const s of activeSystems) {
        const seatCount = s.seats[code] ?? 0;
        const pct = s.totalSeats > 0 ? seatCount / s.totalSeats * 100 : 0;
        values[s.key] = { point: pct, iv: s.intervals?.[code], seats: seatCount };
      }
      rows.push({ code, values });
    }
    return rows;
  }, [voteShare, voteIntervals, populationShare, populationIntervals, activeSystems, showPop, showVotes]);

  const max = useMemo(() => {
    let m = 5;
    for (const p of parties) {
      for (const q of quantities) {
        const v = p.values[q.key];
        if (!v) continue;
        m = Math.max(m, v.point);
        if (v.iv) m = Math.max(m, v.iv.hi);
      }
    }
    return m * 1.02;
  }, [parties, quantities]);

  const allToggleable = useMemo(() => {
    const items: { key: string; label: string }[] = [];
    if (populationShare) items.push({ key: 'pop', label: 'Population' });
    items.push({ key: 'votes', label: 'Votes' });
    for (const s of systems) items.push({ key: s.key, label: s.label });
    return items;
  }, [systems, populationShare]);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-1.5">
        {allToggleable.map(t => (
          <Pill key={t.key} label={t.label} on={enabled.has(t.key)} onClick={() => toggle(t.key)} />
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {stateOptions && onStateChange && (
          <select value={selectedState ?? 'national'} onChange={e => onStateChange(e.target.value)}
            className="rounded-md border border-border bg-card px-2 py-1 text-xs">
            {stateOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        )}
        {onWyomingChange && (
          <div className="flex gap-1">
            {(['double', 'triple'] as const).map(w => (
              <button key={w} onClick={() => onWyomingChange(w)}
                className={`text-2xs px-2 py-1 rounded-sm border ${wyoming === w
                  ? 'bg-foreground text-background border-foreground'
                  : 'border-border text-muted-foreground hover:bg-muted'}`}>
                {w === 'double' ? '2× Wyoming' : '3× Wyoming'}
              </button>
            ))}
          </div>
        )}
      </div>

      {quantities.length > 0 && parties.length > 0 ? (
        <PopSeatRanges quantities={quantities} parties={parties} max={max} />
      ) : (
        <p className="text-sm text-muted-foreground py-4">Toggle a system on to see the chart.</p>
      )}
    </div>
  );
}
