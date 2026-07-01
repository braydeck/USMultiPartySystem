import { useUrlState } from '../hooks/useUrlState';
import { Card } from '@/components/ui/card';
import { PARTY_COLORS, PARTY_NAMES, F5_ORDER, PARTY_TAGLINES, etaPurple } from '../constants/parties';
import factorLoadingsData from '../data/factorLoadings.json';

interface FactorDef {
  short: string; label: string; color: string; eta: number; bw: number;
  strength: string; hi: string; lo: string; note?: string; factor: string;
  items: { loading: number; question: string }[];
}
// Generated from analysis/efa/efa_loadings_k5_final.csv + clusterProfiles (make_factor_reference.py).
const FACTORS = factorLoadingsData as FactorDef[];

const VOTING_SYSTEMS = [
  {
    name: 'STV',
    full: 'Single Transferable Vote',
    used: 'Presidential Primary · House',
    color: '#1d4ed8',
    how: 'Voters rank candidates. Once a candidate passes the Droop quota, their surplus votes transfer to next choices. Losers also transfer. Continues until seats are filled.',
    why: 'Produces proportional outcomes in multi-seat races. Penalizes parties that run too many candidates (vote-splitting). Rewards coalition-building.',
  },
  {
    name: 'IRV',
    full: 'Instant-Runoff Voting',
    used: 'Presidential General · Senate',
    color: '#16a34a',
    how: 'Voters rank candidates. The last-place candidate is eliminated each round and their votes redistribute. Continues until someone clears 50%.',
    why: 'Eliminates spoiler effects. The winner has majority support after preferences are accounted for, often different from first-choice plurality.',
  },
  {
    name: 'Condorcet',
    full: 'Condorcet Method',
    used: 'Presidential General · Senate',
    color: '#a16207',
    how: 'Every candidate faces every other in a head-to-head matchup. The candidate who beats everyone else wins. If no one does, a tiebreak applies.',
    why: 'Finds the candidate most preferred by the electorate overall. Often selects a centrist who may not win IRV, revealing tension between the two methods.',
  },
];

const SCENARIOS = [
  {
    name: 'Party-Line',
    tag: '27 candidates',
    color: '#1d4ed8',
    desc: 'Each of the 9 parties fields exactly 3 intra-party candidates with a 40/35/25 first-choice split. All three share identical ideological positions; only prominence (name recognition) differs.',
    insight: 'Isolates the structural effect of proportional voting itself. Same-party candidates compete on prominence, not ideology.',
    candidates: 'LBR_1, LBR_2, LBR_3 · CON_1, CON_2, CON_3 · ...',
  },
  {
    name: 'Crossover',
    tag: '37 candidates',
    color: '#ea580c',
    desc: '9 base candidates + 28 crossover variants. Each variant shifts one ideological axis by ±25% of the inter-party standard deviation, producing candidates like LBR_hi_so (a Labor candidate who runs tougher on security) or CON_lo_pc (a Conservative who softens on populism).',
    insight: 'Models intra-party ideological diversity. Voters can express a preference not just for a party, but for a faction within it.',
    candidates: 'LBR · LBR_hi_so · LBR_lo_so · LBR_hi_es · ...',
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
    body: 'Policy responses are reduced to 5 underlying ideological dimensions using polychoric EFA. These factors capture the latent structure of American opinion: not what people say they believe, but the correlated belief clusters that actually organize political space.',
  },
  {
    n: 3, color: '#16a34a',
    title: 'Voter Typology: 10 Clusters',
    body: 'A Dirichlet Process Gaussian Mixture Model (DPGMM) groups respondents into 10 voter types based on their 5 factor scores. Each cluster becomes a party. Blue Dogs (C7) are excluded: too small, and ideologically absorbed by adjacent clusters.',
  },
  {
    n: 4, color: '#ea580c',
    title: 'Ballot Generation',
    body: 'Each voter\'s factor scores are compared to each candidate\'s position in the same 5D space. Proximity (via Gaussian kernel, σ=0.35, η²-weighted) produces a ranked preference list. Within-party ordering follows candidate prominence.',
  },
  {
    n: 5, color: '#a16207',
    title: 'Elections',
    body: 'Ballots run through STV (House/Primary), IRV and Condorcet (Senate/Presidential). Results show which parties win seats, which candidates emerge as finalists, and whether the two electoral methods agree on a winner.',
  },
];

type Section = 'overview' | 'data' | 'parties' | 'voting' | 'scenarios' | 'caveats';
const SECTIONS: { id: Section; label: string }[] = [
  { id: 'overview',  label: 'Overview'       },
  { id: 'data',      label: 'Methodology'    },
  { id: 'parties',   label: 'The 9 Parties'  },
  { id: 'voting',    label: 'Voting Systems' },
  { id: 'scenarios', label: 'Two Scenarios'  },
  { id: 'caveats',   label: 'Caveats'        },
];

export function AboutTab() {
  const [active, setActive] = useUrlState<Section>('about', 'overview', { allowed: ['overview', 'data', 'parties', 'voting', 'scenarios', 'caveats'] });

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
              What if Americans voted in a 9-party proportional system in 2028, using their actual political beliefs?
            </p>
            <p className="text-slate-300 text-sm leading-relaxed">
              The US runs winner-take-all elections that compress a complex, multi-dimensional electorate into two parties. This simulation shows what parties could emerge from a proportional distribution of American opinion. This is the empirical core of a larger argument, that our two-party split is an artifact of the voting rules, not the country itself. Emerging parties are ideologically cross-cutting and often surprising.
            </p>
          </Card>

          {/* Three pillars */}
          <div className="grid sm:grid-cols-3 gap-4">
            {[
              { accent: '#1d4ed8', icon: '◎', title: '2024 Pre-Election Survey Data', body: 'Drawn from the 2024 Cooperative Election Study: 60,000 respondents, ~100 policy questions. Real voters, real preferences.' },
              { accent: '#16a34a', icon: '◈', title: '"Party" System derived from clusters', body: 'Parties aren\'t invented. They emerge from factor analysis and clustering of the survey data, each one a statistically distinct voter type.' },
              { accent: '#ea580c', icon: '◆', title: 'Proportional and Preferential Voting', body: 'Elections run via STV, IRV, and Condorcet: systems designed to produce the greatest good for the greatest number. STV already runs in Ireland, Australia, Cambridge, and Portland.' },
            ].map(p => (
              <Card key={p.title} className="p-5">
                <div className="text-2xl mb-2" style={{ color: p.accent }}>{p.icon}</div>
                <div className="font-semibold text-foreground mb-1.5">{p.title}</div>
                <p className="text-xs text-muted-foreground leading-relaxed">{p.body}</p>
              </Card>
            ))}
          </div>

          {/* Quick stats */}
          <Card className="p-5">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-4">By the numbers</div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
              {[
                { n: '~60,000', label: 'Survey respondents' },
                { n: '9',       label: 'Active parties' },
                { n: '873',     label: 'House seats' },
                { n: '51',      label: 'Senate seats' },
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
                { tab: 'Party Quiz', desc: 'Answer the actual CES survey questions and see which of the nine parties your factor scores land closest to.', group: '' },
                { tab: 'Overview', desc: 'A proportional government at a glance: how each chamber\'s composition shifts moving from winner-take-all to STV.', group: '' },
                { tab: 'Parties', desc: 'The nine parties as an ideological constellation and individual profiles, plus a policy-by-policy comparison across up to 4 parties or crossover candidates.', group: '' },
                { tab: 'Presidency', desc: 'A 4-round STV primary that consolidates a 9+ party field into finalists, then a head-to-head general where IRV and Condorcet often pick different winners.', group: 'Scenarios' },
                { tab: 'Senate',   desc: 'Per-state elections for 51 seats (one per state + DC). Condorcet tends to favor centrists; IRV often produces more polarized chambers.', group: 'Scenarios' },
                { tab: 'House',    desc: 'Multi-seat STV across 873 seats, tiered by urban/suburban/rural district type, with a representation-gap analysis.', group: 'Scenarios' },
                { tab: 'Legislation', desc: 'Given the simulated chambers, which bills pass? A Normal approximation of chamber vote counts produces passage probabilities.', group: 'Scenarios' },
                { tab: 'IRV Case Studies', desc: 'Alaska and Maine—the only states using ranked-choice voting for federal elections—comparing IRV with the Condorcet winner and a multi-seat STV what-if.', group: 'Scenarios' },
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
                    <p className="text-xs text-muted-foreground leading-relaxed">{step.body}</p>
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

          {/* Ballot generation detail */}
          <Card className="p-5">
            <div className="font-semibold text-foreground mb-3">How Ballots Are Generated</div>
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="bg-muted rounded-lg p-4">
                <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-2">Positional scoring (Gaussian proximity)</div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Each voter's 5D factor score vector is compared to each candidate's position. Similarity decays exponentially with distance (σ = 0.35, η²-weighted per factor). At this sigma, voters are effectively matched to their ideologically nearest party, but cross-party affinities still influence rank ordering.
                </p>
              </div>
              <div className="bg-muted rounded-lg p-4">
                <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-2">Within-party ordering</div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  For same-party candidates at identical positions, prominence (a proxy for name recognition: 40/35/25%) breaks ties via Plackett-Luce sampling. This ensures the top candidate doesn't sweep all same-party votes, modeling a realistic primary-like distribution.
                </p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ── The 9 Parties ────────────────────────────────────── */}
      {active === 'parties' && (
        <div className="space-y-5">
          <Card className="p-5">
            <p className="text-sm text-muted-foreground leading-relaxed mb-1">
              Each party is a statistically distinct cluster of ~60,000 CES respondents. They aren't named by researchers; the names are assigned afterward, from each cluster's ideological profile. The political spectrum here is five-dimensional, ordered below along the primary axis (F5 Populist Conservatism, low → high).
            </p>
          </Card>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {F5_ORDER.map((code, i) => {
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
                      <span className="text-xs text-muted-foreground font-mono shrink-0">#{i + 1}</span>
                    </div>
                    <p className="text-xs text-muted-foreground leading-snug">{tag}</p>
                  </div>
                </Card>
              );
            })}
          </div>

          <Card className="p-4 bg-amber-50 border-amber-200">
            <div className="text-xs font-semibold text-amber-800 mb-1">Why 9 and not 10?</div>
            <p className="text-xs text-amber-700 leading-relaxed">
              The DPGMM naturally produces 10 clusters. Cluster 7 (Blue Dogs, conservative Democrats) is dropped because it's small and ideologically spans the CON/CUP boundary. Including it produced unstable results and unclear ideological identity. All 9 remaining clusters are statistically robust and ideologically interpretable.
            </p>
          </Card>
        </div>
      )}

      {/* ── Voting Systems ───────────────────────────────────── */}
      {active === 'voting' && (
        <div className="space-y-4">
          {VOTING_SYSTEMS.map(vs => (
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
                  <p className="text-xs text-muted-foreground leading-relaxed">{vs.how}</p>
                </div>
                <div>
                  <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1.5">Why it matters here</div>
                  <p className="text-xs text-muted-foreground leading-relaxed">{vs.why}</p>
                </div>
              </div>
            </Card>
          ))}

          {/* IRV vs Condorcet explainer */}
          <Card className="p-5">
            <div className="font-semibold text-foreground mb-3">IRV vs Condorcet: Why Both?</div>
            <p className="text-xs text-muted-foreground leading-relaxed mb-4">
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
                  <p className="text-xs text-muted-foreground leading-relaxed">{s.desc}</p>
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

      {/* ── Caveats ──────────────────────────────────────────── */}
      {active === 'caveats' && (
        <div className="space-y-4">
          <Card className="p-5 bg-amber-50 border-amber-200">
            <div className="font-semibold text-amber-900 mb-1">This is a simulation, not a prediction</div>
            <p className="text-sm text-amber-800 leading-relaxed">
              The goal is to understand structural properties of electoral systems applied to the actual distribution of American political opinion, not to forecast 2028. Party formation, candidate emergence, strategic voting, and campaign dynamics are all absent.
            </p>
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
                  label: 'Senate is 51 seats, not 102',
                  body: 'The Senate normally has 100 seats with staggered six-year terms, so any single election fills only about a third of them. This simulation instead elects one senator per state plus DC (51 seats) in a single snapshot, because it is modeling what kind of senator each state\'s 2024 electorate would choose—not reconstructing the real class-by-class election calendar.',
                },
                {
                  label: 'House districts are idealized',
                  body: 'Districts are assigned urban/suburban/rural tiers based on census geography. Actual multi-member STV districts would be drawn differently, and gerrymandering is not modeled.',
                },
                {
                  label: 'Survey ≠ likely voters',
                  body: 'CES respondents skew more educated and more engaged than the general electorate. The party system here reflects the opinion distribution of survey-takers, which differs from the distribution of actual voters.',
                },
              ].map(a => (
                <div key={a.label} className="px-5 py-4">
                  <div className="font-medium text-foreground text-sm mb-1">{a.label}</div>
                  <p className="text-xs text-muted-foreground leading-relaxed">{a.body}</p>
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
              <div><span className="font-medium text-muted-foreground">Factor analysis:</span> Polychoric EFA, 5 factors, oblique (promax) rotation</div>
              <div><span className="font-medium text-muted-foreground">Clustering:</span> Dirichlet Process Gaussian Mixture Model (DPGMM)</div>
              <div><span className="font-medium text-muted-foreground">Ballot scoring:</span> Gaussian proximity kernel, σ=0.35, η²-weighted factors</div>
              <div><span className="font-medium text-muted-foreground">Legislation model:</span> Normal approximation of chamber Bernoulli vote counts</div>
            </div>
          </Card>
        </div>
      )}

    </div>
  );
}
