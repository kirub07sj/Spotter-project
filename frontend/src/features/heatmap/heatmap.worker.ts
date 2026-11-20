/// <reference lib="webworker" />
import type { FromWorker, ToWorker } from './protocol';
import { buildLut, renderHour, renderOrder, samplePlan } from './raster';

declare const self: DedicatedWorkerGlobalScope;
const lut = buildLut();

function post(msg: FromWorker, transfer: Transferable[] = []) {
  self.postMessage(msg, transfer);
}

self.onmessage = async (event: MessageEvent<ToWorker>) => {
  const msg = event.data;
  const started = performance.now();
  try {
    const scores = new Uint8Array(msg.scores);
    const { w, h } = msg.size;
    const plan = samplePlan(msg.grid, w, h);
    for (const hour of renderOrder(msg.startHour, msg.hours)) {
      const pixels = new Uint8ClampedArray(w * h * 4);
      renderHour(scores, msg.grid, hour, plan, lut, pixels);
      const bitmap = await createImageBitmap(new ImageData(pixels, w, h));
      post({ type: 'bitmap', planId: msg.planId, hour, bitmap }, [bitmap]);
    }
    post({ type: 'done', planId: msg.planId, ms: performance.now() - started });
  } catch (err) {
    post({
      type: 'error',
      planId: msg.planId,
      message: err instanceof Error ? err.message : String(err),
    });
  }
};
