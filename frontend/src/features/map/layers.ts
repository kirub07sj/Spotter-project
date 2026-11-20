import { PathStyleExtension, type PathStyleExtensionProps } from '@deck.gl/extensions';
import { IconLayer, PathLayer, ScatterplotLayer } from '@deck.gl/layers';
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

export interface RouteLayerData {
  others: MapRoute[];
  selected: MapRoute[];
  segments: MapSegment[];
  checkpoints: Checkpoint[];
  noTravel: MapSegment[];
  confidence: Checkpoint[];
}

/** Run only when plan, selection or visibility changes, never for forecast frames. */
export function prepareRouteLayers(
  data: MapData,
  selectedId: RouteId,
  showAllRoutes: boolean,
  showCheckpoints: boolean,
): RouteLayerData {
  const segments = data.segments.filter((s) => s.routeId === selectedId);
  const checkpoints = showCheckpoints ? (data.checkpoints[selectedId] ?? []) : [];
  return {
    others: showAllRoutes ? data.routes.filter((r) => r.id !== selectedId) : [],
    selected: data.routes.filter((r) => r.id === selectedId),
    segments,
    checkpoints,
    noTravel: segments.filter((s) => s.level === 'NO_TRAVEL'),
    confidence: checkpoints.filter((cp) => cp.low_confidence),
  };
}

const confidenceIcon = {
  url: `data:image/svg+xml,${encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><circle cx="16" cy="16" r="12" fill="none" stroke="black" stroke-width="2" stroke-dasharray="4 3"/></svg>',
  )}`,
  width: 32,
  height: 32,
  mask: true,
};

/** Static route layers (docs/04 §5, layers 5 to 8 and 10). Data references come from
 * useMapData, so rebuilding these objects each frame costs a prop diff, not a re-upload. */
export function routeLayers(data: RouteLayerData, s: LayerState): Layer[] {
  const beforeId = s.beforeId;
  return [
    new PathLayer<MapRoute>({
      id: 'routes-unselected',
      ...below(beforeId),
      data: data.others,
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
      data: data.selected,
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
      data: data.segments,
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
      data: data.noTravel,
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
      data: data.checkpoints,
      getPosition: (cp) => [cp.lon, cp.lat],
      getRadius: (cp) =>
        cp.index === s.hoveredCheckpoint || cp.index === s.emphasizedCheckpoint ? 8 : 5,
      radiusUnits: 'pixels',
      // D-18: a separate dashed ring below marks low confidence.
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
    new IconLayer<Checkpoint>({
      id: 'checkpoint-confidence',
      ...below(beforeId),
      data: data.confidence,
      getPosition: (cp) => [cp.lon, cp.lat],
      getIcon: () => confidenceIcon,
      getSize: (cp) => (cp.index === s.emphasizedCheckpoint ? 28 : 20),
      sizeUnits: 'pixels',
      getColor: (cp) => LEVELS[cp.levels.overall].rgb,
      updateTriggers: { getSize: s.emphasizedCheckpoint },
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
