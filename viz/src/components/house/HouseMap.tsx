import { useMemo } from 'react';
import type { DistrictResult } from '../../types';
import { HexCartogram } from './HexCartogram';
import { StateSelect, US_STATES } from './StateDrilldown';

interface Props {
  districtResults: Record<string, DistrictResult[]>;
  wyoming: 'double' | 'triple';
  /** state FIPS, or 'national' for the whole map */
  selectedFips: string;
  onSelectFips: (fips: string) => void;
  /** parties to keep lit, owned by the parent so the grid shares the same selection */
  highlight: ReadonlySet<string>;
}

export function HouseMap({ districtResults, wyoming, selectedFips, onSelectFips, highlight }: Props) {
  const abbrToFips = useMemo(
    () => Object.fromEntries(US_STATES.map(s => [s.abbr, s.fips])), [],
  );
  const stateEntry = US_STATES.find(s => s.fips === selectedFips);

  return (
    <HexCartogram
        wyoming={wyoming}
        districtResults={districtResults}
        highlight={highlight}
        selected={stateEntry?.abbr ?? null}
        toolbar={<StateSelect value={selectedFips} onChange={onSelectFips} />}
        onSelectState={abbr => onSelectFips(
          abbrToFips[abbr] === selectedFips ? 'national' : (abbrToFips[abbr] ?? 'national'),
        )}
        footnote={
          <>One hexagon cluster is one seat, states sized by population. Heavy outlines separate districts. Click a state
          to zoom, click it again to zoom back out.</>
        }
      />
  );
}
