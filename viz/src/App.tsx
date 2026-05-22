import { useState } from 'react';
import { PrimaryTab } from './tabs/PrimaryTab';
import { SenateTab } from './tabs/SenateTab';
import { HouseTab } from './tabs/HouseTab';
import { QuizTab } from './tabs/QuizTab';
import { PartiesTab } from './tabs/PartiesTab';
import { BlendedPartiesTab } from './tabs/BlendedPartiesTab';
import { PresidentialTab } from './tabs/PresidentialTab';
import { LegislationTab } from './tabs/LegislationTab';
import { CompareTab } from './tabs/CompareTab';
import { LightFusionTab } from './tabs/LightFusionTab';

import primaryData from './data/primary.json';
import primaryStateWinnersData from './data/primaryStateWinners.json';
import presidentialElectionData from './data/presidentialElection.json';
import presidentialElectionPureData from './data/presidentialElectionPure.json';
import presidentialElectionLightFusionData from './data/presidentialElectionLightFusion.json';
import primarySankeyData from './data/primarySankey.json';
import primaryRawData from './data/primaryRaw.json';
import primaryStateWinnersRawData from './data/primaryStateWinnersRaw.json';
import primarySankeyRawData from './data/primarySankeyRaw.json';
import primaryLightFusionData from './data/primaryLightFusion.json';
import primaryStateWinnersLightFusionData from './data/primaryStateWinnersLightFusion.json';
import primarySankeyLightFusionData from './data/primarySankeyLightFusion.json';
import senateCondorcetData from './data/senateCondorcet.json';
import senateIRVData from './data/senateIRV.json';
import senateCondorcetPureData from './data/senateCondorcetPure.json';
import senateIRVPureData from './data/senateIRVPure.json';
import senateCondorcetLightFusionData from './data/senateCondorcetLightFusion.json';
import senateIRVLightFusionData from './data/senateIRVLightFusion.json';
import senateVoteModelData from './data/senateVoteModel.json';
import houseSeatsData from './data/houseSeats.json';
import houseVoteModelData from './data/houseVoteModel.json';
import houseStateMapData from './data/houseStateMap.json';
import coalitionProfilesData from './data/coalitionProfiles.json';
import transferMatrixData from './data/transferMatrix.json';
import clusterProfilesData from './data/clusterProfiles.json';
import blendProfilesData from './data/blendProfiles.json';
import quizQuestionsData from './data/quizQuestions.json';

import type {
  PrimaryData, PrimaryStateWinner, SenateSeat, VoteModelRow, HouseSeat,
  HouseStateEntry, CoalitionProfile, TransferMatrix, ClusterProfile,
  QuizQuestion, BlendProfile, PresidentialElection,
  PrimarySankeyData,
} from './types';

const TABS = [
  { id: 'primary',        label: 'Presidential Primary' },
  { id: 'presidential',   label: 'Presidential General' },
  { id: 'senate',         label: 'Senate' },
  { id: 'house',          label: 'House' },
  { id: 'legislation',    label: 'Legislation' },
  { id: 'compare',        label: 'Compare' },
  { id: 'lightFusion',    label: 'Light Fusion' },
  { id: 'blends',         label: 'Blended Parties' },
  { id: 'parties',        label: 'Parties' },
  { id: 'quiz',           label: 'Who Are You?' },
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
            blended={primaryData as unknown as PrimaryData}
            blendedStateWinners={primaryStateWinnersData as unknown as Record<string, PrimaryStateWinner>}
            blendedSankey={primarySankeyData as unknown as PrimarySankeyData}
            raw={primaryRawData as unknown as PrimaryData}
            rawStateWinners={primaryStateWinnersRawData as unknown as Record<string, PrimaryStateWinner>}
            rawSankey={primarySankeyRawData as unknown as PrimarySankeyData}
            lightFusion={primaryLightFusionData as unknown as PrimaryData}
            lightFusionStateWinners={primaryStateWinnersLightFusionData as unknown as Record<string, PrimaryStateWinner>}
            lightFusionSankey={primarySankeyLightFusionData as unknown as PrimarySankeyData}
            blendProfiles={blendProfilesData as unknown as BlendProfile[]}
            clusters={clusterProfilesData as ClusterProfile[]}
          />
        )}
        {tab === 'presidential' && (
          <PresidentialTab
            mixed={presidentialElectionData as unknown as PresidentialElection}
            pure={presidentialElectionPureData as unknown as PresidentialElection}
            lightFusion={presidentialElectionLightFusionData as unknown as PresidentialElection}
            clusters={clusterProfilesData as ClusterProfile[]}
            blendProfiles={blendProfilesData as unknown as BlendProfile[]}
            senateVotes={senateVoteModelData as VoteModelRow[]}
          />
        )}
        {tab === 'senate' && (
          <SenateTab
            condorcetMixed={senateCondorcetData as SenateSeat[]}
            irvMixed={senateIRVData as SenateSeat[]}
            condorcetPure={senateCondorcetPureData as SenateSeat[]}
            irvPure={senateIRVPureData as SenateSeat[]}
            condorcetLightFusion={senateCondorcetLightFusionData as SenateSeat[]}
            irvLightFusion={senateIRVLightFusionData as SenateSeat[]}
            voteModel={senateVoteModelData as VoteModelRow[]}
            blendProfiles={blendProfilesData as unknown as BlendProfile[]}
          />
        )}
        {tab === 'house' && (
          <HouseTab
            seats={houseSeatsData as HouseSeat[]}
            coalitions={coalitionProfilesData as CoalitionProfile[]}
            transfers={transferMatrixData as unknown as TransferMatrix}
            voteModel={houseVoteModelData as VoteModelRow[]}
            stateMap={houseStateMapData as unknown as Record<string, HouseStateEntry>}
            clusters={clusterProfilesData as ClusterProfile[]}
          />
        )}
        {tab === 'legislation' && (
          <LegislationTab
            houseVotes={houseVoteModelData as VoteModelRow[]}
            senateVotes={senateVoteModelData as VoteModelRow[]}
          />
        )}
        {tab === 'compare' && (
          <CompareTab
            clusters={clusterProfilesData as ClusterProfile[]}
            blendProfiles={blendProfilesData as unknown as BlendProfile[]}
          />
        )}
        {tab === 'lightFusion' && (
          <LightFusionTab profiles={blendProfilesData as unknown as BlendProfile[]} />
        )}
        {tab === 'blends' && (
          <BlendedPartiesTab profiles={blendProfilesData as unknown as BlendProfile[]} />
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
        Built on CES 2024 survey data · 10-party STV simulation · 873 House seats · 50 Senate seats
      </footer>
    </div>
  );
}
