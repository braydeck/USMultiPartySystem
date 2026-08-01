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
 * How close the runner-up has to be, in points of resample win share, for a state to split.
 *
 * The measure is the gap between the top two, not the leader's own share. With ten parties
 * a leader can hold a clear lead on well under half the resamples — Montana's Conservative
 * takes 46% against Solidarity's 24% — while a leader over half can be in a photo finish:
 * Virginia is 50.3 to 47.4. A rule on the leader's level splits Montana and not Virginia,
 * which is backwards.
 *
 * Twelve is a judgement, but not a free one. Sorted, the Condorcet gaps run 0.8 up to 10.6
 * and then jump to 15.5; the IRV gaps run to 9.6 and then jump to 12.7. Twelve sits in the
 * empty space in both, so the split set is the same for any cutoff from 11 to 12 and does
 * not turn on where exactly the line falls. Ten sat on top of a state — Wyoming's gap is
 * exactly 10.0 — which made one delegation depend on a rounding convention.
 */
export const SPLIT_THRESHOLD_PP = 12;

/** Inclusive, with slack for float error: gaps come from subtracting two shares, so a
 *  state exactly on the line lands at 9.999999999999998 rather than 10. */
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
