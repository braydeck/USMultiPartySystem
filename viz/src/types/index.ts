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

export type SenateScenario = 'condFD' | 'irvFD' | 'condRawMulti' | 'irvRawMulti';
export type PresidentialScenario = 'factorDev' | 'rawMulti';

export interface VoteModelRow {
  variable: string;
  domain: string;
  question: string;
  overallPct: number;
  // House canonical (houseVoteModel.json)
  probPass?: number;
  verdict?: string;
  // House State STV (9-party, 873 seats)
  houseStvProbPass?: number;
  houseStvVerdict?: string;
  // House Raw Multi (pure_multi, 873 seats)
  houseRawMultiProbPass?: number;
  houseRawMultiVerdict?: string;
  // House Factor Dev (FD candidates, 873 seats)
  houseFDProbPass?: number;
  houseFDVerdict?: string;
  // Pure senate scenarios
  condPureProbPass?: number;
  condPureVerdict?: string;
  irvPureProbPass?: number;
  irvPureVerdict?: string;
  // Factor Deviation senate scenarios
  condFDProbPass?: number;
  condFDVerdict?: string;
  irvFDProbPass?: number;
  irvFDVerdict?: string;
  // FD president — separate for IRV and Condorcet winners
  presFDSigns?: string;
  presFDPct?: number;
  presFDIRVSigns?: string;
  presFDIRVPct?: number;
  presFDCondSigns?: string;
  presFDCondPct?: number;
  // Raw/pure president (STY)
  presPureSigns?: string;
  presPurePct?: number;
  // Raw Multi senate scenarios
  condRawMultiProbPass?: number;
  condRawMultiVerdict?:  string;
  irvRawMultiProbPass?:  number;
  irvRawMultiVerdict?:   string;
  // Raw Multi president (SD_1 IRV, CTR_1 Condorcet)
  presRawMultiIRVSigns?:  string;
  presRawMultiIRVPct?:    number;
  presRawMultiCondSigns?: string;
  presRawMultiCondPct?:   number;
}

export interface HouseSeat {
  party: number;
  partyName: string;
  urban: number;
  suburban: number;
  rural: number;
  national: number;
  pctNational: number;
  pctPopulation: number;
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

// ── Factor Deviation types ─────────────────────────────────────────────────

export interface FDSenateSeat {
  stateFips: string;
  stateAbbr: string;
  senatorCode: string;
  senatorParty: string;
  senatorAxis: string;
  senatorDir: string;
  // SenateSeat-compatible fields
  senatorLabel: string;
  senatorType: string;
  primaryCluster: string;
  secondaryCluster: string;
}

export interface HouseSeatResult {
  state: string;
  stateFips: number;
  totalSeats: number;
  party: string;
  seats: number;
  voteShare: number;
}

export interface FDHouseSeat {
  code: string;
  party: string;
  axis: string;
  direction: string;
  urban: number;
  suburban: number;
  rural: number;
  national: number;
  pctNational: number;
}

export interface FDKeyPosition {
  variable: string;
  question: string;
  domain: string;
  value: number;
  overall: number;
  diff: number;
}

export interface FDCandidateProfile {
  code: string;
  party: string;
  axis: string;
  direction: string;
  F1: number;
  F2: number;
  F3: number;
  F4: number;
  F5: number;
  keyPositions: FDKeyPosition[];
  variables?: Record<string, BlendVariable>;
}

export interface FDPrimaryCandidate {
  code: string;
  name: string;
  party: string;
  axis: string;
  direction: string;
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

export interface FDPrimaryData {
  stagesOrder: string[];
  stageLabels: Record<string, string>;
  quotaByStage: Record<string, number>;
  candidates: FDPrimaryCandidate[];
}
