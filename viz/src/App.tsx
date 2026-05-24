import { useState } from 'react';
import { PrimaryTab } from './tabs/PrimaryTab';
import { SenateTab } from './tabs/SenateTab';
import { HouseTab } from './tabs/HouseTab';
import { QuizTab } from './tabs/QuizTab';
import { PartiesTab } from './tabs/PartiesTab';
import { PresidentialTab } from './tabs/PresidentialTab';
import { LegislationTab } from './tabs/LegislationTab';
import { CompareTab } from './tabs/CompareTab';

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

import type {
  PrimaryStateWinner, VoteModelRow, HouseSeat,
  HouseStateEntry, CoalitionProfile, TransferMatrix, ClusterProfile,
  QuizQuestion, PresidentialElection,
  PrimarySankeyData,
  FDSenateSeat, FDHouseSeat, FDPrimaryData, FDCandidateProfile,
} from './types';

const TABS = [
  { id: 'primary',      label: 'Presidential Primary' },
  { id: 'presidential', label: 'Presidential General' },
  { id: 'senate',       label: 'Senate' },
  { id: 'house',        label: 'House' },
  { id: 'legislation',  label: 'Legislation' },
  { id: 'compare',      label: 'Compare' },
  { id: 'parties',      label: 'Parties' },
  { id: 'quiz',         label: 'Who Are You?' },
] as const;

type TabId = typeof TABS[number]['id'];

export default function App() {
  const [tab, setTab] = useState<TabId>('primary');

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="border-b border-slate-200 bg-white/90 backdrop-blur sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center gap-3 mb-3">
            <div className="text-xl font-bold text-slate-900">STV 2028</div>
            <div className="text-sm text-slate-500">Proportional Democracy Simulation</div>
          </div>
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
        {tab === 'primary' && (
          <PrimaryTab
            factorDev={fdPrimaryData as unknown as FDPrimaryData}
            factorDevStateWinners={fdPrimaryStateWinnersData as unknown as Record<string, PrimaryStateWinner>}
            factorDevSankey={fdPrimarySankeyData as unknown as PrimarySankeyData}
            pureMulti={pureMultiPrimaryData as unknown as FDPrimaryData}
            pureMultiStateWinners={pureMultiPrimaryStateWinnersData as unknown as Record<string, PrimaryStateWinner>}
            pureMultiSankey={pureMultiPrimarySankeyData as unknown as PrimarySankeyData}
            clusters={clusterProfilesData as ClusterProfile[]}
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
        {tab === 'compare' && (
          <CompareTab
            clusters={clusterProfilesData as ClusterProfile[]}
            fdProfiles={fdProfilesData as unknown as Record<string, FDCandidateProfile>}
          />
        )}
        {tab === 'parties' && (
          <PartiesTab clusters={clusterProfilesData as ClusterProfile[]} />
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
