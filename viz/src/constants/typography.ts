/**
 * The app's type system, in one place — for both DOM text and SVG text.
 *
 * Before this, typography was ~950 inline utility declarations, a third of them arbitrary
 * pixel values, so there was nowhere to adjust the scale and the levels had drifted: section
 * headings were the same size as the card headings inside them, and nothing on a page
 * carried structure. The recurring unit of duplication was never the size on its own — it
 * was size + weight + colour + tracking + case, which is why one heading recipe appeared 58
 * times in a dozen near-identical spellings. So this module names recipes, not just sizes.
 *
 * Levels are defined by ROLE, not appearance. Pick by what the text is, and the hierarchy
 * cannot drift the way it already did.
 *
 * These are class-string constants rather than React components because headings here appear
 * in too many shapes — some with a badge beside the text, some with hint text, some carrying
 * extra margin — for a component to cover without props sprawl. Compose at the call site:
 *
 *     <h3 className={`${CARD_HEADING} mb-1`}>Chamber Composition</h3>
 *
 * Margin stays at the call site: it is layout, not type. Tailwind only sees class names as
 * literal strings, which is why every value here is a whole string and nothing is computed.
 */

// ---------------------------------------------------------------------------
// Heading levels, largest first
//
// Each tier has ONE heading tag, always:
//
//   PAGE_TITLE      h2      (h1 is the app name in App.tsx, outside any tab)
//   SECTION_HEADING h3
//   GROUP_LABEL     h4
//   CARD_HEADING    h4
//   MINOR_HEADING   h5
//
// Fixed rather than chosen per call site, because the tag was previously picked ad hoc and
// CARD_HEADING ended up as both h3 and h4 — on the presidency and overview tabs a card was
// announced as a *peer* of the section containing it, which misstates the structure to a
// screen reader.
//
// The cost: tabs with no section tier jump h2 → h4. A skipped level is a WCAG advisory, not
// a failure, and it reads honestly (there is no h3 there because there is no section). It
// disappears on any tab that gains a section tier. That trade is deliberate — the previous
// alternative, picking tags by nesting depth, is unenforceable and is what drifted.
// ---------------------------------------------------------------------------

/** The tab's name. One per tab. */
export const PAGE_TITLE = 'text-2xl font-bold text-foreground';

/**
 * A major division of a tab — the thing a reader scans for. Dark and larger than the cards
 * it contains. `tracking-wider` rather than `widest` because at this size widest sprawls
 * across the column.
 */
export const SECTION_HEADING =
  'text-lg font-bold text-foreground uppercase tracking-wider';

/**
 * The title of one card or chart. Muted, so a page of cards reads as body content and the
 * section headings carry the structure.
 */
export const CARD_HEADING =
  'text-sm font-semibold text-muted-foreground uppercase tracking-widest';

/** A labelled block inside a card. */
export const MINOR_HEADING =
  'text-xs font-semibold text-muted-foreground uppercase tracking-widest';

/**
 * A division WITHIN a section, naming the group of cards beneath it — "The Senate",
 * "Condorcet — STY", "FPTP · proportional electors".
 *
 * Sits outside the cards it introduces, between SECTION_HEADING and CARD_HEADING. Sentence
 * case and dark, against the section's dark caps above and the card's muted caps below, so
 * every step differs in size AND in either case or colour rather than size alone.
 */
export const GROUP_LABEL = 'text-base font-semibold text-foreground';

// ---------------------------------------------------------------------------
// Data recipes — the dense, numeric parts of the app
// ---------------------------------------------------------------------------

/**
 * The one big number on a stat card. Colour stays at the call site: emerald/rose/amber
 * encode direction, so they are semantic rather than typographic.
 */
export const METRIC_VALUE = 'text-2xl font-bold tabular-nums';

/*
 * Label tier — 12 / 10 / 9px, all muted, all unweighted, chosen by how dense the container
 * is rather than by importance. These are not headings: a heading names a region, a label
 * names a control or a column. Keeping them unweighted is what stops a dense table from
 * reading as a wall of small bold caps.
 */

/** Labels a control, or a column in a full-width table. */
export const FIELD_LABEL = 'text-xs text-muted-foreground uppercase tracking-widest';

/** Column head in a compact grid, where 12px would crowd the row. */
export const TABLE_HEADER = 'text-3xs text-muted-foreground uppercase tracking-widest';

/**
 * A row label or inline caption inside a compact data strip — the tightest tier.
 *
 * Not named AXIS_LABEL: three chart components already use that identifier for a
 * factor-name lookup map.
 */
export const DENSE_LABEL = 'text-4xs text-muted-foreground uppercase tracking-wider';

/*
 * Prose tier — 14 / 12 / 11px. Explanatory copy had drifted across four sizes (92 paragraphs
 * at 12px, 28 at 11px, 9 at 14px, 3 at 10px), which at 1px apart reads as sloppiness rather
 * than as hierarchy. Three tiers, each with a job:
 */

/** Multi-paragraph reading copy — the About tab, the caveats. Text someone sits and reads. */
export const BODY_PROSE = 'text-sm text-muted-foreground leading-relaxed';

/** The one-or-two-sentence explainer under a heading. The default for prose inside a card. */
export const CARD_HINT = 'text-xs text-muted-foreground';

/**
 * A note attached to a chart, or copy inside a compact tile — deliberately quieter than
 * CARD_HINT. This is the floor: 10px prose is below what this app asks anyone to read.
 */
export const FOOTNOTE = 'text-2xs text-muted-foreground';

// ---------------------------------------------------------------------------
// Chart type — SVG and Recharts
// ---------------------------------------------------------------------------

/**
 * SVG text cannot take Tailwind classes, so chart type is declared here as numbers.
 *
 * The floor is lower than the CSS scale's 9px on purpose: DOM text is sized to be read,
 * SVG text is sized to fit inside a mark. Do not "fix" that by raising it — `inMarkTight`
 * exists because a seat circle is ~14 units across, not because someone was careless.
 *
 * IMPORTANT — these numbers are read in the local coordinate system, which is not always
 * pixels. Recharts ticks and `style={{ fontSize }}` on DOM nodes are true pixels. But most
 * charts here draw into a `viewBox` scaled to `width: 100%` (ParliamentChart,
 * FPTPDisproportionality, CandidateTrajectory, VariantConstellationChart, AlluvialFlow,
 * HouseGridChart, PresidencyGrid, PartyVariantBar, the RCV charts), where a viewBox 480–600
 * wide renders into a 340–700px column — so the step is a user-space unit and the rendered
 * size is roughly 0.7–1.2× the number. One ladder still governs both, because the role of
 * the text is the same either way; just don't read these as guaranteed pixels.
 *
 * The cartogram zoom ramps (`HexCartogram`, `HexStateCartogram`) divide by the zoom
 * transform and are deliberately not on this ladder.
 */
export const CHART_TYPE = {
  /** Cartogram state abbreviation — the largest text in any chart. */
  stateLabel: 16,
  /** A bold value in a matrix cell, tooltip body copy, a secondary label in a cartogram cell. */
  cellValue: 12,
  /** Series, node and candidate names; category-axis ticks. */
  seriesLabel: 11,
  /** Value-axis ticks, legend ticks, reference-line labels. */
  axisTick: 10,
  /** Dense axes, tight plots, and axis titles in a small viewBox. */
  smallTick: 9,
  /** Text inside a bar, and the smallest label in a scaled viewBox. */
  inMark: 8,
  /** Text inside a seat circle or hex, where the mark itself is the constraint. */
  inMarkTight: 6,
} as const;

/**
 * Chart text fills. SVG `fill` attributes cannot resolve the `hsl(var(--…))` CSS variables
 * the DOM uses, so the muted-foreground family is restated here as literals.
 */
export const CHART_FILL = {
  /** Axis ticks and de-emphasised labels. */
  tick: '#94a3b8',
  /** Axis titles and named labels. */
  label: '#64748b',
  /** Gridline labels and the faintest tier. */
  faint: '#cbd5e1',
} as const;
