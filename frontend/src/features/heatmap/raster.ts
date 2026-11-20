import type { Grid } from '../../api/types';
import { scoreColor } from '../../lib/risk';

export const NO_DATA = 255;
export const SCALE = 50;
const MAX_SIDE = 512;
const PX_PER_CELL = 5;

/** [west, south, east, north] of the raster: grid cell centres plus half a cell. */
export function rasterBounds(g: Grid): [number, number, number, number] {
  return [
    g.lon0 - g.dlon / 2,
    g.lat0 - g.dlat / 2,
    g.lon0 + (g.cols - 0.5) * g.dlon,
    g.lat0 + (g.rows - 0.5) * g.dlat,
  ];
}

const mercY = (lat: number) => Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
const invMercY = (y: number) => (360 / Math.PI) * Math.atan(Math.exp(y)) - 90;

/** Pixel size: ~5x the grid, aspect taken in Web Mercator so pixels are square on screen. */
export function rasterSize(g: Grid): { w: number; h: number } {
  const [west, south, east, north] = rasterBounds(g);
  const xSpan = ((east - west) * Math.PI) / 180;
  const ySpan = mercY(north) - mercY(south);
  let w = Math.min(g.cols * PX_PER_CELL, MAX_SIDE);
  let h = Math.round((w * ySpan) / xSpan);
  if (h > MAX_SIDE) {
    w = Math.round((w * MAX_SIDE) / h);
    h = MAX_SIDE;
  }
  return { w: Math.max(w, 8), h: Math.max(h, 8) };
}

/** 201-entry RGBA lookup table indexed by the encoded score (0..200). */
export function buildLut(): Uint8ClampedArray {
  const lut = new Uint8ClampedArray(201 * 4);
  for (let i = 0; i <= 200; i++) lut.set(scoreColor(i / SCALE), i * 4);
  return lut;
}

export interface SamplePlan {
  /** fractional grid row for each pixel row (top row = north) */
  gy: Float64Array;
  /** fractional grid column for each pixel column */
  gx: Float64Array;
}

/** Per-row and per-column grid coordinates. Rows are sampled in Mercator y, so the image
 * lines up with the basemap when deck stretches it over the bounds (skill rule 5). */
export function samplePlan(g: Grid, w: number, h: number): SamplePlan {
  const [west, south, east, north] = rasterBounds(g);
  const yTop = mercY(north);
  const dy = (yTop - mercY(south)) / h;
  const dx = (east - west) / w;
  const gy = new Float64Array(h);
  const gx = new Float64Array(w);
  for (let py = 0; py < h; py++) gy[py] = (invMercY(yTop - (py + 0.5) * dy) - g.lat0) / g.dlat;
  for (let px = 0; px < w; px++) gx[px] = (west + (px + 0.5) * dx - g.lon0) / g.dlon;
  return { gy, gx };
}

/** Renders one forecast hour into RGBA pixels. Bilinear over the 4 neighbouring cells,
 * skipping no-data cells and renormalising the weights; edges fade with the covered weight. */
export function renderHour(
  scores: Uint8Array,
  g: Grid,
  hour: number,
  plan: SamplePlan,
  lut: Uint8ClampedArray,
  out: Uint8ClampedArray,
): void {
  const { rows, cols } = g;
  const base = hour * rows * cols;
  const w = plan.gx.length;
  out.fill(0);
  for (let py = 0; py < plan.gy.length; py++) {
    const y = plan.gy[py] as number;
    const r0 = Math.floor(y);
    const fy = y - r0;
    for (let px = 0; px < w; px++) {
      const x = plan.gx[px] as number;
      const c0 = Math.floor(x);
      const fx = x - c0;
      let sum = 0;
      let wsum = 0;
      for (let k = 0; k < 4; k++) {
        const r = r0 + (k >> 1);
        const c = c0 + (k & 1);
        if (r < 0 || c < 0 || r >= rows || c >= cols) continue;
        const v = scores[base + r * cols + c] as number;
        if (v === NO_DATA) continue;
        const wk = (k >> 1 ? fy : 1 - fy) * (k & 1 ? fx : 1 - fx);
        sum += v * wk;
        wsum += wk;
      }
      if (wsum < 0.2) continue; // outside the corridor: transparent
      const li = Math.round(sum / wsum) * 4;
      const o = (py * w + px) * 4;
      out[o] = lut[li] as number;
      out[o + 1] = lut[li + 1] as number;
      out[o + 2] = lut[li + 2] as number;
      out[o + 3] = Math.round((lut[li + 3] as number) * Math.min(1, wsum * 1.6));
    }
  }
}

/** Current hour first, then outward: h, h+1, h-1, h+2, ... (docs/04 §6). */
export function renderOrder(start: number, hours: number): number[] {
  const order = [start];
  for (let d = 1; order.length < hours; d++) {
    if (start + d < hours) order.push(start + d);
    if (start - d >= 0) order.push(start - d);
  }
  return order;
}

export function base64ToBuffer(b64: string): ArrayBuffer {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes.buffer;
}
