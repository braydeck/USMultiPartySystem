/**
 * Which offices ranked-choice voting reaches in Alaska and Maine, and what
 * happened in every contest it has governed.
 *
 * This is the ledger behind the tab's opening panel. It lives as data rather than
 * prose because the interesting facts are structural — Maine's RCV stops short of
 * state general elections, and most RCV contests never needed a second round — and
 * a paragraph hides both.
 *
 * Cells with a `race` key are looked up in rcvResults.json, so their winner and
 * first-round share come from the tabulation rather than from this file. Only
 * contests with no ranked tabulation (and therefore no race record) carry literal
 * numbers, transcribed from the state's published results.
 */

export type CellStatus =
  | 'RANKED'       // went to at least one transfer round
  | 'FIRST_ROUND'  // RCV applied, but a first-choice majority ended it
  | 'NOT_RCV'      // RCV does not govern this office in this state
  | 'NO_ELECTION'; // office was not on the ballot that year

export interface CoverageCell {
  status: CellStatus;
  /** Matches RCVRace.raceName; the winner and first-round share are read from there. */
  race?: string;
  /** For contests with no race record: winner's first-choice share and ballot line. */
  pct?: number;
  winner?: string;
  party?: string;
}

export interface CoverageRow {
  office: string;
  years: Record<number, CoverageCell>;
}

export interface StateCoverage {
  years: number[];
  adopted: string;
  scope: string;
  /** Offices RCV does not reach, named plainly; null where it reaches everything. */
  excluded: string | null;
  generals: CoverageRow[];
  primaries: CoverageRow[];
  /** Ranked contests the tab does not chart, so the panel does not imply it is exhaustive. */
  alsoRanked: string | null;
}

const NONE: CoverageCell = { status: 'NO_ELECTION' };

export const COVERAGE: Record<'AK' | 'ME', StateCoverage> = {
  AK: {
    years: [2022, 2024],
    adopted: 'Ballot Measure 2 (2020), first used 2022',
    scope: 'Every state and federal general election, run off a nonpartisan top-four primary',
    excluded: null,
    generals: [
      { office: 'President', years: {
        2022: NONE,
        2024: { status: 'FIRST_ROUND', race: 'President' } } },
      { office: 'U.S. Senate', years: {
        2022: { status: 'RANKED', race: 'U.S. Senate' },
        2024: NONE } },
      { office: 'U.S. House', years: {
        2022: { status: 'RANKED', race: 'U.S. House, at-large' },
        2024: { status: 'RANKED', race: 'U.S. House, at-large' } } },
      { office: 'U.S. House (special)', years: {
        2022: { status: 'RANKED', race: 'U.S. House, at-large (special)' },
        2024: NONE } },
      { office: 'Governor', years: {
        2022: { status: 'FIRST_ROUND', race: 'Governor' },
        2024: NONE } },
    ],
    primaries: [],
    alsoRanked: 'Eight state legislative districts also went to transfers in 2022 and 2024; only statewide contests are charted here.',
  },

  ME: {
    years: [2018, 2020, 2022, 2024, 2026],
    adopted: 'Question 5 (2016), first used 2018',
    scope: 'Federal general elections, plus every state and federal primary',
    excluded: 'State general elections. Governor and the Legislature still run on plurality, after the Maine Supreme Judicial Court read the state constitution to require it.',
    generals: [
      { office: 'President', years: {
        2018: NONE,
        2020: { status: 'FIRST_ROUND', pct: 53.1, winner: 'Joe Biden', party: 'D' },
        2022: NONE,
        2024: { status: 'FIRST_ROUND', pct: 52.4, winner: 'Kamala Harris', party: 'D' },
        2026: NONE } },
      { office: 'U.S. Senate', years: {
        2018: { status: 'FIRST_ROUND', pct: 54.3, winner: 'Angus King', party: 'I' },
        2020: { status: 'FIRST_ROUND', pct: 51.0, winner: 'Susan Collins', party: 'R' },
        2022: NONE,
        2024: { status: 'FIRST_ROUND', pct: 52.1, winner: 'Angus King', party: 'I' },
        2026: NONE } },
      { office: 'U.S. House, CD1', years: {
        2018: { status: 'FIRST_ROUND', pct: 58.8, winner: 'Chellie Pingree', party: 'D' },
        2020: { status: 'FIRST_ROUND', pct: 62.2, winner: 'Chellie Pingree', party: 'D' },
        2022: { status: 'FIRST_ROUND', pct: 62.9, winner: 'Chellie Pingree', party: 'D' },
        2024: { status: 'FIRST_ROUND', pct: 58.7, winner: 'Chellie Pingree', party: 'D' },
        2026: NONE } },
      { office: 'U.S. House, CD2', years: {
        2018: { status: 'RANKED', race: 'U.S. House, CD2' },
        2020: { status: 'FIRST_ROUND', pct: 53.0, winner: 'Jared Golden', party: 'D' },
        2022: { status: 'RANKED', race: 'U.S. House, CD2' },
        2024: { status: 'FIRST_ROUND', pct: 50.4, winner: 'Jared Golden', party: 'D' },
        2026: NONE } },
      { office: 'Governor', years: {
        2018: { status: 'NOT_RCV' },
        2020: NONE,
        2022: { status: 'NOT_RCV' },
        2024: NONE,
        2026: { status: 'NOT_RCV' } } },
    ],
    primaries: [
      { office: 'Governor (D)', years: {
        2018: { status: 'RANKED', race: 'Governor, Democratic primary' },
        2020: NONE, 2022: NONE, 2024: NONE,
        2026: { status: 'RANKED', race: 'Governor, Democratic primary' } } },
      { office: 'Governor (R)', years: {
        2018: NONE, 2020: NONE, 2022: NONE, 2024: NONE,
        2026: { status: 'RANKED', race: 'Governor, Republican primary' } } },
      { office: 'U.S. House, CD2 (D)', years: {
        2018: { status: 'RANKED', race: 'U.S. House CD2, Democratic primary' },
        2020: NONE, 2022: NONE, 2024: NONE,
        2026: { status: 'RANKED', race: 'U.S. House CD2, Democratic primary' } } },
      { office: 'U.S. House, CD2 (R)', years: {
        2018: NONE,
        2020: { status: 'RANKED', race: 'U.S. House CD2, Republican primary' },
        2022: NONE, 2024: NONE, 2026: NONE } },
    ],
    alsoRanked: 'A handful of state legislative primaries also went to transfers; only statewide and congressional contests are charted here.',
  },
};

export const STATUS_LABEL: Record<CellStatus, string> = {
  RANKED: 'Went to transfers',
  FIRST_ROUND: 'First-choice majority, no transfers',
  NOT_RCV: 'Not ranked — plurality',
  NO_ELECTION: 'Not on the ballot',
};
