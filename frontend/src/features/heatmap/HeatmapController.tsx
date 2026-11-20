import { useEffect } from 'react';
import { useHeatmap } from '../../api/hooks';
import type { Plan } from '../../api/types';
import { useUi } from '../../store/ui';
import type { FromWorker, ToWorker } from './protocol';
import { base64ToBuffer, rasterBounds, rasterSize } from './raster';
import { resetHeatmap, useHeatmapStore } from './store';

/** Fetches the heatmap for a plan and drives the worker. Renders nothing. */
export function HeatmapController({ plan }: { plan: Plan | undefined }) {
  const query = useHeatmap(plan);
  const planId = plan?.plan_id ?? null;

  useEffect(() => {
    resetHeatmap(planId, planId ? 'loading' : 'idle');
  }, [planId]);

  const { refetch } = query;
  useEffect(() => {
    if (query.isError && planId) {
      useHeatmapStore.setState({
        status: 'error',
        error: 'Weather heatmap unavailable',
        retry: () => {
          useHeatmapStore.setState({ status: 'loading', error: null, retry: null });
          void refetch();
        },
      });
    }
  }, [query.isError, planId, refetch]);

  const data = query.data;
  useEffect(() => {
    if (!data || !planId || !plan) return;
    const grid = data.grid;
    const departure = new Date(plan.assumptions.departure_time).getTime();
    const start = new Date(data.hours[0] ?? plan.assumptions.departure_time).getTime();
    const departureOffsetH = (departure - start) / 3_600_000;
    resetHeatmap(planId, 'rendering');
    useHeatmapStore.setState({ bounds: rasterBounds(grid), departureOffsetH });

    const worker = new Worker(new URL('./heatmap.worker.ts', import.meta.url), { type: 'module' });
    const pending: { hour: number; bitmap: ImageBitmap }[] = [];
    let frame = 0;
    let completionFrame = 0;
    let active = true;
    const flush = () => {
      frame = 0;
      const s = useHeatmapStore.getState();
      if (s.planId !== planId) return pending.forEach((p) => p.bitmap.close());
      for (const p of pending) s.bitmaps[p.hour] = p.bitmap;
      useHeatmapStore.setState({ ready: s.ready + pending.length, version: s.version + 1 });
      pending.length = 0;
    };
    worker.onmessage = (event: MessageEvent<FromWorker>) => {
      const msg = event.data;
      if (!active || msg.planId !== planId) {
        if (msg.type === 'bitmap') msg.bitmap.close();
        return;
      }
      if (msg.type === 'bitmap') {
        pending.push({ hour: msg.hour, bitmap: msg.bitmap });
        frame ||= requestAnimationFrame(flush); // one store update per frame, not per bitmap
      } else if (msg.type === 'done') {
        completionFrame = requestAnimationFrame(() => {
          if (active && useHeatmapStore.getState().planId === planId) {
            useHeatmapStore.setState({ status: 'ready', renderMs: msg.ms });
          }
        });
      } else {
        useHeatmapStore.setState({ status: 'error', error: msg.message });
      }
    };
    const scores = base64ToBuffer(data.scores);
    const mask = base64ToBuffer(data.mask);
    const message: ToWorker = {
      type: 'render',
      planId,
      grid,
      scores,
      mask,
      hours: data.hours.length,
      startHour: Math.min(
        Math.floor(useUi.getState().hour + departureOffsetH),
        data.hours.length - 1,
      ),
      size: rasterSize(grid),
    };
    worker.postMessage(message, [scores, mask]);
    return () => {
      active = false;
      if (frame) cancelAnimationFrame(frame);
      if (completionFrame) cancelAnimationFrame(completionFrame);
      for (const p of pending) p.bitmap.close();
      pending.length = 0;
      worker.terminate(); // a replaced plan stops rendering immediately
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- re-run per heatmap response only
  }, [data]);

  return null;
}
