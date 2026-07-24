import type { ClusterProfile } from '../../types';
import { getBlendColor, FACTOR_POLES, DISPLAY_FACTORS } from '../../constants/parties';
import { bamForZ, bamForPctile, BAM_TEXT_LOW, BAM_TEXT_HIGH } from '../../lib/bam';
import { popShareLabel } from '../../lib/population';
import { Card } from '@/components/ui/card';

const FACTOR_SHORT_LABEL: Record<string, string> = {
  F1: 'Security',
  F2: 'Institutions',
  F3: 'Establishment',
  F4: 'Religion',
  F5: 'Conservatism',
};

const PARTY_BLURBS: Record<string, string> = {
  LBR: 'The center-left baseline. Working-class, racially diverse, moderate on tax policy, immigration enforcement, and abortion. Low political engagement.',
  LIB: 'The establishment center-left. Professional-class, educated, progressive on all policy dimensions, and strongly institutionalist. High political engagement, interventionist on foreign policy.',
  DSA: 'The anti-establishment far left. Youngest profile, urban-concentrated, culturally progressive, social libertarian. High institutional distrust, non-interventionist, universally pro-legalization for undocumented immigrants, opposes border patrols.',
  PRG: 'The establishment far left. Wealthy, highly educated, intensely pro-choice, and strongly institutionalist. Highest voter turnout of any party. Tied with NAT as the wealthiest profile.',
  OAO: 'The cross-cutting center. Oldest profile, economically progressive but strongly law-and-order. Supports raising taxes on the wealthy, increasing policing and border patrols, and granting legal status to Dreamers and undocumented immigrants.',
  STY: 'The disaffected center. Young, urban, most racially diverse, lowest income, lowest education. High institutional distrust, non-interventionist, pro-Medicaid, pro-debt-forgiveness, pro-legalization. Lowest voter turnout of any party.',
  CUP: 'The institutionalist center. Religious, law-and-order, pro-police, tough on borders, but economically progressive. The most institutionally trusting profile in the system.',
  CON: 'The pre-Trump Republican coalition. Law-and-order, low-tax, pro-police, pro-border-patrol. Trusts elections, backs universal background checks on firearms. Supports fossil fuel production, socially conservative on trans issues.',
  POP: 'The anti-establishment right. Nativist, economically conservative, isolationist, skeptical of government power. Majority opposed to increased police spending. Most racially diverse right-wing profile, highest homemaker population.',
  NAT: 'The far right. Anti-immigrant, high racial and gender resentment, anti-environmentalist, religiously fundamentalist. Opposes all legalization efforts including for Dreamers, supports heavy abortion restrictions. Rural-concentrated, wealthy, strongly pro-Israel.',
};

function zDescriptor(factor: string, z: number): string {
  const poles = FACTOR_POLES[factor];
  if (!poles) return '';
  const az = Math.abs(z);
  const direction = z >= 0 ? poles.high : poles.low;
  if (az < 0.5) return 'Mixed';
  if (az < 1.0) return `Leans ${direction.toLowerCase()}`;
  if (az < 1.5) return `Moderately ${direction.toLowerCase()}`;
  if (az < 2.0) return `Strongly ${direction.toLowerCase()}`;
  return `Very strongly ${direction.toLowerCase()}`;
}

function pctileDescriptor(factor: string, pctile: number): string {
  const poles = FACTOR_POLES[factor];
  if (!poles) return '';
  const isHigh = pctile >= 50;
  const pole = isHigh ? poles.high : poles.low;
  const magnitude = isHigh ? pctile : 100 - pctile;
  return `More ${pole.toLowerCase()} than ${Math.round(magnitude)}%`;
}

interface Props {
  cluster: ClusterProfile;
  mode?: 'strength' | 'percentile';
}

export function PartyProfileCard({ cluster, mode = 'strength' }: Props) {
  const color = getBlendColor(cluster.party);
  return (
    <Card className="overflow-hidden" style={{ borderColor: color + '55' }}>
      <div className="px-4 py-3 flex items-center justify-between" style={{ backgroundColor: color + '18' }}>
        <div>
          <span className="text-xs font-bold font-mono" style={{ color }}>{cluster.party}</span>
          <div className="text-sm font-semibold text-foreground">{cluster.partyName}</div>
        </div>
        <span className="text-xs text-muted-foreground" title="share of the adult population">{popShareLabel(cluster.party)}</span>
      </div>
      <div className="px-4 py-3 space-y-2">
        {DISPLAY_FACTORS.map(f => {
          const z = (cluster as unknown as Record<string, number>)[`z_${f}`];
          const pctile = (cluster as unknown as Record<string, number>)[`pctile_${f}`];
          if (z == null) return null;
          const label = FACTOR_SHORT_LABEL[f];

          if (mode === 'percentile' && pctile != null) {
            const isHigh = pctile >= 50;
            const fill = bamForPctile(pctile);
            const textColor = isHigh ? BAM_TEXT_HIGH : BAM_TEXT_LOW;
            const desc = pctileDescriptor(f, pctile);

            return (
              <div key={f}>
                <div className="flex items-center justify-between text-xs gap-2 mb-0.5">
                  <span className="text-muted-foreground shrink-0">{label}</span>
                  <span className="font-medium" style={{ color: textColor }}>{desc}</span>
                </div>
                {/* 0-100 bar, bam-colored: magenta at low pole → teal at high pole */}
                <div className="relative h-2 bg-muted rounded-full overflow-hidden">
                  {isHigh ? (
                    <div className="absolute top-0 left-0 h-full rounded-l-full"
                      style={{ width: `${pctile}%`, backgroundColor: fill }} />
                  ) : (
                    <div className="absolute top-0 right-0 h-full rounded-r-full"
                      style={{ width: `${100 - pctile}%`, backgroundColor: fill }} />
                  )}
                  {/* Median marker at 50% */}
                  <div className="absolute top-0 left-1/2 w-px h-full bg-slate-400" />
                </div>
              </div>
            );
          }

          // Strength mode (default)
          const desc = zDescriptor(f, z);
          const isHigh = z >= 0;
          const fill = bamForZ(z);
          const textColor = desc === 'Mixed' ? '#6b7280' : (isHigh ? BAM_TEXT_HIGH : BAM_TEXT_LOW);
          const barPct = Math.min(Math.abs(z) / 2.5 * 50, 50);
          return (
            <div key={f}>
              <div className="flex items-center justify-between text-xs gap-2 mb-0.5">
                <span className="text-muted-foreground shrink-0">{label}</span>
                <span className="font-medium" style={{ color: textColor }}>{desc}</span>
              </div>
              <div className="relative h-2 bg-muted rounded-full overflow-hidden">
                {isHigh ? (
                  <div className="absolute top-0 h-full rounded-r-full"
                    style={{ left: '50%', width: `${barPct}%`, backgroundColor: fill }} />
                ) : (
                  <div className="absolute top-0 h-full rounded-l-full"
                    style={{ left: `${50 - barPct}%`, width: `${barPct}%`, backgroundColor: fill }} />
                )}
                <div className="absolute top-0 left-1/2 w-px h-full bg-slate-400" />
              </div>
            </div>
          );
        })}
      </div>
      {PARTY_BLURBS[cluster.party] && (
        <div className="px-4 pb-3 pt-1 border-t border-border/40">
          <p className="text-[11px] leading-relaxed text-muted-foreground">{PARTY_BLURBS[cluster.party]}</p>
        </div>
      )}
    </Card>
  );
}
