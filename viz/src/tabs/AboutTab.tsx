import { useUrlState } from '../hooks/useUrlState';
import { Card } from '@/components/ui/card';
import { PARTY_COLORS, PARTY_NAMES, F5_ORDER, PARTY_TAGLINES, etaPurple } from '../constants/parties';
import { popShare } from '../lib/population';
import { SHOW_CROSSOVER } from '../constants/features';
import factorLoadingsData from '../data/factorLoadings.json';

interface FactorDef {
  short: string; label: string; color: string; eta: number; bw: number;
  strength: string; hi: string; lo: string; note?: string; factor: string;
  items: { loading: number; question: string }[];
}
// Generated from analysis/efa/efa_loadings_k5_final.csv + clusterProfiles (make_factor_reference.py).
const FACTORS = factorLoadingsData as FactorDef[];

const SINGLE_SEAT_SYSTEMS = [
  {
    name: 'FPTP',
    full: 'First Past the Post',
    used: "Today's system (comparison baseline)",
    color: '#64748b',
    how: 'Whoever wins the most votes in a single-member district takes the seat outright, even without a majority. Every other vote in that district elects no one.',
    why: 'The baseline every chamber in this app compares against. Produces the two-party equilibrium and the disproportionality shown throughout.',
  },
  {
    name: 'Condorcet',
    full: 'Condorcet Method',
    used: 'Presidential General · Senate',
    color: '#a16207',
    how: 'Every candidate faces every other in a head-to-head matchup. The candidate who beats everyone else wins. If no one does, a tiebreak applies.',
    why: 'Finds the candidate most preferred by the electorate overall. Often selects a centrist who may not win IRV, revealing tension between the two methods.',
  },
  {
    name: 'IRV',
    full: 'Instant-Runoff Voting',
    used: 'Presidential General · Senate',
    color: '#16a34a',
    how: 'Voters rank candidates. The last-place candidate is eliminated each round and their votes redistribute. Continues until someone clears 50%.',
    why: 'Eliminates spoiler effects. The winner has majority support after preferences are accounted for, often different from first-choice plurality.',
  },
];

const PROPORTIONAL_SYSTEMS = [
  {
    name: 'STV',
    full: 'Single Transferable Vote',
    used: 'Presidential Primary · House',
    color: '#1d4ed8',
    how: 'Voters rank candidates. Once a candidate passes the Droop quota (the vote share needed to lock a seat), their surplus votes transfer to next choices. Losers also transfer. Continues until seats are filled.',
    why: 'Produces proportional outcomes in multi-seat races. Penalizes parties that run too many candidates (vote-splitting). Rewards coalition-building.',
  },
  {
    name: 'Party List',
    full: 'Open Party List',
    used: 'House alternative view',
    color: '#0369a1',
    how: "Candidate votes are pooled by party within each multi-member district. Seats go to parties by quota (Hare quota with largest remainders here), then filled by each party's top vote-getters.",
    why: "Delivers proportional seat shares directly from vote share, without STV's ranked transfers. Shown alongside STV as a second proportional method for the House.",
  },
];

const SCENARIOS = [
  {
    name: 'Party-Line',
    tag: '28 candidates',
    color: '#1d4ed8',
    desc: 'The nine larger parties each field 3 intra-party candidates with a 40/35/25 first-choice split; the small Order & Opportunity party fields 1, for 28 in all. Same-party candidates share identical ideological positions, so only prominence (name recognition) separates them.',
    insight: 'Isolates the structural effect of proportional voting itself. Same-party candidates compete on prominence, not ideology.',
    candidates: 'LBR_1, LBR_2, LBR_3 · CON_1, CON_2, CON_3 · … · OAO_1',
  },
  {
    name: 'Crossover',
    tag: '38 candidates',
    color: '#ea580c',
    desc: '10 base candidates (one per party) + 28 crossover variants. Each variant shifts one ideological axis by ±25% of the inter-party standard deviation, producing candidates like LBR_hi_so (a Labor candidate who runs tougher on security) or CON_lo_pc (a Conservative who softens on populism).',
    insight: 'Models intra-party ideological diversity. Voters can express a preference not just for a party, but for a faction within it.',
    candidates: 'LBR · LBR_hi_so · LBR_lo_so · LBR_hi_id · …',
  },
];

const STEPS = [
  {
    n: 1, color: '#1d4ed8',
    title: 'Cooperative Election Study (CES 2024)',
    body: '~60,000 respondents across the US answer ~100 policy questions covering taxes, immigration, healthcare, climate, guns, abortion, civil liberties, and more. This is one of the largest and most rigorous political surveys in American social science.',
  },
  {
    n: 2, color: '#7c3aed',
    title: 'Exploratory Factor Analysis (EFA)',
    body: 'A core set of 24 policy items is reduced to 5 underlying ideological dimensions using polychoric EFA (oblimin rotation). These factors capture the latent structure of American opinion: not what people say they believe, but the correlated belief clusters that actually organize political space.',
  },
  {
    n: 3, color: '#16a34a',
    title: 'Voter Typology: 10 Clusters',
    body: 'A Dirichlet Process Gaussian Mixture Model (DPGMM, a clustering method that discovers how many groups the data supports rather than being told in advance) groups respondents into 10 voter types by their 5 factor scores. Each cluster becomes a party, including cluster 7 (Order & Opportunity), a cross-cutting law-and-order + economic-progressive bloc that sits diagonally to the usual left-right axis.',
  },
  {
    n: 4, color: '#ea580c',
    title: 'Ballot Generation',
    body: SHOW_CROSSOVER
      ? 'Each voter gets a ranked preference list. Party-Line ballots rank parties by the voter\'s cluster-membership probability (the same GMM posterior that defined the typology). Crossover ballots start from that and use factor-space proximity to place the shifted variant candidates. Within-party ordering follows candidate prominence.'
      : 'Each voter gets a ranked preference list, ordered by the voter\'s cluster-membership probability — the same GMM posterior that defined the typology. Within-party ordering follows candidate prominence.',
  },
  {
    n: 5, color: '#a16207',
    title: 'Elections',
    body: 'Ballots run through STV (House/Primary), IRV and Condorcet (Senate/Presidential). Results show which parties win seats, which candidates emerge as finalists, and whether the two electoral methods agree on a winner.',
  },
];

type Section = 'overview' | 'data' | 'parties' | 'voting' | 'scenarios' | 'turnout' | 'caveats';
// 'Two Scenarios' is entirely a Party-Line-vs-Crossover comparison, so it goes with the flag.
const SECTIONS = ([
  { id: 'overview',  label: 'Overview'        },
  { id: 'data',      label: 'Methodology'     },
  { id: 'parties',   label: 'The 10 Parties'  },
  { id: 'voting',    label: 'Voting Systems'  },
  { id: 'scenarios', label: 'Two Scenarios'   },
  { id: 'turnout',   label: 'Turnout'         },
  { id: 'caveats',   label: 'Caveats'         },
] as { id: Section; label: string }[]).filter(s => SHOW_CROSSOVER || s.id !== 'scenarios');
const SECTION_IDS = SECTIONS.map(s => s.id);

export function AboutTab() {
  const [active, setActive] = useUrlState<Section>('about', 'overview', { allowed: SECTION_IDS });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-1">What Is This?</h2>
        <p className="text-muted-foreground text-sm">
          A data-driven simulation of American elections under proportional representation, built from 60,000 real survey responses.
        </p>
      </div>

      {/* Nav pills */}
      <div className="flex flex-wrap gap-2">
        {SECTIONS.map(s => (
          <button
            key={s.id}
            onClick={() => setActive(s.id)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              active === s.id
                ? 'bg-slate-900 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* ── Overview ─────────────────────────────────────────── */}
      {active === 'overview' && (
        <div className="space-y-5">
          {/* Hero callout */}
          <Card className="bg-slate-900 text-white border-slate-700 px-6 py-8">
            <div className="text-xs font-mono text-muted-foreground uppercase tracking-widest mb-3">The premise</div>
            <p className="text-xl font-semibold leading-snug mb-4">
              What if Americans voted in a 10-party proportional system in 2028, using their actual political beliefs?
            </p>
            <p className="text-slate-300 text-sm leading-relaxed">
              Winner-take-all voting compresses a multi-dimensional electorate into two parties. Feed the same
              voters into a proportional system and the hidden structure reappears: cross-cutting, often
              surprising coalitions. The claim is simple. The two-party split is an artifact of the rules, not the country.
            </p>
          </Card>

          {/* Three pillars */}
          <div className="grid sm:grid-cols-3 gap-4">
            {[
              { accent: '#1d4ed8', icon: '◎', title: '2024 Pre-Election Survey Data', body: 'Drawn from the 2024 Cooperative Election Study: 60,000 respondents, ~100 policy questions. Real voters, real preferences.' },
              { accent: '#16a34a', icon: '◈', title: '"Parties" derived from clusters', body: 'Each party is a statistically distinct voter cluster from factor analysis of the survey. Read it as an electoral force that would shape a multiparty system, not a firm prediction of the parties that would form.' },
              { accent: '#ea580c', icon: '◆', title: 'Proportional and Preferential Voting', body: 'Elections run via STV, IRV, and Condorcet: systems designed to produce the greatest good for the greatest number. STV already runs in Ireland, Australia, Cambridge, and Portland.' },
            ].map(p => (
              <Card key={p.title} className="p-5">
                <div className="text-2xl mb-2" style={{ color: p.accent }}>{p.icon}</div>
                <div className="font-semibold text-foreground mb-1.5">{p.title}</div>
                <p className="text-sm text-muted-foreground leading-relaxed">{p.body}</p>
              </Card>
            ))}
          </div>

          {/* Quick stats */}
          <Card className="p-5">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-4">By the numbers</div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
              {[
                { n: '~60,000', label: 'Survey respondents' },
                { n: '10',      label: 'Active parties' },
                { n: '873',     label: 'House seats' },
                { n: '102',     label: 'Senate seats' },
              ].map(s => (
                <div key={s.label}>
                  <div className="text-2xl font-bold text-foreground">{s.n}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">{s.label}</div>
                </div>
              ))}
            </div>
          </Card>

          {/* Tab guide */}
          <Card className="p-5">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-4">What each tab shows</div>
            <div className="space-y-2.5">
              {[
                { tab: 'Party Quiz', desc: 'Answer the actual CES survey questions and see which of the ten parties your factor scores land closest to.', group: '' },
                { tab: 'Overview', desc: 'A proportional government at a glance: how each chamber\'s composition shifts from winner-take-all to STV, a population-vs-voters breakdown, and a turnout-robustness check across the whole model.', group: '' },
                { tab: 'Parties', desc: `The ten parties as an ideological constellation and individual profiles, plus a policy-by-policy comparison across up to 4 parties${SHOW_CROSSOVER ? ' or crossover candidates' : ''}.`, group: '' },
                { tab: 'Presidency', desc: 'A 4-round STV primary that consolidates a 9+ party field into finalists, then a head-to-head general where IRV and Condorcet often pick different winners.', group: 'Scenarios' },
                { tab: 'Senate',   desc: 'Per-state elections for 102 seats (two per state + DC). Condorcet tends to favor centrists; IRV often produces more polarized chambers.', group: 'Scenarios' },
                { tab: 'House',    desc: 'Multi-seat STV across 873 seats, tiered by urban/suburban/rural district type, with a representation-gap analysis.', group: 'Scenarios' },
                { tab: 'Legislation', desc: 'Given the simulated chambers, which bills pass? A Normal approximation of chamber vote counts produces passage probabilities.', group: 'Scenarios' },
                { tab: 'IRV Case Studies', desc: 'Alaska and Maine, the only states using ranked-choice voting for federal elections, comparing IRV with the Condorcet winner and a multi-seat STV what-if.', group: 'Scenarios' },
              ].map((r, i, arr) => (
                <div key={r.tab}>
                  {r.group && arr[i - 1]?.group !== r.group && (
                    <div className="text-[10px] font-semibold text-muted-foreground/70 uppercase tracking-widest mt-3 mb-1.5">Under the {r.group} menu</div>
                  )}
                  <div className="flex gap-3 text-sm">
                    <span className="font-semibold text-foreground w-44 shrink-0">{r.tab}</span>
                    <span className="text-muted-foreground leading-snug">{r.desc}</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* ── Methodology ──────────────────────────────────────── */}
      {active === 'data' && (
        <div className="space-y-5">
          <Card className="overflow-hidden">
            <div className="px-5 py-4 border-b border-border/50 bg-muted">
              <div className="font-semibold text-foreground">From Survey Responses to Election Results</div>
              <p className="text-xs text-muted-foreground mt-0.5">A five-step pipeline, each grounded in published methods</p>
            </div>
            <div className="divide-y divide-slate-100">
              {STEPS.map((step, i) => (
                <div key={i} className="flex gap-4 px-5 py-5">
                  <div
                    className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0 mt-0.5"
                    style={{ backgroundColor: step.color }}
                  >
                    {step.n}
                  </div>
                  <div>
                    <div className="font-semibold text-foreground text-sm mb-1">{step.title}</div>
                    <p className="text-sm text-muted-foreground leading-relaxed">{step.body}</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Factor detail */}
          <Card className="overflow-hidden">
            <div className="px-5 py-4 border-b border-border/50 bg-muted">
              <div className="font-semibold text-foreground">The 5 Ideological Dimensions</div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Latent factors that emerge from how survey responses correlate, ordered by how strongly each one sorts people into parties (η²). Expand a factor to see the survey items that define it and how heavily each one weighs (its loading).
              </p>
            </div>
            <div className="divide-y divide-slate-100">
              {FACTORS.map(f => {
                const etaPct = Math.round(f.eta * 100);
                return (
                  <div key={f.short} className="flex items-start gap-4 px-5 py-4">
                    <div
                      className="text-xs font-bold font-mono px-2 py-1 rounded shrink-0 mt-0.5"
                      style={{ backgroundColor: f.color + '18', color: f.color }}
                    >
                      {f.short}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <div className="font-semibold text-foreground text-sm">{f.label}</div>
                        <div className="text-[11px] text-muted-foreground font-mono shrink-0">η² = {f.eta.toFixed(2)}</div>
                      </div>
                      <div className="h-1.5 bg-muted rounded-full overflow-hidden mb-2" title={`η² = ${f.eta.toFixed(3)} (B/W ${f.bw})`}>
                        <div className="h-full rounded-full" style={{ width: `${etaPct}%`, backgroundColor: etaPurple(f.eta) }} />
                      </div>
                      <p className="text-xs text-muted-foreground mb-2">{f.strength}</p>
                      <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-muted-foreground mb-2">
                        <span><span className="font-medium text-muted-foreground">High:</span> {f.hi}</span>
                        <span><span className="font-medium text-muted-foreground">Low:</span> {f.lo}</span>
                      </div>
                      <details className="mt-1">
                        <summary className="text-xs font-medium cursor-pointer text-muted-foreground hover:text-foreground select-none">
                          {f.items.length} survey items that define it
                        </summary>
                        {f.note && <p className="text-[11px] text-muted-foreground mt-2 italic leading-relaxed">{f.note}</p>}
                        <ul className="mt-2 space-y-1">
                          {f.items.map((it, i) => (
                            <li key={i} className="flex items-start gap-2 text-xs">
                              <span
                                className="font-mono shrink-0 w-11 text-right tabular-nums"
                                style={{ color: it.loading >= 0 ? '#16a34a' : '#dc2626' }}
                              >
                                {it.loading >= 0 ? '+' : ''}{it.loading.toFixed(2)}
                              </span>
                              <span className="text-foreground leading-snug">{it.question}</span>
                            </li>
                          ))}
                        </ul>
                      </details>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

          {/* What the factors reveal */}
          <Card className="p-5 bg-slate-50 border-slate-200">
            <div className="font-semibold text-foreground mb-1">What the factors reveal</div>
            <p className="text-sm text-muted-foreground leading-relaxed">
              The cleavages people assume are missing turn out not to be separate axes. Support for climate policy and for the culture-war issues both track left-right almost perfectly: neither pulls voters off the main spectrum. The dimension that genuinely cuts across the parties is institutional trust: in elections and in government (the Institutional Distrust factor). That is why the cross-pressured parties (Solidarity, Order &amp; Opportunity, Civic Union) exist rather than collapsing onto the usual left-right line.
            </p>
          </Card>

          {/* Ballot generation detail */}
          <Card className="p-5">
            <div className="font-semibold text-foreground mb-1">How a voter becomes a ranked ballot</div>
            <p className="text-sm text-muted-foreground leading-relaxed mb-4">
              Proximity does the ranking. Every voter sits in the same five-factor space as the candidates, and the
              ballot orders those candidates from nearest to farthest. Nothing is hand-assigned.
            </p>

            <div className="grid sm:grid-cols-3 gap-3 mb-4">
              {[
                { n: '1', h: 'Place the voter', b: 'Five factor scores fix each respondent in ideological space.' },
                { n: '2', h: 'Rank by nearness', b: 'A Gaussian kernel (σ 0.35) scores every candidate; closer ranks higher. Cross-party affinities shape the lower ranks.' },
                { n: '3', h: 'Break ties by name', b: 'Identical same-party candidates split 40 / 35 / 25 (Plackett-Luce), so the top name never sweeps.' },
              ].map(s => (
                <div key={s.n} className="bg-muted rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-600 text-white text-[11px] font-bold">{s.n}</span>
                    <span className="text-xs font-semibold text-foreground uppercase tracking-widest">{s.h}</span>
                  </div>
                  <p className="text-[13px] text-muted-foreground leading-relaxed">{s.b}</p>
                </div>
              ))}
            </div>

            {/* Worked example: one voter's ballot as ranked party pills, with the depth cutoff */}
            <div className="rounded-lg border border-border p-4 mb-4">
              <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-2.5">Example: one ballot, nearest candidate first</div>
              <div className="flex flex-wrap items-center gap-1.5">
                {['STY', 'LBR', 'LIB', 'PRG', 'DSA', 'CUP', 'OAO'].map((c, idx) => (
                  <span key={c} className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold text-white" style={{ background: PARTY_COLORS[c] }}>
                    <span className="opacity-70">{idx + 1}</span>{PARTY_NAMES[c]}
                  </span>
                ))}
                <span className="mx-1 text-[11px] font-medium text-indigo-600">│ stops here at 7</span>
                {['CON', 'POP', 'NAT'].map(c => (
                  <span key={c} className="inline-flex items-center rounded-full border border-dashed border-border px-2 py-0.5 text-[11px] text-muted-foreground line-through">
                    {PARTY_NAMES[c]}
                  </span>
                ))}
              </div>
              <p className="text-[11px] text-muted-foreground mt-2.5">
                Ballots run seven deep by default. Past the cutoff the ballot exhausts and stops transferring, which is why seven is the default.
              </p>
            </div>

            <div className={`grid gap-3 ${SHOW_CROSSOVER ? 'sm:grid-cols-2' : ''}`}>
              <div className="bg-muted rounded-lg p-3">
                <div className="text-xs font-semibold text-foreground mb-1">
                  {SHOW_CROSSOVER ? 'Party-line field' : 'How ballots are ordered'}
                </div>
                <p className="text-[12px] text-muted-foreground leading-relaxed">Ranks parties by each voter's cluster-membership probability, the DPGMM posterior that defined the typology.</p>
              </div>
              {SHOW_CROSSOVER && (
                <div className="bg-muted rounded-lg p-3">
                  <div className="text-xs font-semibold text-foreground mb-1">Crossover field</div>
                  <p className="text-[12px] text-muted-foreground leading-relaxed">Adds the shifted variant candidates, each placed by factor-space proximity.</p>
                </div>
              )}
            </div>
          </Card>

          {/* Why the default asks for seven ranks */}
          <Card className="p-5">
            <div className="font-semibold text-foreground mb-2">Why ballots ask for at least seven</div>
            <p className="text-sm text-muted-foreground leading-relaxed mb-3">
              Short ballots break proportional representation. When all of a voter&apos;s ranked choices are
              eliminated, the ballot exhausts and stops transferring, so late seats fill below the quota that is
              supposed to earn them. Ballot length is the fix, and the returns diminish fast. Share of House seats
              filled below quota, by how many candidates voters rank (double-Wyoming, 5% turnout):
            </p>
            <div className="grid grid-cols-5 gap-2 text-center mb-3">
              {([['3', '34%'], ['5', '18%'], ['7', '13%'], ['10', '9%'], ['All', '8%']] as const).map(([r, v]) => (
                <div key={r} className={`rounded-lg border p-2 ${r === '7' ? 'border-indigo-300 bg-indigo-50' : 'border-border bg-muted/40'}`}>
                  <div className="text-[11px] text-muted-foreground">Rank {r}</div>
                  <div className="text-lg font-bold tabular-nums text-foreground">{v}</div>
                </div>
              ))}
            </div>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Seven captures most of the gain toward the full-ranking floor without asking voters to rank a whole
              field. It also matches the standard rule that a voter should rank at least as many candidates as the
              district has seats: the largest districts here elect seven.
            </p>
          </Card>
        </div>
      )}

      {/* ── The 10 Parties ───────────────────────────────────── */}
      {active === 'parties' && (
        <div className="space-y-5">
          <Card className="p-5">
            <p className="text-sm text-foreground leading-relaxed mb-3">
              Each &ldquo;party&rdquo; is a statistically distinct cluster of the surveyed electorate, named after the
              fact from its ideological profile. The spectrum is five-dimensional; the cards below run along the
              primary axis (F5, Populist Conservatism, low to high), and the figure on each card is that
              cluster&apos;s share of the adult population.
            </p>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Party formation is complex, so treat these less as firm predictions of what parties would form and
              more as <strong>10 electoral forces</strong> that would shape a multiparty system. They show how, even
              inside a two-party system, voter preferences are diverse and cross-cutting, and they are the clusters
              that emerge from the specific battery of CES items used here.
            </p>
          </Card>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {F5_ORDER.map((code) => {
              const color = PARTY_COLORS[code];
              const name  = PARTY_NAMES[code] ?? code;
              const tag   = PARTY_TAGLINES[code] ?? '';
              return (
                <Card
                  key={code}
                  className="overflow-hidden"
                  style={{ borderColor: color + '44', borderLeftColor: color, borderLeftWidth: 4 }}
                >
                  <div className="px-4 py-3">
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div>
                        <span
                          className="text-xs font-bold font-mono px-2 py-0.5 rounded"
                          style={{ backgroundColor: color + '18', color }}
                        >
                          {code}
                        </span>
                        <div className="font-semibold text-foreground text-sm mt-1">{name}</div>
                      </div>
                      <span className="text-xs font-semibold font-mono shrink-0 tabular-nums" style={{ color }} title="share of the adult population">{Math.round(popShare(code))}%</span>
                    </div>
                    <p className="text-xs text-muted-foreground leading-snug">{tag}</p>
                  </div>
                </Card>
              );
            })}
          </div>

        </div>
      )}

      {/* ── Voting Systems ───────────────────────────────────── */}
      {active === 'voting' && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground leading-relaxed">
            <span className="font-medium text-foreground">Five counting methods, and why the choice matters.</span> The
            same ballots (or the same district votes) can elect different winners, or different seat splits, depending
            on the counting rule, and that disagreement is itself a finding.
          </p>

          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest pt-1">Single-Seat Systems</h4>
          {SINGLE_SEAT_SYSTEMS.map(vs => (
            <Card key={vs.name} className="overflow-hidden">
              <div
                className="px-5 py-4 border-b"
                style={{ backgroundColor: vs.color + '10', borderBottomColor: vs.color + '30' }}
              >
                <div className="flex items-center gap-3">
                  <span
                    className="text-sm font-bold font-mono px-2.5 py-1 rounded"
                    style={{ backgroundColor: vs.color + '20', color: vs.color }}
                  >
                    {vs.name}
                  </span>
                  <div>
                    <div className="font-semibold text-foreground">{vs.full}</div>
                    <div className="text-xs text-muted-foreground">Used in: {vs.used}</div>
                  </div>
                </div>
              </div>
              <div className="px-5 py-4 grid sm:grid-cols-2 gap-4">
                <div>
                  <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1.5">How it works</div>
                  <p className="text-sm text-muted-foreground leading-relaxed">{vs.how}</p>
                </div>
                <div>
                  <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1.5">Why it matters here</div>
                  <p className="text-sm text-muted-foreground leading-relaxed">{vs.why}</p>
                </div>
              </div>
            </Card>
          ))}

          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest pt-3">Proportional Systems</h4>
          {PROPORTIONAL_SYSTEMS.map(vs => (
            <Card key={vs.name} className="overflow-hidden">
              <div
                className="px-5 py-4 border-b"
                style={{ backgroundColor: vs.color + '10', borderBottomColor: vs.color + '30' }}
              >
                <div className="flex items-center gap-3">
                  <span
                    className="text-sm font-bold font-mono px-2.5 py-1 rounded"
                    style={{ backgroundColor: vs.color + '20', color: vs.color }}
                  >
                    {vs.name}
                  </span>
                  <div>
                    <div className="font-semibold text-foreground">{vs.full}</div>
                    <div className="text-xs text-muted-foreground">Used in: {vs.used}</div>
                  </div>
                </div>
              </div>
              <div className="px-5 py-4 grid sm:grid-cols-2 gap-4">
                <div>
                  <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1.5">How it works</div>
                  <p className="text-sm text-muted-foreground leading-relaxed">{vs.how}</p>
                </div>
                <div>
                  <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1.5">Why it matters here</div>
                  <p className="text-sm text-muted-foreground leading-relaxed">{vs.why}</p>
                </div>
              </div>
            </Card>
          ))}

          {/* IRV vs Condorcet explainer */}
          <Card className="p-5">
            <div className="font-semibold text-foreground mb-3">IRV vs Condorcet: Why Both?</div>
            <p className="text-sm text-muted-foreground leading-relaxed mb-4">
              IRV and Condorcet frequently disagree on a winner, and the gap between them is politically revealing. IRV can elect a candidate with strong first-choice support who loses head-to-head. Condorcet finds the candidate most preferred <em>overall</em>, often a centrist. Showing both exposes the method-dependence of "winning."
            </p>
            <div className="grid sm:grid-cols-2 gap-3">
              <Card className="p-3 bg-green-50 border-green-200">
                <div className="text-xs font-semibold text-green-800 mb-1">IRV tends to elect...</div>
                <p className="text-xs text-green-700">Candidates with strong first-choice bases, often from larger parties. Can miss broadly acceptable centrists if they lack top-of-ballot support.</p>
              </Card>
              <Card className="p-3 bg-amber-50 border-amber-200">
                <div className="text-xs font-semibold text-amber-800 mb-1">Condorcet tends to elect...</div>
                <p className="text-xs text-amber-700">The "least-bad" option: the candidate who beats everyone else one-on-one. Often a centrist who nobody loves but most can live with.</p>
              </Card>
            </div>
          </Card>
        </div>
      )}

      {/* ── Two Scenarios ────────────────────────────────────── */}
      {active === 'scenarios' && (
        <div className="space-y-5">
          <p className="text-sm text-muted-foreground leading-relaxed">
            <span className="font-medium text-foreground">Two candidate fields, run on the same electorate.</span> Party-Line
            isolates the pure effect of proportional voting; Crossover adds intra-party factions. Comparing them shows how
            much ideological variety <em>within</em> parties changes who wins.
          </p>
          <div className="grid sm:grid-cols-2 gap-4">
            {SCENARIOS.map(s => (
              <Card
                key={s.name}
                className="border-2 overflow-hidden"
                style={{ borderColor: s.color + '55' }}
              >
                <div className="px-5 py-4 border-b" style={{ borderColor: s.color + '33', backgroundColor: s.color + '0c' }}>
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className="text-xs font-bold px-2 py-0.5 rounded font-mono"
                      style={{ backgroundColor: s.color + '22', color: s.color }}
                    >
                      {s.tag}
                    </span>
                  </div>
                  <div className="font-bold text-foreground text-lg">{s.name}</div>
                </div>
                <div className="px-5 py-4 space-y-3">
                  <p className="text-sm text-muted-foreground leading-relaxed">{s.desc}</p>
                  <div className="bg-muted rounded-lg p-3">
                    <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1">What it isolates</div>
                    <p className="text-xs text-muted-foreground">{s.insight}</p>
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1">Example candidates</div>
                    <code className="text-xs text-muted-foreground font-mono">{s.candidates}</code>
                  </div>
                </div>
              </Card>
            ))}
          </div>

          <Card className="p-5">
            <div className="font-semibold text-foreground mb-3">What comparing them reveals</div>
            <div className="space-y-3 text-sm">
              {[
                { q: 'Do intra-party factions matter?', a: 'If Crossover and Party-Line produce very different senate compositions, ideological variance within parties is electorally significant. If results converge, party label dominates.' },
                { q: 'Which parties benefit from crossover candidates?', a: 'Some parties gain seats by splitting their ideological space; crossover variants attract voters who\'d otherwise vote adjacent. Others lose seats to vote-splitting.' },
                { q: 'Does the presidential winner change?', a: 'Often yes. The Crossover field\'s STY_hi_so and the Party-Line field\'s LBR_1 are different candidacies: one is a security-minded Solidarity candidate, the other the Labor baseline.' },
              ].map(r => (
                <div key={r.q} className="flex gap-3">
                  <div className="text-muted-foreground shrink-0 mt-0.5">→</div>
                  <div>
                    <span className="font-medium text-foreground">{r.q} </span>
                    <span className="text-muted-foreground">{r.a}</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* ── Turnout ──────────────────────────────────────────── */}
      {active === 'turnout' && (
        <div className="space-y-5">
          <Card className="bg-slate-900 text-white border-slate-700 px-6 py-7">
            <div className="text-xs font-mono text-muted-foreground uppercase tracking-widest mb-3">The turnout slider</div>
            <p className="text-lg font-semibold leading-snug mb-3">
              Elections aren&apos;t decided by the population. They&apos;re decided by whoever shows up. The
              &ldquo;turnout gap closed&rdquo; slider lets you test how much that matters.
            </p>
            <p className="text-slate-300 text-sm leading-relaxed">
              Turnout is deeply uneven, and it doesn&apos;t fall evenly across the forces. The app opens at 5% of that
              gap closed, a small mobilization of suppressed voters; the slider sweeps the rest, from observed 2024
              turnout toward a more equal electorate, so you can see which results depend on it.
            </p>
          </Card>

          <Card className="p-5">
            <div className="font-semibold text-foreground mb-2">The turnout inversion</div>
            <p className="text-sm text-muted-foreground leading-relaxed mb-3">
              Validated 2024 turnout runs <em>backwards</em> to force size. The high-intensity ideological poles
              vote most (Progressive at 81%, Nationalist at 74%) while the large, cross-pressured center votes
              least: Solidarity at just 33%. Winner-take-all converts that intensity gap directly into power. The
              engaged extremes are over-represented and the disengaged center is under-represented, before a single
              seat is even allocated.
            </p>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Because a force&apos;s share of voters equals its population share times its turnout relative to the
              average, low turnout only costs you if you&apos;re <em>below</em> average: being small doesn&apos;t hurt
              you, being disengaged does. See the Population Breakdown on the Overview for the visual.
            </p>
          </Card>

          <Card className="p-5">
            <div className="font-semibold text-foreground mb-2">What the slider models: the contraction effect</div>
            <p className="text-sm text-muted-foreground leading-relaxed mb-3">
              It is <em>not</em> a uniform turnout boost. The documented effect of proportional representation
              (Cox, Fiva &amp; Smith on Norway&apos;s 1919 reform) is a <strong>contraction</strong>: mobilization
              redistributes from the over-mobilized to the under-mobilized, compressing the turnout <em>gap</em>
              between forces rather than lifting everyone. That is exactly what the slider does: at &ldquo;X% gap
              closed,&rdquo; the suppressed forces close X% of their turnout gap toward the mobilized ones (each
              pairwise gap shrinks by X%). We model this as upward-only, lifting the suppressed while holding the
              high-turnout poles fixed, which is deliberately conservative for the extremist-containment question,
              since it never deflates the poles.
            </p>
            <div className="grid sm:grid-cols-3 gap-3 mt-3">
              <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                <div className="text-xs font-semibold text-emerald-800 mb-1">0% · Observed</div>
                <p className="text-[11px] text-emerald-700 leading-relaxed">Validated 2024 turnout, no assumed behavioral response. The only setting that rests entirely on measured data.</p>
              </div>
              <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                <div className="text-xs font-semibold text-emerald-800 mb-1">≤15% · Plausible</div>
                <p className="text-[11px] text-emerald-700 leading-relaxed">The quasi-experimental PR turnout effect is small (1–4 points aggregate, often null), so ~15% gap closure is the ceiling of what one cycle plausibly delivers.</p>
              </div>
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                <div className="text-xs font-semibold text-amber-800 mb-1">20–30% · Stress</div>
                <p className="text-[11px] text-amber-700 leading-relaxed">Beyond documented one-cycle effects; included to test what heavier mobilization would take. Above 30% is excluded entirely.</p>
              </div>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed mt-4">
              The app opens at <strong>5% gap closed</strong>, one notch off the pure-observed floor. A proportional
              system gives currently-suppressed voters someone to vote for, so the opening view credits a small
              mobilization rather than assuming none. Five percent sits at the conservative low end of the plausible
              band, well under the ceiling the quasi-experimental evidence supports. Every result is still checkable at
              0%, and the findings that matter hold at both.
            </p>
          </Card>

          <Card className="p-5">
            <div className="font-semibold text-foreground mb-3">How to read it: each claim against its hostile end</div>
            <div className="space-y-2.5 text-sm">
              {[
                { q: 'President: robust', a: 'Solidarity (Condorcet) and Labour (IRV) win at observed turnout and at every compression level. Nothing hinges on the assumption.' },
                { q: 'House: scales, doesn’t flip', a: 'Conservative stays the plurality throughout; Solidarity’s delegation grows monotonically as the gap closes. Weakest at 0%, so it’s quoted as a range, not a point.' },
                { q: 'Senate: conditional on mobilization', a: 'The one result observed data does not support: Labour leads at observed turnout, across the plausible band (≤15%), and through 20%; Solidarity only reaches the plurality at 25%, inside the stress band, beyond what one cycle plausibly delivers. So at observed turnout the Senate is Labour’s, and Solidarity’s Senate is contingent, reported that way.' },
              ].map(r => (
                <div key={r.q} className="flex gap-3">
                  <div className="text-muted-foreground shrink-0 mt-0.5">→</div>
                  <div><span className="font-medium text-foreground">{r.q}. </span><span className="text-muted-foreground">{r.a}</span></div>
                </div>
              ))}
            </div>
            <p className="text-[11px] text-muted-foreground leading-relaxed mt-4">
              Turnout is <strong>validated</strong> (matched to the TargetSmart voter file via CES <code>TS_g2024</code>),
              not self-reported, so the 32%-to-81% spread across forces is a measured gap, not survey over-reporting
              (which is small, roughly 3 points, once you compare matched respondents like with like). Two facts make
              this defensible. First, coding unmatched respondents as non-voters is the field standard, not our choice:
              Grimmer &amp; Hersh (2018) show it recovers actual state turnout far better than dropping them, and our
              weighted national validated turnout (59%) lands on the voting-age-population benchmark (~59%; the
              widely-cited 64% figure uses the narrower eligible-population denominator). Second, and decisively, the
              simulation only ever uses turnout <em>relative</em> to the average, because STV and Condorcet counting
              normalize ballot weight against the quota. So whether Solidarity&apos;s true turnout is the validated 32%
              or as high as 41% (its upper bound once you credit hard-to-match voters), its weight relative to other
              forces barely moves and its ordering never does. The one real uncertainty, that low-engagement forces are
              hardest to locate on the voter file and so their floor is slightly understated, is exactly what the
              compression slider sweeps upward.
            </p>
          </Card>
        </div>
      )}

      {/* ── Caveats ──────────────────────────────────────────── */}
      {active === 'caveats' && (
        <div className="space-y-4">
          <Card className="p-5 bg-amber-50 border-amber-200">
            <div className="font-semibold text-amber-900 mb-1">This is a simulation, not a prediction</div>
            <p className="text-sm text-amber-800 leading-relaxed">
              The goal is to understand structural properties of electoral systems applied to the actual distribution of American political opinion, not to forecast 2028. Party formation, candidate emergence, strategic voting, and campaign dynamics are all absent.
            </p>
          </Card>

          <Card className="p-5 bg-emerald-50 border-emerald-200">
            <div className="font-semibold text-emerald-900 mb-1">Stress-tested, not hand-picked</div>
            <p className="text-sm text-emerald-800 leading-relaxed">
              The item set, the five-factor count, and the rotation were each re-run against alternatives: a mechanical selection rule, four additional policy domains, and other factor counts. The core parties reappear every time. One limit worth naming plainly: the parties are stable ideological types, but which individual voter lands in which is a statistical estimate, not a fixed assignment. Full item-selection and robustness checks are in the{' '}
              <a href="https://github.com/braydeck/USMultiPartySystem/blob/main/docs/EFA_ITEM_SELECTION_ROBUSTNESS.md" target="_blank" rel="noopener noreferrer" className="underline hover:text-emerald-900">methodology on GitHub ↗</a>.
            </p>
          </Card>

          <Card className="p-5">
            <div className="font-semibold text-foreground mb-2">How precise are the seat counts?</div>
            <div className="space-y-3 text-sm text-muted-foreground leading-relaxed">
              <p>
                The card above names the limit: which individual voter lands in which party is a
                statistical estimate. This section is what that limit costs in seats. Each state&apos;s
                respondents are resampled 1,000 times, with replacement and within state so every state
                keeps its own sample size, and the whole election is re-run on every draw, at all seven
                participation stops. The headline is the{' '}
                <strong className="text-foreground">most likely</strong> winner across those draws; the
                whiskers and ranges show how far the result travels. The figures below describe the
                app&apos;s default 5% stop; the pattern holds at the others, the particular states change.
              </p>
              <p>
                Most results barely move, and the ones that do skew small: the median sample across the
                13 least stable Condorcet races is 385 respondents against 661 across all 51. But sample
                size explains only a small part of this. Log sample size correlates with confidence in the
                winner at only +0.30 under Condorcet and +0.34 under IRV, and some of the least stable
                Condorcet races are among the largest samples in the file. Michigan is the eighth-largest
                state sample of the 51 at 1,531 respondents and reproduces its most likely winner in 43%
                of draws; North Carolina is tenth-largest at 1,444 and 35%; Indiana, at 978, sits well
                above the median and reproduces its winner in 34%. The clearest case where the sample is
                the explanation is Wyoming, which has the smallest CES sample of any state at 70 respondents, and its spread
                of opinion is close to the national spread, so it is the sample doing the work. Under IRV
                its observed winner is the less likely one: Populist takes 29% of resamples and
                Conservative 52%.
              </p>
              <p>
                Wyoming also shows why a race can be unstable without either party being weak. Conservative
                and Populist win almost the same share of the draws in which they reach the final round,
                57% and 60%. What separates them is getting there. Conservative reaches the final round in
                92% of draws and Populist in 49%. Populist won the observed sample because it survived that
                far, which happens less than half the time.
              </p>
              <p>
                Where the observed sample names a different winner than the likely one, the vote-flow chart
                for that state shows an <strong className="text-foreground">example count</strong> that
                produces the likely winner instead, chosen to be typical of those draws. Its individual
                percentages illustrate one path rather than measuring that state. Four states are
                substituted this way under IRV. Five more disagree under Condorcet — Arkansas, Michigan,
                Nebraska, North Carolina and South Carolina — where there are no elimination rounds to
                substitute, so the head-to-head view names the likely winner in a note and leaves the
                observed sample&apos;s own margins on screen. The hatching on the map marks something
                broader and not the same set: any race whose winner changes in more than half of
                resamples.
              </p>
              <p>
                The two counting methods are equally reliable on average and differently shaped. Mean
                confidence in the winner is 71% under both. The distributions are not alike: Condorcet
                reproduces its winner in over 90% of draws in 19 of 51 races but falls below 50% in 13,
                while IRV clears 90% in only 8 races, drops below 50% in 6, and puts 21 races between 50%
                and 70%. Condorcet is more decisive where it is decisive and closer to a coin flip where it
                is not. That follows from what each rule asks. Condorcet asks whether one party beats every
                rival head to head, a question with either a robust answer or a fragile one, while IRV&apos;s
                answer rides on an elimination order that reshuffles support every round, which keeps most
                races off both extremes. Neither method is the more trustworthy one here; they concentrate
                their uncertainty in different places.
              </p>
              <p>
                The presidency shows the same contrast. IRV returns Labor in 100% of draws. Condorcet
                returns Solidarity in 62% and Labor in 38%, so the Condorcet presidency is close to a coin
                flip even though the observed sample names a single winner. No draw of the 7,000 produced a
                Condorcet cycle, so every one resolved to a winner.
              </p>
              <p className="text-[11px]">
                These are <strong className="text-foreground">bootstrap percentile intervals</strong>, not
                credible intervals. An election outcome is a complex, discontinuous function of the
                underlying data, so resampling is the right tool for it. Per-party ranges do not sum to the
                chamber size, because two parties cannot both land at their maximum; the most likely and
                expected chambers both do sum correctly. And this captures <em>sampling</em> uncertainty
                only. Candidate fields are held fixed, because the senate&apos;s per-state candidate pool
                comes from a committed 52-row state profile that cannot be resampled, so the true
                uncertainty is wider than shown and the senate ranges carry no uncertainty at all about who
                runs.
              </p>
            </div>
          </Card>

          <Card className="overflow-hidden">
            <div className="px-5 py-4 border-b border-border/50 bg-muted">
              <div className="font-semibold text-foreground">Key Assumptions</div>
            </div>
            <div className="divide-y divide-slate-100">
              {[
                {
                  label: 'Perfect party cohesion',
                  body: 'Senators and representatives vote with their party 100% of the time on the legislation model. Real legislatures have party discipline ranging from ~70% (US Democrats) to ~95% (UK Conservative Party). This overstates certainty in passage probabilities.',
                },
                {
                  label: 'Sincere voting',
                  body: 'Voters rank candidates by genuine ideological proximity. In real ranked-choice elections, strategic voting (burying strong competitors, propping up weak ones) is common. This simulation shows what sincere preferences would produce.',
                },
                {
                  label: 'Static ideological space',
                  body: 'The 5D factor space is fit to CES 2024 data and held fixed. In reality, the emergence of new parties would shift voter alignments, party platforms would evolve, and the factor structure itself might change.',
                },
                {
                  label: 'Prominence as name recognition',
                  body: 'The 40/35/25 within-party split is a modeling assumption, not empirical data. It prevents the top candidate from sweeping all same-party ballots, but the specific values are illustrative.',
                },
                {
                  label: 'Both Senate seats are filled at once',
                  body: 'The Senate has staggered six-year terms, so a real election fills only about a third of it. This simulation fills every seat in one snapshot, because it is modeling what kind of senator each state\'s 2024 electorate would choose rather than reconstructing the class-by-class calendar. One race is modelled per state, since two contests six years apart cannot be simulated separately: a state that returns the same party in most resamples fills both seats with it, and a state whose winner changes from sample to sample splits, sending one senator from each of its two closest parties. That is a modelling choice, not a result — the ten-point cutoff is a judgement about which states are genuinely contested.',
                },
                {
                  label: 'House districts are idealized',
                  body: 'Districts are assigned urban/suburban/rural tiers based on census geography. Actual multi-member STV districts would be drawn differently, and gerrymandering is not modeled.',
                },
                {
                  label: 'Population vs. voters',
                  body: 'The party typology is built on the full weighted survey population (latent preference). Real electorates are shaped by uneven turnout, so the office simulations default to observed 2024 validated turnout and let you sweep the contraction effect (see the Turnout section). CES also skews somewhat more educated and engaged than the adult population, which the survey weights only partly correct.',
                },
                {
                  label: 'Institutional distrust is a floor',
                  body: 'Clustering requires a complete answer on all 24 items, which restricts the sample to the ~45,700 respondents who returned for the post-election wave. That attrition is not random: the returners run about eleven years older and more politically engaged than the full 60,000, and the post-election weights correct the demographic margins but not the engagement gap. Institutional distrust is the factor most exposed, because it is built entirely from post-wave items (election fairness, trust in federal and state government), and among voters who did answer, the least engaged are the most distrustful. The alienated, low-information, "system is rigged" voter is the one least likely to have stayed to report it. Read the institutional-distrust scores as a floor: the simulation more likely understates distrust than overstates it, especially toward elections and state government.',
                },
              ].map(a => (
                <div key={a.label} className="px-5 py-4">
                  <div className="font-medium text-foreground text-sm mb-1">{a.label}</div>
                  <p className="text-sm text-muted-foreground leading-relaxed">{a.body}</p>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-5">
            <div className="font-semibold text-foreground mb-3">What this can and can't tell you</div>
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <div className="text-xs font-semibold text-green-700 uppercase tracking-widest mb-2">Can tell you</div>
                <ul className="space-y-1.5 text-xs text-muted-foreground">
                  {[
                    'Which ideological coalitions exist in the American electorate',
                    'How different voting methods produce different outcomes from the same ballots',
                    'Which policy positions have majority support across the full chamber',
                    'Where IRV and Condorcet disagree, and why',
                    'How intra-party factionalism affects seat allocation',
                  ].map(l => (
                    <li key={l} className="flex gap-2"><span className="text-green-500 shrink-0">✓</span>{l}</li>
                  ))}
                </ul>
              </div>
              <div>
                <div className="text-xs font-semibold text-red-700 uppercase tracking-widest mb-2">Cannot tell you</div>
                <ul className="space-y-1.5 text-xs text-muted-foreground">
                  {[
                    'Who would actually win in 2028',
                    'How strategic voting would change outcomes',
                    'How new parties would alter voter alignments over time',
                    'Whether these parties could build stable governing coalitions',
                    'How media, money, and endorsements would shape the race',
                  ].map(l => (
                    <li key={l} className="flex gap-2"><span className="text-red-400 shrink-0">✗</span>{l}</li>
                  ))}
                </ul>
              </div>
            </div>
          </Card>

          <Card className="p-5 bg-muted">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-2">Data & Methods</div>
            <div className="space-y-1 text-xs text-muted-foreground">
              <div><span className="font-medium text-muted-foreground">Survey:</span> Cooperative Election Study (CES) 2024, Harvard/YouGov</div>
              <div><span className="font-medium text-muted-foreground">Factor analysis:</span> Polychoric EFA, 24 items → 5 factors, oblique (oblimin) rotation</div>
              <div><span className="font-medium text-muted-foreground">Clustering:</span> Dirichlet Process Gaussian Mixture Model (DPGMM), 10 clusters</div>
              <div><span className="font-medium text-muted-foreground">Ballot scoring:</span> GMM cluster posterior{SHOW_CROSSOVER && ' (Party-Line); + Gaussian proximity σ=0.35, equal factor weights (Crossover variants)'}</div>
              <div><span className="font-medium text-muted-foreground">Legislation model:</span> Normal approximation of chamber Bernoulli vote counts</div>
            </div>
          </Card>
        </div>
      )}

    </div>
  );
}
