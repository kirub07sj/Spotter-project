import { create } from 'zustand';
import type { PlanInputs } from '../api/hooks';
import type { RouteId } from '../api/types';

/** UI state only; server state lives in TanStack Query. Components subscribe with narrow
 * selectors so a slider drag only re-renders the slider and the map (docs/04 §7). */
export interface UiState {
  submitted: PlanInputs | null;
  selectedRouteId: RouteId | null;
  hoveredRouteId: RouteId | null;
  hoveredCheckpoint: number | null;
  hour: number;
  playing: boolean;
  heatmapVisible: boolean;
  heatmapOpacity: number;
  showAllRoutes: boolean;
  showCheckpoints: boolean;
  theme: 'dark' | 'light';
  submit: (inputs: PlanInputs) => void;
  selectRoute: (id: RouteId | null) => void;
  hoverRoute: (id: RouteId | null) => void;
  hoverCheckpoint: (index: number | null) => void;
  setHour: (hour: number) => void;
  setPlaying: (playing: boolean) => void;
  toggleTheme: () => void;
  setLayer: (
    patch: Partial<
      Pick<UiState, 'heatmapVisible' | 'heatmapOpacity' | 'showAllRoutes' | 'showCheckpoints'>
    >,
  ) => void;
}

export const MAX_HOUR = 48;

const initialTheme: 'dark' | 'light' =
  typeof window !== 'undefined' && localStorage.getItem('spotter_theme') === 'light'
    ? 'light'
    : 'dark';

export const useUi = create<UiState>()((set) => ({
  submitted: null,
  selectedRouteId: null,
  hoveredRouteId: null,
  hoveredCheckpoint: null,
  hour: 0,
  playing: false,
  heatmapVisible: true,
  heatmapOpacity: 0.85,
  showAllRoutes: true,
  showCheckpoints: true,
  theme: initialTheme,
  submit: (inputs) =>
    set({
      submitted: inputs,
      selectedRouteId: null,
      hour: 0,
      playing: false,
      hoveredCheckpoint: null,
    }),
  selectRoute: (id) => set({ selectedRouteId: id, hoveredCheckpoint: null }),
  hoverRoute: (id) => set({ hoveredRouteId: id }),
  hoverCheckpoint: (index) => set({ hoveredCheckpoint: index }),
  setHour: (hour) => set({ hour: Math.min(Math.max(hour, 0), MAX_HOUR) }),
  setPlaying: (playing) => set({ playing }),
  toggleTheme: () =>
    set((state) => {
      const next = state.theme === 'dark' ? 'light' : 'dark';
      if (typeof window !== 'undefined') localStorage.setItem('spotter_theme', next);
      return { theme: next };
    }),
  setLayer: (patch) => set(patch),
}));
