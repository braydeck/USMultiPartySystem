import { useState } from 'react';
import { PrimaryTab } from './tabs/PrimaryTab';
import { SenateTab } from './tabs/SenateTab';
import { HouseTab } from './tabs/HouseTab';
import { QuizTab } from './tabs/QuizTab';
import { PartiesTab } from './tabs/PartiesTab';
import { PresidentialTab } from './tabs/PresidentialTab';
import { LegislationTab } from './tabs/LegislationTab';
import { CompareTab } from './tabs/CompareTab';
import { AboutTab } from './tabs/AboutTab';
import { OverviewTab } from './tabs/OverviewTab';
import { RCVTab } from './tabs/RCVTab';

import senateVoteModelData from './data/senateVoteModel.json';
import houseSeatsData from './data/houseSeats.json';
import houseSeatsProbBasedData from './data/houseSeatsProbBased.json';
import houseVoteModelData from './data/houseVoteModel.json';
import houseStateMapData from './data/houseStateMap.json';
import coalitionProfilesData from './data/coalitionProfiles.json';
import transferMatrixData from './data/transferMatrix.json';
import clusterProfilesData from './data/clusterProfiles.json';
import quizQuestionsData from './data/quizQuestions.json';
import fdSenateCondorcetData from './data/fdSenateCondorcet.json';
import fdSenateIRVData from './data/fdSenateIRV.json';
import pureMultiSenateCondorcetData from './data/pureMultiSenateCondorcet.json';
import pureMultiSenateIRVData from './data/pureMultiSenateIRV.json';
import senateBucketsData from './data/senateBuckets.json';
import senateCondorcetData from './data/senateCondorcet.json';
import fdHouseSeatsData from './data/fdHouseSeats.json';
import fdPrimaryData from './data/fdPrimary.json';
import fdPrimaryStateWinnersData from './data/fdPrimaryStateWinners.json';
import fdPrimarySankeyData from './data/fdPrimarySankey.json';
import fdPresidentialElectionData from './data/fdPresidentialElection.json';
import rawMultiPresidentialElectionData from './data/rawMultiPresidentialElection.json';
import fdProfilesData from './data/fdProfiles.json';
import pureMultiPrimaryData from './data/pureMultiPrimary.json';
import pureMultiPrimaryStateWinnersData from './data/pureMultiPrimaryStateWinners.json';
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

import type {
  PrimaryStateWinner, VoteModelRow, HouseSeat,
  HouseStateEntry, CoalitionProfile, TransferMatrix, ClusterProfile,
  QuizQuestion, PresidentialElection,
  PrimarySankeyData,
  FDSenateSeat, FDHouseSeat, FDPrimaryData, FDCandidateProfile, FPTPState,
  DistrictResult, RCVData,
} from './types';

const TABS = [
  { id: 'about',        label: 'What Is This?' },
  { id: 'overview',     label: 'Overview' },
  { id: 'primary',      label: 'Presidential Primary' },
  { id: 'presidential', label: 'Presidential General' },
  { id: 'senate',       label: 'Senate' },
  { id: 'house',        label: 'House' },
  { id: 'rcv',          label: 'RCV Case Studies' },
  { id: 'legislation',  label: 'Legislation' },
  { id: 'parties',      label: 'Parties' },
  { id: 'quiz',         label: 'Who Are You?' },
] as const;

type TabId = typeof TABS[number]['id'];

export default function App() {
  const [tab, setTab] = useState<TabId>('about');

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      {/* Title — scrolls away */}
      <div className="border-b border-slate-100 bg-white">
        <div className="max-w-7xl mx-auto px-4 pt-3 pb-2 flex items-center gap-3">
          <div className="text-xl font-bold text-slate-900">STV 2028</div>
          <div className="text-sm text-slate-500">Proportional Democracy Simulation</div>
        </div>
      </div>
      {/* Nav tabs — sticky */}
      <header className="border-b border-slate-200 bg-white/95 backdrop-blur sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 py-1.5">
          <div className="relative">
            <nav className="flex gap-1 overflow-x-auto pb-px">
              {TABS.map(t => (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={`px-4 py-1.5 rounded text-sm font-medium whitespace-nowrap transition-colors ${
                    tab === t.id
                      ? 'bg-slate-200 text-slate-900'
                      : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </nav>
            <div className="pointer-events-none absolute right-0 top-0 h-full w-8 bg-gradient-to-l from-white" />
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {tab === 'about' && <AboutTab />}
        {tab === 'overview' && (
          <OverviewTab
            fdElection={fdPresidentialElectionData as unknown as PresidentialElection}
            rawMultiElection={rawMultiPresidentialElectionData as unknown as PresidentialElection}
            rawMultiSenateCond={pureMultiSenateCondorcetData as unknown as FDSenateSeat[]}
            rawMultiSenateIRV={pureMultiSenateIRVData as unknown as FDSenateSeat[]}
            fdSenateCond={fdSenateCondorcetData as unknown as FDSenateSeat[]}
            fdSenateIRV={fdSenateIRVData as unknown as FDSenateSeat[]}
            houseSeats={houseSeatsData as HouseSeat[]}
            senateVotes={senateVoteModelData as VoteModelRow[]}
            houseVotes={houseVoteModelData as VoteModelRow[]}
            clusters={clusterProfilesData as ClusterProfile[]}
            fdProfiles={fdProfilesData as unknown as Record<string, FDCandidateProfile>}
            fptpStates={fptpDisproportionalityData as FPTPState[]}
            stateMap={houseStateMapData as unknown as Record<string, HouseStateEntry>}
            clusterSpreads={clusterSpreadsData as { party: string; n: number; [key: string]: string | number }[]}
          />
        )}
        {tab === 'primary' && (
          <PrimaryTab
            factorDev={fdPrimaryData as unknown as FDPrimaryData}
            factorDevStateWinners={fdPrimaryStateWinnersData as unknown as Record<string, PrimaryStateWinner>}
            factorDevSankey={fdPrimarySankeyData as unknown as PrimarySankeyData}
            pureMulti={pureMultiPrimaryData as unknown as FDPrimaryData}
            pureMultiStateWinners={pureMultiPrimaryStateWinnersData as unknown as Record<string, PrimaryStateWinner>}
            pureMultiSankey={pureMultiPrimarySankeyData as unknown as PrimarySankeyData}
            pureMultiBuckets={pureMultiPrimaryBucketsData}
            clusters={clusterProfilesData as ClusterProfile[]}
            clusterSpreads={clusterSpreadsData as { party: string; n: number; [key: string]: string | number }[]}
          />
        )}
        {tab === 'presidential' && (
          <PresidentialTab
            factorDev={fdPresidentialElectionData as unknown as PresidentialElection}
            rawMulti={rawMultiPresidentialElectionData as unknown as PresidentialElection}
            clusters={clusterProfilesData as ClusterProfile[]}
            fdProfiles={fdProfilesData as unknown as Record<string, FDCandidateProfile>}
            senateVotes={senateVoteModelData as VoteModelRow[]}
          />
        )}
        {tab === 'senate' && (
          <SenateTab
            condorcetFD={fdSenateCondorcetData as unknown as FDSenateSeat[]}
            irvFD={fdSenateIRVData as unknown as FDSenateSeat[]}
            condorcetRawMulti={pureMultiSenateCondorcetData as unknown as FDSenateSeat[]}
            irvRawMulti={pureMultiSenateIRVData as unknown as FDSenateSeat[]}
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
          />
        )}
        {tab === 'rcv' && (
          <RCVTab
            data={rcvResultsData as unknown as RCVData}
            houseStateMap={houseStateMapData as unknown as Record<string, HouseStateEntry>}
          />
        )}
        {tab === 'legislation' && (
          <LegislationTab
            houseVotes={houseVoteModelData as VoteModelRow[]}
            senateVotes={senateVoteModelData as VoteModelRow[]}
            fdElection={fdPresidentialElectionData as unknown as PresidentialElection}
            rawMultiElection={rawMultiPresidentialElectionData as unknown as PresidentialElection}
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
            questions={quizQuestionsData as QuizQuestion[]}
            clusters={clusterProfilesData as ClusterProfile[]}
            houseVotes={houseVoteModelData as VoteModelRow[]}
          />
        )}
      </main>

      <footer className="border-t border-slate-200 mt-12 py-6 text-center text-xs text-slate-500">
        Built on CES 2024 survey data · 10-party STV simulation · 873 House seats · 51 Senate seats
      </footer>
    </div>
  );
}
