import { MINOR_HEADING, CARD_HINT } from '../../constants/typography';

/**
 * Three-up "rule → what it does → what follows" cards, sitting under a tab's title.
 *
 * Replaces the multi-sentence intro paragraph each chamber tab used to carry. A paragraph
 * makes the reader hold three parallel mechanisms in their head and infer which consequence
 * attaches to which; three cells put each pairing in its own box and let the eye compare them
 * column-wise instead.
 *
 * Slim on purpose: term, one line of mechanism, one line of consequence below a rule. It is a
 * primer, not a findings card — the numbers live in the charts below it.
 *
 * The sibling `ConceptStrip` is the app-wide voting-systems explainer on the Overview; this is
 * the per-chamber version, and deliberately carries no external links or code badges.
 */
export interface Mechanism {
  /** The rule or method being named. */
  term: string;
  /** What it does, mechanically. */
  what: string;
  /** What follows from it in this simulation. */
  consequence: string;
  /** Optional accent for the term, e.g. a method's established colour. */
  color?: string;
}

export function MechanismStrip({ items }: { items: Mechanism[] }) {
  return (
    <div className={`grid gap-3 ${items.length === 3 ? 'sm:grid-cols-3' : 'sm:grid-cols-2'}`}>
      {items.map(m => (
        <div key={m.term}
          className="rounded-lg border border-border bg-card p-3 flex flex-col justify-between">
          <div>
            {/* Colour via inline style, not a class: it has to beat MINOR_HEADING's
                text-muted-foreground, and utility order in the sheet can't be relied on. */}
            <h4 className={`${MINOR_HEADING} mb-1.5`} style={m.color ? { color: m.color } : undefined}>
              {m.term}
            </h4>
            <p className={`${CARD_HINT} leading-snug mb-2`}>{m.what}</p>
          </div>
          <p className="text-2xs text-foreground/80 leading-snug pt-1.5 border-t border-border/50">
            {m.consequence}
          </p>
        </div>
      ))}
    </div>
  );
}
