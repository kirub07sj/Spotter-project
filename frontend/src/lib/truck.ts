import type { LonLat } from './polyline';

export interface TruckPosition {
  position: LonLat;
  /** before departure / after arrival the marker is pinned to an end and dimmed */
  state: 'waiting' | 'driving' | 'arrived';
}

/** Position at `t` seconds after departure: binary search on the per-vertex cumulative
 * time, then linear interpolation. O(log n) per route per frame. Presentation only. */
export function truckPositionAt(
  path: LonLat[],
  cumTimeS: number[],
  t: number,
): TruckPosition | null {
  const n = Math.min(path.length, cumTimeS.length);
  if (n === 0) return null;
  const first = path[0] as LonLat;
  const last = path[n - 1] as LonLat;
  if (t <= 0) return { position: first, state: t < 0 ? 'waiting' : 'driving' };
  if (t >= (cumTimeS[n - 1] as number)) return { position: last, state: 'arrived' };
  let lo = 0;
  let hi = n - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if ((cumTimeS[mid] as number) <= t) lo = mid;
    else hi = mid;
  }
  const t0 = cumTimeS[lo] as number;
  const t1 = cumTimeS[hi] as number;
  const f = t1 > t0 ? (t - t0) / (t1 - t0) : 0;
  const a = path[lo] as LonLat;
  const b = path[hi] as LonLat;
  return { position: [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f], state: 'driving' };
}
