import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useUrlState } from '../../hooks/useUrlState';
import { DEPTH_KEYS, type DepthKey } from '../../constants/depth';
import { F5_ORDER, PARTY_NAMES } from '../../constants/parties';
import { CARD_HINT, MINOR_HEADING } from '../../constants/typography';
import { PartyCode } from '../shared/PartyRowLabel';

/** Percent of a group's voters represented by a district seat at party rank 1..10, then by a
 *  state-tier seat only, then unrepresented. */
type Row = number[];
type Cell = Record<string, Row>;
interface RepByRank {
  stv: Record<string, Record<string, Record<string, { off: Cell; on: Cell }>>>;
  list: Record<string, Record<string, { off: Cell; on: Cell }>>;
  mmp: Record<string, Record<string, Cell>>;
}

// One hue, dark to light, for how far down the ballot a district seat sits; indigo for a
// state-tier seat; rose for none. Checked with the dataviz validator: adjacent steps clear the
// CVD and normal-vision floors.
const BUCKETS = [
  { label: '1st choice', color: '#064e3b' },
  { label: '2nd choice', color: '#059669' },
  { label: '3rd choice', color: '#34d399' },
  { label: '4th or later', color: '#c7f9de' },
  { label: 'State reserve or top-off seat', color: '#4f46e5' },
  { label: 'None of their choices', color: '#e11d48' },
];
const NONE = BUCKETS.length - 1;
const toBuckets = (r: Row) => [r[0], r[1], r[2], r.slice(3, 10).reduce((a, b) => a + b, 0), r[10], r[11]];
const pct = (v: number) => `${v.toFixed(1)}%`;

type Tip = { x: number; y: number; title: string; values: number[] };

/** Each voter's highest-ranked party that holds one of their seats, by party and system. Reads
 *  the House tab's depth, apportionment, turnout and reserve filters from the URL, so it follows
 *  them from whichever system view it sits in. */
export function RepresentedByChoice() {
  const [depth] = useUrlState<DepthKey>('depth', 'top7', { allowed: [...DEPTH_KEYS] });
  const [wyoming] = useUrlState<'double' | 'triple'>('wyoming', 'double', { allowed: ['double', 'triple'] });
  const [part] = useUrlState<string>('part', '5', { allowed: ['0', '5', '10', '15', '20', '25', '30'] });
  const [reserve] = useUrlState<'off' | 'on'>('reserve', 'off', { allowed: ['off', 'on'] });
  const [data, setData] = useState<RepByRank | null>(null);
  const [tip, setTip] = useState<Tip | null>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const tipRef = useRef<HTMLDivElement>(null);

  // Keep the tooltip inside the chart, which is narrower than the tooltip on phones.
  useLayoutEffect(() => {
    const el = tipRef.current, box = boxRef.current;
    if (!tip || !el || !box) return;
    el.style.left = `${Math.max(0, Math.min(tip.x + 12, box.clientWidth - el.offsetWidth))}px`;
  }, [tip]);

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/houseRepByRank.json`).then(r => r.json()).then(setData).catch(() => {});
  }, []);

  const stv = data?.stv[depth]?.[wyoming]?.[part]?.[reserve];
  const list = data?.list[wyoming]?.[part]?.[reserve];
  const mmp = data?.mmp[wyoming]?.[part];
  if (!stv || !list || !mmp) return null;

  const systems = [
    { label: reserve === 'on' ? 'STV + reserve' : 'STV', cell: stv },
    { label: reserve === 'on' ? 'List + reserve' : 'Party list', cell: list },
    { label: 'MMP', cell: mmp },
  ];
  const groups = [{ key: 'ALL', name: 'All voters' }, ...F5_ORDER.map(p => ({ key: p, name: PARTY_NAMES[p] }))];

  return (
    <div ref={boxRef} className="relative" onMouseLeave={() => setTip(null)}>
      <h5 className={`${MINOR_HEADING} mb-1`}>Represented by choice</h5>
      <p className={`${CARD_HINT} mb-3 max-w-2xl leading-relaxed`}>
        Where on each voter&apos;s ballot the first party holding one of their seats sits. A voter&apos;s
        seats are their district&apos;s, plus their state&apos;s reserve or top-off seats. A voter whose
        highest-ranked seated party holds no seat in their district, only a state seat, counts under
        the state seat. Party list and MMP ballots carry one choice. Each party row is the voters who
        rank that party first.
      </p>

      <div className="flex flex-col-reverse gap-4 lg:flex-row lg:items-start">
        <div className="min-w-0 flex-1">
          <div className="grid grid-cols-[5.5rem_minmax(0,1fr)_3rem] sm:grid-cols-[10rem_5.5rem_minmax(0,1fr)_3rem] gap-x-2 pb-1 text-3xs text-muted-foreground uppercase tracking-widest">
            <span className="hidden sm:block" />
            <span />
            <span>Represented by</span>
            <span className="text-right">None</span>
          </div>
          {groups.map(g => (
            <div key={g.key}
              className={`grid grid-cols-[5.5rem_minmax(0,1fr)_3rem] sm:grid-cols-[10rem_5.5rem_minmax(0,1fr)_3rem] items-center gap-x-2 gap-y-[3px] py-1.5 border-t ${g.key === 'ALL' ? 'border-border pb-3' : 'border-border/50'}`}>
              <div className="col-span-3 sm:col-span-1 sm:row-span-3 flex items-center gap-1.5 min-w-0 text-xs font-medium text-foreground">
                {g.key !== 'ALL' && <PartyCode code={g.key} className="text-3xs font-bold" />}
                <span className="truncate" title={g.name}>{g.name}</span>
              </div>
              {systems.map(s => {
                const values = toBuckets(s.cell[g.key]);
                const title = `${g.name} · ${s.label}`;
                const describe = values.map((v, i) => `${BUCKETS[i].label} ${pct(v)}`).join(', ');
                return (
                  <SystemBar key={s.label} label={s.label} values={values} aria={`${title}: ${describe}`}
                    onHover={(e) => {
                      const box = boxRef.current?.getBoundingClientRect();
                      if (!box) return;
                      setTip({ x: e.clientX - box.left, y: e.clientY - box.top, title, values });
                    }} />
                );
              })}
            </div>
          ))}
        </div>

        <ul className="flex flex-wrap gap-x-4 gap-y-1.5 lg:flex-col lg:w-44 lg:pt-6 text-2xs text-muted-foreground">
          {BUCKETS.map(b => (
            <li key={b.label} className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-[3px]" style={{ backgroundColor: b.color }} />
              {b.label}
            </li>
          ))}
        </ul>
      </div>

      {tip && (
        <div className="pointer-events-none absolute z-10 whitespace-nowrap rounded-md border border-border bg-background px-2.5 py-2 shadow-md text-2xs"
          ref={tipRef} style={{ left: tip.x + 12, top: tip.y + 12 }}>
          <div className="font-semibold text-foreground mb-1">{tip.title}</div>
          {tip.values.map((v, i) => v >= 0.05 || i === 0 || i === NONE ? (
            <div key={i} className="flex items-center gap-1.5 text-muted-foreground">
              <span className="inline-block h-2 w-2 rounded-[2px]" style={{ backgroundColor: BUCKETS[i].color }} />
              <span className="flex-1">{BUCKETS[i].label}</span>
              <span className="tabular-nums text-foreground ml-3">{pct(v)}</span>
            </div>
          ) : null)}
        </div>
      )}
    </div>
  );
}

function SystemBar({ label, values, aria, onHover }: {
  label: string; values: number[]; aria: string; onHover: (e: React.MouseEvent<HTMLDivElement>) => void;
}) {
  return (
    <>
      <span className="text-2xs text-muted-foreground leading-tight">{label}</span>
      {/* Taller hit area than the 10px bar, so hovering a thin mark is easy. */}
      <div className="py-1 cursor-default" onMouseMove={onHover} role="img" aria-label={aria}>
        <div className="flex h-2.5 gap-[2px] overflow-hidden rounded-[4px]">
          {values.map((v, i) => v >= 0.05 && (
            <div key={i} style={{ flex: `${v} 0 0`, backgroundColor: BUCKETS[i].color }} />
          ))}
        </div>
      </div>
      <span className="text-right text-2xs tabular-nums text-foreground">{pct(values[NONE])}</span>
    </>
  );
}
