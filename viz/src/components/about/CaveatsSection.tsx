import { useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { F5_ORDER, PARTY_COLORS, PARTY_NAMES } from '../../constants/parties';
import { RangeKey, SeatRangeStrip } from '../shared/SeatRangeStrip';
import { UNCERTAINTY_STOPS, uncertaintyAt } from '../../lib/uncertainty';
import type { StateUncertainty } from '../../lib/uncertainty';
import { DEFAULT_GAP_STOP, DEFAULT_STOP_INDEX } from '../../lib/participationStops';
import { SHOW_CROSSOVER } from '../../constants/features';
import { MINOR_HEADING, TABLE_HEADER, BODY_PROSE, CARD_HINT } from '../../constants/typography';

// Local like HouseGridChart's copy: used here only to label bootstrap cells on hover.
const FIPS_TO_ABBR: Record<string, string> = {
  '01':'AL','02':'AK','04':'AZ','05':'AR','06':'CA','08':'CO','09':'CT','10':'DE','11':'DC',
  '12':'FL','13':'GA','15':'HI','16':'ID','17':'IL','18':'IN','19':'IA','20':'KS','21':'KY',
  '22':'LA','23':'ME','24':'MD','25':'MA','26':'MI','27':'MN','28':'MS','29':'MO','30':'MT',
  '31':'NE','32':'NV','33':'NH','34':'NJ','35':'NM','36':'NY','37':'NC','38':'ND','39':'OH',
  '40':'OK','41':'OR','42':'PA','44':'RI','45':'SC','46':'SD','47':'TN','48':'TX','49':'UT',
  '50':'VT','51':'VA','53':'WA','54':'WV','55':'WI','56':'WY',
};

const pct = (x: number) => Math.round(x * 100);
const partyOf = (code: string) => code.split('_')[0];
const partyName = (code: string) => PARTY_NAMES[partyOf(code)] ?? partyOf(code);
const partyColor = (code: string) => PARTY_COLORS[partyOf(code)] ?? '#64748b';

// Sequential single-hue ramp: dark = the winner reproduces itself, pale = closer to a coin
// flip. Confidence is not a good/bad axis, so no red-green encoding.
const BANDS = [
  { label: '≥90%', min: 0.90, color: '#3730a3' },
  { label: '70–90%', min: 0.70, color: '#6366f1' },
  { label: '50–70%', min: 0.50, color: '#a5b4fc' },
  { label: '<50%', min: 0, color: '#e0e7ff' },
];
const bandOf = (p: number) => BANDS.find(b => p >= b.min) ?? BANDS[BANDS.length - 1];

interface Race { abbr: string; p: number; party: string }

/** Half the 95% seat band as a share of the delegation, which is where House uncertainty
 *  actually differs by party: absolute widths look alike, relative ones do not. */
function BandWidths({ rows, max }: { rows: { party: string; rel: number }[]; max: number }) {
  return (
    <div className="rounded-lg border border-border divide-y divide-border/60">
      {rows.map(r => (
        <div key={r.party} className="flex items-center gap-3 px-3 py-1.5">
          <span className="w-24 shrink-0 text-xs font-medium leading-tight" style={{ color: PARTY_COLORS[r.party] }}>
            {PARTY_NAMES[r.party] ?? r.party}
          </span>
          <span className="h-1.5 flex-1 rounded-full bg-muted overflow-hidden">
            <span
              className="block h-full rounded-full"
              style={{ width: `${(r.rel / max) * 100}%`, backgroundColor: PARTY_COLORS[r.party] }}
            />
          </span>
          <span className="text-2xs tabular-nums text-foreground w-12 text-right">
            ±{Math.round(r.rel * 100)}%
          </span>
        </div>
      ))}
      <div className={`px-3 py-1.5 ${TABLE_HEADER}`}>
        Half the 95% band, as a share of the delegation
      </div>
    </div>
  );
}

function racesOf(states: Record<string, StateUncertainty>): Race[] {
  return Object.entries(states)
    .map(([fips, s]) => ({ abbr: FIPS_TO_ABBR[fips] ?? fips, p: s.pModal, party: s.modal }))
    .sort((a, b) => b.p - a.p);
}

/** 51 senate races as one sorted strip, so two methods can be compared by shape. */
function ConfidenceStrip({ name, races }: { name: string; races: Race[] }) {
  const mean = races.reduce((a, r) => a + r.p, 0) / races.length;
  const counts = BANDS.map(b => races.filter(r => bandOf(r.p) === b).length);
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1.5">
        <span className="text-sm font-semibold text-foreground">{name}</span>
        <span className="text-2xs text-muted-foreground tabular-nums">
          mean {pct(mean)}% · {races.length} races
        </span>
      </div>
      <div className="flex gap-[2px] mb-1.5">
        {races.map(r => (
          <div
            key={r.abbr}
            className="h-7 flex-1 min-w-0 rounded-sm"
            style={{ backgroundColor: bandOf(r.p).color }}
            title={`${r.abbr}: ${partyName(r.party)} in ${pct(r.p)}% of draws`}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {BANDS.map((b, i) => (
          <span key={b.label} className="inline-flex items-center gap-1 text-2xs text-muted-foreground tabular-nums">
            <span className="h-2 w-2 rounded-sm" style={{ backgroundColor: b.color }} />
            {counts[i]} <span className="text-muted-foreground/70">at {b.label}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

function Bar({ v, color, w = 'w-24' }: { v: number; color: string; w?: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 ${w}`}>
      <span className="h-1.5 flex-1 rounded-full bg-muted overflow-hidden">
        <span className="block h-full rounded-full" style={{ width: `${pct(v)}%`, backgroundColor: color }} />
      </span>
      <span className="text-2xs tabular-nums text-foreground w-8 text-right">{pct(v)}%</span>
    </span>
  );
}

/** Stacked share of draws won, one bar per counting method. */
function WinnerBar({ dist }: { dist: Record<string, number> }) {
  const parts = Object.entries(dist).sort((a, b) => b[1] - a[1]);
  return (
    <div className="flex h-8 rounded-md overflow-hidden">
      {parts.map(([p, v]) => (
        <div
          key={p}
          className="flex items-center justify-center text-2xs font-semibold text-white overflow-hidden whitespace-nowrap"
          style={{ width: `${v * 100}%`, backgroundColor: partyColor(p) }}
          title={`${partyName(p)}: ${pct(v)}% of draws`}
        >
          {v >= 0.14 && <span>{PARTY_NAMES[p] ?? p} {pct(v)}%</span>}
        </div>
      ))}
    </div>
  );
}

const SCOPE = {
  can: [
    'Which ideological coalitions exist in the American electorate',
    'How different counting rules produce different outcomes from the same ballots',
    'Which policy positions hold majority support across a chamber',
    'Where different electoral systems disagree and why',
    'How intra-party factionalism moves seats',
  ],
  cannot: [
    'Which party type would win in 2028',
    'Which parties would definitely form or who would run',
    'How strategic voting would change outcomes',
    'How new parties would shift voter alignments over time',
    'Whether these parties could govern together',
    'How media, money, and endorsements would shape the race',
  ],
};

const ROBUSTNESS = [
  { label: 'Item set', body: 'Re-run under a mechanical selection rule' },
  { label: 'Policy domains', body: 'Four additional domains added' },
  { label: 'Factor count', body: 'Alternative counts and rotations' },
];

type Bias = 'over' | 'under' | 'unknown' | 'design';

const BIAS_STYLE: Record<Bias, { chip: string; dot: string }> = {
  over:    { chip: 'bg-amber-50 text-amber-800 border-amber-200', dot: '▲' },
  under:   { chip: 'bg-amber-50 text-amber-800 border-amber-200', dot: '▼' },
  unknown: { chip: 'bg-slate-100 text-slate-600 border-slate-200', dot: '◆' },
  design:  { chip: 'bg-slate-100 text-slate-600 border-slate-200', dot: '●' },
};

const ASSUMPTIONS: {
  label: string; lede: string; bias: Bias; tag: string; body: string;
  source?: { href: string; label: string };
}[] = [
  {
    label: 'Perfect party cohesion',
    lede: 'Members vote with their party on every bill, so passage probabilities come out sharper than a real chamber’s.',
    bias: 'over', tag: 'Overstates certainty',
    body: 'Senators and representatives vote with their party 100% of the time in the legislation model. Real legislatures run from about 70% discipline (US Democrats) to about 95% (UK Conservatives).',
  },
  {
    label: 'Institutional distrust is a floor',
    lede: 'The most distrustful voters are the least likely to have returned for the post-election wave the factor is built from.',
    bias: 'under', tag: 'Understates distrust',
    body: 'Clustering requires a complete answer on all 24 items, which restricts the sample to the ~45,700 respondents who returned for the post-election wave. That attrition is not random: the returners run about eleven years older and more politically engaged than the full 60,000, and the post-election weights correct the demographic margins but not the engagement gap. Institutional distrust is the factor most exposed, because it is built entirely from post-wave items (election fairness, trust in federal and state government), and among voters who did answer, the least engaged are the most distrustful. Read the scores as a floor: the simulation more likely understates distrust than overstates it, especially toward elections and state government.',
  },
  {
    label: 'Sincere voting',
    lede: 'Ballots rank by genuine proximity. No burying strong rivals, no tactical top-ranking.',
    bias: 'unknown', tag: 'Direction unknown',
    body: 'Voters rank candidates by ideological proximity. In real ranked-choice elections, strategic voting (burying strong competitors, propping up weak ones) is common. This simulation shows what sincere preferences would produce.',
  },
  {
    label: 'Static ideological space',
    lede: 'The five-factor space is fit to 2024 and held fixed. Platforms and alignments never move.',
    bias: 'unknown', tag: 'Direction unknown',
    body: 'The 5D factor space is fit to CES 2024 data and held fixed. In reality, the emergence of new parties would shift voter alignments, party platforms would evolve, and the factor structure itself might change.',
  },
  {
    label: 'Slate discipline is total',
    lede: 'Every voter ranks their party’s slate in the same order, so transfers never leak to a rival before the party is exhausted.',
    bias: 'over', tag: 'Overstates discipline',
    body: 'Same-party candidates share their party’s posterior score, so they occupy consecutive ranks, and within that block every voter lists the slate in one fixed order. That is the strong-discipline limit case: real parties control their transfers imperfectly and unevenly, and how well a party manages them is part of how it converts votes into seats. Slate size does respond to local strength (3 candidates above a 12% district share, 2 above 5%, 1 above 1%), so mis-nomination is possible, but cross-party slates and factional tickets are not modeled at all.',
  },
  {
    label: 'Full compliance with the ranking instruction',
    lede: 'Every ballot ranks exactly as deep as the instruction asks, so exhaustion comes out higher than a real electorate’s.',
    bias: 'over', tag: 'Overstates exhaustion',
    body: 'Ballots truncate at the instructed depth for every voter. In ACT Legislative Assembly elections, which fill 5-seat electorates by Hare-Clark STV and instruct voters to number five boxes, 98.2% met the minimum, 68.4% stopped at exactly five, and roughly 30% ranked more than required, so real depth sits at the instruction and above it. Truncating everyone at the instruction therefore understates ranking depth, and the below-quota and exhaustion figures reported at each depth are ceilings rather than point estimates. The ACT votes under compulsory turnout, so its compliance rate is an upper bound.',
    source: {
      href: 'https://www.parliament.act.gov.au/__data/assets/pdf_file/0009/3052467/Ballot-paper-preference-analysis-impact-of-ballot-paper-instructions.pdf',
      label: 'Ballot paper preference analysis, ACT Legislative Assembly ↗',
    },
  },
  {
    label: 'The whole Senate is elected at once',
    lede: 'One race per state plus DC, filling both seats. Contested states split their delegation.',
    bias: 'design', tag: 'Scope choice',
    body: 'The Senate has staggered six-year terms, so a real election fills only about a third of it. This simulation fills all 102 seats in one snapshot, because it is modeling what kind of senator each state’s 2024 electorate would choose, not reconstructing the class-by-class calendar. Only one race is modelled per state — two contests six years apart cannot be simulated separately — so a state gives both seats to its winner unless its top two parties finish within 12 points across resamples, in which case it sends one of each. That cutoff is a judgement, though not a free one: sorted, the gaps between first and second cluster below 11 points and then jump, so the split set holds anywhere in the empty space rather than turning on the exact line.',
  },
  {
    label: 'House districts are idealized',
    lede: 'Urban, suburban and rural tiers from census geography. No gerrymandering.',
    bias: 'design', tag: 'Scope choice',
    body: 'Districts are assigned urban/suburban/rural tiers based on census geography. Actual multi-member STV districts would be drawn differently, and gerrymandering is not modeled.',
  },
  {
    label: 'Population vs. voters',
    lede: 'The typology is built on the weighted population; the elections run on validated 2024 turnout, sweepable under Turnout.',
    bias: 'design', tag: 'Scope choice',
    body: 'The party typology is built on the full weighted survey population (latent preference). Real electorates are shaped by uneven turnout, so the office simulations default to observed 2024 validated turnout and let you sweep the contraction effect (see the Turnout section). CES also skews somewhat more educated and engaged than the adult population, which the survey weights only partly correct.',
  },
];

// Per-state CES sample sizes, from the clustering input file. Four cases that break the
// sample-size story: the top row is the largest of the four, so the bars are read against it.
const SAMPLE_CASES = [
  { state: 'Michigan', n: 1531, rank: '8th-largest sample', conf: 0.43 },
  { state: 'North Carolina', n: 1444, rank: '10th-largest', conf: 0.35 },
  { state: 'Indiana', n: 978, rank: 'above median', conf: 0.34 },
  { state: 'Wyoming', n: 70, rank: 'smallest sample', conf: 0.52 },
];
const SAMPLE_MAX = Math.max(...SAMPLE_CASES.map(c => c.n));

export function CaveatsSection() {
  const u = uncertaintyAt(DEFAULT_STOP_INDEX);

  const senate = useMemo(() => {
    if (!u) return null;
    return {
      cond: racesOf(u.senate.cond.states),
      irv: racesOf(u.senate.irv.states),
      condDisagree: Object.entries(u.senate.cond.states)
        .filter(([, s]) => s.modal !== partyOf(s.observed))
        .map(([f]) => FIPS_TO_ABBR[f] ?? f).sort(),
      irvDisagree: Object.entries(u.senate.irv.states)
        .filter(([, s]) => s.modal !== partyOf(s.observed))
        .map(([f]) => FIPS_TO_ABBR[f] ?? f).sort(),
    };
  }, [u]);

  const house = useMemo(() => {
    const rows = Object.entries(u?.house.seats ?? {})
      .map(([party, iv]) => ({ party, iv, rel: (iv.hi - iv.lo) / 2 / iv.expected }))
      .sort((a, b) => b.iv.expected - a.iv.expected);
    const bands = [...rows].sort((a, b) => b.rel - a.rel);
    return rows.length < 2 ? null : {
      bands,
      widest: bands[0],
      tightest: bands[bands.length - 1],
      first: rows[0],
      second: rows[1],
      pluralityGap: rows[0].iv.lo - rows[1].iv.hi,
    };
  }, [u]);

  const wy = u?.senate.irv.states['56']?.decomp;
  const nDraws = u?.nDraws ?? 1000;
  const nElections = nDraws * UNCERTAINTY_STOPS.length;

  return (
    <div className="space-y-4">
      {/* Claim */}
      <Card className="bg-slate-900 text-white border-slate-700 px-6 py-7">
        <div className="text-xs font-mono text-slate-400 uppercase tracking-widest mb-3">What this is not</div>
        <p className="text-xl font-semibold leading-snug mb-3">
          This is a simulation, not a prediction.
        </p>
        <p className="text-slate-300 text-sm leading-relaxed">
          It measures what electoral rules do to a real distribution of American opinion. Party
          formation, candidate emergence, strategic voting and campaign dynamics are all outside the
          model. Nothing here forecasts 2028.
        </p>
      </Card>

      {/* Scope */}
      <Card className="p-5">
        <div className="grid sm:grid-cols-2 gap-x-6 gap-y-4">
          <div>
            <div className="text-xs font-semibold text-emerald-700 uppercase tracking-widest mb-2">Answers</div>
            <ul className="space-y-1.5">
              {SCOPE.can.map(l => (
                <li key={l} className="flex gap-2 text-sm text-foreground/90 leading-snug">
                  <span className="text-emerald-600 shrink-0">✓</span>{l}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <div className="text-xs font-semibold text-red-700 uppercase tracking-widest mb-2">Cannot answer</div>
            <ul className="space-y-1.5">
              {SCOPE.cannot.map(l => (
                <li key={l} className="flex gap-2 text-sm text-muted-foreground leading-snug">
                  <span className="text-red-400 shrink-0">✗</span>{l}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Card>

      {/* Robustness */}
      <Card className="p-5 bg-emerald-50 border-emerald-200">
        <div className="font-semibold text-emerald-900 mb-1">The parties survive robustness checks</div>
        <p className="text-sm text-emerald-800 leading-relaxed mb-3">
          Three parts of the recipe were re-run against alternatives. The core parties reappear every time.
        </p>
        <div className="grid sm:grid-cols-3 gap-2 mb-3">
          {ROBUSTNESS.map(r => (
            <div key={r.label} className="rounded-lg bg-white/70 border border-emerald-200 px-3 py-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-900">
                <span className="text-emerald-600">✓</span>{r.label}
              </div>
              <p className="text-2xs text-emerald-800/90 leading-snug mt-0.5">{r.body}</p>
            </div>
          ))}
        </div>
        <p className="text-sm text-emerald-800 leading-relaxed">
          Parties are stable ideological types, but which
          individual voter lands in which is a statistical estimate.{' '}
          <a
            href="https://github.com/braydeck/USMultiPartySystem/blob/main/docs/EFA_ITEM_SELECTION_ROBUSTNESS.md"
            target="_blank" rel="noopener noreferrer"
            className="underline hover:text-emerald-900"
          >
            Full checks on GitHub ↗
          </a>
        </p>
      </Card>

      {/* Sampling precision */}
      {senate && (
        <Card className="p-5">
          <div className="font-semibold text-foreground mb-1">
            Resampling moves the small delegations and the close races, but relative size is steady.
          </div>
          <p className={`${BODY_PROSE} mb-4`}>
            Each state&apos;s respondents are resampled {nDraws.toLocaleString()} times, with replacement
            and within state, and every chamber re-runs on every draw at all seven participation stops.
            Headlines report the most likely result across those draws. Figures here describe the
            app&apos;s default {DEFAULT_GAP_STOP}% stop.
          </p>

          <div className="grid grid-cols-3 gap-3 mb-5">
            {[
              { n: nDraws.toLocaleString(), l: 'resamples per stop' },
              { n: UNCERTAINTY_STOPS.length, l: 'participation stops' },
              { n: nElections.toLocaleString(), l: 'elections counted' },
            ].map(s => (
              <div key={s.l} className="rounded-lg bg-muted/50 border border-border p-3 text-center">
                <div className="text-xl font-bold tabular-nums text-foreground">{s.n}</div>
                <div className="text-2xs text-muted-foreground leading-snug mt-0.5">{s.l}</div>
              </div>
            ))}
          </div>

          {house && (
            <>
              <div className="text-sm font-semibold text-foreground mb-1">
                The House barely moves. 873 seats average out the noise
              </div>
              <p className={`${BODY_PROSE} mb-3`}>
                Every delegation lands inside a band a few seats wide. {partyName(house.first.party)}&apos;s
                floor across resamples sits {house.pluralityGap} seats above{' '}
                {partyName(house.second.party)}&apos;s ceiling. Each seat is one of hundreds of district counts, and the draws that cost a
                party a seat in one district often hand it one in another.
              </p>
              <div className="mb-2">
                <SeatRangeStrip seats={u!.house.seats} order={[...F5_ORDER]} label="Seats across resamples" />
              </div>
              <div className="mb-5"><RangeKey /></div>

              <div className="text-sm font-semibold text-foreground mb-1">
                Sampling puts smaller delegations relative size at risk 
              </div>
              <p className={`${BODY_PROSE} mb-3`}>
                The same few-seat band is a rounding error against{' '}
                {partyName(house.tightest.party)}&apos;s {Math.round(house.tightest.iv.expected)} seats and
                close to a third of {partyName(house.widest.party)}&apos;s{' '}
                {Math.round(house.widest.iv.expected)}. Read the large delegations as counts and the small
                ones as ranges.
              </p>
              <div className="mb-5">
                <BandWidths rows={house.bands} max={house.widest.rel} />
              </div>
            </>
          )}

          <div className="text-sm font-semibold text-foreground mb-1">
            A senate seat is one winner, so nothing averages out
          </div>
          <p className={`${BODY_PROSE} mb-3`}>
            Each cell is one of the 51 state races, sorted by how often its winner repeats. The two methods are
            equally reliable on average but differently shaped. Condorcet is more decisive where it is
            decisive and closer to a coin flip where it is not. IRV&apos;s answer rides on an elimination order that reshuffles every
            round, but keeps extremes from winning in most races.
          </p>
          <div className="space-y-4 mb-5">
            <ConfidenceStrip name="Condorcet" races={senate.cond} />
            <ConfidenceStrip name="IRV" races={senate.irv} />
          </div>

          <div className="text-sm font-semibold text-foreground mb-1">Sample size has small effects on shakiness</div>
          <p className={`${BODY_PROSE} mb-3`}>
            Log sample size correlates with confidence in the winner at just +0.30 under Condorcet and
            +0.34 under IRV. The median sample across the 13 least stable Condorcet races is 385
            respondents against 661 across all 51, so size does some work, and some of the least stable
            races carry some of the largest samples in the file.
          </p>
          <div className="rounded-lg border border-border divide-y divide-border/60 mb-5">
            {SAMPLE_CASES.map(c => (
              <div key={c.state} className="grid grid-cols-[7.5rem_1fr_1fr] items-center gap-3 px-3 py-2">
                <div>
                  <div className="text-sm font-medium text-foreground leading-tight">{c.state}</div>
                  <div className="text-3xs text-muted-foreground">{c.rank}</div>
                </div>
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-1.5 flex-1 rounded-full bg-muted overflow-hidden">
                    <span className="block h-full rounded-full bg-slate-400" style={{ width: `${(c.n / SAMPLE_MAX) * 100}%` }} />
                  </span>
                  <span className="text-2xs tabular-nums text-muted-foreground w-10 text-right">{c.n.toLocaleString()}</span>
                </span>
                <Bar v={c.conf} color="#6366f1" w="w-full" />
              </div>
            ))}
            <div className={`grid grid-cols-[7.5rem_1fr_1fr] gap-3 px-3 py-1.5 ${TABLE_HEADER}`}>
              <span />
              <span>CES respondents</span>
              <span>Winner repeats</span>
            </div>
          </div>

          {wy && (
            <>
              <div className="text-sm font-semibold text-foreground mb-1">
                A race can be unstable without either party being weak
              </div>
              <p className={`${BODY_PROSE} mb-3`}>
                Wyoming under IRV. Conservative and Populist win almost the same share of the draws in
                which they reach the final round. What separates them is getting there, and Populist won
                the observed sample by surviving that far.
              </p>
              <div className="rounded-lg border border-border p-3 mb-5">
                {[
                  { k: 'final' as const, l: 'Reaches the final round' },
                  { k: 'winIfFinal' as const, l: 'Wins once it gets there' },
                  { k: 'win' as const, l: 'Wins the seat' },
                ].map(row => (
                  <div key={row.k} className="grid grid-cols-[9.5rem_1fr_1fr] items-center gap-3 py-1">
                    <span className="text-xs text-muted-foreground leading-snug">{row.l}</span>
                    {['CON', 'POP'].map(p => (
                      <span key={p} className="inline-flex items-center gap-2">
                        <span className="text-2xs font-semibold w-16 shrink-0" style={{ color: partyColor(p) }}>
                          {PARTY_NAMES[p]}
                        </span>
                        <Bar v={wy[p]?.[row.k] ?? 0} color={partyColor(p)} w="flex-1" />
                      </span>
                    ))}
                  </div>
                ))}
              </div>
            </>
          )}

          {u && (
            <>
              <div className="text-sm font-semibold text-foreground mb-1">
                IRV&apos;s presidency is settled. Condorcet&apos;s is close to a coin flip
              </div>
              <p className={`${BODY_PROSE} mb-3`}>
                Share of the {nDraws.toLocaleString()} draws each party wins the presidency. No draw of
                the {nElections.toLocaleString()} produced a Condorcet cycle, so every one resolved to a winner.
              </p>
              <div className="space-y-2 mb-4">
                {([['IRV', u.president.irv.dist], ['Condorcet', u.president.cond.dist]] as const).map(([label, dist]) => (
                  <div key={label} className="flex items-center gap-3">
                    <span className="text-2xs font-semibold text-muted-foreground w-16 shrink-0">{label}</span>
                    <div className="flex-1"><WinnerBar dist={dist} /></div>
                  </div>
                ))}
              </div>
            </>
          )}

          <details className="border-t border-border/60 pt-3">
            <summary className="text-2xs font-semibold text-muted-foreground hover:text-foreground cursor-pointer select-none">
              How to read the intervals, and where the observed sample disagrees
            </summary>
            <div className="space-y-2 mt-2.5 text-2xs text-muted-foreground leading-relaxed">
              <p>
                These are <strong className="text-foreground">bootstrap percentile intervals</strong>, not
                credible intervals. An election outcome is a complex, discontinuous function of the
                underlying data, so resampling is the right tool for it. Per-party ranges do not sum to the
                chamber size, because two parties cannot both land at their maximum; the most likely and
                expected chambers both do sum correctly.
              </p>
              <p>
                The House bootstrap resolves to chamber totals, not to per-district winners, so there is
                no district-level counterpart to the senate&apos;s reproduction rates. A delegation&apos;s
                band is the net of hundreds of districts moving in both directions, and which particular
                districts moved is not recoverable from it.
              </p>
              <p>
                This captures <em>sampling</em> uncertainty only. Candidate fields are held fixed, because
                the senate&apos;s per-state candidate pool comes from a committed 52-row state profile that
                cannot be resampled, so the true uncertainty is wider than shown and the senate ranges
                carry no uncertainty at all about who runs.
              </p>
              <p>
                Where the observed sample names a different winner than the likely one, the vote-flow chart
                for that state shows an <strong className="text-foreground">example count</strong> that
                produces the likely winner instead, chosen to be typical of those draws; its individual
                percentages illustrate one path rather than measuring that state.{' '}
                {senate.irvDisagree.length} states are substituted this way under IRV
                ({senate.irvDisagree.join(', ')}). {senate.condDisagree.length} disagree under Condorcet
                ({senate.condDisagree.join(', ')}), where there are no elimination rounds to substitute, so
                the head-to-head view names the likely winner in a note and leaves the observed
                sample&apos;s own margins on screen. Hatching on the map marks something broader and not
                the same set: any race whose winner changes in more than half of resamples.
              </p>
              <p>
                The pattern above holds at the other participation stops; the particular states change.
              </p>
            </div>
          </details>
        </Card>
      )}

      {/* Assumptions */}
      <Card className="overflow-hidden">
        <div className="px-5 py-4 border-b border-border/50 bg-muted">
          <div className="font-semibold text-foreground">
            {ASSUMPTIONS.length} assumptions, and which way each one bends the result
          </div>
          <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-2xs text-muted-foreground">
            <span className="inline-flex items-center gap-1.5"><span className="text-amber-600">▲▼</span>Known direction of bias</span>
            <span className="inline-flex items-center gap-1.5"><span className="text-slate-400">◆●</span>Scope or modeling choice, no direction</span>
          </div>
        </div>
        <div className="divide-y divide-border/60">
          {ASSUMPTIONS.map(a => {
            const s = BIAS_STYLE[a.bias];
            return (
              <div key={a.label} className="px-5 py-3.5">
                <div className="flex flex-wrap items-baseline gap-x-2.5 gap-y-1 mb-1">
                  <span className="font-medium text-foreground text-sm">{a.label}</span>
                  <span className={`inline-flex items-center gap-1 text-3xs font-semibold px-1.5 py-0.5 rounded border ${s.chip}`}>
                    <span aria-hidden="true">{s.dot}</span>{a.tag}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground leading-snug">{a.lede}</p>
                <details className="mt-1">
                  <summary className="text-2xs font-medium text-muted-foreground/80 hover:text-foreground cursor-pointer select-none">
                    Detail
                  </summary>
                  <p className={`${CARD_HINT} leading-relaxed mt-1.5`}>
                    {a.body}
                    {a.source && (
                      <>
                        {' '}
                        <a href={a.source.href} target="_blank" rel="noopener noreferrer"
                          className="underline hover:text-foreground">
                          {a.source.label}
                        </a>
                      </>
                    )}
                  </p>
                </details>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Data & Methods */}
      <Card className="p-5 bg-muted">
        <div className={`${MINOR_HEADING} mb-2`}>Data &amp; Methods</div>
        <div className="space-y-1 text-xs text-muted-foreground">
          <div><span className="font-medium text-muted-foreground">Survey:</span> Cooperative Election Study (CES) 2024, Harvard/YouGov</div>
          <div><span className="font-medium text-muted-foreground">Factor analysis:</span> Polychoric EFA, 24 items → 5 factors, oblique (oblimin) rotation</div>
          <div><span className="font-medium text-muted-foreground">Clustering:</span> Dirichlet Process Gaussian Mixture Model (DPGMM), 10 clusters</div>
          <div><span className="font-medium text-muted-foreground">Ballot scoring:</span> GMM cluster posterior{SHOW_CROSSOVER && ' (Party-Line); + Gaussian proximity σ=0.35, equal factor weights (Crossover variants)'}</div>
          <div><span className="font-medium text-muted-foreground">Legislation model:</span> Normal approximation of chamber Bernoulli vote counts</div>
        </div>
      </Card>
    </div>
  );
}
