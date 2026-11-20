import { render } from '@testing-library/react';
import { planOk } from '../../test/plans';
import { HeatmapController } from './HeatmapController';
import type { FromWorker } from './protocol';
import { useHeatmapStore } from './store';

const data = {
  grid: { lat0: 40, lon0: -110, dlat: 1, dlon: 1, rows: 1, cols: 1 },
  hours: [planOk.assumptions.departure_time],
  scores: 'AA==',
  mask: 'AQ==',
};
vi.mock('../../api/hooks', () => ({
  useHeatmap: () => ({ data, isError: false, refetch: vi.fn() }),
}));

const workers: MockWorker[] = [];
const frames: FrameRequestCallback[] = [];
class MockWorker {
  onmessage: ((event: MessageEvent<FromWorker>) => void) | null = null;
  postMessage = vi.fn();
  terminate = vi.fn();
  constructor() {
    workers.push(this);
  }
  send(message: FromWorker) {
    this.onmessage?.({ data: message } as MessageEvent<FromWorker>);
  }
}

beforeEach(() => {
  workers.length = frames.length = 0;
  useHeatmapStore.setState({ planId: null, bitmaps: [], status: 'idle' });
  vi.stubGlobal('Worker', MockWorker);
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => frames.push(callback));
  vi.stubGlobal('cancelAnimationFrame', vi.fn());
});
afterEach(() => vi.unstubAllGlobals());

it('closes bitmaps still waiting for a frame when a plan is replaced', () => {
  const close = vi.fn();
  const { unmount } = render(<HeatmapController plan={planOk} />);
  const worker = workers[0];
  if (!worker) throw new Error('Worker not created');
  worker.send({
    type: 'bitmap',
    planId: planOk.plan_id,
    hour: 0,
    bitmap: { close } as unknown as ImageBitmap,
  });
  unmount();
  expect(close).toHaveBeenCalledOnce();
  expect(worker.terminate).toHaveBeenCalledOnce();
});

it('ignores a queued completion from a replaced plan', () => {
  const { unmount } = render(<HeatmapController plan={planOk} />);
  workers[0]?.send({ type: 'done', planId: planOk.plan_id, ms: 10 });
  unmount();
  useHeatmapStore.setState({ planId: 'replacement', status: 'loading' });
  frames[0]?.(0);
  expect(useHeatmapStore.getState().status).toBe('loading');
});
