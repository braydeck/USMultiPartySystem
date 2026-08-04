import { resetUrlParams } from '../../hooks/useUrlState';
import { SECTION_HEADING, GROUP_LABEL, CARD_HINT } from '../../constants/typography';

interface Concept {
  code: string;
  name: string;
  color: string;
  what: string;
  here: string;
}

interface ConceptGroup {
  title: string;
  items: Concept[];
}

function buildConceptGroups(): ConceptGroup[] {
  return [
    {
      title: 'Single-Seat Systems',
      items: [
        {
          code: 'FPTP',
          name: 'First Past the Post',
          color: '#64748b',
          what: 'Plurality wins a single-member district.',
          here: "Today's system; baseline for all charts. Greatest disproportionality.",
        },
        {
          code: 'Condorcet',
          name: 'Round-Robin',
          color: '#a16207',
          what: 'Candidate who wins every head-to-head matchup.',
          here: 'Favors broadly acceptable consensus candidates.',
        },
        {
          code: 'IRV',
          name: 'Instant-Runoff',
          color: '#16a34a',
          what: 'Ranked ballot. Lowest drops each round; votes transfer to a majority.',
          here: 'Rewards first-choice strength; largely preserves 2-party balance.',
        },
      ],
    },
    {
      title: 'Proportional Representation (PR)',
      items: [
        {
          code: 'STV',
          name: 'Single Transferable Vote',
          color: '#1d4ed8',
          what: 'Ranked choices in multi-seat districts transfer via quotas.',
          here: 'If a candidate is eliminated or reaches a quota, votes transfer to subsequent choices until seats are filled.',
        },
        {
          code: 'Party List',
          name: 'Open Party List',
          color: '#0369a1',
          what: 'Seats allocated to party lists matching overall vote share.',
          here: 'Translates candidate votes directly into proportional party seats. Top vote recipients are seated within parties.',
        },
      ],
    },
  ];
}

export function ConceptStrip() {
  const groups = buildConceptGroups();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between border-b border-border pb-2">
        <h3 className={SECTION_HEADING}>
          Voting Systems at a Glance
        </h3>
        <a
          href={urlForVoting()}
          onClick={(e) => {
            e.preventDefault();
            resetUrlParams({ tab: 'about', about: 'voting' });
          }}
          className="text-xs text-indigo-600 hover:text-indigo-700 font-medium shrink-0"
        >
          Full explainer →
        </a>
      </div>

      <div className="space-y-4">
        {groups.map((group) => (
          <div key={group.title} className="space-y-2">
            <h4 className={GROUP_LABEL}>
              {group.title}
            </h4>
            <div
              className={`grid gap-3 ${
                group.items.length === 3 ? 'sm:grid-cols-3' : 'sm:grid-cols-2'
              }`}
            >
              {group.items.map((c) => (
                <div
                  key={c.code}
                  className="rounded-lg border border-border bg-card p-3 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center gap-2 mb-1.5">
                      <span
                        className="text-2xs font-bold font-mono px-1.5 py-0.5 rounded shrink-0"
                        style={{ backgroundColor: c.color + '18', color: c.color }}
                      >
                        {c.code}
                      </span>
                      <div className="text-xs font-semibold text-foreground">
                        {c.name}
                      </div>
                    </div>
                    <p className={`${CARD_HINT} leading-snug mb-2`}>
                      {c.what}
                    </p>
                  </div>
                  <p className="text-2xs text-foreground/80 leading-snug pt-1 border-t border-border/50">
                    {c.here}
                  </p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function urlForVoting(): string {
  const url = new URL(window.location.href);
  return `${url.pathname}?tab=about&about=voting`;
}