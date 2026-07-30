// The participation stop the app opens on, in one place. Overview is pinned to this stop's
// data while the Senate tab derives its default from it, so if the two resolved it
// independently they could silently report different chambers for the same election.
import { GAP_STOPS } from '../components/shared/ParticipationSlider';

export const DEFAULT_GAP_STOP = 5;
export const DEFAULT_STOP_INDEX = GAP_STOPS.indexOf(DEFAULT_GAP_STOP);
