import { useState } from 'react';
import { useUrlState, resetUrlParams, urlForParams } from './hooks/useUrlState';
import { SenateTab } from './tabs/SenateTab';
import { HouseTab } from './tabs/HouseTab';
import { QuizTab } from './tabs/QuizTab';
import { PartiesTab } from './tabs/PartiesTab';
import { PresidencyTab } from './tabs/PresidencyTab';
import { SingleRaceTab } from './tabs/SingleRaceTab';
import { LegislationTab } from './tabs/LegislationTab';
import { AboutTab } from './tabs/AboutTab';
import { OverviewTab } from './tabs/OverviewTab';
import { RCVTab } from './tabs/RCVTab';
import { TooltipProvider } from './components/ui/tooltip';
import { StateLink } from './components/shared/StateLink';
import { SocialLinks } from './components/SocialLinks';

import senateVoteModelData from './data/senateVoteModel.json';
import houseSeatsData from './data/houseSeats.json';
import houseSeatsProbBasedData from './data/houseSeatsProbBased.json';
import houseVoteModelData from './data/houseVoteModel.json';
import candidateVoteModelData from './data/candidateVoteModel.json';
import houseStateMapData from './data/houseStateMap.json';
import coalitionProfilesData from './data/coalitionProfiles.json';
import transferMatrixData from './data/transferMatrix.json';
import clusterProfilesData from './data/clusterProfiles.json';
import quizQuestionsData from './data/quizQuestions.json';
import fdSenateCondorcetData from './data/fdSenateCondorcet.json';
import fdSenateIRVData from './data/fdSenateIRV.json';
import pureMultiSenateCondorcetData from './data/pureMultiSenateCondorcet.json';
import pureMultiSenateIRVData from './data/pureMultiSenateIRV.json';
// Current-participation (validated-turnout-weighted) datasets — turnout axis.
import pureMultiSenateCondorcetTurnoutData from './data/pureMultiSenateCondorcetTurnout.json';
import pureMultiSenateIRVTurnoutData from './data/pureMultiSenateIRVTurnout.json';
import rawMultiPresidentialElectionTurnoutData from './data/rawMultiPresidentialElectionTurnout.json';
import houseSeatsTurnoutData from './data/houseSeatsTurnout.json';
import houseStateMapTurnoutData from './data/houseStateMapTurnout.json';
import districtStvResultsTurnoutData from './data/districtStvResultsTurnout.json';
import houseVoteModelTurnoutData from './data/houseVoteModelTurnout.json';
import senateVoteModelTurnoutData from './data/senateVoteModelTurnout.json';
import senateBucketsData from './data/senateBuckets.json';
import senateCondorcetData from './data/senateCondorcet.json';
import fdHouseSeatsData from './data/fdHouseSeats.json';
import fdPrimaryData from './data/fdPrimary.json';
import fdPrimaryStateWinnersData from './data/fdPrimaryStateWinners.json';
import fdPrimaryStageSharesData from './data/fdPrimaryStageShares.json';
import fdPrimarySankeyData from './data/fdPrimarySankey.json';
import fdPrimaryBucketsData from './data/fdPrimaryBuckets.json';
import fdPresidentialElectionData from './data/fdPresidentialElection.json';
import rawMultiPresidentialElectionData from './data/rawMultiPresidentialElection.json';
import fdProfilesData from './data/fdProfiles.json';
import pureMultiPrimaryData from './data/pureMultiPrimary.json';
import pureMultiPrimaryStateWinnersData from './data/pureMultiPrimaryStateWinners.json';
import pureMultiPrimaryStageSharesData from './data/pureMultiPrimaryStageShares.json';
import pureMultiPrimarySankeyData from './data/pureMultiPrimarySankey.json';
import pureMultiPrimaryBucketsData from './data/pureMultiPrimaryBuckets.json';
import fptpDisproportionalityData from './data/fptpDisproportionality.json';
import countyTiersData from './data/countyTiers.json';
import districtStvResultsData from './data/districtStvResults.json';
import districtCountyMapData from './data/districtCountyMap.json';
import houseTransfersData from './data/houseTransfers.json';
import fdVariantAttractionData from './data/fdVariantAttraction.json';
import fdCandidatePositionsData from './data/fdCandidatePositions.json';
import clusterSpreadsData from './data/clusterSpreads.json';
import fdAttractionDriversData from './data/fdAttractionDrivers.json';
import fdDistrictStvResultsData from './data/fdDistrictStvResults.json';
import rcvResultsData from './data/rcvResults.json';
import houseSeatsTripleData from './data/houseSeatsTriple.json';
import fdHouseSeatsTripleData from './data/fdHouseSeatsTriple.json';
import districtStvResultsTripleData from './data/districtStvResultsTriple.json';
import fdDistrictStvResultsTripleData from './data/fdDistrictStvResultsTriple.json';
import houseStateMapTripleData from './data/houseStateMapTriple.json';
import districtCountyMapTripleData from './data/districtCountyMapTriple.json';


import type {
  PrimaryStateWinner, PrimaryStageShares, VoteModelRow, CandidateVoteRow, HouseSeat,
  HouseStateEntry, CoalitionProfile, TransferMatrix, ClusterProfile,
  QuizQuestion, PresidentialElection,
  PrimarySankeyData,
  FDSenateSeat, FDHouseSeat, FDPrimaryData, FDCandidateProfile, FPTPState,
  DistrictResult, RCVData,
} from './types';

// Top-level tabs shown directly in the nav strip, before the Scenarios dropdown.
const TOP_TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'quiz',     label: 'Party Quiz' },
  { id: 'parties',  label: 'Parties' },
] as const;

// Simulation scenarios, collapsed into the "Scenarios" dropdown.
const SCENARIO_TABS = [
  { id: 'presidency',  label: 'Presidency' },
  { id: 'senate',      label: 'Senate' },
  { id: 'house',       label: 'House' },
  { id: 'singleRace',  label: 'Single Race' },
  { id: 'legislation', label: 'Legislation' },
  { id: 'rcv',         label: 'IRV Case Studies' },
] as const;

// Shown last in the nav, after the Scenarios dropdown.
const ABOUT_TAB = { id: 'about', label: 'What Is This?' } as const;

const ALL_TABS = [...TOP_TABS, ...SCENARIO_TABS, ABOUT_TAB] as const;

type TabId = typeof ALL_TABS[number]['id'];

// Nav tab styling — mirrors the shadcn TabsTrigger classes, with active state applied
// conditionally since these are now real links rather than Radix triggers.
const NAV_TAB_BASE =
  'inline-flex items-center justify-center whitespace-nowrap rounded-md px-4 py-1.5 text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2';
const navTabClass = (active: boolean) =>
  `${NAV_TAB_BASE} ${active ? 'bg-secondary text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground hover:bg-accent'}`;

export default function App() {
  // On mobile, land on the Party Quiz (the shareable hook) by default; desktop opens on Overview.
  const landingDefault: TabId =
    typeof window !== 'undefined' && window.matchMedia('(max-width: 639px)').matches ? 'quiz' : 'overview';
  const [tab] = useUrlState<TabId>('tab', landingDefault, { allowed: ALL_TABS.map(t => t.id) });
  const [menuOpen, setMenuOpen] = useState(false);
  const [scenariosOpen, setScenariosOpen] = useState(false);
  // Tab navigation resets the query string so a tab's filters don't follow you to the next tab.
  const setTab = (next: TabId) => resetUrlParams({ tab: next });

  const isScenario = SCENARIO_TABS.some(t => t.id === tab);
  const activeLabel = ALL_TABS.find(t => t.id === tab)?.label ?? 'Menu';

  return (
    <TooltipProvider>
    <div className="min-h-screen bg-background text-foreground">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:top-2 focus:left-2 focus:bg-card focus:text-foreground focus:px-4 focus:py-2 focus:rounded-md focus:shadow-lg focus:border focus:border-border">
        Skip to content
      </a>
      {/* Title — scrolls away */}
      <div className="border-b border-border/50 bg-card">
        <div className="max-w-7xl mx-auto px-4 pt-3 pb-2 flex items-center gap-3">
          <h1 className="text-xl font-bold text-foreground">STV 2028</h1>
          <div className="text-sm text-muted-foreground">Proportional Democracy Simulation</div>
        </div>
      </div>
      {/* Nav tabs — sticky */}
      <header className="border-b border-border bg-card/95 backdrop-blur sticky top-0 z-20">
        <nav aria-label="Main navigation" className="max-w-7xl mx-auto px-4 py-1.5">
          {/* Desktop: tab strip + Scenarios dropdown */}
          <div className="hidden sm:flex items-center gap-1">
            <div className="inline-flex items-center gap-1">
              {TOP_TABS.map(t => (
                <StateLink key={t.id} href={urlForParams({ tab: t.id }, true)}
                  onNavigate={() => setTab(t.id)}
                  aria-current={tab === t.id ? 'page' : undefined}
                  className={navTabClass(tab === t.id)}>
                  {t.label}
                </StateLink>
              ))}
            </div>

            <div className="relative">
              <button
                type="button"
                onClick={() => setScenariosOpen(o => !o)}
                aria-expanded={scenariosOpen}
                aria-haspopup="true"
                className={`inline-flex items-center gap-1 whitespace-nowrap rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
                  isScenario ? 'bg-secondary text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                }`}
              >
                {isScenario ? SCENARIO_TABS.find(t => t.id === tab)?.label : 'Scenarios'}
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6" /></svg>
              </button>
              {scenariosOpen && (
                <>
                  <div className="fixed inset-0 z-30" onClick={() => setScenariosOpen(false)} aria-hidden="true" />
                  <div className="absolute left-0 mt-1 z-40 min-w-[200px] flex flex-col rounded-md border border-border bg-card shadow-lg overflow-hidden py-1">
                    {SCENARIO_TABS.map(t => (
                      <StateLink
                        key={t.id}
                        href={urlForParams({ tab: t.id }, true)}
                        onNavigate={() => { setTab(t.id); setScenariosOpen(false); }}
                        aria-current={tab === t.id ? 'page' : undefined}
                        className={`text-left px-3 py-2 text-sm transition-colors ${
                          tab === t.id ? 'bg-slate-900 text-white font-medium' : 'text-foreground hover:bg-muted'
                        }`}
                      >
                        {t.label}
                      </StateLink>
                    ))}
                  </div>
                </>
              )}
            </div>

            <StateLink href={urlForParams({ tab: ABOUT_TAB.id }, true)}
              onNavigate={() => setTab(ABOUT_TAB.id)}
              aria-current={tab === ABOUT_TAB.id ? 'page' : undefined}
              className={navTabClass(tab === ABOUT_TAB.id)}>
              {ABOUT_TAB.label}
            </StateLink>
          </div>

          {/* Mobile: hamburger menu */}
          <div className="sm:hidden">
            <button
              type="button"
              onClick={() => setMenuOpen(o => !o)}
              aria-expanded={menuOpen}
              aria-label={menuOpen ? 'Close navigation menu' : 'Open navigation menu'}
              className="w-full flex items-center justify-between rounded-md px-3 py-2 text-sm font-medium text-foreground hover:bg-muted"
            >
              <span>{activeLabel}</span>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
                {menuOpen ? <path d="M6 6l12 12M6 18L18 6" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
              </svg>
            </button>
            {menuOpen && (
              <div className="mt-1 flex flex-col rounded-md border border-border bg-card shadow-lg overflow-hidden">
                {TOP_TABS.map(t => (
                  <StateLink
                    key={t.id}
                    href={urlForParams({ tab: t.id }, true)}
                    onNavigate={() => { setTab(t.id); setMenuOpen(false); }}
                    aria-current={tab === t.id ? 'page' : undefined}
                    className={`text-left px-3 py-2.5 text-sm transition-colors ${
                      tab === t.id ? 'bg-slate-900 text-white font-medium' : 'text-foreground hover:bg-muted'
                    }`}
                  >
                    {t.label}
                  </StateLink>
                ))}
                <div className="px-3 pt-2 pb-1 mt-1 border-t border-border/50 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                  Scenarios
                </div>
                {SCENARIO_TABS.map(t => (
                  <StateLink
                    key={t.id}
                    href={urlForParams({ tab: t.id }, true)}
                    onNavigate={() => { setTab(t.id); setMenuOpen(false); }}
                    aria-current={tab === t.id ? 'page' : undefined}
                    className={`text-left px-3 py-2.5 text-sm transition-colors ${
                      tab === t.id ? 'bg-slate-900 text-white font-medium' : 'text-foreground hover:bg-muted'
                    }`}
                  >
                    {t.label}
                  </StateLink>
                ))}
                <StateLink
                  href={urlForParams({ tab: ABOUT_TAB.id }, true)}
                  onNavigate={() => { setTab(ABOUT_TAB.id); setMenuOpen(false); }}
                  aria-current={tab === ABOUT_TAB.id ? 'page' : undefined}
                  className={`text-left px-3 py-2.5 text-sm transition-colors border-t border-border/50 mt-1 ${
                    tab === ABOUT_TAB.id ? 'bg-slate-900 text-white font-medium' : 'text-foreground hover:bg-muted'
                  }`}
                >
                  {ABOUT_TAB.label}
                </StateLink>
              </div>
            )}
          </div>
        </nav>
      </header>

      <main id="main-content" className="max-w-7xl mx-auto px-4 py-8">
        {tab === 'about' && <AboutTab />}
        {tab === 'overview' && (
          <OverviewTab
            fdElection={fdPresidentialElectionData as unknown as PresidentialElection}
            rawMultiElection={rawMultiPresidentialElectionData as unknown as PresidentialElection}
            rawMultiSenateCond={pureMultiSenateCondorcetTurnoutData as unknown as FDSenateSeat[]}
            rawMultiSenateIRV={pureMultiSenateIRVTurnoutData as unknown as FDSenateSeat[]}
            fdSenateCond={fdSenateCondorcetData as unknown as FDSenateSeat[]}
            fdSenateIRV={fdSenateIRVData as unknown as FDSenateSeat[]}
            houseSeats={houseSeatsTurnoutData as HouseSeat[]}
            senateVotes={senateVoteModelData as VoteModelRow[]}
            houseVotes={houseVoteModelData as VoteModelRow[]}
            clusters={clusterProfilesData as ClusterProfile[]}
            fdProfiles={fdProfilesData as unknown as Record<string, FDCandidateProfile>}
            fptpStates={fptpDisproportionalityData as FPTPState[]}
            stateMap={houseStateMapData as unknown as Record<string, HouseStateEntry>}
            clusterSpreads={clusterSpreadsData as { party: string; n: number; [key: string]: string | number }[]}
            onNavigate={(t) => setTab(t as TabId)}
          />
        )}
        {tab === 'presidency' && (
          <PresidencyTab
            generalProps={{
              factorDev: fdPresidentialElectionData as unknown as PresidentialElection,
              rawMulti: rawMultiPresidentialElectionData as unknown as PresidentialElection,
              rawMultiTurnout: rawMultiPresidentialElectionTurnoutData as unknown as PresidentialElection,
              clusters: clusterProfilesData as ClusterProfile[],
              fdProfiles: fdProfilesData as unknown as Record<string, FDCandidateProfile>,
              senateVotes: senateVoteModelData as VoteModelRow[],
              houseStateMap: houseStateMapData as unknown as Record<string, HouseStateEntry>,
            }}
            primaryProps={{
              factorDev: fdPrimaryData as unknown as FDPrimaryData,
              factorDevStateWinners: fdPrimaryStateWinnersData as unknown as Record<string, PrimaryStateWinner>,
              factorDevStageShares: fdPrimaryStageSharesData as unknown as Record<string, PrimaryStageShares>,
              factorDevBuckets: fdPrimaryBucketsData,
              factorDevSankey: fdPrimarySankeyData as unknown as PrimarySankeyData,
              pureMulti: pureMultiPrimaryData as unknown as FDPrimaryData,
              pureMultiStateWinners: pureMultiPrimaryStateWinnersData as unknown as Record<string, PrimaryStateWinner>,
              pureMultiStageShares: pureMultiPrimaryStageSharesData as unknown as Record<string, PrimaryStageShares>,
              pureMultiSankey: pureMultiPrimarySankeyData as unknown as PrimarySankeyData,
              pureMultiBuckets: pureMultiPrimaryBucketsData,
              clusters: clusterProfilesData as ClusterProfile[],
              clusterSpreads: clusterSpreadsData as { party: string; n: number; [key: string]: string | number }[],
            }}
          />
        )}
        {tab === 'senate' && (
          <SenateTab
            condorcetFD={fdSenateCondorcetData as unknown as FDSenateSeat[]}
            irvFD={fdSenateIRVData as unknown as FDSenateSeat[]}
            condorcetRawMulti={pureMultiSenateCondorcetData as unknown as FDSenateSeat[]}
            irvRawMulti={pureMultiSenateIRVData as unknown as FDSenateSeat[]}
            condorcetRawMultiTurnout={pureMultiSenateCondorcetTurnoutData as unknown as FDSenateSeat[]}
            irvRawMultiTurnout={pureMultiSenateIRVTurnoutData as unknown as FDSenateSeat[]}
            voteModel={senateVoteModelData as VoteModelRow[]}
            clusters={clusterProfilesData as ClusterProfile[]}
            fdProfiles={fdProfilesData as unknown as Record<string, FDCandidateProfile>}
            clusterSpreads={clusterSpreadsData as { party: string; n: number; [key: string]: string | number }[]}
            houseTransfers={houseTransfersData as { source: string; totalVoters: number; destinations: { party: string; pct: number }[] }[]}
            fdVariantAttraction={fdVariantAttractionData as { variant: string; party: string; axis: string; direction: string; totalVoters: number; homePct: number; crossPct: number; sources: { party: string; pct: number }[] }[]}
            fdAttractionDrivers={fdAttractionDriversData as { variant: string; party: string; axis: string; direction: string; attracted: string; attractedPct: number; factors: { factor: string; pct: number }[] }[]}
            senateBuckets={senateBucketsData}
            senateCondorcet={senateCondorcetData}
          />
        )}
        {tab === 'house' && (
          <HouseTab
            seats={houseSeatsData as HouseSeat[]}
            seatsProbBased={houseSeatsProbBasedData as HouseSeat[]}
            coalitions={coalitionProfilesData as CoalitionProfile[]}
            transfers={transferMatrixData as unknown as TransferMatrix}
            voteModel={houseVoteModelData as VoteModelRow[]}
            stateMap={houseStateMapData as unknown as Record<string, HouseStateEntry>}
            clusters={clusterProfilesData as ClusterProfile[]}
            fdHouseSeats={fdHouseSeatsData as unknown as FDHouseSeat[]}
            fptpStates={fptpDisproportionalityData as FPTPState[]}
            countyTiers={countyTiersData as Record<string, string>}
            districtResults={districtStvResultsData as unknown as Record<string, DistrictResult[]>}
            districtCountyMap={districtCountyMapData as Record<string, string[]>}
            houseTransfers={houseTransfersData as { source: string; totalVoters: number; destinations: { party: string; pct: number }[] }[]}
            fdVariantAttraction={fdVariantAttractionData as { variant: string; party: string; axis: string; direction: string; totalVoters: number; homePct: number; crossPct: number; sources: { party: string; pct: number }[] }[]}
            fdCandidatePositions={fdCandidatePositionsData as { code: string; party: string; axis: string; direction: string; F1: number; F2: number; F3: number; F4: number; F5: number }[]}
            clusterSpreads={clusterSpreadsData as { party: string; n: number; [key: string]: string | number }[]}
            fdAttractionDrivers={fdAttractionDriversData as { variant: string; party: string; axis: string; direction: string; attracted: string; attractedPct: number; factors: { factor: string; pct: number }[] }[]}
            fdDistrictResults={fdDistrictStvResultsData as unknown as Record<string, DistrictResult[]>}
            seatsTriple={houseSeatsTripleData as HouseSeat[]}
            fdHouseSeatsTriple={fdHouseSeatsTripleData as unknown as FDHouseSeat[]}
            stateMapTriple={houseStateMapTripleData as unknown as Record<string, HouseStateEntry>}
            districtResultsTriple={districtStvResultsTripleData as unknown as Record<string, DistrictResult[]>}
            fdDistrictResultsTriple={fdDistrictStvResultsTripleData as unknown as Record<string, DistrictResult[]>}
            districtCountyMapTriple={districtCountyMapTripleData as Record<string, string[]>}
            seatsTurnout={houseSeatsTurnoutData as HouseSeat[]}
            stateMapTurnout={houseStateMapTurnoutData as unknown as Record<string, HouseStateEntry>}
            districtResultsTurnout={districtStvResultsTurnoutData as unknown as Record<string, DistrictResult[]>}
          />
        )}
        {tab === 'singleRace' && <SingleRaceTab />}
        {tab === 'rcv' && (
          <RCVTab
            data={rcvResultsData as unknown as RCVData}
            houseStateMap={houseStateMapData as unknown as Record<string, HouseStateEntry>}
          />
        )}
        {tab === 'legislation' && (
          <LegislationTab
            candidateVotes={candidateVoteModelData as unknown as CandidateVoteRow[]}
            houseVotes={houseVoteModelData as VoteModelRow[]}
            senateVotes={senateVoteModelData as VoteModelRow[]}
            fdElection={fdPresidentialElectionData as unknown as PresidentialElection}
            rawMultiElection={rawMultiPresidentialElectionData as unknown as PresidentialElection}
            houseVotesTurnout={houseVoteModelTurnoutData as VoteModelRow[]}
            senateVotesTurnout={senateVoteModelTurnoutData as VoteModelRow[]}
            rawMultiElectionTurnout={rawMultiPresidentialElectionTurnoutData as unknown as PresidentialElection}
          />
        )}
        {tab === 'parties' && (
          <PartiesTab
            clusters={clusterProfilesData as ClusterProfile[]}
            clusterSpreads={clusterSpreadsData as { party: string; n: number; [key: string]: string | number }[]}
            fdProfiles={fdProfilesData as unknown as Record<string, FDCandidateProfile>}
          />
        )}
        {tab === 'quiz' && (
          <QuizTab
            questions={quizQuestionsData as unknown as QuizQuestion[]}
            clusters={clusterProfilesData as ClusterProfile[]}
            houseSeats={houseSeatsData as HouseSeat[]}
            spreads={clusterSpreadsData as { party: string; n: number; [key: string]: string | number }[]}
          />
        )}
      </main>

      <footer className="border-t border-border mt-12 py-8 text-center text-xs text-muted-foreground">
        <SocialLinks />
        <p className="mt-4">
          Built by <span className="font-medium text-foreground">Brayden Decker</span>
          <span className="mx-2 text-slate-300">·</span>
          <a
            href="https://brayden-decker-contact.pages.dev/"
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-indigo-600 hover:underline"
          >
            Contact me ↗
          </a>
        </p>
        <p className="mt-1">
          Built on CES 2024 survey data · 10-party STV simulation · 873 / 1,726 House seats · 51 Senate seats
        </p>
      </footer>
    </div>
    </TooltipProvider>
  );
}
