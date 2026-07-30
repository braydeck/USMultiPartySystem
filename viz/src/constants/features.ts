/** Feature gates for work that is kept in the codebase but not shown on the site. */

import type { Pipeline } from './labels';

/**
 * The Crossover candidate field — 10 base candidates plus 28 factor-deviation variants — is hidden.
 * It was always the least data-driven half of the model: the variants are synthetic positions
 * (one axis shifted by ±25% of the inter-party SD) scored by factor-space proximity rather than by
 * the DPGMM posterior every other surface uses, and it has no bootstrap, no turnout stops, and no
 * ballot-depth variants, so it drifts further out of date with each change to the party-line side.
 *
 * Nothing is deleted. The pipeline, the data files, and every Crossover-only card still exist and
 * still work; this flag only removes the affordances that reach them. Two ways back in:
 *
 *   1. Load any page with `?lab=crossover` — read once at startup, so it survives tab navigation
 *      (which clears the query string) and lasts until the next reload.
 *   2. Flip `CROSSOVER_BY_DEFAULT` to true and rebuild, to put it back for everyone.
 */
const CROSSOVER_BY_DEFAULT = false;

export const SHOW_CROSSOVER = CROSSOVER_BY_DEFAULT || (
  typeof window !== 'undefined'
  && new URLSearchParams(window.location.search).get('lab') === 'crossover'
);

/**
 * Candidate-field options for the Scenario/Pipeline toggle, and the `allowed` list its URL param
 * validates against. One source for both: with Crossover hidden, `?scenario=crossover` has to fall
 * back to party-line rather than reaching a view with no control to leave it.
 */
export const PIPELINE_OPTIONS: readonly Pipeline[] = SHOW_CROSSOVER
  ? ['rawMulti', 'factorDev']
  : ['rawMulti'];
