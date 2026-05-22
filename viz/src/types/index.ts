export interface PrimaryCandidate {
  code: string;
  name: string;
  F1: number;
  F2: number;
  F3: number;
  F4: number;
  F5: number;
  stages: Record<string, {
    voteTotal: number;
    votePct: number;
    status: string;
    quotaThreshold: number;
  }>;
}

export interface PrimaryData {
  stagesOrder: string[];
  stageLabels: Record<string, string>;
  quotaByStage: Record<string, number>;
  candidates: PrimaryCandidate[];
}

export interface SenateSeat {
  stateFips: string;
  stateAbbr: string;
  senatorCode: string;
  senatorLabel: string;
  senatorType: string;
  primaryCluster: string;
  secondaryCluster: string;
}

export type SenateScenario = 'condMixed' | 'irvMixed' | 'condPure' | 'irvPure' | 'condLF' | 'irvLF';
export type PresidentialScenario = 'mixed' | 'pure' | 'lightFusion';

export interface VoteModelRow {
  variable: string;
  domain: string;
  question: string;
  overallPct: number;
  // House (houseVoteModel.json)
  probPass?: number;
  verdict?: string;
  // Mixed senate scenarios
  condMixedProbPass?: number;
  condMixedVerdict?: string;
  irvMixedProbPass?: number;
  irvMixedVerdict?: string;
  // Pure senate scenarios
  condPureProbPass?: number;
  condPureVerdict?: string;
  irvPureProbPass?: number;
  irvPureVerdict?: string;
  // Light Fusion senate scenarios
  condLFProbPass?: number;
  condLFVerdict?: string;
  irvLFProbPass?: number;
  irvLFVerdict?: string;
  // LF president (STY_ctr)
  presLFSigns?: string;
  presLFPct?: number;
  // Presidential sign + support %
  presMixedSigns?: string;      // CON/SD (IRV winner)
  presMixedPct?: number;
  presMixedCondSigns?: string;  // SD/CON (Condorcet winner)
  presMixedCondPct?: number;
  presPureSigns?: string;       // STY (pure IRV winner)
  presPurePct?: number;
  // Legacy aliases (UnifiedBillTable in LegislationTab)
  condProbPass?: number;
  condVerdict?: string;
  irvProbPass?: number;
  irvVerdict?: string;
}

export interface HouseSeat {
  party: number;
  partyName: string;
  urban: number;
  suburban: number;
  rural: number;
  national: number;
  pctNational: number;
}

export interface CoalitionProfile {
  type: string;
  chamber: string;
  F1: number;
  F2: number;
  F3: number;
  F4: number;
  F5: number;
  seatsHouse: number;
  seatsSenateCondorcet: number;
  seatsSenateIRV: number;
}

export interface ClusterVariable {
  pct: number;
  question: string;
  domain: string;
}

export interface ClusterProfile {
  id: string;
  party: string;
  partyName: string;
  F1: number;
  F2: number;
  F3: number;
  F4: number;
  F5: number;
  seatsHouse: number;
  variables: Record<string, ClusterVariable>;
  keyPositions?: KeyPosition[];
}

export interface QuizQuestion {
  variable: string;
  factor: string;
  question: string;
  domain: string;
  clusterSupport: Record<string, number>;
}

export interface TransferMatrix {
  parties: string[];
  matrix: Record<string, Record<string, number>>;
}

export interface PrimaryStateWinner {
  stateAbbr: string;
  winnerCode: string;
  runnerUpCode: string;
  pod: string;
  nRespondents: number;
  shares: Record<string, number>;
}

export interface HouseStateEntry {
  stateAbbr: string;
  pluralityParty: string;
  totalSeats: number;
  seats: Record<string, number>;
}

export interface KeyPosition {
  question: string;
  pct: number;
  direction: 'supports' | 'opposes';
  diffPp: number;
}

export interface BlendVariable {
  pct: number;
  question: string;
  domain: string;
  diffPp: number;
}

export interface BlendProfile {
  code: string;
  isPure?: boolean;
  isLightFusion?: boolean;
  seatsCond: number;
  seatsIRV: number;
  F1: number;
  F2: number;
  F3: number;
  F4: number;
  F5: number;
  keyPositions: KeyPosition[];
  variables: Record<string, BlendVariable>;
}

export interface PresidentialCandidate {
  code: string;
  name: string;
  pct: number;
  votes: number;
  eliminated: boolean;
  winner: boolean;
}

export interface IRVRound {
  round: number;
  candidates: PresidentialCandidate[];
}

export interface CondorcetMatchup {
  candidateA: string;
  candidateB: string;
  aWinsPct: number;
  margin: number;
  winner: string;
}

export interface PresidentialStateWinner {
  stateAbbr: string;
  winner: string;
  pod: string;
  nRespondents: number;
  shares: Record<string, number>;
}

export interface PresidentialElection {
  irvRounds: IRVRound[];
  irvWinner: string;
  condorcetMatchups: CondorcetMatchup[];
  condorcetWinner: string;
  irvStateWinners: Record<string, PresidentialStateWinner>;
}

export interface PrimaryTransfer {
  source: string;
  target: string;
  votes: number;
  pct: number;
  round: string;
  type: string;
}

export interface PrimarySankeyNode {
  id: string;
  label: string;
  stageIdx: number;
  pct: number;
}

export interface PrimarySankeyLink {
  source: string;
  target: string;
  value: number;
  type?: string; // "continuation" | "elimination" | "surplus"
}

export interface PrimarySankeyData {
  stageLabels: string[];
  nodes: PrimarySankeyNode[];
  links: PrimarySankeyLink[];
}

export interface ConstellationNode {
  id: string;
  label: string;
  seats: number;
  F1: number; F2: number; F3: number; F4: number; F5: number;
}
