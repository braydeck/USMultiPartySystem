import type { ComponentProps } from 'react';
import { useUrlState } from '../hooks/useUrlState';
import { PrimaryTab } from './PrimaryTab';
import { PresidentialTab } from './PresidentialTab';
import { ToggleGroup } from '../components/shared/ToggleGroup';

type View = 'general' | 'primary';

interface Props {
  generalProps: Omit<ComponentProps<typeof PresidentialTab>, 'controlBarExtra'>;
  primaryProps: Omit<ComponentProps<typeof PrimaryTab>, 'controlBarExtra'>;
}

/** Unified Presidency scenario: a General/Primary view toggle (default General) injected
 * into the active child tab's sticky control bar, so View and Scenario sit on one bar. */
export function PresidencyTab({ generalProps, primaryProps }: Props) {
  const [view, setView] = useUrlState<View>('view', 'general', { allowed: ['general', 'primary'] });

  const viewToggle = (
    <ToggleGroup
      label="View"
      value={view}
      onChange={setView}
      options={['general', 'primary'] as const}
      labels={{ general: 'General', primary: 'Primary' }}
    />
  );

  return view === 'general'
    ? <PresidentialTab {...generalProps} controlBarExtra={viewToggle} />
    : <PrimaryTab {...primaryProps} controlBarExtra={viewToggle} />;
}
