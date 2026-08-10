import { useUrlState } from '../hooks/useUrlState';
import { Card } from '@/components/ui/card';
import { PARTY_COLORS, PARTY_NAMES, F5_ORDER, PARTY_TAGLINES, etaPurple } from '../constants/parties';
import { popShare } from '../lib/population';
import { SHOW_CROSSOVER } from '../constants/features';
import factorLoadingsData from '../data/factorLoadings.json';
import { CaveatsSection } from '../components/about/CaveatsSection';
import { TurnoutRobustnessCard } from '../components/shared/TurnoutRobustnessCard';
import { TurnoutVerificationCard } from '../components/shared/TurnoutVerificationCard';
import { PAGE_TITLE, MINOR_HEADING, BODY_PROSE, CARD_HINT, FOOTNOTE, TABLE_HEADER } from '../constants/typography';

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
    desc: 'The nine larger parties each field a 3-candidate slate; the small Order & Opportunity party fields 1, for 28 in all. Same-party candidates share identical ideological positions and are ranked in a fixed slate order, so nothing but ballot position separates them.',
    insight: 'Isolates the structural effect of proportional voting itself. Same-party candidates differ only in slate position, not ideology.',
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
      ? 'Each voter gets a ranked preference list. Party-Line ballots rank parties by the voter\'s cluster-membership probability (the same GMM posterior that defined the typology). Crossover ballots start from that and use factor-space proximity to place the shifted variant candidates. Within a party, candidates take consecutive ranks in a fixed slate order.'
      : 'Each voter gets a ranked preference list, ordered by the voter\'s cluster-membership probability — the same GMM posterior that defined the typology. Within a party, candidates take consecutive ranks in a fixed slate order.',
  },
  {
    n: 5, color: '#a16207',
    title: 'Elections',
    body: 'Ballots run through STV (House/Primary), IRV and Condorcet (Senate/Presidential). Results show which parties win seats, which candidates emerge as finalists, and whether the two electoral methods agree on a winner.',
  },
];

// Illustrative slate sizes for the worked ballot: a district where three parties clear the
// 12% threshold and one clears 5%, so the rank-7 cutoff falls inside the third slate.
const EXAMPLE_SLATES = [
  { code: 'STY', n: 3 },
  { code: 'LBR', n: 3 },
  { code: 'LIB', n: 3 },
  { code: 'PRG', n: 2 },
] as const;

/** One ballot drawn as contiguous party blocks, with the ranking instruction's cutoff in place. */
function ExampleBallot({ slates, depth }: { slates: readonly { code: string; n: number }[]; depth: number }) {
  let rank = 0;
  return (
    <div className="flex flex-wrap items-stretch gap-2">
      {slates.map(({ code, n }) => {
        const color = PARTY_COLORS[code];
        const seats = Array.from({ length: n }, () => ++rank);
        return (
          <div
            key={code}
            className="inline-flex items-center gap-2 rounded-lg border px-2 py-1.5"
            style={{ borderColor: color + '55', backgroundColor: color + '0e' }}
          >
            <span className="text-2xs font-semibold" style={{ color }}>{PARTY_NAMES[code]}</span>
            <span className="flex items-center gap-1">
              {seats.map(r => (
                <span key={r} className="flex items-center gap-1">
                  {r <= depth ? (
                    <span
                      className="flex h-5 w-5 items-center justify-center rounded-full text-2xs font-bold text-white tabular-nums"
                      style={{ backgroundColor: color }}
                      title={`rank ${r}`}
                    >
                      {r}
                    </span>
                  ) : (
                    <span
                      className="flex h-5 w-5 items-center justify-center rounded-full border border-dashed border-border text-2xs text-muted-foreground tabular-nums"
                      title="unranked: past the instruction"
                    >
                      {r}
                    </span>
                  )}
                  {r === depth && (
                    <span className="mx-0.5 text-2xs font-medium text-indigo-600 whitespace-nowrap">│ rank {depth}</span>
                  )}
                </span>
              ))}
            </span>
          </div>
        );
      })}
    </div>
  );
}

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
        <h2 className={`${PAGE_TITLE} mb-1`}>What Is This?</h2>
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
                <p className={BODY_PROSE}>{p.body}</p>
              </Card>
            ))}
          </div>

          {/* Quick stats */}
          <Card className="p-5">
            <div className={`${MINOR_HEADING} mb-4`}>By the numbers</div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
              {[
                { n: '~60,000', label: 'Survey respondents' },
                { n: '10',      label: 'Active parties' },
                { n: '873',     label: 'House seats' },
                { n: '102',     label: 'Senate seats' },
              ].map(s => (
                <div key={s.label}>
                  <div className={PAGE_TITLE}>{s.n}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">{s.label}</div>
                </div>
              ))}
            </div>
          </Card>

          {/* Tab guide */}
          <Card className="p-5">
            <div className={`${MINOR_HEADING} mb-4`}>What each tab shows</div>
            <div className="space-y-2.5">
              {[
                { tab: 'Party Quiz', desc: 'Answer the actual CES survey questions and see which of the ten parties your factor scores land closest to.', group: '' },
                { tab: 'Overview', desc: 'A proportional government at a glance: how each chamber\'s composition shifts from winner-take-all to STV, a population-vs-voters breakdown, and a turnout-robustness check across the whole model.', group: '' },
                { tab: 'Parties', desc: `The ten parties as an ideological constellation and individual profiles, plus a policy-by-policy comparison across up to 4 parties${SHOW_CROSSOVER ? ' or crossover candidates' : ''}.`, group: '' },
                { tab: 'Presidency', desc: 'A 4-round STV primary that consolidates a 9+ party field into finalists, then a head-to-head general where IRV and Condorcet often pick different winners.', group: 'Scenarios' },
                { tab: 'Senate',   desc: 'Per-state elections filling 102 seats (two per state + DC). Condorcet tends to favor centrists; IRV often produces more polarized chambers.', group: 'Scenarios' },
                { tab: 'House',    desc: 'Multi-seat STV across 873 seats, tiered by urban/suburban/rural district type, with a representation-gap analysis.', group: 'Scenarios' },
                { tab: 'Legislation', desc: 'Given the simulated chambers, which bills pass? A Normal approximation of chamber vote counts produces passage probabilities.', group: 'Scenarios' },
                { tab: 'IRV Case Studies', desc: 'Alaska and Maine, the only states using ranked-choice voting for federal elections, comparing IRV with the Condorcet winner and a multi-seat STV what-if.', group: 'Scenarios' },
              ].map((r, i, arr) => (
                <div key={r.tab}>
                  {r.group && arr[i - 1]?.group !== r.group && (
                    <div className="text-3xs font-semibold text-muted-foreground/70 uppercase tracking-widest mt-3 mb-1.5">Under the {r.group} menu</div>
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
              <p className={`${CARD_HINT} mt-0.5`}>A five-step pipeline, each grounded in published methods</p>
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
                    <p className={BODY_PROSE}>{step.body}</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Factor detail */}
          <Card className="overflow-hidden">
            <div className="px-5 py-4 border-b border-border/50 bg-muted">
              <div className="font-semibold text-foreground">The 5 Ideological Dimensions</div>
              <p className={`${CARD_HINT} mt-0.5`}>
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
                        <div className="text-2xs text-muted-foreground font-mono shrink-0">η² = {f.eta.toFixed(2)}</div>
                      </div>
                      <div className="h-1.5 bg-muted rounded-full overflow-hidden mb-2" title={`η² = ${f.eta.toFixed(3)} (B/W ${f.bw})`}>
                        <div className="h-full rounded-full" style={{ width: `${etaPct}%`, backgroundColor: etaPurple(f.eta) }} />
                      </div>
                      <p className={`${CARD_HINT} mb-2`}>{f.strength}</p>
                      <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-muted-foreground mb-2">
                        <span><span className="font-medium text-muted-foreground">High:</span> {f.hi}</span>
                        <span><span className="font-medium text-muted-foreground">Low:</span> {f.lo}</span>
                      </div>
                      <details className="mt-1">
                        <summary className="text-xs font-medium cursor-pointer text-muted-foreground hover:text-foreground select-none">
                          {f.items.length} survey items that define it
                        </summary>
                        {f.note && <p className={`${FOOTNOTE} mt-2 italic leading-relaxed`}>{f.note}</p>}
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
            <p className={BODY_PROSE}>
              The cleavages people assume are missing turn out not to be separate axes. Support for climate policy and for the culture-war issues both track left-right almost perfectly: neither pulls voters off the main spectrum. The dimension that genuinely cuts across the parties is institutional trust: in elections and in government (the Institutional Distrust factor). That is why the cross-pressured parties (Solidarity, Order &amp; Opportunity, Civic Union) exist rather than collapsing onto the usual left-right line.
            </p>
          </Card>

          {/* Ballot generation detail */}
          <Card className="p-5">
            <div className="font-semibold text-foreground mb-1">How a voter becomes a ranked ballot</div>
            <p className={`${BODY_PROSE} mb-4`}>
              A voter ranks parties by how strongly the model thinks they belong to each one, and ranks a
              party&apos;s candidates as a slate. Nothing is hand-assigned.
            </p>

            <div className="grid sm:grid-cols-3 gap-3 mb-4">
              {[
                { n: '1', h: 'Score every party', b: 'The DPGMM gives each respondent a membership probability in all ten clusters. That posterior is the ranking key.' },
                { n: '2', h: 'Rank parties by it', b: 'Highest posterior first. Co-partisans share their party\'s score, so a party\'s candidates take consecutive ranks.' },
                { n: '3', h: 'Keep the slate in order', b: 'Inside a party block every voter lists the slate in the same order, so transfers exhaust the party before leaving it.' },
              ].map(s => (
                <div key={s.n} className="bg-muted rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-600 text-white text-2xs font-bold">{s.n}</span>
                    <span className="text-xs font-semibold text-foreground uppercase tracking-widest">{s.h}</span>
                  </div>
                  <p className={BODY_PROSE}>{s.b}</p>
                </div>
              ))}
            </div>

            {/* Worked example: a ballot as party blocks, with the depth cutoff landing mid-slate */}
            <div className="rounded-lg border border-border p-4 mb-4">
              <div className={`${MINOR_HEADING} mb-2.5`}>Example: one ballot as party blocks</div>
              <ExampleBallot slates={EXAMPLE_SLATES} depth={7} />
              <p className={`${CARD_HINT} mt-2.5`}>
                Seven ranks reach three parties, and the cutoff can land inside a slate. Past it the ballot
                exhausts and stops transferring.
              </p>
            </div>

            <div className="rounded-lg border border-border p-4 mb-4">
              <div className={`${MINOR_HEADING} mb-2.5`}>How many candidates a party runs</div>
              <div className="grid grid-cols-3 gap-2">
                {([['≥12%', 3], ['≥5%', 2], ['≥1%', 1]] as const).map(([share, n]) => (
                  <div key={share} className="rounded-lg bg-muted/50 border border-border p-3 text-center">
                    <div className="text-lg font-bold tabular-nums text-foreground">{share}</div>
                    <div className={`${FOOTNOTE} leading-snug`}>of the district →<br />{n} candidate{n > 1 ? 's' : ''}</div>
                  </div>
                ))}
              </div>
              <p className={`${CARD_HINT} mt-2.5`}>
                Slate size follows the party&apos;s local strength, so nominating badly is possible: too many
                candidates splits the vote, too few leaves surplus unharvested.
              </p>
            </div>

            <div className={`grid gap-3 ${SHOW_CROSSOVER ? 'sm:grid-cols-2' : ''}`}>
              <div className="bg-muted rounded-lg p-3">
                <div className="text-xs font-semibold text-foreground mb-1">
                  {SHOW_CROSSOVER ? 'Party-line field' : 'What sets the order'}
                </div>
                <p className={`${CARD_HINT} leading-relaxed`}>The DPGMM posterior that defined the typology sets the order between parties; a fixed slate order sets it within them.</p>
              </div>
              {SHOW_CROSSOVER && (
                <div className="bg-muted rounded-lg p-3">
                  <div className="text-xs font-semibold text-foreground mb-1">Crossover field</div>
                  <p className={`${CARD_HINT} leading-relaxed`}>Adds the shifted variant candidates, each placed by factor-space proximity.</p>
                </div>
              )}
            </div>
          </Card>

          {/* Why the default asks for seven ranks */}
          <Card className="p-5">
            <div className="font-semibold text-foreground mb-2">Ballot depth is an instruction, not a guess</div>
            <p className={`${BODY_PROSE} mb-3`}>
              How deep people rank is set by what the ballot tells them to do, so the depth control is a
              design choice rather than a behavioral unknown. It matters because short ballots break
              proportional representation: once all of a voter&apos;s choices are eliminated the ballot
              exhausts and stops transferring, so late seats fill below the quota that is supposed to earn
              them. Share of House seats filled below quota, by instructed depth (double-Wyoming, 5% turnout):
            </p>
            <div className="grid grid-cols-5 gap-2 text-center mb-3">
              {([['3', '34%'], ['5', '18%'], ['7', '13%'], ['10', '9%'], ['All', '8%']] as const).map(([r, v]) => (
                <div key={r} className={`rounded-lg border p-2 ${r === '7' ? 'border-indigo-300 bg-indigo-50' : 'border-border bg-muted/40'}`}>
                  <div className="text-2xs text-muted-foreground">Rank {r}</div>
                  <div className="text-lg font-bold tabular-nums text-foreground">{v}</div>
                </div>
              ))}
            </div>
            <p className={`${CARD_HINT} leading-relaxed mb-4`}>
              Seven captures most of the gain toward the full-ranking floor without asking voters to rank a whole
              field. It also matches the standard rule that a voter should rank at least as many candidates as the
              district has seats: the largest districts here elect seven.
            </p>

            <div className={`${MINOR_HEADING} mb-2.5`}>Voters follow the instruction, and a third go past it</div>
            <div className="grid sm:grid-cols-[8rem_1fr] gap-3 mb-2.5">
              <div className="rounded-lg bg-muted/50 border border-border p-3 text-center flex flex-col justify-center">
                <div className="text-2xl font-bold tabular-nums text-foreground">98.2%</div>
                <div className={`${FOOTNOTE} leading-snug`}>met the five-box minimum, 2024</div>
              </div>
              <div className="rounded-lg border border-border overflow-hidden">
                <div className={`grid grid-cols-3 gap-2 px-3 py-1.5 bg-muted/40 ${TABLE_HEADER}`}>
                  <span>Election</span><span className="text-right">Stopped at five</span><span className="text-right">Went past five</span>
                </div>
                {([['2012', '72%', '26%'], ['2016', '64%', '35%'], ['2020', '68.1%', '31%'], ['2024', '68.4%', '30%']] as const)
                  .map(([yr, exact, more]) => (
                    <div key={yr} className="grid grid-cols-3 gap-2 px-3 py-1 text-xs tabular-nums border-t border-border/50">
                      <span className="text-muted-foreground">{yr}</span>
                      <span className="text-right text-foreground">{exact}</span>
                      <span className="text-right text-foreground">{more}</span>
                    </div>
                  ))}
              </div>
            </div>
            <p className={`${CARD_HINT} leading-relaxed`}>
              Shares of formal voters in the Australian Capital Territory, the closest real comparison
              available: Hare-Clark fills 5-seat electorates there and the ballot says to number five boxes
              from 1 to 5, so both the counting rule and the instruction match a district in this model.
              Compliance is near-total, the overshoot is one-sided, and both hold across four elections, so
              truncating every simulated ballot at the instruction understates how deep a real electorate
              ranks. The below-quota figures above are therefore ceilings. Two things to hold against that:
              the ACT votes under compulsory turnout, so its compliance rate is an upper bound, and its
              last-parcel surplus rule reads fewer deep preferences than the Gregory fractional method used
              here, so depth should matter somewhat more in this model than in the ACT&apos;s own data.{' '}
              <a
                href="https://www.parliament.act.gov.au/__data/assets/pdf_file/0009/3052467/Ballot-paper-preference-analysis-impact-of-ballot-paper-instructions.pdf"
                target="_blank" rel="noopener noreferrer"
                className="underline hover:text-foreground"
              >
                Elections ACT, <em>Ballot paper instructions under Hare-Clark</em>, March 2026 ↗
              </a>
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
            <p className={`${CARD_HINT} leading-relaxed`}>
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
                    <p className={`${CARD_HINT} leading-snug`}>{tag}</p>
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
          <p className={BODY_PROSE}>
            <span className="font-medium text-foreground">Five counting methods, and why the choice matters.</span> The
            same ballots (or the same district votes) can elect different winners, or different seat splits, depending
            on the counting rule, and that disagreement is itself a finding.
          </p>

          <h5 className={`${MINOR_HEADING} pt-1`}>Single-Seat Systems</h5>
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
                  <div className={`${MINOR_HEADING} mb-1.5`}>How it works</div>
                  <p className={BODY_PROSE}>{vs.how}</p>
                </div>
                <div>
                  <div className={`${MINOR_HEADING} mb-1.5`}>Why it matters here</div>
                  <p className={BODY_PROSE}>{vs.why}</p>
                </div>
              </div>
            </Card>
          ))}

          <h5 className={`${MINOR_HEADING} pt-3`}>Proportional Systems</h5>
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
                  <div className={`${MINOR_HEADING} mb-1.5`}>How it works</div>
                  <p className={BODY_PROSE}>{vs.how}</p>
                </div>
                <div>
                  <div className={`${MINOR_HEADING} mb-1.5`}>Why it matters here</div>
                  <p className={BODY_PROSE}>{vs.why}</p>
                </div>
              </div>
            </Card>
          ))}

          {/* IRV vs Condorcet explainer */}
          <Card className="p-5">
            <div className="font-semibold text-foreground mb-3">IRV vs Condorcet: Why Both?</div>
            <p className={`${BODY_PROSE} mb-4`}>
              IRV and Condorcet frequently disagree on a winner. IRV can elect a candidate with strong first-choice support who loses head-to-head. Condorcet finds the candidate most preferred <em>overall</em>.
            </p>
            <div className="grid sm:grid-cols-2 gap-3">
              <Card className="p-3 bg-green-50 border-green-200">
                <div className="text-xs font-semibold text-green-800 mb-1">IRV tends to elect...</div>
                <p className="text-xs text-green-700">Candidates with strong first-choice bases, often from larger parties. Can miss broadly acceptable choices if they lack strong top-of-ballot support.</p>
              </Card>
              <Card className="p-3 bg-amber-50 border-amber-200">
                <div className="text-xs font-semibold text-amber-800 mb-1">Condorcet tends to elect...</div>
                <p className="text-xs text-amber-700">The most acceptable option, the candidate who beats everyone else one-on-one. This can lead to a compromise choice without strong top-of-ballot support.</p>
              </Card>
            </div>
          </Card>
        </div>
      )}

      {/* ── Two Scenarios ────────────────────────────────────── */}
      {active === 'scenarios' && (
        <div className="space-y-5">
          <p className={BODY_PROSE}>
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
                  <p className={BODY_PROSE}>{s.desc}</p>
                  <div className="bg-muted rounded-lg p-3">
                    <div className={`${MINOR_HEADING} mb-1`}>What it isolates</div>
                    <p className={CARD_HINT}>{s.insight}</p>
                  </div>
                  <div>
                    <div className={`${MINOR_HEADING} mb-1`}>Example candidates</div>
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
            <p className={`${BODY_PROSE} mb-3`}>
              Validated 2024 turnout runs <em>backwards</em> to force size. The high-intensity ideological poles
              vote most (Progressive at 81%, Nationalist at 74%) while the large, cross-pressured center votes
              least: Solidarity at just 33%. Winner-take-all converts that intensity gap directly into power. The
              engaged extremes are over-represented and the disengaged center is under-represented, before a single
              seat is even allocated.
            </p>
            <p className={BODY_PROSE}>
              Because a force&apos;s share of voters equals its population share times its turnout relative to the
              average, low turnout only costs you if you&apos;re <em>below</em> average: being small doesn&apos;t hurt
              you, being disengaged does. See the Population Breakdown on the Overview for the visual.
            </p>
          </Card>

          <Card className="p-5">
            <div className="font-semibold text-foreground mb-2">What the slider models: the contraction effect</div>
            <p className={`${BODY_PROSE} mb-3`}>
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
                <p className="text-2xs text-emerald-700 leading-relaxed">Validated 2024 turnout, no assumed behavioral response. The only setting that rests entirely on measured data.</p>
              </div>
              <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                <div className="text-xs font-semibold text-emerald-800 mb-1">≤15% · Plausible</div>
                <p className="text-2xs text-emerald-700 leading-relaxed">The quasi-experimental PR turnout effect is small (1–4 points aggregate, often null), so ~15% gap closure is the ceiling of what one cycle plausibly delivers.</p>
              </div>
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                <div className="text-xs font-semibold text-amber-800 mb-1">20–30% · Stress</div>
                <p className="text-2xs text-amber-700 leading-relaxed">Beyond documented one-cycle effects; included to test what heavier mobilization would take. Above 30% is excluded entirely.</p>
              </div>
            </div>
            <p className={`${BODY_PROSE} mt-4`}>
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
                { q: 'President: robust to turnout, sensitive to ballot depth', a: 'Labour wins the instant runoff in all 35 combinations of turnout and ballot depth — nothing there hinges on the turnout assumption. The Condorcet winner is Solidarity in 26 of the 35, and Labour in the other nine: every case where voters rank only three candidates, plus full and seven-deep ranking at observed turnout. Three preferences exhaust before they reach Solidarity, so its head-to-head win depends on voters ranking deeper than three.' },
                { q: 'House: scales, doesn’t flip', a: 'Conservative stays the plurality throughout; Solidarity’s delegation grows monotonically as the gap closes. Weakest at 0%, so it’s quoted as a range, not a point.' },
                { q: 'Senate: conditional on mobilization', a: 'The one result observed data does not support: Labour leads at observed turnout, across the plausible band (≤15%), and through 20%; Solidarity only reaches the plurality at 25%, inside the stress band, beyond what one cycle plausibly delivers. So at observed turnout the Senate is Labour’s, and Solidarity’s Senate is contingent, reported that way.' },
              ].map(r => (
                <div key={r.q} className="flex gap-3">
                  <div className="text-muted-foreground shrink-0 mt-0.5">→</div>
                  <div><span className="font-medium text-foreground">{r.q}. </span><span className="text-muted-foreground">{r.a}</span></div>
                </div>
              ))}
            </div>
            <p className={`${CARD_HINT} leading-relaxed mt-4`}>
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

          {/* Moved off the Overview: these are the evidence that the turnout treatment holds
              up, which belongs with the explanation of the slider rather than in a headline
              summary of the chambers. */}
          <TurnoutRobustnessCard />
          <TurnoutVerificationCard />
        </div>
      )}

      {/* ── Caveats ──────────────────────────────────────────── */}
      {active === 'caveats' && <CaveatsSection />}

    </div>
  );
}
