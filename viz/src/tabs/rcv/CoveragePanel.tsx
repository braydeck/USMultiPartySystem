import type { RCVRace } from '../../types';
import { CollapsibleSection } from '../../components/shared/CollapsibleSection';
import { CARD_HINT, MINOR_HEADING, TABLE_HEADER, FOOTNOTE } from '../../constants/typography';
import { partyColor } from './ballotParties';
import { COVERAGE, STATUS_LABEL, type CellStatus, type CoverageCell, type CoverageRow } from './coverage';

/**
 * Every contest RCV has governed in one state, as a year × office grid.
 *
 * Folded away by default. The grid answers "did we miss anything", which is a
 * question a reader asks once; leaving it open put a dense audit table between the
 * title and the races it is auditing. The contests that actually went to transfers
 * are named on the summary card above instead, where they are one click from the
 * race itself.
 */

const SOLID = '#1d4ed8';

function statusStyle(status: CellStatus): React.CSSProperties {
  switch (status) {
    case 'RANKED':
      return { background: SOLID, borderColor: SOLID };
    case 'FIRST_ROUND':
      return { background: '#e8edf7', borderColor: '#c3cfe6' };
    case 'NOT_RCV':
      return {
        borderColor: '#dcdfe4',
        backgroundImage:
          'repeating-linear-gradient(45deg, #eef0f3 0 3px, #ffffff 3px 6px)',
      };
    default:
      return { background: 'transparent', borderColor: 'transparent' };
  }
}

function CoverageCellBox({
  cell, race, onSelect,
}: {
  cell: CoverageCell;
  race?: RCVRace;
  onSelect?: (race: RCVRace) => void;
}) {
  const { status } = cell;
  if (status === 'NO_ELECTION') {
    return <div className="h-9 rounded flex items-center justify-center text-muted-foreground/40 text-xs">·</div>;
  }

  const rounds = race?.irvRounds.length ?? 0;
  const winner = race?.irvWinner ?? cell.winner;
  const party = race ? race.parties[race.irvWinner] : cell.party;
  const pct = race ? race.irvRounds[0].pcts[race.pluralityWinner] : cell.pct;

  const tooltip = [
    STATUS_LABEL[status],
    winner ? `${winner}${party ? ` (${party})` : ''}` : null,
    pct != null ? `${pct.toFixed(1)}% first choices` : null,
    status === 'RANKED' ? `${rounds} rounds` : null,
  ].filter(Boolean).join(' · ');

  const inner =
    status === 'RANKED' ? (
      <>
        <span className="text-2xs font-bold text-white tabular-nums leading-none">{rounds}</span>
        <span className="text-4xs text-white/75 uppercase leading-none mt-0.5">rounds</span>
      </>
    ) : status === 'FIRST_ROUND' ? (
      // One decimal: several of these won by a fraction of a point over 50, and a
      // rounded "50%" reads as a tie rather than as a majority.
      <span className="text-2xs font-semibold text-slate-500 tabular-nums leading-none">
        {pct != null ? `${pct.toFixed(1)}%` : 'R1'}
      </span>
    ) : null;

  const box = (
    <div
      className="h-9 rounded border flex flex-col items-center justify-center"
      style={statusStyle(status)}
      title={tooltip}
    >
      {inner}
      {party && status !== 'NOT_RCV' && (
        <span
          className="absolute bottom-0 left-0 right-0 h-[3px] rounded-b"
          style={{ backgroundColor: partyColor(party) }}
        />
      )}
    </div>
  );

  if (status === 'RANKED' && race && onSelect) {
    return (
      <button
        className="relative block w-full focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
        onClick={() => onSelect(race)}
        title={`${tooltip} — open this race`}
      >
        {box}
      </button>
    );
  }
  return <div className="relative">{box}</div>;
}

function Grid({
  rows, years, races, onSelect,
}: {
  rows: CoverageRow[];
  years: number[];
  races: RCVRace[];
  onSelect: (race: RCVRace) => void;
}) {
  // Year columns are capped so the cells stay chip-sized: at two columns (Alaska) a
  // 1fr track stretches each cell into a full-width bar and the grid stops reading
  // as a grid.
  const template = `minmax(7.5rem, 9rem) repeat(${years.length}, minmax(2.75rem, 4rem))`;
  return (
    <div className="overflow-x-auto">
      <div className="min-w-[20rem] w-fit space-y-1">
        <div className="grid gap-1 items-end" style={{ gridTemplateColumns: template }}>
          <div />
          {years.map(y => (
            <div key={y} className={`${TABLE_HEADER} text-center tabular-nums`}>{y}</div>
          ))}
        </div>
        {rows.map(row => (
          <div key={row.office} className="grid gap-1 items-center" style={{ gridTemplateColumns: template }}>
            <div className="text-2xs text-foreground/80 truncate pr-1" title={row.office}>{row.office}</div>
            {years.map(y => {
              const cell = row.years[y] ?? { status: 'NO_ELECTION' as CellStatus };
              const race = cell.race
                ? races.find(r => r.year === y && r.raceName === cell.race)
                : undefined;
              return (
                <CoverageCellBox key={y} cell={cell} race={race} onSelect={onSelect} />
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

function LegendKey({ status, label }: { status: CellStatus; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="w-4 h-3.5 rounded border inline-block" style={statusStyle(status)} />
      <span className={FOOTNOTE}>{label}</span>
    </span>
  );
}

export function CoveragePanel({
  stateAbbr, races, onSelect,
}: {
  stateAbbr: 'AK' | 'ME';
  races: RCVRace[];
  onSelect: (race: RCVRace) => void;
}) {
  const cov = COVERAGE[stateAbbr];
  const governed = [...cov.generals, ...cov.primaries]
    .flatMap(r => Object.values(r.years))
    .filter(c => c.status === 'RANKED' || c.status === 'FIRST_ROUND').length;

  return (
    <CollapsibleSection
      id="rcvCoverage"
      title="Every contest ranked ballots have governed"
      hint={`${governed} in ${stateAbbr === 'AK' ? 'Alaska' : 'Maine'} · ${cov.adopted}`}
    >
      <div className="space-y-4">
        <p className="text-sm text-foreground/85 leading-snug">{cov.scope}.</p>

        <div className="space-y-3">
          <div>
            <h5 className={`${MINOR_HEADING} mb-1.5`}>General elections</h5>
            <Grid rows={cov.generals} years={cov.years} races={races} onSelect={onSelect} />
          </div>
          {cov.primaries.length > 0 && (
            <div>
              <h5 className={`${MINOR_HEADING} mb-1.5`}>Primaries</h5>
              <Grid rows={cov.primaries} years={cov.years} races={races} onSelect={onSelect} />
            </div>
          )}
        </div>

        <div className="flex flex-wrap gap-x-4 gap-y-1.5 pt-1 border-t border-border/50">
          <LegendKey status="RANKED" label="Went to transfers — click to jump to it" />
          <LegendKey status="FIRST_ROUND" label="First-choice majority ended it" />
          {stateAbbr === 'ME' && <LegendKey status="NOT_RCV" label="Plurality, not ranked" />}
          <span className={FOOTNOTE}>Colour bar = winner&apos;s party</span>
        </div>

        {cov.excluded && <p className={CARD_HINT}>{cov.excluded}</p>}
        {cov.alsoRanked && <p className={FOOTNOTE}>{cov.alsoRanked}</p>}
      </div>
    </CollapsibleSection>
  );
}
