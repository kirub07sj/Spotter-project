import { create } from 'zustand';

export type HeatmapStatus = 'idle' | 'loading' | 'rendering' | 'ready' | 'error';

/** Bitmaps live outside React state that changes often: the array is mutated in place and
 * `version` is bumped at most once per animation frame (map-performance skill). */
export interface HeatmapState {
  planId: string | null;
  status: HeatmapStatus;
  bounds: [number, number, number, number] | null;
  /** grid hour 0 is floor(departure); offset of departure into that hour, in hours */
  departureOffsetH: number;
  bitmaps: (ImageBitmap | undefined)[];
  ready: number;
  version: number;
  renderMs: number | null;
  error: string | null;
  retry: (() => void) | null;
}

export const useHeatmapStore = create<HeatmapState>()(() => ({
  planId: null,
  status: 'idle',
  bounds: null,
  departureOffsetH: 0,
  bitmaps: [],
  ready: 0,
  version: 0,
  renderMs: null,
  error: null,
  retry: null,
}));

export function resetHeatmap(planId: string | null, status: HeatmapStatus) {
  const old = useHeatmapStore.getState().bitmaps;
  for (const b of old) b?.close(); // release GPU-side memory of the previous plan
  useHeatmapStore.setState({
    planId,
    status,
    bounds: null,
    bitmaps: [],
    ready: 0,
    version: useHeatmapStore.getState().version + 1,
    renderMs: null,
    error: null,
  });
}

/** Nearest available bitmap to `index` (docs/04 §6 step 6). */
export function nearestBitmap(bitmaps: (ImageBitmap | undefined)[], index: number) {
  if (bitmaps[index]) return bitmaps[index];
  for (let d = 1; d < bitmaps.length; d++) {
    const b = bitmaps[index - d] ?? bitmaps[index + d];
    if (b) return b;
  }
  return undefined;
}
