import type { StateUncertainty } from './uncertainty';

/**
 * Senate delegations, allowing a state to send two senators from different parties.
 *
 * The model elects one winner per state, because it cannot simulate two staggered races
 * with different electorates six years apart. Doubling that winner fills the chamber but
 * asserts every delegation is matched, which is false today — a dozen states currently
 * send one of each — and it hands marginal states two seats they would not both win.
 *
 * So: where a state is genuinely contested, split it. "Contested" is measured on the
 * resampling, not on one margin — the share of resamples each party wins the state. A
 * state whose winner changes from sample to sample is a state whose two seats, decided
 * by two different electorates, plausibly go different ways. Where one party wins the
 * state in most resamples, it takes both.
 *
 * The chamber size is unchanged: every state still returns two senators.
 */

/**
 * How close the runner-up has to be, in points of resample win share, for a state to
 * split. Ten is a judgement call, not a derived quantity: it is wide enough to catch the
 * genuinely marginal states and narrow enough to leave safe ones alone.
 */
export const SPLIT_THRESHOLD_PP = 10;

/** Inclusive at the threshold, with slack for float error: Wyoming's gap is exactly ten
 *  points and subtracting the two shares gives 9.999999999999998. */
const EPS = 1e-9;

export interface Delegation {
  fips: string;
  /** One party per seat. Two entries always; equal when the state does not split. */
  seats: [string, string];
  split: boolean;
  topParty: string;
  topPct: number;
  runnerParty?: string;
  runnerPct?: number;
}

/** Per-state delegations under the split rule, in FIPS order. */
export function delegations(states: Record<string, StateUncertainty>): Delegation[] {
  return Object.entries(states)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([fips, st]) => {
      const ranked = Object.entries(st.dist).sort((a, b) => b[1] - a[1]);
      const [topParty, topP] = ranked[0] ?? [st.modal, 1];
      const runner = ranked[1];
      const gapPP = runner ? (topP - runner[1]) * 100 : Infinity;
      const split = gapPP <= SPLIT_THRESHOLD_PP + EPS;
      return {
        fips,
        seats: (split && runner ? [topParty, runner[0]] : [topParty, topParty]) as [string, string],
        split,
        topParty,
        topPct: topP * 100,
        runnerParty: runner?.[0],
        runnerPct: runner ? runner[1] * 100 : undefined,
      };
    });
}

/** Seats per party across the chamber. Sums to twice the number of states. */
export function delegationSeats(states: Record<string, StateUncertainty>): Record<string, number> {
  const out: Record<string, number> = {};
  for (const d of delegations(states)) {
    for (const p of d.seats) out[p] = (out[p] ?? 0) + 1;
  }
  return out;
}
