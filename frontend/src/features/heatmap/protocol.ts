import type { Grid } from '../../api/types';

/** Typed worker messages (map-performance skill). */
export type ToWorker = {
  type: 'render';
  planId: string;
  grid: Grid;
  scores: ArrayBuffer;
  mask: ArrayBuffer;
  hours: number;
  startHour: number;
  size: { w: number; h: number };
};

export type FromWorker =
  | { type: 'bitmap'; planId: string; hour: number; bitmap: ImageBitmap }
  | { type: 'done'; planId: string; ms: number }
  | { type: 'error'; planId: string; message: string };
