import type { LonLat } from './polyline';
import { truckPositionAt } from './truck';

const path: LonLat[] = [
  [0, 0],
  [1, 0],
  [1, 2],
];
const cum = [0, 100, 300];

describe('truckPositionAt', () => {
  it('interpolates between vertices by time', () => {
    expect(truckPositionAt(path, cum, 50)).toEqual({ position: [0.5, 0], state: 'driving' });
    expect(truckPositionAt(path, cum, 200)).toEqual({ position: [1, 1], state: 'driving' });
    expect(truckPositionAt(path, cum, 100)).toEqual({ position: [1, 0], state: 'driving' });
  });

  it('pins to the ends before departure and after arrival', () => {
    expect(truckPositionAt(path, cum, -10)).toEqual({ position: [0, 0], state: 'waiting' });
    expect(truckPositionAt(path, cum, 0)?.state).toBe('driving');
    expect(truckPositionAt(path, cum, 999)).toEqual({ position: [1, 2], state: 'arrived' });
  });

  it('handles repeated timestamps and empty input', () => {
    expect(
      truckPositionAt(
        [
          [0, 0],
          [1, 1],
          [2, 2],
        ],
        [0, 10, 10],
        10,
      )?.state,
    ).toBe('arrived');
    expect(truckPositionAt([], [], 5)).toBeNull();
  });

  it('is O(log n) on long routes', () => {
    const n = 2000;
    const long: LonLat[] = Array.from({ length: n }, (_, i) => [i, 0]);
    const t = Array.from({ length: n }, (_, i) => i * 10);
    expect(truckPositionAt(long, t, 12_345)?.position[0]).toBeCloseTo(1234.5);
  });
});
