import { BitmapLayer, IconLayer, ScatterplotLayer } from '@deck.gl/layers';
import type { Layer } from '@deck.gl/core';
import type { RouteId } from '../../api/types';
import type { LonLat } from '../../lib/polyline';
import { ROUTE_COLORS } from '../../lib/routes';
import { nearestBitmap } from './store';

export interface HeatmapLayerInput {
  bitmaps: (ImageBitmap | undefined)[];
  bounds: [number, number, number, number];
  /** fractional index into the hourly bitmaps */
  position: number;
  opacity: number;
  beforeId: string | undefined;
}

const below = (beforeId: string | undefined): object => (beforeId ? { beforeId } : {});

/** Two BitmapLayers crossfading between neighbouring hours: the slider only swaps `image`
 * and `opacity`, never recomputes pixels (docs/04 §6 step 5). */
export function heatmapLayers({
  bitmaps,
  bounds,
  position,
  opacity,
  beforeId,
}: HeatmapLayerInput): Layer[] {
  const last = Math.max(bitmaps.length - 1, 0);
  const p = Math.min(Math.max(position, 0), last);
  const base = Math.floor(p);
  const f = p - base;
  const current = nearestBitmap(bitmaps, base);
  const next = bitmaps[Math.min(base + 1, last)];
  return [
    new BitmapLayer({
      id: 'heatmap-current',
      ...below(beforeId),
      image: current ?? null,
      bounds,
      opacity: opacity * (next ? 1 - f : 1),
      visible: Boolean(current),
      parameters: { depthWriteEnabled: false },
    }),
    new BitmapLayer({
      id: 'heatmap-next',
      ...below(beforeId),
      image: next ?? null,
      bounds,
      opacity: opacity * f,
      visible: Boolean(next) && f > 0.001,
      parameters: { depthWriteEnabled: false },
    }),
  ];
}

export interface TruckDatum {
  id: RouteId;
  position: LonLat;
  selected: boolean;
  moving: boolean;
}

const TRUCK_SVG = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><path d="M8 40V20h30v20zm30-14h10l8 9v5H38z" fill="#000"/><circle cx="18" cy="44" r="6" fill="#000"/><circle cx="46" cy="44" r="6" fill="#000"/></svg>',
)}`;
const TRUCK_ICON = { url: TRUCK_SVG, width: 64, height: 64, mask: true };
const WHITE: [number, number, number] = [255, 255, 255];

/** Truck markers at the slider time: a route-coloured disc with a white truck glyph. */
export function truckLayers(trucks: TruckDatum[]): Layer[] {
  const key = trucks.map((t) => `${t.id}${t.selected ? 1 : 0}${t.moving ? 1 : 0}`).join();
  return [
    new ScatterplotLayer<TruckDatum>({
      id: 'truck-discs',
      data: trucks,
      getPosition: (t) => t.position,
      getRadius: (t) => (t.selected ? 15 : 11),
      radiusUnits: 'pixels',
      getFillColor: (t) => [...ROUTE_COLORS[t.id].rgb, t.moving ? 255 : 130],
      getLineColor: WHITE,
      getLineWidth: 2,
      lineWidthUnits: 'pixels',
      stroked: true,
      updateTriggers: { getRadius: key, getFillColor: key },
    }),
    new IconLayer<TruckDatum>({
      id: 'truck-glyphs',
      data: trucks,
      getPosition: (t) => t.position,
      getIcon: () => TRUCK_ICON,
      getSize: (t) => (t.selected ? 20 : 15),
      sizeUnits: 'pixels',
      getColor: WHITE,
      updateTriggers: { getSize: key },
    }),
  ];
}
