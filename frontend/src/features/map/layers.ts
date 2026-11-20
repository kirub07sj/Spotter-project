import { PathStyleExtension, type PathStyleExtensionProps } from '@deck.gl/extensions';
import { PathLayer, ScatterplotLayer } from '@deck.gl/layers';
import type { Layer } from '@deck.gl/core';
import type { Checkpoint, RouteId } from '../../api/types';
import { LEVELS } from '../../lib/risk';
import { ROUTE_COLORS } from '../../lib/routes';
import type { MapData, MapRoute, MapSegment } from './useMapData';

export interface LayerState {
  selectedId: RouteId;
  hoveredRouteId: RouteId | null;
  hoveredCheckpoint: number | null;
  emphasizedCheckpoint: number | null;
  showAllRoutes: boolean;
  showCheckpoints: boolean;
  beforeId: string | undefined;
}

const CASING: [number, number, number] = [15, 23, 42];
const dashExtension = [new PathStyleExtension({ dash: true })];

/** Interleaved deck layers accept `beforeId` (draw under basemap labels), but the prop isn't
 * in deck.gl's TypeScript types; an `object`-typed spread passes it through untyped. */
const below = (beforeId: string | undefined): object => (beforeId ? { beforeId } : {});

/** Static route layers (docs/04 §5, layers 5 to 8 and 10). Data references come from
 * useMapData, so rebuilding these objects each frame costs a prop diff, not a re-upload. */
export function routeLayers(data: MapData, s: LayerState, selectedSegments: MapSegment[]): Layer[] {
  const others = s.showAllRoutes ? data.routes.filter((r) => r.id !== s.selectedId) : [];
  const selected = data.routes.filter((r) => r.id === s.selectedId);
  const cps = s.showCheckpoints ? (data.checkpoints[s.selectedId] ?? []) : [];
  const noTravel = selectedSegments.filter((seg) => seg.level === 'NO_TRAVEL');
  const beforeId = s.beforeId;
  return [
    new PathLayer<MapRoute>({
      id: 'routes-unselected',
      ...below(beforeId),
      data: others,
      getPath: (r) => r.path,
      getColor: (r) => [...ROUTE_COLORS[r.id].rgb, r.id === s.hoveredRouteId ? 255 : 170],
      getWidth: (r) => (r.id === s.hoveredRouteId ? 7 : 4),
      widthUnits: 'pixels',
      capRounded: true,
      jointRounded: true,
      pickable: true,
      updateTriggers: { getColor: s.hoveredRouteId, getWidth: s.hoveredRouteId },
    }),
    new PathLayer<MapRoute>({
      id: 'route-selected-casing',
      ...below(beforeId),
      data: selected,
      getPath: (r) => r.path,
      getColor: CASING,
      getWidth: 10,
      widthUnits: 'pixels',
      capRounded: true,
      jointRounded: true,
    }),
    new PathLayer<MapSegment>({
      id: 'route-selected-risk',
      ...below(beforeId),
      data: selectedSegments,
      getPath: (seg) => seg.path,
      getColor: (seg) => LEVELS[seg.level].rgb,
      getWidth: 6,
      widthUnits: 'pixels',
      capRounded: true,
      jointRounded: true,
      pickable: true,
    }),
    // D-12: No Travel stretches get a dashed purple overlay on top of the risk colour.
    new PathLayer<MapSegment, PathStyleExtensionProps<MapSegment>>({
      id: 'route-selected-no-travel',
      ...below(beforeId),
      data: noTravel,
      getPath: (seg) => seg.path,
      getColor: [255, 255, 255],
      getWidth: 2,
      widthUnits: 'pixels',
      getDashArray: [3, 2],
      dashJustified: true,
      extensions: dashExtension,
    }),
    new ScatterplotLayer<Checkpoint>({
      id: 'checkpoints',
      ...below(beforeId),
      data: cps,
      getPosition: (cp) => [cp.lon, cp.lat],
      getRadius: (cp) =>
        cp.index === s.hoveredCheckpoint || cp.index === s.emphasizedCheckpoint ? 8 : 5,
      radiusUnits: 'pixels',
      // D-18: low-confidence checkpoints are drawn hollow so the forecast reads as uncertain.
      getFillColor: (cp) => [...LEVELS[cp.levels.overall].rgb, cp.low_confidence ? 60 : 255],
      getLineColor: (cp) => (cp.low_confidence ? LEVELS[cp.levels.overall].rgb : [255, 255, 255]),
      getLineWidth: (cp) => (cp.index === s.emphasizedCheckpoint ? 3 : 1.5),
      lineWidthUnits: 'pixels',
      stroked: true,
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 255, 120],
      updateTriggers: {
        getRadius: [s.hoveredCheckpoint, s.emphasizedCheckpoint],
        getLineWidth: s.emphasizedCheckpoint,
      },
    }),
  ];
}

export function endpointLayer(data: MapData): Layer {
  return new ScatterplotLayer<MapData['endpoints'][number]>({
    id: 'endpoints',
    data: data.endpoints,
    getPosition: (e) => e.position,
    getRadius: 8,
    radiusUnits: 'pixels',
    getFillColor: (e) => (e.kind === 'origin' ? [255, 255, 255] : CASING),
    getLineColor: CASING,
    getLineWidth: 3,
    lineWidthUnits: 'pixels',
    stroked: true,
  });
}
