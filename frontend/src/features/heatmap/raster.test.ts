import type { Grid } from '../../api/types';
import { scoreColor } from '../../lib/risk';
import {
  NO_DATA,
  base64ToBuffer,
  buildLut,
  rasterBounds,
  rasterSize,
  renderHour,
  renderOrder,
  samplePlan,
} from './raster';

const grid: Grid = { lat0: 40, lon0: -110, dlat: 0.5, dlon: 0.5, rows: 2, cols: 3 };

describe('raster helpers', () => {
  it('bounds extend half a cell past the cell centres', () => {
    expect(rasterBounds(grid)).toEqual([-110.25, 39.75, -108.75, 40.75]);
  });

  it('sizes the image ~5x the grid with a Mercator aspect', () => {
    const { w, h } = rasterSize(grid);
    expect(w).toBe(15);
    expect(h).toBeGreaterThan(9); // 1 deg tall vs 1.5 wide, stretched by Mercator at 40N
  });

  it('LUT has 201 RGBA entries matching the palette', () => {
    const lut = buildLut();
    expect(lut.length).toBe(201 * 4);
    expect(Array.from(lut.slice(100 * 4, 100 * 4 + 4))).toEqual(scoreColor(2));
  });

  it('renders the current hour first, then outward', () => {
    expect(renderOrder(3, 7)).toEqual([3, 4, 2, 5, 1, 6, 0]);
    expect(renderOrder(0, 3)).toEqual([0, 1, 2]);
    expect(renderOrder(2, 3)).toEqual([2, 1, 0]);
  });

  it('decodes base64 to bytes', () => {
    expect(Array.from(new Uint8Array(base64ToBuffer(btoa('\x00\x01\xff'))))).toEqual([0, 1, 255]);
  });
});

describe('renderHour', () => {
  const lut = buildLut();

  function render(scores: number[], hour = 0, hours = 1) {
    const all = new Uint8Array(hours * 6).fill(NO_DATA);
    all.set(scores, hour * 6);
    const plan = samplePlan(grid, 30, 20);
    const out = new Uint8ClampedArray(30 * 20 * 4);
    renderHour(all, grid, hour, plan, lut, out);
    return out;
  }

  const pixel = (out: Uint8ClampedArray, x: number, y: number) =>
    Array.from(out.slice((y * 30 + x) * 4, (y * 30 + x) * 4 + 4));

  it('a uniform field renders the LUT colour everywhere inside', () => {
    const out = render([100, 100, 100, 100, 100, 100]);
    expect(pixel(out, 15, 10)).toEqual(Array.from(lut.slice(400, 404)));
  });

  it('no-data cells are transparent; their neighbours are not', () => {
    // bottom row (south) has data, top row (north) is no data
    const out = render([0, 0, 0, NO_DATA, NO_DATA, NO_DATA]);
    expect(pixel(out, 15, 1)[3]).toBe(0); // near the top edge: transparent
    expect(pixel(out, 15, 18)[3]).toBeGreaterThan(0); // near the bottom: tinted
  });

  it('reads the requested hour slice', () => {
    const out = render([200, 200, 200, 200, 200, 200], 1, 2);
    expect(pixel(out, 15, 10)).toEqual(Array.from(lut.slice(800, 804)));
  });
});
