import { useEffect, useMemo, useState } from 'react';
import { useUrlState } from '../hooks/useUrlState';
import { ToggleGroup } from '../components/shared/ToggleGroup';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { RaceMap } from '../components/singleRace/RaceMap';
import { ScenarioCard } from '../components/singleRace/ScenarioCard';
import { ElectorateShift } from '../components/singleRace/ElectorateShift';
import { createEngine, SHIFT_AXES } from '../lib/singleRace';
import type { SRMeta, SRVoters, ECRule, SingleRaceEngine, SRCandidate, Shift } from '../lib/singleRace';
import { getFDColor, darkenHex, lightenHex } from '../constants/parties';

type Office = 'house' | 'senate' | 'presidency';
const OFFICES: Office[] = ['house', 'senate', 'presidency'];
const OFFICE_LABELS: Record<Office, string> = { house: 'House', senate: 'Senate', presidency: 'Presidency' };
const EC_RULES: ECRule[] = ['currentLaw', 'proportional'];
const EC_LABELS: Record<ECRule, string> = { currentLaw: 'Current law', proportional: 'Proportional' };

interface Scenario { a: string; b: string; }

function parseScenarios(s: string, valid: Set<string>): Scenario[] {
  const out = s.split(',').map(p => {
    const [a, b] = p.split('.');
    return { a, b };
  }).filter(sc => valid.has(sc.a) && valid.has(sc.b));
  return out.length ? out : [{ a: 'STY', b: 'CON' }];
}
const serializeScenarios = (scs: Scenario[]) => scs.map(s => `${s.a}.${s.b}`).join(',');

// Shift sliders encode as a sparse "factor:value" list (zeros omitted), e.g. "F5:0.2,F1:-0.15".
const SHIFT_RANGE = 0.75;
function parseShift(s: string): number[] {
  const v = [0, 0, 0, 0, 0];
  if (!s) return v;
  const idxOf: Record<string, number> = {};
  for (const a of SHIFT_AXES) idxOf[a.factor] = a.idx;
  for (const part of s.split(',')) {
    const [f, raw] = part.split(':');
    const i = idxOf[f];
    const n = Number(raw);
    if (i !== undefined && Number.isFinite(n)) v[i] = Math.max(-SHIFT_RANGE, Math.min(SHIFT_RANGE, n));
  }
  return v;
}
function serializeShift(v: number[]): string {
  const out: string[] = [];
  for (const a of SHIFT_AXES) {
    const val = Math.round((v[a.idx] ?? 0) * 100) / 100;
    if (val !== 0) out.push(`${a.factor}:${val}`);
  }
  return out.join(',');
}

function colorFor(c: SRCandidate): string {
  return getFDColor(c.party, (c.direction as 'base' | 'hi' | 'lo') ?? 'base');
}
function resolveColors(a: SRCandidate, b: SRCandidate): [string, string] {
  let ac = colorFor(a);
  let bc = colorFor(b);
  if (ac === bc) bc = darkenHex(bc, 0.35);
  return [ac, bc];
}

export function SingleRaceTab() {
  const [data, setData] = useState<{ meta: SRMeta; voters: SRVoters } | null>(null);

  useEffect(() => {
    let alive = true;
    Promise.all([
      import('../data/singleRaceMeta.json'),
      fetch(`${import.meta.env.BASE_URL}data/singleRaceVoters.json`).then(r => r.json()),
    ]).then(([meta, voters]) => {
      if (alive) setData({ meta: meta.default as unknown as SRMeta, voters: voters as SRVoters });
    });
    return () => { alive = false; };
  }, []);

  if (!data) {
    return (
      <div className="py-24 text-center text-sm text-muted-foreground">Loading race data…</div>
    );
  }
  return <SingleRace meta={data.meta} voters={data.voters} />;
}

function SingleRace({ meta, voters }: { meta: SRMeta; voters: SRVoters }) {
  const engine: SingleRaceEngine = useMemo(() => createEngine(voters, meta), [voters, meta]);
  const validCodes = useMemo(() => new Set(meta.candidates.map(c => c.code)), [meta]);

  const [office, setOffice] = useUrlState<Office>('office', 'house', { allowed: OFFICES });
  const [fips, setFips] = useUrlState<string>('st', '06');
  const [cdRaw, setCd] = useUrlState<string>('cd', '');
  const [ecRule, setEcRule] = useUrlState<ECRule>('ec', 'currentLaw', { allowed: EC_RULES });
  const [scRaw, setScRaw] = useUrlState<string>('sc', 'STY.CON');
  const [opRaw, setOpRaw] = useUrlState<string>('op', '');
  const [toRaw, setToRaw] = useUrlState<string>('to', '');
  const opinionSigma = useMemo(() => parseShift(opRaw), [opRaw]);
  const turnoutSigma = useMemo(() => parseShift(toRaw), [toRaw]);
  const setOpinionSigma = (v: number[]) => setOpRaw(serializeShift(v));
  const setTurnoutSigma = (v: number[]) => setToRaw(serializeShift(v));

  // Derive the shift once per slider change (turnout β needs a per-axis solve).
  const shift: Shift | undefined = useMemo(() => {
    const hasOpinion = SHIFT_AXES.some(a => opinionSigma[a.idx] !== 0);
    const hasTurnout = SHIFT_AXES.some(a => turnoutSigma[a.idx] !== 0);
    if (!hasOpinion && !hasTurnout) return undefined;
    const opinionDelta = hasOpinion
      ? [0, 1, 2, 3, 4].map(i => opinionSigma[i] * engine.factorSD[i])
      : undefined;
    const turnoutBeta = hasTurnout ? engine.solveTurnoutBeta(turnoutSigma) : undefined;
    return { opinionDelta, turnoutBeta };
  }, [opinionSigma, turnoutSigma, engine]);

  // Effective electorate relative to today's (100% at zero turnout shift).
  const baseEss = useMemo(() => engine.essFraction(), [engine]);
  const essFraction = useMemo(
    () => Math.min(1, engine.essFraction(shift?.turnoutBeta) / baseEss),
    [engine, shift, baseEss],
  );

  const scenarios = useMemo(() => parseScenarios(scRaw, validCodes), [scRaw, validCodes]);
  const setScenarios = (next: Scenario[]) => setScRaw(serializeScenarios(next));

  const state = engine.statesByFips[fips] ?? meta.states[0];
  const cd = state.cds.includes(cdRaw) ? cdRaw : state.cds[0];

  const raceLabel = office === 'house'
    ? `${state.name} · District ${cd.split('-')[1]}`
    : office === 'senate'
      ? state.name
      : 'United States';

  // Leading-scenario winner tint for the selection map.
  const tint = useMemo(() => {
    if (office === 'presidency') return {};
    const s0 = scenarios[0];
    const a = engine.candByCode[s0.a];
    const b = engine.candByCode[s0.b];
    const [ac, bc] = resolveColors(a, b);
    const out: Record<string, string> = {};
    if (office === 'senate') {
      for (const st of meta.states) {
        const r = engine.headToHead(st.cds, a, b, shift);
        out[st.fips] = lightenHex(r.winner === 'A' ? ac : bc, 0.62);
      }
    } else {
      for (const cdId of engine.allCds) {
        const r = engine.headToHead([cdId], a, b, shift);
        out[cdId] = lightenHex(r.winner === 'A' ? ac : bc, 0.62);
      }
    }
    return out;
  }, [office, scenarios, engine, meta, shift]);

  const addScenario = () => {
    setScenarios([...scenarios, { a: scenarios[0]?.a ?? 'STY', b: 'POP' }]);
  };
  const removeScenario = (i: number) => setScenarios(scenarios.filter((_, idx) => idx !== i));
  const setA = (i: number, code: string) => setScenarios(scenarios.map((s, idx) => idx === i ? { ...s, a: code } : s));
  const setB = (i: number, code: string) => setScenarios(scenarios.map((s, idx) => idx === i ? { ...s, b: code } : s));

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Single Race Simulator</h2>
        <p className="mt-1 text-sm text-muted-foreground max-w-3xl">
          Pick two candidates and run them head-to-head under current first-past-the-post rules.
          A voter's ballot goes to whichever candidate ranks higher in the same 5-factor ideology
          model that drives the STV and IRV simulations — so a race is decided by which candidate
          the electorate actually prefers, not by renormalizing a multi-party field. Add a second
          scenario to compare matchups in the same race.
        </p>
      </div>

      <div className="flex items-center gap-x-4 gap-y-2 flex-wrap sticky top-[52px] z-10 bg-background/95 backdrop-blur py-2 border-b border-border/50">
        <ToggleGroup label="Office" value={office} onChange={setOffice} options={OFFICES} labels={OFFICE_LABELS} />
        {office === 'presidency' && (
          <ToggleGroup label="Electoral College" value={ecRule} onChange={setEcRule} options={EC_RULES} labels={EC_LABELS} />
        )}
        {office !== 'presidency' && (
          <div className="flex items-center gap-2">
            <label className="text-xs text-muted-foreground uppercase tracking-widest">Race</label>
            <select
              value={fips}
              onChange={e => { setFips(e.target.value); setCd(''); }}
              className="rounded-md border border-border bg-card px-2 py-1 text-sm"
            >
              {meta.states.map(s => <option key={s.fips} value={s.fips}>{s.name}</option>)}
            </select>
            {office === 'house' && (
              <select
                value={cd}
                onChange={e => setCd(e.target.value)}
                className="rounded-md border border-border bg-card px-2 py-1 text-sm"
              >
                {state.cds.map(c => <option key={c} value={c}>District {c.split('-')[1]}</option>)}
              </select>
            )}
          </div>
        )}
      </div>

      {office === 'presidency' && (
        <p className="text-xs text-muted-foreground max-w-3xl">
          Each state's electors go to the statewide winner ({EC_LABELS.currentLaw}), with Maine and
          Nebraska splitting by congressional district; or split in proportion to the two-way vote
          ({EC_LABELS.proportional}). 270 electoral votes win.
        </p>
      )}

      <ElectorateShift
        opinionSigma={opinionSigma}
        turnoutSigma={turnoutSigma}
        setOpinionSigma={setOpinionSigma}
        setTurnoutSigma={setTurnoutSigma}
        essFraction={essFraction}
      />

      <div className={office === 'presidency' ? 'grid gap-4 lg:grid-cols-2' : 'grid gap-4 md:grid-cols-2'}>
        {scenarios.map((s, i) => {
          const a = engine.candByCode[s.a];
          const b = engine.candByCode[s.b];
          const [ac, bc] = resolveColors(a, b);
          const h2h = office !== 'presidency'
            ? engine.headToHead(office === 'house' ? [cd] : state.cds, a, b, shift)
            : undefined;
          const ec = office === 'presidency' ? engine.presidencyEC(a, b, ecRule, shift) : undefined;
          return (
            <ScenarioCard
              key={i}
              index={i}
              candidates={meta.candidates}
              partyOrder={meta.partyOrder}
              aCode={s.a}
              bCode={s.b}
              aCand={a}
              bCand={b}
              aColor={ac}
              bColor={bc}
              office={office}
              raceLabel={raceLabel}
              h2h={h2h}
              ec={ec}
              canRemove={scenarios.length > 1}
              onChangeA={code => setA(i, code)}
              onChangeB={code => setB(i, code)}
              onRemove={() => removeScenario(i)}
            />
          );
        })}
      </div>

      <Button variant="secondary" size="sm" onClick={addScenario}>+ Add scenario</Button>

      {office !== 'presidency' && (
        <Card className="p-4 space-y-2">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">
            Race map
          </h3>
          <p className="text-xs text-muted-foreground -mt-1">
            Shaded by the leading scenario's winner. Click to change the race.
          </p>
          <RaceMap
            office={office}
            states={meta.states}
            selectedFips={fips}
            selectedCd={cd}
            onSelectState={f => { setFips(f); setCd(''); }}
            onSelectCd={setCd}
            tint={tint}
          />
        </Card>
      )}
    </div>
  );
}
